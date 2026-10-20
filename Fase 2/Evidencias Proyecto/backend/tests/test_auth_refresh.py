"""POST /auth/refresh: renovar la sesión sin pedir la clave.

Pruebas unitarias: la búsqueda del usuario en la base se reemplaza por una
simulada (patch), así que no necesitan PostgreSQL.
"""
import unittest
from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.config import settings
from app.database import get_db
from app.main import app
from app.security import create_token, decode_token

OPERADOR = {'id': uuid4(), 'nombre': 'Operador', 'empresa_id': uuid4()}


def _token(tipo='refresh', rol='operador', user_id=None, duracion=timedelta(days=30), secreto=None):
    return create_token(user_id or OPERADOR['id'], rol, duracion, tipo, secreto or settings.jwt_secret)


class RefreshTest(unittest.TestCase):
    def setUp(self):
        app.dependency_overrides[get_db] = lambda: None  # la base no se usa: se simula la búsqueda
        self.addCleanup(app.dependency_overrides.clear)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def refresh(self, token):
        return self.client.post('/auth/refresh', json={'refresh_token': token})

    @patch('app.routers.auth.fetch_operator_by_id', return_value=OPERADOR)
    def test_refresh_valido_entrega_tokens_nuevos_del_mismo_usuario(self, _):
        response = self.refresh(_token())
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        acceso = decode_token(data['access_token'], settings.jwt_secret)
        renovacion = decode_token(data['refresh_token'], settings.jwt_secret)
        self.assertEqual((acceso['type'], acceso['sub'], acceso['rol']), ('access', str(OPERADOR['id']), 'operador'))
        self.assertEqual((renovacion['type'], renovacion['sub']), ('refresh', str(OPERADOR['id'])))
        self.assertEqual(data['expires_in'], 8 * 60 * 60)

    @patch('app.routers.auth.fetch_web_user_by_id', return_value={'id': uuid4(), 'nombre': 'Admin', 'empresa_id': uuid4()})
    def test_usuario_del_panel_conserva_su_rol(self, _):
        response = self.refresh(_token(rol='coordinador'))
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(decode_token(response.json()['access_token'], settings.jwt_secret)['rol'], 'coordinador')

    @patch('app.routers.auth.fetch_operator_by_id', return_value=OPERADOR)
    def test_rechaza_tokens_invalidos_con_401(self, _):
        casos = {
            'access_token en vez de refresh': _token(tipo='access'),
            'refresh vencido': _token(duracion=timedelta(seconds=-1)),
            'firmado con otra clave': _token(secreto='clave-falsa-de-un-atacante'),
            'texto cualquiera': 'no-es-un-token',
        }
        for nombre, token in casos.items():
            with self.subTest(nombre):
                response = self.refresh(token)
                self.assertEqual(response.status_code, 401, response.text)
                self.assertEqual(response.json()['detail'], 'Sesión vencida: vuelve a iniciar sesión')

    @patch('app.routers.auth.fetch_operator_by_id', return_value=None)
    def test_cuenta_desactivada_o_borrada_no_renueva(self, _):
        self.assertEqual(self.refresh(_token()).status_code, 401)

    def test_falta_el_refresh_token_responde_422(self):
        self.assertEqual(self.client.post('/auth/refresh', json={}).status_code, 422)
        self.assertEqual(self.client.post('/auth/refresh', json={'refresh_token': ''}).status_code, 422)


if __name__ == '__main__':
    unittest.main()
