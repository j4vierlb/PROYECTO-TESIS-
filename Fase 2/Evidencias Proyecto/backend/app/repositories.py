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

from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.engine import Connection

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
