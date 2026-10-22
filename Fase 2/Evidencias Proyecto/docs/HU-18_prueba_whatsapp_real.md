# HU-18 — Prueba real de WhatsApp (Twilio Sandbox + ngrok)

## Fecha

| | |
|---|---|
| **Fecha** | planificada: martes 13/10/2026; realizada: martes 20/10/2026 desde las 02:27 (hora de Chile) |
| **Responsable** | Pedro Vergiu |
| **Duración estimada** | 1 hora |
| **Fecha límite** | martes 13/10/2026 (no se cumplió: faltaban WSL 2/Docker y las cuentas de Twilio y ngrok) |

## Requisitos antes de la prueba

- [ ] `.env` **de la raíz del repo** (copiado de `.env.example`) con `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_NUMBER` y `OPENAI_API_KEY` completos. Con `docker compose up` el backend lee **solo** ese archivo (`env_file: .env`); `backend/.env` se usa únicamente si el backend se corre fuera de Docker con `uvicorn`.
- [ ] `KILLBICHOS_OPERADOR_ID` = id del operador con que se inicia sesión en la app, para que la visita del caso 3 aparezca en su agenda.
- [ ] Teléfono unido al Sandbox (mensaje `join <código>` al +1 415 523 8886).
- [ ] `docker compose up --build` desde la raíz (la base ya carga `schema.sql`, `seed.sql` y `migracion_message_sid.sql`). Si se cambia el `.env`, reiniciar el backend: `docker compose up -d backend`.
- [ ] ngrok instalado y con sesión iniciada (`ngrok config add-authtoken ...`).
- [ ] `TWILIO_VALIDATE_SIGNATURE=true` y `TWILIO_WEBHOOK_URL` = URL de ngrok + `/webhooks/whatsapp`.

Pasos detallados: [backend/README.md](../backend/README.md), sección "Prueba real con WhatsApp".

## Casos de prueba

| # | Qué se envía por WhatsApp | Resultado esperado | OK |
|---|---|---|---|
| 1 | `Hola, ¿qué servicios tienen?` | Respuesta de consulta, sin agendar ni inventar precios | ☑ |
| 2 | (número nuevo) `Quiero agendar hoy a las 17:00` (hoy, dentro del horario 08:00–18:00 y al menos 1 h después de la hora de la prueba) | Pide la dirección antes de agendar | ☑ |
| 3 | `Av. Macul 1234, Macul` | Confirma la visita; aparece en el panel web y en la pestaña **Hoy** de la app del operador | ☑ (BD verificada; faltan capturas de panel y app) |
| 4 | Pedir un horario fuera de atención (ej. domingo 20:00) | Ofrece el siguiente horario libre | ☑ (falló el 20/10; corregido el 21/10 y repetido desde el teléfono el 22/10) |
| 5 | Pedir un horario a menos de 1 h de otra visita | Ofrece un horario alternativo | ☑ |
| 6 | Aceptar el horario alternativo (`sí, ese me sirve`) | Agenda en el horario ofrecido | ☑ |
| 7 | `Quiero cancelar mi visita` | Indica que un operador confirmará; no cambia nada en la base | ☑ |
| 8 | `OPENAI_API_KEY` vacía y reiniciar el backend | Mensaje de contingencia "un operador te contactará" | ☐ |
| 9 | `curl` al webhook sin firma, con validación activa | 403 Firma de Twilio inválida | ☑ |

## Cuenta Trial de Twilio: cómo se hizo la prueba

La cuenta Trial nueva de Twilio (consola `1console.twilio.com`) usa un número compartido, **+1 737 250 8034**, en vez del Sandbox clásico. Ese número **no permite configurar el webhook** y **solo deja enviar plantillas predefinidas** (error 21654 *ContentSid Required*). Crear plantillas propias también requiere Upgrade (error 20003).

Para no pagar el Upgrade se usó [`backend/scripts/puente_twilio_trial.py`](../backend/scripts/puente_twilio_trial.py). El script consulta por la API los mensajes que llegan al número, los reenvía al webhook con la misma firma `X-Twilio-Signature` que pone Twilio y registra la respuesta del bot. Con esto:

- **Sí se prueba de verdad:** el mensaje real desde WhatsApp, la validación de firma, el agente de OpenAI, el agendamiento en PostgreSQL, el panel y la app.
- **No se prueba:** que la respuesta llegue al teléfono, porque Twilio Trial la rechaza. La respuesta del bot queda en `mensajes_whatsapp` y en el log del puente, y esa es la evidencia.
- Twilio contesta además su propio *"Standard auto-reply"* en inglés a cada mensaje; no es del sistema.

### Respuestas del bot (log del puente)

| # | Mensaje real enviado | Respuesta del bot | Observación |
|---|---|---|---|
| 1 | Hola, ¿qué servicios tienen? | Hola, ofrecemos control de plagas para casas, departamentos y locales. ¿Quieres que te ayude con algo específico? | OK, sin precios inventados |
| 2 | Quiero agendar hoy a las 17:00 | Para agendar la visita necesito tu dirección, por favor. | OK |
| 3 | Av. Macul 1234, Macul | Perfecto 😊 Tu visita quedó agendada para el 20/10/2026 a las 17:00 (hora de Chile). | OK: en BD 20/10 17:00, `agendada`, `whatsapp_ia`, operador Juan Técnico |
| 4 | Quiero agendar el domingo a las 20:00 | El domingo no atendemos y el horario máximo es hasta las 18:00. ¿Quieres agendar otro día y hora dentro de nuestro horario de atención? | Parcial: la IA rechaza el horario sin consultar al backend y no ofrece el siguiente horario libre |
| 9 | `curl` sin firma al webhook por ngrok | `403 {"detail":"Firma de Twilio inválida"}` | OK |

### Corrección del caso 4 (21/10/2026)

**Causa:** el prompt del agente decía *"Solo propone o aceptes horarios dentro del horario de atención"*. La IA rechazaba el domingo por su cuenta y nunca le pasaba la fecha al backend, que es el que busca el siguiente horario libre.

**Cambio** (`backend/app/ai/agent.py`): la IA ya no rechaza horarios. Si el cliente pide una fecha y hora concretas y hay dirección, responde `create_appointment` con esa fecha, y el backend la valida y ofrece la alternativa.

**Verificación** con mensajes simulados al webhook (mismo formato y firma que Twilio, desde un número de prueba que luego se borró):

| Mensaje | Respuesta del sistema |
|---|---|
| Hola, mi dirección es Av. Macul 1234, Macul. Quiero agendar el domingo a las 20:00 | Ese horario no está disponible 😕 ¿Te acomoda el 26/10/2026 a las 08:00 (hora de Chile)? Si prefieres, indícame otro día y hora. |
| (otro cliente, con una visita del operador a las 17:30) Quiero agendar hoy a las 17:00 | Ese horario no está disponible 😕 ¿Te acomoda el 22/10/2026 a las 08:00 (hora de Chile)? … |
| sí, ese me sirve | Perfecto 😊 Tu visita quedó agendada para el 22/10/2026 a las 08:00 (hora de Chile). |

Consulta y cancelación se revisaron después del cambio y siguen respondiendo igual (sin agendar).

### Casos 4 a 7 desde el teléfono (22/10/2026)

Después del Upgrade de la cuenta Twilio se usó el **Sandbox de WhatsApp** (+1 415 523 8886): el teléfono se unió con `join <código>`, el webhook del Sandbox apunta a la URL de ngrok y Twilio llama directo al backend, sin el puente. Así la respuesta del bot sí llega al teléfono.

| # | Mensaje real enviado | Respuesta del bot | Verificación en BD |
|---|---|---|---|
| — | Hola | Hola, ¿en qué puedo ayudarte hoy? | intención `saludo` |
| 4 | Quiero agendar para el domingo a las 22:00 | Ese horario no está disponible 😕 ¿Te acomoda el 26/10/2026 a las 08:00 (hora de Chile)? Si prefieres, indícame otro día y hora. | no crea visita |
| 5 | Quiero agendar hoy a las 10:30 (había una visita a las 10:00) | Ese horario no está disponible 😕 ¿Te acomoda el 22/10/2026 a las 11:00 (hora de Chile)? … | no crea visita |
| 6 | Si, ese me sirve | Perfecto 😊 Tu visita quedó agendada para el 22/10/2026 a las 11:00 (hora de Chile). | visita 22/10 11:00, `agendada`, `whatsapp_ia` |
| 7 | Quiero cancelar mi visita | Para cancelar tu visita, un operador debe confirmar la modificación. Te contactaremos pronto. | intención `cancelar`; las visitas de las 10:00 y 11:00 siguen `agendada` |

Cada mensaje del cliente quedó en `mensajes_whatsapp` con su `message_sid` real de Twilio. Capturas: `HU18_00_sandbox_04_whatsapp.jpg` y `HU18_04-07_whatsapp.jpg` (fondo del chat difuminado).

## Evidencia (capturas)

Guardar en [`evidencias/HU-18/`](evidencias/HU-18/) con este nombre: `HU18_<n°caso>_<descripción>.png`.

1. `HU18_00_ngrok.png` — terminal de ngrok con la URL pública y los `POST /webhooks/whatsapp 200`.
2. `HU18_00_twilio_sandbox.png` — Sandbox settings con la URL configurada (ocultar el Auth Token).
3. `HU18_<caso>_whatsapp.png` — conversación en el teléfono, una por cada caso 1–8. Los casos 4 a 7 están en `HU18_00_sandbox_04_whatsapp.jpg` (unión al Sandbox, saludo y caso 4) y `HU18_04-07_whatsapp.jpg`.
4. `HU18_03_panel.png` — la visita creada en el panel web (origen `whatsapp_ia`).
5. `HU18_03_app.png` — la misma visita en la pestaña **Hoy** de la app móvil. La app solo muestra las visitas del día (`/operadores/me/visitas-hoy`): por eso el caso 2 agenda para hoy. Si se agendó para otro día, esta captura se toma ese día.
6. `HU18_03_bd.png` — `SELECT` en `mensajes_whatsapp` mostrando el historial y `message_sid`.
7. `HU18_09_curl_403.png` — respuesta 403 del caso 9.

**Antes de subir:** tapar números de teléfono reales, Account SID, Auth Token y `OPENAI_API_KEY` (también si se ven en la terminal o en el `.env`).

## Resultado

| Fecha real | Casos OK | Observaciones |
|---|---|---|
| 20–21/10/2026 (en curso) | 4/9 desde el teléfono; 4, 5 y 6 OK con mensajes simulados | Prueba con cuenta Trial vía puente (ver arriba). Caso 4 corregido el 21/10. Pendientes: casos 4–8 desde el teléfono y capturas de panel y app. |
| 22/10/2026 | 8/9 (casos 1–7 y 9) | Casos 4–7 desde el teléfono con el Sandbox después del Upgrade. Falta el caso 8 y las capturas de panel y app del caso 3. |
