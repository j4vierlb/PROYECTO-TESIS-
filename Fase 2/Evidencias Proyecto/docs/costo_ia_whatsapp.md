# Costo por mensaje del agente de WhatsApp (gpt-4.1-mini)

Estimación hecha el 09/10/2026 sobre el código actual de [`backend/app/ai/agent.py`](../backend/app/ai/agent.py).

## Precios de OpenAI (gpt-4.1-mini)

| Tipo de token | USD por 1 millón |
|---|---|
| Entrada | 0,40 |
| Entrada en caché | 0,10 |
| Salida | 1,60 |

Fuente: <https://developers.openai.com/api/docs/models/gpt-4.1-mini>. Tipo de cambio supuesto: 1 USD = 950 CLP.

## Tokens por llamada

Cada mensaje del cliente genera **una** llamada a OpenAI. Tokens medidos con `tiktoken` (codificación `o200k_base`):

| Parte | Tokens |
|---|---|
| `SYSTEM_PROMPT` (reglas) | 369 |
| Contexto (fecha, horario, cliente, dirección) | ~80 |
| Formato de los mensajes | ~10 |
| Historial: ~25 por mensaje, máximo 20 mensajes | 25 – 500 |
| **Entrada total** | **~485 – 960** |
| **Salida** (JSON con `action`, `reply`, etc.) | **~60** |

La caché de OpenAI solo se activa desde 1.024 tokens de entrada, así que con el historial limitado a 20 mensajes casi nunca aplica. Se calcula sin caché.

## Costo

| Caso | Entrada | Salida | USD | CLP |
|---|---|---|---|---|
| Primer mensaje de una conversación | 485 | 60 | 0,00029 | 0,28 |
| Mensaje con historial lleno (20) | 960 | 60 | 0,00048 | 0,46 |
| **Conversación típica de agendamiento** (5 mensajes del cliente) | 2.900 | 300 | **0,0016** | **1,5** |

**Resultado: ~0,3 a 0,5 CLP por mensaje, ~1,5 CLP por visita agendada.**

Con 300 conversaciones al mes (≈10 al día): ~0,50 USD/mes (~470 CLP) en OpenAI.

## Lo que no incluye

- **Twilio / WhatsApp**: el Sandbox es gratis. En producción Twilio cobra una tarifa por mensaje más la tarifa de Meta por conversación, que suele ser mayor que el costo de la IA. Revisar <https://www.twilio.com/whatsapp/pricing> antes de cotizar.
- **IA del croquis**: costo aparte (incluye imagen); ver [diseno_ia_croquis.md](diseno_ia_croquis.md).

## Cómo verificarlo con datos reales

La respuesta de OpenAI trae `usage.prompt_tokens` y `usage.completion_tokens`. Registrarlos durante la prueba HU-18 permite reemplazar esta estimación por el promedio real.
