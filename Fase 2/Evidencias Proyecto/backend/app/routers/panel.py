from datetime import date, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.database import get_db
from app.dependencies import require_web_user
from app.repositories import _is_within_business_hours
from app.schemas import (
    ClientCreate, ClientSummary, ClientUpdate, CurrentUser, OperatorSummary,
    PanelStats, PanelVisitResponse, PanelVisitUpdate, VisitCreate, VisitStatus,
)
from app.zona_horaria import hoy_chile

router = APIRouter(tags=["panel web"])


def _client_write(db: Connection, statement, params: dict, *, returning_id=False):
    """La restricción UNIQUE del teléfono también protege escrituras concurrentes."""
    try:
        result = db.execute(statement, params)
        row_id = result.scalar_one() if returning_id else None
        db.commit()
        return row_id
    except IntegrityError as exc:
        db.rollback()
        if getattr(exc.orig, "sqlstate", None) == "23505":
            raise HTTPException(status_code=409, detail="Ya existe un cliente con ese teléfono") from exc
        raise


def _validate_operator_slot(db: Connection, empresa_id: UUID, operador_id, fecha_hora, visit_id=None):
    if not _is_within_business_hours(fecha_hora):
        names = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
        days = ", ".join(names[int(day)] for day in settings.killbichos_operating_days.split(",") if day.strip().isdigit() and 0 <= int(day) <= 6)
        raise HTTPException(status_code=422, detail=f"Horario de atención: {days}, desde {settings.killbichos_open_time} y antes de las {settings.killbichos_close_time} (hora de Chile). Elige otro horario.")
    if operador_id is None:
        return
    # Serializa asignaciones del panel al mismo operador dentro de la transacción.
    operator = db.execute(text("""
        SELECT id FROM operadores
        WHERE id = :id AND empresa_id = :empresa_id AND activo = TRUE FOR UPDATE
    """), {"id": str(operador_id), "empresa_id": str(empresa_id)}).first()
    if operator is None:
        raise HTTPException(status_code=400, detail="Selecciona un operador activo de tu empresa")
    conflict = db.execute(text("""
        SELECT id FROM visitas
        WHERE empresa_id = :empresa_id AND operador_id = :operador_id
          AND estado IN ('agendada', 'reagendada', 'en_curso')
          AND fecha_hora > CAST(:fecha_hora AS timestamptz) - INTERVAL '1 hour'
          AND fecha_hora < CAST(:fecha_hora AS timestamptz) + INTERVAL '1 hour'
          AND (CAST(:visit_id AS uuid) IS NULL OR id <> CAST(:visit_id AS uuid))
        LIMIT 1
    """), {"empresa_id": str(empresa_id), "operador_id": str(operador_id),
          "fecha_hora": fecha_hora, "visit_id": str(visit_id) if visit_id else None}).first()
    if conflict is not None:
        raise HTTPException(status_code=409, detail="El operador tiene otra visita a menos de una hora. Elige otro horario u operador.")


def _client(row: dict) -> ClientSummary:
    return ClientSummary(id=row["id"], nombre=row["nombre"], telefono_whatsapp=row["telefono_whatsapp"],
                         direccion=row["direccion"] or "", lat=row["lat"], lng=row["lng"])


def _visit(row: dict) -> PanelVisitResponse:
    client = ClientSummary(
        id=row["cliente_id"], nombre=row["cliente_nombre"],
        telefono_whatsapp=row["telefono_whatsapp"], direccion=row["direccion"] or "",
        lat=row["lat"], lng=row["lng"],
    )
    return PanelVisitResponse(
        id=row["id"], cliente=client, operador_id=row["operador_id"], fecha_hora=row["fecha_hora"],
        estado=row["estado"], origen_agendamiento=row["origen_agendamiento"], notas=row["notas"],
        operador=OperatorSummary(id=row["operador_id"], nombre=row["operador_nombre"], email=row["operador_email"])
        if row["operador_id"] else None,
    )


def _client_row(db: Connection, client_id: UUID, empresa_id: UUID, *, lock=False) -> dict:
    row = db.execute(text("""
        SELECT id, nombre, telefono_whatsapp, direccion,
               ST_Y(ubicacion::geometry) AS lat, ST_X(ubicacion::geometry) AS lng
        FROM clientes WHERE id = :id AND empresa_id = :empresa_id
    """ + (" FOR UPDATE" if lock else "")), {"id": str(client_id), "empresa_id": str(empresa_id)}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return dict(row)


@router.get("/panel/operadores", response_model=list[OperatorSummary])
def operators(user: CurrentUser = Depends(require_web_user), db: Connection = Depends(get_db)):
    rows = db.execute(text("""
        SELECT id, nombre, email FROM operadores
        WHERE empresa_id = :empresa_id AND activo = TRUE ORDER BY nombre
    """), {"empresa_id": str(user.empresa_id)}).mappings().all()
    return [OperatorSummary(**dict(row)) for row in rows]


@router.get("/panel/stats", response_model=PanelStats)
def stats(user: CurrentUser = Depends(require_web_user), db: Connection = Depends(get_db)):
    row = db.execute(text("""
        SELECT
          (SELECT count(*) FROM clientes WHERE empresa_id = :empresa_id) AS clientes,
          (SELECT count(*) FROM visitas WHERE empresa_id = :empresa_id
             AND (fecha_hora AT TIME ZONE 'America/Santiago')::date = :hoy) AS visitas_hoy,
          (SELECT count(*) FROM visitas WHERE empresa_id = :empresa_id
             AND estado IN ('agendada', 'reagendada')) AS pendientes
    """), {"empresa_id": str(user.empresa_id), "hoy": hoy_chile()}).mappings().one()
    return PanelStats(**dict(row))


@router.get("/clientes", response_model=list[ClientSummary])
def list_clients(user: CurrentUser = Depends(require_web_user), db: Connection = Depends(get_db)):
    rows = db.execute(text("""
        SELECT id, nombre, telefono_whatsapp, direccion,
               ST_Y(ubicacion::geometry) AS lat, ST_X(ubicacion::geometry) AS lng
        FROM clientes WHERE empresa_id = :empresa_id ORDER BY nombre
    """), {"empresa_id": str(user.empresa_id)}).mappings().all()
    return [_client(dict(row)) for row in rows]


@router.post("/clientes", response_model=ClientSummary, status_code=status.HTTP_201_CREATED)
def create_client(payload: ClientCreate, user: CurrentUser = Depends(require_web_user), db: Connection = Depends(get_db)):
    row = _client_write(db, text("""
        INSERT INTO clientes (empresa_id, nombre, telefono_whatsapp, direccion, ubicacion)
        VALUES (:empresa_id, :nombre, :telefono, :direccion,
                ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography)
        RETURNING id
    """), {"empresa_id": str(user.empresa_id), "nombre": payload.nombre.strip(), "telefono": payload.telefono_whatsapp.strip(),
          "direccion": payload.direccion.strip(), "lat": payload.lat, "lng": payload.lng}, returning_id=True)
    return _client(_client_row(db, row, user.empresa_id))


@router.patch("/clientes/{client_id}", response_model=ClientSummary)
def update_client(client_id: UUID, payload: ClientUpdate, user: CurrentUser = Depends(require_web_user), db: Connection = Depends(get_db)):
    _client_row(db, client_id, user.empresa_id)
    values = payload.model_dump(exclude_unset=True)
    if not values:
        return _client(_client_row(db, client_id, user.empresa_id))
    sets = []
    params = {"id": str(client_id), "empresa_id": str(user.empresa_id)}
    for key in ("nombre", "telefono_whatsapp", "direccion"):
        if key in values:
            sets.append(f"{key} = :{key}")
            params[key] = values[key].strip() if isinstance(values[key], str) else values[key]
    if "lat" in values or "lng" in values:
        current = _client_row(db, client_id, user.empresa_id)
        params.update({"lat": values.get("lat", current["lat"]), "lng": values.get("lng", current["lng"])})
        if (params["lat"] is None) != (params["lng"] is None):
            raise HTTPException(status_code=422, detail="Completa ambas coordenadas o deja ambas vacías")
        sets.append("ubicacion = ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography")
    if sets:
        _client_write(db, text(f"UPDATE clientes SET {', '.join(sets)} WHERE id = :id AND empresa_id = :empresa_id"), params)
    return _client(_client_row(db, client_id, user.empresa_id))


@router.delete("/clientes/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(client_id: UUID, user: CurrentUser = Depends(require_web_user), db: Connection = Depends(get_db)):
    # Impide que una visita concurrente aparezca entre la comprobación y el DELETE.
    _client_row(db, client_id, user.empresa_id, lock=True)
    has_visits = db.execute(
        text("SELECT EXISTS (SELECT 1 FROM visitas WHERE cliente_id = :id AND empresa_id = :empresa_id)"),
        {"id": str(client_id), "empresa_id": str(user.empresa_id)},
    ).scalar_one()
    if has_visits:
        raise HTTPException(status_code=409, detail="No se puede eliminar un cliente con visitas asociadas")
    try:
        db.execute(text("DELETE FROM clientes WHERE id = :id AND empresa_id = :empresa_id"), {"id": str(client_id), "empresa_id": str(user.empresa_id)})
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="No se puede eliminar un cliente con registros asociados") from exc


_VISITS = """
    SELECT v.id, v.cliente_id, v.operador_id, v.fecha_hora, v.estado, v.origen_agendamiento, v.notas,
           c.nombre AS cliente_nombre, c.telefono_whatsapp, c.direccion,
           ST_Y(c.ubicacion::geometry) AS lat, ST_X(c.ubicacion::geometry) AS lng,
           o.nombre AS operador_nombre, o.email AS operador_email
    FROM visitas v JOIN clientes c ON c.id = v.cliente_id
    LEFT JOIN operadores o ON o.id = v.operador_id
    WHERE v.empresa_id = :empresa_id
"""


@router.get("/panel/visitas", response_model=list[PanelVisitResponse])
def list_panel_visits(fecha: date | None = None, operador_id: UUID | None = None,
                      user: CurrentUser = Depends(require_web_user), db: Connection = Depends(get_db)):
    filters = []
    params = {"empresa_id": str(user.empresa_id)}
    if fecha:
        # La fecha elegida en el panel es un día de Chile: se compara con el
        # día de cada visita convertido a la hora de Chile, no a UTC.
        filters.append("(v.fecha_hora AT TIME ZONE 'America/Santiago')::date = :fecha")
        params["fecha"] = fecha
    if operador_id:
        filters.append("v.operador_id = :operador_id")
        params["operador_id"] = str(operador_id)
    suffix = (" AND " + " AND ".join(filters)) if filters else ""
    rows = db.execute(text(_VISITS + suffix + " ORDER BY v.fecha_hora"), params).mappings().all()
    return [_visit(dict(row)) for row in rows]


@router.post("/panel/visitas", response_model=PanelVisitResponse, status_code=status.HTTP_201_CREATED)
def create_visit(payload: VisitCreate, user: CurrentUser = Depends(require_web_user), db: Connection = Depends(get_db)):
    _client_row(db, payload.cliente_id, user.empresa_id)
    _validate_operator_slot(db, user.empresa_id, payload.operador_id, payload.fecha_hora)
    row_id = db.execute(text("""
        INSERT INTO visitas (empresa_id, cliente_id, operador_id, fecha_hora, estado, origen_agendamiento, notas)
        VALUES (:empresa_id, :cliente_id, :operador_id, :fecha_hora, 'agendada', 'manual', :notas) RETURNING id
    """), {"empresa_id": str(user.empresa_id), "cliente_id": str(payload.cliente_id), "operador_id": str(payload.operador_id) if payload.operador_id else None,
          "fecha_hora": payload.fecha_hora, "notas": payload.notas}).scalar_one()
    db.commit()
    return _visit(_visit_row(db, row_id, user.empresa_id))


def _visit_row(db: Connection, visit_id: UUID, empresa_id: UUID, *, lock=False) -> dict:
    sql = _VISITS + " AND v.id = :id" + (" FOR UPDATE OF v" if lock else "")
    row = db.execute(text(sql), {"empresa_id": str(empresa_id), "id": str(visit_id)}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Visita no encontrada")
    return dict(row)


@router.patch("/panel/visitas/{visit_id}", response_model=PanelVisitResponse)
def update_panel_visit(visit_id: UUID, payload: PanelVisitUpdate, user: CurrentUser = Depends(require_web_user), db: Connection = Depends(get_db)):
    current = _visit_row(db, visit_id, user.empresa_id, lock=True)
    values = payload.model_dump(exclude_unset=True)
    new_date = values.get("fecha_hora", current["fecha_hora"])
    moved = new_date.astimezone(timezone.utc) != current["fecha_hora"].astimezone(timezone.utc)
    operator_id = values.get("operador_id", current["operador_id"])
    reassigned = str(operator_id) != str(current["operador_id"])
    if values.get("estado") == VisitStatus.reagendada and current["estado"] != "reagendada" and not moved:
        raise HTTPException(status_code=422, detail="Para reagendar debes indicar una nueva fecha y hora")
    if current["estado"] in {"completada", "cancelada"} and (moved or reassigned):
        raise HTTPException(status_code=409, detail="Reactiva la visita antes de cambiar su fecha u operador")
    if moved and values.get("estado", current["estado"]) not in {"cancelada", "completada"}:
        values["estado"] = VisitStatus.reagendada
    target_state = values.get("estado", current["estado"])
    if target_state in {"agendada", "reagendada", "en_curso"} and (moved or reassigned or "estado" in values):
        _validate_operator_slot(db, user.empresa_id, operator_id, new_date, visit_id)
    if "operador_id" in values:
        values["operador_id"] = str(operator_id) if operator_id else None
    if values:
        sets = ", ".join(f"{key} = :{key}" for key in values)
        db.execute(text(f"UPDATE visitas SET {sets} WHERE id = :id AND empresa_id = :empresa_id"), {**values, "id": str(visit_id), "empresa_id": str(user.empresa_id)})
        db.commit()
    return _visit(_visit_row(db, visit_id, user.empresa_id))


@router.delete("/panel/visitas/{visit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_visit(visit_id: UUID, user: CurrentUser = Depends(require_web_user), db: Connection = Depends(get_db)):
    _visit_row(db, visit_id, user.empresa_id)
    # Las visitas forman parte del historial y pueden tener un croquis asociado.
    # Se cancelan en lugar de borrarse para conservar la trazabilidad.
    db.execute(
        text("UPDATE visitas SET estado = 'cancelada' WHERE id = :id AND empresa_id = :empresa_id"),
        {"id": str(visit_id), "empresa_id": str(user.empresa_id)},
    )
    db.commit()
