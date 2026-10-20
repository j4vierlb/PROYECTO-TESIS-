# =============================================================================
# tests/test_geocoding.py — Dirección → coordenadas (app/geocoding.py)
# -----------------------------------------------------------------------------
# Se corre desde la carpeta backend con:
#   python -m unittest discover tests
# No llama a Google: las respuestas se simulan con httpx.MockTransport.
# =============================================================================

import unittest
from unittest.mock import patch

import httpx

from app import geocoding
from app.geocoding import geocodificar

# Plaza de Macul, dentro de la Región Metropolitana.
MACUL = (-33.4870, -70.5990)


RM = "Región Metropolitana de Santiago"


def _result(lat, lng, location_type="ROOFTOP", partial=False, region=RM):
    result = {
        "geometry": {"location": {"lat": lat, "lng": lng}, "location_type": location_type},
        "address_components": [{"long_name": region, "types": ["administrative_area_level_1", "political"]}],
    }
    if partial:
        result["partial_match"] = True
    return result


def _client(payload, status_code=200, seen=None):
    """Cliente httpx que siempre responde `payload` y guarda los parámetros pedidos."""

    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(dict(request.url.params))
        return httpx.Response(status_code, json=payload)

    return httpx.Client(transport=httpx.MockTransport(handler))


class GeocodificarTest(unittest.TestCase):
    def setUp(self):
        patcher = patch.object(geocoding.settings, "google_maps_api_key", "clave-de-prueba")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_direccion_precisa_devuelve_coordenadas(self):
        http = _client({"status": "OK", "results": [_result(*MACUL)]})
        self.assertEqual(geocodificar("Av. Macul 1234, Macul", http), (*MACUL, "ROOFTOP"))

    def test_sin_clave_no_llama_a_google(self):
        seen = []
        http = _client({"status": "OK", "results": [_result(*MACUL)]}, seen=seen)
        with patch.object(geocoding.settings, "google_maps_api_key", ""):
            self.assertIsNone(geocodificar("Av. Macul 1234, Macul", http))
        self.assertEqual(seen, [])

    def test_direccion_vacia(self):
        self.assertIsNone(geocodificar("   "))
        self.assertIsNone(geocodificar(None))

    def test_sin_resultados(self):
        http = _client({"status": "ZERO_RESULTS", "results": []})
        self.assertIsNone(geocodificar("asdfgh", http))

    def test_ubicacion_aproximada_se_descarta(self):
        http = _client({"status": "OK", "results": [_result(*MACUL, location_type="APPROXIMATE")]})
        self.assertIsNone(geocodificar("Macul", http))

    def test_coincidencia_parcial_se_descarta(self):
        http = _client({"status": "OK", "results": [_result(*MACUL, partial=True)]})
        self.assertIsNone(geocodificar("Av. Macul 99999", http))

    def test_resultados_lejanos_entre_si_son_ambiguos(self):
        # Mismo nombre de calle en Macul y en Maipú (~15 km).
        http = _client({"status": "OK", "results": [_result(*MACUL), _result(-33.5110, -70.7580)]})
        self.assertIsNone(geocodificar("Los Aromos 100", http))

    def test_resultados_cercanos_usan_el_primero(self):
        # Segundo resultado a ~30 m: es el mismo predio.
        http = _client({"status": "OK", "results": [_result(*MACUL), _result(-33.4872, -70.5992)]})
        self.assertEqual(geocodificar("Av. Macul 1234, Macul", http), (*MACUL, "ROOFTOP"))

    def test_punto_fuera_del_rectangulo(self):
        # Concepción.
        http = _client({"status": "OK", "results": [_result(-36.8270, -73.0500, region=RM)]})
        self.assertIsNone(geocodificar("Av. Brasil 1000", http))

    def test_valparaiso_cae_en_el_rectangulo_pero_se_descarta(self):
        http = _client({"status": "OK", "results": [_result(-33.0458, -71.6197, region="Valparaíso")]})
        self.assertIsNone(geocodificar("Av. Brasil 1000", http))

    def test_sin_region_informada_se_descarta(self):
        result = _result(*MACUL)
        del result["address_components"]
        http = _client({"status": "OK", "results": [result]})
        self.assertIsNone(geocodificar("Av. Macul 1234, Macul", http))

    def test_error_http_no_lanza_excepcion(self):
        http = _client({}, status_code=500)
        self.assertIsNone(geocodificar("Av. Macul 1234, Macul", http))

    def test_agrega_region_si_no_hay_comuna(self):
        seen = []
        http = _client({"status": "ZERO_RESULTS", "results": []}, seen=seen)
        geocodificar("Los Aromos 100", http)
        self.assertEqual(seen[0]["address"], "Los Aromos 100, Región Metropolitana")
        self.assertEqual(seen[0]["components"], "country:CL")

    def test_no_agrega_region_si_trae_comuna_con_tildes(self):
        seen = []
        http = _client({"status": "ZERO_RESULTS", "results": []}, seen=seen)
        geocodificar("Irarrázaval 3000, Ñuñoa", http)
        self.assertEqual(seen[0]["address"], "Irarrázaval 3000, Ñuñoa")


if __name__ == "__main__":
    unittest.main()
