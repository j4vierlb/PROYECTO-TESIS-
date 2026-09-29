# =============================================================================
# ai/agent.py — Agente conversacional (OpenAI) para WhatsApp
# -----------------------------------------------------------------------------
# Recibe el historial de la conversación con un cliente y le pide al modelo
# que decida qué hacer: solo responder, o solicitar la creación de una visita.
# El modelo SIEMPRE devuelve JSON; aquí se valida antes de que el router lo
# use, porque la respuesta de una IA nunca es 100% confiable.
#
# Este módulo no toca la base de datos: la decisión final (crear o no la
# visita) la toma el router después de validar fecha, horario y operador.
# =============================================================================

import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

from app.config import settings

logger = logging.getLogger(__name__)
SANTIAGO = ZoneInfo("America/Santiago")

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
MAX_WHATSAPP_CHARS = 1600  # máximo que acepta WhatsApp por mensaje
MAX_INTENT_CHARS = 50      # largo de mensajes_whatsapp.intencion_detectada
VALID_ACTIONS = {"reply", "create_appointment"}
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]

SYSTEM_PROMPT = """
Eres el agente conversacional de Kill Bichos, empresa chilena de control de plagas.
Tu trabajo es atender clientes por WhatsApp de forma amable, breve y natural.

Reglas:
- Habla en español claro, cordial y chileno neutro.
- No inventes disponibilidad ni confirmes una visita si el backend no la crea.
- Si el cliente quiere agendar, necesitas una fecha y una hora concretas. Si falta una, pregunta.
- Si el cliente dice 'mañana', 'este viernes', etc., conviértelo usando la fecha actual proporcionada.
- Solo propone o aceptes horarios dentro del horario de atención indicado.
- Antes de crear una visita, necesitas la dirección del cliente. Si no está registrada y el cliente quiere agendar, pregunta por ella.
- Si en la conversación se le ofreció al cliente un horario alternativo y lo acepta, usa ese horario.
- Para consultas generales responde directamente sin inventar precios, horarios comerciales o servicios no indicados.
- Si el cliente pide cancelar/reagendar, no ejecutes cambios todavía: indícale que un operador debe confirmar la modificación.
- Devuelve SIEMPRE JSON válido con exactamente estas claves:
  action, intent, reply, appointment_datetime, client_address, notes

Valores permitidos para action: reply, create_appointment.
intent debe ser una cadena corta como consulta, agendar_visita, confirmar_horario, reagendar, cancelar.
appointment_datetime debe ser ISO 8601 con zona horaria de Chile (ej: 2026-10-01T10:00:00-03:00) si action=create_appointment; en otro caso null.
client_address debe contener la dirección entregada por el cliente si existe; si no, usa null.
notes debe ser texto breve o null.
"""


def _business_hours_text() -> str:
    """Describe el horario de atención configurado en el .env, para que la IA
    no proponga horarios que el backend después va a rechazar."""
    days = [
        DIAS[int(d)]
        for d in settings.killbichos_operating_days.split(",")
        if d.strip().isdigit() and 0 <= int(d) <= 6
    ]
    return (
        f"Horario de atención: {', '.join(days)}, "
        f"de {settings.killbichos_open_time} a {settings.killbichos_close_time}."
    )


def _extract_json(text: str) -> dict:
    """Obtiene el objeto JSON de la respuesta, aunque venga envuelto en ```."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("La IA no devolvió JSON")
    return json.loads(text[start:end + 1])


def _optional_text(value: object) -> str | None:
    """Convierte a texto limpio, o None si viene vacío o no es texto."""
    if not isinstance(value, str):
        return None
    return value.strip() or None


def _validate_decision(result: dict) -> dict:
    """Asegura que la respuesta de la IA tenga la forma que el router espera:
    action válida, reply recortado al máximo de WhatsApp e intent acotado al
    largo de la columna en la base de datos."""
    action = result.get("action")
    if action not in VALID_ACTIONS:
        logger.warning("La IA devolvió una action inválida: %r", action)
        action = "reply"

    reply = _optional_text(result.get("reply")) or "No pude procesar tu solicitud."
    intent = _optional_text(result.get("intent")) or "consulta"
    return {
        "action": action,
        "intent": intent[:MAX_INTENT_CHARS],
        "reply": reply[:MAX_WHATSAPP_CHARS],
        "appointment_datetime": _optional_text(result.get("appointment_datetime")),
        "client_address": _optional_text(result.get("client_address")),
        "notes": _optional_text(result.get("notes")),
    }


def generate_agent_decision(
    history: list[dict],
    client_name: str,
    client_address: str | None,
) -> dict:
    """Llama a OpenAI con el historial y devuelve la decisión ya validada.

    Es síncrona a propósito (httpx.Client): el endpoint de WhatsApp es un
    `def` normal que FastAPI ejecuta en un hilo aparte, así que esperar aquí
    no bloquea al resto del servidor. Cualquier error (sin API key, timeout,
    JSON inválido) se propaga para que el router responda un mensaje de
    contingencia al cliente."""
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY no está configurada")

    now = datetime.now(SANTIAGO)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "system",
            "content": (
                f"Fecha y hora actual en Santiago de Chile: {now.isoformat()} ({DIAS[now.weekday()]}). "
                f"{_business_hours_text()} "
                f"Cliente: {client_name}. Dirección registrada: {client_address or 'no registrada'}."
            ),
        },
    ]
    for item in history:
        messages.append({
            "role": "user" if item["emisor"] == "cliente" else "assistant",
            "content": item["contenido"],
        })

    payload = {
        "model": settings.openai_model,
        "messages": messages,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=30) as client:
        response = client.post(OPENAI_URL, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

    content = data["choices"][0]["message"]["content"]
    return _validate_decision(_extract_json(content))
