"""El contexto que recibe la IA dice qué datos del cliente ya están guardados."""
import json
import unittest
from unittest.mock import MagicMock, patch

from app.ai import agent


def contexto_enviado(client_name, client_address, previous_visits):
    """Llama a generate_agent_decision con OpenAI simulado y devuelve los textos de
    contexto: el del principio y el recordatorio final."""
    respuesta = MagicMock()
    respuesta.json.return_value = {
        'choices': [{'message': {'content': json.dumps(dict(action='reply', intent='consulta', reply='hola'))}}]
    }
    cliente_http = MagicMock()
    cliente_http.__enter__.return_value.post.return_value = respuesta
    with patch.object(agent.settings, 'openai_api_key', 'clave-de-prueba'), \
            patch.object(agent.httpx, 'Client', return_value=cliente_http):
        agent.generate_agent_decision(
            [dict(emisor='cliente', contenido='hola')], client_name, client_address, previous_visits
        )
    payload = cliente_http.__enter__.return_value.post.call_args.kwargs['json']
    mensajes = payload['messages']
    return mensajes[1]['content'], mensajes[-1]['content']


class ContextoDelClienteTest(unittest.TestCase):
    def test_el_recordatorio_final_repite_los_datos_del_cliente(self):
        _, final = contexto_enviado('Ana Pérez', 'Av. Libertad 1000, Viña del Mar', 2)
        self.assertIn(agent.SCHEDULING_REMINDER, final)
        self.assertIn('Datos del cliente:', final)
        self.assertIn('NO le pidas el nombre en tu respuesta', final)
        self.assertIn('NO le pidas la dirección en tu respuesta', final)

    def test_el_recordatorio_final_de_un_cliente_nuevo_pide_los_datos(self):
        _, final = contexto_enviado('ayline', None, 0)
        self.assertIn('debes pedirle su nombre completo', final)
        self.assertIn('Pídele la dirección completa', final)
        self.assertNotIn('NO le pidas', final)

    def test_con_visitas_previas_no_se_pide_el_nombre(self):
        texto, _ = contexto_enviado('Ana Pérez', 'Av. Libertad 1000, Viña del Mar', 2)
        self.assertIn('Visitas previas: 2', texto)
        self.assertIn('nombre ya está confirmado', texto)
        self.assertNotIn('debes pedirle su nombre', texto)

    def test_con_direccion_registrada_no_se_vuelve_a_pedir(self):
        texto, _ = contexto_enviado('Ana Pérez', 'Av. Libertad 1000, Viña del Mar', 1)
        self.assertIn('Dirección registrada: Av. Libertad 1000, Viña del Mar', texto)
        self.assertIn('No se la pidas de nuevo', texto)

    def test_primera_visita_exige_pedir_el_nombre(self):
        texto, _ = contexto_enviado('ayline', None, 0)
        self.assertIn('primera visita: debes pedirle su nombre completo', texto)

    def test_visitas_desconocidas_se_tratan_como_primera_visita(self):
        texto, _ = contexto_enviado('ayline', None, None)
        self.assertIn('debes pedirle su nombre completo', texto)

    def test_sin_direccion_se_pide_completa(self):
        texto, _ = contexto_enviado('ayline', None, 0)
        self.assertIn('Dirección registrada: ninguna. Pídele la dirección completa', texto)

    def test_el_contexto_incluye_cliente_horario_y_fecha(self):
        texto, _ = contexto_enviado('Ana Pérez', None, 1)
        self.assertIn('Cliente: Ana Pérez.', texto)
        self.assertIn('Horario de atención', texto)
        self.assertIn('Fecha y hora actual', texto)


if __name__ == '__main__':
    unittest.main()
