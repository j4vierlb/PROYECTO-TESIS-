# =============================================================================
# routers/croquis.py — Croquis de una visita
# -----------------------------------------------------------------------------
#   GET  /croquis/{visita_id}              el plano de la visita con todas sus trampas.
#   POST /croquis/{visita_id}/sugerencia   la IA propone las trampas (ver
#                                          docs/diseno_ia_croquis.md).
# =============================================================================

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.engine import Connection

from app.ai.croquis_agent import sugerir_dispositivos
from app.database import get_db
from app.dependencies import ensure_visit_access, get_current_user
from app.geocoding import geocodificar
from app.repositories import (
    croquis_exists_for_visit,
    fetch_croquis_for_visit,
    fetch_devices_for_croquis,
    fetch_previous_croquis,
    fetch_visit,
    insert_suggested_croquis,
    save_client_location,
)
from app.schemas import (
    CroquisResponse,
    CroquisSuggestionRequest,
    CroquisSuggestionResponse,
    CurrentUser,
    DeviceResponse,
)

router = APIRouter(tags=["croquis"])


def _build_croquis(db: Connection, visit_id: UUID) -> dict:
    """Los datos del croquis más la lista de trampas, listos para la respuesta."""
    croquis = fetch_croquis_for_visit(db, visit_id)          # 404 si la visita no tiene croquis
    devices = fetch_devices_for_croquis(db, croquis["id"])   # las trampas de ese croquis
    return dict(
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


@router.get("/croquis/{visit_id}", response_model=CroquisResponse)
def get_croquis(visit_id: UUID, user: CurrentUser = Depends(get_current_user), db: Connection = Depends(get_db)) -> CroquisResponse:
    """El croquis pertenece a una visita, así que hereda su mismo control de
    acceso (404 si la visita no existe, 403 si es de otro operador)."""
    visit = fetch_visit(db, visit_id)
    ensure_visit_access(user, visit)
    return CroquisResponse(**_build_croquis(db, visit_id))


@router.post(
    "/croquis/{visit_id}/sugerencia",
    response_model=CroquisSuggestionResponse,
    status_code=status.HTTP_201_CREATED,
)
def suggest_croquis(
    visit_id: UUID,
    body: CroquisSuggestionRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Connection = Depends(get_db),
) -> CroquisSuggestionResponse:
    """Crea el croquis de la visita con trampas propuestas por la IA (o por
    reglas si la IA no está disponible). Todas quedan sin confirmar: el
    operador las revisa en terreno con PATCH /dispositivos-trampa/{id}."""
    visit = fetch_visit(db, visit_id)
    ensure_visit_access(user, visit)
    if visit["estado"] == "cancelada":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La visita está cancelada")
    if croquis_exists_for_visit(db, visit_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La visita ya tiene croquis")

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

    version, previous = fetch_previous_croquis(db, visit["cliente_id"])
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
        [{"tipo": d["tipo"], "lat": d["lat"], "lng": d["lng"]} for d in previous],
    )
    insert_suggested_croquis(
        db, visit, version + 1, suggestion.imagen_satelital_url, previous, suggestion.dispositivos
    )
    return CroquisSuggestionResponse(
        **_build_croquis(db, visit_id),
        origen=suggestion.origen,
        resumen=suggestion.resumen,
        advertencias=suggestion.advertencias,
    )
