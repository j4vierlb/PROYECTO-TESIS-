# WhatsApp saliente bloqueado por Twilio (error 20003) — perfil de cumplimiento

**Responsable:** Pedro Vergiu · **Abierto:** 14/11/2026 · **Estado:** pendiente de crear el perfil

## Qué pasa

Los mensajes que el sistema envía por iniciativa propia (aviso de visita,
recordatorio del día anterior y respuestas de un operador desde el panel)
fallan con el error **20003** de Twilio. La cuenta de Twilio de Pedro no tiene
un **perfil de cumplimiento aprobado** en Trust Hub, y sin él Twilio bloquea el
envío por su API REST.

Este bloqueo es de la cuenta, no del código. Estos mensajes salen por la API
REST (`app/whatsapp_saliente.py`). Las respuestas del agente al cliente van en
la respuesta del webhook (TwiML) y no usan esa API; hay que confirmar igual que
siguen llegando.

## Qué hace el backend mientras tanto

Twilio responde el 20003 con un HTTP 4xx, así que el backend lo trata como
error **permanente** y no reintenta:

- el mensaje queda en `mensajes_whatsapp` con `estado_entrega = 'failed'` y
  `error_entrega = '20003: …'`, y en el panel se ve como no entregado;
- un **recordatorio** que falló queda marcado en `visitas.recordatorio_enviado_at`
  y **no se vuelve a enviar solo** cuando se apruebe el perfil.

Mensajes bloqueados (para revisar después de la aprobación):

```sql
SELECT created_at, intencion_detectada, left(contenido, 60) AS contenido, error_entrega
FROM mensajes_whatsapp
WHERE error_entrega LIKE '20003%'
ORDER BY created_at;
```

## Qué tiene que hacer Pedro (en la consola de Twilio)

Lo hace el titular de la cuenta; no se puede hacer desde el repositorio.

- [ ] En **Trust Hub**, crear el **Primary Customer Profile** de tipo **individual**.
- [ ] Completar los datos personales, subir la **foto del carnet** y la **selfie**.
- [ ] Enviarlo a revisión. Twilio responde en unas horas o días.
- [ ] Anotar aquí la fecha de envío y la de aprobación (o el motivo si lo rechazan).

**No subir al repositorio** el carnet, la selfie, el RUT ni capturas donde se
vean. Para la evidencia basta una captura del estado del perfil
(*Twilio-approved*) con los datos personales tapados.

| Fecha | Estado del perfil | Nota |
|---|---|---|
| 14/11/2026 | No creado | Envío saliente bloqueado con 20003 |
| | Enviado a revisión | |
| | Aprobado / rechazado | |

## Después de la aprobación

1. Desde el panel, crear una visita para mañana a un cliente con el teléfono
   unido al Sandbox: debe llegar el aviso y quedar `delivered` o `read`.
2. En **WhatsApp**, responder desde el panel: debe llegar al teléfono.
3. Pulsar **Enviar recordatorios de mañana**: debe llegar el recordatorio.
4. Correr la consulta de arriba. Si hay recordatorios de visitas futuras que
   fallaron con 20003, liberarlos para que el ciclo los vuelva a enviar:

   ```sql
   UPDATE visitas SET recordatorio_enviado_at = NULL
   WHERE id IN (<ids de las visitas afectadas>) AND fecha_hora > now();
   ```

5. Guardar la evidencia con fecha en `pruebas/` y cambiar el estado de arriba.

**Plazo:** antes de la defensa. Si no está aprobado a tiempo, la demo muestra
solo la conversación con el agente (que no usa la API REST) y se explica este
bloqueo como un límite de la cuenta, no del sistema.
