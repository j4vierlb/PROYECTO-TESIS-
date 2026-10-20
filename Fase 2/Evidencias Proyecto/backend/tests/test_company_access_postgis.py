"""TENANT: aislamiento de visitas, croquis y fotos entre dos empresas.

JWT obtenido por login real, SQL/PostGIS reales y rollback por caso. Requiere
CROQUIS_TEST_DATABASE_URL con una base separada croquis_regression, inicializada
con schema.sql y migracion_croquis_terreno.sql. No cambia permisos del backend.
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.main import app
import test_croquis_terreno as fixture

CLIENT_B = '40000000-0000-0000-0000-000000000002'
VISIT_B = '50000000-0000-0000-0000-000000000005'
CROQUIS_B = '60000000-0000-0000-0000-000000000005'
TRAP_B = '70000000-0000-0000-0000-000000000005'
PHOTO_A = '0123456789abcdef0123456789abcdef.jpg'
PHOTO_B = 'abcdef0123456789abcdef0123456789.jpg'
RESOURCES = {
    'A': {'visit': fixture.VISITA_ANTERIOR, 'client': fixture.CLIENTE, 'croquis': fixture.CROQUIS_ANTERIOR, 'photo': fixture.TRAMPA_ACTIVA},
    'B': {'visit': VISIT_B, 'client': CLIENT_B, 'croquis': CROQUIS_B, 'photo': TRAP_B},
}
EMAILS = {
    ('admin', 'A'): 'admin@croquis.test', ('admin', 'B'): 'admin@otra.test',
    ('coordinador', 'A'): 'coord-a@tenant.test', ('coordinador', 'B'): 'coord-b@tenant.test',
}


def resource_path(company, kind):
    ids = RESOURCES[company]
    return {'visit': f"/visitas/{ids['visit']}", 'croquis': f"/croquis/{ids['visit']}",
            'photo': f"/dispositivos-trampa/{ids['photo']}/foto"}[kind]


@unittest.skipUnless(os.getenv('CROQUIS_TEST_DATABASE_URL'), 'Falta CROQUIS_TEST_DATABASE_URL aislada')
class CompanyAccessPostgisTest(unittest.TestCase):
    def setUp(self):
        self.engine = fixture._engine()
        self.connection = self.engine.connect()
        self.transaction = self.connection.begin()
        self.db = Session(bind=self.connection, join_transaction_mode='create_savepoint')
        self.addCleanup(self.cleanup_db)
        fixture._seed(self.db)
        # Reutiliza el hash sintético del fixture; nunca lee claves del .env.
        password_hash = self.db.execute(text('SELECT password_hash FROM usuarios WHERE id=:id'), dict(id=fixture.ADMIN)).scalar_one()
        for suffix, company in ((3, 'A'), (4, 'B')):
            self.db.execute(text('''INSERT INTO usuarios(id,empresa_id,nombre,email,password_hash,rol)
                VALUES (:id,:company,:name,:email,:password,'coordinador')'''),
                dict(id=f'20000000-0000-0000-0000-{suffix:012d}',
                     company=fixture.EMPRESA if company == 'A' else fixture.OTRA_EMPRESA,
                     name=f'Coordinador QA {company}', email=EMAILS[('coordinador', company)], password=password_hash))
        self.db.execute(text('''INSERT INTO clientes(id,empresa_id,nombre,telefono_whatsapp,direccion,ubicacion)
            VALUES (:id,:company,'Cliente B QA','+00000000020','Direccion B QA',
            ST_SetSRID(ST_MakePoint(-70.60,-33.48),4326)::geography)'''), dict(id=CLIENT_B, company=fixture.OTRA_EMPRESA))
        self.db.execute(text('''INSERT INTO visitas(id,empresa_id,cliente_id,fecha_hora,estado,origen_agendamiento)
            VALUES (:id,:company,:client,now(),'completada','manual')'''), dict(id=VISIT_B, company=fixture.OTRA_EMPRESA, client=CLIENT_B))
        self.db.execute(text('INSERT INTO croquis(id,cliente_id,visita_id,version) VALUES (:id,:client,:visit,1)'), dict(id=CROQUIS_B, client=CLIENT_B, visit=VISIT_B))
        self.db.execute(text('''INSERT INTO dispositivos_trampa(id,croquis_id,codigo,tipo,ubicacion,confirmado,foto_path)
            VALUES (:id,:croquis,'B-01','cebadero',ST_SetSRID(ST_MakePoint(-70.60,-33.48),4326)::geography,true,:photo)'''),
            dict(id=TRAP_B, croquis=CROQUIS_B, photo=PHOTO_B))
        uploads = self.enterContext(tempfile.TemporaryDirectory(prefix='tenant-test-'))
        self.enterContext(patch('app.fotos.settings.upload_dir', uploads))
        for name in (PHOTO_A, PHOTO_B): Path(uploads, name).write_bytes(fixture.JPEG)
        self.previous_overrides = app.dependency_overrides.copy()
        app.dependency_overrides[get_db] = lambda: self.db
        self.addCleanup(self.restore_overrides)
        self.client = self.enterContext(TestClient(app))

    def cleanup_db(self):
        self.db.close()
        self.transaction.rollback()
        self.connection.close()
        self.engine.dispose()

    def restore_overrides(self):
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)

    def check_access(self, role, source, target, kind):
        path = resource_path(target, kind)
        headers = {}
        if role != 'anonymous':
            login = self.client.post('/auth/login', json={'usuario': EMAILS[(role, source)], 'clave': fixture.CLAVE})
            self.assertEqual(login.status_code, 200, 'Falló el login sintético de control')
            headers['Authorization'] = f"Bearer {login.json()['access_token']}"
        response = self.client.get(path, headers=headers)
        expected = [401] if role == 'anonymous' else [200] if source == target else [403, 404]
        returned_target = False
        if response.status_code == 200:
            returned_target = (response.content == fixture.JPEG) if kind == 'photo' else (
                response.json().get('id') == RESOURCES[target]['visit' if kind == 'visit' else 'croquis'])
        foreign_data = role != 'anonymous' and source != target and returned_target
        self.observation = dict(role=role, source_company=source, target_company=target,
                                resource=kind, method='GET', path=path, expected_status=expected,
                                actual_status=response.status_code, returned_target_resource=returned_target,
                                foreign_data_returned=foreign_data)
        self.assertIn(response.status_code, expected,
                      f'{role} {source} -> {target}: {kind} respondió {response.status_code}; esperado {expected}')
        if response.status_code != 200:
            for resource_id in RESOURCES[target].values(): self.assertNotIn(resource_id, response.text)
            return
        if kind == 'visit':
            self.assertEqual(response.json()['id'], RESOURCES[target]['visit'])
            self.assertEqual(response.json()['cliente']['id'], RESOURCES[target]['client'])
        elif kind == 'croquis':
            self.assertEqual(response.json()['id'], RESOURCES[target]['croquis'])
            self.assertEqual(response.json()['visita_id'], RESOURCES[target]['visit'])
            self.assertTrue(response.json()['dispositivos'])
        else:
            self.assertEqual(response.content, fixture.JPEG)
            self.assertIn('image/jpeg', response.headers['content-type'])


def access_case(role, source, target, kind):
    def run(self): self.check_access(role, source, target, kind)
    return run


# Cada combinación es una prueba independiente: 24 autenticadas y 6 sin token.
for role in ('admin', 'coordinador'):
    for source in ('A', 'B'):
        for target in ('A', 'B'):
            for kind in ('visit', 'croquis', 'photo'):
                name = f'test_TENANT_{role}_{source}_to_{target}_{kind}'
                setattr(CompanyAccessPostgisTest, name, access_case(role, source, target, kind))
for target in ('A', 'B'):
    for kind in ('visit', 'croquis', 'photo'):
        setattr(CompanyAccessPostgisTest, f'test_TENANT_anonymous_to_{target}_{kind}', access_case('anonymous', None, target, kind))
