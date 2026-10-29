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

# Plaza de Macul, en Santiago.
MACUL = (-33.4870, -70.5990)
# Viña del Mar y Concepción: Kill Bichos agenda en cualquier lugar de Chile.
VINA = (-33.0153, -71.5500)
CONCEPCION = (-36.8270, -73.0500)


def _result(lat, lng, location_type="ROOFTOP", partial=False, comuna="Macul", pais="CL", extra=None):
    """Resultado de Google con los componentes que usa la validación: país y
    comuna/ciudad (en Chile Google los informa como administrative_area_level_3
    y locality)."""
    components = [
        {"long_name": "Chile", "short_name": pais, "types": ["country", "political"]},
        {"long_name": comuna, "short_name": comuna, "types": ["administrative_area_level_3", "political"]},
    ]
    components.extend(extra or [])
    result = {
        "geometry": {"location": {"lat": lat, "lng": lng}, "location_type": location_type},
        "address_components": components,
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

    def test_viña_del_mar_se_ubica(self):
        http = _client({"status": "OK", "results": [_result(*VINA, comuna="Viña del Mar")]})
        self.assertEqual(
            geocodificar("Av. Libertad 1000, Viña del Mar", http), (*VINA, "ROOFTOP")
        )

    def test_concepcion_se_ubica(self):
        http = _client({"status": "OK", "results": [_result(*CONCEPCION, comuna="Concepción")]})
        self.assertEqual(
            geocodificar("Barros Arana 600, Concepción", http), (*CONCEPCION, "ROOFTOP")
        )

    def test_la_comuna_se_compara_sin_tildes_ni_mayusculas(self):
        http = _client({"status": "OK", "results": [_result(*VINA, comuna="Viña del Mar")]})
        self.assertEqual(
            geocodificar("av libertad 1000, VINA DEL MAR", http), (*VINA, "ROOFTOP")
        )

    def test_comuna_o_ciudad_tambien_se_acepta_como_locality(self):
        extra = [{"long_name": "Santiago", "short_name": "Santiago", "types": ["locality", "political"]}]
        http = _client({"status": "OK", "results": [_result(*MACUL, comuna="Macul", extra=extra)]})
        # Google informa locality=Santiago y comuna=Macul; basta con nombrar una.
        self.assertEqual(geocodificar("Av. Macul 1234, Santiago", http), (*MACUL, "ROOFTOP"))

    def test_sin_comuna_en_la_direccion_no_se_guarda(self):
        # Google ubicó la calle en alguna ciudad, pero el cliente no dijo cuál:
        # el pin podría quedar en un lugar equivocado.
        http = _client({"status": "OK", "results": [_result(*VINA, comuna="Viña del Mar")]})
        self.assertIsNone(geocodificar("Viana 1233", http))

    def test_comuna_distinta_a_la_escrita_no_se_guarda(self):
        http = _client({"status": "OK", "results": [_result(*VINA, comuna="Viña del Mar")]})
        self.assertIsNone(geocodificar("Av. Libertad 1000, Quilpué", http))

    def test_resultado_sin_comuna_informada_no_se_guarda(self):
        result = _result(*MACUL)
        result["address_components"] = [
            c for c in result["address_components"] if "country" in c["types"]
        ]
        http = _client({"status": "OK", "results": [result]})
        self.assertIsNone(geocodificar("Av. Macul 1234, Macul", http))

    def test_fuera_de_chile_no_se_guarda(self):
        http = _client({"status": "OK", "results": [_result(-34.60, -58.38, comuna="Buenos Aires", pais="AR")]})
        self.assertIsNone(geocodificar("Av. Corrientes 1000, Buenos Aires", http))

    def test_sin_pais_informado_no_se_guarda(self):
        result = _result(*MACUL)
        result["address_components"] = [
            c for c in result["address_components"] if "country" not in c["types"]
        ]
        http = _client({"status": "OK", "results": [result]})
        self.assertIsNone(geocodificar("Av. Macul 1234, Macul", http))

    def test_error_http_no_lanza_excepcion(self):
        http = _client({}, status_code=500)
        self.assertIsNone(geocodificar("Av. Macul 1234, Macul", http))

    def test_envia_la_direccion_tal_como_la_escribio_el_cliente(self):
        # Antes se le agregaba ", Región Metropolitana", lo que confundía a Google
        # con direcciones de otras ciudades.
        seen = []
        http = _client({"status": "ZERO_RESULTS", "results": []}, seen=seen)
        geocodificar("Av. Libertad 1000, Viña del Mar", http)
        self.assertEqual(seen[0]["address"], "Av. Libertad 1000, Viña del Mar")
        self.assertEqual(seen[0]["components"], "country:CL")


if __name__ == "__main__":
    unittest.main()
