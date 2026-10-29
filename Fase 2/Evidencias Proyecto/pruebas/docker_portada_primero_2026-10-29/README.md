# Docker actualizado y portada como entrada inicial — 29/10/2026

Base de trabajo `0a03c30`, exclusivamente en `juan`, más la corrección
descrita aquí. Juan solicitó el 29/10 hacer commit, push y su PR, sin crear ramas.

## Comportamiento solicitado

Juan confirmó que desea ver **siempre la portada primero**, incluso con sesión
activa. Esto sustituye la decisión de la entrega inicial de entrar directamente
al panel con sesión. Abrir o recargar `http://localhost:8080/` muestra la portada:

- Ingresar sin sesión abre el login existente.
- Ingresar con sesión activa abre el panel, sin volver a pedir credenciales.
- La portada conserva la sesión y no consulta recursos privados antes de Ingresar.
- `#restablecer=...` sigue teniendo prioridad y abre recuperación, con limpieza
  del token en la URL. Se conservan los avisos de sesión vencida y cierre en otra
  pestaña, y el retorno al login al cerrar sesión.

## Pruebas

**162/162 pruebas frontend aprobadas**, diez archivos, incluidas las regresiones
de login, clientes, agenda, croquis, WhatsApp y recuperación. Se adaptaron los
casos del panel para recorrer Ingresar, mediante un auxiliar explícito de tests;
no se añade una puerta de acceso especial al producto. El nuevo caso comprueba
que volver a montar la app con sesión conserva el token y muestra la portada
sin solicitar datos de la API. [Log](frontend.log).

En el navegador, contra Docker:

1. Abrir `localhost:8080/` mostró la portada y su QR.
2. Ingresar abrió la agenda con la sesión existente y respuestas reales de la API.
3. Recargar volvió a mostrar la portada con la sesión todavía vigente.
4. Ingresar otra vez abrió la agenda, sin solicitar credenciales ni borrar datos.

Capturas públicas: [portada](portada_docker.png) y
[portada después de recargar con sesión](portada_tras_recargar_con_sesion.png).
No se guardan capturas del panel con datos privados de clientes.

## Reconstrucción y verificación del backend

Se reconstruyeron y recrearon únicamente `backend` y `web`, con `--no-deps` al
iniciar. La base existente no se reinició y no se aplicaron migraciones.
Se conservaron las imágenes anteriores con etiquetas de recuperación locales.

El backend contiene el main actualizado, incluida la geocodificación nacional,
presentación del agente y endpoint de próximas visitas. La ayuda del API incluye
`/operadores/me/visitas-proximas`. Se verificaron salud, autenticación de cuentas
de demostración y consultas GET de estadísticas, clientes, agenda y próximas:
todas las consultas autenticadas respondieron 200 y próximas sin sesión, 401.
Solo se guardan estados y conteos: [verificación HTTP](backend_verificacion.json).
No se crearon, editaron o eliminaron clientes, visitas o trampas en estas pruebas.

La compilación de producción del panel en Docker terminó correctamente. Archivo
servido: `index-Dlxlp7Fl.js`; CSS `index-D2KwU7D-.css`. Las imágenes desplegadas y
los controles de datos están en [metadatos](despliegue.json). Los logs operativos
completos de build e inicio quedan fuera del repositorio, en
`tmp/despliegue_docker_2026-10-29/` del espacio de trabajo.

## Datos y límites

Se conservó el mismo contenedor de base de datos y los volúmenes de datos y
fotos. Antes y después: **4 clientes, 6 visitas, 4 croquis, 14 trampas y 2 usuarios**.
No se usó `down -v`, no se borraron volúmenes ni se cambiaron claves o `.env`.

No se enviaron mensajes de WhatsApp ni correos como parte de las comprobaciones.
No se declara una prueba física nueva en Android/iOS ni una recompilación del APK.
La verificación corresponde al despliegue local previo a su publicación en Git;
los contenedores ya ejecutaban este código al recoger las evidencias. La entrega
de la PR no equivale a fusionarla automáticamente en main.
