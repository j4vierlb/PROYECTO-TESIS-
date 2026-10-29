"""El agente de WhatsApp debe presentarse como el asistente de Kill Bichos.

La conducta final depende del modelo, así que aquí se comprueba lo que sí es
nuestro: que la instrucción pida la presentación (solo en el primer mensaje) y
que el historial completo llegue a OpenAI, que es lo que le permite no
repetirla. OpenAI está simulado: no se hace ninguna llamada real.

Se ejecuta desde backend: python -m unittest tests.test_agente_presentacion -v
"""
import json
import unittest
from unittest.mock import MagicMock, patch

from app.ai import agent
from app.config import settings

RESPUESTA = {
    'choices': [{'message': {'content': json.dumps({
        'action': 'reply', 'intent': 'saludo', 'reply': 'Hola, soy el asistente virtual de Kill Bichos.',
        'appointment_datetime': None, 'client_address': None, 'notes': None,
    })}}],
}


def _llamar(historial):
    """Ejecuta generate_agent_decision con OpenAI simulado y devuelve el cuerpo enviado."""
    respuesta = MagicMock()
    respuesta.json.return_value = RESPUESTA
    cliente = MagicMock()
    cliente.__enter__.return_value.post.return_value = respuesta
    with patch.object(settings, 'openai_api_key', 'clave-de-prueba'), \
            patch('app.ai.agent.httpx.Client', return_value=cliente):
        agent.generate_agent_decision(historial, 'Javier Lara', 'Viana 1233')
    return cliente.__enter__.return_value.post.call_args.kwargs['json']


class AgentePresentacionTest(unittest.TestCase):
    def test_la_instruccion_pide_presentarse_como_asistente_de_kill_bichos(self):
        prompt = agent.SYSTEM_PROMPT
        self.assertIn('asistente virtual de Kill Bichos', prompt)
        self.assertIn('primer mensaje', prompt)

    def test_la_instruccion_evita_repetir_la_presentacion(self):
        self.assertIn('no repitas la presentación', agent.SYSTEM_PROMPT)

    def test_primer_mensaje_envia_la_instruccion_a_openai(self):
        cuerpo = _llamar([{'emisor': 'cliente', 'contenido': 'Hola'}])
        sistema = [m['content'] for m in cuerpo['messages'] if m['role'] == 'system']
        self.assertTrue(any('asistente virtual de Kill Bichos' in texto for texto in sistema))
        self.assertEqual(cuerpo['messages'][-2]['content'], 'Hola')

    def test_el_historial_completo_llega_para_poder_distinguir_el_primer_mensaje(self):
        historial = [
            {'emisor': 'cliente', 'contenido': 'Hola'},
            {'emisor': 'agente_ia', 'contenido': 'Hola, soy el asistente virtual de Kill Bichos.'},
            {'emisor': 'cliente', 'contenido': 'Quiero agendar una visita'},
        ]
        cuerpo = _llamar(historial)
        roles = [m['role'] for m in cuerpo['messages'] if m['role'] != 'system']
        self.assertEqual(roles, ['user', 'assistant', 'user'])


if __name__ == '__main__':
    unittest.main()
