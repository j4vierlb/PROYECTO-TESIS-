"""Lectura web de croquis/fotos con JWT y PostGIS reales; rollback por caso.

No modifica el control de visitas que Javier corrige en su PR. La barrera
entre empresas de GET /croquis requiere esa corrección y su prueba propia.
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


@unittest.skipUnless(os.getenv('CROQUIS_TEST_DATABASE_URL'), 'Falta CROQUIS_TEST_DATABASE_URL aislada')
class PanelCroquisReadTest(unittest.TestCase):
    def setUp(self):
        self.engine = fixture._engine()
        self.connection = self.engine.connect()
        self.transaction = self.connection.begin()
        self.db = Session(bind=self.connection, join_transaction_mode='create_savepoint')
        self.addCleanup(self.cleanup_db)
        fixture._seed(self.db)
        self.previous_overrides = app.dependency_overrides.copy()
        app.dependency_overrides[get_db] = lambda: self.db
        self.addCleanup(self.restore_overrides)
        self.uploads = self.enterContext(tempfile.TemporaryDirectory())
        self.enterContext(patch('app.fotos.settings.upload_dir', self.uploads))
        Path(self.uploads, '0123456789abcdef0123456789abcdef.jpg').write_bytes(fixture.JPEG)
        self.client = self.enterContext(TestClient(app))

    def cleanup_db(self):
        self.db.close(); self.transaction.rollback(); self.connection.close(); self.engine.dispose()

    def restore_overrides(self):
        app.dependency_overrides.clear(); app.dependency_overrides.update(self.previous_overrides)

    def headers(self, role, foreign=False):
        user_id = fixture.ADMIN_OTRA if foreign else fixture.ADMIN
        self.db.execute(text('UPDATE usuarios SET rol=:role WHERE id=:id'), dict(role=role, id=user_id))
        response = self.client.post('/auth/login', json=dict(usuario='admin@otra.test' if foreign else 'admin@croquis.test', clave=fixture.CLAVE))
        self.assertEqual(response.status_code, 200)
        return dict(Authorization=f"Bearer {response.json()['access_token']}")

    def test_CRB01_admin_y_coordinador_consultan_croquis_completado_con_retiradas(self):
        for role in ('admin', 'coordinador'):
            with self.subTest(role=role):
                before = self.db.execute(text('SELECT count(*) FROM dispositivos_trampa')).scalar_one()
                response = self.client.get(f'/croquis/{fixture.VISITA_ANTERIOR}', headers=self.headers(role))
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(len(response.json()['dispositivos']), 2)
                self.assertIn('retirado', [d['estado'] for d in response.json()['dispositivos']])
                self.assertEqual(self.db.execute(text('SELECT count(*) FROM dispositivos_trampa')).scalar_one(), before)

    def test_CRB02_admin_y_coordinador_descargan_foto_de_su_empresa(self):
        for role in ('admin', 'coordinador'):
            with self.subTest(role=role):
                response = self.client.get(f'/dispositivos-trampa/{fixture.TRAMPA_ACTIVA}/foto', headers=self.headers(role))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.content, fixture.JPEG)
                self.assertIn('private', response.headers['cache-control'])

    def test_CRB03_get_inexistente_no_crea_croquis(self):
        before = self.db.execute(text('SELECT count(*) FROM croquis')).scalar_one()
        response = self.client.get(f'/croquis/{fixture.VISITA_HOY}', headers=self.headers('admin'))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.db.execute(text('SELECT count(*) FROM croquis')).scalar_one(), before)

    def test_CRB04_foto_y_croquis_exigen_token(self):
        for path in (f'/croquis/{fixture.VISITA_ANTERIOR}', f'/dispositivos-trampa/{fixture.TRAMPA_ACTIVA}/foto'):
            self.assertEqual(self.client.get(path).status_code, 401)

    def test_CRB05_fotos_rechazan_admin_y_coordinador_de_otra_empresa(self):
        for role in ('admin', 'coordinador'):
            with self.subTest(role=role):
                response = self.client.get(f'/dispositivos-trampa/{fixture.TRAMPA_ACTIVA}/foto', headers=self.headers(role, foreign=True))
                self.assertEqual(response.status_code, 403)
