# =============================================================================
# repositories/agendamiento.py — Agendamiento de visitas pedidas por la IA (horarios y técnicos)
# (ver repositories/__init__.py para el patrón general de las consultas)
# =============================================================================

import logging
from datetime import datetime, time, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.config import settings
from app.repositories._comun import SANTIAGO, UTC, VISIT_MARGIN, SUGGESTION_SEARCH_DAYS, _ACTIVE_VISIT_STATES


logger = logging.getLogger(__name__)


# Excepción propia: se lanza cuando no se puede agendar. Lleva, si existe, un
# horario alternativo para ofrecérselo al cliente.
class HorarioNoDisponible(Exception):
    """El horario pedido no se puede agendar. Si se encontró uno libre
    cercano, viene en `sugerencia` (UTC) para ofrecérselo al cliente."""

    def __init__(self, motivo: str, sugerencia: datetime | None = None):
        super().__init__(motivo)
        self.sugerencia = sugerencia

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
    # weekday(): lunes = 0 ... domingo = 6. La hora de cierre NO se incluye
    # (es 'menor que', no 'menor o igual').
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


# La consulta SQL de abajo: toma los técnicos activos de la empresa, cuenta sus
# visitas del día (LEFT JOIN + COUNT), descarta a los que ya tienen otra visita
# a menos de VISIT_MARGIN (NOT EXISTS) y ordena por menos visitas primero
# (ORDER BY COUNT). Así el trabajo se reparte parejo entre los técnicos.
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
    # Prueba hora en punto por hora (desde la siguiente) hasta encontrar una dentro
    # del horario de atención y con un técnico libre.
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
        # Idempotencia: si el cliente repite la confirmación no se crea otra visita;
        # se devuelve la que ya existía, con created=False.
        return {**dict(existing), "created": False}

    # Dos filtros antes de insertar: 1) dentro del horario de atención y 2) que haya
    # un técnico libre. Si falla alguno se lanza HorarioNoDisponible con una alternativa.
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
