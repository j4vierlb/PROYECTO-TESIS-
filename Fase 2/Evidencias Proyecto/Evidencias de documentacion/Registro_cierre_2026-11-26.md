# Registro de cierre: limitaciones conocidas (26 de noviembre de 2026)

Responsable: Javier Lara Bustos. Este registro reúne lo que el sistema no hace, lo que no se probó y lo que quedó pendiente al cierre del proyecto. Lo que no está verificado se indica como "no verificado" o "pendiente".

## 1. Agendamiento por WhatsApp

- **Día y fecha que no coinciden.** El sistema no detecta si el día de la semana y la fecha que dice el cliente no corresponden (por ejemplo, "martes 16 de diciembre", que cae miércoles). El agente de IA solo recibe en su instrucción la fecha y el día de hoy, y el backend no revisa esa coincidencia. Qué fecha agenda en esa situación no está probado. Estado: pendiente de probar por WhatsApp.
- **Posible condición de carrera.** El agendamiento por WhatsApp busca un técnico libre y luego crea la visita, sin bloqueo ni restricción única en la base de datos. Si dos clientes piden la misma hora al mismo tiempo, podrían quedar con el mismo técnico. No se probó. El panel sí bloquea la fila del técnico al asignar una visita.
- **Caída de OpenAI.** Está implementado un mensaje de contingencia al cliente, pero solo se probó el caso sin clave de OpenAI (HU-18, caso 8). Una caída real (tiempo de espera o error del servicio) no tiene prueba registrada, y no existe un aviso automático al operador cuando la IA falla.
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
