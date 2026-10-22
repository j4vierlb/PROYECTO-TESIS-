# =============================================================================
# routers/croquis.py — Croquis de una visita
# -----------------------------------------------------------------------------
#   GET  /croquis/{visita_id}               el plano de la visita con sus trampas.
#   POST /croquis/{visita_id}               crea el croquis si la visita no tiene
#                                           (copia las trampas activas de la
#                                           visita anterior del mismo cliente).
#   POST /croquis/{visita_id}/dispositivos  el operador agrega una trampa que
#                                           instaló en terreno.
#   POST /croquis/{visita_id}/sugerencia    la IA propone trampas a partir de la
#                                           foto satelital (ver
#                                           docs/diseno_ia_croquis.md).
# =============================================================================

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.engine import Connection

from app.ai.croquis_agent import sugerir_dispositivos
from app.database import get_db
from app.dependencies import ensure_visit_access, ensure_visit_open, get_current_user, require_operator
from app.geocoding import geocodificar
from app.repositories import (
    add_device,
    add_suggested_devices,
    create_croquis_for_visit,
    fetch_croquis_for_visit,
    fetch_device,
    fetch_devices_for_croquis,
    fetch_visit,
    save_client_location,
)
from app.schemas import (
    CroquisResponse,
    CroquisSuggestionRequest,
    CroquisSuggestionResponse,
    CurrentUser,
    DeviceCreate,
    DeviceResponse,
)

router = APIRouter(tags=["croquis"])


def _croquis_response(db: Connection, visit_id: UUID) -> CroquisResponse:
    """Arma la respuesta: los datos del croquis más la lista de trampas."""
    croquis = fetch_croquis_for_visit(db, visit_id)          # 404 si la visita no tiene croquis
    devices = fetch_devices_for_croquis(db, croquis["id"])   # las trampas de ese croquis
    return CroquisResponse(
        id=croquis["id"],
        visita_id=visit_id,
        cliente_id=croquis["cliente_id"],
        version=croquis["version"],
        imagen_satelital_url=croquis["imagen_satelital_url"],
        sugerido_por_ia=croquis["sugerido_por_ia"],
        validado_por_operador=croquis["validado_por_operador"],
        dispositivos=[DeviceResponse.from_row(device) for device in devices],
    )


@router.get("/croquis/{visit_id}", response_model=CroquisResponse)
def get_croquis(visit_id: UUID, user: CurrentUser = Depends(get_current_user), db: Connection = Depends(get_db)) -> CroquisResponse:
    """El croquis pertenece a una visita, así que hereda su mismo control de
    acceso (404 si la visita no existe, 403 si es de otro operador)."""
    visit = fetch_visit(db, visit_id)
    ensure_visit_access(user, visit)
    return _croquis_response(db, visit_id)


@router.post("/croquis/{visit_id}", response_model=CroquisResponse)
def create_croquis(
    visit_id: UUID,
    response: Response,
    user: CurrentUser = Depends(require_operator),
    db: Connection = Depends(get_db),
) -> CroquisResponse:
    """Crea el croquis de la visita la primera vez que el técnico lo abre.
    Si ya existe, lo devuelve tal cual (llamarlo dos veces no duplica nada):
    201 si se creó ahora, 200 si ya existía."""
    visit = fetch_visit(db, visit_id)
    ensure_visit_access(user, visit)
    ensure_visit_open(visit["estado"])
    _, created = create_croquis_for_visit(db, visit, user.id)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return _croquis_response(db, visit_id)


@router.post("/croquis/{visit_id}/dispositivos", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
def create_device(
    visit_id: UUID,
    payload: DeviceCreate,
    user: CurrentUser = Depends(require_operator),
    db: Connection = Depends(get_db),
) -> DeviceResponse:
    """Agrega al croquis una trampa que el operador instaló en terreno. El
    backend le asigna el siguiente código libre (T-01, T-02...)."""
    visit = fetch_visit(db, visit_id)
    ensure_visit_access(user, visit)
    ensure_visit_open(visit["estado"])
    croquis = fetch_croquis_for_visit(db, visit_id)  # 404 si todavía no se creó
    device_id = add_device(db, croquis["id"], payload.tipo.value, payload.lat, payload.lng)
    return DeviceResponse.from_row(fetch_device(db, device_id))


@router.post("/croquis/{visit_id}/sugerencia", response_model=CroquisSuggestionResponse)
def suggest_devices(
    visit_id: UUID,
    body: CroquisSuggestionRequest,
    user: CurrentUser = Depends(require_operator),
    db: Connection = Depends(get_db),
) -> CroquisSuggestionResponse:
    """Agrega al croquis de la visita (lo crea si no existe) las trampas que
    propone la IA a partir de la foto satelital, o el plan B por reglas si la
    IA no está disponible. Quedan sin confirmar: el técnico las revisa con
    PATCH /dispositivos-trampa/{id}. Las trampas que ya están en el croquis
    se le informan a la IA para que no las repita."""
    visit = fetch_visit(db, visit_id)
    ensure_visit_access(user, visit)
    ensure_visit_open(visit["estado"])

    lat, lng = visit["lat"], visit["lng"]
    if lat is None or lng is None:
        # Cliente sin coordenadas (p. ej. llegó por WhatsApp y la geocodificación
        # en segundo plano no encontró un punto confiable): se intenta una vez más.
        found = geocodificar(visit["direccion"])
        if found is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El cliente no tiene ubicación y su dirección no se pudo geolocalizar",
            )
        lat, lng, _ = found
        save_client_location(db, visit["cliente_id"], lat, lng)

    croquis_id, _ = create_croquis_for_visit(db, visit, user.id)
    existing = [
        {"tipo": d["tipo"], "lat": d["lat"], "lng": d["lng"]}
        for d in fetch_devices_for_croquis(db, croquis_id)
        if d["estado"] != "retirado"
    ]
    # Cierra la transacción de lectura antes de esperar a Google y OpenAI.
    db.commit()

    suggestion = sugerir_dispositivos(
        lat,
        lng,
        {
            "tipo_recinto": body.tipo_recinto.value,
            "plaga": body.plaga.value,
            "superficie_m2": body.superficie_m2,
            "notas": body.notas,
        },
        existing,
    )
    if suggestion.dispositivos:
        add_suggested_devices(db, croquis_id, suggestion.imagen_satelital_url, suggestion.dispositivos)
    croquis = _croquis_response(db, visit_id)
    return CroquisSuggestionResponse(
        **croquis.model_dump(),
        origen=suggestion.origen,
        resumen=suggestion.resumen,
        advertencias=suggestion.advertencias,
    )
