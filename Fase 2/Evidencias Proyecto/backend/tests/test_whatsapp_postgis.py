"""SQL de WhatsApp saliente contra PostGIS aislado, con rollback por prueba.

Activar explícitamente PANEL_TEST_DATABASE_URL apuntando a panel_regression
(con schema.sql cargado). Sin esa variable se omiten estos casos. Twilio no
se llama: las credenciales quedan vacías durante la prueba.
"""
import os
import unittest
from datetime import datetime, time, timedelta, timezone
from unittest.mock import patch
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.main import app
from app.repositories import (
    claim_visits_for_reminder,
    client_wrote_since,
    fetch_active_whatsapp_conversation,
    insert_whatsapp_message,
    list_whatsapp_conversations,
    update_whatsapp_delivery,
)
from panel_fixture import CLIENT_ID, COMPANY_ID, EMAIL, OPERATOR_ID, OTHER_CLIENT_ID, PASSWORD, seed, test_engine

UTC = timezone.utc
SANTIAGO = ZoneInfo('America/Santiago')


@unittest.skipUnless(os.getenv('PANEL_TEST_DATABASE_URL'), 'Falta PANEL_TEST_DATABASE_URL de una base aislada')
class WhatsAppPostgisTest(unittest.TestCase):
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
        no_twilio = patch.multiple(settings, twilio_account_sid='', twilio_auth_token='')
        no_twilio.start()
        self.addCleanup(no_twilio.stop)
        self.previous_overrides = app.dependency_overrides.copy()
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

    def conversation(self, client_id=CLIENT_ID):
        return fetch_active_whatsapp_conversation(self.db, UUID(client_id))

    def visit(self, when, estado='agendada'):
        return self.db.execute(text("""
            INSERT INTO visitas (empresa_id, cliente_id, operador_id, fecha_hora, estado, origen_agendamiento)
            VALUES (:company, :client, :operator, :when, :estado, 'manual') RETURNING id
        """), dict(company=COMPANY_ID, client=CLIENT_ID, operator=OPERATOR_ID, when=when, estado=estado)).scalar_one()

    def test_estado_de_entrega_no_retrocede(self):
        conversation = self.conversation()
        sent = insert_whatsapp_message(self.db, conversation['id'], 'sistema', 'Aviso', delivery_status='queued')
        self.assertTrue(update_whatsapp_delivery(self.db, 'delivered', message_id=sent['id'], message_sid='SM-out'))
        self.assertFalse(update_whatsapp_delivery(self.db, 'sent', message_sid='SM-out'))  # llegó tarde
        self.assertTrue(update_whatsapp_delivery(self.db, 'read', message_sid='SM-out'))
        row = self.db.execute(text('SELECT estado_entrega, message_sid FROM mensajes_whatsapp WHERE id = :id'),
                              dict(id=sent['id'])).one()
        self.assertEqual(tuple(row), ('read', 'SM-out'))

    def test_estado_de_entrega_no_toca_mensajes_del_cliente(self):
        conversation = self.conversation()
        insert_whatsapp_message(self.db, conversation['id'], 'cliente', 'Hola', message_sid='SM-in')
        self.assertFalse(update_whatsapp_delivery(self.db, 'delivered', message_sid='SM-in'))

    def test_recordatorio_se_reclama_una_sola_vez(self):
        tomorrow = (datetime.now(SANTIAGO) + timedelta(days=1)).date()
        self.visit(datetime.combine(tomorrow, time(15), SANTIAGO))
        self.visit(datetime.combine(tomorrow, time(11), SANTIAGO), estado='cancelada')
        self.visit(datetime.combine(tomorrow + timedelta(days=1), time(15), SANTIAGO))
        first = claim_visits_for_reminder(self.db, tomorrow, UUID(COMPANY_ID))
        self.assertEqual(len(first), 1)
        self.assertEqual(claim_visits_for_reminder(self.db, tomorrow), [])

    def test_bandeja_y_ventana_de_24_horas(self):
        conversation = self.conversation()
        insert_whatsapp_message(self.db, conversation['id'], 'cliente', 'Hola')
        insert_whatsapp_message(self.db, conversation['id'], 'agente_ia', 'Hola 😊', delivery_status='queued')
        self.conversation(OTHER_CLIENT_ID)  # otra empresa: no debe aparecer
        self.assertTrue(client_wrote_since(self.db, UUID(CLIENT_ID), datetime.now(UTC) - timedelta(hours=24)))
        rows = list_whatsapp_conversations(self.db, UUID(COMPANY_ID))
        self.assertEqual([r['cliente_id'] for r in rows], [UUID(CLIENT_ID)])
        self.assertEqual(rows[0]['ultimo_emisor'], 'agente_ia')

        response = self.client.get(f"/panel/conversaciones/{conversation['id']}")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ventana_abierta'])
        self.assertEqual([m['estado_entrega'] for m in response.json()['mensajes']], [None, 'queued'])

        response = self.client.patch(f"/panel/conversaciones/{conversation['id']}", json=dict(atendida_por_humano=True))
        self.assertTrue(response.json()['atendida_por_humano'])
        self.assertTrue(self.conversation()['atendida_por_humano'])

    def test_conversacion_de_otra_empresa_da_404(self):
        other = self.conversation(OTHER_CLIENT_ID)
        self.assertEqual(self.client.get(f"/panel/conversaciones/{other['id']}").status_code, 404)

    def test_reagendar_desde_el_panel_reinicia_el_recordatorio(self):
        # El panel valida el horario de atención: lunes a viernes, 10:00 de Chile.
        day = datetime.now(SANTIAGO).date() + timedelta(days=1)
        while day.weekday() > 4:
            day += timedelta(days=1)
        when = datetime.combine(day, time(10, 0), tzinfo=SANTIAGO)
        visit_id = self.visit(when)
        self.db.execute(text('UPDATE visitas SET recordatorio_enviado_at = now() WHERE id = :id'), dict(id=visit_id))
        same = self.client.patch(f'/panel/visitas/{visit_id}', json=dict(fecha_hora=when.isoformat(), notas='x'))
        self.assertEqual(same.status_code, 200)
        reminder = 'SELECT recordatorio_enviado_at FROM visitas WHERE id = :id'
        self.assertIsNotNone(self.db.execute(text(reminder), dict(id=visit_id)).scalar_one())
        new_time = (when + timedelta(hours=2)).isoformat()
        response = self.client.patch(f'/panel/visitas/{visit_id}', json=dict(fecha_hora=new_time, operador_id=None))
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()['operador_id'])
        self.assertIsNone(self.db.execute(text(reminder), dict(id=visit_id)).scalar_one())

    def test_fecha_hora_null_es_rechazada(self):
        visit_id = self.visit(datetime.now(UTC) + timedelta(days=1))
        self.assertEqual(self.client.patch(f'/panel/visitas/{visit_id}', json=dict(fecha_hora=None)).status_code, 422)


if __name__ == '__main__':
    unittest.main()
