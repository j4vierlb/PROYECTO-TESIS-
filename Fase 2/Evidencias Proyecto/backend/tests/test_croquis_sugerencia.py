"""Contrato HTTP de POST /croquis/{visita_id}/sugerencia; NO es una prueba de PostgreSQL.

Se ejecuta desde backend: python -m unittest discover tests -v
Las consultas y la IA se reemplazan por simulaciones (unittest.mock).
"""
import unittest
from unittest.mock import MagicMock, patch
from uuid import UUID

from fastapi.testclient import TestClient

from app.ai.croquis_agent import Sugerencia
from app.database import get_db
from app.dependencies import get_current_user
from app.main import app
from app.routers import croquis as router
from app.schemas import CurrentUser

VISIT_ID = '55555555-5555-5555-5555-555555555555'
CLIENT_ID = '33333333-3333-3333-3333-333333333333'
OPERATOR_ID = '44444444-4444-4444-4444-444444444444'
COMPANY_ID = '11111111-1111-1111-1111-111111111111'
CROQUIS_ID = UUID('66666666-6666-6666-6666-666666666666')
BODY = {'tipo_recinto': 'casa', 'plaga': 'roedores', 'superficie_m2': 200}


def _device(codigo, sugerido=True, confirmado=False, estado='activo', lat=-33.4869, lng=-70.5989):
    return dict(id=f'77777777-7777-7777-7777-7777777777{codigo[-2:]}', codigo=codigo, tipo='cebadero',
                lat=lat, lng=lng, sugerido_por_ia=sugerido, confirmado=confirmado, estado=estado, foto_path=None)


class CroquisSugerenciaTest(unittest.TestCase):
    def setUp(self):
        self.visit = dict(id=UUID(VISIT_ID), cliente_id=UUID(CLIENT_ID), operador_id=UUID(OPERATOR_ID),
                          empresa_id=UUID(COMPANY_ID), estado='agendada', direccion='Av. Macul 1234, Macul',
                          lat=-33.487, lng=-70.599)
        self.suggestion = Sugerencia(dispositivos=[{'tipo': 'cebadero', 'lat': -33.4869, 'lng': -70.5989}],
                                     advertencias=['No se ve la bodega.'], resumen='Casa con patio.',
                                     imagen_satelital_url='https://maps.googleapis.com/maps/api/staticmap?x=1')
        # Antes de la sugerencia el croquis está vacío; después tiene T-01.
        self.devices_before, self.devices_after = [], [_device('T-01')]
        self.mocks = {}
        for name, value in {
            'fetch_visit': self.visit,
            'create_croquis_for_visit': (CROQUIS_ID, True),
            'add_suggested_devices': None,
            'save_client_location': None,
            'geocodificar': None,
            'sugerir_dispositivos': self.suggestion,
            'fetch_croquis_for_visit': dict(id=CROQUIS_ID, cliente_id=CLIENT_ID, version=1,
                                            imagen_satelital_url=self.suggestion.imagen_satelital_url,
                                            sugerido_por_ia=True, validado_por_operador=False),
        }.items():
            patcher = patch.object(router, name, return_value=value)
            self.mocks[name] = patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch.object(router, 'fetch_devices_for_croquis',
                               side_effect=lambda db, _id: (self.devices_before if self.calls() == 1 else self.devices_after))
        self.mocks['fetch_devices_for_croquis'] = patcher.start()
        self.addCleanup(patcher.stop)

        self.user = CurrentUser(id=OPERATOR_ID, nombre='Operador', rol='operador', empresa_id=COMPANY_ID)
        self.previous_overrides = app.dependency_overrides.copy()
        app.dependency_overrides[get_db] = lambda: MagicMock()
        app.dependency_overrides[get_current_user] = lambda: self.user
        self.client = TestClient(app)

    def calls(self):
        return self.mocks['fetch_devices_for_croquis'].call_count

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)

    def post(self, body=BODY):
        return self.client.post(f'/croquis/{VISIT_ID}/sugerencia', json=body)

    def test_agrega_las_trampas_sugeridas(self):
        response = self.post()
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual(data['origen'], 'ia')
        self.assertEqual(data['resumen'], 'Casa con patio.')
        self.assertEqual(data['advertencias'], ['No se ve la bodega.'])
        self.assertEqual(data['dispositivos'][0]['codigo'], 'T-01')
        self.assertFalse(data['dispositivos'][0]['confirmado'])

        lat, lng, contexto, existentes = self.mocks['sugerir_dispositivos'].call_args.args
        self.assertEqual((lat, lng), (-33.487, -70.599))
        self.assertEqual(contexto['plaga'], 'roedores')
        self.assertEqual(existentes, [])
        self.mocks['create_croquis_for_visit'].assert_called_once()
        _, croquis_id, imagen, nuevos = self.mocks['add_suggested_devices'].call_args.args
        self.assertEqual(croquis_id, CROQUIS_ID)
        self.assertEqual(nuevos, self.suggestion.dispositivos)

    def test_informa_a_la_ia_las_trampas_que_ya_estan(self):
        self.devices_before = [_device('T-01', sugerido=False, confirmado=True, lat=-33.4871, lng=-70.5991),
                               _device('T-02', estado='retirado')]
        self.assertEqual(self.post().status_code, 200)
        existentes = self.mocks['sugerir_dispositivos'].call_args.args[3]
        self.assertEqual(existentes, [{'tipo': 'cebadero', 'lat': -33.4871, 'lng': -70.5991}])

    def test_sin_trampas_nuevas_no_inserta_nada(self):
        self.suggestion.dispositivos = []
        self.assertEqual(self.post().status_code, 200)
        self.mocks['add_suggested_devices'].assert_not_called()

    def test_cliente_sin_ubicacion_se_geocodifica(self):
        self.visit.update(lat=None, lng=None)
        self.mocks['geocodificar'].return_value = (-33.48, -70.59, 'ROOFTOP')
        self.assertEqual(self.post().status_code, 200)
        self.mocks['save_client_location'].assert_called_once()
        self.assertEqual(self.mocks['sugerir_dispositivos'].call_args.args[:2], (-33.48, -70.59))

    def test_cliente_sin_ubicacion_ni_direccion_util(self):
        self.visit.update(lat=None, lng=None)
        self.assertEqual(self.post().status_code, 409)
        self.mocks['sugerir_dispositivos'].assert_not_called()
        self.mocks['create_croquis_for_visit'].assert_not_called()

    def test_visita_cerrada(self):
        for estado in ('cancelada', 'completada'):
            self.visit['estado'] = estado
            self.assertEqual(self.post().status_code, 409)
        self.mocks['sugerir_dispositivos'].assert_not_called()

    def test_visita_de_otro_operador(self):
        self.visit['operador_id'] = UUID('99999999-9999-9999-9999-999999999999')
        self.assertEqual(self.post().status_code, 403)
        self.mocks['sugerir_dispositivos'].assert_not_called()

    def test_solo_operadores(self):
        self.user = CurrentUser(id=OPERATOR_ID, nombre='Admin', rol='admin', empresa_id=COMPANY_ID)
        self.assertEqual(self.post().status_code, 403)

    def test_valida_el_body(self):
        self.assertEqual(self.post({'tipo_recinto': 'castillo', 'plaga': 'roedores'}).status_code, 422)
        self.assertEqual(self.post({'tipo_recinto': 'casa', 'plaga': 'roedores', 'superficie_m2': -5}).status_code, 422)


if __name__ == '__main__':
    unittest.main()
