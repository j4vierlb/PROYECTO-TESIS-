# HU-18 — Prueba real de WhatsApp (Twilio Sandbox + ngrok)

## Fecha

| | |
|---|---|
| **Fecha propuesta** | martes 13/10/2026, 16:00 (hora de Chile) — *por confirmar con el equipo* |
| **Responsable** | Pedro Vergiu |
| **Duración estimada** | 1 hora |
| **Fecha límite** | viernes 16/10/2026 (si el martes falla algo, se repite antes de esa fecha) |

## Requisitos antes de la prueba

- [ ] `backend/.env` con `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` y `OPENAI_API_KEY` completos.
- [ ] Teléfono unido al Sandbox (mensaje `join <código>` al +1 415 523 8886).
- [ ] Base de datos arriba con `schema.sql` + `seed.sql` (o con la migración `migracion_message_sid.sql`).
- [ ] ngrok instalado y con sesión iniciada (`ngrok config add-authtoken ...`).
- [ ] `TWILIO_VALIDATE_SIGNATURE=true` y `TWILIO_WEBHOOK_URL` = URL de ngrok + `/webhooks/whatsapp`.

Pasos detallados: [backend/README.md](../backend/README.md), sección "Prueba real con WhatsApp".

## Casos de prueba

| # | Qué se envía por WhatsApp | Resultado esperado | OK |
|---|---|---|---|
| 1 | `Hola, ¿qué servicios tienen?` | Respuesta de consulta, sin agendar ni inventar precios | ☐ |
| 2 | (número nuevo) `Quiero agendar mañana a las 10` | Pide la dirección antes de agendar | ☐ |
| 3 | `Av. Macul 1234, Macul` | Confirma la visita; aparece en el panel web y en la app del operador | ☐ |
| 4 | Pedir un horario fuera de atención (ej. domingo 20:00) | Ofrece el siguiente horario libre | ☐ |
| 5 | Pedir un horario a menos de 1 h de otra visita | Ofrece un horario alternativo | ☐ |
| 6 | Aceptar el horario alternativo (`sí, ese me sirve`) | Agenda en el horario ofrecido | ☐ |
| 7 | `Quiero cancelar mi visita` | Indica que un operador confirmará; no cambia nada en la base | ☐ |
| 8 | `OPENAI_API_KEY` vacía y reiniciar el backend | Mensaje de contingencia "un operador te contactará" | ☐ |
| 9 | `curl` al webhook sin firma, con validación activa | 403 Firma de Twilio inválida | ☐ |

## Evidencia (capturas)

Guardar en [`evidencias/HU-18/`](evidencias/HU-18/) con este nombre: `HU18_<n°caso>_<descripción>.png`.

1. `HU18_00_ngrok.png` — terminal de ngrok con la URL pública y los `POST /webhooks/whatsapp 200`.
2. `HU18_00_twilio_sandbox.png` — Sandbox settings con la URL configurada (ocultar el Auth Token).
3. `HU18_<caso>_whatsapp.png` — conversación en el teléfono, una por cada caso 1–8.
4. `HU18_03_panel.png` — la visita creada en el panel web (origen `whatsapp_ia`).
5. `HU18_03_app.png` — la misma visita en la agenda de la app móvil.
6. `HU18_03_bd.png` — `SELECT` en `mensajes_whatsapp` mostrando el historial y `message_sid`.
7. `HU18_09_curl_403.png` — respuesta 403 del caso 9.

**Antes de subir:** tapar números de teléfono reales, Account SID y Auth Token.

## Resultado

| Fecha real | Casos OK | Observaciones |
|---|---|---|
| | /9 | |
