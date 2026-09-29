# =============================================================================
# repositories.py — Todas las consultas a la base de datos
# -----------------------------------------------------------------------------
# Aquí vive todo el SQL del backend. Los routers (la capa de endpoints) nunca
# escriben SQL directamente: llaman a estas funciones. Así, si cambia una
# tabla, solo hay que tocar este archivo.
#
# Seguridad: los valores siempre van como parámetros con nombre (:id, :email)
# y nunca pegados dentro del texto del SQL. SQLAlchemy los envía por separado
# a PostgreSQL, lo que evita ataques de "inyección SQL".
#
# Patrón que se repite en casi todas las funciones:
#   db.execute(text("SQL..."), {"parametro": valor})  -> ejecuta la consulta
#   .mappings()                                        -> filas como diccionarios
#   .first() / .all()                                  -> una fila / todas
#   db.commit()                                        -> confirma un cambio (UPDATE)
# =============================================================================

import logging
from datetime import datetime, time, timedelta, timezone
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Consultas relacionadas a visitas
# ---------------------------------------------------------------------------
# ST_Y/ST_X extraen latitud/longitud de la columna GEOGRAPHY(Point) de
# PostGIS, para poder devolverlas como lat/lng sueltos (no GeoJSON), tal
# como acordamos en el formato de la API.
#
# Es la parte común de las consultas de visitas: une cada visita con los
# datos de su cliente (JOIN). Cada función le agrega su propio WHERE.
_VISIT_SELECT = """
    SELECT v.id, v.operador_id, v.fecha_hora, v.estado, v.origen_agendamiento, v.notas,
           c.id AS cliente_id, c.nombre AS cliente_nombre, c.telefono_whatsapp, c.direccion,
           ST_Y(c.ubicacion::geometry) AS lat, ST_X(c.ubicacion::geometry) AS lng
    FROM visitas v
    JOIN clientes c ON c.id = v.cliente_id
"""


def fetch_visit(db: Connection, visit_id: UUID) -> dict[str, Any]:
    """Busca una visita por su id. Si no existe, corta el request con un 404."""
    row = db.execute(text(_VISIT_SELECT + " WHERE v.id = :id"), {"id": str(visit_id)}).mappings().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visita no encontrada")
    return dict(row)


def fetch_visits_for_today(db: Connection, operador_id: UUID) -> list[dict[str, Any]]:
    """Visitas del operador cuya fecha cae en el día actual, comparando
    siempre en UTC (mismo huso horario en que se guarda fecha_hora), para
    que el resultado no dependa de la zona horaria del servidor."""
    # (fecha AT TIME ZONE 'UTC')::date = "el día de esa fecha, en UTC".
    # Se compara con el día de hoy, también en UTC. ORDER BY la hora.
    rows = db.execute(
        text(
            _VISIT_SELECT
            + """
            WHERE v.operador_id = :operador_id
              AND (v.fecha_hora AT TIME ZONE 'UTC')::date = (now() AT TIME ZONE 'UTC')::date
            ORDER BY v.fecha_hora
            """
        ),
        {"operador_id": str(operador_id)},
    ).mappings().all()
    return [dict(row) for row in rows]


def fetch_visit_history(db: Connection, operador_id: UUID, limit: int, offset: int) -> list[dict[str, Any]]:
    """Visitas completadas del operador, de la más reciente a la más antigua,
    con la cantidad de trampas que siguen instaladas en su croquis."""
    # Igual que _VISIT_SELECT, más una subconsulta que cuenta las trampas del
    # croquis de cada visita que no fueron retiradas.
    # ORDER BY ... DESC = de la más nueva a la más antigua.
    # LIMIT/OFFSET = paginación: "dame `limit` filas saltándote las primeras
    # `offset`". Ej: limit=20 offset=20 es la segunda página.
    rows = db.execute(
        text(
            """
            SELECT v.id, v.operador_id, v.fecha_hora, v.estado, v.origen_agendamiento, v.notas,
                   c.id AS cliente_id, c.nombre AS cliente_nombre, c.telefono_whatsapp, c.direccion,
                   ST_Y(c.ubicacion::geometry) AS lat, ST_X(c.ubicacion::geometry) AS lng,
                   (
                       SELECT count(*)
                       FROM croquis cr
                       JOIN dispositivos_trampa d ON d.croquis_id = cr.id
                       WHERE cr.visita_id = v.id AND d.estado <> 'retirado'
                   ) AS dispositivos_instalados
            FROM visitas v
            JOIN clientes c ON c.id = v.cliente_id
            WHERE v.operador_id = :operador_id
              AND v.estado = 'completada'
            ORDER BY v.fecha_hora DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        {"operador_id": str(operador_id), "limit": limit, "offset": offset},
    ).mappings().all()
    return [dict(row) for row in rows]


def update_visit_fields(db: Connection, visit_id: UUID, changes: dict[str, Any]) -> None:
    """UPDATE parcial: arma el SET solo con los campos presentes en `changes`
    (viene de VisitUpdate.model_dump(exclude_unset=True)), así un PATCH que
    no manda 'notas' no la pisa con NULL."""
    # Si el PATCH llegó vacío ({}), no hay nada que actualizar.
    if not changes:
        return
    # Ej: {"estado": ..., "notas": ...} -> "estado = :estado, notas = :notas".
    # Los nombres de columna vienen de VisitUpdate (solo estado/notas posibles),
    # nunca del usuario, así que armar este texto es seguro; los valores
    # siguen yendo como parámetros.
    set_clause = ", ".join(f"{key} = :{key}" for key in changes)
    db.execute(text(f"UPDATE visitas SET {set_clause} WHERE id = :id"), {**changes, "id": str(visit_id)})
    db.commit()


# ---------------------------------------------------------------------------
# Consultas relacionadas a croquis y dispositivos
# ---------------------------------------------------------------------------
# Parte común de las consultas de trampas: convierte la ubicación PostGIS
# en lat/lng, igual que en las visitas.
_DEVICE_SELECT = """
    SELECT id, croquis_id, codigo, tipo, sugerido_por_ia, confirmado, estado,
           ST_Y(ubicacion::geometry) AS lat, ST_X(ubicacion::geometry) AS lng
    FROM dispositivos_trampa
"""


def fetch_croquis_for_visit(db: Connection, visit_id: UUID) -> dict[str, Any]:
    """Busca el croquis asociado a una visita. Si no tiene, responde 404."""
    row = db.execute(
        text(
            """
            SELECT id, visita_id, cliente_id, version, imagen_satelital_url,
                   sugerido_por_ia, validado_por_operador
            FROM croquis
            WHERE visita_id = :visita_id
            """
        ),
        {"visita_id": str(visit_id)},
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Croquis no encontrado")
    return dict(row)


def fetch_devices_for_croquis(db: Connection, croquis_id: UUID) -> list[dict[str, Any]]:
    """Todas las trampas de un croquis, ordenadas por su código (T-01, T-02...)."""
    rows = db.execute(
        text(_DEVICE_SELECT + " WHERE croquis_id = :croquis_id ORDER BY codigo"),
        {"croquis_id": str(croquis_id)},
    ).mappings().all()
    return [dict(row) for row in rows]


def fetch_device(db: Connection, device_id: UUID) -> dict[str, Any]:
    """Busca una trampa por su id. Si no existe, responde 404."""
    row = db.execute(text(_DEVICE_SELECT + " WHERE id = :id"), {"id": str(device_id)}).mappings().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispositivo no encontrado")
    return dict(row)


def confirm_device(db: Connection, device_id: UUID) -> None:
    """Marca la trampa como confirmada por el operador en terreno."""
    db.execute(text("UPDATE dispositivos_trampa SET confirmado = TRUE WHERE id = :id"), {"id": str(device_id)})
    db.commit()


def move_device(db: Connection, device_id: UUID, lat: float, lng: float) -> None:
    """Cambia la ubicación de una trampa."""
    # ST_MakePoint crea un punto (ojo: primero longitud, después latitud).
    # ST_SetSRID(..., 4326) indica que son coordenadas GPS normales (WGS 84)
    # y ::geography lo convierte al tipo de la columna.
    db.execute(
        text(
            """
            UPDATE dispositivos_trampa
            SET ubicacion = ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography
            WHERE id = :id
            """
        ),
        {"id": str(device_id), "lat": lat, "lng": lng},
    )
    db.commit()


def remove_device(db: Connection, device_id: UUID) -> None:
    """No borra el registro: lo marca 'retirado' (soft delete), para
    conservar el historial del dispositivo."""
    db.execute(text("UPDATE dispositivos_trampa SET estado = 'retirado' WHERE id = :id"), {"id": str(device_id)})
    db.commit()


# ---------------------------------------------------------------------------
# Consultas relacionadas a autenticación
# ---------------------------------------------------------------------------
# Hay dos tablas de personas: `operadores` (técnicos de la app móvil) y
# `usuarios` (admin/coordinador del panel web). Todas filtran por
# activo = TRUE, así una cuenta desactivada no puede entrar ni seguir usando
# un token que ya tenía.

def fetch_operator_by_email(db: Connection, email: str) -> dict[str, Any] | None:
    """Busca un operador activo por email (para el login). None si no existe."""
    row = db.execute(
        text("SELECT id, nombre, empresa_id, password_hash FROM operadores WHERE email = :email AND activo = TRUE"),
        {"email": email},
    ).mappings().first()
    return dict(row) if row else None


def fetch_web_user_by_email(db: Connection, email: str) -> dict[str, Any] | None:
    """Busca un usuario del panel web activo por email (para el login)."""
    row = db.execute(
        text(
            "SELECT id, nombre, empresa_id, rol, password_hash FROM usuarios "
            "WHERE email = :email AND activo = TRUE"
        ),
        {"email": email},
    ).mappings().first()
    return dict(row) if row else None


def fetch_operator_by_id(db: Connection, user_id: UUID) -> dict[str, Any] | None:
    """Busca un operador activo por id (para validar el token en cada request)."""
    row = db.execute(
        text("SELECT id, nombre, empresa_id FROM operadores WHERE id = :id AND activo = TRUE"),
        {"id": str(user_id)},
    ).mappings().first()
    return dict(row) if row else None


def fetch_web_user_by_id(db: Connection, user_id: UUID) -> dict[str, Any] | None:
    """Busca un usuario del panel web activo por id (para validar su token)."""
    row = db.execute(
        text("SELECT id, nombre, empresa_id FROM usuarios WHERE id = :id AND activo = TRUE"),
        {"id": str(user_id)},
    ).mappings().first()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# WhatsApp + agente IA
# ---------------------------------------------------------------------------
# Funciones que usa routers/whatsapp.py: identificar al cliente por su
# número, guardar la conversación y agendar la visita que pide la IA.

SANTIAGO = ZoneInfo("America/Santiago")
UTC = timezone.utc
# Dos visitas del mismo operador deben estar separadas por al menos 1 hora.
VISIT_MARGIN = timedelta(hours=1)
# Hasta cuántos días hacia adelante se busca un horario alternativo.
SUGGESTION_SEARCH_DAYS = 7
# Solo estos estados "ocupan" al operador (una visita cancelada no).
_ACTIVE_VISIT_STATES = "('agendada', 'reagendada')"


class HorarioNoDisponible(Exception):
    """El horario pedido no se puede agendar. Si se encontró uno libre
    cercano, viene en `sugerencia` (UTC) para ofrecérselo al cliente."""

    def __init__(self, motivo: str, sugerencia: datetime | None = None):
        super().__init__(motivo)
        self.sugerencia = sugerencia


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


def update_whatsapp_client_address(db: Connection, cliente_id: UUID, address: str) -> None:
    """Guarda la dirección que el cliente entregó por WhatsApp. La ubicación
    (lat/lng) queda vacía hasta que alguien la geolocalice."""
    db.execute(
        text("UPDATE clientes SET direccion = :direccion WHERE id = :cliente_id"),
        {"direccion": address, "cliente_id": str(cliente_id)},
    )
    db.commit()


def fetch_active_whatsapp_conversation(db: Connection, cliente_id: UUID) -> dict[str, Any]:
    """Devuelve la conversación activa del cliente, o crea una nueva."""
    row = db.execute(
        text("""
            SELECT id, cliente_id, estado
            FROM conversaciones_whatsapp
            WHERE cliente_id = :cliente_id AND estado = 'activa'
            ORDER BY created_at DESC
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
            RETURNING id, cliente_id, estado
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
) -> dict[str, Any] | None:
    """Guarda un mensaje. Devuelve None si el MessageSid ya existía: el
    UNIQUE de la columna + ON CONFLICT DO NOTHING cubren el caso en que dos
    reintentos llegan al mismo tiempo y ambos pasaron whatsapp_message_exists."""
    row = db.execute(
        text("""
            INSERT INTO mensajes_whatsapp
                (conversacion_id, emisor, contenido, intencion_detectada, message_sid)
            VALUES (:conversation_id, :emisor, :content, :intent, :message_sid)
            ON CONFLICT DO NOTHING
            RETURNING id, conversacion_id, emisor, contenido, intencion_detectada, message_sid, created_at
        """),
        {
            "conversation_id": str(conversation_id),
            "emisor": emitter,
            "content": content,
            "intent": intent,
            "message_sid": message_sid,
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


def _is_within_business_hours(fecha_hora: datetime) -> bool:
    """Revisa día y hora (en hora de Chile) contra el horario del .env.
    La hora de cierre no se incluye: una visita no puede empezar al cerrar."""
    local_dt = fecha_hora.astimezone(SANTIAGO)
    operating_days = {
        int(day.strip())
        for day in settings.killbichos_operating_days.split(",")
        if day.strip().isdigit()
    }
    open_time = time.fromisoformat(settings.killbichos_open_time)
    close_time = time.fromisoformat(settings.killbichos_close_time)
    return local_dt.weekday() in operating_days and open_time <= local_dt.time() < close_time


def _configured_operator_id(db: Connection, empresa_id: UUID) -> str | None:
    """KILLBICHOS_OPERADOR_ID del .env, solo si es un operador activo de la
    empresa. Si está vacío o no es válido, se asigna automáticamente."""
    configured = settings.killbichos_operador_id.strip()
    if not configured:
        return None
    try:
        UUID(configured)
    except ValueError:
        logger.warning("KILLBICHOS_OPERADOR_ID=%s no es un UUID válido", configured)
        return None
    row = db.execute(
        text("SELECT 1 FROM operadores WHERE id = :id AND empresa_id = :empresa_id AND activo = TRUE"),
        {"id": configured, "empresa_id": str(empresa_id)},
    ).first()
    if row is None:
        logger.warning("KILLBICHOS_OPERADOR_ID=%s no corresponde a un operador activo de la empresa", configured)
        return None
    return configured


def _find_available_operator(
    db: Connection, empresa_id: UUID, fecha_hora: datetime, fixed_operator_id: str | None
) -> UUID | None:
    """Operador libre para esa fecha y hora: sin otra visita a menos de
    VISIT_MARGIN. Si hay un operador fijo (fixed_operator_id), solo se
    considera ese; si no, entre los libres se elige el que tiene menos
    visitas ese día."""
    row = db.execute(
        text(f"""
            SELECT o.id
            FROM operadores o
            LEFT JOIN visitas v
              ON v.operador_id = o.id
             AND v.estado IN {_ACTIVE_VISIT_STATES}
             AND (v.fecha_hora AT TIME ZONE 'America/Santiago')::date = :fecha_local
            WHERE o.empresa_id = :empresa_id
              AND o.activo = TRUE
              AND (CAST(:operador_id AS uuid) IS NULL OR o.id = CAST(:operador_id AS uuid))
              AND NOT EXISTS (
                  SELECT 1
                  FROM visitas c
                  WHERE c.operador_id = o.id
                    AND c.estado IN {_ACTIVE_VISIT_STATES}
                    AND c.fecha_hora > CAST(:fecha_hora AS timestamptz) - CAST(:margen AS interval)
                    AND c.fecha_hora < CAST(:fecha_hora AS timestamptz) + CAST(:margen AS interval)
              )
            GROUP BY o.id
            ORDER BY COUNT(v.id), o.id
            LIMIT 1
        """),
        {
            "empresa_id": str(empresa_id),
            "operador_id": fixed_operator_id,
            "fecha_hora": fecha_hora,
            "fecha_local": fecha_hora.astimezone(SANTIAGO).date(),
            "margen": VISIT_MARGIN,
        },
    ).first()
    return row[0] if row else None


def _find_next_available_slot(
    db: Connection, empresa_id: UUID, desde: datetime, fixed_operator_id: str | None
) -> datetime | None:
    """Primer horario en punto, posterior a `desde`, que esté dentro del
    horario de atención y tenga un operador libre. Busca hasta
    SUGGESTION_SEARCH_DAYS días; devuelve None si no encuentra (en UTC)."""
    start = max(desde, datetime.now(UTC)).astimezone(SANTIAGO)
    candidate = start.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    limit = start + timedelta(days=SUGGESTION_SEARCH_DAYS)
    while candidate <= limit:
        if _is_within_business_hours(candidate) and _find_available_operator(
            db, empresa_id, candidate, fixed_operator_id
        ):
            return candidate.astimezone(UTC)
        candidate += timedelta(hours=1)
    return None


def create_whatsapp_visit(
    db: Connection,
    empresa_id: UUID,
    cliente_id: UUID,
    fecha_hora: datetime,
    notas: str | None = None,
) -> dict[str, Any]:
    """Crea la visita pedida por WhatsApp, ya asignada a un operador (la app
    móvil solo muestra visitas con operador). Lanza HorarioNoDisponible, con
    un horario alternativo si lo hay, cuando la hora está fuera de horario o
    ningún operador está libre. `created` indica si la visita es nueva o si
    ya existía (por ejemplo, porque el cliente repitió la confirmación)."""
    existing = db.execute(
        text(f"""
            SELECT id, fecha_hora, estado, operador_id
            FROM visitas
            WHERE cliente_id = :cliente_id
              AND fecha_hora = :fecha_hora
              AND estado IN {_ACTIVE_VISIT_STATES}
            LIMIT 1
        """),
        {"cliente_id": str(cliente_id), "fecha_hora": fecha_hora},
    ).mappings().first()
    if existing:
        return {**dict(existing), "created": False}

    fixed_operator_id = _configured_operator_id(db, empresa_id)
    if not _is_within_business_hours(fecha_hora):
        raise HorarioNoDisponible(
            "La hora está fuera del horario de atención",
            _find_next_available_slot(db, empresa_id, fecha_hora, fixed_operator_id),
        )

    operador_id = _find_available_operator(db, empresa_id, fecha_hora, fixed_operator_id)
    if operador_id is None:
        raise HorarioNoDisponible(
            "Ningún operador está libre en ese horario",
            _find_next_available_slot(db, empresa_id, fecha_hora, fixed_operator_id),
        )

    row = db.execute(
        text("""
            INSERT INTO visitas
                (empresa_id, cliente_id, operador_id, fecha_hora, estado, origen_agendamiento, notas)
            VALUES
                (:empresa_id, :cliente_id, :operador_id, :fecha_hora,
                 'agendada', 'whatsapp_ia', :notas)
            RETURNING id, fecha_hora, estado, origen_agendamiento, notas, operador_id
        """),
        {
            "empresa_id": str(empresa_id),
            "cliente_id": str(cliente_id),
            "operador_id": str(operador_id),
            "fecha_hora": fecha_hora,
            "notas": notas,
        },
    ).mappings().one()
    db.commit()
    return {**dict(row), "created": True}
