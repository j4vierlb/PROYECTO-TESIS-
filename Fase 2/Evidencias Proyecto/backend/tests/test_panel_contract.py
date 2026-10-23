"""Contrato HTTP del panel con DB simulada; NO es una prueba de PostgreSQL.

Se ejecuta desde backend: python -m unittest discover tests -v
No toca datos reales ni llama a WhatsApp/Twilio.
"""
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.database import get_db
from app.dependencies import require_web_user
from app.main import app
from app.schemas import CurrentUser
from app.config import settings

CLIENT_ID = '33333333-3333-3333-3333-333333333333'
OPERATOR_ID = '44444444-4444-4444-4444-444444444444'
VISIT_ID = '55555555-5555-5555-5555-555555555555'
COMPANY_ID = '11111111-1111-1111-1111-111111111111'


class PanelContractTest(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.multiple(settings, killbichos_open_time='08:00', killbichos_close_time='18:00', killbichos_operating_days='0,1,2,3,4,5'))
        self.conflict = False
        self.operator_exists = True
        self.visit_exists = True
        self.client_row = dict(id=CLIENT_ID, nombre='Cliente WhatsApp', telefono_whatsapp='+56912345678',
                               direccion=None, lat=None, lng=None)
        self.visit_row = dict(id=VISIT_ID, cliente_id=CLIENT_ID, cliente_nombre='Cliente WhatsApp',
                              telefono_whatsapp='+56912345678', direccion=None, lat=None, lng=None,
                              operador_id=None, operador_nombre=None, operador_email=None,
                              fecha_hora=datetime(2026, 9, 29, 13, tzinfo=timezone.utc),
                              estado='agendada', origen_agendamiento='manual', notas=None)
        self.db = MagicMock()
        self.db.execute.side_effect = self.execute
        self.previous_overrides = app.dependency_overrides.copy()
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[require_web_user] = lambda: CurrentUser(
            id='22222222-2222-2222-2222-222222222222', nombre='Admin de prueba', rol='admin', empresa_id=COMPANY_ID)
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)

    def execute(self, statement, params=None):
        sql = str(statement)
        result = MagicMock()
        if 'FROM clientes' in sql:
            result.mappings().first.return_value = self.client_row
            result.mappings().all.return_value = [self.client_row]
        elif 'FROM visitas v' in sql:
            result.mappings().first.return_value = self.visit_row if self.visit_exists else None
            result.mappings().all.return_value = [self.visit_row]
        elif 'FROM visitas' in sql:
            result.first.return_value = (VISIT_ID,) if self.conflict else None
        elif 'INSERT INTO visitas' in sql:
            self.visit_row['fecha_hora'] = params['fecha_hora']
            self.visit_row['operador_id'] = params['operador_id']
            if params['operador_id']:
                self.visit_row.update(operador_nombre='Operador de prueba', operador_email='test@example.invalid')
            result.scalar_one.return_value = VISIT_ID
        elif 'FROM operadores' in sql:
            result.first.return_value = (1,) if self.operator_exists else None
        elif 'UPDATE visitas' in sql:
            self.visit_row.update({k: v for k, v in params.items() if k in self.visit_row and k != 'id'})
            if self.visit_row['operador_id']:
                self.visit_row.update(operador_nombre='Operador de prueba', operador_email='test@example.invalid')
            else:
                self.visit_row.update(operador_nombre=None, operador_email=None)
        elif 'INSERT INTO clientes' in sql:
            self.client_row.update(nombre=params['nombre'], telefono_whatsapp=params['telefono'], direccion=params['direccion'], lat=params['lat'], lng=params['lng'])
            result.scalar_one.return_value = CLIENT_ID
        elif 'UPDATE clientes' in sql:
            self.client_row.update({k: v for k, v in params.items() if k in self.client_row and k != 'id'})
        else:
            self.fail(f'Consulta inesperada en la prueba: {sql}')
        return result

    def visit_body(self, operator=None):
        # Es exactamente el contrato producido por el formulario corregido.
        return dict(cliente_id=CLIENT_ID, operador_id=operator, fecha_hora='2026-09-29T13:00:00.000Z')

    def test_panel_clientes_con_ubicacion_null_devuelve_200(self):
        response = self.client.get('/clientes')
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()[0]['lat'])
        self.assertIsNone(response.json()[0]['lng'])

    def test_agenda_con_cliente_sin_coordenadas_y_sin_operador_devuelve_200(self):
        response = self.client.get('/panel/visitas?fecha=2026-09-29')
        self.assertEqual(response.status_code, 200)
        visit = response.json()[0]
        self.assertIsNone(visit['cliente']['lat'])
        self.assertIsNone(visit['operador_id'])
        self.assertIsNone(visit['operador'])

    def test_sin_asignar_null_devuelve_201_y_conserva_utc(self):
        response = self.client.post('/panel/visitas', json=self.visit_body())
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(response.json()['operador_id'])
        self.assertIsNone(response.json()['operador'])
        self.assertEqual(datetime.fromisoformat(response.json()['fecha_hora']), datetime(2026, 9, 29, 13, tzinfo=timezone.utc))
        insertion = next(call for call in self.db.execute.call_args_list if 'INSERT INTO visitas' in str(call.args[0]))
        self.assertIsNone(insertion.args[1]['operador_id'])
        self.db.commit.assert_called_once()

    def test_uuid_de_operador_devuelve_201(self):
        response = self.client.post('/panel/visitas', json=self.visit_body(OPERATOR_ID))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['operador']['id'], OPERATOR_ID)

    def test_cadena_vacia_reproduce_el_422_que_el_frontend_corrige(self):
        response = self.client.post('/panel/visitas', json=self.visit_body(''))
        self.assertEqual(response.status_code, 422)
        self.db.execute.assert_not_called()

    def test_editar_cliente_sin_coordenadas_conserva_null(self):
        response = self.client.patch(f'/clientes/{CLIENT_ID}', json=dict(
            nombre='Nombre corregido', telefono_whatsapp='+56912345678', direccion=None, lat=None, lng=None))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['nombre'], 'Nombre corregido')
        self.assertIsNone(response.json()['lat'])
        self.assertIsNone(response.json()['lng'])
        update = next(call for call in self.db.execute.call_args_list if 'UPDATE clientes' in str(call.args[0]))
        self.assertIsNone(update.args[1]['lat'])
        self.assertIsNone(update.args[1]['lng'])

    def test_reprogramar_actualiza_fecha_estado_y_operador(self):
        response = self.client.patch(f'/panel/visitas/{VISIT_ID}', json=dict(fecha_hora='2026-07-15T15:00:00Z', operador_id=OPERATOR_ID, notas='Nueva hora'))
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['estado'], 'reagendada')
        self.assertEqual(response.json()['operador_id'], OPERATOR_ID)
        self.assertEqual(datetime.fromisoformat(response.json()['fecha_hora']).hour, 15)

    def test_quitar_operador_no_cambia_fecha_ni_estado(self):
        self.visit_row['operador_id'] = OPERATOR_ID
        response = self.client.patch(f'/panel/visitas/{VISIT_ID}', json=dict(operador_id=None))
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIsNone(response.json()['operador_id'])
        self.assertEqual(response.json()['estado'], 'agendada')

    def test_operador_inactivo_o_externo_es_rechazado(self):
        self.operator_exists = False
        response = self.client.patch(f'/panel/visitas/{VISIT_ID}', json=dict(operador_id=OPERATOR_ID))
        self.assertEqual(response.status_code, 400)
        self.db.commit.assert_not_called()

    def test_conflicto_de_operador_devuelve_409_sin_guardar(self):
        self.conflict = True
        response = self.client.post('/panel/visitas', json=self.visit_body(OPERATOR_ID))
        self.assertEqual(response.status_code, 409)
        self.db.commit.assert_not_called()

    def test_fuera_de_horario_incluso_sin_operador(self):
        for timestamp in ('2026-09-29T10:59:00Z', '2026-09-29T21:00:00Z', '2026-09-27T13:00:00Z'):
            with self.subTest(timestamp=timestamp):
                response = self.client.post('/panel/visitas', json={**self.visit_body(), 'fecha_hora': timestamp})
                self.assertEqual(response.status_code, 422, response.text)
                self.assertIn('Horario de atención', response.json()['detail'])
        self.db.commit.assert_not_called()

    def test_usa_horario_configurado_y_no_horario_fijo(self):
        with patch.multiple(settings, killbichos_open_time='12:00', killbichos_close_time='16:00'):
            self.assertEqual(self.client.post('/panel/visitas', json=self.visit_body()).status_code, 422)
            response = self.client.post('/panel/visitas', json={**self.visit_body(), 'fecha_hora': '2026-09-29T15:00:00Z'})
            self.assertEqual(response.status_code, 201, response.text)

    def test_rechaza_fechas_sin_zona_en_creacion_y_edicion(self):
        self.assertEqual(self.client.post('/panel/visitas', json={**self.visit_body(), 'fecha_hora': '2026-09-29T10:00:00'}).status_code, 422)
        self.assertEqual(self.client.patch(f'/panel/visitas/{VISIT_ID}', json=dict(fecha_hora='2026-09-29T10:00:00')).status_code, 422)
        self.db.execute.assert_not_called()

    def test_fecha_estado_nulos_y_campos_ajenos_son_rechazados(self):
        for body in ({'fecha_hora': None}, {'estado': None}, {'empresa_id': COMPANY_ID}, {'cliente_id': CLIENT_ID}):
            self.assertEqual(self.client.patch(f'/panel/visitas/{VISIT_ID}', json=body).status_code, 422)
        self.db.execute.assert_not_called()

    def test_visita_de_otra_empresa_no_se_modifica(self):
        self.visit_exists = False
        response = self.client.patch(f'/panel/visitas/{VISIT_ID}', json=dict(notas='No guardar'))
        self.assertEqual(response.status_code, 404)
        self.db.commit.assert_not_called()

    def test_no_reprograma_visita_finalizada_pero_permite_notas(self):
        self.visit_row['estado'] = 'completada'
        response = self.client.patch(f'/panel/visitas/{VISIT_ID}', json=dict(fecha_hora='2026-09-29T15:00:00Z'))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.client.patch(f'/panel/visitas/{VISIT_ID}', json=dict(notas='Informe revisado')).status_code, 200)

    def test_cliente_nuevo_admite_ubicacion_vacia(self):
        response = self.client.post('/clientes', json=dict(nombre='Cliente nuevo', telefono_whatsapp='+56912345678', direccion='Macul 1234'))
        self.assertEqual(response.status_code, 201, response.text)
        self.assertIsNone(response.json()['lat'])
        self.assertIsNone(response.json()['lng'])

    def test_coordenadas_incompletas_y_nombre_vacio_son_rechazados(self):
        response = self.client.post('/clientes', json=dict(nombre='Cliente nuevo', telefono_whatsapp='+56912345678', direccion='Macul 1234', lat=-33))
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.client.patch(f'/clientes/{CLIENT_ID}', json=dict(nombre='  ')).status_code, 422)
        self.assertEqual(self.client.patch(f'/clientes/{CLIENT_ID}', json=dict(lat=-33)).status_code, 422)
        self.db.commit.assert_not_called()

    def test_no_amplia_el_contrato_movil(self):
        from app.schemas import VisitUpdate
        self.assertEqual(set(VisitUpdate.model_fields), {'estado', 'notas'})

    def test_reagendada_requiere_una_nueva_fecha(self):
        response = self.client.patch(f'/panel/visitas/{VISIT_ID}', json=dict(estado='reagendada'))
        self.assertEqual(response.status_code, 422, response.text)
        self.db.commit.assert_not_called()


if __name__ == '__main__':
    unittest.main()
