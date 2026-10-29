"""GET /operadores/me/visitas-proximas: visitas pendientes de los próximos días.

Pruebas de integración con FastAPI + login real + PostGIS aislado. Cada prueba
corre dentro de una transacción que se deshace al final (rollback).

Activar con CROQUIS_TEST_DATABASE_URL apuntando a una base llamada
croquis_regression (con schema.sql). Sin esa variable se omiten. Nunca usar la
base de trabajo.
"""
import os
import unittest
from datetime import datetime, time, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.database import get_db
from app.main import app
from app.security import hash_password
from app.zona_horaria import ZONA_CHILE, hoy_chile

EMPRESA = '10000000-0000-0000-0000-000000000001'
ADMIN = '20000000-0000-0000-0000-000000000001'
OPERADOR = '30000000-0000-0000-0000-000000000001'
OTRO_OPERADOR = '30000000-0000-0000-0000-000000000002'
CLIENTE = '40000000-0000-0000-0000-000000000001'
CLAVE = 'ProximasDemo123!'


def _engine():
    engine = create_engine(os.environ['CROQUIS_TEST_DATABASE_URL'])
    if engine.url.database != 'croquis_regression':
        engine.dispose()
        raise RuntimeError('La prueba solo admite la base aislada croquis_regression')
    return engine


def _dia(dias, hora=10):
    """Instante a las `hora` (hora de Chile) de hoy + `dias`."""
    return datetime.combine(hoy_chile() + timedelta(days=dias), time(hora, 0), tzinfo=ZONA_CHILE)


def _seed(db):
    clave = hash_password(CLAVE)
    db.execute(text("INSERT INTO empresas(id, nombre) VALUES (:e, 'Empresa QA')"), dict(e=EMPRESA))
    db.execute(text("""INSERT INTO usuarios(id, empresa_id, nombre, email, password_hash, rol)
                       VALUES (:a, :e, 'Admin QA', 'admin@proximas.test', :c, 'admin')"""),
               dict(a=ADMIN, e=EMPRESA, c=clave))
    db.execute(text("""INSERT INTO operadores(id, empresa_id, nombre, email, password_hash) VALUES
                       (:a, :e, 'Operador QA', 'op@proximas.test', :c),
                       (:b, :e, 'Otro operador', 'otro@proximas.test', :c)"""),
               dict(a=OPERADOR, b=OTRO_OPERADOR, e=EMPRESA, c=clave))
    db.execute(text("""INSERT INTO clientes(id, empresa_id, nombre, telefono_whatsapp, direccion, ubicacion)
                       VALUES (:id, :e, 'Cliente QA', '+00000000010', 'Av. QA 123, Macul',
                               ST_SetSRID(ST_MakePoint(-70.5989, -33.4869), 4326)::geography)"""),
               dict(id=CLIENTE, e=EMPRESA))


@unittest.skipUnless(os.getenv('CROQUIS_TEST_DATABASE_URL'), 'Falta CROQUIS_TEST_DATABASE_URL de una base aislada')
class VisitasProximasTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = _engine()

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    def setUp(self):
        self.connection = self.engine.connect()
        self.transaction = self.connection.begin()
        self.db = Session(bind=self.connection, join_transaction_mode='create_savepoint')
        self.addCleanup(self._cleanup_db)
        _seed(self.db)
        app.dependency_overrides[get_db] = lambda: self.db
        self.addCleanup(app.dependency_overrides.clear)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def _cleanup_db(self):
        self.db.close()
        self.transaction.rollback()
        self.connection.close()

    def _visita(self, dias, hora=10, estado='agendada', operador=OPERADOR):
        return self.db.execute(
            text("""INSERT INTO visitas(empresa_id, cliente_id, operador_id, fecha_hora, estado, origen_agendamiento)
                    VALUES (:e, :c, :o, :f, :estado, 'manual') RETURNING id"""),
            dict(e=EMPRESA, c=CLIENTE, o=operador, f=_dia(dias, hora), estado=estado),
        ).scalar_one()

    def _headers(self, usuario='op@proximas.test'):
        response = self.client.post('/auth/login', json=dict(usuario=usuario, clave=CLAVE))
        self.assertEqual(response.status_code, 200, response.text)
        return {'Authorization': f"Bearer {response.json()['access_token']}"}

    def _proximas(self, params=None, usuario='op@proximas.test'):
        return self.client.get('/operadores/me/visitas-proximas', params=params, headers=self._headers(usuario))

    def test_devuelve_las_visitas_futuras_de_la_mas_cercana_a_la_mas_lejana(self):
        lejana = self._visita(5)
        cercana_tarde = self._visita(1, hora=15)
        cercana_manana = self._visita(1, hora=9)
        response = self._proximas()
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual([v['id'] for v in response.json()],
                         [str(cercana_manana), str(cercana_tarde), str(lejana)])

    def test_trae_los_datos_del_cliente_igual_que_la_agenda_de_hoy(self):
        self._visita(2)
        visita = self._proximas().json()[0]
        self.assertEqual(visita['cliente']['nombre'], 'Cliente QA')
        self.assertEqual(visita['cliente']['direccion'], 'Av. QA 123, Macul')
        self.assertAlmostEqual(visita['cliente']['lat'], -33.4869, places=4)
        self.assertEqual(visita['estado'], 'agendada')

    def test_no_incluye_hoy_ni_el_pasado(self):
        self._visita(0, hora=23)
        self._visita(-1)
        self._visita(-30, estado='completada')
        self.assertEqual(self._proximas().json(), [])

    def test_hoy_a_ultima_hora_de_chile_sigue_siendo_hoy(self):
        # 23:30 hora de Chile ya es "mañana" en UTC; no debe contarse como próxima.
        self._visita(0, hora=23)
        self.assertEqual(self._proximas().json(), [])

    def test_solo_las_pendientes_agendada_y_reagendada(self):
        agendada = self._visita(2, estado='agendada')
        reagendada = self._visita(3, estado='reagendada')
        self._visita(2, estado='cancelada')
        self._visita(2, estado='completada')
        self._visita(2, estado='en_curso')
        ids = {v['id'] for v in self._proximas().json()}
        self.assertEqual(ids, {str(agendada), str(reagendada)})

    def test_solo_las_del_operador_que_pregunta(self):
        propia = self._visita(2)
        self._visita(2, operador=OTRO_OPERADOR)
        self.assertEqual([v['id'] for v in self._proximas().json()], [str(propia)])
        otro = self._proximas(usuario='otro@proximas.test').json()
        self.assertEqual(len(otro), 1)
        self.assertNotEqual(otro[0]['id'], str(propia))

    def test_ventana_de_14_dias_por_defecto(self):
        dentro = self._visita(14)
        self._visita(15)
        self.assertEqual([v['id'] for v in self._proximas().json()], [str(dentro)])

    def test_parametro_dias_amplia_o_reduce_la_ventana(self):
        manana = self._visita(1)
        en_20 = self._visita(20)
        self.assertEqual([v['id'] for v in self._proximas({'dias': 1}).json()], [str(manana)])
        self.assertEqual([v['id'] for v in self._proximas({'dias': 20}).json()], [str(manana), str(en_20)])

    def test_dias_fuera_de_rango_se_rechaza(self):
        for dias in (0, -1, 61):
            self.assertEqual(self._proximas({'dias': dias}).status_code, 422, dias)

    def test_exige_sesion_y_un_operador(self):
        self.assertEqual(self.client.get('/operadores/me/visitas-proximas').status_code, 401)
        self.assertEqual(self._proximas(usuario='admin@proximas.test').status_code, 403)

    def test_sin_visitas_responde_lista_vacia(self):
        response = self._proximas()
        self.assertEqual((response.status_code, response.json()), (200, []))


if __name__ == '__main__':
    unittest.main()
