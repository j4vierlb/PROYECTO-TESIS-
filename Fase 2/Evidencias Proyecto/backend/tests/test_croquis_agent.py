# =============================================================================
# tests/test_croquis_agent.py — Sugerencia de trampas (app/ai/croquis_agent.py)
# -----------------------------------------------------------------------------
# Se corre desde la carpeta backend con:
#   python -m unittest discover tests
# No llama a Google ni a OpenAI: las respuestas se simulan con httpx.MockTransport.
# =============================================================================

import json
import unittest
from unittest.mock import patch

import httpx

from app.ai import croquis_agent
from app.ai.croquis_agent import (
    IMAGE_SIZE,
    latlng_to_pixel,
    max_devices,
    pixel_to_latlng,
    plan_b,
    sugerir_dispositivos,
    validate_devices,
)
from app.geocoding import distance_meters

LAT, LNG = -33.4870, -70.5990  # Macul
CENTER = IMAGE_SIZE / 2
CONTEXTO = {"tipo_recinto": "casa", "plaga": "roedores", "superficie_m2": 200, "notas": None}


def _device(tipo="cebadero", x=CENTER + 40, y=CENTER, confianza=0.8):
    return {"tipo": tipo, "x": x, "y": y, "zona": "patio", "motivo": "muro", "confianza": confianza}


class GeometriaTest(unittest.TestCase):
    def test_centro_de_la_imagen_es_el_predio(self):
        lat, lng = pixel_to_latlng(CENTER, CENTER, LAT, LNG)
        self.assertAlmostEqual(lat, LAT, places=7)
        self.assertAlmostEqual(lng, LNG, places=7)

    def test_ida_y_vuelta(self):
        lat, lng = pixel_to_latlng(100, 500, LAT, LNG)
        x, y = latlng_to_pixel(lat, lng, LAT, LNG)
        self.assertAlmostEqual(x, 100, places=3)
        self.assertAlmostEqual(y, 500, places=3)

    def test_orientacion_y_escala(self):
        # 100 px a la derecha = al este; 100 px hacia abajo = al sur. En zoom 20
        # cada píxel mide ~0,12 m en Santiago, así que 100 px ≈ 12,5 m.
        lat_e, lng_e = pixel_to_latlng(CENTER + 100, CENTER, LAT, LNG)
        lat_s, _ = pixel_to_latlng(CENTER, CENTER + 100, LAT, LNG)
        self.assertGreater(lng_e, LNG)
        self.assertLess(lat_s, LAT)
        self.assertAlmostEqual(distance_meters(LAT, LNG, lat_e, lng_e), 12.5, delta=0.5)


class ReglasTest(unittest.TestCase):
    def test_max_dispositivos(self):
        self.assertEqual(max_devices(200), 7)        # perímetro ~56,6 m → 4 + 3
        self.assertEqual(max_devices(None), 7)       # sin superficie: 200 m²
        self.assertEqual(max_devices(1_000_000), 30)  # tope

    def test_plan_b_esquinas_y_perimetro(self):
        devices = plan_b(LAT, LNG, "roedores", 400, [])  # cuadrado de 20 m
        self.assertEqual(len(devices), max_devices(400))
        self.assertTrue(all(d["tipo"] == "cebadero" for d in devices))
        # Las esquinas quedan a ~14,1 m del centro (media diagonal).
        corner = distance_meters(LAT, LNG, devices[0]["lat"], devices[0]["lng"])
        self.assertAlmostEqual(corner, 14.14, delta=0.3)

    def test_plan_b_tipo_segun_plaga(self):
        self.assertEqual(plan_b(LAT, LNG, "moscas", 200, [])[0]["tipo"], "trampa_luz")
        self.assertEqual(plan_b(LAT, LNG, "cucarachas", 200, [])[0]["tipo"], "trampa_pegamento")

    def test_plan_b_no_repite_trampas_instaladas(self):
        first = plan_b(LAT, LNG, "roedores", 200, [])
        again = plan_b(LAT, LNG, "roedores", 200, first[:2])
        self.assertEqual(len(again), len(first) - 2)


class ValidacionTest(unittest.TestCase):
    def test_dispositivo_valido(self):
        devices, _ = validate_devices({"dispositivos": [_device()]}, LAT, LNG, 200, [])
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0]["tipo"], "cebadero")

    def test_descarta_tipo_invalido_y_pixeles_fuera(self):
        raw = [_device(tipo="veneno"), _device(x=700), _device(y=-1), _device(x="100")]
        devices, _ = validate_devices({"dispositivos": raw}, LAT, LNG, 200, [])
        self.assertEqual(devices, [])

    def test_descarta_lejos_del_predio(self):
        # La esquina de la imagen está a ~56 m del centro: pasa con el límite
        # de 60 m, pero no si el límite fuera 50 m.
        corner = {"dispositivos": [_device(x=0, y=0)]}
        self.assertEqual(len(validate_devices(corner, LAT, LNG, 200, [])[0]), 1)
        with patch.object(croquis_agent, "MAX_DISTANCE_METERS", 50):
            self.assertEqual(validate_devices(corner, LAT, LNG, 200, [])[0], [])

    def test_descarta_duplicados_a_menos_de_3_m(self):
        raw = [_device(x=400), _device(x=410)]  # 10 px ≈ 1,2 m
        devices, _ = validate_devices({"dispositivos": raw}, LAT, LNG, 200, [])
        self.assertEqual(len(devices), 1)

    def test_respeta_el_maximo_y_prefiere_mayor_confianza(self):
        raw = [_device(x=40 * i, y=100, confianza=i / 20) for i in range(1, 16)]
        devices, _ = validate_devices({"dispositivos": raw}, LAT, LNG, 200, [])
        self.assertEqual(len(devices), max_devices(200))
        best = pixel_to_latlng(40 * 15, 100, LAT, LNG)
        self.assertAlmostEqual(devices[0]["lng"], best[1], places=7)

    def test_descuenta_las_trampas_instaladas_del_maximo(self):
        existentes = plan_b(LAT, LNG, "roedores", 200, [])[:5]
        raw = [_device(x=40 * i, y=40) for i in range(1, 10)]
        devices, _ = validate_devices({"dispositivos": raw}, LAT, LNG, 200, existentes)
        self.assertEqual(len(devices), max_devices(200) - 5)

    def test_json_raro_no_falla(self):
        self.assertEqual(validate_devices({"dispositivos": "nada"}, LAT, LNG, 200, []), ([], []))
        self.assertEqual(validate_devices({}, LAT, LNG, 200, []), ([], []))


def _http(openai_content=None, map_status=200, openai_status=200, calls=None):
    """Simula Static Maps (devuelve una imagen) y OpenAI (devuelve openai_content)."""

    def handler(request: httpx.Request) -> httpx.Response:
        if calls is not None:
            calls.append(request)
        if "staticmap" in request.url.path:
            return httpx.Response(map_status, content=b"\x89PNG fake", headers={"content-type": "image/png"})
        body = {"choices": [{"message": {"content": json.dumps(openai_content)}}], "usage": {}}
        return httpx.Response(openai_status, json=body)

    return httpx.Client(transport=httpx.MockTransport(handler))


class SugerirDispositivosTest(unittest.TestCase):
    def setUp(self):
        for name, value in (("google_maps_api_key", "clave-google"), ("openai_api_key", "clave-openai")):
            patcher = patch.object(croquis_agent.settings, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_flujo_completo_con_ia(self):
        calls = []
        answer = {"resumen": "Casa con patio.", "dispositivos": [_device()], "advertencias": ["No se ve la bodega."]}
        result = sugerir_dispositivos(LAT, LNG, CONTEXTO, http=_http(answer, calls=calls))

        self.assertEqual(result.origen, "ia")
        self.assertEqual(len(result.dispositivos), 1)
        self.assertEqual(result.resumen, "Casa con patio.")
        self.assertEqual(result.advertencias, ["No se ve la bodega."])
        # La URL que se guarda no lleva la clave del backend.
        self.assertNotIn("clave-google", result.imagen_satelital_url)
        self.assertIn("maptype=satellite", result.imagen_satelital_url)
        # A OpenAI se le manda la imagen en base64, no la URL con la clave.
        sent = json.loads(calls[1].content)
        image_url = sent["messages"][1]["content"][1]["image_url"]["url"]
        self.assertTrue(image_url.startswith("data:image/png;base64,"))
        self.assertNotIn("clave-google", calls[1].content.decode())

    def test_sin_clave_de_google_usa_reglas_sin_llamar_a_nadie(self):
        calls = []
        with patch.object(croquis_agent.settings, "google_maps_api_key", ""):
            result = sugerir_dispositivos(LAT, LNG, CONTEXTO, http=_http(calls=calls))
        self.assertEqual(result.origen, "reglas")
        self.assertEqual(len(result.dispositivos), max_devices(200))
        self.assertIsNone(result.imagen_satelital_url)
        self.assertEqual(calls, [])

    def test_falla_la_foto_usa_reglas(self):
        result = sugerir_dispositivos(LAT, LNG, CONTEXTO, http=_http(map_status=403))
        self.assertEqual(result.origen, "reglas")
        self.assertIsNone(result.imagen_satelital_url)

    def test_falla_openai_usa_reglas_pero_guarda_la_foto(self):
        result = sugerir_dispositivos(LAT, LNG, CONTEXTO, http=_http(openai_status=500))
        self.assertEqual(result.origen, "reglas")
        self.assertIsNotNone(result.imagen_satelital_url)
        self.assertIn("la IA no respondió", result.advertencias[0])

    def test_ia_sin_ubicaciones_validas_usa_reglas(self):
        answer = {"resumen": "x", "dispositivos": [_device(tipo="veneno")], "advertencias": []}
        result = sugerir_dispositivos(LAT, LNG, CONTEXTO, http=_http(answer))
        self.assertEqual(result.origen, "reglas")
        self.assertGreater(len(result.dispositivos), 0)

    def test_croquis_anterior_lleno_no_agrega_nada(self):
        calls = []
        existentes = plan_b(LAT, LNG, "roedores", 200, [])
        result = sugerir_dispositivos(LAT, LNG, CONTEXTO, existentes, http=_http(calls=calls))
        self.assertEqual(result.dispositivos, [])
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
