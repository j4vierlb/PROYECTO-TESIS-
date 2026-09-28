from datetime import date, datetime, time, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.database import get_db
from app.dependencies import require_web_user
from app.schemas import (
    ClientCreate, ClientSummary, ClientUpdate, CurrentUser, OperatorSummary,
    PanelStats, PanelVisitResponse, VisitCreate, VisitStatus, VisitUpdate,
)

router = APIRouter(tags=["panel web"])


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


def _client_row(db: Connection, client_id: UUID, empresa_id: UUID) -> dict:
    row = db.execute(text("""
        SELECT id, nombre, telefono_whatsapp, direccion,
               ST_Y(ubicacion::geometry) AS lat, ST_X(ubicacion::geometry) AS lng
        FROM clientes WHERE id = :id AND empresa_id = :empresa_id
    """), {"id": str(client_id), "empresa_id": str(empresa_id)}).mappings().first()
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
             AND (fecha_hora AT TIME ZONE 'UTC')::date = (now() AT TIME ZONE 'UTC')::date) AS visitas_hoy,
          (SELECT count(*) FROM visitas WHERE empresa_id = :empresa_id
             AND estado IN ('agendada', 'reagendada')) AS pendientes
    """), {"empresa_id": str(user.empresa_id)}).mappings().one()
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
    row = db.execute(text("""
        INSERT INTO clientes (empresa_id, nombre, telefono_whatsapp, direccion, ubicacion)
        VALUES (:empresa_id, :nombre, :telefono, :direccion,
                ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography)
        RETURNING id
    """), {"empresa_id": str(user.empresa_id), "nombre": payload.nombre.strip(), "telefono": payload.telefono_whatsapp.strip(),
          "direccion": payload.direccion.strip(), "lat": payload.lat, "lng": payload.lng}).scalar_one()
    db.commit()
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
        sets.append("ubicacion = ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography")
    if sets:
        db.execute(text(f"UPDATE clientes SET {', '.join(sets)} WHERE id = :id AND empresa_id = :empresa_id"), params)
        db.commit()
    return _client(_client_row(db, client_id, user.empresa_id))


@router.delete("/clientes/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(client_id: UUID, user: CurrentUser = Depends(require_web_user), db: Connection = Depends(get_db)):
    _client_row(db, client_id, user.empresa_id)
    try:
        db.execute(text("DELETE FROM clientes WHERE id = :id AND empresa_id = :empresa_id"), {"id": str(client_id), "empresa_id": str(user.empresa_id)})
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="No se puede eliminar un cliente con visitas asociadas") from exc


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
        filters.append("(v.fecha_hora AT TIME ZONE 'UTC')::date = :fecha")
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
    if payload.operador_id:
        exists = db.execute(text("SELECT 1 FROM operadores WHERE id = :id AND empresa_id = :empresa_id AND activo = TRUE"),
                            {"id": str(payload.operador_id), "empresa_id": str(user.empresa_id)}).first()
        if not exists:
            raise HTTPException(status_code=400, detail="Operador no válido")
    row_id = db.execute(text("""
        INSERT INTO visitas (empresa_id, cliente_id, operador_id, fecha_hora, estado, origen_agendamiento, notas)
        VALUES (:empresa_id, :cliente_id, :operador_id, :fecha_hora, 'agendada', 'manual', :notas) RETURNING id
    """), {"empresa_id": str(user.empresa_id), "cliente_id": str(payload.cliente_id), "operador_id": str(payload.operador_id) if payload.operador_id else None,
          "fecha_hora": payload.fecha_hora, "notas": payload.notas}).scalar_one()
    db.commit()
    return _visit(_visit_row(db, row_id, user.empresa_id))


def _visit_row(db: Connection, visit_id: UUID, empresa_id: UUID) -> dict:
    row = db.execute(text(_VISITS + " AND v.id = :id"), {"empresa_id": str(empresa_id), "id": str(visit_id)}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Visita no encontrada")
    return dict(row)


@router.patch("/panel/visitas/{visit_id}", response_model=PanelVisitResponse)
def update_panel_visit(visit_id: UUID, payload: VisitUpdate, user: CurrentUser = Depends(require_web_user), db: Connection = Depends(get_db)):
    _visit_row(db, visit_id, user.empresa_id)
    values = payload.model_dump(exclude_unset=True, mode="json")
    if values:
        sets = ", ".join(f"{key} = :{key}" for key in values)
        db.execute(text(f"UPDATE visitas SET {sets} WHERE id = :id AND empresa_id = :empresa_id"), {**values, "id": str(visit_id), "empresa_id": str(user.empresa_id)})
        db.commit()
    return _visit(_visit_row(db, visit_id, user.empresa_id))


@router.delete("/panel/visitas/{visit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_visit(visit_id: UUID, user: CurrentUser = Depends(require_web_user), db: Connection = Depends(get_db)):
    _visit_row(db, visit_id, user.empresa_id)
    db.execute(text("DELETE FROM visitas WHERE id = :id AND empresa_id = :empresa_id"), {"id": str(visit_id), "empresa_id": str(user.empresa_id)})
    db.commit()
