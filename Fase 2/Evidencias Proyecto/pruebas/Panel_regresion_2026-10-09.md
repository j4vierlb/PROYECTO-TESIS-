# Evidencias de regresión del panel web — 09/10/2026

Responsable: Juan. Rama de trabajo: `juan`.

## Resultado final con PostgreSQL real y navegador

**APROBADO para las tres fallas del panel.** Después de reparar Docker se
ejecutaron **51 pruebas automatizadas**: 29 de frontend, 11 de integración con
PostgreSQL/PostGIS real y 11 de contrato HTTP/fechas existentes. La compilación
de producción también pasó. No se cambiaron routers, esquemas ni código funcional
del backend para ejecutar estas pruebas.

Se creó el contenedor desechable `killbichos-panel-test-852f2b`, con PostGIS
16-3.4, el esquema del repositorio y la base `panel_regression`, en el puerto
local 15432. No se reutilizó el volumen de trabajo. Las pruebas de integración
usaron transacciones con rollback por caso; el login, JWT, autorización, SQL y
serialización fueron reales. Solo se reemplazó la dependencia de conexión para
dirigir esas pruebas a la base aislada.

Luego se levantó el backend en 8000 y Vite en 5173, apuntando a esa misma base
temporal mediante una variable de entorno del proceso, sin cambiar el `.env`.
La verificación de navegador usó la habilidad de control de navegador, datos
sintéticos y peticiones reales a FastAPI; no se simuló `fetch` en esta etapa.

### Verificación end-to-end

| Caso | Observación en navegador y base real | Resultado |
| --- | --- | --- |
| Clientes sin ubicación | El listado abre sin pantalla en blanco y muestra `Sin coordenadas` | Aprobado |
| Edición sin coordenadas ni dirección | Se guarda el nombre; `direccion` y `ubicacion` siguen en null; el cambio persiste tras recargar | Aprobado |
| 10:00 de verano, Sin asignar | 29/09/2026 10:00 se guarda como 29/09/2026 13:00 UTC; `operador_id` es null; la tarjeta muestra 10:00 y Sin asignar en escritorio | Aprobado |
| 23:30 de verano | Se guarda como 30/09/2026 02:30 UTC, pero aparece el 29/09 a las 23:30 y no el 30/09 | Aprobado |
| 10:00 de invierno, con operador | 15/07/2026 10:00 se guarda como 15/07/2026 14:00 UTC; la tarjeta muestra 10:00 y Operador QA | Aprobado |
| Recarga y navegación por día | Al recargar y volver a elegir el día, se recuperan ambas visitas de verano, ordenadas 10:00 y 23:30; anterior/siguiente cambian el día correcto | Aprobado |
| Filtro por operador | En el día con visitas sin asignar, el filtro Operador QA las excluye y Todos los operadores vuelve a mostrarlas | Aprobado |

No se observaron errores ni advertencias en la consola del navegador. Se verificó
la pantalla Clientes con el tamaño normal del panel y la etiqueta de operador en
el breakpoint de escritorio (1280 × 900); se restauró el tamaño al finalizar.
En el tamaño angosto la etiqueta del operador está oculta por el CSS existente:
no se cambió ese comportamiento de diseño.

Capturas de datos sintéticos:

- [Clientes sin coordenadas después de editar y recargar](capturas/clientes_sin_coordenadas.jpg).
- [Visita de verano Sin asignar](capturas/agenda_sin_asignar_verano.jpg).
- [Visita de las 23:30 en el día chileno](capturas/agenda_2330_dia_chileno.jpg).
- [Invierno con operador](capturas/agenda_invierno_operador.jpg).
- [Visitas recuperadas después de recargar](capturas/agenda_recarga_persistencia.jpg).

### Integración automatizada nueva

`backend/tests/test_panel_postgis.py` agrega 11 casos: cliente con ubicación
null; edición y persistencia null; creación con coordenadas cero; visita Sin
asignar; hora de verano; hora de invierno; cruce de medianoche; asignación y
filtro por operador; rechazo de UUID vacío sin inserción; estadísticas por día
chileno; acceso sin token; y rechazo de cliente de otra empresa. Algunas
verificaciones se agrupan en un solo método de prueba.

Los payloads de visitas se generan ejecutando la utilidad real del frontend
en Node.js, no duplicando su conversión de zona horaria en Python.

### Limpieza y conservación de datos

Se cerró la sesión sintética y la pestaña de pruebas. Se detuvieron únicamente
los procesos de backend y Vite creados para esta ejecución. `docker stop` sobre
el contenedor creado con `--rm` eliminó el contenedor y su almacenamiento
temporal, recreables desde el esquema y `panel_fixture.py`.

`killbichos_db` sigue activo con el volumen `database_killbichos_data`. Antes y
después de las pruebas conserva 1 empresa, 2 clientes y 1 visita. No se realizaron
escrituras en esa base de trabajo.

**Pendiente fuera de estas tres fallas:** la prueba real de Twilio, porque sus
credenciales y URL pública no están disponibles en las ramas revisadas.

### Cómo repetir las 11 pruebas de integración (PowerShell)

Desde `Fase 2/Evidencias Proyecto/backend`, con Docker y Node.js disponibles:

```powershell
python -m pip install -r requirements.txt
$panelSchemaPath = (Resolve-Path -LiteralPath '../database/schema.sql').Path
docker run --rm -d --name killbichos-panel-test -p 127.0.0.1:15432:5432 -e POSTGRES_USER=paneltest -e POSTGRES_PASSWORD=paneltest-local -e POSTGRES_DB=panel_regression --mount "type=bind,source=$panelSchemaPath,target=/docker-entrypoint-initdb.d/1_schema.sql,readonly" postgis/postgis:16-3.4
# Repetir este chequeo hasta que diga 'accepting connections':
docker exec killbichos-panel-test pg_isready -h 127.0.0.1 -U paneltest -d panel_regression
$env:PANEL_TEST_DATABASE_URL = 'postgresql+psycopg://paneltest:paneltest-local@127.0.0.1:15432/panel_regression'
python -m unittest discover tests -v
docker stop killbichos-panel-test
Remove-Item Env:PANEL_TEST_DATABASE_URL
```

Con esa variable activa, la suite backend completa ejecuta 22 pruebas. Sin la
variable, las 11 de integración se omiten explícitamente. La configuración de
pruebas solo admite una base llamada `panel_regression`, para evitar que se
apunte por accidente a la base de trabajo. No ejecutar `panel_fixture.py` antes
de la suite automatizada: cada prueba crea y revierte sus propios datos.

Los apartados que siguen documentan el trabajo y las limitaciones de la
**ejecución inicial**; la limitación de Docker y las pruebas de persistencia
quedaron resueltas en la ejecución final descrita arriba.

## Alcance y cambios

Se actualizó `juan` con `origin/main` mediante fast-forward (base `1f2ec3f`),
sin crear ramas ni modificar las ramas de los compañeros. Así se conservan
las correcciones de Javier para clientes opcionales, operadores nulos y filtros
por fecha de Chile. Las nuevas correcciones funcionales son exclusivamente del
frontend; en backend solo se agregó un archivo de pruebas.

| ID | Falla | Corrección | Verificación ejecutada |
| --- | --- | --- | --- |
| PANEL-HORA | Se recortaba la hora UTC recibida, sin conversión; al guardar se enviaba una fecha sin zona | Mostrar `America/Santiago`; convertir el `datetime-local` chileno a ISO UTC con `Z`; ordenar horarios y usar el día seleccionado | Verano, invierno, medianoche, cambios de día/año, hora inexistente por cambio de horario, formulario y respuesta HTTP |
| PANEL-CLIENTES | `toFixed()` sobre coordenadas nulas rompía Clientes | Mostrar `Sin coordenadas`; normalizar campos del formulario y conservar `null` al editar; validar ambas coordenadas juntas | Listado con ubicación nula, sin dirección, ubicación completa, coordenada cero y edición sin inventar ubicación |
| PANEL-ASIGNACION | `Sin asignar` enviaba `""` a un campo UUID | Enviar `operador_id: null`; conservar UUID cuando se elige operador | Formulario sin asignación y sin operadores disponibles; contrato FastAPI acepta null (201) y rechaza cadena vacía (422) |

## Resultado automatizado

| Comando | Resultado real |
| --- | --- |
| Frontend: `npm test` | 29 pruebas aprobadas: 23 de utilidades y 6 de interfaz React |
| Frontend: `$env:TZ='Pacific/Auckland'; npm test` (PowerShell) | Las mismas 29 pruebas aprobadas con una zona del navegador distinta de Chile |
| Frontend: `npm run build` | Compilación de producción exitosa, Vite 8.3.1 |
| Frontend: `npm audit` | 0 vulnerabilidades reportadas después de actualizar la dependencia transitiva `source-map-js` |
| Backend: `python -m unittest discover tests -v` | 11 pruebas aprobadas: 6 de contrato HTTP del panel y 5 existentes de fecha chilena |
| Git: `git diff --check` | Sin errores de espacios en el diff |

Archivos de pruebas:

- `frontend/tests/panel-utils.test.js`: conversiones de fecha/hora y payloads.
- `frontend/tests/panel.test.jsx`: interacción con la interfaz, envío HTTP y recarga.
- `backend/tests/test_panel_contract.py`: endpoints reales de FastAPI con DB simulada.
- `backend/tests/test_zona_horaria.py`: pruebas existentes del día chileno.

Las pruebas de interfaz simulan `fetch`; las de contrato simulan la conexión SQL.
No verifican ejecución SQL, persistencia en PostGIS ni el flujo completo entre
navegador, servidor y base de datos. No se enviaron mensajes ni llamadas a Twilio.

## Twilio y configuración local

Se revisaron en modo lectura `main`, `origin/main`, `origin/javier` y `origin/pedro`.
Las plantillas no contienen Account SID ni Auth Token reales, ni una URL pública
configurada. El número Sandbox del ejemplo no sustituye estas credenciales.

Se creó `backend/.env` local a partir de su plantilla, incluyendo
`TWILIO_ACCOUNT_SID=` y `TWILIO_AUTH_TOKEN=` pendientes de completar, además
de `TWILIO_WEBHOOK_URL=` y `TWILIO_VALIDATE_SIGNATURE=true`. Se incluyó el
origen local `http://127.0.0.1:5173` para CORS. `git check-ignore` confirmó que
el `.env` está excluido de Git. No se copiaron ni publicaron secretos.

No se pudo confirmar cuáles son las dos líneas exactas solicitadas por el equipo;
se preservó la configuración completa del ejemplo. La integración Twilio queda
pendiente de completar los valores reales directamente en el `.env` local.

## Verificaciones pendientes con base real

### Actualización posterior: Docker reparado el 09/10/2026

Con autorización de Juan se respaldó la configuración, se renombraron las
carpetas de comunicación `Docker/run` y `docker-secrets-engine`, y se cambió
`EnableDockerAI` a `false`. No se eliminaron imágenes, contenedores ni volúmenes.
Los respaldos llevan el sufijo `backup-2026-10-09-327f5d`.

Docker Engine 29.6.2 volvió a responder. El contenedor existente `killbichos_db`
se inició automáticamente, `pg_isready` confirmó disponibilidad, PostgreSQL
respondió `SELECT 1`, y PostGIS sigue instalado. También se verificó `SELECT 1`
usando la conexión real del backend; el volumen sigue siendo
`database_killbichos_data`. Estas son comprobaciones de disponibilidad, no
pruebas end-to-end del panel. Los casos de persistencia detallados abajo siguen
pendientes de ejecución.

### Limitación durante la ejecución inicial

Docker Desktop falló al arrancar. La CLI no encontró `dockerDesktopLinuxEngine`;
el registro de arranque indicó un error al inicializar `dockerInference`.
No se borraron archivos de Docker ni volúmenes, ni se modificó su configuración.
Por tanto, no se afirma haber realizado pruebas end-to-end ni de persistencia.

Cuando Docker y la base estén disponibles, repetir en un entorno de prueba:

1. Iniciar backend y panel. Abrir Clientes con un cliente WhatsApp que tenga
   dirección y ubicación nulas. Debe aparecer sin pantalla en blanco y con
   `Sin coordenadas`.
2. Editar solo su nombre y guardar. Verificar HTTP 200 y que la ubicación siga
   siendo `null`, no una coordenada de ejemplo ni `(0, 0)`.
3. Elegir un día de verano e ingresar una visita a las 10:00 con `Sin asignar`.
   Verificar POST 201, `operador_id: null`, fecha UTC a las 13:00 y agenda a las
   10:00 después de recargar el navegador.
4. Repetir en invierno: 10:00 de Chile debe persistirse como 14:00 UTC.
5. Agendar a las 23:30 de un día de verano: la UTC pertenece al día siguiente,
   pero la visita debe seguir apareciendo en el día chileno elegido.
6. Repetir con un operador elegido: verificar su UUID y nombre en la tarjeta.
7. Completar credenciales y URL de Twilio en local. Mantener validación de firma
   activada y coordinar una prueba real de Sandbox con el responsable de WhatsApp.
