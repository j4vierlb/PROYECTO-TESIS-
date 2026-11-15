# =============================================================================
# repositories/whatsapp.py — Clientes, conversaciones, mensajes y recordatorios de WhatsApp
# (ver repositories/__init__.py para el patrón general de las consultas)
# =============================================================================

import logging
from datetime import date, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.repositories._comun import _ACTIVE_VISIT_STATES


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# WhatsApp + agente IA
# ---------------------------------------------------------------------------
# Funciones que usa routers/whatsapp.py: identificar al cliente por su
# número, guardar la conversación y agendar la visita que pide la IA.
def normalize_phone(phone: str) -> str:
    """Twilio entrega el número como 'whatsapp:+569...'; se guarda sin prefijo."""
    return phone.removeprefix("whatsapp:").strip()


def fetch_or_create_whatsapp_client(
    db: Connection, phone: str, empresa_id: UUID, profile_name: str | None = None
) -> dict[str, Any]:
    """Busca al cliente por su número de WhatsApp. Si es nuevo, lo crea sin
    dirección ni ubicación (la IA le pedirá la dirección antes de agendar).
    profile_name es el nombre de perfil de WhatsApp que envía Twilio."""
    phone = normalize_phone(phone)
    select_sql = text("""
        SELECT id, empresa_id, nombre, telefono_whatsapp, direccion
        FROM clientes
        WHERE telefono_whatsapp = :phone
    """)
    row = db.execute(select_sql, {"phone": phone}).mappings().first()
    if row:
        return dict(row)

    # ON CONFLICT: si llegan dos mensajes simultáneos del mismo número nuevo,
    # el segundo no falla por el UNIQUE de telefono_whatsapp; solo relee.
    db.execute(
        text("""
            INSERT INTO clientes (empresa_id, nombre, telefono_whatsapp)
            VALUES (:empresa_id, :nombre, :phone)
            ON CONFLICT (telefono_whatsapp) DO NOTHING
        """),
        {
            "empresa_id": str(empresa_id),
            "nombre": (profile_name or "").strip()[:150] or f"Cliente WhatsApp {phone}",
            "phone": phone,
        },
    )
    db.commit()
    return dict(db.execute(select_sql, {"phone": phone}).mappings().one())


def count_client_visits(db: Connection, cliente_id: UUID) -> int:
    """Cuántas visitas tiene el cliente en total (cualquier estado). Si es 0,
    es su primer agendamiento y hay que pedirle su nombre real."""
    return db.execute(
        text("SELECT COUNT(*) FROM visitas WHERE cliente_id = :cliente_id"),
        {"cliente_id": str(cliente_id)},
    ).scalar_one()


def update_whatsapp_client_name(db: Connection, cliente_id: UUID, nombre: str) -> None:
    """Guarda el nombre real que el cliente entregó por WhatsApp (reemplaza al
    nombre de perfil o a 'Cliente WhatsApp +569...')."""
    db.execute(
        text("UPDATE clientes SET nombre = :nombre WHERE id = :cliente_id"),
        {"nombre": nombre[:150], "cliente_id": str(cliente_id)},
    )
    db.commit()


def update_whatsapp_client_address(db: Connection, cliente_id: UUID, address: str) -> None:
    """Guarda la dirección que el cliente entregó por WhatsApp y borra la
    ubicación anterior, que ya no corresponde. La nueva la calcula
    geocoding.geocodificar_cliente en segundo plano."""
    db.execute(
        text("UPDATE clientes SET direccion = :direccion, ubicacion = NULL WHERE id = :cliente_id"),
        {"direccion": address, "cliente_id": str(cliente_id)},
    )
    db.commit()


def fetch_active_whatsapp_conversation(db: Connection, cliente_id: UUID) -> dict[str, Any]:
    """Devuelve la conversación activa del cliente, o crea una nueva.
    operador_activo_at = última vez que el operador la tomó o escribió."""
    row = db.execute(
        text("""
            SELECT cw.id, cw.cliente_id, cw.estado, cw.atendida_por_humano,
                   GREATEST(cw.atendida_por_humano_desde,
                            (SELECT max(m.created_at) FROM mensajes_whatsapp m
                              WHERE m.conversacion_id = cw.id AND m.emisor = 'operador')) AS operador_activo_at
            FROM conversaciones_whatsapp cw
            WHERE cw.cliente_id = :cliente_id AND cw.estado = 'activa'
            ORDER BY cw.created_at DESC
            LIMIT 1
        """),
        {"cliente_id": str(cliente_id)},
    ).mappings().first()
    if row:
        return dict(row)
    row = db.execute(
        text("""
            INSERT INTO conversaciones_whatsapp (cliente_id, estado)
            VALUES (:cliente_id, 'activa')
            RETURNING id, cliente_id, estado, atendida_por_humano, NULL::timestamptz AS operador_activo_at
        """),
        {"cliente_id": str(cliente_id)},
    ).mappings().one()
    db.commit()
    return dict(row)


def whatsapp_message_exists(db: Connection, message_sid: str) -> bool:
    """True si ya se procesó un mensaje con ese MessageSid (reintento de Twilio)."""
    if not message_sid:
        return False
    row = db.execute(
        text("SELECT 1 FROM mensajes_whatsapp WHERE message_sid = :message_sid LIMIT 1"),
        {"message_sid": message_sid},
    ).first()
    return row is not None


def insert_whatsapp_message(
    db: Connection,
    conversation_id: UUID,
    emitter: str,
    content: str,
    intent: str | None = None,
    message_sid: str | None = None,
    delivery_status: str | None = None,
    delivery_error: str | None = None,
) -> dict[str, Any] | None:
    """Guarda un mensaje. Devuelve None si el MessageSid ya existía: el
    UNIQUE de la columna + ON CONFLICT DO NOTHING cubren el caso en que dos
    reintentos llegan al mismo tiempo y ambos pasaron whatsapp_message_exists.
    delivery_status solo se usa en los mensajes enviados al cliente."""
    row = db.execute(
        text("""
            INSERT INTO mensajes_whatsapp
                (conversacion_id, emisor, contenido, intencion_detectada, message_sid,
                 estado_entrega, error_entrega)
            VALUES (:conversation_id, :emisor, :content, :intent, :message_sid,
                    :estado_entrega, :error_entrega)
            ON CONFLICT DO NOTHING
            RETURNING id, conversacion_id, emisor, contenido, intencion_detectada, message_sid,
                      estado_entrega, error_entrega, created_at
        """),
        {
            "conversation_id": str(conversation_id),
            "emisor": emitter,
            "content": content,
            "intent": intent,
            "message_sid": message_sid,
            "estado_entrega": delivery_status,
            "error_entrega": delivery_error,
        },
    ).mappings().first()
    db.commit()
    return dict(row) if row else None


def fetch_whatsapp_history(db: Connection, conversation_id: UUID, limit: int = 20) -> list[dict[str, Any]]:
    """Últimos `limit` mensajes de la conversación, del más antiguo al más nuevo."""
    rows = db.execute(
        text("""
            SELECT emisor, contenido, intencion_detectada, created_at
            FROM mensajes_whatsapp
            WHERE conversacion_id = :conversation_id
            ORDER BY created_at DESC
            LIMIT :limit
        """),
        {"conversation_id": str(conversation_id), "limit": limit},
    ).mappings().all()
    return list(reversed([dict(r) for r in rows]))


# Estados de entrega que informa Twilio, de menor a mayor avance. Twilio
# puede avisar en desorden (ej: "delivered" antes que "sent"), así que solo
# se guarda un estado si no retrocede respecto del que ya estaba.
DELIVERY_RANK = {
    "no_enviado": 0, "accepted": 1, "queued": 1, "sending": 2, "sent": 3,
    "failed": 4, "undelivered": 4, "delivered": 5, "read": 6,
}
_DELIVERY_RANK_SQL = "CASE estado_entrega " + " ".join(
    f"WHEN '{estado}' THEN {rank}" for estado, rank in DELIVERY_RANK.items()
) + " ELSE -1 END"


def update_whatsapp_delivery(
    db: Connection,
    status: str,
    *,
    message_id: UUID | None = None,
    message_sid: str | None = None,
    error: str | None = None,
) -> bool:
    """Guarda el estado de entrega de un mensaje enviado al cliente. Se busca
    por su id (mensajes recién enviados y respuestas TwiML) o, si no viene,
    por su MessageSid. Anota también el MessageSid si el mensaje aún no lo
    tenía. Devuelve True si se actualizó algo."""
    if message_id is None and not message_sid:
        return False
    rank = DELIVERY_RANK.get(status)
    if rank is None:
        logger.info("Estado de entrega desconocido de Twilio ignorado: %s", status)
        return False
    where = "id = :id" if message_id is not None else "message_sid = :message_sid"
    updated = db.execute(
        text(f"""
            UPDATE mensajes_whatsapp
            SET estado_entrega = :estado,
                error_entrega = COALESCE(:error, error_entrega),
                message_sid = COALESCE(message_sid, :message_sid)
            WHERE {where} AND emisor <> 'cliente' AND {_DELIVERY_RANK_SQL} <= :rank
        """),
        {
            "id": str(message_id) if message_id else None,
            "message_sid": message_sid or None,
            "estado": status,
            "error": error,
            "rank": rank,
        },
    ).rowcount
    db.commit()
    return bool(updated)


def fetch_whatsapp_client(db: Connection, cliente_id: UUID) -> dict[str, Any] | None:
    row = db.execute(
        text("SELECT id, empresa_id, nombre, telefono_whatsapp FROM clientes WHERE id = :id"),
        {"id": str(cliente_id)},
    ).mappings().first()
    return dict(row) if row else None


def client_wrote_since(db: Connection, cliente_id: UUID, since: datetime) -> bool:
    """True si el cliente escribió por WhatsApp después de `since`. WhatsApp
    solo deja enviar texto libre hasta 24 h después del último mensaje del
    cliente; pasado eso, solo plantillas aprobadas."""
    return db.execute(
        text("""
            SELECT EXISTS (
                SELECT 1
                FROM mensajes_whatsapp m
                JOIN conversaciones_whatsapp cw ON cw.id = m.conversacion_id
                WHERE cw.cliente_id = :cliente_id AND m.emisor = 'cliente' AND m.created_at >= :since
            )
        """),
        {"cliente_id": str(cliente_id), "since": since},
    ).scalar_one()


# Parte común de la bandeja: la conversación, su cliente y cuándo escribió
# el cliente por última vez (para saber si sigue abierta la ventana de 24 h).
_CONVERSATION_SELECT = """
    SELECT cw.id, cw.estado, cw.atendida_por_humano,
           c.id AS cliente_id, c.nombre AS cliente_nombre, c.telefono_whatsapp,
           (SELECT max(m.created_at) FROM mensajes_whatsapp m
             WHERE m.conversacion_id = cw.id AND m.emisor = 'cliente') AS ultimo_cliente_at
    FROM conversaciones_whatsapp cw
    JOIN clientes c ON c.id = cw.cliente_id
"""


def list_whatsapp_conversations(db: Connection, empresa_id: UUID) -> list[dict[str, Any]]:
    """Conversaciones de la empresa para la bandeja del panel, con su último
    mensaje. La del mensaje más reciente va primero."""
    rows = db.execute(
        text(f"""
            SELECT conv.*, ultimo.emisor AS ultimo_emisor, ultimo.contenido AS ultimo_contenido,
                   ultimo.created_at AS ultimo_at
            FROM ({_CONVERSATION_SELECT} WHERE c.empresa_id = :empresa_id) conv
            JOIN LATERAL (
                SELECT emisor, contenido, created_at
                FROM mensajes_whatsapp m
                WHERE m.conversacion_id = conv.id
                ORDER BY created_at DESC
                LIMIT 1
            ) ultimo ON TRUE
            ORDER BY ultimo.created_at DESC
        """),
        {"empresa_id": str(empresa_id)},
    ).mappings().all()
    return [dict(row) for row in rows]


def fetch_whatsapp_conversation(db: Connection, conversation_id: UUID, empresa_id: UUID) -> dict[str, Any]:
    """Una conversación de la empresa con los datos de su cliente. Corta con
    404 si no existe o es de otra empresa."""
    row = db.execute(
        text(_CONVERSATION_SELECT + " WHERE cw.id = :id AND c.empresa_id = :empresa_id"),
        {"id": str(conversation_id), "empresa_id": str(empresa_id)},
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversación no encontrada")
    return dict(row)


def fetch_conversation_messages(db: Connection, conversation_id: UUID, limit: int = 200) -> list[dict[str, Any]]:
    """Últimos `limit` mensajes con su estado de entrega, del más antiguo al más nuevo."""
    rows = db.execute(
        text("""
            SELECT id, emisor, contenido, intencion_detectada, estado_entrega, error_entrega, created_at
            FROM mensajes_whatsapp
            WHERE conversacion_id = :conversation_id
            ORDER BY created_at DESC
            LIMIT :limit
        """),
        {"conversation_id": str(conversation_id), "limit": limit},
    ).mappings().all()
    return list(reversed([dict(r) for r in rows]))


def set_conversation_human(db: Connection, conversation_id: UUID, value: bool) -> None:
    """TRUE = la atiende un operador y la IA deja de responder; FALSE = vuelve a la IA."""
    db.execute(
        text("""
            UPDATE conversaciones_whatsapp
            SET atendida_por_humano = :value,
                atendida_por_humano_desde = CASE WHEN :value THEN now() END
            WHERE id = :id
        """),
        {"id": str(conversation_id), "value": value},
    )
    db.commit()


def claim_visits_for_reminder(db: Connection, dia: date, empresa_id: UUID | None = None) -> list[dict[str, Any]]:
    """Marca como recordadas las visitas activas de `dia` (día de Chile) que
    aún no tienen recordatorio, y las devuelve. Se marcan ANTES de enviar y
    en un solo UPDATE: si dos procesos corren a la vez, cada visita la toma
    uno solo y nadie recibe dos recordatorios. Si el envío falla por algo
    pasajero, release_reminder_claim la deja libre para la próxima pasada."""
    rows = db.execute(
        text(f"""
            UPDATE visitas
            SET recordatorio_enviado_at = now()
            WHERE recordatorio_enviado_at IS NULL
              AND estado IN {_ACTIVE_VISIT_STATES}
              AND fecha_hora > now()
              AND (fecha_hora AT TIME ZONE 'America/Santiago')::date = :dia
              AND (CAST(:empresa_id AS uuid) IS NULL OR empresa_id = CAST(:empresa_id AS uuid))
            RETURNING id, cliente_id, fecha_hora
        """),
        {"dia": dia, "empresa_id": str(empresa_id) if empresa_id else None},
    ).mappings().all()
    db.commit()
    return [dict(row) for row in rows]


def release_reminder_claim(db: Connection, visit_id: UUID) -> None:
    """Quita la marca de recordatorio para que el ciclo lo vuelva a intentar."""
    db.execute(text("UPDATE visitas SET recordatorio_enviado_at = NULL WHERE id = :id"), {"id": str(visit_id)})
    db.commit()
