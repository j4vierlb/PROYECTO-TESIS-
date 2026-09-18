from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.engine import Connection

from app.database import get_db
from app.dependencies import ensure_visit_access, get_current_user, require_operator
from app.repositories import fetch_visit, fetch_visits_for_today, update_visit_fields
from app.schemas import ClientSummary, CurrentUser, VisitResponse, VisitUpdate

router = APIRouter(tags=["visitas"])


def _to_visit_response(row: dict) -> VisitResponse:
    return VisitResponse(
        id=row["id"],
        cliente=ClientSummary(
            id=row["cliente_id"],
            nombre=row["cliente_nombre"],
            telefono_whatsapp=row["telefono_whatsapp"],
            direccion=row["direccion"],
            lat=row["lat"],
            lng=row["lng"],
        ),
        operador_id=row["operador_id"],
        fecha_hora=row["fecha_hora"],
        estado=row["estado"],
        origen_agendamiento=row["origen_agendamiento"],
        notas=row["notas"],
    )


@router.get("/operadores/me/visitas-hoy", response_model=list[VisitResponse])
def visits_today(user: CurrentUser = Depends(require_operator), db: Connection = Depends(get_db)) -> list[VisitResponse]:
    rows = fetch_visits_for_today(db, user.id)
    return [_to_visit_response(row) for row in rows]


@router.get("/visitas/{visit_id}", response_model=VisitResponse)
def get_visit(visit_id: UUID, user: CurrentUser = Depends(get_current_user), db: Connection = Depends(get_db)) -> VisitResponse:
    visit = fetch_visit(db, visit_id)
    ensure_visit_access(user, visit)
    return _to_visit_response(visit)


@router.patch("/visitas/{visit_id}", response_model=VisitResponse)
def update_visit(
    visit_id: UUID,
    changes: VisitUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: Connection = Depends(get_db),
) -> VisitResponse:
    visit = fetch_visit(db, visit_id)
    ensure_visit_access(user, visit)
    # mode="json" asegura que el Enum de estado se guarde como el string
    # ("en_curso"), no como el objeto VisitStatus.
    update_visit_fields(db, visit_id, changes.model_dump(exclude_unset=True, mode="json"))
    return _to_visit_response(fetch_visit(db, visit_id))
