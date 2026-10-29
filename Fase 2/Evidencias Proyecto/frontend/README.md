# Panel web Kill Bichos

Panel operativo para administrar clientes y agendar visitas por operador.

## Portada pública

Sin sesión, el sitio muestra información de Kill Bichos, servicios, contacto,
horarios y la guía de tres pasos del WhatsApp de prueba. **Ingresar** abre el
login existente. Con sesión activa se entra directamente al panel; cerrar o
vencer la sesión conserva el retorno al login y sus mensajes actuales.

El enlace `#restablecer=...` tiene prioridad sobre portada y panel. Su token se
consume y retira de la barra como antes; la portada no lo envía a WhatsApp.

Los textos y datos públicos se mantienen en `src/public-site-config.js`.
Los horarios y datos del Sandbox fueron confirmados por Juan el 29/10/2026:
lunes a sábado, 08:00–18:00; número `+14155238886`; unión
`join example-primitive`, leído del QR proporcionado por Javier. Son datos
públicos; este archivo no debe contener credenciales de Twilio ni otras claves.

Botón y QR usan el mismo enlace `wa.me` y solo preparan el mensaje: el usuario
debe enviarlo desde WhatsApp. Se advierte que es un **Sandbox de Twilio**, no
un servicio abierto al público. Si la configuración es inválida, el botón se
deshabilita y no se genera un QR ficticio.

El QR SVG se genera localmente con `qrcode`, sin servicios externos ni peticiones
a la API. `jsqr` es una dependencia de pruebas para decodificar el SVG renderizado
y comprobar el destino. No se modifican backend, base de datos ni archivos `.env`.
La portada requiere recompilar el frontend para desplegar sus cambios.
[Pruebas y capturas del 29/10](../pruebas/portada_publica_2026-10-29/README.md).

## Ejecución

Con el backend corriendo en `http://localhost:8000`:

```bash
npm install
npm run dev
```

La URL de la API se puede cambiar con `VITE_API_URL`.

El panel utiliza el usuario de prueba `admin@killbichos.cl` con clave `demo1234`.

## Alcance

- Login para usuarios administrativos (`admin` y `coordinador`).
- Agenda filtrable por día y operador.
- Creación de visitas, edición de notas, asignación o cambio de operador y reprogramación real.
- Cambiar fecha/hora marca la visita como `reagendada` y lleva la agenda al día guardado.
- Filtro para visitas sin asignar y acceso rápido a Hoy.
- CRUD de clientes con ubicación automática desde la dirección y confirmación antes de eliminar.
- Resumen de clientes, visitas del día y visitas pendientes.
- Cargas cancelables al navegar, reintento ante errores y prevención de doble envío.
- Retorno al login cuando vence la sesión; sin credenciales precargadas.
- Navegación por teclado y adaptación a pantallas de escritorio y móvil.
- Consulta de croquis por visita, trampas retiradas y fotos privadas, sin editar el registro del técnico.

## Fechas y datos opcionales

La agenda muestra `America/Santiago`, incluyendo horario de verano e invierno.
El formulario interpreta la hora elegida como hora de Chile y la envía en UTC
con sufijo `Z`, como exige el contrato de la API. Una hora inexistente por el
cambio de horario se rechaza con un mensaje antes de enviar la solicitud.

`Sin asignar` envía `operador_id: null`. Los clientes que llegan desde WhatsApp
sin ubicación se muestran como `Ubicación pendiente de confirmar` y se pueden editar sin inventar
una ubicación. El formulario solo solicita nombre, teléfono y dirección; no pide
latitud ni longitud. Al guardar, el backend intenta geocodificar la dirección
con `GOOGLE_MAPS_API_KEY` (clave del backend, no la variable `VITE_`).

Ingresar calle, número y comuna o ciudad de cualquier lugar de Chile. El país
debe ser Chile y la comuna o ciudad encontrada por Google debe aparecer en la
dirección ingresada; ya no se asume la Región Metropolitana. Si Google no confirma
un punto confiable, el cliente se guarda y el panel indica «Ubicación pendiente
de confirmar». Corregir la dirección y volver a guardar permite reintentar.
Cambiar la dirección recalcula el punto; si falla, se quita el punto anterior
para no mostrar el lugar equivocado. Guardar la misma dirección ya ubicada no
vuelve a consultar Google ni mueve una corrección hecha en terreno.

El contrato HTTP mantiene las coordenadas opcionales para integraciones previas,
pero este formulario no reenvía coordenadas antiguas ni expone la clave del
backend al navegador. No se implementa autocompletado de Places: la búsqueda se
hace una vez al guardar, con el servicio de geocodificación ya existente.

## Reglas del agendamiento

Se usan los mismos días y horas configurados para WhatsApp en
`KILLBICHOS_OPERATING_DAYS`, `KILLBICHOS_OPEN_TIME` y `KILLBICHOS_CLOSE_TIME`.
La hora de cierre no se incluye. La API comprueba los horarios incluso cuando
la visita no tiene operador, y rechaza choques de un operador a menos de una hora.
Las visitas canceladas no bloquean el horario. Una visita finalizada o cancelada
debe reactivarse antes de cambiar su fecha u operador; sus notas sí se pueden editar.

Estas funciones requieren actualizar también `routers/panel.py` y los esquemas
del panel en `schemas.py`. El contrato móvil `VisitUpdate` no se amplió y no hay
migraciones para estas reglas de agendamiento. El visor de croquis requiere la
migración de terreno de main, descrita a continuación. Los módulos de WhatsApp
y los endpoints de croquis no se modificaron para implementar el visor.

## Croquis de solo lectura

Desde cada visita de Agenda, **Ver croquis** consulta `GET /croquis/{visita_id}`.
No crea croquis ni agrega, mueve, confirma o retira trampas. También funciona
para visitas completadas o canceladas. Las trampas retiradas se conservan en gris;
las propuestas IA sin confirmar aparecen en amarillo. El listado permite elegir
una trampa y consultar su foto incluso si Google Maps no está configurado.

Las fotos se descargan por `GET /dispositivos-trampa/{id}/foto`, con el token
en `Authorization`. Solo se aceptan las rutas relativas de fotos del backend;
no se siguen redirecciones ni se envían tokens en URLs. Las imágenes JPEG/PNG
se muestran mediante URLs blob que se liberan al cambiar de selección o cerrar.

En el `.env` de la **raíz del repositorio**, junto al compose:

```dotenv
VITE_API_URL=http://localhost:8000
VITE_GOOGLE_MAPS_API_KEY=
```

Completar la segunda variable localmente con la clave **web** proporcionada por
Javier. No usar la clave del iPhone. Reiniciar `npm run dev`, o reconstruir web
con `docker compose up -d --no-deps --build web`, después de cambiarla.
Vite lee el `.env` raíz y solo publica variables con prefijo `VITE_`.
Nunca agregar ese prefijo a secretos de OpenAI, Twilio, PostgreSQL o JWT.

La clave web es visible en el navegador por diseño. Restringirla a **Maps
JavaScript API** y referentes HTTP `http://localhost:8080/*` y
`http://localhost:5173/*`. Abrir el panel con `localhost`, no `127.0.0.1`, para
probar esos referentes. No requiere Map ID: usa una capa Data de puntos no editables.
Referencia: [carga del SDK](https://developers.google.com/maps/documentation/javascript/load-maps-js-api)
y [capa Data](https://developers.google.com/maps/documentation/javascript/datalayer).

Si la base ya existía, aplicar la migración desde la raíz (PowerShell):

```powershell
Get-Content -Raw 'Fase 2/Evidencias Proyecto/database/migracion_croquis_terreno.sql' |
  docker compose exec -T db psql -v ON_ERROR_STOP=1 -U killbichos -d killbichos
docker compose up -d --no-deps --build backend
```

Estos comandos asumen que `db` pertenece al compose raíz y ya está levantado.
Si se mantiene una base del compose antiguo, identificar su contenedor y red
antes de ejecutar comandos; no levantar otra base ni borrar volúmenes para resolverlo.

**Verificación local del 20/10/2026:** el mapa real se comprobó en
`localhost:5173` después de corregir los referentes de la clave. El PR #14
de Javier ya está integrado y sus permisos de empresa se verificaron para
visitas, croquis y fotos: 30 casos aprobados dentro de una regresión de 205
pruebas (107 backend y 98 frontend). Ver el reporte PR14 de la carpeta pruebas.
La validación se limita al entorno local registrado; no acredita un despliegue
remoto. Un `RefererNotAllowedMapError` en otro origen requiere revisar los
referentes permitidos de la clave en Google Cloud.

## Ubicación pendiente en Clientes — 28/10/2026

Cuando faltan coordenadas válidas, la tabla muestra una etiqueta amarilla
**Ubicación pendiente de confirmar**, incluso después de navegar o recargar.
No depende del mensaje temporal al guardar. Corregir calle, número y comuna y
guardar vuelve a intentar la ubicación; si se confirma, la etiqueta se reemplaza
por las coordenadas. El cliente puede conservarse mientras se corrige la dirección.
Validación: **130/130 pruebas frontend**, compilación y prueba manual local con
un cliente sintético. [Evidencias](../pruebas/ubicacion_pendiente_2026-10-28/README.md).

## Pruebas

Desde esta carpeta:

```bash
npm ci
npm test
npm run build
```

Las pruebas de React simulan las respuestas HTTP; no conectan una base real.
Los casos, resultados, capturas y pasos para probar con PostGIS real están en
[`../pruebas/Panel_regresion_2026-10-09.md`](../pruebas/Panel_regresion_2026-10-09.md),
[`../pruebas/Panel_cierre_2026-10-19.md`](../pruebas/Panel_cierre_2026-10-19.md) y
[`../pruebas/Croquis_web_2026-10-19.md`](../pruebas/Croquis_web_2026-10-19.md).
