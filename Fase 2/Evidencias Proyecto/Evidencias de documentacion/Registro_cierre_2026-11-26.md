# Registro de cierre: limitaciones conocidas (26 de noviembre de 2026)

**Nota:** este registro corresponde al cierre del proyecto para la comisión del 3 de diciembre de 2026. El desarrollo continuará después de esa fecha. Las limitaciones listadas más abajo (aviso automático al operador cuando falla la IA, bloqueo de concurrencia en WhatsApp, validación de día y fecha, prueba de conflicto offline y evidencia de Android) son mejoras identificadas, no defectos ocultos.

Responsable: Javier Lara Bustos. Este registro reúne lo que el sistema no hace, lo que no se probó y lo que quedó pendiente al cierre del proyecto. Lo que no está verificado se indica como "no verificado" o "pendiente".

## 1. Agendamiento por WhatsApp

- **Día y fecha que no coinciden.** El sistema no detecta si el día de la semana y la fecha que dice el cliente no corresponden (por ejemplo, "martes 16 de diciembre", que cae miércoles). El agente de IA solo recibe en su instrucción la fecha y el día de hoy, y el backend no revisa esa coincidencia. Qué fecha agenda en esa situación no está probado. Estado: pendiente de probar por WhatsApp.
- **Posible condición de carrera.** El agendamiento por WhatsApp busca un técnico libre y luego crea la visita, sin bloqueo ni restricción única en la base de datos. Si dos clientes piden la misma hora al mismo tiempo, podrían quedar con el mismo técnico. No se probó. El panel sí bloquea la fila del técnico al asignar una visita.
- **Caída de OpenAI.** Está implementado un mensaje de contingencia al cliente, y se probó en dos casos: sin clave de OpenAI (HU-18, caso 8) y con una clave rechazada por OpenAI (error 401) en el servidor el 26 de noviembre de 2026, documentado con captura en [Contingencia_IA_2026-11-26.md](Contingencia_IA_2026-11-26.md). Un tiempo de espera agotado o un error 5xx de OpenAI no tienen prueba registrada, y no hay un aviso automático al operador cuando la IA falla (`whatsapp.py`, líneas 326 a 329: se registra el error, se envía el mensaje de contingencia al cliente y la intención queda en `None`). La conversación queda en la bandeja del panel y el operador la ve si la abre. Comprobado por lectura del código; no hay prueba automatizada de este caso.
- **Evidencia real de la contingencia.** El 26 de noviembre de 2026 a la 01:22 (hora de Chile) la IA no respondió porque OpenAI rechazó la clave del servidor (error 401). El cliente recibió el mensaje de contingencia y la conversación quedó visible en el panel, donde el operador puede tomarla. Ver la captura [HU18_contingencia_IA_26-11_privacidad.png](HU18_contingencia_IA_26-11_privacidad.png) y la nota [Contingencia_IA_2026-11-26.md](Contingencia_IA_2026-11-26.md).
- **Vencimiento de la clave de OpenAI.** La clave del servidor se creó el 19 de octubre de 2026 con vencimiento a 30 días y dejó de valer el 18 de noviembre, por lo que desde ese día la IA fallaba con 401 sin que nadie lo notara hasta el 26 de noviembre. El sistema no avisa antes de que una clave venza. Se reemplazó por una clave nueva el mismo día y se verificó con una visita agendada y su recordatorio ([Verificacion_WhatsApp_2026-11-26.md](Verificacion_WhatsApp_2026-11-26.md)). La clave nueva se creó sin fecha de caducidad (confirmado por Javier en el panel de OpenAI). Sigue sin existir un aviso previo si en el futuro se usa una clave con vencimiento.
- **Caída del servidor.** No se probó qué ocurre con los mensajes de WhatsApp cuando el servidor está caído. Estado: no verificado.

## 2. Recuperación de contraseña por correo

Probada en el entorno local. No está habilitada en el servidor, por lo que el caso SRV-11 figura como "No aplica" en la validación del servidor.

## 3. Modo offline de la app

- **Conflicto en iPhone.** La prueba del 16 de noviembre de 2026 no incluyó un conflicto con el servidor (por ejemplo, una visita cancelada desde el panel mientras la app estaba sin conexión). Estado: prueba no realizada.
- **Android (Redmi).** La prueba es parcial: se perdieron los registros del backend al reconstruirlo el 14 de noviembre, por lo que la ejecución única de los cambios de la cola quedó sin verificar.

## 4. Costo de la IA

La estimación es de aproximadamente 1 USD al mes, con un tope de US$10 y una alerta en US$5. El consumo real no se ha medido.

## 5. Evidencia pendiente

Faltan las capturas `HU18_03_panel.png` y `HU18_03_app.png` de la prueba HU-18.

## 6. Despliegue

El despliegue es manual: `git pull --ff-only` y `docker compose up -d --build` en el servidor, después de guardar los registros del backend. No hay integración ni despliegue continuos (CI/CD).

## 7. Roles y proceso

- **Roles:** Juan Bórquez fue Product Owner y desarrollador; Javier Lara fue desarrollador y asumió en la práctica la función de Scrum Master y la integración de los cambios a `main`; Pedro Vergiu fue desarrollador. Javier convocaba las reuniones.
- **Revisión y retrospectiva:** fueron informales. No se levantaron actas y los acuerdos quedaron en el chat de WhatsApp del equipo.
- **Revisión de los Pull Requests (al 24 de noviembre de 2026, según GitHub):** de 61 PR integrados, 39 tuvieron una revisión aprobada de un integrante distinto del autor y 22 se integraron sin revisión registrada. Por autor: Javier, 20 con revisión y 14 sin; Juan, 11 con revisión y 5 sin; Pedro, 8 con revisión y 3 sin.
