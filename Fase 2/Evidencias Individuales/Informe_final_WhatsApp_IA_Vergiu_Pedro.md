# Informe final — Agente de WhatsApp con IA: costos, limitaciones y paso a producción

**Responsable:** Pedro Vergiu · **Fecha:** 06/11/2026

Esta sección resume cómo funciona el canal de WhatsApp de Kill Bichos IA, cuánto cuesta operarlo, qué límites tiene la demostración actual y qué debe hacer la empresa para usarlo con clientes reales. Las fuentes internas son [`costo_ia_whatsapp.md`](../Evidencias%20Proyecto/docs/costo_ia_whatsapp.md), la prueba [`HU-18_prueba_whatsapp_real.md`](../Evidencias%20Proyecto/docs/HU-18_prueba_whatsapp_real.md) y la sección "Limitaciones conocidas y pasos a producción" del [`README.md`](../../README.md) de la raíz.

## 1. Qué hace el agente

El cliente escribe al número de WhatsApp de la empresa. Twilio reenvía el mensaje al backend (`POST /webhooks/whatsapp`), que valida la firma de Twilio, guarda el mensaje y le pide a OpenAI (`gpt-4.1-mini`) una decisión en JSON: responder una consulta, pedir la dirección o agendar. La IA no decide la disponibilidad: el backend valida el horario de atención y los choques con otras visitas, y si el horario no sirve ofrece el siguiente libre. La visita creada queda con origen `whatsapp_ia` y aparece en el panel web y en la app del técnico.

Además, el sistema envía mensajes por iniciativa propia: aviso al agendar, reagendar o cancelar desde el panel, recordatorio el día anterior y respuestas escritas por un operador desde la pestaña WhatsApp del panel (mientras un operador atiende, la IA no responde).

Si OpenAI falla (sin clave, tope de gasto alcanzado, caída o respuesta inválida), el cliente recibe un mensaje de contingencia: *"Gracias por escribirnos 😊 Un operador te contactará pronto para ayudarte."* No se agenda nada y el error queda en el log.

## 2. Costos

### 2.1 OpenAI (IA)

Precios de `gpt-4.1-mini`: 0,40 USD por millón de tokens de entrada y 1,60 USD por millón de salida. Tokens medidos con `tiktoken` sobre el prompt real del agente:

| Uso | Costo unitario | Volumen supuesto al mes | USD/mes |
|---|---|---|---|
| Mensaje de WhatsApp | 0,3–0,5 CLP | — | — |
| Conversación de agendamiento (5 mensajes) | ~1,5 CLP | 300 conversaciones | ~0,50 |
| Sugerencia de croquis con IA | ~1,4 CLP | 150–300 croquis | ~0,25–0,45 |
| **Total OpenAI** | | | **~1 USD (~950 CLP)** |

La cuenta de OpenAI de producción es de Kill Bichos. Se recomienda un tope mensual de **US$10** y una alerta a los **US$5** (*Settings → Limits*). Si se llega al tope, el sistema sigue funcionando sin IA: WhatsApp responde el mensaje de contingencia y el croquis usa el plan B por reglas.

### 2.2 Twilio y Meta (mensajería)

En producción este es el costo principal, mayor que el de la IA. Se compone de dos cobros por mensaje:

- **Twilio:** **0,005 USD por mensaje**, enviado o recibido, más 0,001 USD por cada mensaje que termine como *Failed* (confirmado en la página oficial de Twilio, *pricing current as of September 2026*, revisada el 07/11/2026).
- **Meta:** cobra por cada **plantilla** enviada (avisos y recordatorios), según país y categoría. La documentación oficial de Meta confirma que Chile tiene tarifa propia, que la tabla vigente rige desde el **1 de octubre de 2026** y que desde esa fecha las plantillas *utility* se cobran también dentro de la ventana de 24 h. Las respuestas de texto libre del bot a un cliente que escribió no pagan plantilla. **El valor para Chile no se pudo leer automáticamente** (solo aparece en el selector interactivo y en el CSV de la tabla de Meta); ~0,02 USD por plantilla *utility* viene de una fuente externa y es una **estimación** hasta revisarlo a mano.

Estimación orientativa con 300 conversaciones (≈10 mensajes entre ida y vuelta cada una) y 300 avisos o recordatorios al mes:

| Concepto | Cálculo | USD/mes |
|---|---|---|
| Twilio, conversaciones | 3.000 × 0,005 | ~15 |
| Twilio, avisos y recordatorios | 300 × 0,005 | ~1,5 |
| Meta, plantillas | 300 × ~0,02 | ~6 |
| **Total mensajería** | | **~22,5 USD (~21.000 CLP)** |

A esto se suma el número de teléfono en Twilio (cargo mensual fijo) y el servidor (sección 4). El cobro de Twilio está confirmado; el de Meta queda como estimación. Antes de dar la cifra a la empresa, abrir <https://whatsappbusiness.com/es-la/products/platform-pricing/>, elegir Chile, USD y la categoría *utility*, y reemplazar los ~0,02 USD de la tabla.

### 2.3 Google Maps

La geocodificación de direcciones y la foto satelital del croquis se cobran en Google Cloud. Con este volumen debería quedar dentro de la cuota gratuita mensual; se debe confirmar en <https://mapsplatform.google.com/pricing/>.

## 3. Limitaciones del Sandbox de Twilio

La demostración usa el **Sandbox de WhatsApp de Twilio** (+1 415 523 8886), un entorno de prueba gratuito. Permite mostrar el flujo completo (el cliente escribe, la IA responde, se agenda y la visita aparece en el panel y en la app), pero:

1. **Cada teléfono debe unirse antes** enviando `join <código>` al número del Sandbox (o escaneando el QR de la portada). La unión vence a las **72 horas**.
2. **No es público:** solo responde a los teléfonos unidos. Un cliente real de Kill Bichos no podría escribir.
3. **Ventana de 24 h:** los avisos y recordatorios que envía el sistema solo salen como texto libre si el cliente escribió en las últimas 24 h. Fuera de esa ventana WhatsApp exige una plantilla aprobada por Meta; sin ella el mensaje queda guardado como **no enviado** y el panel no deja responder (`409`).
4. **El número es de Twilio**, compartido y en inglés, no el de la empresa.
5. **URL pública:** Twilio necesita una dirección pública. En la demo local se usa un túnel de ngrok (servicio opcional en `docker-compose.yml`), y en ese modo el bot solo responde mientras el computador que corre el túnel está encendido. <!-- Actualizar cuando el backend esté desplegado en el servidor: indicar su URL fija y que este límite ya no aplica. -->

Durante la prueba HU-18 también se encontró que la **cuenta Trial** nueva de Twilio no permite configurar el webhook ni enviar texto libre (errores 21654 y 20003). Se trabajó primero con un script puente que reenviaba los mensajes al webhook y, tras el Upgrade de la cuenta, con el Sandbox. Resultado: 9 de 9 casos aprobados. Los casos 1 a 7 y 9 se hicieron con mensajes reales desde el teléfono. El caso 8 (sin clave de OpenAI) se verificó el 06/11/2026 enviando al webhook mensajes firmados igual que Twilio: el cliente recibió el mensaje de contingencia y no se agendó nada (ver HU-18).

## 4. Pasos para pasar a producción

La puesta en marcha real es una decisión y un gasto de la empresa, no del equipo de desarrollo. Necesita:

1. **Cuenta de Meta Business** de Kill Bichos, verificada.
2. **Número de WhatsApp propio** registrado en Twilio como *WhatsApp Sender* (puede ser el número comercial actual si no está usado en la app de WhatsApp normal).
3. **Plantillas aprobadas por Meta** para el aviso de visita y el recordatorio, en español, con categoría *utility*.
4. **Servidor siempre encendido** con dirección fija y HTTPS (un VPS o servicio en la nube) en vez de ngrok, con copia de seguridad de la base.
5. **Cuentas de pago** de Twilio y OpenAI a nombre de la empresa, con tope de gasto y alertas.

El código ya está preparado: solo cambian variables del `.env`, sin modificar el programa:

| Variable | Valor en producción |
|---|---|
| `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` | Credenciales de la cuenta de la empresa |
| `TWILIO_WHATSAPP_NUMBER` | Número propio aprobado |
| `TWILIO_WEBHOOK_URL` | `https://<dominio-del-servidor>/webhooks/whatsapp` |
| `TWILIO_VALIDATE_SIGNATURE` | `true` (obligatorio; con `false` cualquiera podría enviar mensajes falsos) |
| `TWILIO_CONTENT_SID_AVISO`, `TWILIO_CONTENT_SID_RECORDATORIO` | `ContentSid` de las plantillas aprobadas |
| `OPENAI_API_KEY` | Clave de la cuenta de la empresa |

Recomendaciones antes de abrir el canal: probar las plantillas con un número interno, revisar durante la primera semana las conversaciones en el panel para ajustar el prompt, y registrar `usage` de OpenAI para reemplazar la estimación de costos por el promedio real.

## 5. Conclusión

El agente de WhatsApp cumple el flujo de agendamiento con un costo de IA bajo (~1 USD al mes). El costo relevante en producción es la mensajería de Twilio y Meta (del orden de 20–25 USD al mes con el volumen supuesto, por confirmar). La principal limitación actual no es técnica sino de cuentas: el Sandbox solo sirve para demostrar. Para atender clientes reales, Kill Bichos debe registrar su número, aprobar plantillas y contratar un servidor; el sistema no requiere cambios de código para ese paso.

## Fuentes externas

- Precios de `gpt-4.1-mini`: <https://developers.openai.com/api/docs/models/gpt-4.1-mini>
- Precios de WhatsApp en Twilio: <https://www.twilio.com/en-us/whatsapp/pricing>
- Tarifas de Meta por país (selector interactivo): <https://whatsappbusiness.com/es-la/products/platform-pricing/>
- Aviso de Twilio sobre el cambio de precios de Meta (octubre 2026): <https://support.twilio.com/hc/en-us/articles/53100480177819-Notice-Changes-to-WhatsApp-s-Pricing-October-2026>
- Precios de la plataforma de WhatsApp de Meta: <https://developers.facebook.com/docs/whatsapp/pricing>
- Calculadora con tarifas por país (referencial, no oficial): <https://zernio.com/whatsapp-api-pricing>
