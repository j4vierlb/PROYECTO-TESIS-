# =============================================================================
# ai/croquis_agent.py — Sugerencia de trampas a partir de la foto satelital
# -----------------------------------------------------------------------------
# Pide a Google la foto satelital del predio, se la muestra a OpenAI junto con
# el tipo de recinto y la plaga, y la IA responde dónde pondría cada trampa en
# PÍXELES de la imagen. Aquí se convierten a lat/lng y se validan antes de que
# el router guarde nada (ver docs/diseno_ia_croquis.md, secciones 2 y 3).
#
# Si falta la foto, falla la IA o no queda ninguna trampa válida, se usa el
# plan B por reglas: cebaderos en las esquinas + 1 cada 15 m de perímetro.
#
# Este módulo no toca la base de datos.
# =============================================================================

import base64
import json
import logging
import math
from dataclasses import dataclass, field
from urllib.parse import urlencode

import httpx

from app.ai.agent import OPENAI_URL, _extract_json
from app.config import settings
from app.geocoding import describe_error, distance_meters

logger = logging.getLogger(__name__)

STATIC_MAP_URL = "https://maps.googleapis.com/maps/api/staticmap"
# Sin clave de Google se usa Esri World Imagery, que no pide clave. Usa la misma
# proyección (Web Mercator), así que la conversión píxel -> lat/lng es la misma.
# Pensado para desarrollo y pruebas: en producción, Google o una cuenta ArcGIS.
ESRI_EXPORT_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export"
EARTH_RADIUS_M = 6_378_137  # radio de la esfera de Web Mercator (EPSG:3857)
IMAGE_SIZE = 640        # px, máximo de Static Maps sin plan premium
ZOOM = 20               # Google: ~0,12 m por píxel en Santiago, la imagen cubre ~80 × 80 m
ESRI_ZOOM = 19          # Esri no tiene zoom 20 en Santiago: ~0,25 m/px, cubre ~160 × 160 m
TILE_SIZE = 256         # tamaño del "mundo" de Google en zoom 0

MAX_DISTANCE_METERS = 60    # una trampa más lejos del centro no es de este predio
MIN_SEPARATION_METERS = 3   # dos trampas más cerca que esto son la misma
METERS_PER_DEVICE = 15      # 1 dispositivo cada 15 m de perímetro
MAX_DEVICES = 30
DEFAULT_AREA_M2 = 200       # si nadie indicó la superficie, una casa típica

VALID_TYPES = {"cebadero", "trampa_pegamento", "trampa_luz", "otro"}

# Qué dispositivo usa el plan B según la plaga.
PLAN_B_TYPE = {
    "roedores": "cebadero",
    "cucarachas": "trampa_pegamento",
    "moscas": "trampa_luz",
    "otra": "trampa_pegamento",
}

SYSTEM_PROMPT = """
Eres un técnico experto en control de plagas de Kill Bichos (Santiago de Chile).
Recibes una foto satelital de 640x640 píxeles centrada en el predio de un cliente
y propones dónde instalar dispositivos de control. Un operador revisará tu
propuesta en terreno: sé concreto y explica cada ubicación.

Criterios:
- Roedores: cebaderos en el perímetro, junto a muros, rejas, vegetación densa,
  zonas de basura y accesos. Separación de 10 a 15 m entre cebaderos.
- Cucarachas: trampas de pegamento cerca de cocinas, desagües y bodegas.
- Moscas: trampas de luz cerca de accesos y zonas de basura, lejos de ventanas.
- El predio del cliente está en el CENTRO de la imagen (píxel 320, 320). Se te indica
  un radio aproximado en píxeles según su superficie: ubica todo dentro de ese radio.
- Coloca los dispositivos en bordes y rincones: junto a muros, rejas, cercos,
  vegetación, contenedores de basura y accesos. Nunca en medio de espacios abiertos.
- No ubiques dispositivos sobre canchas deportivas, calles, estacionamientos abiertos,
  piscinas ni techos de edificios vecinos.
- No repitas dispositivos donde ya hay uno instalado (se te indican sus píxeles).
- Si la imagen no permite ver algo importante, dilo en advertencias.

Devuelve SIEMPRE JSON válido con exactamente estas claves:
  resumen (texto breve), dispositivos (lista), advertencias (lista de textos)
Cada dispositivo: tipo, x, y, zona, motivo, confianza
- tipo: cebadero, trampa_pegamento, trampa_luz u otro
- x, y: píxel de la imagen (0 a 639; x hacia la derecha, y hacia abajo)
- confianza: número entre 0 y 1
"""


@dataclass
class Sugerencia:
    """Resultado ya validado, listo para guardar."""
    dispositivos: list[dict]                 # {tipo, lat, lng}
    advertencias: list[str] = field(default_factory=list)
    resumen: str | None = None
    imagen_satelital_url: str | None = None  # SIN la clave de Google
    origen: str = "ia"                       # "ia" o "reglas" (plan B)


# ---------------------------------------------------------------------------
# Píxel de la imagen <-> lat/lng (proyección Web Mercator, la de Google Maps)
# ---------------------------------------------------------------------------
def _world_pixel(lat: float, lng: float, zoom: int) -> tuple[float, float]:
    scale = TILE_SIZE * 2 ** zoom
    sin_lat = math.sin(math.radians(lat))
    x = (lng + 180) / 360 * scale
    y = (0.5 - math.log((1 + sin_lat) / (1 - sin_lat)) / (4 * math.pi)) * scale
    return x, y


def latlng_to_pixel(lat: float, lng: float, center_lat: float, center_lng: float, zoom: int = ZOOM) -> tuple[float, float]:
    """Dónde cae (lat, lng) en la imagen centrada en (center_lat, center_lng)."""
    x, y = _world_pixel(lat, lng, zoom)
    cx, cy = _world_pixel(center_lat, center_lng, zoom)
    return x - cx + IMAGE_SIZE / 2, y - cy + IMAGE_SIZE / 2


def pixel_to_latlng(px: float, py: float, center_lat: float, center_lng: float, zoom: int = ZOOM) -> tuple[float, float]:
    """Inversa de latlng_to_pixel."""
    scale = TILE_SIZE * 2 ** zoom
    cx, cy = _world_pixel(center_lat, center_lng, zoom)
    x = cx + px - IMAGE_SIZE / 2
    y = cy + py - IMAGE_SIZE / 2
    lng = x / scale * 360 - 180
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / scale))))
    return lat, lng


def _offset(lat: float, lng: float, east_m: float, north_m: float) -> tuple[float, float]:
    """Desplaza un punto unos metros (aproximación válida para distancias cortas)."""
    return lat + north_m / 111_320, lng + east_m / (111_320 * math.cos(math.radians(lat)))


# ---------------------------------------------------------------------------
# Reglas
# ---------------------------------------------------------------------------
def max_devices(superficie_m2: float | None) -> int:
    """Esquinas + 1 cada 15 m de perímetro, suponiendo un predio cuadrado."""
    perimeter = 4 * math.sqrt(superficie_m2 or DEFAULT_AREA_M2)
    return min(MAX_DEVICES, 4 + int(perimeter // METERS_PER_DEVICE))


def plan_b(lat: float, lng: float, plaga: str, superficie_m2: float | None, existentes: list[dict]) -> list[dict]:
    """Plan B por reglas: un cuadrado de la superficie indicada alrededor del
    centro, con un dispositivo en cada esquina y el resto repartido en los lados."""
    tipo = PLAN_B_TYPE.get(plaga, "trampa_pegamento")
    half = math.sqrt(superficie_m2 or DEFAULT_AREA_M2) / 2
    corners = [(-half, half), (half, half), (half, -half), (-half, -half)]  # NO, NE, SE, SO
    total = max_devices(superficie_m2)

    points = list(corners)
    extras = total - 4
    for side in range(4):
        # Reparte los extras entre los 4 lados, en orden.
        per_side = extras // 4 + (1 if side < extras % 4 else 0)
        (x1, y1), (x2, y2) = corners[side], corners[(side + 1) % 4]
        for i in range(1, per_side + 1):
            t = i / (per_side + 1)
            points.append((x1 + (x2 - x1) * t, y1 + (y2 - y1) * t))

    candidates = [{"tipo": tipo, **dict(zip(("lat", "lng"), _offset(lat, lng, x, y)))} for x, y in points]
    return _drop_close(candidates, existentes)[: max(0, total - len(existentes))]


def _drop_close(candidates: list[dict], existentes: list[dict]) -> list[dict]:
    """Descarta los que quedan a menos de 3 m de otro (ya instalado o ya aceptado)."""
    kept: list[dict] = []
    for device in candidates:
        others = existentes + kept
        if all(
            distance_meters(device["lat"], device["lng"], o["lat"], o["lng"]) >= MIN_SEPARATION_METERS
            for o in others
        ):
            kept.append(device)
    return kept


def validate_devices(
    result: dict,
    lat: float,
    lng: float,
    superficie_m2: float | None,
    existentes: list[dict],
    zoom: int = ZOOM,
) -> tuple[list[dict], list[str]]:
    """Aplica las validaciones de la sección 3 del diseño. Devuelve los
    dispositivos válidos (tipo, lat, lng) y las advertencias de la IA."""
    raw = result.get("dispositivos")
    raw = raw if isinstance(raw, list) else []
    # Primero los de mayor confianza: si sobran, se descartan los más dudosos.
    raw = sorted(
        (d for d in raw if isinstance(d, dict)),
        key=lambda d: d.get("confianza") if isinstance(d.get("confianza"), (int, float)) else 0,
        reverse=True,
    )

    candidates = []
    for device in raw:
        tipo, x, y = device.get("tipo"), device.get("x"), device.get("y")
        if tipo not in VALID_TYPES:
            continue
        if not all(isinstance(v, (int, float)) and 0 <= v < IMAGE_SIZE for v in (x, y)):
            continue
        d_lat, d_lng = pixel_to_latlng(x, y, lat, lng, zoom)
        if distance_meters(lat, lng, d_lat, d_lng) > MAX_DISTANCE_METERS:
            continue
        candidates.append({"tipo": tipo, "lat": d_lat, "lng": d_lng})

    devices = _drop_close(candidates, existentes)[: max(0, max_devices(superficie_m2) - len(existentes))]
    if len(devices) < len(raw):
        logger.info("Croquis IA: %d de %d dispositivos pasaron las validaciones", len(devices), len(raw))

    warnings = result.get("advertencias")
    warnings = [w.strip() for w in warnings if isinstance(w, str) and w.strip()] if isinstance(warnings, list) else []
    return devices, warnings


# ---------------------------------------------------------------------------
# Llamadas externas
# ---------------------------------------------------------------------------
def esri_image_url(lat: float, lng: float, zoom: int = ESRI_ZOOM) -> str:
    """Foto de Esri equivalente a la de Google: mismo centro, zoom y tamaño.
    Se pide el rectángulo en metros de Web Mercator que cubre la imagen."""
    x = EARTH_RADIUS_M * math.radians(lng)
    y = EARTH_RADIUS_M * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    meters_per_px = 2 * math.pi * EARTH_RADIUS_M / (TILE_SIZE * 2 ** zoom)
    half = IMAGE_SIZE / 2 * meters_per_px
    params = {
        "bbox": f"{x - half:.2f},{y - half:.2f},{x + half:.2f},{y + half:.2f}",
        "bboxSR": 3857,
        "imageSR": 3857,
        "size": f"{IMAGE_SIZE},{IMAGE_SIZE}",
        "format": "jpg",
        "f": "image",
    }
    return f"{ESRI_EXPORT_URL}?{urlencode(params)}"


def meters_per_pixel(lat: float, zoom: int) -> float:
    """Metros reales que mide un píxel de la imagen a esa latitud."""
    return 156_543.03 * math.cos(math.radians(lat)) / 2 ** zoom


def predio_radius_px(superficie_m2: float | None, lat: float, zoom: int) -> int:
    """Radio del predio en píxeles, suponiéndolo cuadrado (media diagonal) más
    5 m de margen porque la coordenada geocodificada puede no caer en su centro."""
    half_diagonal = math.sqrt(superficie_m2 or DEFAULT_AREA_M2) * math.sqrt(2) / 2
    return round((half_diagonal + 5) / meters_per_pixel(lat, zoom))


def image_zoom() -> int:
    """Zoom de la foto según el proveedor que se va a usar."""
    return ZOOM if settings.google_maps_api_key else ESRI_ZOOM


def static_map_url(lat: float, lng: float, with_key: bool = False) -> str:
    """URL de la foto satelital (Google si hay clave; si no, Esri). La versión
    sin clave es la que se guarda en croquis.imagen_satelital_url: la clave del
    backend no debe salir de aquí."""
    if not settings.google_maps_api_key:
        return esri_image_url(lat, lng)
    params = {
        "center": f"{lat:.6f},{lng:.6f}",
        "zoom": ZOOM,
        "size": f"{IMAGE_SIZE}x{IMAGE_SIZE}",
        "maptype": "satellite",
    }
    if with_key:
        params["key"] = settings.google_maps_api_key
    return f"{STATIC_MAP_URL}?{urlencode(params)}"


def _fetch_image(http: httpx.Client, lat: float, lng: float) -> tuple[bytes, str]:
    response = http.get(static_map_url(lat, lng, with_key=True), timeout=10)
    response.raise_for_status()
    mime = response.headers.get("content-type", "image/png").split(";")[0]
    if not mime.startswith("image/"):
        raise ValueError(f"El proveedor de mapas no devolvió una imagen ({mime})")
    return response.content, mime


def _ask_openai(
    http: httpx.Client,
    image: bytes,
    mime: str,
    contexto: dict,
    existentes_px: list[dict],
) -> dict:
    description = (
        f"Tipo de recinto: {contexto['tipo_recinto']}. Plaga objetivo: {contexto['plaga']}. "
        f"Superficie aproximada: {contexto.get('superficie_m2') or 'no indicada'} m². "
        f"Máximo de dispositivos nuevos: {contexto['maximo']}. "
        f"Escala de la imagen: {contexto['metros_por_pixel']:.2f} m por píxel. "
        f"Radio aproximado del predio desde el centro: {contexto['radio_px']} píxeles. "
        f"Notas del operador: {contexto.get('notas') or 'sin notas'}. "
        f"Dispositivos ya instalados (no repetir): {json.dumps(existentes_px, ensure_ascii=False) if existentes_px else 'ninguno'}."
    )
    payload = {
        "model": settings.openai_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": description},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{base64.b64encode(image).decode()}"},
                    },
                ],
            },
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    response = http.post(OPENAI_URL, json=payload, headers=headers, timeout=60)
    response.raise_for_status()
    data = response.json()
    if usage := data.get("usage"):
        logger.info("Croquis IA: tokens entrada=%s salida=%s", usage.get("prompt_tokens"), usage.get("completion_tokens"))
    return _extract_json(data["choices"][0]["message"]["content"])


def sugerir_dispositivos(
    lat: float,
    lng: float,
    contexto: dict,
    existentes: list[dict] | None = None,
    http: httpx.Client | None = None,
) -> Sugerencia:
    """Propone dispositivos para el predio en (lat, lng). Nunca lanza
    excepciones por fallas externas: ante cualquier problema usa el plan B.

    contexto: tipo_recinto, plaga, superficie_m2 (opcional), notas (opcional).
    existentes: dispositivos que siguen instalados, como {tipo, lat, lng}.
    `http` permite inyectar un cliente simulado en las pruebas."""
    existentes = existentes or []
    superficie = contexto.get("superficie_m2")
    if len(existentes) >= max_devices(superficie):
        return Sugerencia(
            dispositivos=[],
            advertencias=["El croquis anterior ya tiene la cantidad máxima de dispositivos para esta superficie."],
            origen="reglas",
        )

    def fallback(reason: str, image_url: str | None = None) -> Sugerencia:
        devices = plan_b(lat, lng, contexto["plaga"], superficie, existentes)
        return Sugerencia(
            dispositivos=devices,
            advertencias=[f"Sugerencia por reglas, no por IA: {reason}. Revisa cada ubicación en terreno."],
            imagen_satelital_url=image_url,
            origen="reglas",
        )

    zoom = image_zoom()
    own_http = http is None
    http = http or httpx.Client()
    try:
        try:
            image, mime = _fetch_image(http, lat, lng)
        except Exception as exc:
            logger.warning("No se pudo descargar la foto satelital (%s, %s): %s", lat, lng, describe_error(exc))
            return fallback("no se pudo descargar la foto satelital")

        image_url = static_map_url(lat, lng)
        if not settings.openai_api_key:
            return fallback("no hay clave de OpenAI", image_url)

        existentes_px = [
            {"tipo": d["tipo"], **dict(zip(("x", "y"), (round(v) for v in latlng_to_pixel(d["lat"], d["lng"], lat, lng, zoom))))}
            for d in existentes
        ]
        try:
            result = _ask_openai(
                http,
                image,
                mime,
                {
                    **contexto,
                    "maximo": max_devices(superficie) - len(existentes),
                    "metros_por_pixel": meters_per_pixel(lat, zoom),
                    "radio_px": predio_radius_px(superficie, lat, zoom),
                },
                existentes_px,
            )
        except Exception:
            logger.exception("Falló la IA del croquis")
            return fallback("la IA no respondió", image_url)
    finally:
        if own_http:
            http.close()

    devices, warnings = validate_devices(result, lat, lng, superficie, existentes, zoom)
    if not devices:
        return fallback("la IA no propuso ninguna ubicación válida", image_url)

    resumen = result.get("resumen")
    return Sugerencia(
        dispositivos=devices,
        advertencias=warnings,
        resumen=resumen.strip() if isinstance(resumen, str) and resumen.strip() else None,
        imagen_satelital_url=image_url,
    )
