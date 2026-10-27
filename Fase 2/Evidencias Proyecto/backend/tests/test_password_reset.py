"""Pruebas reales FastAPI + PostgreSQL aislado. SMTP simulado: no envía correos."""
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.main import app
from app.password_reset import GENERIC_MESSAGE, digest, mail_ready
from app.security import verify_password
from panel_fixture import EMAIL, PASSWORD, USER_ID, seed, test_engine

NEW_PASSWORD = 'NuevaClaveSegura2026!'


@unittest.skipUnless(os.getenv('PANEL_TEST_DATABASE_URL'), 'Requiere base aislada panel_regression')
class PasswordResetTest(unittest.TestCase):
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
        self.addCleanup(self.cleanup_db)
        seed(self.db)
        previous = app.dependency_overrides.copy()
        self.addCleanup(lambda: (app.dependency_overrides.clear(), app.dependency_overrides.update(previous)))
        app.dependency_overrides[get_db] = lambda: self.db
        self.enterContext(patch.multiple(settings, password_reset_enabled=True,
                                        password_reset_panel_url='http://localhost:8080',
                                        smtp_host='smtp.example.test', smtp_port=587,
                                        smtp_user='test-user', smtp_password='test-only',
                                        smtp_from='panel@example.test', smtp_security='starttls'))
        self.mail = self.enterContext(patch('app.routers.password_reset.send_reset_email'))
        self.client = self.enterContext(TestClient(app))

    def cleanup_db(self):
        self.db.close()
        self.transaction.rollback()
        self.connection.close()

    def request_link(self, email=EMAIL):
        return self.client.post('/auth/forgot-password', json={'email': email})

    def token(self):
        self.assertEqual(self.request_link().status_code, 202)
        delivery = self.mail.call_args.args[0]
        return delivery[1].split('#restablecer=')[1]

    def reset(self, token, password=NEW_PASSWORD):
        return self.client.post('/auth/reset-password', json={'token': token, 'password': password})

    def login(self, password=PASSWORD):
        return self.client.post('/auth/login', json={'usuario': EMAIL, 'clave': password})

    def test_enlace_de_un_uso_cambia_clave_y_no_autentica_automaticamente(self):
        token = self.token()
        response = self.reset(token)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertNotIn('access_token', response.json())
        self.assertEqual(self.login().status_code, 401)
        self.assertEqual(self.login(NEW_PASSWORD).status_code, 200)
        self.assertEqual(self.reset(token).status_code, 400)

    def test_se_guarda_solo_hash_no_token_ni_clave_en_texto(self):
        token = self.token()
        row = self.db.execute(text('SELECT token_hash, expires_at > now() AS vigente FROM password_reset_tokens')).mappings().one()
        self.assertEqual(row['token_hash'], digest(token))
        self.assertNotEqual(row['token_hash'], token)
        self.assertTrue(row['vigente'])
        self.reset(token)
        stored = self.db.execute(text('SELECT password_hash FROM usuarios WHERE id=:id'), {'id': USER_ID}).scalar_one()
        self.assertNotEqual(stored, NEW_PASSWORD)
        self.assertTrue(verify_password(NEW_PASSWORD, stored))

    def test_cuentas_inexistentes_operadores_e_inactivas_mismo_mensaje(self):
        known = self.request_link()
        unknown = self.request_link('nadie@example.test')
        operator = self.request_link('operador@panel.test')
        self.db.execute(text('UPDATE usuarios SET activo=false WHERE id=:id'), {'id': USER_ID})
        inactive = self.request_link()
        for result in (known, unknown, operator, inactive):
            self.assertEqual(result.status_code, 202)
            self.assertEqual(result.json(), {'message': GENERIC_MESSAGE})
            self.assertEqual(result.headers['cache-control'], 'no-store')
        self.assertEqual(self.mail.call_args_list[1].args[0], None)
        self.assertEqual(self.mail.call_args_list[2].args[0], None)
        self.assertEqual(self.mail.call_args_list[3].args[0], None)

    def test_normaliza_correo_y_no_refleja_host_de_request(self):
        response = self.request_link(f'  {EMAIL.upper()}  ')
        self.assertEqual(response.status_code, 202)
        recipient, link = self.mail.call_args.args[0]
        self.assertEqual(recipient, EMAIL)
        self.assertTrue(link.startswith('http://localhost:8080#restablecer='))
        self.assertNotIn('testserver', link)
        self.assertNotIn('token', response.json())

    def test_rechaza_enlace_vencido(self):
        token = self.token()
        self.db.execute(text("UPDATE password_reset_tokens SET expires_at=now()-interval '1 second'"))
        self.assertEqual(self.reset(token).status_code, 400)
        self.assertEqual(self.login().status_code, 200)

    def test_rechaza_enlace_alterado_sin_cambiar_cuenta(self):
        token = self.token()
        changed = ('A' if token[0] != 'A' else 'B') + token[1:]
        self.assertEqual(self.reset(changed).status_code, 400)
        self.assertEqual(self.login().status_code, 200)

    def test_rechaza_cuenta_desactivada_despues_de_solicitar(self):
        token = self.token()
        self.db.execute(text('UPDATE usuarios SET activo=false WHERE id=:id'), {'id': USER_ID})
        self.assertEqual(self.reset(token).status_code, 400)

    def test_cambio_invalida_todos_los_enlaces_previos(self):
        first, second = self.token(), self.token()
        self.assertEqual(self.reset(first).status_code, 200)
        self.assertEqual(self.reset(second).status_code, 400)

    def test_restaura_coordinador_sin_cambiar_su_rol(self):
        self.db.execute(text("UPDATE usuarios SET rol='coordinador' WHERE id=:id"), {'id': USER_ID})
        self.assertEqual(self.reset(self.token()).status_code, 200)
        response = self.login(NEW_PASSWORD)
        self.assertEqual(response.status_code, 200)
        from app.security import decode_token
        self.assertEqual(decode_token(response.json()['access_token'], settings.jwt_secret)['rol'], 'coordinador')

    def test_revoca_acceso_y_refresh_previos_permite_nueva_sesion(self):
        previous = self.login().json()
        self.assertEqual(self.reset(self.token()).status_code, 200)
        response = self.client.get('/panel/operadores', headers={'Authorization': f"Bearer {previous['access_token']}"})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.client.post('/auth/refresh', json={'refresh_token': previous['refresh_token']}).status_code, 401)
        current = self.login(NEW_PASSWORD).json()
        self.assertEqual(self.client.get('/panel/operadores', headers={'Authorization': f"Bearer {current['access_token']}"}).status_code, 200)
        self.assertEqual(self.client.post('/auth/refresh', json={'refresh_token': current['refresh_token']}).status_code, 200)

    def test_tokens_legacy_sin_version_quedan_revocados_despues_del_cambio(self):
        from jose import jwt
        from app.security import decode_token
        payload = decode_token(self.login().json()['access_token'], settings.jwt_secret)
        payload.pop('sv')
        token = jwt.encode(payload, settings.jwt_secret, algorithm='HS256')
        headers = {'Authorization': f'Bearer {token}'}
        self.assertEqual(self.client.get('/panel/operadores', headers=headers).status_code, 200)
        self.reset(self.token())
        self.assertEqual(self.client.get('/panel/operadores', headers=headers).status_code, 401)

    def test_no_permite_token_de_sesion_como_enlace(self):
        self.assertEqual(self.reset(self.login().json()['access_token']).status_code, 422)

    def test_valida_clave_longitud_y_bytes_utf8(self):
        token = self.token()
        for password in ('corta', 'x' * 73, 'ñ' * 37, 'ClaveConNulo\x00Seguro2026'):
            with self.subTest(length=len(password)):
                self.assertEqual(self.reset(token, password).status_code, 422)
        self.assertEqual(self.reset(token, 'ñ' * 12).status_code, 200)

    def test_dos_canjes_simultaneos_solo_uno_puede_cambiar_la_clave(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from uuid import uuid4
        from fastapi import HTTPException
        from app.password_reset import issue_token, redeem_token
        from app.security import hash_password
        # Cuenta sintética con commit propio para que DOS conexiones reales la
        # vean. No se comparte Session entre hilos; se limpia únicamente su UUID.
        company, user = uuid4(), uuid4()
        email = f'{user}@concurrency.test'
        with self.engine.begin() as db:
            db.execute(text("INSERT INTO empresas(id,nombre) VALUES (:id,'Concurrencia QA')"), {'id': company})
            db.execute(text("""INSERT INTO usuarios(id,empresa_id,nombre,email,password_hash,rol)
                VALUES (:id,:company,'Admin QA',:email,:password,'admin')"""),
                       {'id': user, 'company': company, 'email': email, 'password': hash_password(PASSWORD)})
        try:
            with self.engine.connect() as db:
                token = issue_token(db, email)[1].split('#restablecer=')[1]
            barrier = Barrier(2)
            def attempt(_):
                with self.engine.connect() as db:
                    barrier.wait(timeout=10)
                    try:
                        redeem_token(db, token, NEW_PASSWORD)
                        return 200
                    except HTTPException as exc:
                        return exc.status_code
            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(attempt, range(2)))
            self.assertEqual(sorted(results), [200, 400])
        finally:
            with self.engine.begin() as db:
                db.execute(text('DELETE FROM empresas WHERE id=:id'), {'id': company})

    def test_limita_solicitudes_por_email_incluso_inexistente(self):
        for _ in range(3):
            self.assertEqual(self.request_link('inexistente@example.test').status_code, 202)
        response = self.request_link('inexistente@example.test')
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers['retry-after'], '900')

    def test_limita_por_ip_aunque_cambie_correo(self):
        for i in range(20):
            self.assertEqual(self.request_link(f'nadie{i}@example.test').status_code, 202)
        self.assertEqual(self.request_link('otro@example.test').status_code, 429)

    def test_limita_canje_y_libera_cupo_al_vencer(self):
        for _ in range(30):
            self.assertEqual(self.reset('A' * 43).status_code, 400)
        self.assertEqual(self.reset('A' * 43).status_code, 429)
        self.db.execute(text("UPDATE password_reset_limits SET expires_at=now()-interval '1 second'"))
        self.assertEqual(self.reset('A' * 43).status_code, 400)

    def test_mensaje_503_para_todas_las_cuentas_si_no_hay_correo_configurado(self):
        with patch.object(settings, 'password_reset_enabled', False):
            for email in (EMAIL, 'nadie@example.test'):
                self.assertEqual(self.request_link(email).status_code, 503)
        self.mail.assert_not_called()


class MailConfigurationTest(unittest.TestCase):
    def test_falla_cerrada_sin_https_o_con_fragmento_host_credenciales(self):
        with patch.multiple(settings, password_reset_enabled=True, smtp_host='smtp.example.test',
                            smtp_from='panel@example.test', smtp_security='starttls',
                            smtp_user='', smtp_password=''):
            for url in ('http://panel.example.test', 'https://user:pass@panel.example.test',
                        'https://panel.example.test/#secreto', 'https://panel.example.test/?q=1'):
                with self.subTest(url=url), patch.object(settings, 'password_reset_panel_url', url):
                    self.assertFalse(mail_ready())
            with patch.object(settings, 'password_reset_panel_url', 'https://panel.example.test'):
                self.assertTrue(mail_ready())
                with patch.object(settings, 'smtp_security', 'none'):
                    self.assertFalse(mail_ready())

    @patch('app.password_reset.smtplib.SMTP')
    def test_envia_solo_con_starttls_y_no_registra_enlace_al_fallar(self, smtp):
        from app.password_reset import send_reset_email
        with patch.multiple(settings, smtp_security='starttls', smtp_host='smtp.example.test',
                            smtp_port=587, smtp_user='user', smtp_password='test-only', smtp_from='panel@example.test'):
            send_reset_email(('admin@example.test', 'https://panel.example.test/#restablecer=secreto'))
            # La instancia que entra al contexto es el transporte original.
            smtp.return_value.starttls.assert_called_once()
            smtp.return_value.login.assert_called_once_with('user', 'test-only')
            smtp.return_value.send_message.assert_called_once()
            smtp.side_effect = OSError('secret must not be logged')
            with self.assertLogs('app.password_reset', level='WARNING') as logs:
                send_reset_email(('admin@example.test', 'https://panel.example.test/#restablecer=secreto'))
            self.assertNotIn('secreto', str(logs.output))
            self.assertNotIn('secret must', str(logs.output))


if __name__ == '__main__':
    unittest.main()
