# Recuperación de contraseña del panel web

Implementación local del 26/10/2026, en `juan`. Incluye administradores y
coordinadores activos del panel; no cambia la recuperación de los operadores
de la app móvil. No se han cambiado credenciales reales ni desplegado esta
versión en el backend de trabajo.

## Flujo

1. En el login: **Olvidé mi contraseña**, ingresar correo.
2. `POST /auth/forgot-password`, JSON `{"email":"admin@example.test"}`.
   Responde 202 y el mismo mensaje exista o no una cuenta activa del panel.
3. El correo contiene un enlace a la URL configurada del panel. El token va
   en el fragmento `#restablecer=…`, no en el query string. El panel lo quita
   de la barra/historial al abrir y no lo almacena en localStorage/sessionStorage.
4. Ingresar y confirmar una clave de al menos 12 caracteres, máximo 72 bytes
   UTF-8 (límite del bcrypt existente). Nunca se trunca la contraseña.
5. `POST /auth/reset-password`, JSON con `token` y `password`, sin sesión previa.
6. Se cambia el hash bcrypt y se vuelve al login. No inicia sesión automáticamente.

Los enlaces duran 15 minutos, usan 32 bytes criptográficamente aleatorios y
la base solo guarda su SHA-256. El canje bloquea la fila del usuario y vuelve
a verificar el token después de adquirir el lock: dos peticiones simultáneas
no pueden consumirlo dos veces. Un cambio invalida **todos** los enlaces y
access/refresh tokens anteriores de esa cuenta mediante `session_version`.
No afecta las sesiones de otras cuentas ni de operadores móviles.

Tokens anteriores al despliegue sin `sv` se interpretan como versión 0: siguen
válidos hasta su vencimiento o hasta el primer restablecimiento de la cuenta.

## Coordinación necesaria con Javier

Confirmar servicio SMTP autorizado, remitente, host, puerto, usuario y
contraseña de aplicación/SMTP, además de la URL del panel que abrirá el usuario.
**No enviarlos en comentarios de PR ni subirlos a Git.** Configurarlos directamente
en el `.env` privado que lee Docker Compose (o en el backend local si no usa Docker).
No sirven para esto las claves de Google Maps, OpenAI o Twilio.

Al revisar la publicación se detectó que el JWT_SECRET local coincidía con el
valor de las plantillas históricas. Las plantillas ahora contienen solo un
marcador: generar un secreto privado distinto por entorno antes de exponer el
backend. Quitar el ejemplo no elimina el valor antiguo del historial. No se
rotó el `.env` local automáticamente, ya que hacerlo invalida las sesiones de
todos los usuarios, incluidos operadores; coordinar esa renovación con el equipo.

```dotenv
PASSWORD_RESET_ENABLED=false
PASSWORD_RESET_PANEL_URL=http://localhost:8080
SMTP_HOST=
SMTP_PORT=587
SMTP_SECURITY=starttls
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=
```

`SMTP_SECURITY=starttls` usa normalmente 587. Para TLS implícito, `ssl` y 465.
No se permite SMTP en texto plano ni desactivar verificación de certificados.
El remitente debe ser una dirección autorizada por el proveedor. El envío usa
usuario/contraseña SMTP; OAuth o APIs de proveedores necesitan un adaptador.
Fuera de localhost/loopback, la URL del panel debe ser **HTTPS**. No se deriva
del header Host ni del email proporcionado. `localhost` sirve únicamente para
abrir el correo en el mismo PC que ejecuta el panel, no desde otro teléfono.

Después de configurar y probar el proveedor, activar `PASSWORD_RESET_ENABLED=true`.
No poner `true` con datos de ejemplo. Sin configuración, la solicitud responde
503 para cualquier correo y el panel indica contactar al soporte.

## Migración y despliegue (pendientes en la base de trabajo)

1. Resguardar la base con el procedimiento de respaldo del equipo.
2. Aplicar **antes de reconstruir el backend** la migración idempotente
   `database/migracion_password_reset.sql`. Agrega una columna y dos tablas;
   no elimina cuentas, visitas, fotos ni croquis. El backend nuevo consulta la
   columna `session_version` incluso con recuperación deshabilitada.
3. Para PowerShell, desde la raíz del repositorio, con usuario/base habituales:

   ```powershell
   Get-Content -Raw "Fase 2/Evidencias Proyecto/database/migracion_password_reset.sql" | docker compose exec -T db psql -v ON_ERROR_STOP=1 -U killbichos -d killbichos
   docker compose up -d --build backend web
   ```

   Ajustar usuario/base si el `.env` del equipo define otros. No usar `down -v`
   ni volver a ejecutar `schema.sql` sobre una base con datos. Para instalaciones
   nuevas, `schema.sql` ya incluye estas estructuras.
4. Probar con una cuenta y un buzón controlados por el equipo: recepción real,
   abrir enlace, cambiar clave, rechazo de clave anterior, login nuevo, cierre
   de sesiones anteriores y rechazo al reutilizar enlace.
5. Confirmar entrega/no spam, HTTPS y registros del proveedor. No registrar
   cuerpo de peticiones de autenticación, contraseñas o enlaces en API/proxy.

## Protección contra abuso y límites conocidos

- Contadores en PostgreSQL, compartidos entre workers/reinicios: por 15 minutos,
  3 solicitudes por correo, 20 por IP y 30 canjes por IP. 429 con `Retry-After`.
  No se bloquea el login de la cuenta por pedir recuperación.
- La IP es `request.client.host`: no se acepta un X-Forwarded-For arbitrario.
  Si se usa un proxy, configurar únicamente proxies de confianza en ASGI. Sin
  esto, varios usuarios detrás del proxy pueden compartir el límite de IP.
- Las claves de los contadores son HMAC; no se guardan emails/IP en esa tabla.
  Tokens y contadores vencidos se limpian al procesar solicitudes posteriores.
- El correo se manda después de emitir la respuesta, para que su latencia no
  revele si existe la cuenta. Un 202 **no garantiza entrega**. Fallos SMTP dejan
  una advertencia genérica, sin destinatario, enlace ni credenciales.
- BackgroundTasks no es una cola durable: un reinicio puede perder el envío y
  requerir solicitar otro enlace. No hay reintentos automáticos ni cola externa
  en esta entrega; verificar monitorización del proveedor antes de producción.
- Se guarda la nueva clave únicamente como hash bcrypt. Nunca se recupera la
  clave vieja ni se envían contraseñas por correo.
- Las pruebas usan SMTP simulado, no acreditan recepción real. La prueba final
  con el proveedor y la aceptación del cambio compartido de autenticación se
  deben coordinar con Javier.

## Referencia de seguridad

[OWASP Forgot Password Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html).
