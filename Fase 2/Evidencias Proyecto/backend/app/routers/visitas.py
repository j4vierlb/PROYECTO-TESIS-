# =============================================================================
# routers/visitas.py — Endpoints de visitas
# -----------------------------------------------------------------------------
#   GET   /operadores/me/visitas-hoy       agenda del día del operador logueado
#   GET   /operadores/me/visitas-historial visitas ya completadas (historial)
#   GET   /visitas/{id}                    detalle de una visita
#   PATCH /visitas/{id}                    cambiar estado y/o notas
#
# Cómo leer un endpoint de FastAPI:
#   @router.get("/ruta")          -> qué método HTTP y qué URL atiende
#   response_model=...            -> forma del JSON que responde (schemas.py)
#   parámetro = Depends(algo)     -> FastAPI ejecuta `algo` antes del endpoint
#                                    y le pasa el resultado (usuario, conexión).
# =============================================================================

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.engine import Connection

from app.database import get_db
from app.dependencies import ensure_visit_access, get_current_user, require_operator
from app.repositories import fetch_visit, fetch_visit_history, fetch_visits_for_today, update_visit_fields
from app.schemas import ClientSummary, CurrentUser, VisitHistoryItem, VisitResponse, VisitUpdate
from app.zona_horaria import hoy_chile

# El router agrupa estos endpoints; main.py lo registra en la aplicación.
# tags=["visitas"] los agrupa bajo ese título en /docs.
router = APIRouter(tags=["visitas"])


def _to_visit_response(row: dict) -> VisitResponse:
    """Convierte una fila de la base (plana) en la respuesta de la API, que
    tiene los datos del cliente anidados dentro de "cliente"."""
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
    """Agenda del día. "me" = el operador dueño del token, así nadie puede
    pedir la agenda de otro operador cambiando un id en la URL."""
    # "Hoy" es el día de Chile, no el de UTC (ver zona_horaria.py).
    rows = fetch_visits_for_today(db, user.id, hoy_chile())
    return [_to_visit_response(row) for row in rows]


@router.get("/operadores/me/visitas-historial", response_model=list[VisitHistoryItem])
def visits_history(
    # Query(...) = parámetros que van en la URL: ?limit=20&offset=0.
    # ge/le limitan los valores permitidos (limit entre 1 y 100); si no se
    # cumplen, FastAPI responde 422 sin llegar a ejecutar el endpoint.
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: CurrentUser = Depends(require_operator),
    db: Connection = Depends(get_db),
) -> list[VisitHistoryItem]:
    """Visitas completadas del operador logueado, paginadas con limit/offset."""
    rows = fetch_visit_history(db, user.id, limit, offset)
    # Reutiliza la conversión de una visita normal y le agrega el conteo de
    # trampas. `**` "desarma" el diccionario en argumentos con nombre.
    return [
        VisitHistoryItem(
            **_to_visit_response(row).model_dump(),
            dispositivos_instalados=row["dispositivos_instalados"],
        )
        for row in rows
    ]


@router.get("/visitas/{visit_id}", response_model=VisitResponse)
def get_visit(visit_id: UUID, user: CurrentUser = Depends(get_current_user), db: Connection = Depends(get_db)) -> VisitResponse:
    """Detalle de una visita. {visit_id} en la URL llega como parámetro, y
    FastAPI valida que sea un UUID (si no, 422)."""
    visit = fetch_visit(db, visit_id)  # 404 si no existe
    ensure_visit_access(user, visit)   # 403 si es de otro operador
    return _to_visit_response(visit)


@router.patch("/visitas/{visit_id}", response_model=VisitResponse)
def update_visit(
    visit_id: UUID,
    changes: VisitUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: Connection = Depends(get_db),
) -> VisitResponse:
    """Cambia el estado y/o las notas de una visita y devuelve la visita ya
    actualizada. `changes` es el JSON del body, validado con VisitUpdate."""
    visit = fetch_visit(db, visit_id)
    ensure_visit_access(user, visit)
    # exclude_unset=True: solo los campos que realmente vinieron en el JSON.
    # mode="json" asegura que el Enum de estado se guarde como el string
    # ("en_curso"), no como el objeto VisitStatus.
    update_visit_fields(db, visit_id, changes.model_dump(exclude_unset=True, mode="json"))
    # Se vuelve a leer de la base para responder con los datos reales guardados.
    return _to_visit_response(fetch_visit(db, visit_id))
