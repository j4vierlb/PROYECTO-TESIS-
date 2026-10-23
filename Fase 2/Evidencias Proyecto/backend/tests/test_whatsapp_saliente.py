"""Mensajes de WhatsApp salientes: avisos, recordatorios, bandeja y estado de entrega.

Se ejecuta desde backend: python -m unittest discover tests -v
Twilio y la base de datos están simulados: no se envía ningún mensaje real.
"""
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from twilio.request_validator import RequestValidator

from app import whatsapp_saliente as saliente
from app.config import settings
from app.database import get_db
from app.dependencies import require_web_user
from app.main import app
from app.routers.panel import _notice_for_change
from app.schemas import CurrentUser

UTC = timezone.utc
SANTIAGO = ZoneInfo('America/Santiago')
CLIENT_ID = UUID('33333333-3333-3333-3333-333333333333')
CONVERSATION_ID = UUID('88888888-8888-8888-8888-888888888888')
MESSAGE_ID = UUID('99999999-9999-9999-9999-999999999999')
COMPANY_ID = UUID('11111111-1111-1111-1111-111111111111')
TOKEN = 'token-de-prueba'
WEBHOOK_URL = 'https://ejemplo.ngrok-free.app/webhooks/whatsapp'

TWILIO_SETTINGS = dict(
    twilio_account_sid='AC-prueba', twilio_auth_token=TOKEN, twilio_whatsapp_number='+14155238886',
    twilio_webhook_url=WEBHOOK_URL, twilio_status_callback_url='', twilio_validate_signature=True,
    twilio_content_sid_aviso='', twilio_content_sid_recordatorio='',
)


def patch_settings(**values):
    return patch.multiple(settings, **{**TWILIO_SETTINGS, **values})


def saved_message(**changes):
    return dict(id=MESSAGE_ID, conversacion_id=CONVERSATION_ID, emisor='sistema', contenido='hola',
                intencion_detectada=None, message_sid=None, estado_entrega='queued', error_entrega=None,
                created_at=datetime.now(UTC)) | changes


class FormatoTest(unittest.TestCase):
    def test_numero_en_formato_de_twilio(self):
        self.assertEqual(saliente.whatsapp_address('whatsapp:+56912345678'), 'whatsapp:+56912345678')
        self.assertEqual(saliente.whatsapp_address('+56 9 1234 5678'), 'whatsapp:+56912345678')
        self.assertEqual(saliente.whatsapp_address('9 1234-5678'), 'whatsapp:+56912345678')
        self.assertEqual(saliente.whatsapp_address('56912345678'), 'whatsapp:+56912345678')

    def test_saludo_usa_el_primer_nombre_y_omite_el_generico(self):
        fecha = datetime(2026, 10, 23, 13, tzinfo=UTC)
        self.assertTrue(saliente.texto_aviso('agendada', 'Ana Pérez', fecha).startswith('Hola Ana 😊'))
        self.assertTrue(saliente.texto_aviso('cancelada', 'Cliente WhatsApp +569', fecha).startswith('Hola, tu visita'))

    def test_textos_en_hora_de_chile(self):
        fecha = datetime(2026, 10, 23, 13, tzinfo=UTC)  # 10:00 en Chile (UTC-3)
        self.assertIn('23/10/2026 a las 10:00', saliente.texto_aviso('reagendada', 'Ana', fecha))
        self.assertIn('mañana 23/10/2026 a las 10:00', saliente.texto_recordatorio('Ana', fecha))

    def test_url_de_estado_se_deriva_del_webhook(self):
        with patch_settings():
            self.assertEqual(saliente.status_callback_url(MESSAGE_ID),
                             f'{WEBHOOK_URL}/estado?mensaje_id={MESSAGE_ID}')
        with patch_settings(twilio_status_callback_url='https://otra.app/estado'):
            self.assertEqual(saliente.status_callback_base(), 'https://otra.app/estado')


@patch_settings()
class EnviarWhatsAppTest(unittest.TestCase):
    def setUp(self):
        self.db = MagicMock()
        self.twilio = MagicMock()
        self.twilio.messages.create.return_value = MagicMock(sid='SM-saliente', status='queued')
        patches = {
            'fetch_whatsapp_client': MagicMock(return_value=dict(
                id=CLIENT_ID, empresa_id=COMPANY_ID, nombre='Ana', telefono_whatsapp='+56912345678')),
            'fetch_active_whatsapp_conversation': MagicMock(return_value=dict(id=CONVERSATION_ID)),
            'insert_whatsapp_message': MagicMock(side_effect=lambda *a, **k: saved_message(
                estado_entrega=k['delivery_status'], error_entrega=k['delivery_error'])),
            'update_whatsapp_delivery': MagicMock(return_value=True),
            'client_wrote_since': MagicMock(return_value=True),
            '_twilio_client': MagicMock(return_value=self.twilio),
        }
        self.mocks = {}
        for name, mock in patches.items():
            patcher = patch.object(saliente, name, mock)
            self.mocks[name] = patcher.start()
            self.addCleanup(patcher.stop)

    def test_dentro_de_la_ventana_envia_texto_libre_con_url_de_estado(self):
        message = saliente.enviar_whatsapp(self.db, CLIENT_ID, 'Hola Ana', intencion='aviso_agendada')
        kwargs = self.twilio.messages.create.call_args.kwargs
        self.assertEqual(kwargs['to'], 'whatsapp:+56912345678')
        self.assertEqual(kwargs['from_'], 'whatsapp:+14155238886')
        self.assertEqual(kwargs['body'], 'Hola Ana')
        self.assertEqual(kwargs['status_callback'], f'{WEBHOOK_URL}/estado?mensaje_id={MESSAGE_ID}')
        self.assertNotIn('content_sid', kwargs)
        self.mocks['update_whatsapp_delivery'].assert_called_once_with(
            self.db, 'queued', message_id=MESSAGE_ID, message_sid='SM-saliente')
        self.assertEqual(message['message_sid'], 'SM-saliente')

    def test_fuera_de_la_ventana_usa_la_plantilla(self):
        self.mocks['client_wrote_since'].return_value = False
        saliente.enviar_whatsapp(self.db, CLIENT_ID, 'Recordatorio', content_sid='HX123',
                                 content_variables={'1': '23/10/2026', '2': '10:00'})
        kwargs = self.twilio.messages.create.call_args.kwargs
        self.assertEqual(kwargs['content_sid'], 'HX123')
        self.assertEqual(kwargs['content_variables'], '{"1": "23/10/2026", "2": "10:00"}')
        self.assertNotIn('body', kwargs)

    def test_fuera_de_la_ventana_sin_plantilla_no_llama_a_twilio(self):
        self.mocks['client_wrote_since'].return_value = False
        message = saliente.enviar_whatsapp(self.db, CLIENT_ID, 'Aviso')
        self.twilio.messages.create.assert_not_called()
        self.assertEqual(message['estado_entrega'], 'no_enviado')
        self.assertIn('24 h', message['error_entrega'])

    def test_sin_credenciales_no_llama_a_twilio(self):
        with patch.object(settings, 'twilio_auth_token', ''):
            message = saliente.enviar_whatsapp(self.db, CLIENT_ID, 'Aviso')
        self.twilio.messages.create.assert_not_called()
        self.assertEqual(message['estado_entrega'], 'no_enviado')

    def test_error_de_twilio_queda_como_failed(self):
        error = Exception('número inválido')
        error.code, error.msg = 21211, 'Invalid To Phone Number'
        self.twilio.messages.create.side_effect = error
        message = saliente.enviar_whatsapp(self.db, CLIENT_ID, 'Aviso')
        self.assertEqual(message['estado_entrega'], 'failed')
        self.mocks['update_whatsapp_delivery'].assert_called_once_with(
            self.db, 'failed', message_id=MESSAGE_ID, error='21211: Invalid To Phone Number')

    def test_no_avisa_visitas_que_ya_pasaron(self):
        visit = dict(cliente_id=CLIENT_ID, cliente_nombre='Ana', fecha_hora=datetime.now(UTC) - timedelta(hours=1))
        self.assertIsNone(saliente.avisar_visita(self.db, visit, 'cancelada'))
        self.twilio.messages.create.assert_not_called()

    def test_recordatorio_respeta_la_hora_configurada(self):
        claim = MagicMock(return_value=[dict(id='v1', cliente_id=CLIENT_ID,
                                             fecha_hora=datetime(2026, 10, 23, 13, tzinfo=UTC))])
        with patch.object(saliente, 'claim_visits_for_reminder', claim), \
                patch.object(settings, 'whatsapp_recordatorio_hora', '18:00'):
            antes = datetime(2026, 10, 22, 17, 59, tzinfo=SANTIAGO)
            self.assertEqual(saliente.enviar_recordatorios(self.db, antes), [])
            claim.assert_not_called()
            despues = datetime(2026, 10, 22, 18, 0, tzinfo=SANTIAGO)
            self.assertEqual(len(saliente.enviar_recordatorios(self.db, despues)), 1)
        self.assertEqual(claim.call_args.args[1].isoformat(), '2026-10-23')
        self.assertIn('mañana 23/10/2026 a las 10:00', self.twilio.messages.create.call_args.kwargs['body'])

    def run_reminders(self):
        claim = MagicMock(return_value=[dict(id='v1', cliente_id=CLIENT_ID,
                                             fecha_hora=datetime(2026, 10, 23, 13, tzinfo=UTC))])
        with patch.object(saliente, 'claim_visits_for_reminder', claim), \
                patch.object(saliente, 'release_reminder_claim') as release:
            sent = saliente.enviar_recordatorios(self.db, datetime(2026, 10, 22, 19, tzinfo=SANTIAGO))
        return sent, release

    def test_recordatorio_se_reintenta_si_twilio_esta_caido(self):
        error = Exception('Service Unavailable')
        error.code, error.status = 20503, 503
        self.twilio.messages.create.side_effect = error
        sent, release = self.run_reminders()
        self.assertEqual(sent[0]['estado_entrega'], 'failed')
        release.assert_called_once_with(self.db, 'v1')

    def test_recordatorio_se_reintenta_si_falla_la_red(self):
        self.twilio.messages.create.side_effect = ConnectionError('timeout')
        _, release = self.run_reminders()
        release.assert_called_once_with(self.db, 'v1')

    def test_recordatorio_con_error_permanente_no_se_reintenta(self):
        error = Exception('número inválido')
        error.code, error.status = 21211, 400
        self.twilio.messages.create.side_effect = error
        sent, release = self.run_reminders()
        self.assertEqual(sent[0]['estado_entrega'], 'failed')
        release.assert_not_called()

    def test_recordatorio_sin_plantilla_no_se_reintenta(self):
        self.mocks['client_wrote_since'].return_value = False
        sent, release = self.run_reminders()
        self.assertEqual(sent[0]['estado_entrega'], 'no_enviado')
        release.assert_not_called()

    def test_recordatorio_que_falla_en_la_base_se_libera(self):
        self.mocks['fetch_whatsapp_client'].side_effect = RuntimeError('se cayó la conexión')
        sent, release = self.run_reminders()
        self.assertEqual(sent, [])
        release.assert_called_once_with(self.db, 'v1')


class AvisoPorCambioTest(unittest.TestCase):
    def visit(self, estado='agendada', hora=10):
        return dict(estado=estado, fecha_hora=datetime(2026, 10, 23, hora, tzinfo=UTC))

    def test_que_aviso_corresponde(self):
        self.assertEqual(_notice_for_change(self.visit(), self.visit('cancelada')), 'cancelada')
        self.assertEqual(_notice_for_change(self.visit(), self.visit(hora=12)), 'reagendada')
        self.assertEqual(_notice_for_change(self.visit('cancelada'), self.visit()), 'agendada')
        self.assertIsNone(_notice_for_change(self.visit(), self.visit('en_curso')))
        self.assertIsNone(_notice_for_change(self.visit(), self.visit()))
        self.assertIsNone(_notice_for_change(self.visit('cancelada'), self.visit('cancelada', hora=12)))


@patch_settings()
class WebhookTest(unittest.TestCase):
    def setUp(self):
        self.previous_overrides = app.dependency_overrides.copy()
        app.dependency_overrides[get_db] = lambda: MagicMock()
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def tearDown(self):
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)

    def signed_post(self, url, form):
        signature = RequestValidator(TOKEN).compute_signature(url, form)
        path = url.removeprefix('https://ejemplo.ngrok-free.app')
        return self.client.post(path, data=form, headers={'X-Twilio-Signature': signature})

    def inbound(self, human, operator_minutes_ago=5):
        base = 'app.routers.whatsapp.'
        active_at = datetime.now(UTC) - timedelta(minutes=operator_minutes_ago)
        with patch(base + 'whatsapp_message_exists', return_value=False), \
                patch(base + 'fetch_or_create_whatsapp_client', return_value=dict(
                    id=CLIENT_ID, nombre='Ana', direccion='Av. Macul 1234')), \
                patch(base + 'fetch_active_whatsapp_conversation', return_value=dict(
                    id=CONVERSATION_ID, atendida_por_humano=human, operador_activo_at=active_at)), \
                patch(base + 'set_conversation_human') as set_human, \
                patch(base + 'insert_whatsapp_message', return_value=saved_message()) as insert, \
                patch(base + 'fetch_whatsapp_history', return_value=[]), \
                patch(base + 'generate_agent_decision', return_value=dict(
                    intent='consulta', reply='Hola 😊', action='reply')) as agent:
            response = self.signed_post(WEBHOOK_URL, dict(From='whatsapp:+56912345678', Body='Hola', MessageSid='SM-1'))
        self.set_human = set_human
        return response, agent, insert

    def test_con_operador_a_cargo_la_ia_no_responde(self):
        response, agent, insert = self.inbound(human=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('<Message', response.text)
        agent.assert_not_called()
        insert.assert_called_once()  # el mensaje del cliente sí queda guardado
        self.set_human.assert_not_called()

    def test_operador_inactivo_la_conversacion_vuelve_a_la_ia(self):
        with patch.object(settings, 'whatsapp_operador_max_horas', 2):
            response, agent, _ = self.inbound(human=True, operator_minutes_ago=121)
        agent.assert_called_once()
        self.assertIn('Hola 😊', response.text)
        self.set_human.assert_called_once()
        self.assertIs(self.set_human.call_args.args[2], False)

    def test_sin_tiempo_maximo_el_operador_no_pierde_la_conversacion(self):
        with patch.object(settings, 'whatsapp_operador_max_horas', 0):
            _, agent, _ = self.inbound(human=True, operator_minutes_ago=60 * 24)
        agent.assert_not_called()
        self.set_human.assert_not_called()

    def test_respuesta_de_la_ia_pide_estado_de_entrega(self):
        response, agent, _ = self.inbound(human=False)
        agent.assert_called_once()
        self.assertIn(f'action="{WEBHOOK_URL}/estado?mensaje_id={MESSAGE_ID}"', response.text)
        self.assertIn('Hola 😊', response.text)

    def test_estado_de_entrega_con_firma_valida(self):
        url = f'{WEBHOOK_URL}/estado?mensaje_id={MESSAGE_ID}'
        form = dict(MessageSid='SM-salida', MessageStatus='undelivered', ErrorCode='63016',
                    ErrorMessage='Fuera de la ventana')
        with patch('app.routers.whatsapp.update_whatsapp_delivery') as update:
            response = self.signed_post(url, form)
        self.assertEqual(response.status_code, 204)
        update.assert_called_once()
        self.assertEqual(update.call_args.args[1], 'undelivered')
        self.assertEqual(update.call_args.kwargs['message_id'], MESSAGE_ID)
        self.assertEqual(update.call_args.kwargs['message_sid'], 'SM-salida')
        self.assertEqual(update.call_args.kwargs['error'], '63016: Fuera de la ventana')

    def test_estado_de_entrega_sin_firma_es_rechazado(self):
        with patch('app.routers.whatsapp.update_whatsapp_delivery') as update:
            response = self.client.post(f'/webhooks/whatsapp/estado?mensaje_id={MESSAGE_ID}',
                                        data=dict(MessageSid='SM-x', MessageStatus='delivered'))
        self.assertEqual(response.status_code, 403)
        update.assert_not_called()


@patch_settings()
class BandejaTest(unittest.TestCase):
    def setUp(self):
        self.previous_overrides = app.dependency_overrides.copy()
        self.db = MagicMock()
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[require_web_user] = lambda: CurrentUser(
            id='22222222-2222-2222-2222-222222222222', nombre='Admin', rol='admin', empresa_id=COMPANY_ID)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def tearDown(self):
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)

    def conversation(self, hours_ago=1, human=False):
        return dict(id=CONVERSATION_ID, estado='activa', atendida_por_humano=human, cliente_id=CLIENT_ID,
                    cliente_nombre='Ana', telefono_whatsapp='+56912345678',
                    ultimo_cliente_at=datetime.now(UTC) - timedelta(hours=hours_ago))

    def send(self, conversation):
        base = 'app.routers.conversaciones.'
        with patch(base + 'fetch_whatsapp_conversation', return_value=conversation), \
                patch(base + 'set_conversation_human') as set_human, \
                patch(base + 'enviar_whatsapp', return_value=saved_message(emisor='operador')) as send:
            response = self.client.post(f'/panel/conversaciones/{CONVERSATION_ID}/mensajes',
                                        json=dict(contenido=' Hola, soy Juan '))
        return response, set_human, send

    def test_operador_escribe_y_toma_la_conversacion(self):
        response, set_human, send = self.send(self.conversation())
        self.assertEqual(response.status_code, 201)
        set_human.assert_called_once_with(self.db, CONVERSATION_ID, True)
        send.assert_called_once_with(self.db, CLIENT_ID, 'Hola, soy Juan', emisor='operador', intencion='operador')

    def test_fuera_de_la_ventana_de_24_h_devuelve_409(self):
        response, _, send = self.send(self.conversation(hours_ago=25))
        self.assertEqual(response.status_code, 409)
        send.assert_not_called()

    def test_sin_twilio_devuelve_503(self):
        with patch.object(settings, 'twilio_account_sid', ''):
            response, _, send = self.send(self.conversation())
        self.assertEqual(response.status_code, 503)
        send.assert_not_called()

    def test_lista_indica_si_la_ventana_esta_abierta(self):
        rows = [self.conversation(hours_ago=2) | dict(ultimo_contenido='Hola', ultimo_emisor='cliente',
                                                      ultimo_at=datetime.now(UTC)),
                self.conversation(hours_ago=30, human=True) | dict(ultimo_contenido=None, ultimo_emisor=None,
                                                                   ultimo_at=None)]
        with patch('app.routers.conversaciones.list_whatsapp_conversations', return_value=rows):
            response = self.client.get('/panel/conversaciones')
        self.assertEqual(response.status_code, 200)
        self.assertEqual([c['ventana_abierta'] for c in response.json()], [True, False])
        self.assertEqual(response.json()[1]['atendida_por_humano'], True)


if __name__ == '__main__':
    unittest.main()
