# =============================================================================
# routers/conversaciones.py — Bandeja de WhatsApp del panel web
# -----------------------------------------------------------------------------
#   GET   /panel/conversaciones                  conversaciones de la empresa
#   GET   /panel/conversaciones/{id}             historial con estado de entrega
#   PATCH /panel/conversaciones/{id}             tomar la conversación / devolverla a la IA
#   POST  /panel/conversaciones/{id}/mensajes    el operador le escribe al cliente
#   POST  /panel/whatsapp/recordatorios          enviar ahora los recordatorios de mañana
#
# Cuando un operador escribe, la conversación queda "atendida por humano" y
# la IA deja de responder en ella hasta que alguien la devuelva desde el panel.
# =============================================================================

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.engine import Connection

from app.database import get_db
from app.dependencies import require_web_user
from app.repositories import (
    fetch_conversation_messages,
    fetch_whatsapp_conversation,
    list_whatsapp_conversations,
    set_conversation_human,
)
from app.schemas import (
    ClientSummary, ConversationDetail, ConversationSummary, ConversationUpdate, CurrentUser,
    OperatorMessageCreate, RemindersResult, WhatsAppMessage,
)
from app.whatsapp_saliente import VENTANA_SESION, enviar_recordatorios, enviar_whatsapp, twilio_configurado

router = APIRouter(tags=["bandeja whatsapp"])


def _window_open(last_client_message: datetime | None) -> bool:
    return last_client_message is not None and last_client_message >= datetime.now(timezone.utc) - VENTANA_SESION


def _summary(row: dict) -> dict:
    return dict(
        id=row["id"],
        cliente=ClientSummary(id=row["cliente_id"], nombre=row["cliente_nombre"],
                              telefono_whatsapp=row["telefono_whatsapp"]),
        atendida_por_humano=row["atendida_por_humano"],
        ventana_abierta=_window_open(row["ultimo_cliente_at"]),
        ultimo_mensaje=row.get("ultimo_contenido"),
        ultimo_emisor=row.get("ultimo_emisor"),
        ultimo_at=row.get("ultimo_at"),
    )


def _detail(db: Connection, row: dict) -> ConversationDetail:
    messages = [WhatsAppMessage(**m) for m in fetch_conversation_messages(db, row["id"])]
    last = messages[-1] if messages else None
    return ConversationDetail(
        **{**_summary(row), "ultimo_mensaje": last.contenido if last else None,
           "ultimo_emisor": last.emisor if last else None, "ultimo_at": last.created_at if last else None},
        mensajes=messages,
    )


def _require_twilio() -> None:
    if not twilio_configurado():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="Twilio no está configurado en el servidor")


@router.get("/panel/conversaciones", response_model=list[ConversationSummary])
def list_conversations(user: CurrentUser = Depends(require_web_user), db: Connection = Depends(get_db)):
    return [ConversationSummary(**_summary(row)) for row in list_whatsapp_conversations(db, user.empresa_id)]


@router.get("/panel/conversaciones/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: UUID, user: CurrentUser = Depends(require_web_user),
                     db: Connection = Depends(get_db)):
    return _detail(db, fetch_whatsapp_conversation(db, conversation_id, user.empresa_id))


@router.patch("/panel/conversaciones/{conversation_id}", response_model=ConversationDetail)
def update_conversation(conversation_id: UUID, payload: ConversationUpdate,
                        user: CurrentUser = Depends(require_web_user), db: Connection = Depends(get_db)):
    fetch_whatsapp_conversation(db, conversation_id, user.empresa_id)
    set_conversation_human(db, conversation_id, payload.atendida_por_humano)
    return _detail(db, fetch_whatsapp_conversation(db, conversation_id, user.empresa_id))


@router.post("/panel/conversaciones/{conversation_id}/mensajes", response_model=WhatsAppMessage,
             status_code=status.HTTP_201_CREATED)
def send_operator_message(conversation_id: UUID, payload: OperatorMessageCreate,
                          user: CurrentUser = Depends(require_web_user), db: Connection = Depends(get_db)):
    """El operador le escribe al cliente. Solo dentro de la ventana de 24 h:
    fuera de ella WhatsApp no acepta texto libre (solo plantillas)."""
    conversation = fetch_whatsapp_conversation(db, conversation_id, user.empresa_id)
    _require_twilio()
    if not _window_open(conversation["ultimo_cliente_at"]):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El cliente no escribe hace más de 24 h: WhatsApp no permite enviarle texto libre",
        )
    # El operador toma la conversación: desde ahora la IA no responde en ella.
    if not conversation["atendida_por_humano"]:
        set_conversation_human(db, conversation_id, True)
    message = enviar_whatsapp(db, conversation["cliente_id"], payload.contenido.strip(),
                              emisor="operador", intencion="operador")
    return WhatsAppMessage(**message)


@router.post("/panel/whatsapp/recordatorios", response_model=RemindersResult)
def send_reminders_now(user: CurrentUser = Depends(require_web_user), db: Connection = Depends(get_db)):
    """Envía ya, sin esperar la hora configurada, los recordatorios de las
    visitas de mañana de la empresa que aún no lo recibieron."""
    _require_twilio()
    sent = enviar_recordatorios(db, empresa_id=user.empresa_id, respetar_hora=False)
    failed = sum(1 for m in sent if m["estado_entrega"] in {"failed", "no_enviado"})
    return RemindersResult(enviados=len(sent) - failed, no_enviados=failed)
