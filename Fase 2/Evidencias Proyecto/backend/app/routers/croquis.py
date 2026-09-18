from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.engine import Connection

from app.database import get_db
from app.dependencies import ensure_visit_access, get_current_user
from app.repositories import fetch_croquis_for_visit, fetch_devices_for_croquis, fetch_visit
from app.schemas import CroquisResponse, CurrentUser, DeviceResponse

router = APIRouter(tags=["croquis"])


@router.get("/croquis/{visit_id}", response_model=CroquisResponse)
def get_croquis(visit_id: UUID, user: CurrentUser = Depends(get_current_user), db: Connection = Depends(get_db)) -> CroquisResponse:
    """El croquis pertenece a una visita, así que hereda su mismo control de
    acceso (404 si la visita no existe, 403 si es de otro operador)."""
    visit = fetch_visit(db, visit_id)
    ensure_visit_access(user, visit)
    croquis = fetch_croquis_for_visit(db, visit_id)
    devices = fetch_devices_for_croquis(db, croquis["id"])
    return CroquisResponse(
        id=croquis["id"],
        visita_id=visit_id,
        cliente_id=croquis["cliente_id"],
        version=croquis["version"],
        imagen_satelital_url=croquis["imagen_satelital_url"],
        sugerido_por_ia=croquis["sugerido_por_ia"],
        validado_por_operador=croquis["validado_por_operador"],
        dispositivos=[
            DeviceResponse(
                id=device["id"],
                codigo=device["codigo"],
                tipo=device["tipo"],
                lat=device["lat"],
                lng=device["lng"],
                sugerido_por_ia=device["sugerido_por_ia"],
                confirmado=device["confirmado"],
                estado=device["estado"],
            )
            for device in devices
        ],
    )
