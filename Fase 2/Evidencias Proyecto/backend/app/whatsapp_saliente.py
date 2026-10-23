# =============================================================================
# whatsapp_saliente.py — Mensajes de WhatsApp que el sistema le envía al cliente
# -----------------------------------------------------------------------------
# El webhook (routers/whatsapp.py) solo CONTESTA lo que el cliente escribe.
# Este módulo es para lo que se envía por iniciativa propia, con la API REST
# de Twilio:
#   - avisos cuando el panel agenda, reagenda o cancela una visita;
#   - el recordatorio del día anterior a la visita;
#   - lo que escribe un operador desde la bandeja del panel.
#
# Regla de WhatsApp: solo se puede enviar texto libre hasta 24 h después del
# último mensaje del cliente. Fuera de esa ventana solo se aceptan
# plantillas aprobadas (ContentSid). Si no hay plantilla configurada, el
# mensaje se guarda como "no_enviado" en vez de llamar a Twilio para que lo
# rechace.
#
# Todo mensaje enviado queda en mensajes_whatsapp, y Twilio informa después
# si llegó (POST /webhooks/whatsapp/estado).
# =============================================================================

import json
import logging
import re
from datetime import datetime, time, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.engine import Connection

from app.ai.agent import MAX_WHATSAPP_CHARS
from app.config import settings
from app.repositories import (
    claim_visits_for_reminder,
    client_wrote_since,
    fetch_active_whatsapp_conversation,
    fetch_whatsapp_client,
    insert_whatsapp_message,
    release_reminder_claim,
    update_whatsapp_delivery,
)
from app.zona_horaria import ZONA_CHILE, ahora_chile

logger = logging.getLogger(__name__)
UTC = timezone.utc
VENTANA_SESION = timedelta(hours=24)

# Eventos de una visita que se le avisan al cliente.
AVISO_AGENDADA = "agendada"
AVISO_REAGENDADA = "reagendada"
AVISO_CANCELADA = "cancelada"


def twilio_configurado() -> bool:
    return bool(settings.twilio_account_sid and settings.twilio_auth_token and settings.twilio_whatsapp_number)


def status_callback_base() -> str:
    """URL pública del webhook de estado, sin parámetros."""
    if settings.twilio_status_callback_url.strip():
        return settings.twilio_status_callback_url.strip()
    if settings.twilio_webhook_url.strip():
        return settings.twilio_webhook_url.strip().rstrip("/") + "/estado"
    return ""


def status_callback_url(mensaje_id: UUID | str) -> str | None:
    """URL donde Twilio informará el estado de ese mensaje. Lleva el id del
    mensaje para encontrarlo aunque todavía no tenga MessageSid (pasa con
    las respuestas TwiML del agente)."""
    base = status_callback_base()
    return f"{base}?mensaje_id={mensaje_id}" if base else None


def whatsapp_address(phone: str) -> str:
    """Número en el formato que pide Twilio: 'whatsapp:+56912345678'.
    Los clientes creados en el panel pueden traer espacios o venir sin el
    código de Chile (ej: '9 1234 5678')."""
    phone = phone.removeprefix("whatsapp:").strip()
    digits = re.sub(r"\D", "", phone)
    if phone.startswith("+"):
        number = f"+{digits}"
    elif len(digits) == 9 and digits.startswith("9"):
        number = f"+56{digits}"
    else:
        number = f"+{digits}"
    return f"whatsapp:{number}"


def _describe_twilio_error(exc: Exception) -> str:
    code = getattr(exc, "code", None)
    message = getattr(exc, "msg", None) or str(exc)
    return f"{code}: {message}" if code else message


def _error_pasajero(exc: Exception) -> bool:
    """True si vale la pena reintentar: Twilio caído (5xx), demasiadas
    solicitudes (429) o un error de red sin respuesta de Twilio. Un número
    inválido o una plantilla rechazada (4xx) fallaría igual al reintentar."""
    status = getattr(exc, "status", None)
    if status is None:
        return getattr(exc, "code", None) is None
    return status == 429 or status >= 500


def _twilio_client():
    from twilio.rest import Client  # import local: solo se necesita al enviar

    return Client(settings.twilio_account_sid, settings.twilio_auth_token)


def ventana_abierta(db: Connection, cliente_id: UUID) -> bool:
    return client_wrote_since(db, cliente_id, datetime.now(UTC) - VENTANA_SESION)


def enviar_whatsapp(
    db: Connection,
    cliente_id: UUID,
    texto: str,
    *,
    emisor: str = "sistema",
    intencion: str | None = None,
    content_sid: str = "",
    content_variables: dict[str, str] | None = None,
) -> dict[str, Any] | None:
    """Envía `texto` al cliente y lo guarda en su conversación activa.
    Si la ventana de 24 h está cerrada se usa la plantilla `content_sid`
    (con `content_variables`). Nunca lanza por un error de Twilio: el error
    queda en el mensaje (estado_entrega 'failed' o 'no_enviado'). Devuelve
    el mensaje guardado, o None si el cliente no existe."""
    client = fetch_whatsapp_client(db, cliente_id)
    if client is None:
        return None
    texto = texto[:MAX_WHATSAPP_CHARS]
    abierta = ventana_abierta(db, cliente_id)

    motivo_no_envio = None
    if not twilio_configurado():
        motivo_no_envio = "Twilio no está configurado"
    elif not abierta and not content_sid:
        motivo_no_envio = "El cliente no escribe hace más de 24 h y no hay plantilla aprobada configurada"

    conversation = fetch_active_whatsapp_conversation(db, cliente_id)
    mensaje = insert_whatsapp_message(
        db, conversation["id"], emisor, texto, intencion,
        delivery_status="no_enviado" if motivo_no_envio else "queued",
        delivery_error=motivo_no_envio,
    )
    if motivo_no_envio:
        logger.warning("WhatsApp a %s no enviado (%s): %s", cliente_id, intencion, motivo_no_envio)
        return mensaje

    params: dict[str, Any] = {
        "from_": whatsapp_address(settings.twilio_whatsapp_number),
        "to": whatsapp_address(client["telefono_whatsapp"]),
    }
    callback = status_callback_url(mensaje["id"])
    if callback:
        params["status_callback"] = callback
    if abierta:
        params["body"] = texto
    else:
        params["content_sid"] = content_sid
        params["content_variables"] = json.dumps(content_variables or {}, ensure_ascii=False)

    try:
        sent = _twilio_client().messages.create(**params)
    except Exception as exc:
        error = _describe_twilio_error(exc)
        logger.warning("Twilio rechazó el WhatsApp a %s (%s): %s", cliente_id, intencion, error)
        update_whatsapp_delivery(db, "failed", message_id=mensaje["id"], error=error)
        return {**mensaje, "estado_entrega": "failed", "error_entrega": error, "reintentable": _error_pasajero(exc)}

    estado = sent.status or "queued"
    update_whatsapp_delivery(db, estado, message_id=mensaje["id"], message_sid=sent.sid)
    return {**mensaje, "message_sid": sent.sid, "estado_entrega": estado}


# ---------------------------------------------------------------------------
# Textos de los avisos
# ---------------------------------------------------------------------------

def _saludo(nombre: str | None) -> str:
    """'Hola Ana' con el primer nombre. Los clientes nuevos de WhatsApp sin
    nombre de perfil se llaman 'Cliente WhatsApp +569...': a esos, solo 'Hola'."""
    nombre = (nombre or "").strip()
    if not nombre or nombre.startswith("Cliente WhatsApp"):
        return "Hola"
    return f"Hola {nombre.split()[0]}"


def _fecha_hora_chile(fecha_hora: datetime) -> tuple[str, str]:
    local = fecha_hora.astimezone(ZONA_CHILE)
    return local.strftime("%d/%m/%Y"), local.strftime("%H:%M")


def texto_aviso(evento: str, nombre: str | None, fecha_hora: datetime) -> str:
    fecha, hora = _fecha_hora_chile(fecha_hora)
    saludo = _saludo(nombre)
    if evento == AVISO_AGENDADA:
        return (
            f"{saludo} 😊 Agendamos tu visita de control de plagas para el {fecha} a las {hora} "
            "(hora de Chile). Si necesitas cambiarla, respóndenos por aquí."
        )
    if evento == AVISO_REAGENDADA:
        return (
            f"{saludo}, tu visita de control de plagas se cambió para el {fecha} a las {hora} "
            "(hora de Chile). Si no te acomoda, respóndenos por aquí."
        )
    if evento == AVISO_CANCELADA:
        return (
            f"{saludo}, tu visita de control de plagas del {fecha} a las {hora} fue cancelada. "
            "Si quieres agendar otra, escríbenos por aquí 😊"
        )
    raise ValueError(f"Evento de aviso desconocido: {evento}")


def texto_recordatorio(nombre: str | None, fecha_hora: datetime) -> str:
    fecha, hora = _fecha_hora_chile(fecha_hora)
    return (
        f"{_saludo(nombre)} 😊 Te recordamos tu visita de control de plagas mañana {fecha} "
        f"a las {hora} (hora de Chile). Si necesitas cambiarla, respóndenos por aquí."
    )


# ---------------------------------------------------------------------------
# Avisos y recordatorios
# ---------------------------------------------------------------------------

def avisar_visita(db: Connection, visita: dict[str, Any], evento: str) -> dict[str, Any] | None:
    """Le avisa al cliente un cambio en su visita. `visita` necesita
    cliente_id, cliente_nombre y fecha_hora. No avisa visitas que ya pasaron
    (ej: una visita antigua registrada o cancelada a posteriori)."""
    if visita["fecha_hora"] <= datetime.now(UTC):
        return None
    texto = texto_aviso(evento, visita.get("cliente_nombre"), visita["fecha_hora"])
    return enviar_whatsapp(
        db, visita["cliente_id"], texto,
        intencion=f"aviso_{evento}",
        content_sid=settings.twilio_content_sid_aviso,
        content_variables={"1": texto},
    )


def avisar_visita_en_segundo_plano(visita: dict[str, Any], evento: str) -> None:
    """Tarea de BackgroundTasks: el panel responde sin esperar a Twilio.
    Abre su propia conexión, porque corre después de responder el request."""
    if not settings.whatsapp_avisos_activos or not twilio_configurado():
        return
    from app.database import engine  # import local: las pruebas sin BD no lo necesitan

    try:
        with engine.connect() as db:
            avisar_visita(db, visita, evento)
    except Exception:
        logger.exception("No se pudo enviar el aviso '%s' de la visita %s", evento, visita.get("id"))


def _hora_recordatorio() -> time:
    try:
        return time.fromisoformat(settings.whatsapp_recordatorio_hora)
    except ValueError:
        logger.warning("WHATSAPP_RECORDATORIO_HORA=%s no es una hora válida; se usa 18:00",
                       settings.whatsapp_recordatorio_hora)
        return time(18, 0)


def enviar_recordatorios(
    db: Connection,
    ahora: datetime | None = None,
    *,
    empresa_id: UUID | None = None,
    respetar_hora: bool = True,
) -> list[dict[str, Any]]:
    """Envía el recordatorio a las visitas de mañana (día de Chile) que aún
    no lo tienen. Con respetar_hora=True no hace nada antes de
    WHATSAPP_RECORDATORIO_HORA. Devuelve los mensajes guardados.
    Si Twilio falla por algo pasajero, la visita se libera y el ciclo de
    main.py lo reintenta en 10 minutos (hasta que la visita deja de ser
    "de mañana" a medianoche)."""
    ahora = (ahora or ahora_chile()).astimezone(ZONA_CHILE)
    if respetar_hora and ahora.time() < _hora_recordatorio():
        return []
    manana = ahora.date() + timedelta(days=1)
    enviados = []
    for visita in claim_visits_for_reminder(db, manana, empresa_id):
        try:
            client = fetch_whatsapp_client(db, visita["cliente_id"])
            fecha, hora = _fecha_hora_chile(visita["fecha_hora"])
            mensaje = enviar_whatsapp(
                db, visita["cliente_id"],
                texto_recordatorio(client["nombre"] if client else None, visita["fecha_hora"]),
                intencion="recordatorio",
                content_sid=settings.twilio_content_sid_recordatorio,
                content_variables={"1": fecha, "2": hora},
            )
        except Exception:
            logger.exception("Falló el recordatorio de la visita %s; se reintentará", visita["id"])
            db.rollback()
            release_reminder_claim(db, visita["id"])
            continue
        if mensaje and mensaje.get("reintentable"):
            release_reminder_claim(db, visita["id"])
        if mensaje:
            enviados.append(mensaje)
    if enviados:
        logger.info("Recordatorios de WhatsApp para el %s: %d", manana, len(enviados))
    return enviados


def ejecutar_recordatorios() -> None:
    """Una pasada del recordatorio automático (la llama el ciclo de main.py)."""
    if not settings.whatsapp_recordatorios_activos or not twilio_configurado():
        return
    from app.database import engine

    with engine.connect() as db:
        enviar_recordatorios(db)
