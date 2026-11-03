from datetime import date, timezone
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.database import get_db
from app.dependencies import require_admin, require_web_user
from app.geocoding import geocodificar
from app.repositories import _is_within_business_hours
from app.schemas import (
    ClientCreate, ClientSummary, ClientUpdate, CurrentUser, OperatorCreate, OperatorDetail,
    OperatorSummary, OperatorUpdate, PanelStats, PanelVisitResponse, PanelVisitUpdate,
    VisitCreate, VisitStatus,
)
from app.security import hash_password
from app.whatsapp_saliente import (
    AVISO_AGENDADA, AVISO_CANCELADA, AVISO_REAGENDADA, avisar_visita_en_segundo_plano,
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


@router.get("/panel/operadores", response_model=list[OperatorDetail])
def operators(incluir_inactivos: bool = False, user: CurrentUser = Depends(require_web_user),
              db: Connection = Depends(get_db)):
    # Sin el parámetro se mantiene la lista de activos que usan los
    # desplegables del panel. Los inactivos solo los ve el administrador.
    if incluir_inactivos and user.rol != "admin":
        raise HTTPException(status_code=403, detail="Se requiere un administrador")
    rows = db.execute(text("""
        SELECT id, nombre, email, telefono, activo FROM operadores
        WHERE empresa_id = :empresa_id AND (activo = TRUE OR :todos) ORDER BY nombre
    """), {"empresa_id": str(user.empresa_id), "todos": incluir_inactivos}).mappings().all()
    return [OperatorDetail(**dict(row)) for row in rows]


def _operator_row(db: Connection, operator_id: UUID, empresa_id: UUID, *, lock=False) -> dict:
    row = db.execute(text("""
        SELECT id, nombre, email, telefono, activo FROM operadores
        WHERE id = :id AND empresa_id = :empresa_id
    """ + (" FOR UPDATE" if lock else "")), {"id": str(operator_id), "empresa_id": str(empresa_id)}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Técnico no encontrado")
    return dict(row)


@router.post("/panel/operadores", response_model=OperatorDetail, status_code=status.HTTP_201_CREATED)
def create_operator(payload: OperatorCreate, user: CurrentUser = Depends(require_admin), db: Connection = Depends(get_db)):
    # El login busca primero en operadores y después en usuarios: si el correo
    # estuviera en ambas tablas, la cuenta del panel quedaría inaccesible.
    taken = db.execute(text("""
        SELECT EXISTS (SELECT 1 FROM operadores WHERE lower(email) = :email)
            OR EXISTS (SELECT 1 FROM usuarios WHERE lower(email) = :email)
    """), {"email": payload.email}).scalar_one()
    if taken:
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese correo")
    try:
        row_id = db.execute(text("""
            INSERT INTO operadores (empresa_id, nombre, email, telefono, password_hash)
            VALUES (:empresa_id, :nombre, :email, :telefono, :password_hash) RETURNING id
        """), {"empresa_id": str(user.empresa_id), "nombre": payload.nombre, "email": payload.email,
              "telefono": payload.telefono, "password_hash": hash_password(payload.clave)}).scalar_one()
        db.commit()
    except IntegrityError as exc:
        # Dos altas simultáneas con el mismo correo: la restricción UNIQUE decide.
        db.rollback()
        if getattr(exc.orig, "sqlstate", None) == "23505":
            raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese correo") from exc
        raise
    return OperatorDetail(**_operator_row(db, row_id, user.empresa_id))


@router.patch("/panel/operadores/{operator_id}", response_model=OperatorDetail)
def update_operator(operator_id: UUID, payload: OperatorUpdate, user: CurrentUser = Depends(require_admin),
                    db: Connection = Depends(get_db)):
    # No se eliminan técnicos: se desactivan para conservar el historial de
    # visitas. Un técnico inactivo no puede iniciar sesión ni usar su token.
    _operator_row(db, operator_id, user.empresa_id, lock=True)
    values = payload.model_dump(exclude_unset=True)
    sets, params = [], {"id": str(operator_id), "empresa_id": str(user.empresa_id)}
    for key in ("nombre", "telefono", "activo"):
        if key in values:
            sets.append(f"{key} = :{key}")
            params[key] = values[key]
    if "clave" in values:
        # Subir session_version cierra las sesiones abiertas en la app.
        sets += ["password_hash = :password_hash", "session_version = session_version + 1"]
        params["password_hash"] = hash_password(values["clave"])
    if sets:
        db.execute(text(f"UPDATE operadores SET {', '.join(sets)} WHERE id = :id AND empresa_id = :empresa_id"), params)
        db.commit()
    return OperatorDetail(**_operator_row(db, operator_id, user.empresa_id))


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
    lat, lng = payload.lat, payload.lng
    # El panel envía la dirección, no obliga al usuario a conocer coordenadas.
    # Se conserva compatibilidad con integraciones que proporcionan ambas.
    if lat is None and lng is None:
        found = geocodificar(payload.direccion)
        if found is not None:
            lat, lng, _ = found
    row = _client_write(db, text("""
        INSERT INTO clientes (empresa_id, nombre, telefono_whatsapp, direccion, ubicacion)
        VALUES (:empresa_id, :nombre, :telefono, :direccion,
                ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography)
        RETURNING id
    """), {"empresa_id": str(user.empresa_id), "nombre": payload.nombre.strip(), "telefono": payload.telefono_whatsapp.strip(),
          "direccion": payload.direccion.strip(), "lat": lat, "lng": lng}, returning_id=True)
    return _client(_client_row(db, row, user.empresa_id))


@router.patch("/clientes/{client_id}", response_model=ClientSummary)
def update_client(client_id: UUID, payload: ClientUpdate, user: CurrentUser = Depends(require_web_user), db: Connection = Depends(get_db)):
    # Serializa cambios de dirección y ubicación del mismo cliente. La consulta
    # a Google está acotada por el timeout del servicio de geocodificación.
    current = _client_row(db, client_id, user.empresa_id, lock=True)
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
        params.update({"lat": values.get("lat", current["lat"]), "lng": values.get("lng", current["lng"])})
        if (params["lat"] is None) != (params["lng"] is None):
            raise HTTPException(status_code=422, detail="Completa ambas coordenadas o deja ambas vacías")
        sets.append("ubicacion = ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography")
    elif "direccion" in values:
        address = params["direccion"]
        if address != current["direccion"] or current["lat"] is None or current["lng"] is None:
            # No conservar el punto de la dirección anterior si Google falla.
            # Volver a guardar una dirección pendiente permite reintentar.
            found = geocodificar(address) if address else None
            params.update({"lat": found[0] if found else None, "lng": found[1] if found else None})
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


_ACTIVE = {VisitStatus.agendada.value, VisitStatus.reagendada.value}


def _notice_for_change(before: dict, after: dict) -> str | None:
    """Qué aviso de WhatsApp corresponde a un cambio hecho en el panel.
    Cambiar solo las notas, el operador o el avance (en curso, completada)
    no se le avisa al cliente."""
    if after["estado"] == VisitStatus.cancelada.value and before["estado"] != VisitStatus.cancelada.value:
        return AVISO_CANCELADA
    if after["estado"] not in _ACTIVE:
        return None
    if before["estado"] == VisitStatus.cancelada.value:
        return AVISO_AGENDADA  # se reactivó una visita cancelada
    if after["fecha_hora"] != before["fecha_hora"]:
        return AVISO_REAGENDADA
    return None


@router.post("/panel/visitas", response_model=PanelVisitResponse, status_code=status.HTTP_201_CREATED)
def create_visit(payload: VisitCreate, background_tasks: BackgroundTasks,
                 user: CurrentUser = Depends(require_web_user), db: Connection = Depends(get_db)):
    _client_row(db, payload.cliente_id, user.empresa_id)
    _validate_operator_slot(db, user.empresa_id, payload.operador_id, payload.fecha_hora)
    row_id = db.execute(text("""
        INSERT INTO visitas (empresa_id, cliente_id, operador_id, fecha_hora, estado, origen_agendamiento, notas)
        VALUES (:empresa_id, :cliente_id, :operador_id, :fecha_hora, 'agendada', 'manual', :notas) RETURNING id
    """), {"empresa_id": str(user.empresa_id), "cliente_id": str(payload.cliente_id), "operador_id": str(payload.operador_id) if payload.operador_id else None,
          "fecha_hora": payload.fecha_hora, "notas": payload.notas}).scalar_one()
    db.commit()
    row = _visit_row(db, row_id, user.empresa_id)
    # El aviso por WhatsApp se envía después de responder: el panel no espera a Twilio.
    background_tasks.add_task(avisar_visita_en_segundo_plano, row, AVISO_AGENDADA)
    return _visit(row)


def _visit_row(db: Connection, visit_id: UUID, empresa_id: UUID, *, lock=False) -> dict:
    sql = _VISITS + " AND v.id = :id" + (" FOR UPDATE OF v" if lock else "")
    row = db.execute(text(sql), {"empresa_id": str(empresa_id), "id": str(visit_id)}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Visita no encontrada")
    return dict(row)


@router.patch("/panel/visitas/{visit_id}", response_model=PanelVisitResponse)
def update_panel_visit(visit_id: UUID, payload: PanelVisitUpdate, background_tasks: BackgroundTasks,
                       user: CurrentUser = Depends(require_web_user), db: Connection = Depends(get_db)):
    before = _visit_row(db, visit_id, user.empresa_id, lock=True)
    values = payload.model_dump(exclude_unset=True)
    new_date = values.get("fecha_hora", before["fecha_hora"])
    moved = new_date.astimezone(timezone.utc) != before["fecha_hora"].astimezone(timezone.utc)
    operator_id = values.get("operador_id", before["operador_id"])
    reassigned = str(operator_id) != str(before["operador_id"])
    if values.get("estado") == VisitStatus.reagendada and before["estado"] != "reagendada" and not moved:
        raise HTTPException(status_code=422, detail="Para reagendar debes indicar una nueva fecha y hora")
    if before["estado"] in {"completada", "cancelada"} and (moved or reassigned):
        raise HTTPException(status_code=409, detail="Reactiva la visita antes de cambiar su fecha u operador")
    if moved and values.get("estado", before["estado"]) not in {"cancelada", "completada"}:
        values["estado"] = VisitStatus.reagendada
    target_state = values.get("estado", before["estado"])
    if target_state in {"agendada", "reagendada", "en_curso"} and (moved or reassigned or "estado" in values):
        _validate_operator_slot(db, user.empresa_id, operator_id, new_date, visit_id)
    if "operador_id" in values:
        values["operador_id"] = str(operator_id) if operator_id else None
    if values:
        sets = [f"{key} = :{key}" for key in values]
        if moved:
            # Si cambió la fecha, la visita debe recibir un recordatorio nuevo.
            sets.append("recordatorio_enviado_at = NULL")
        db.execute(text(f"UPDATE visitas SET {', '.join(sets)} WHERE id = :id AND empresa_id = :empresa_id"),
                   {**values, "id": str(visit_id), "empresa_id": str(user.empresa_id)})
        db.commit()
    after = _visit_row(db, visit_id, user.empresa_id)
    notice = _notice_for_change(before, after)
    if notice:
        background_tasks.add_task(avisar_visita_en_segundo_plano, after, notice)
    return _visit(after)


@router.delete("/panel/visitas/{visit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_visit(visit_id: UUID, background_tasks: BackgroundTasks,
                 user: CurrentUser = Depends(require_web_user), db: Connection = Depends(get_db)):
    before = _visit_row(db, visit_id, user.empresa_id)
    # Las visitas forman parte del historial y pueden tener un croquis asociado.
    # Se cancelan en lugar de borrarse para conservar la trazabilidad.
    db.execute(
        text("UPDATE visitas SET estado = 'cancelada' WHERE id = :id AND empresa_id = :empresa_id"),
        {"id": str(visit_id), "empresa_id": str(user.empresa_id)},
    )
    db.commit()
    if before["estado"] != VisitStatus.cancelada.value:
        background_tasks.add_task(avisar_visita_en_segundo_plano, before, AVISO_CANCELADA)
