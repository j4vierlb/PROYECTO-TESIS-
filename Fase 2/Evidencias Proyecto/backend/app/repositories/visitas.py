# =============================================================================
# repositories/visitas.py — Consultas de visitas
# (ver repositories/__init__.py para el patrón general de las consultas)
# =============================================================================

from datetime import date, timedelta
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.repositories._comun import _ACTIVE_VISIT_STATES


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
    SELECT v.id, v.empresa_id, v.operador_id, v.fecha_hora, v.estado, v.origen_agendamiento, v.notas,
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


def fetch_visits_for_today(db: Connection, operador_id: UUID, dia: date) -> list[dict[str, Any]]:
    """Visitas del operador que caen en `dia`, entendido como día de Chile
    (lo calcula zona_horaria.hoy_chile). fecha_hora se guarda en UTC, así
    que antes de comparar se convierte a la hora de Chile: si no, desde las
    21:00 la agenda mostraría las visitas del día siguiente."""
    # (fecha AT TIME ZONE 'America/Santiago')::date = "el día de esa fecha
    # en Chile". Se compara con el día pedido. ORDER BY la hora.
    rows = db.execute(
        text(
            _VISIT_SELECT
            + """
            WHERE v.operador_id = :operador_id
              AND (v.fecha_hora AT TIME ZONE 'America/Santiago')::date = :dia
            ORDER BY v.fecha_hora
            """
        ),
        {"operador_id": str(operador_id), "dia": dia},
    ).mappings().all()
    return [dict(row) for row in rows]


def fetch_upcoming_visits(db: Connection, operador_id: UUID, hoy: date, dias: int) -> list[dict[str, Any]]:
    """Visitas pendientes del operador desde mañana hasta dentro de `dias` días
    (días de Chile, igual que la agenda de hoy). Solo las que siguen por hacerse
    ('agendada' o 'reagendada'): las canceladas y las ya hechas no aparecen."""
    rows = db.execute(
        text(
            _VISIT_SELECT
            + f"""
            WHERE v.operador_id = :operador_id
              AND v.estado IN {_ACTIVE_VISIT_STATES}
              AND (v.fecha_hora AT TIME ZONE 'America/Santiago')::date > :hoy
              AND (v.fecha_hora AT TIME ZONE 'America/Santiago')::date <= :hasta
            ORDER BY v.fecha_hora
            """
        ),
        {"operador_id": str(operador_id), "hoy": hoy, "hasta": hoy + timedelta(days=dias)},
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
