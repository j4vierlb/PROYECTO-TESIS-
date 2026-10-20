"""FastAPI + autenticación real + PostGIS aislado, con rollback por prueba.

Activar explícitamente PANEL_TEST_DATABASE_URL apuntando a panel_regression.
Sin esa variable se omiten estos casos. No se cambian routers ni esquemas.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest
from datetime import date, datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.main import app
from panel_fixture import CLIENT_ID, EMAIL, OPERATOR_ID, OTHER_CLIENT_ID, PASSWORD, seed, test_engine


@unittest.skipUnless(os.getenv('PANEL_TEST_DATABASE_URL'), 'Falta PANEL_TEST_DATABASE_URL de una base aislada')
class PanelPostgisTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = test_engine()

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    def setUp(self):
        self.enterContext(patch.multiple(settings, killbichos_open_time='08:00', killbichos_close_time='18:00', killbichos_operating_days='0,1,2,3,4,5'))
        self.connection = self.engine.connect()
        self.transaction = self.connection.begin()
        self.db = Session(bind=self.connection, join_transaction_mode='create_savepoint')
        self.addCleanup(self.cleanup_database)
        seed(self.db)
        self.previous_overrides = app.dependency_overrides.copy()
        # Solo se cambia la conexión. JWT, roles, routers, validación y SQL son reales.
        app.dependency_overrides[get_db] = lambda: self.db
        self.addCleanup(self.restore_overrides)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        response = self.client.post('/auth/login', json=dict(usuario=EMAIL, clave=PASSWORD))
        self.assertEqual(response.status_code, 200)
        self.client.headers['Authorization'] = f"Bearer {response.json()['access_token']}"

    def restore_overrides(self):
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)

    def cleanup_database(self):
        self.db.close()
        self.transaction.rollback()
        self.connection.close()

    def frontend_payload(self, wall_time, operator=''):
        utility = Path(__file__).resolve().parents[2] / 'frontend/src/panel-utils.js'
        script = f"import {{visitPayload}} from {json.dumps(utility.as_uri())}; console.log(JSON.stringify(visitPayload(JSON.parse(process.argv[1]))))"
        form = dict(cliente_id=CLIENT_ID, operador_id=operator, fecha_hora=wall_time)
        output = subprocess.run([shutil.which('node') or 'node', '--input-type=module', '-e', script, json.dumps(form)],
                                check=True, capture_output=True, text=True, timeout=15)
        return json.loads(output.stdout)

    def create_visit(self, wall_time='2026-09-29T10:00', operator=''):
        payload = self.frontend_payload(wall_time, operator)
        response = self.client.post('/panel/visitas', json=payload)
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def saved_visit(self, visit):
        return self.db.execute(text('SELECT operador_id, fecha_hora FROM visitas WHERE id = :id'),
                               dict(id=visit['id'])).mappings().one()

    def test_cliente_whatsapp_sin_ubicacion_se_lista_y_edita_sin_inventar_coordenadas(self):
        response = self.client.get('/clientes')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertIsNone(response.json()[0]['lat'])
        response = self.client.patch(f'/clientes/{CLIENT_ID}', json=dict(
            nombre='Cliente editado QA', direccion=None, lat=None, lng=None))
        self.assertEqual(response.status_code, 200, response.text)
        persisted = self.db.execute(text('SELECT nombre, direccion, ubicacion FROM clientes WHERE id = :id'),
                                    dict(id=CLIENT_ID)).mappings().one()
        self.assertEqual(persisted['nombre'], 'Cliente editado QA')
        self.assertIsNone(persisted['direccion'])
        self.assertIsNone(persisted['ubicacion'])

    def test_cliente_con_coordenadas_cero_roundtrip_postgis(self):
        response = self.client.post('/clientes', json=dict(
            nombre='Coordenadas cero QA', telefono_whatsapp='+00000000003', direccion='Dirección QA', lat=0, lng=0))
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()['lat'], 0)
        self.assertEqual(response.json()['lng'], 0)

    def test_sin_asignar_se_guarda_null_y_reaparece_en_la_agenda(self):
        visit = self.create_visit()
        self.assertIsNone(visit['operador_id'])
        self.assertIsNone(visit['operador'])
        self.assertIsNone(self.saved_visit(visit)['operador_id'])
        agenda = self.client.get('/panel/visitas?fecha=2026-09-29')
        self.assertEqual(agenda.status_code, 200)
        self.assertEqual(agenda.json()[0]['id'], visit['id'])
        self.assertIsNone(agenda.json()[0]['cliente']['lat'])

    def test_hora_de_verano_10_chile_persiste_13_utc(self):
        visit = self.create_visit()
        self.assertEqual(self.saved_visit(visit)['fecha_hora'], datetime(2026, 9, 29, 13, tzinfo=timezone.utc))

    def test_hora_de_invierno_10_chile_persiste_14_utc(self):
        visit = self.create_visit('2026-07-15T10:00')
        self.assertEqual(self.saved_visit(visit)['fecha_hora'], datetime(2026, 7, 15, 14, tzinfo=timezone.utc))

    def test_2330_chile_se_guarda_en_utc_del_dia_siguiente_sin_cambiar_dia_agenda(self):
        # Este caso de zona horaria configura atención nocturna explícitamente.
        with patch.multiple(settings, killbichos_open_time='00:00', killbichos_close_time='23:59'):
            visit = self.create_visit('2026-09-29T23:30')
        self.assertEqual(self.saved_visit(visit)['fecha_hora'], datetime(2026, 9, 30, 2, 30, tzinfo=timezone.utc))
        self.assertEqual(self.client.get('/panel/visitas?fecha=2026-09-29').json()[0]['id'], visit['id'])
        self.assertEqual(self.client.get('/panel/visitas?fecha=2026-09-30').json(), [])

    def test_operador_asignado_y_filtro(self):
        assigned = self.create_visit(operator=OPERATOR_ID)
        self.create_visit('2026-09-29T11:00')
        response = self.client.get(f'/panel/visitas?fecha=2026-09-29&operador_id={OPERATOR_ID}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual([v['id'] for v in response.json()], [assigned['id']])
        self.assertEqual(response.json()[0]['operador']['nombre'], 'Operador QA')

    def test_operador_vacio_es_rechazado_sin_guardar_visita(self):
        payload = self.frontend_payload('2026-09-29T10:00')
        payload['operador_id'] = ''
        self.assertEqual(self.client.post('/panel/visitas', json=payload).status_code, 422)
        self.assertEqual(self.db.execute(text('SELECT count(*) FROM visitas')).scalar_one(), 0)

    def test_estadisticas_cuentan_hoy_segun_chile(self):
        with patch.multiple(settings, killbichos_open_time='00:00', killbichos_close_time='23:59'):
            self.create_visit('2026-09-29T23:30')
            self.create_visit('2026-09-30T00:30')
        with patch('app.routers.panel.hoy_chile', return_value=date(2026, 9, 29)):
            response = self.client.get('/panel/stats')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), dict(clientes=1, visitas_hoy=1, pendientes=2))

    def test_sin_token_no_se_puede_entrar_al_panel(self):
        del self.client.headers['Authorization']
        self.assertEqual(self.client.get('/clientes').status_code, 401)

    def test_no_se_puede_agendar_cliente_de_otra_empresa(self):
        payload = self.frontend_payload('2026-09-29T10:00')
        payload['cliente_id'] = OTHER_CLIENT_ID
        self.assertEqual(self.client.post('/panel/visitas', json=payload).status_code, 404)
        self.assertEqual(self.db.execute(text('SELECT count(*) FROM visitas')).scalar_one(), 0)

    def test_reprogramacion_real_cambia_agenda_estado_y_operador(self):
        visit = self.create_visit()
        body = self.frontend_payload('2026-07-15T11:00', OPERATOR_ID)
        del body['cliente_id']
        response = self.client.patch(f"/panel/visitas/{visit['id']}", json={**body, 'notas': 'Reprogramada QA'})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['estado'], 'reagendada')
        self.assertEqual(response.json()['operador']['id'], OPERATOR_ID)
        self.assertEqual(self.saved_visit(visit)['fecha_hora'], datetime(2026, 7, 15, 15, tzinfo=timezone.utc))
        self.assertEqual(self.client.get('/panel/visitas?fecha=2026-09-29').json(), [])
        self.assertEqual(self.client.get('/panel/visitas?fecha=2026-07-15').json()[0]['id'], visit['id'])

    def test_asignar_y_desasignar_visita_existente(self):
        visit = self.create_visit()
        url = f"/panel/visitas/{visit['id']}"
        self.assertEqual(self.client.patch(url, json=dict(operador_id=OPERATOR_ID)).status_code, 200)
        self.assertEqual(str(self.saved_visit(visit)['operador_id']), OPERATOR_ID)
        response = self.client.patch(url, json=dict(operador_id=None))
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIsNone(self.saved_visit(visit)['operador_id'])

    def test_bloquea_choques_y_permite_separacion_exacta_de_una_hora(self):
        self.create_visit(operator=OPERATOR_ID)
        response = self.client.post('/panel/visitas', json=self.frontend_payload('2026-09-29T10:30', OPERATOR_ID))
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(self.db.execute(text('SELECT count(*) FROM visitas')).scalar_one(), 1)
        self.create_visit('2026-09-29T11:00', OPERATOR_ID)

    def test_reprogramacion_conflictiva_no_altera_la_visita(self):
        self.create_visit(operator=OPERATOR_ID)
        later = self.create_visit('2026-09-29T12:00', OPERATOR_ID)
        response = self.client.patch(f"/panel/visitas/{later['id']}", json=dict(fecha_hora='2026-09-29T13:30:00Z'))
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(self.saved_visit(later)['fecha_hora'], datetime(2026, 9, 29, 15, tzinfo=timezone.utc))

    def test_no_permite_domingo_cierre_ni_madrugada_sin_asignar(self):
        for wall in ('2026-09-27T10:00', '2026-09-29T18:00', '2026-09-29T07:59'):
            response = self.client.post('/panel/visitas', json=self.frontend_payload(wall))
            self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.db.execute(text('SELECT count(*) FROM visitas')).scalar_one(), 0)

    def test_cancelar_con_croquis_conserva_visita_croquis_y_trampas(self):
        visit = self.create_visit(operator=OPERATOR_ID)
        croquis_id = self.db.execute(text('INSERT INTO croquis(cliente_id, visita_id, operador_id) VALUES (:client, :visit, :operator) RETURNING id'), dict(client=CLIENT_ID, visit=visit['id'], operator=OPERATOR_ID)).scalar_one()
        self.db.execute(text("INSERT INTO dispositivos_trampa(croquis_id, codigo, tipo, ubicacion) VALUES (:id, 'QA-01', 'cebadero', ST_SetSRID(ST_MakePoint(-70.6, -33.4), 4326)::geography)"), dict(id=croquis_id))
        response = self.client.delete(f"/panel/visitas/{visit['id']}")
        self.assertEqual(response.status_code, 204, response.text)
        self.assertEqual(self.db.execute(text('SELECT estado FROM visitas WHERE id = :id'), dict(id=visit['id'])).scalar_one(), 'cancelada')
        self.assertEqual(self.db.execute(text('SELECT count(*) FROM croquis WHERE id = :id'), dict(id=croquis_id)).scalar_one(), 1)
        self.assertEqual(self.db.execute(text('SELECT count(*) FROM dispositivos_trampa WHERE croquis_id = :id'), dict(id=croquis_id)).scalar_one(), 1)

    def test_cancelar_libera_el_horario(self):
        visit = self.create_visit(operator=OPERATOR_ID)
        self.assertEqual(self.client.patch(f"/panel/visitas/{visit['id']}", json=dict(estado='cancelada')).status_code, 200)
        self.create_visit(operator=OPERATOR_ID)

    def test_cliente_con_visitas_no_se_elimina(self):
        self.create_visit()
        response = self.client.delete(f'/clientes/{CLIENT_ID}')
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(self.db.execute(text('SELECT count(*) FROM clientes WHERE id = :id'), dict(id=CLIENT_ID)).scalar_one(), 1)

    def test_cliente_sin_visitas_se_puede_eliminar(self):
        self.assertEqual(self.client.delete(f'/clientes/{CLIENT_ID}').status_code, 204)
        self.assertEqual(self.db.execute(text('SELECT count(*) FROM clientes WHERE id = :id'), dict(id=CLIENT_ID)).scalar_one(), 0)

    def test_crear_sin_coordenadas_y_telefono_duplicado_controlado(self):
        body = dict(nombre='Sin GPS QA', direccion='Macul 1234', telefono_whatsapp='+00000000004')
        response = self.client.post('/clientes', json=body)
        self.assertEqual(response.status_code, 201, response.text)
        self.assertIsNone(response.json()['lat'])
        self.assertIsNone(response.json()['lng'])
        response = self.client.post('/clientes', json=body)
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(self.client.get('/clientes').status_code, 200)

    def test_telefono_duplicado_al_editar_no_cambia_cliente(self):
        self.client.post('/clientes', json=dict(nombre='Otro QA', direccion='Macul 1234', telefono_whatsapp='+00000000004'))
        response = self.client.patch(f'/clientes/{CLIENT_ID}', json=dict(telefono_whatsapp='+00000000004'))
        self.assertEqual(response.status_code, 409, response.text)
        actual = self.db.execute(text('SELECT telefono_whatsapp FROM clientes WHERE id = :id'), dict(id=CLIENT_ID)).scalar_one()
        self.assertEqual(actual, '+00000000001')

    def test_no_puede_modificar_visita_de_otra_empresa(self):
        row_id = self.db.execute(text("INSERT INTO visitas(empresa_id, cliente_id, fecha_hora) SELECT empresa_id, id, '2026-09-29T13:00:00Z'::timestamptz FROM clientes WHERE id = :id RETURNING id"), dict(id=OTHER_CLIENT_ID)).scalar_one()
        response = self.client.patch(f'/panel/visitas/{row_id}', json=dict(notas='No guardar'))
        self.assertEqual(response.status_code, 404)
        self.assertIsNone(self.db.execute(text('SELECT notas FROM visitas WHERE id = :id'), dict(id=row_id)).scalar_one())

    def test_no_asigna_operador_inactivo(self):
        visit = self.create_visit()
        self.db.execute(text('UPDATE operadores SET activo = FALSE WHERE id = :id'), dict(id=OPERATOR_ID))
        response = self.client.patch(f"/panel/visitas/{visit['id']}", json=dict(operador_id=OPERATOR_ID))
        self.assertEqual(response.status_code, 400, response.text)
        self.assertIsNone(self.saved_visit(visit)['operador_id'])

    def test_no_asigna_operador_de_otra_empresa(self):
        visit = self.create_visit()
        other_operator = '88888888-8888-8888-8888-888888888888'
        self.db.execute(text("""INSERT INTO operadores(id, empresa_id, nombre, email, password_hash)
                                SELECT :id, c.empresa_id, 'Operador externo QA', 'externo@panel.test', o.password_hash
                                FROM clientes c CROSS JOIN operadores o
                                WHERE c.id = :client AND o.id = :operator"""), dict(id=other_operator, client=OTHER_CLIENT_ID, operator=OPERATOR_ID))
        response = self.client.patch(f"/panel/visitas/{visit['id']}", json=dict(operador_id=other_operator))
        self.assertEqual(response.status_code, 400, response.text)
        self.assertIsNone(self.saved_visit(visit)['operador_id'])

    def test_tecnico_no_puede_editar_por_el_endpoint_del_panel(self):
        visit = self.create_visit()
        login = self.client.post('/auth/login', json=dict(usuario='operador@panel.test', clave=PASSWORD))
        self.assertEqual(login.status_code, 200)
        headers = {'Authorization': f"Bearer {login.json()['access_token']}"}
        self.assertEqual(self.client.patch(f"/panel/visitas/{visit['id']}", json=dict(notas='No guardar'), headers=headers).status_code, 403)


if __name__ == '__main__':
    unittest.main()
