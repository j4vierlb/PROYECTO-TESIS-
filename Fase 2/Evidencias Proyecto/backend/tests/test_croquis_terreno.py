"""Croquis en terreno: crear croquis, agregar trampas y fotos, con permisos.

Pruebas de integración con FastAPI + login real + PostGIS aislado. Cada
prueba corre dentro de una transacción que se deshace al final (rollback).

Activar con CROQUIS_TEST_DATABASE_URL apuntando a una base llamada
croquis_regression (con schema.sql y migracion_croquis_terreno.sql). Sin
esa variable estas pruebas se omiten. Nunca usar la base de trabajo.
"""
import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.database import get_db
from app.main import app
from app.security import hash_password

EMPRESA = '10000000-0000-0000-0000-000000000001'
OTRA_EMPRESA = '10000000-0000-0000-0000-000000000002'
ADMIN = '20000000-0000-0000-0000-000000000001'
ADMIN_OTRA = '20000000-0000-0000-0000-000000000002'
OPERADOR = '30000000-0000-0000-0000-000000000001'
OTRO_OPERADOR = '30000000-0000-0000-0000-000000000002'
CLIENTE = '40000000-0000-0000-0000-000000000001'
VISITA_ANTERIOR = '50000000-0000-0000-0000-000000000001'  # completada, con croquis
VISITA_HOY = '50000000-0000-0000-0000-000000000002'       # agendada, sin croquis
VISITA_CERRADA = '50000000-0000-0000-0000-000000000003'   # completada, con croquis
VISITA_OTRO = '50000000-0000-0000-0000-000000000004'      # de otro operador
CROQUIS_ANTERIOR = '60000000-0000-0000-0000-000000000001'
CROQUIS_CERRADA = '60000000-0000-0000-0000-000000000003'
TRAMPA_ACTIVA = '70000000-0000-0000-0000-000000000001'
TRAMPA_RETIRADA = '70000000-0000-0000-0000-000000000002'
TRAMPA_CERRADA = '70000000-0000-0000-0000-000000000003'
CLAVE = 'CroquisDemo123!'
JPEG = b'\xff\xd8\xff\xe0' + b'\x00' * 200
PNG = b'\x89PNG\r\n\x1a\n' + b'\x00' * 200


def _engine():
    engine = create_engine(os.environ['CROQUIS_TEST_DATABASE_URL'])
    if engine.url.database != 'croquis_regression':
        engine.dispose()
        raise RuntimeError('La prueba solo admite la base aislada croquis_regression')
    return engine


def _seed(db):
    clave = hash_password(CLAVE)
    db.execute(text("INSERT INTO empresas(id, nombre) VALUES (:a, 'Empresa QA'), (:b, 'Otra QA')"),
               dict(a=EMPRESA, b=OTRA_EMPRESA))
    db.execute(text("""INSERT INTO usuarios(id, empresa_id, nombre, email, password_hash, rol) VALUES
                       (:a, :e, 'Admin QA', 'admin@croquis.test', :c, 'admin'),
                       (:b, :o, 'Admin otra', 'admin@otra.test', :c, 'admin')"""),
               dict(a=ADMIN, b=ADMIN_OTRA, e=EMPRESA, o=OTRA_EMPRESA, c=clave))
    db.execute(text("""INSERT INTO operadores(id, empresa_id, nombre, email, password_hash) VALUES
                       (:a, :e, 'Operador QA', 'op@croquis.test', :c),
                       (:b, :e, 'Otro operador', 'otro@croquis.test', :c)"""),
               dict(a=OPERADOR, b=OTRO_OPERADOR, e=EMPRESA, c=clave))
    db.execute(text("""INSERT INTO clientes(id, empresa_id, nombre, telefono_whatsapp, direccion, ubicacion)
                       VALUES (:id, :e, 'Cliente QA', '+00000000010', 'Av. QA 123',
                               ST_SetSRID(ST_MakePoint(-70.5989, -33.4869), 4326)::geography)"""),
               dict(id=CLIENTE, e=EMPRESA))
    db.execute(text("""INSERT INTO visitas(id, empresa_id, cliente_id, operador_id, fecha_hora, estado, origen_agendamiento) VALUES
                       (:ant, :e, :c, :op, now() - interval '30 days', 'completada', 'manual'),
                       (:hoy, :e, :c, :op, now(), 'agendada', 'manual'),
                       (:cer, :e, :c, :op, now() - interval '60 days', 'completada', 'manual'),
                       (:otro, :e, :c, :otro_op, now(), 'agendada', 'manual')"""),
               dict(ant=VISITA_ANTERIOR, hoy=VISITA_HOY, cer=VISITA_CERRADA, otro=VISITA_OTRO,
                    e=EMPRESA, c=CLIENTE, op=OPERADOR, otro_op=OTRO_OPERADOR))
    db.execute(text("""INSERT INTO croquis(id, cliente_id, visita_id, operador_id, version) VALUES
                       (:ant, :c, :v_ant, :op, 2), (:cer, :c, :v_cer, :op, 1)"""),
               dict(ant=CROQUIS_ANTERIOR, cer=CROQUIS_CERRADA, c=CLIENTE,
                    v_ant=VISITA_ANTERIOR, v_cer=VISITA_CERRADA, op=OPERADOR))
    db.execute(text("""INSERT INTO dispositivos_trampa(id, croquis_id, codigo, tipo, ubicacion, confirmado, estado, foto_path) VALUES
        (:a, :ant, 'T-01', 'cebadero', ST_SetSRID(ST_MakePoint(-70.59885, -33.48685), 4326)::geography, TRUE, 'activo',
         '0123456789abcdef0123456789abcdef.jpg'),
        (:r, :ant, 'T-02', 'trampa_luz', ST_SetSRID(ST_MakePoint(-70.59895, -33.48695), 4326)::geography, TRUE, 'retirado', NULL),
        (:c, :cer, 'T-01', 'cebadero', ST_SetSRID(ST_MakePoint(-70.59880, -33.48700), 4326)::geography, TRUE, 'activo', NULL)"""),
               dict(a=TRAMPA_ACTIVA, r=TRAMPA_RETIRADA, c=TRAMPA_CERRADA,
                    ant=CROQUIS_ANTERIOR, cer=CROQUIS_CERRADA))


@unittest.skipUnless(os.getenv('CROQUIS_TEST_DATABASE_URL'), 'Falta CROQUIS_TEST_DATABASE_URL de una base aislada')
class CroquisTerrenoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = _engine()

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    def setUp(self):
        self.connection = self.engine.connect()
        self.transaction = self.connection.begin()
        # Los commit() del código quedan como "savepoints" dentro de esta
        # transacción, que se deshace entera al terminar la prueba.
        self.db = Session(bind=self.connection, join_transaction_mode='create_savepoint')
        self.addCleanup(self._cleanup_db)
        _seed(self.db)
        self.uploads = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.uploads, True)
        patcher = patch('app.fotos.settings.upload_dir', self.uploads)
        patcher.start()
        self.addCleanup(patcher.stop)
        app.dependency_overrides[get_db] = lambda: self.db
        self.addCleanup(app.dependency_overrides.clear)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def _cleanup_db(self):
        self.db.close()
        self.transaction.rollback()
        self.connection.close()

    def _token(self, usuario):
        response = self.client.post('/auth/login', json=dict(usuario=usuario, clave=CLAVE))
        self.assertEqual(response.status_code, 200, response.text)
        return {'Authorization': f"Bearer {response.json()['access_token']}"}

    def op(self):
        return self._token('op@croquis.test')

    def _crear_croquis(self, visita=VISITA_HOY):
        return self.client.post(f'/croquis/{visita}', headers=self.op())

    # --- Crear el croquis ---------------------------------------------------

    def test_crear_croquis_copia_trampas_activas_de_la_visita_anterior_sin_confirmar(self):
        self.assertEqual(self.client.get(f'/croquis/{VISITA_HOY}', headers=self.op()).status_code, 404)
        response = self._crear_croquis()
        self.assertEqual(response.status_code, 201, response.text)
        croquis = response.json()
        self.assertEqual(croquis['version'], 3)  # el cliente ya tenía versiones 1 y 2
        # Solo la trampa activa (la retirada no se copia), con su foto, y sin confirmar.
        self.assertEqual([d['codigo'] for d in croquis['dispositivos']], ['T-01'])
        copiada = croquis['dispositivos'][0]
        self.assertFalse(copiada['confirmado'])
        self.assertEqual(copiada['estado'], 'activo')
        self.assertIsNotNone(copiada['foto_url'])
        self.assertNotEqual(copiada['id'], TRAMPA_ACTIVA)  # es una fila nueva
        # La trampa original de la visita anterior no cambia.
        original = self.db.execute(text('SELECT confirmado FROM dispositivos_trampa WHERE id = :id'),
                                   dict(id=TRAMPA_ACTIVA)).scalar_one()
        self.assertTrue(original)

    def test_crear_croquis_dos_veces_no_lo_duplica(self):
        primero = self._crear_croquis()
        segundo = self._crear_croquis()
        self.assertEqual(primero.status_code, 201)
        self.assertEqual(segundo.status_code, 200)
        self.assertEqual(primero.json()['id'], segundo.json()['id'])
        total = self.db.execute(text('SELECT count(*) FROM croquis WHERE visita_id = :v'), dict(v=VISITA_HOY)).scalar_one()
        self.assertEqual(total, 1)

    def test_primer_croquis_del_cliente_parte_vacio_en_version_1(self):
        self.db.execute(text("""INSERT INTO clientes(id, empresa_id, nombre, telefono_whatsapp)
                                VALUES ('40000000-0000-0000-0000-000000000009', :e, 'Nuevo', '+00000000019')"""),
                        dict(e=EMPRESA))
        self.db.execute(text("UPDATE visitas SET cliente_id = '40000000-0000-0000-0000-000000000009' WHERE id = :v"),
                        dict(v=VISITA_HOY))
        response = self._crear_croquis()
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()['version'], 1)
        self.assertEqual(response.json()['dispositivos'], [])

    def test_no_se_crea_croquis_en_visita_ajena_cerrada_o_por_un_admin(self):
        self.assertEqual(self._crear_croquis(VISITA_OTRO).status_code, 403)
        self.assertEqual(self._crear_croquis(VISITA_ANTERIOR).status_code, 409)
        admin = self.client.post(f'/croquis/{VISITA_HOY}', headers=self._token('admin@croquis.test'))
        self.assertEqual(admin.status_code, 403)
        self.assertEqual(self.client.post(f'/croquis/{VISITA_HOY}').status_code, 401)

    # --- Agregar trampas ----------------------------------------------------

    def test_agregar_trampas_asigna_codigos_correlativos_y_queda_confirmada(self):
        self._crear_croquis()  # trae T-01 copiada de la visita anterior
        uno = self.client.post(f'/croquis/{VISITA_HOY}/dispositivos', headers=self.op(),
                               json=dict(tipo='trampa_pegamento', lat=-33.4870, lng=-70.5990))
        dos = self.client.post(f'/croquis/{VISITA_HOY}/dispositivos', headers=self.op(),
                               json=dict(tipo='cebadero', lat=-33.4871, lng=-70.5991))
        self.assertEqual(uno.status_code, 201, uno.text)
        self.assertEqual((uno.json()['codigo'], dos.json()['codigo']), ('T-02', 'T-03'))
        self.assertTrue(uno.json()['confirmado'])
        self.assertFalse(uno.json()['sugerido_por_ia'])
        self.assertAlmostEqual(uno.json()['lat'], -33.4870, places=5)
        self.assertAlmostEqual(uno.json()['lng'], -70.5990, places=5)
        croquis = self.client.get(f'/croquis/{VISITA_HOY}', headers=self.op()).json()
        self.assertEqual([d['codigo'] for d in croquis['dispositivos']], ['T-01', 'T-02', 'T-03'])

    def test_agregar_trampa_valida_tipo_coordenadas_y_croquis(self):
        url = f'/croquis/{VISITA_HOY}/dispositivos'
        sin_croquis = self.client.post(url, headers=self.op(), json=dict(tipo='cebadero', lat=-33.48, lng=-70.59))
        self.assertEqual(sin_croquis.status_code, 404)
        self._crear_croquis()
        for body in (dict(tipo='bomba', lat=-33.48, lng=-70.59),
                     dict(tipo='cebadero', lat=95, lng=-70.59),
                     dict(tipo='cebadero', lat=-33.48)):
            self.assertEqual(self.client.post(url, headers=self.op(), json=body).status_code, 422, body)

    def test_no_se_agregan_trampas_en_visita_cerrada_ni_ajena(self):
        cerrada = self.client.post(f'/croquis/{VISITA_CERRADA}/dispositivos', headers=self.op(),
                                   json=dict(tipo='cebadero', lat=-33.48, lng=-70.59))
        self.assertEqual(cerrada.status_code, 409)
        ajena = self.client.post(f'/croquis/{VISITA_OTRO}/dispositivos', headers=self.op(),
                                 json=dict(tipo='cebadero', lat=-33.48, lng=-70.59))
        self.assertEqual(ajena.status_code, 403)

    # --- Permisos del PATCH (corrección de seguridad) -------------------------

    def test_patch_rechaza_trampa_de_otro_operador_y_de_visita_cerrada(self):
        otro = self._token('otro@croquis.test')
        ajena = self.client.patch(f'/dispositivos-trampa/{TRAMPA_CERRADA}', headers=otro, json=dict(accion='eliminar'))
        self.assertEqual(ajena.status_code, 403)
        cerrada = self.client.patch(f'/dispositivos-trampa/{TRAMPA_CERRADA}', headers=self.op(), json=dict(accion='eliminar'))
        self.assertEqual(cerrada.status_code, 409)
        estado = self.db.execute(text('SELECT estado FROM dispositivos_trampa WHERE id = :id'),
                                 dict(id=TRAMPA_CERRADA)).scalar_one()
        self.assertEqual(estado, 'activo')

    def test_patch_sigue_funcionando_para_el_dueno_en_visita_abierta(self):
        nueva = self._crear_croquis().json()['dispositivos'][0]
        response = self.client.patch(f"/dispositivos-trampa/{nueva['id']}", headers=self.op(),
                                     json=dict(accion='mover', lat=-33.4872, lng=-70.5992))
        self.assertEqual(response.status_code, 200, response.text)
        self.assertAlmostEqual(response.json()['lat'], -33.4872, places=5)

    # --- Fotos --------------------------------------------------------------

    def _trampa_nueva(self):
        self._crear_croquis()
        return self.client.post(f'/croquis/{VISITA_HOY}/dispositivos', headers=self.op(),
                                json=dict(tipo='cebadero', lat=-33.4870, lng=-70.5990)).json()['id']

    def test_subir_y_ver_foto(self):
        trampa = self._trampa_nueva()
        subida = self.client.post(f'/dispositivos-trampa/{trampa}/foto', headers=self.op(),
                                  files={'foto': ('trampa.jpg', JPEG, 'image/jpeg')})
        self.assertEqual(subida.status_code, 200, subida.text)
        foto_url = subida.json()['foto_url']
        self.assertTrue(foto_url.startswith(f'/dispositivos-trampa/{trampa}/foto?v='))
        self.assertEqual(len(os.listdir(self.uploads)), 1)
        # El operador de la visita y un admin de la misma empresa la pueden ver.
        for headers in (self.op(), self._token('admin@croquis.test')):
            vista = self.client.get(foto_url, headers=headers)
            self.assertEqual(vista.status_code, 200)
            self.assertEqual(vista.content, JPEG)
            self.assertEqual(vista.headers['content-type'], 'image/jpeg')

    def test_foto_png_tambien_se_acepta(self):
        trampa = self._trampa_nueva()
        subida = self.client.post(f'/dispositivos-trampa/{trampa}/foto', headers=self.op(),
                                  files={'foto': ('trampa.png', PNG, 'image/png')})
        self.assertEqual(subida.status_code, 200, subida.text)

    def test_foto_no_es_publica_ni_visible_para_otros(self):
        trampa = self._trampa_nueva()
        url = self.client.post(f'/dispositivos-trampa/{trampa}/foto', headers=self.op(),
                               files={'foto': ('t.jpg', JPEG, 'image/jpeg')}).json()['foto_url']
        self.assertEqual(self.client.get(url).status_code, 401)
        self.assertEqual(self.client.get(url, headers=self._token('otro@croquis.test')).status_code, 403)
        self.assertEqual(self.client.get(url, headers=self._token('admin@otra.test')).status_code, 403)

    def test_foto_rechaza_archivos_que_no_son_imagen_o_muy_grandes(self):
        trampa = self._trampa_nueva()
        url = f'/dispositivos-trampa/{trampa}/foto'
        # Dice ser JPEG, pero el contenido es texto: se revisan los bytes, no el nombre.
        falsa = self.client.post(url, headers=self.op(), files={'foto': ('virus.jpg', b'<?php echo 1;', 'image/jpeg')})
        self.assertEqual(falsa.status_code, 415)
        with patch('app.fotos.settings.max_photo_bytes', 100):
            grande = self.client.post(url, headers=self.op(), files={'foto': ('g.jpg', JPEG, 'image/jpeg')})
        self.assertEqual(grande.status_code, 413)
        self.assertEqual(os.listdir(self.uploads), [])  # no quedó nada guardado

    def test_foto_en_visita_cerrada_o_por_otro_operador_se_rechaza(self):
        cerrada = self.client.post(f'/dispositivos-trampa/{TRAMPA_CERRADA}/foto', headers=self.op(),
                                   files={'foto': ('t.jpg', JPEG, 'image/jpeg')})
        self.assertEqual(cerrada.status_code, 409)
        trampa = self._trampa_nueva()
        ajena = self.client.post(f'/dispositivos-trampa/{trampa}/foto', headers=self._token('otro@croquis.test'),
                                 files={'foto': ('t.jpg', JPEG, 'image/jpeg')})
        self.assertEqual(ajena.status_code, 403)

    def test_trampa_sin_foto_responde_404(self):
        trampa = self._trampa_nueva()
        self.assertEqual(self.client.get(f'/dispositivos-trampa/{trampa}/foto', headers=self.op()).status_code, 404)


if __name__ == '__main__':
    unittest.main()
