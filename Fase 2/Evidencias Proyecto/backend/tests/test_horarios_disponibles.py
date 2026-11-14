"""La IA pide las horas libres y el backend las calcula con la regla real de agendamiento.

Se prueba el cálculo (repositorio) y la respuesta (webhook) con la base simulada."""
import unittest
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import UUID

from app.ai import agent
from app.repositories import agendamiento
from app.repositories._comun import SANTIAGO, UTC
from app.routers import whatsapp

EMPRESA = UUID('11111111-1111-1111-1111-111111111111')


def proximo_dia(weekday: int) -> date:
    """Primer día con ese weekday (0 = lunes ... 6 = domingo) a más de 7 días de hoy."""
    day = datetime.now(SANTIAGO).date() + timedelta(days=8)
    while day.weekday() != weekday:
        day += timedelta(days=1)
    return day


def hora_local(slot: datetime) -> str:
    return slot.astimezone(SANTIAGO).strftime('%H:%M')


class CalculoDeHorasLibresTest(unittest.TestCase):
    def listar(self, dia, operador=lambda *args: 'operador-1', limite=6):
        with patch.object(agendamiento, '_configured_operator_id', return_value=None), \
                patch.object(agendamiento, '_find_available_operator', side_effect=operador):
            return agendamiento.list_available_slots(MagicMock(), EMPRESA, datetime.now(UTC), dia=dia, limite=limite)

    def test_un_dia_habil_lista_las_primeras_horas_desde_la_apertura(self):
        slots = self.listar(proximo_dia(0))
        self.assertEqual([hora_local(s) for s in slots], ['08:00', '09:00', '10:00', '11:00', '12:00', '13:00'])

    def test_la_hora_de_cierre_no_se_ofrece(self):
        slots = self.listar(proximo_dia(0), limite=50)
        self.assertEqual(hora_local(slots[-1]), '17:00')
        self.assertEqual(len(slots), 10)

    def test_un_domingo_no_tiene_horas(self):
        self.assertEqual(self.listar(proximo_dia(6)), [])

    def test_las_horas_con_el_tecnico_ocupado_no_se_ofrecen(self):
        def operador(db, empresa, candidato, fijo):
            return None if candidato.hour == 9 else 'operador-1'

        horas = [hora_local(s) for s in self.listar(proximo_dia(2), operador=operador, limite=4)]
        self.assertEqual(horas, ['08:00', '10:00', '11:00', '12:00'])

    def test_hoy_no_se_ofrecen_horas_que_ya_pasaron(self):
        hoy = datetime.now(SANTIAGO).date()
        ahora = datetime.now(UTC)
        for slot in self.listar(hoy, limite=50):
            self.assertGreater(slot, ahora)

    def test_sin_dia_busca_hacia_adelante(self):
        with patch.object(agendamiento, '_configured_operator_id', return_value=None), \
                patch.object(agendamiento, '_find_available_operator', return_value='operador-1'):
            slots = agendamiento.list_available_slots(MagicMock(), EMPRESA, datetime.now(UTC))
        self.assertEqual(len(slots), 6)
        self.assertEqual(slots, sorted(slots))
        self.assertTrue(all(agendamiento._is_within_business_hours(s) for s in slots))


def slot(dia: date, hora: int) -> datetime:
    return datetime(dia.year, dia.month, dia.day, hora, 0, tzinfo=SANTIAGO).astimezone(UTC)


class RespuestaDeHorariosTest(unittest.TestCase):
    def responder(self, decision, listas):
        """`listas` son los resultados sucesivos de list_available_slots."""
        with patch.object(whatsapp, 'list_available_slots', side_effect=listas), \
                patch.object(whatsapp.settings, 'killbichos_empresa_id', str(EMPRESA)), \
                patch.object(whatsapp, 'business_hours_text', return_value='Horario de atención: lunes a sábado, de 08:00 a 18:00.'):
            return whatsapp._availability_reply(MagicMock(), decision)

    def test_con_un_dia_lista_sus_horas(self):
        lunes = proximo_dia(0)
        reply = self.responder(
            dict(appointment_datetime=datetime(lunes.year, lunes.month, lunes.day, tzinfo=SANTIAGO).isoformat()),
            [[slot(lunes, 8), slot(lunes, 9), slot(lunes, 10)]],
        )
        self.assertIn(f'lunes {lunes.strftime("%d/%m")}', reply)
        self.assertIn('08:00, 09:00 y 10:00', reply)
        self.assertIn('hora de Chile', reply)

    def test_un_dia_sin_horas_explica_el_horario_y_ofrece_los_proximos(self):
        domingo, lunes = proximo_dia(6), proximo_dia(0)
        reply = self.responder(
            dict(appointment_datetime=datetime(domingo.year, domingo.month, domingo.day, tzinfo=SANTIAGO).isoformat()),
            [[], [slot(lunes, 8), slot(lunes, 9)]],
        )
        self.assertIn('Ese día no tengo horas libres', reply)
        self.assertIn('lunes a sábado, de 08:00 a 18:00', reply)
        self.assertIn('08:00 y 09:00', reply)

    def test_sin_dia_ofrece_los_proximos_con_el_horario_de_atencion(self):
        lunes, martes = proximo_dia(0), proximo_dia(1)
        reply = self.responder(dict(appointment_datetime=None), [[slot(lunes, 17), slot(martes, 8)]])
        self.assertNotIn('Ese día', reply)
        self.assertIn('Horario de atención', reply)
        self.assertIn('17:00', reply)
        self.assertIn(f'martes {martes.strftime("%d/%m")}', reply)

    def test_si_no_hay_ninguna_hora_avisa_que_un_operador_contactara(self):
        reply = self.responder(dict(appointment_datetime=None), [[]])
        self.assertIn('Un operador te contactará', reply)

    def test_una_fecha_invalida_se_trata_como_sin_dia(self):
        lunes = proximo_dia(0)
        reply = self.responder(dict(appointment_datetime='mañana'), [[slot(lunes, 8)]])
        self.assertIn('Las próximas horas libres', reply)


class AgenteHorariosTest(unittest.TestCase):
    def test_list_availability_es_una_accion_valida(self):
        validada = agent._validate_decision(dict(action='list_availability', reply='x', appointment_datetime=None))
        self.assertEqual(validada['action'], 'list_availability')

    def test_el_prompt_pide_usar_la_accion(self):
        self.assertIn('list_availability', agent.SYSTEM_PROMPT)
        self.assertIn('list_availability', agent.SCHEDULING_REMINDER)
        self.assertIn('Horario de atención', agent.SYSTEM_PROMPT)


if __name__ == '__main__':
    unittest.main()
