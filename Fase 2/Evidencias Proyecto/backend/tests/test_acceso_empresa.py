"""Aislamiento entre empresas en visitas y croquis.

Un admin o coordinador solo ve las visitas (y croquis) de SU empresa; un
operador, solo las suyas. Antes de esta corrección, GET /visitas/{id},
PATCH /visitas/{id} y GET /croquis/{visita_id} no comparaban la empresa.

Integración con FastAPI + login real + PostGIS aislado, con rollback por
prueba. Usa la misma base aislada que test_croquis_terreno.py
(CROQUIS_TEST_DATABASE_URL apuntando a croquis_regression); sin esa
variable se omite.
"""
import os
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.database import get_db
from app.main import app
from app.security import hash_password

EMPRESA_A = 'a0000000-0000-0000-0000-00000000000a'
EMPRESA_B = 'b0000000-0000-0000-0000-00000000000b'
OPERADOR_A = 'a0000000-0000-0000-0000-0000000000a1'
OPERADOR_B = 'b0000000-0000-0000-0000-0000000000b1'
VISITA_A = 'a0000000-0000-0000-0000-0000000000f1'
VISITA_B = 'b0000000-0000-0000-0000-0000000000f1'
CLAVE = 'EmpresaDemo123!'
# Quién inicia sesión en cada caso: (email, empresa).
USUARIOS = {
    'admin_a': 'admin@a.test', 'coord_a': 'coord@a.test', 'op_a': 'op@a.test',
    'admin_b': 'admin@b.test', 'coord_b': 'coord@b.test', 'op_b': 'op@b.test',
}


def _engine():
    engine = create_engine(os.environ['CROQUIS_TEST_DATABASE_URL'])
    if engine.url.database != 'croquis_regression':
        engine.dispose()
        raise RuntimeError('La prueba solo admite la base aislada croquis_regression')
    return engine


def _seed(db):
    """Dos empresas iguales: cada una con admin, coordinador, operador,
    cliente, una visita agendada y su croquis con una trampa."""
    clave = hash_password(CLAVE)
    for letra, empresa, operador, visita in (('a', EMPRESA_A, OPERADOR_A, VISITA_A),
                                             ('b', EMPRESA_B, OPERADOR_B, VISITA_B)):
        db.execute(text('INSERT INTO empresas(id, nombre) VALUES (:id, :nombre)'),
                   dict(id=empresa, nombre=f'Empresa {letra.upper()}'))
        db.execute(text("""INSERT INTO usuarios(empresa_id, nombre, email, password_hash, rol) VALUES
                           (:e, 'Admin', :admin, :c, 'admin'), (:e, 'Coordinador', :coord, :c, 'coordinador')"""),
                   dict(e=empresa, admin=f'admin@{letra}.test', coord=f'coord@{letra}.test', c=clave))
        db.execute(text("INSERT INTO operadores(id, empresa_id, nombre, email, password_hash) VALUES (:id, :e, 'Operador', :email, :c)"),
                   dict(id=operador, e=empresa, email=f'op@{letra}.test', c=clave))
        cliente = db.execute(text("""INSERT INTO clientes(empresa_id, nombre, telefono_whatsapp, direccion, ubicacion)
                                     VALUES (:e, 'Cliente', :tel, 'Calle 1',
                                             ST_SetSRID(ST_MakePoint(-70.5989, -33.4869), 4326)::geography)
                                     RETURNING id"""),
                             dict(e=empresa, tel=f'+0000000001{letra}')).scalar_one()
        db.execute(text("""INSERT INTO visitas(id, empresa_id, cliente_id, operador_id, fecha_hora, estado, origen_agendamiento, notas)
                           VALUES (:id, :e, :c, :op, now(), 'agendada', 'manual', 'Nota original')"""),
                   dict(id=visita, e=empresa, c=cliente, op=operador))
        croquis = db.execute(text("""INSERT INTO croquis(cliente_id, visita_id, operador_id) VALUES (:c, :v, :op) RETURNING id"""),
                             dict(c=cliente, v=visita, op=operador)).scalar_one()
        db.execute(text("""INSERT INTO dispositivos_trampa(croquis_id, codigo, tipo, ubicacion)
                           VALUES (:k, 'T-01', 'cebadero', ST_SetSRID(ST_MakePoint(-70.5989, -33.4869), 4326)::geography)"""),
                   dict(k=croquis))


@unittest.skipUnless(os.getenv('CROQUIS_TEST_DATABASE_URL'), 'Falta CROQUIS_TEST_DATABASE_URL de una base aislada')
class AccesoEntreEmpresasTest(unittest.TestCase):
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
        self._tokens = {}

    def _cleanup_db(self):
        self.db.close()
        self.transaction.rollback()
        self.connection.close()

    def h(self, quien):
        """Header Authorization con un token real del usuario indicado."""
        if quien not in self._tokens:
            response = self.client.post('/auth/login', json=dict(usuario=USUARIOS[quien], clave=CLAVE))
            self.assertEqual(response.status_code, 200, response.text)
            self._tokens[quien] = {'Authorization': f"Bearer {response.json()['access_token']}"}
        return self._tokens[quien]

    def test_admin_y_coordinador_no_ven_visitas_ni_croquis_de_otra_empresa(self):
        # En las dos direcciones: A -> B y B -> A.
        for quien, visita_ajena in (('admin_a', VISITA_B), ('coord_a', VISITA_B),
                                    ('admin_b', VISITA_A), ('coord_b', VISITA_A)):
            for url in (f'/visitas/{visita_ajena}', f'/croquis/{visita_ajena}'):
                with self.subTest(quien=quien, url=url):
                    response = self.client.get(url, headers=self.h(quien))
                    self.assertEqual(response.status_code, 403, response.text)
                    self.assertNotIn('Cliente', response.text)  # no se filtra ningún dato

    def test_admin_y_coordinador_si_ven_las_de_su_empresa(self):
        for quien, visita_propia in (('admin_a', VISITA_A), ('coord_a', VISITA_A),
                                     ('admin_b', VISITA_B), ('coord_b', VISITA_B)):
            for url in (f'/visitas/{visita_propia}', f'/croquis/{visita_propia}'):
                with self.subTest(quien=quien, url=url):
                    self.assertEqual(self.client.get(url, headers=self.h(quien)).status_code, 200)

    def test_admin_de_otra_empresa_no_puede_modificar_la_visita(self):
        response = self.client.patch(f'/visitas/{VISITA_A}', headers=self.h('admin_b'),
                                     json=dict(estado='cancelada', notas='Cambio ajeno'))
        self.assertEqual(response.status_code, 403, response.text)
        fila = self.db.execute(text('SELECT estado, notas FROM visitas WHERE id = :id'), dict(id=VISITA_A)).mappings().one()
        self.assertEqual((fila['estado'], fila['notas']), ('agendada', 'Nota original'))

    def test_operador_sigue_limitado_a_sus_propias_visitas(self):
        self.assertEqual(self.client.get(f'/visitas/{VISITA_A}', headers=self.h('op_a')).status_code, 200)
        self.assertEqual(self.client.get(f'/croquis/{VISITA_A}', headers=self.h('op_a')).status_code, 200)
        for url in (f'/visitas/{VISITA_A}', f'/croquis/{VISITA_A}'):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url, headers=self.h('op_b')).status_code, 403)

    def test_operador_de_otra_empresa_no_crea_croquis_ni_agrega_trampas(self):
        self.assertEqual(self.client.post(f'/croquis/{VISITA_A}', headers=self.h('op_b')).status_code, 403)
        agregar = self.client.post(f'/croquis/{VISITA_A}/dispositivos', headers=self.h('op_b'),
                                   json=dict(tipo='cebadero', lat=-33.48, lng=-70.59))
        self.assertEqual(agregar.status_code, 403)

    def test_visita_inexistente_sigue_respondiendo_404(self):
        inexistente = '00000000-0000-0000-0000-000000000000'
        self.assertEqual(self.client.get(f'/visitas/{inexistente}', headers=self.h('admin_a')).status_code, 404)
        self.assertEqual(self.client.get(f'/croquis/{inexistente}', headers=self.h('admin_a')).status_code, 404)


if __name__ == '__main__':
    unittest.main()
