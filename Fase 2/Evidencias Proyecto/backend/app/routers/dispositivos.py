# =============================================================================
# routers/dispositivos.py — Acciones sobre una trampa
# -----------------------------------------------------------------------------
#   PATCH /dispositivos-trampa/{id}        confirmar, mover o retirar una trampa.
#                                          Body: {"accion": "mover", "lat": -33.48, "lng": -70.59}
#   POST  /dispositivos-trampa/{id}/foto   sube la foto de referencia (JPEG o PNG,
#                                          campo "foto" de un formulario multipart).
#   GET   /dispositivos-trampa/{id}/foto   descarga esa foto (requiere sesión).
#
# Una trampa hereda el acceso de la visita de su croquis: un operador solo
# toca las de sus visitas, y nada se modifica si la visita ya está cerrada.
# =============================================================================

from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.engine import Connection

from app.database import get_db
from app.dependencies import ensure_device_access, ensure_visit_open, get_current_user, require_operator
from app.fotos import guardar_foto, ruta_foto
from app.repositories import (
    confirm_device,
    fetch_device,
    fetch_device_context,
    move_device,
    remove_device,
    set_device_photo,
)
from app.schemas import CurrentUser, DeviceAction, DeviceResponse, DeviceUpdate

router = APIRouter(tags=["dispositivos"])


@router.patch("/dispositivos-trampa/{device_id}", response_model=DeviceResponse)
def update_device(
    device_id: UUID,
    changes: DeviceUpdate,
    # Solo un operador puede tocar trampas (un admin recibe 403).
    user: CurrentUser = Depends(require_operator),
    db: Connection = Depends(get_db),
) -> DeviceResponse:
    """Aplica la acción indicada sobre un dispositivo trampa:
    - confirmar: el operador valida la ubicación sugerida por la IA.
    - mover: reemplaza la ubicación PostGIS por las nuevas coordenadas.
    - eliminar: no borra el registro, solo lo marca 'retirado' (soft delete)."""
    device = fetch_device_context(db, device_id)  # 404 si no existe
    ensure_device_access(user, device)            # 403 si es de otro operador
    ensure_visit_open(device["visita_estado"])    # 409 si la visita ya cerró
    if changes.accion == DeviceAction.confirmar:
        confirm_device(db, device_id)
    elif changes.accion == DeviceAction.mover:
        # lat y lng ya vienen validados por DeviceUpdate (obligatorios al mover).
        move_device(db, device_id, changes.lat, changes.lng)
    elif changes.accion == DeviceAction.eliminar:
        remove_device(db, device_id)
    # Se relee la trampa para responder con su estado real después del cambio.
    return DeviceResponse.from_row(fetch_device(db, device_id))


@router.post("/dispositivos-trampa/{device_id}/foto", response_model=DeviceResponse)
def upload_device_photo(
    device_id: UUID,
    foto: UploadFile = File(...),
    user: CurrentUser = Depends(require_operator),
    db: Connection = Depends(get_db),
) -> DeviceResponse:
    """Guarda la foto de referencia de la trampa (reemplaza la anterior, si
    había). 413 si pesa demasiado, 415 si no es JPEG ni PNG."""
    device = fetch_device_context(db, device_id)
    ensure_device_access(user, device)
    ensure_visit_open(device["visita_estado"])
    nombre = guardar_foto(foto.file)
    set_device_photo(db, device_id, nombre)
    return DeviceResponse.from_row(fetch_device(db, device_id))


@router.get("/dispositivos-trampa/{device_id}/foto")
def get_device_photo(
    device_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Connection = Depends(get_db),
) -> FileResponse:
    """Entrega la foto solo a quien puede ver la trampa: el operador de la
    visita o un usuario del panel de la misma empresa. No es pública."""
    device = fetch_device_context(db, device_id)
    ensure_device_access(user, device)
    path, media_type = ruta_foto(device["foto_path"])
    # private: el teléfono puede guardarla en caché, pero no un proxy compartido.
    return FileResponse(path, media_type=media_type, headers={"Cache-Control": "private, max-age=86400"})
