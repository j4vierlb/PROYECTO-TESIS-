"""Primer agendamiento por WhatsApp: se pide el nombre real del cliente.

Se prueba _schedule_visit con la base y el repositorio simulados: la regla la
decide el backend (no solo la IA), igual que con la dirección."""
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import UUID

from fastapi import BackgroundTasks

from app.ai import agent
from app.routers import whatsapp

CLIENT_ID = UUID('33333333-3333-3333-3333-333333333333')
BASE = 'app.routers.whatsapp.'
# Dos días adelante: la regla rechaza fechas a más de 60 días.
FECHA = (datetime.now(whatsapp.SANTIAGO) + timedelta(days=2)).replace(hour=10, minute=0, second=0, microsecond=0).isoformat()


def decision(nombre=None, direccion=None, fecha=FECHA):
    return dict(
        action='create_appointment', intent='agendar_visita', reply='ok',
        appointment_datetime=fecha, client_address=direccion, client_name=nombre, notes=None,
    )


def cliente(nombre='Cliente WhatsApp +56912345678'):
    return dict(id=CLIENT_ID, nombre=nombre, direccion='Av. Macul 1234, Macul')


class PrimerAgendamientoTest(unittest.TestCase):
    def agendar(self, dec, visitas_previas, cli=None):
        visita = dict(created=True, fecha_hora=whatsapp._parse_appointment_datetime(FECHA))
        with patch(BASE + 'count_client_visits', return_value=visitas_previas), \
                patch(BASE + 'update_whatsapp_client_name') as guardar_nombre, \
                patch(BASE + 'create_whatsapp_visit', return_value=visita) as crear:
            texto = whatsapp._schedule_visit(MagicMock(), cli or cliente(), dec, 'SM-1', BackgroundTasks())
        return texto, guardar_nombre, crear

    def test_primera_visita_sin_nombre_lo_pide_y_no_agenda(self):
        texto, guardar, crear = self.agendar(decision(), visitas_previas=0)
        self.assertIn('nombre completo', texto)
        crear.assert_not_called()
        guardar.assert_not_called()

    def test_primera_visita_con_nombre_lo_guarda_y_agenda(self):
        texto, guardar, crear = self.agendar(decision(nombre='Ana Pérez'), visitas_previas=0)
        guardar.assert_called_once()
        self.assertEqual(guardar.call_args.args[2], 'Ana Pérez')
        crear.assert_called_once()
        self.assertIn('quedó agendada', texto)

    def test_nombre_igual_al_registrado_no_se_vuelve_a_guardar(self):
        _, guardar, crear = self.agendar(decision(nombre='Ana Pérez'), 0, cliente('Ana Pérez'))
        guardar.assert_not_called()
        crear.assert_called_once()

    def test_cliente_con_visitas_previas_no_se_le_pide_el_nombre(self):
        texto, guardar, crear = self.agendar(decision(), visitas_previas=3)
        guardar.assert_not_called()
        crear.assert_called_once()
        self.assertIn('quedó agendada', texto)


class AgenteNombreTest(unittest.TestCase):
    def test_la_decision_incluye_client_name_y_lo_limpia(self):
        validada = agent._validate_decision(
            dict(action='reply', reply='hola', client_name='  Ana Pérez  '))
        self.assertEqual(validada['client_name'], 'Ana Pérez')

    def test_client_name_ausente_o_invalido_queda_en_none(self):
        self.assertIsNone(agent._validate_decision(dict(action='reply', reply='x'))['client_name'])
        self.assertIsNone(agent._validate_decision(dict(action='reply', reply='x', client_name=7))['client_name'])

    def test_el_nombre_en_minuscula_o_mayuscula_se_corrige(self):
        formato = agent._format_person_name
        self.assertEqual(formato('ayline correa pino'), 'Ayline Correa Pino')
        self.assertEqual(formato('AYLINE CORREA'), 'Ayline Correa')
        self.assertEqual(formato('maría de los ángeles soto'), 'María de los Ángeles Soto')
        self.assertEqual(formato('  juan   pérez '.strip()), 'Juan Pérez')

    def test_el_nombre_con_mayusculas_mezcladas_se_respeta(self):
        self.assertEqual(agent._format_person_name('Ana McKay'), 'Ana McKay')
        self.assertIsNone(agent._format_person_name(None))
        validada = agent._validate_decision(dict(action='reply', reply='x', client_name='ayline correa pino'))
        self.assertEqual(validada['client_name'], 'Ayline Correa Pino')

    def test_el_prompt_explica_el_horario_de_atencion(self):
        self.assertIn('Horario de atención', agent.SYSTEM_PROMPT)
        self.assertIn('por qué un horario no está disponible', agent.SYSTEM_PROMPT)

    def test_el_prompt_pide_el_nombre_en_la_primera_visita(self):
        self.assertIn('PRIMERA visita', agent.SYSTEM_PROMPT)
        self.assertIn('client_name', agent.SYSTEM_PROMPT)


if __name__ == '__main__':
    unittest.main()
