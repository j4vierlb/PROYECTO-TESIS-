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

# El logger deja avisos y errores escritos en la consola del backend
# (se ven con: docker compose logs backend). Es mejor que usar print().
logger = logging.getLogger(__name__)
# Zona horaria de Chile. La IA necesita saber qué hora es allá para
# convertir frases como 'mañana' o 'el viernes' en una fecha real.
SANTIAGO = ZoneInfo("America/Santiago")

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
MAX_WHATSAPP_CHARS = 1600  # máximo que acepta WhatsApp por mensaje
MAX_INTENT_CHARS = 50      # largo de mensajes_whatsapp.intencion_detectada
# Las únicas dos cosas que dejamos hacer a la IA: solo responder, o pedir
# que se cree una visita. Cualquier otra acción se descarta más abajo.
VALID_ACTIONS = {"reply", "create_appointment"}
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]

# El 'prompt del sistema' son las instrucciones fijas que se le dan a la IA
# antes de cada conversación: quién es, qué reglas tiene y en qué formato
# debe contestar. Aquí es donde se le ordena devolver siempre un JSON.
SYSTEM_PROMPT = """
Eres el agente conversacional de Kill Bichos, empresa chilena de control de plagas.
Tu trabajo es atender clientes por WhatsApp de forma amable, breve y natural.

Reglas:
- Habla en español claro, cordial y chileno neutro.
- En tu primer mensaje de la conversación, cuando saludes o respondas por primera vez, preséntate
  brevemente como el asistente virtual de Kill Bichos (por ejemplo: "Hola, soy el asistente virtual
  de Kill Bichos"). Si ya respondiste antes en esta conversación, no repitas la presentación.
- No inventes disponibilidad ni confirmes una visita si el backend no la crea.
- Si el cliente quiere agendar, necesitas una fecha y una hora concretas. Si falta una, pregunta.
- Si el cliente dice 'mañana', 'este viernes', etc., conviértelo usando la fecha actual proporcionada.
- No rechaces horarios por tu cuenta ni inventes disponibilidad. Si el cliente pide una fecha
  y hora concretas para agendar (aunque parezcan fuera del horario de atención u ocupadas) y ya
  tienes su dirección, usa action=create_appointment con esa fecha y hora: el sistema la valida
  y, si no se puede, le ofrece automáticamente el horario libre más cercano. Esto aplica aunque
  en mensajes anteriores de la conversación se haya respondido distinto.
- Antes de crear la PRIMERA visita de un cliente (el contexto indica "Visitas previas: 0") necesitas su
  nombre real. El nombre registrado puede ser solo su nombre de perfil de WhatsApp o "Cliente WhatsApp",
  así que pregúntalo siempre ("¿Me indicas tu nombre completo?") y no agendes hasta que lo entregue.
  Cuando lo dé, devuélvelo en client_name. Si el cliente ya tiene visitas previas no se lo vuelvas a pedir.
- Antes de crear una visita, necesitas la dirección del cliente. Si no está registrada y el cliente quiere agendar, pregunta por ella.
- Atendemos en cualquier lugar de Chile. Pide la dirección completa: calle, número y comuna o ciudad
  (por ejemplo "Av. Libertad 1000, Viña del Mar"). Si el cliente la da sin comuna o ciudad, vuelve a
  preguntar por la comuna antes de agendar, porque sin ella no se puede ubicar el lugar en el mapa.
- Si en la conversación se le ofreció al cliente un horario alternativo y lo acepta, usa ese horario.
- Para consultas generales responde directamente sin inventar precios, horarios comerciales o servicios no indicados.
- Si el cliente pide cancelar/reagendar, no ejecutes cambios todavía: indícale que un operador debe confirmar la modificación.
- Devuelve SIEMPRE JSON válido con exactamente estas claves:
  action, intent, reply, appointment_datetime, client_address, client_name, notes

Valores permitidos para action: reply, create_appointment.
intent debe ser una cadena corta como consulta, agendar_visita, confirmar_horario, reagendar, cancelar.
appointment_datetime debe ser ISO 8601 con zona horaria de Chile (ej: 2026-10-01T10:00:00-03:00) si action=create_appointment; en otro caso null.
client_address debe contener la dirección entregada por el cliente si existe; si no, usa null.
client_name debe contener el nombre real que el cliente entregó en la conversación; si no lo ha dado, usa null.
notes debe ser texto breve o null.
"""


SCHEDULING_REMINDER = (
    "Recordatorio: responde solo al ÚLTIMO mensaje del cliente. Si ese mensaje pide agendar una "
    "visita en una fecha y hora concretas (o acepta un horario que se le ofreció) y hay dirección, "
    "usa action=create_appointment con esa fecha y hora aunque esté fuera del horario de atención: "
    "no la rechaces tú, el sistema ofrece la alternativa. Si el último mensaje es una consulta, "
    "un saludo, una cancelación o un cambio de una visita, usa action=reply."
)


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
    # Busca la primera '{' y la última '}'. A veces el modelo agrega texto o
    # comillas ``` alrededor del JSON; así nos quedamos solo con el JSON.
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
    # Nunca se confía ciegamente en la IA. Si inventa una acción que no
    # existe, la cambiamos por 'reply' (solo responder), que es lo más seguro.
    action = result.get("action")
    if action not in VALID_ACTIONS:
        logger.warning("La IA devolvió una action inválida: %r", action)
        action = "reply"

    reply = _optional_text(result.get("reply")) or "No pude procesar tu solicitud."
    intent = _optional_text(result.get("intent")) or "consulta"
    return {
        "action": action,
        # Los [:N] recortan el texto a un largo máximo, para no pasarnos del
        # tamaño de la columna en la base ni del límite de caracteres de WhatsApp.
        "intent": intent[:MAX_INTENT_CHARS],
        "reply": reply[:MAX_WHATSAPP_CHARS],
        "appointment_datetime": _optional_text(result.get("appointment_datetime")),
        "client_address": _optional_text(result.get("client_address")),
        "client_name": _optional_text(result.get("client_name")),
        "notes": _optional_text(result.get("notes")),
    }


def generate_agent_decision(
    history: list[dict],
    client_name: str,
    client_address: str | None,
    previous_visits: int | None = None,
) -> dict:
    """Llama a OpenAI con el historial y devuelve la decisión ya validada.

    Es síncrona a propósito (httpx.Client): el endpoint de WhatsApp es un
    `def` normal que FastAPI ejecuta en un hilo aparte, así que esperar aquí
    no bloquea al resto del servidor. Cualquier error (sin API key, timeout,
    JSON inválido) se propaga para que el router responda un mensaje de
    contingencia al cliente."""
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY no está configurada")

    # Se le dice a la IA la fecha y hora actual en cada llamada, porque un
    # modelo de lenguaje no sabe por sí solo qué día es hoy.
    now = datetime.now(SANTIAGO)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "system",
            "content": (
                f"Fecha y hora actual en Santiago de Chile: {now.isoformat()} ({DIAS[now.weekday()]}). "
                f"{_business_hours_text()} "
                f"Cliente: {client_name}. Dirección registrada: {client_address or 'no registrada'}. "
                f"Visitas previas: {previous_visits if previous_visits is not None else 'desconocido'}."
            ),
        },
    ]
    # El historial se traduce al formato de OpenAI: lo que escribió el cliente
    # es 'user' y lo que respondió nuestro bot es 'assistant'.
    for item in history:
        messages.append({
            "role": "user" if item["emisor"] == "cliente" else "assistant",
            "content": item["contenido"],
        })
    # Recordatorio al final, después del historial: es lo último que lee el
    # modelo. Sin esto, si antes rechazó un horario, tiende a repetir esa
    # respuesta en vez de dejar que el backend ofrezca el siguiente libre.
    messages.append({"role": "system", "content": SCHEDULING_REMINDER})

    payload = {
        "model": settings.openai_model,
        "messages": messages,
        # temperature baja (0.2) = respuestas más predecibles y menos 'creativas'.
        # Para agendar visitas queremos consistencia, no inventiva.
        "temperature": 0.2,
        # Obliga al modelo a contestar con un JSON válido, para poder leerlo
        # desde el código sin adivinar.
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }

    # timeout=30: si OpenAI no responde en 30 segundos se corta el intento y
    # el router le manda al cliente el mensaje de contingencia.
    with httpx.Client(timeout=30) as client:
        response = client.post(OPENAI_URL, json=payload, headers=headers)
        # Si OpenAI devolvió un error (401, 429, 500...), esto lanza una excepción
        # en vez de seguir como si nada hubiera pasado.
        response.raise_for_status()
        data = response.json()

    content = data["choices"][0]["message"]["content"]
    return _validate_decision(_extract_json(content))
