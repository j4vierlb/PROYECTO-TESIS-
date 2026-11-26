# Evidencia del plan de contingencia cuando falla la IA (26 de noviembre de 2026)

Responsable: Javier Lara Bustos. Este registro documenta un caso real en el que el agente de IA no pudo responder y el sistema aplicó su mensaje de contingencia.

## Qué ocurrió

El 26 de noviembre de 2026, entre las 01:21 y las 01:22 (hora de Chile; 04:21 y 04:22 UTC), el servidor desplegado rechazó las consultas del agente a OpenAI con el error `401 Unauthorized`: la clave de OpenAI configurada en el servidor no era aceptada. No fue una caída del servicio de OpenAI, sino una clave inválida, que para el backend produce el mismo efecto: la llamada a la IA falla.

Desde el número de prueba se escribieron mensajes al WhatsApp del sistema ("Hola quiero agendar una visita" y "Por qué un operador ?"). A cada uno el sistema respondió:

> Gracias por escribirnos. Un operador te contactará pronto para ayudarte.

## Evidencia

- **Captura del panel:** [Contingencia_IA_2026-11-26_panel.png](Contingencia_IA_2026-11-26_panel.png). Muestra la bandeja de WhatsApp con la conversación, los mensajes del cliente de las 01:22, las respuestas de contingencia del agente con el estado "Entregado" y el botón "Tomar conversación". Los apellidos y los teléfonos de las otras conversaciones están tapados.
- **Registro del backend del servidor** (copia guardada en el servidor antes de cambiar la clave, sin datos sensibles; los identificadores de los mensajes se omiten aquí):

```
2026-11-26T04:21:49Z ERROR: app.routers.whatsapp - Falló el agente de IA
httpx.HTTPStatusError: Client error '401 Unauthorized' for url 'https://api.openai.com/v1/chat/completions'
POST /webhooks/whatsapp HTTP/1.1" 200 OK
2026-11-26T04:22:10Z ERROR: app.routers.whatsapp - Falló el agente de IA
httpx.HTTPStatusError: Client error '401 Unauthorized' for url 'https://api.openai.com/v1/chat/completions'
POST /webhooks/whatsapp HTTP/1.1" 200 OK
2026-11-26T04:22:48Z ERROR: app.routers.whatsapp - Falló el agente de IA
httpx.HTTPStatusError: Client error '401 Unauthorized' for url 'https://api.openai.com/v1/chat/completions'
POST /webhooks/whatsapp HTTP/1.1" 200 OK
```

Las horas del registro (04:21 y 04:22 UTC) coinciden con las 01:21 y 01:22 de Chile que muestra el panel. El webhook respondió 200 y Twilio confirmó la entrega.

## Qué demuestra

1. **El cliente no queda sin respuesta.** Recibe el mensaje de contingencia en vez de un silencio o un error.
2. **No se agenda nada ni se inventan datos.** El agente no decide nada cuando la IA falla.
3. **La conversación queda guardada** y visible en la bandeja del panel, con los mensajes del cliente y las respuestas del agente.
4. **Un operador puede intervenir.** Con "Tomar conversación" la IA deja de responder en esa conversación y la persona escribe al cliente desde el panel.

El comportamiento está en `routers/whatsapp.py` (líneas 326 a 329): se registra el error, se envía el mensaje de contingencia y la intención queda en `None`.

## Limitaciones

- No hay un aviso automático al operador: la conversación se ve si se abre la bandeja del panel.
- Esta evidencia corresponde a una clave inválida (401). Un tiempo de espera agotado o un error 5xx de OpenAI siguen sin prueba propia, aunque el código los trata en el mismo bloque.
- El caso se corrigió el mismo día reemplazando la clave en el servidor. Después del cambio no aparecieron más errores 401 de OpenAI en el backend.
