"""Gestión de técnicos desde el panel: FastAPI + autenticación real + PostgreSQL aislado.

Requiere PANEL_TEST_DATABASE_URL apuntando a panel_regression (con schema.sql
actual). Cada prueba se deshace al final con rollback.
"""
import os
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.main import app
from app.security import verify_password
from panel_fixture import COMPANY_ID, EMAIL, OPERATOR_ID, OTHER_COMPANY_ID, PASSWORD, PASSWORD_HASH, seed, test_engine

OTHER_OPERATOR_ID = '88888888-8888-8888-8888-888888888888'
COORDINATOR_EMAIL = 'coordinador@panel.test'
NEW_PASSWORD = 'ClaveTecnico2026!'


@unittest.skipUnless(os.getenv('PANEL_TEST_DATABASE_URL'), 'Falta PANEL_TEST_DATABASE_URL de una base aislada')
class OperadoresPanelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = test_engine()

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    def setUp(self):
        self.connection = self.engine.connect()
        self.transaction = self.connection.begin()
        self.db = Session(bind=self.connection, join_transaction_mode='create_savepoint')
        self.addCleanup(self.cleanup_database)
        seed(self.db)
        self.db.execute(text("""INSERT INTO operadores(id, empresa_id, nombre, email, password_hash)
                                VALUES (:id, :company, 'Técnico externo QA', 'externo@otra.test', :password)"""),
                        dict(id=OTHER_OPERATOR_ID, company=OTHER_COMPANY_ID, password=PASSWORD_HASH))
        self.db.execute(text("""INSERT INTO usuarios(empresa_id, nombre, email, password_hash, rol)
                                VALUES (:company, 'Coordinador QA', :email, :password, 'coordinador')"""),
                        dict(company=COMPANY_ID, email=COORDINATOR_EMAIL, password=PASSWORD_HASH))
        previous = app.dependency_overrides.copy()
        self.addCleanup(lambda: (app.dependency_overrides.clear(), app.dependency_overrides.update(previous)))
        app.dependency_overrides[get_db] = lambda: self.db
        self.client = self.enterContext(TestClient(app))
        self.admin = self.headers(EMAIL, PASSWORD)

    def cleanup_database(self):
        self.db.close()
        self.transaction.rollback()
        self.connection.close()

    def login(self, email, password):
        return self.client.post('/auth/login', json=dict(usuario=email, clave=password))

    def headers(self, email, password):
        response = self.login(email, password)
        self.assertEqual(response.status_code, 200, response.text)
        return {'Authorization': f"Bearer {response.json()['access_token']}"}

    def create(self, **changes):
        body = dict(nombre='  Técnico Nuevo QA ', email=' Nuevo.Tecnico@Panel.TEST ', telefono='+56911112222', clave=NEW_PASSWORD)
        body.update(changes)
        return self.client.post('/panel/operadores', json=body, headers=self.admin)

    def test_crear_tecnico_guarda_clave_cifrada_y_puede_iniciar_sesion(self):
        response = self.create()
        self.assertEqual(response.status_code, 201, response.text)
        created = response.json()
        self.assertEqual(set(created), {'id', 'nombre', 'email', 'telefono', 'activo'})
        self.assertEqual((created['nombre'], created['email'], created['activo']),
                         ('Técnico Nuevo QA', 'nuevo.tecnico@panel.test', True))
        stored = self.db.execute(text('SELECT empresa_id, password_hash FROM operadores WHERE id = :id'),
                                 dict(id=created['id'])).mappings().one()
        self.assertEqual(str(stored['empresa_id']), COMPANY_ID)
        self.assertNotEqual(stored['password_hash'], NEW_PASSWORD)
        self.assertTrue(verify_password(NEW_PASSWORD, stored['password_hash']))
        tecnico = self.headers('nuevo.tecnico@panel.test', NEW_PASSWORD)
        self.assertEqual(self.client.get('/operadores/me/visitas-hoy', headers=tecnico).status_code, 200)
        listed = self.client.get('/panel/operadores', headers=self.admin).json()
        self.assertIn(created['id'], [item['id'] for item in listed])

    def test_telefono_es_opcional_y_vacio_se_guarda_como_nulo(self):
        self.assertIsNone(self.create(telefono=None).json()['telefono'])
        self.assertIsNone(self.create(email='otro@panel.test', telefono='   ').json()['telefono'])

    def test_validaciones_de_clave_y_datos(self):
        for changes in (dict(clave='corta123'), dict(clave='x' * 73), dict(clave='ñ' * 40),
                        dict(clave='ClaveConNulo\x00123'), dict(email='sin-arroba'), dict(nombre=' ')):
            with self.subTest(changes=changes):
                self.assertEqual(self.create(**changes).status_code, 422)
        self.assertEqual(self.create(clave='x' * 72).status_code, 201)

    def test_correo_repetido_en_operadores_o_usuarios_responde_409(self):
        self.assertEqual(self.create().status_code, 201)
        for email in ('NUEVO.tecnico@panel.test', 'operador@panel.test', 'externo@otra.test', EMAIL, COORDINATOR_EMAIL):
            with self.subTest(email=email):
                response = self.create(email=email)
                self.assertEqual(response.status_code, 409)
                self.assertEqual(response.json()['detail'], 'Ya existe una cuenta con ese correo')

    def test_otra_empresa_no_se_lista_ni_se_puede_editar(self):
        listed = self.client.get('/panel/operadores?incluir_inactivos=true', headers=self.admin).json()
        self.assertEqual([item['id'] for item in listed], [OPERATOR_ID])
        response = self.client.patch(f'/panel/operadores/{OTHER_OPERATOR_ID}', json=dict(activo=False), headers=self.admin)
        self.assertEqual(response.status_code, 404)
        still_active = self.db.execute(text('SELECT activo FROM operadores WHERE id = :id'),
                                       dict(id=OTHER_OPERATOR_ID)).scalar_one()
        self.assertTrue(still_active)
        self.assertEqual(self.client.patch('/panel/operadores/99999999-9999-9999-9999-999999999999',
                                           json=dict(nombre='Nadie'), headers=self.admin).status_code, 404)

    def test_desactivar_bloquea_login_y_token_y_reactivar_lo_devuelve(self):
        tecnico = self.headers('operador@panel.test', PASSWORD)
        response = self.client.patch(f'/panel/operadores/{OPERATOR_ID}', json=dict(activo=False), headers=self.admin)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertFalse(response.json()['activo'])
        self.assertEqual(self.login('operador@panel.test', PASSWORD).status_code, 401)
        self.assertEqual(self.client.get('/operadores/me/visitas-hoy', headers=tecnico).status_code, 401)
        # Sin el parámetro, la lista de los desplegables sigue mostrando solo activos.
        self.assertEqual(self.client.get('/panel/operadores', headers=self.admin).json(), [])
        listed = self.client.get('/panel/operadores?incluir_inactivos=true', headers=self.admin).json()
        self.assertEqual([(item['id'], item['activo']) for item in listed], [(OPERATOR_ID, False)])
        # No se borra: la fila sigue en la base para conservar el historial.
        self.assertEqual(self.db.execute(text('SELECT count(*) FROM operadores WHERE id = :id'),
                                         dict(id=OPERATOR_ID)).scalar_one(), 1)
        response = self.client.patch(f'/panel/operadores/{OPERATOR_ID}', json=dict(activo=True), headers=self.admin)
        self.assertTrue(response.json()['activo'])
        self.assertEqual(self.login('operador@panel.test', PASSWORD).status_code, 200)

    def test_cambiar_clave_cierra_sesiones_abiertas(self):
        login = self.login('operador@panel.test', PASSWORD).json()
        old_access = {'Authorization': f"Bearer {login['access_token']}"}
        response = self.client.patch(f'/panel/operadores/{OPERATOR_ID}', json=dict(clave=NEW_PASSWORD), headers=self.admin)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertNotIn('clave', response.json())
        self.assertEqual(self.client.get('/operadores/me/visitas-hoy', headers=old_access).status_code, 401)
        self.assertEqual(self.client.post('/auth/refresh', json=dict(refresh_token=login['refresh_token'])).status_code, 401)
        self.assertEqual(self.login('operador@panel.test', PASSWORD).status_code, 401)
        nueva = self.headers('operador@panel.test', NEW_PASSWORD)
        self.assertEqual(self.client.get('/operadores/me/visitas-hoy', headers=nueva).status_code, 200)

    def test_editar_nombre_y_borrar_telefono_sin_tocar_la_clave(self):
        self.client.patch(f'/panel/operadores/{OPERATOR_ID}', json=dict(telefono='+56933334444'), headers=self.admin)
        response = self.client.patch(f'/panel/operadores/{OPERATOR_ID}',
                                     json=dict(nombre='  Operador Editado ', telefono=None), headers=self.admin)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual((response.json()['nombre'], response.json()['telefono']), ('Operador Editado', None))
        self.assertEqual(self.login('operador@panel.test', PASSWORD).status_code, 200)
        for body in (dict(nombre=None), dict(activo=None), dict(clave=None), dict(clave='corta')):
            with self.subTest(body=body):
                self.assertEqual(self.client.patch(f'/panel/operadores/{OPERATOR_ID}', json=body,
                                                   headers=self.admin).status_code, 422)

    def test_tecnico_y_coordinador_no_gestionan_tecnicos(self):
        tecnico = self.headers('operador@panel.test', PASSWORD)
        coordinador = self.headers(COORDINATOR_EMAIL, PASSWORD)
        for headers, list_status in ((tecnico, 403), (coordinador, 200)):
            with self.subTest(headers=headers):
                self.assertEqual(self.client.get('/panel/operadores', headers=headers).status_code, list_status)
                self.assertEqual(self.client.get('/panel/operadores?incluir_inactivos=true', headers=headers).status_code, 403)
                self.assertEqual(self.client.post('/panel/operadores', headers=headers, json=dict(
                    nombre='Intruso', email='intruso@panel.test', clave=NEW_PASSWORD)).status_code, 403)
                self.assertEqual(self.client.patch(f'/panel/operadores/{OPERATOR_ID}', headers=headers,
                                                   json=dict(activo=False)).status_code, 403)
        self.assertEqual(self.client.get('/panel/operadores').status_code, 401)
        self.assertTrue(self.db.execute(text('SELECT activo FROM operadores WHERE id = :id'),
                                        dict(id=OPERATOR_ID)).scalar_one())
