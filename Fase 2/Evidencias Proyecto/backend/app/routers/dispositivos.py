from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.engine import Connection

from app.database import get_db
from app.dependencies import require_operator
from app.repositories import confirm_device, fetch_device, move_device, remove_device
from app.schemas import CurrentUser, DeviceAction, DeviceResponse, DeviceUpdate

router = APIRouter(tags=["dispositivos"])


def _to_device_response(row: dict) -> DeviceResponse:
    return DeviceResponse(
        id=row["id"],
        codigo=row["codigo"],
        tipo=row["tipo"],
        lat=row["lat"],
        lng=row["lng"],
        sugerido_por_ia=row["sugerido_por_ia"],
        confirmado=row["confirmado"],
        estado=row["estado"],
    )


@router.patch("/dispositivos-trampa/{device_id}", response_model=DeviceResponse)
def update_device(
    device_id: UUID,
    changes: DeviceUpdate,
    user: CurrentUser = Depends(require_operator),
    db: Connection = Depends(get_db),
) -> DeviceResponse:
    """Aplica la acción indicada sobre un dispositivo trampa:
    - confirmar: el operador valida la ubicación sugerida por la IA.
    - mover: reemplaza la ubicación PostGIS por las nuevas coordenadas.
    - eliminar: no borra el registro, solo lo marca 'retirado' (soft delete)."""
    fetch_device(db, device_id)  # 404 si no existe
    if changes.accion == DeviceAction.confirmar:
        confirm_device(db, device_id)
    elif changes.accion == DeviceAction.mover:
        move_device(db, device_id, changes.lat, changes.lng)
    elif changes.accion == DeviceAction.eliminar:
        remove_device(db, device_id)
    return _to_device_response(fetch_device(db, device_id))
