# =============================================================================
# tests/test_zona_horaria.py — "Hoy" se calcula con la hora de Chile
# -----------------------------------------------------------------------------
# Se corre desde la carpeta backend con:
#   python -m unittest discover tests
# No necesita base de datos ni librerías extra (unittest viene con Python).
# =============================================================================

import unittest
from datetime import date, datetime, timezone

from app.zona_horaria import hoy_chile

UTC = timezone.utc


class HoyEnChileTest(unittest.TestCase):
    def test_despues_de_las_21_sigue_siendo_hoy_en_chile(self):
        # 29/09 a las 22:30 en Chile (verano, UTC-3) = 30/09 a la 01:30 UTC.
        # En UTC ya es "mañana", pero para la agenda tiene que seguir siendo 29/09.
        instante = datetime(2026, 9, 30, 1, 30, tzinfo=UTC)
        self.assertEqual(hoy_chile(instante), date(2026, 9, 29))

    def test_ultimo_minuto_del_dia(self):
        # 29/09 a las 23:59 en Chile = 30/09 a las 02:59 UTC.
        instante = datetime(2026, 9, 30, 2, 59, tzinfo=UTC)
        self.assertEqual(hoy_chile(instante), date(2026, 9, 29))

    def test_despues_de_medianoche_cambia_el_dia(self):
        # 30/09 a las 00:30 en Chile = 30/09 a las 03:30 UTC.
        instante = datetime(2026, 9, 30, 3, 30, tzinfo=UTC)
        self.assertEqual(hoy_chile(instante), date(2026, 9, 30))

    def test_horario_de_invierno(self):
        # En invierno Chile es UTC-4: 15/07 a las 21:30 = 16/07 a la 01:30 UTC.
        instante = datetime(2026, 7, 16, 1, 30, tzinfo=UTC)
        self.assertEqual(hoy_chile(instante), date(2026, 7, 15))

    def test_durante_el_dia_coincide_con_utc(self):
        # 29/09 a las 10:00 en Chile = 13:00 UTC del mismo día.
        instante = datetime(2026, 9, 29, 13, 0, tzinfo=UTC)
        self.assertEqual(hoy_chile(instante), date(2026, 9, 29))


if __name__ == "__main__":
    unittest.main()
