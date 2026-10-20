# Costo de OpenAI: agente de WhatsApp e IA del croquis (gpt-4.1-mini)

Estimación hecha el 09/10/2026 sobre [`backend/app/ai/agent.py`](../backend/app/ai/agent.py) y actualizada el 19/10/2026 con la IA del croquis ([`backend/app/ai/croquis_agent.py`](../backend/app/ai/croquis_agent.py)).

## Quién paga y tope de gasto

| | |
|---|---|
| **Quién paga** | **Kill Bichos.** La cuenta de OpenAI y la clave `OPENAI_API_KEY` de producción son de la empresa, con su medio de pago. El equipo usa su propia clave solo para desarrollo y pruebas. |
| **Gasto estimado** | **~1 USD/mes (~950 CLP)**: WhatsApp ~0,50 USD + croquis ~0,25–0,45 USD (detalle abajo). |
| **Tope mensual** | **US$10/mes**, configurado en *Settings → Limits* de la cuenta de OpenAI (unas 10 veces lo estimado). |
| **Alerta** | Correo a Kill Bichos al llegar a **US$5** en el mes. |

**Si se llega al tope**, OpenAI rechaza las llamadas y el sistema sigue funcionando sin IA. El bot de WhatsApp responde el mensaje de contingencia ("un operador te contactará") y el croquis usa el plan B por reglas. El tope protege ante un abuso (miles de mensajes al bot) o un error que haga llamadas en bucle.

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

## Costo del agente de WhatsApp

| Caso | Entrada | Salida | USD | CLP |
|---|---|---|---|---|
| Primer mensaje de una conversación | 485 | 60 | 0,00029 | 0,28 |
| Mensaje con historial lleno (20) | 960 | 60 | 0,00048 | 0,46 |
| **Conversación típica de agendamiento** (5 mensajes del cliente) | 2.900 | 300 | **0,0016** | **1,5** |

**Resultado: ~0,3 a 0,5 CLP por mensaje, ~1,5 CLP por visita agendada.**

Con 300 conversaciones al mes (≈10 al día): ~0,50 USD/mes (~470 CLP) en OpenAI.

## Costo de la IA del croquis

Una llamada por croquis (`POST /croquis/{visita_id}/sugerencia`). Si se usa el plan B por reglas, no se llama a OpenAI y no hay costo.

| Parte | Tokens |
|---|---|
| Foto satelital 640×640 | ~650 |
| `SYSTEM_PROMPT` + datos del predio y trampas existentes | ~600 |
| **Entrada total** | **~1.250** |
| **Salida** (JSON con 7–15 trampas, cada una con zona y motivo) | **~600** |

1.250 × 0,40 + 600 × 1,60 por millón ≈ **0,0015 USD (~1,4 CLP) por croquis**.

Con 150–300 croquis al mes (uno por visita): ~0,25–0,45 USD/mes.

## Total mensual estimado

| Uso | Cantidad al mes | USD/mes |
|---|---|---|
| WhatsApp | 300 conversaciones | ~0,50 |
| Croquis | 150–300 | ~0,25–0,45 |
| **Total OpenAI** | | **~1 USD (~950 CLP)** |

## Lo que no incluye

- **Twilio / WhatsApp**: el Sandbox es gratis. En producción Twilio cobra una tarifa por mensaje más la tarifa de Meta por conversación, que suele ser mayor que el costo de la IA. Revisar <https://www.twilio.com/whatsapp/pricing> antes de cotizar.
- **Google Maps** (geocodificación y foto satelital del croquis): se cobra aparte en Google Cloud; con este volumen debería quedar dentro de la cuota gratuita mensual. Confirmar en <https://mapsplatform.google.com/pricing/>.

## Cómo verificarlo con datos reales

La respuesta de OpenAI trae `usage.prompt_tokens` y `usage.completion_tokens`. Registrarlos durante la prueba HU-18 permite reemplazar esta estimación por el promedio real. La IA del croquis ya los escribe en el log (`Croquis IA: tokens entrada=… salida=…`).
