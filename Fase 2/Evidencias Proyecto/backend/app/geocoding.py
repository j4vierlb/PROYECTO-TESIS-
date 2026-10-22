# =============================================================================
# geocoding.py — Dirección (texto) → coordenadas (lat, lng)
# -----------------------------------------------------------------------------
# Los clientes que llegan por WhatsApp solo dan su dirección escrita. Sin
# coordenadas no hay foto satelital ni croquis, así que aquí se convierte la
# dirección en un punto con Google Geocoding API (ver docs/diseno_ia_croquis.md,
# sección 1.1).
#
# Regla principal: ante la duda, NO se guarda nada. Una ubicación imprecisa
# produce una foto del lugar equivocado y un croquis inútil; es mejor dejar el
# cliente sin coordenadas y que el operador las fije en terreno.
# =============================================================================

import logging
import math
import re
from uuid import UUID

import httpx
from sqlalchemy import text

from app.config import settings

logger = logging.getLogger(__name__)

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
TIMEOUT_SECONDS = 5.0

# Solo estos tipos apuntan al predio. GEOMETRIC_CENTER y APPROXIMATE
# significan que Google solo encontró la calle o la comuna.
PRECISE_LOCATION_TYPES = {"ROOFTOP", "RANGE_INTERPOLATED"}

# Rectángulo de la Región Metropolitana (Kill Bichos solo atiende ahí). Por sí
# solo no basta: Valparaíso y Viña del Mar también caen dentro, por eso además
# se revisa la región que informa Google (_in_rm_region).
RM_LAT = (-34.3, -32.9)
RM_LNG = (-71.8, -69.8)

# Si hay varios resultados pero todos a menos de esta distancia, se usa el primero.
MAX_SPREAD_METERS = 100

# Comunas de la RM: si la dirección no nombra ninguna, se agrega la región para
# que Google no elija una calle con el mismo nombre en otra ciudad.
COMUNAS_RM = {
    "alhue", "buin", "calera de tango", "cerrillos", "cerro navia", "colina", "conchali",
    "curacavi", "el bosque", "el monte", "estacion central", "huechuraba", "independencia",
    "isla de maipo", "la cisterna", "la florida", "la granja", "la pintana", "la reina",
    "lampa", "las condes", "lo barnechea", "lo espejo", "lo prado", "macul", "maipu",
    "maria pinto", "melipilla", "nunoa", "padre hurtado", "paine", "pedro aguirre cerda",
    "penaflor", "penalolen", "pirque", "providencia", "pudahuel", "puente alto", "quilicura",
    "quinta normal", "recoleta", "renca", "san bernardo", "san joaquin", "san jose de maipo",
    "san miguel", "san pedro", "san ramon", "santiago", "talagante", "tiltil", "vitacura",
}

_ACCENTS = str.maketrans("áéíóúüñ", "aeiouun")


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower().translate(_ACCENTS))


def _with_region(address: str) -> str:
    """Agrega ", Región Metropolitana" si la dirección no trae comuna."""
    normalized = _normalize(address)
    if any(re.search(rf"\b{comuna}\b", normalized) for comuna in COMUNAS_RM):
        return address
    if "metropolitana" in normalized:
        return address
    return f"{address}, Región Metropolitana"


def distance_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distancia aproximada (fórmula de haversine)."""
    radius = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def describe_error(exc: Exception) -> str:
    """Describe un error de httpx SIN la URL: las de Google llevan la clave
    en "?key=..." y no debe quedar escrita en los logs."""
    if isinstance(exc, httpx.HTTPStatusError):
        return f"HTTP {exc.response.status_code}"
    return type(exc).__name__


def _location(result: dict) -> tuple[float, float]:
    loc = result["geometry"]["location"]
    return float(loc["lat"]), float(loc["lng"])


def _in_rm_region(result: dict) -> bool:
    """True si Google ubica el resultado en la Región Metropolitana."""
    for component in result.get("address_components") or []:
        if "administrative_area_level_1" in component.get("types", []):
            return "metropolitana" in _normalize(component.get("long_name", ""))
    return False


def _pick_result(data: dict, address: str) -> tuple[float, float, str] | None:
    """Aplica las validaciones del diseño. Devuelve None si algo no cuadra."""
    status = data.get("status")
    if status != "OK":
        if status != "ZERO_RESULTS":
            logger.warning("Geocoding respondió %s para %r: %s", status, address, data.get("error_message"))
        return None

    results = data.get("results") or []
    if not results:
        return None
    first = results[0]
    lat, lng = _location(first)

    if len(results) > 1:
        far = [r for r in results[1:] if distance_meters(lat, lng, *_location(r)) >= MAX_SPREAD_METERS]
        if far:
            logger.info("Dirección ambigua (%d resultados distintos), no se guarda: %r", len(results), address)
            return None

    if first.get("partial_match"):
        logger.info("Coincidencia parcial, no se guarda: %r", address)
        return None

    precision = first["geometry"].get("location_type", "")
    if precision not in PRECISE_LOCATION_TYPES:
        logger.info("Ubicación imprecisa (%s), no se guarda: %r", precision, address)
        return None

    in_box = RM_LAT[0] <= lat <= RM_LAT[1] and RM_LNG[0] <= lng <= RM_LNG[1]
    if not (in_box and _in_rm_region(first)):
        logger.info("Punto fuera de la Región Metropolitana (%s, %s), no se guarda: %r", lat, lng, address)
        return None

    return lat, lng, precision


def geocodificar(direccion: str | None, http: httpx.Client | None = None) -> tuple[float, float, str] | None:
    """Convierte la dirección en (lat, lng, precision). Devuelve None si no hay
    clave, si la dirección está vacía, si Google falla o si el resultado no es
    confiable. Nunca lanza excepciones: quien la llama sigue igual.

    `http` permite inyectar un cliente simulado en las pruebas."""
    address = (direccion or "").strip()
    if not address or not settings.google_maps_api_key:
        return None

    params = {
        "address": _with_region(address),
        "components": "country:CL",
        "region": "cl",
        "language": "es",
        "key": settings.google_maps_api_key,
    }
    try:
        if http is None:
            with httpx.Client(timeout=TIMEOUT_SECONDS) as own_http:
                response = own_http.get(GEOCODE_URL, params=params)
        else:
            response = http.get(GEOCODE_URL, params=params, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        return _pick_result(response.json(), address)
    except Exception as exc:
        # Timeout, sin red, JSON raro... El cliente queda sin coordenadas como antes.
        logger.warning("Falló la geocodificación de %r: %s", address, describe_error(exc))
        return None


def geocodificar_cliente(cliente_id: UUID, direccion: str) -> None:
    """Tarea en segundo plano: geocodifica y guarda en clientes.ubicacion.

    Abre su propia conexión porque corre después de responder el request. Solo
    escribe si la dirección del cliente sigue siendo la misma y aún no tiene
    ubicación (así no pisa una corrección hecha a mano mientras tanto)."""
    result = geocodificar(direccion)
    if result is None:
        return
    lat, lng, precision = result

    from app.database import engine  # import local: las pruebas sin BD no lo necesitan

    try:
        with engine.begin() as db:
            updated = db.execute(
                text("""
                    UPDATE clientes
                    SET ubicacion = ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography
                    WHERE id = :id AND direccion = :direccion AND ubicacion IS NULL
                """),
                {"id": str(cliente_id), "direccion": direccion, "lat": lat, "lng": lng},
            ).rowcount
        if updated:
            logger.info("Cliente %s geocodificado (%s): %s, %s", cliente_id, precision, lat, lng)
    except Exception:
        logger.exception("No se pudo guardar la ubicación del cliente %s", cliente_id)
