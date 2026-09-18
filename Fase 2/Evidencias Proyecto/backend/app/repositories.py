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
_VISIT_SELECT = """
    SELECT v.id, v.operador_id, v.fecha_hora, v.estado, v.origen_agendamiento, v.notas,
           c.id AS cliente_id, c.nombre AS cliente_nombre, c.telefono_whatsapp, c.direccion,
           ST_Y(c.ubicacion::geometry) AS lat, ST_X(c.ubicacion::geometry) AS lng
    FROM visitas v
    JOIN clientes c ON c.id = v.cliente_id
"""


def fetch_visit(db: Connection, visit_id: UUID) -> dict[str, Any]:
    row = db.execute(text(_VISIT_SELECT + " WHERE v.id = :id"), {"id": str(visit_id)}).mappings().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visita no encontrada")
    return dict(row)


def fetch_visits_for_today(db: Connection, operador_id: UUID) -> list[dict[str, Any]]:
    """Visitas del operador cuya fecha cae en el día actual, comparando
    siempre en UTC (mismo huso horario en que se guarda fecha_hora), para
    que el resultado no dependa de la zona horaria del servidor."""
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


def update_visit_fields(db: Connection, visit_id: UUID, changes: dict[str, Any]) -> None:
    """UPDATE parcial: arma el SET solo con los campos presentes en `changes`
    (viene de VisitUpdate.model_dump(exclude_unset=True)), así un PATCH que
    no manda 'notas' no la pisa con NULL."""
    if not changes:
        return
    set_clause = ", ".join(f"{key} = :{key}" for key in changes)
    db.execute(text(f"UPDATE visitas SET {set_clause} WHERE id = :id"), {**changes, "id": str(visit_id)})
    db.commit()


# ---------------------------------------------------------------------------
# Consultas relacionadas a croquis y dispositivos
# ---------------------------------------------------------------------------
_DEVICE_SELECT = """
    SELECT id, croquis_id, codigo, tipo, sugerido_por_ia, confirmado, estado,
           ST_Y(ubicacion::geometry) AS lat, ST_X(ubicacion::geometry) AS lng
    FROM dispositivos_trampa
"""


def fetch_croquis_for_visit(db: Connection, visit_id: UUID) -> dict[str, Any]:
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
    rows = db.execute(
        text(_DEVICE_SELECT + " WHERE croquis_id = :croquis_id ORDER BY codigo"),
        {"croquis_id": str(croquis_id)},
    ).mappings().all()
    return [dict(row) for row in rows]


def fetch_device(db: Connection, device_id: UUID) -> dict[str, Any]:
    row = db.execute(text(_DEVICE_SELECT + " WHERE id = :id"), {"id": str(device_id)}).mappings().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispositivo no encontrado")
    return dict(row)


def confirm_device(db: Connection, device_id: UUID) -> None:
    db.execute(text("UPDATE dispositivos_trampa SET confirmado = TRUE WHERE id = :id"), {"id": str(device_id)})
    db.commit()


def move_device(db: Connection, device_id: UUID, lat: float, lng: float) -> None:
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
def fetch_operator_by_email(db: Connection, email: str) -> dict[str, Any] | None:
    row = db.execute(
        text("SELECT id, nombre, empresa_id, password_hash FROM operadores WHERE email = :email AND activo = TRUE"),
        {"email": email},
    ).mappings().first()
    return dict(row) if row else None


def fetch_web_user_by_email(db: Connection, email: str) -> dict[str, Any] | None:
    row = db.execute(
        text(
            "SELECT id, nombre, empresa_id, rol, password_hash FROM usuarios "
            "WHERE email = :email AND activo = TRUE"
        ),
        {"email": email},
    ).mappings().first()
    return dict(row) if row else None


def fetch_operator_by_id(db: Connection, user_id: UUID) -> dict[str, Any] | None:
    row = db.execute(
        text("SELECT id, nombre, empresa_id FROM operadores WHERE id = :id AND activo = TRUE"),
        {"id": str(user_id)},
    ).mappings().first()
    return dict(row) if row else None


def fetch_web_user_by_id(db: Connection, user_id: UUID) -> dict[str, Any] | None:
    row = db.execute(
        text("SELECT id, nombre, empresa_id FROM usuarios WHERE id = :id AND activo = TRUE"),
        {"id": str(user_id)},
    ).mappings().first()
    return dict(row) if row else None
