# =============================================================================
# routers/whatsapp.py — Webhook de WhatsApp (Twilio) + agente IA
# -----------------------------------------------------------------------------
#   POST /webhooks/whatsapp   Twilio llama aquí cada vez que un cliente
#                             escribe al número de WhatsApp de la empresa
#
# Flujo de un mensaje:
#   1. Se valida la firma de Twilio (para que nadie más pueda llamar aquí).
#   2. Se ignora si su MessageSid ya se procesó (Twilio reintenta si tardamos).
#   3. Se busca o crea el cliente y su conversación, y se guarda el mensaje.
#   4. La IA (ai/agent.py) decide si solo responde o si hay que agendar.
#   5. Si hay que agendar: se valida la fecha, se guarda la dirección y se
#      crea la visita con operador asignado; si el horario no está libre,
#      se le ofrece al cliente el siguiente horario disponible.
#   6. Se responde en formato TwiML (XML), que Twilio reenvía por WhatsApp.
#
# Pase lo que pase, el cliente siempre recibe una respuesta: si falla la IA o
# la base de datos, se le avisa que un operador lo contactará y el error
# queda en el log con logging.exception.
# =============================================================================

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.engine import Connection
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse

from app.ai.agent import MAX_WHATSAPP_CHARS, generate_agent_decision
from app.config import settings
from app.database import get_db
from app.repositories import (
    HorarioNoDisponible,
    create_whatsapp_visit,
    fetch_active_whatsapp_conversation,
    fetch_or_create_whatsapp_client,
    fetch_whatsapp_history,
    insert_whatsapp_message,
    update_whatsapp_client_address,
    whatsapp_message_exists,
)

logger = logging.getLogger(__name__)
SANTIAGO = ZoneInfo("America/Santiago")
UTC = timezone.utc
MAX_DAYS_AHEAD = 60  # no se agendan visitas a más de 60 días

FALLBACK_REPLY = (
    "Gracias por escribirnos 😊 Tuvimos un inconveniente procesando tu mensaje. "
    "Un operador te contactará pronto."
)

router = APIRouter(prefix="/webhooks", tags=["whatsapp"])


async def read_twilio_form(request: Request) -> dict[str, str]:
    """Lee el formulario que envía Twilio. Es async porque leer el cuerpo del
    request lo exige; así el endpoint puede ser un `def` normal (síncrono),
    que FastAPI ejecuta en un hilo aparte sin bloquear el servidor mientras
    espera a la base de datos o a OpenAI."""
    form = await request.form()
    return {str(key): str(value) for key, value in form.items()}


def _twiml(message: str | None = None) -> Response:
    """Respuesta en el XML que entiende Twilio. Sin mensaje = no responder."""
    response = MessagingResponse()
    if message:
        response.message(message[:MAX_WHATSAPP_CHARS])
    return Response(content=str(response), media_type="application/xml")


def _validate_twilio(request: Request, form: dict[str, str]) -> None:
    """Comprueba la firma X-Twilio-Signature. Se calcula sobre la URL pública
    exacta configurada en Twilio (TWILIO_WEBHOOK_URL), no sobre la URL local
    que ve el servidor detrás de ngrok o de un proxy."""
    if not settings.twilio_validate_signature:
        return
    if not settings.twilio_auth_token or not settings.twilio_webhook_url:
        logger.error("TWILIO_AUTH_TOKEN o TWILIO_WEBHOOK_URL no están configurados")
        raise HTTPException(status_code=500, detail="Webhook de Twilio no configurado")
    signature = request.headers.get("X-Twilio-Signature", "")
    validator = RequestValidator(settings.twilio_auth_token)
    if not validator.validate(settings.twilio_webhook_url, form, signature):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Firma de Twilio inválida")


def _parse_appointment_datetime(value: str) -> datetime:
    """Valida la fecha que propuso la IA y la devuelve en UTC.
    Lanza ValueError si no es ISO 8601 con zona horaria, si ya pasó o si está
    a más de MAX_DAYS_AHEAD días."""
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"appointment_datetime no es ISO 8601 válido: {value!r}") from exc

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"appointment_datetime no incluye zona horaria: {value!r}")

    parsed_utc = parsed.astimezone(UTC)
    now_utc = datetime.now(UTC)
    if parsed_utc <= now_utc:
        raise ValueError(f"La fecha de la visita ya pasó: {value!r}")
    if parsed_utc > now_utc + timedelta(days=MAX_DAYS_AHEAD):
        raise ValueError(f"La fecha de la visita supera {MAX_DAYS_AHEAD} días: {value!r}")
    return parsed_utc


def _format_local(fecha_hora: datetime) -> str:
    return fecha_hora.astimezone(SANTIAGO).strftime("%d/%m/%Y a las %H:%M")


def _schedule_visit(db: Connection, client: dict, decision: dict, message_sid: str) -> str:
    """Intenta agendar la visita que pidió la IA y devuelve el texto que se
    le responde al cliente (confirmación, pedido de datos o alternativa)."""
    new_address = decision["client_address"]
    address = new_address or client.get("direccion")
    if not address:
        return "Claro 😊 Antes de agendar, necesito la dirección donde se realizará la visita."
    if new_address and new_address != (client.get("direccion") or "").strip():
        update_whatsapp_client_address(db, client["id"], new_address)

    if not decision["appointment_datetime"]:
        return "Claro 😊 Para agendar necesito que me indiques una fecha y una hora concreta."

    try:
        appointment_utc = _parse_appointment_datetime(decision["appointment_datetime"])
    except ValueError as exc:
        logger.warning("Fecha inválida de la IA (MessageSid=%s): %s", message_sid, exc)
        return (
            f"No pude agendar en esa fecha. Puedo agendar visitas desde hoy y hasta "
            f"{MAX_DAYS_AHEAD} días más. ¿Qué día y hora te acomoda?"
        )

    try:
        visit = create_whatsapp_visit(
            db,
            UUID(settings.killbichos_empresa_id),
            client["id"],
            appointment_utc,
            decision["notes"],
        )
    except HorarioNoDisponible as exc:
        db.rollback()
        logger.info("Horario no disponible (MessageSid=%s): %s", message_sid, exc)
        if exc.sugerencia:
            return (
                f"Ese horario no está disponible 😕 ¿Te acomoda el {_format_local(exc.sugerencia)} "
                "(hora de Chile)? Si prefieres, indícame otro día y hora."
            )
        return (
            "No encontré horarios disponibles en los próximos días. "
            "Un operador te contactará pronto para coordinar la visita."
        )

    action_text = "quedó agendada" if visit["created"] else "ya estaba agendada"
    return (
        f"Perfecto 😊 Tu visita {action_text} para el "
        f"{_format_local(visit['fecha_hora'])} (hora de Chile)."
    )


@router.post("/whatsapp")
def whatsapp_webhook(
    request: Request,
    form: dict[str, str] = Depends(read_twilio_form),
    db: Connection = Depends(get_db),
) -> Response:
    """Recibe un mensaje de WhatsApp desde Twilio y responde con TwiML."""
    _validate_twilio(request, form)

    from_number = form.get("From", "")
    body = form.get("Body", "").strip()
    message_sid = form.get("MessageSid", "").strip()

    if not from_number or not body:
        return _twiml()

    try:
        if whatsapp_message_exists(db, message_sid):
            logger.info("Mensaje duplicado de Twilio ignorado: %s", message_sid)
            return _twiml()

        client = fetch_or_create_whatsapp_client(
            db, from_number, UUID(settings.killbichos_empresa_id), form.get("ProfileName")
        )
        conversation = fetch_active_whatsapp_conversation(db, client["id"])
        inserted = insert_whatsapp_message(
            db, conversation["id"], "cliente", body, message_sid=message_sid or None
        )
        if inserted is None:
            # Otro reintento con el mismo MessageSid ganó la carrera.
            logger.info("Mensaje duplicado de Twilio ignorado: %s", message_sid)
            return _twiml()

        history = fetch_whatsapp_history(db, conversation["id"], limit=20)
    except Exception:
        db.rollback()
        logger.exception("Error guardando el mensaje de WhatsApp (MessageSid=%s)", message_sid)
        return _twiml(FALLBACK_REPLY)

    try:
        decision = generate_agent_decision(history, client["nombre"], client.get("direccion"))
    except Exception:
        logger.exception("Falló el agente de IA (MessageSid=%s)", message_sid)
        reply = "Gracias por escribirnos 😊 Un operador te contactará pronto para ayudarte."
        intent = None
    else:
        intent = decision["intent"]
        reply = decision["reply"]
        if decision["action"] == "create_appointment":
            try:
                reply = _schedule_visit(db, client, decision, message_sid)
            except Exception:
                db.rollback()
                logger.exception("Error creando la visita (MessageSid=%s)", message_sid)
                reply = (
                    "Entendí que quieres agendar una visita, pero no pude registrarla ahora. "
                    "Un operador te contactará pronto."
                )

    try:
        insert_whatsapp_message(db, conversation["id"], "agente_ia", reply[:MAX_WHATSAPP_CHARS], intent)
    except Exception:
        # La respuesta se envía igual aunque no quede guardada en el historial.
        db.rollback()
        logger.exception("No se pudo guardar la respuesta del agente (MessageSid=%s)", message_sid)
    return _twiml(reply)
