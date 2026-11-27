# Verificación de WhatsApp después de reemplazar la clave de OpenAI (26 de noviembre de 2026)

Responsable: Javier Lara Bustos. Este registro muestra que el agendamiento por WhatsApp y el recordatorio volvieron a funcionar en el servidor desplegado después de reemplazar la clave de OpenAI que había vencido (ver [Contingencia_IA_2026-11-26.md](Contingencia_IA_2026-11-26.md)).

## Qué se hizo

Javier escribió al WhatsApp del sistema como un cliente de prueba y agendó una visita. Después recibió el recordatorio de esa visita. Esta parte la declara Javier y la vio en su teléfono y en el panel.

## Registro del backend

Se leyó el registro del servidor de la última hora con `docker compose logs -t --since 60m backend`, filtrando las líneas con las palabras `whatsapp`, `error` y `Falló`. Las horas están en UTC; en Chile son tres horas menos (21:48 y 21:49 del 26 de noviembre). Los identificadores de mensaje se omiten.

```
00:48:31  POST /webhooks/whatsapp          200 OK
00:48:33  POST /webhooks/whatsapp/estado   204 No Content
00:48:34  POST /webhooks/whatsapp          200 OK
00:48:34  POST /webhooks/whatsapp/estado   204 No Content
00:48:36  POST /webhooks/whatsapp/estado   204 No Content
00:48:37  POST /webhooks/whatsapp/estado   204 No Content
00:48:46  POST /webhooks/whatsapp          200 OK
00:48:49  POST /webhooks/whatsapp/estado   204 No Content
00:48:49  POST /webhooks/whatsapp/estado   204 No Content
00:49:32  app.whatsapp_saliente - Recordatorios de WhatsApp para el 2026-11-27: 1
00:49:34  POST /webhooks/whatsapp/estado   204 No Content
00:49:34  POST /webhooks/whatsapp/estado   204 No Content
```

## Qué demuestra

1. Tres mensajes del cliente llegaron al webhook y el backend respondió 200 a cada uno.
2. No aparece ninguna línea con `error` ni con `Falló` en esa hora, es decir, ninguna llamada a OpenAI falló (antes de reemplazar la clave aparecían 401).
3. El sistema buscó los recordatorios del día siguiente, encontró uno y Twilio informó el estado de ese mensaje.

## Qué no demuestra

- El registro no muestra el contenido de los mensajes ni la creación de la visita en la base de datos. Eso se comprobó a mano en el panel y en el teléfono.
- Los avisos de estado confirman que Twilio respondió y que el backend los registró, pero este registro no distingue si el mensaje quedó entregado o fallido.
- El filtro solo muestra las líneas con esas palabras; una falla que no las contenga no aparecería.
- Es una sola prueba, de un solo cliente, y no se midió el comportamiento con varios clientes a la vez.
