# Evidencias de regresión del panel web

**Informe histórico de las tres correcciones iniciales del panel.** La
ejecución vigente del conjunto está en
[Verificacion_PR14_2026-10-20.md](Verificacion_PR14_2026-10-20.md):
205 aprobadas (107 backend y 98 frontend), incluidas las 30 de aislamiento.
Las 51 pruebas y los comandos siguientes describen la ejecución del 09/10;
no constituyen el conteo ni las instrucciones de la suite actual.

Ejecución: 09/10/2026. Revisión documental: 13/10/2026. Responsable: Juan.
Código del panel: commit `1d8fdbd`, integrado en `main` por la PR #11.

## Resultado y alcance

Las tres fallas del panel están corregidas y verificadas. Se aprobaron **51
pruebas automatizadas**: 29 frontend, 6 de contrato HTTP, 5 de fecha chilena y
11 de integración con PostgreSQL/PostGIS real. La compilación de producción
también pasó. Las verificaciones de navegador y sus capturas son evidencia
adicional, no pruebas que se sumen al recuento automatizado.

| ID | Falla corregida | Resultado comprobado |
| --- | --- | --- |
| PANEL-HORA | La agenda mostraba un recorte de UTC y el formulario enviaba hora sin zona | Se muestra America/Santiago y se envía ISO UTC con Z; verano, invierno y cruce de medianoche conservan la hora y el día chilenos |
| PANEL-CLIENTES | `toFixed()` fallaba con coordenadas nulas | El cliente se muestra como Sin coordenadas, se puede editar y conserva null en la base tras recargar |
| PANEL-ASIGNACION | Sin asignar enviaba una cadena vacía a un campo UUID | Se envía `operador_id: null`; crear y volver a consultar la visita funciona. Un operador elegido conserva su UUID |

Las correcciones funcionales están en el frontend. No se modificaron routers,
esquemas ni lógica del backend para estas pruebas; allí se añadieron pruebas y
datos sintéticos para el entorno aislado.

## Ejecuciones automatizadas

| Suite o comando | Resultado real y alcance |
| --- | --- |
| Frontend `npm test` | 29 aprobadas: 23 de utilidades y 6 de interfaz React |
| Frontend con `TZ=Pacific/Auckland` | Las mismas 29 aprobadas con otra zona; no añade casos |
| Backend con `PANEL_TEST_DATABASE_URL` | 22 aprobadas: 6 contrato HTTP, 5 fecha chilena y 11 PostGIS |
| `npm run build` | Compilación exitosa con Vite 8.3.1 |
| `npm audit` | 0 vulnerabilidades reportadas en esa ejecución |
| `git diff --check` | Sin errores de espacios en el diff |

Archivos de pruebas:

- `frontend/tests/panel-utils.test.js`: fechas, horas y payloads.
- `frontend/tests/panel.test.jsx`: formularios, envío HTTP simulado y recarga.
- `backend/tests/test_panel_contract.py`: endpoints FastAPI con conexión SQL simulada.
- `backend/tests/test_zona_horaria.py`: día chileno.
- `backend/tests/test_panel_postgis.py`: autenticación, consultas y PostGIS reales.
- `backend/tests/panel_fixture.py`: datos sintéticos de la base de prueba.

Las pruebas React simulan `fetch` y las de contrato simulan SQL. Las 11 de
PostGIS ejecutan SQL real y generan los payloads mediante la utilidad real del
frontend en Node.js. Solo se reemplaza la dependencia de conexión para apuntar
a una base aislada; JWT, roles, validación y serialización son reales.

## Verificación end-to-end en navegador

Se levantaron FastAPI en 8000 y Vite en 5173 contra `panel_regression`, en un
contenedor separado con PostGIS 16-3.4 y el esquema del repositorio. Las
peticiones del navegador fueron reales, sin simular `fetch`. Los casos
automatizados de integración se aislaron mediante transacciones con rollback.

| Caso | Resultado en navegador y base real |
| --- | --- |
| Clientes sin ubicación | El listado abre sin pantalla en blanco y muestra Sin coordenadas |
| Edición sin ubicación ni dirección | El nombre se guarda; direccion y ubicacion siguen en null después de recargar |
| 10:00 de verano Sin asignar | 29/09/2026 10:00 → 29/09/2026 13:00 UTC; operador_id null; tarjeta a las 10:00 |
| 23:30 de verano | 29/09/2026 23:30 → 30/09/2026 02:30 UTC; aparece el 29/09 y no el 30/09 |
| 10:00 de invierno con operador | 15/07/2026 10:00 → 15/07/2026 14:00 UTC; tarjeta a las 10:00 con Operador QA |
| Recarga y navegación por día | Al recargar y seleccionar el día se recuperan las visitas a las 10:00 y 23:30; anterior/siguiente cambian el día correcto |
| Filtro por operador | Operador QA excluye las visitas sin asignar y Todos los operadores vuelve a mostrarlas |

No se observaron errores ni advertencias en la consola del navegador. La
etiqueta del operador se verificó en escritorio a 1280 × 900. En el tamaño
angosto el CSS existente la oculta; ese comportamiento de diseño no se cambió.

Capturas con datos sintéticos:

- [Cliente editado y sin coordenadas](capturas/clientes_sin_coordenadas.jpg).
- [Visita de verano Sin asignar](capturas/agenda_sin_asignar_verano.jpg).
- [23:30 en el día chileno](capturas/agenda_2330_dia_chileno.jpg).
- [Invierno con operador](capturas/agenda_invierno_operador.jpg).
- [Persistencia después de recargar](capturas/agenda_recarga_persistencia.jpg).

## Conservación de datos

No se reutilizó el volumen de trabajo. Al finalizar se cerró la sesión de
prueba, se detuvieron sus servidores y se eliminó el contenedor desechable
creado con `--rm`. Sus datos se pueden recrear desde el esquema y las fixtures.
La base de trabajo conservó 1 empresa, 2 clientes y 1 visita antes y después;
no se realizaron escrituras en ella. Esos recuentos corresponden a la fecha
de la prueba, no a una afirmación sobre su contenido actual.

## Reproducción del entorno histórico

Frontend, desde su carpeta:

```powershell
npm ci
npm test
npm run build
```

Backend, desde `Fase 2/Evidencias Proyecto/backend`, con Docker y Node.js:

```powershell
python -m pip install -r requirements.txt
$panelSchemaPath = (Resolve-Path -LiteralPath '../database/schema.sql').Path
docker run --rm -d --name killbichos-panel-test -p 127.0.0.1:15432:5432 -e POSTGRES_USER=paneltest -e POSTGRES_PASSWORD=paneltest-local -e POSTGRES_DB=panel_regression --mount "type=bind,source=$panelSchemaPath,target=/docker-entrypoint-initdb.d/1_schema.sql,readonly" postgis/postgis:16-3.4
# Repetir el chequeo hasta que indique accepting connections:
docker exec killbichos-panel-test pg_isready -h 127.0.0.1 -U paneltest -d panel_regression
$env:PANEL_TEST_DATABASE_URL = 'postgresql+psycopg://paneltest:paneltest-local@127.0.0.1:15432/panel_regression'
python -m unittest discover tests -v
docker stop killbichos-panel-test
Remove-Item Env:PANEL_TEST_DATABASE_URL
```

La suite backend ejecuta 22 pruebas con esa variable. Sin ella, omite las 11
de PostGIS expresamente. La configuración de integración solo admite una base
llamada `panel_regression`. No ejecutar `panel_fixture.py` antes de la suite:
cada prueba crea y revierte sus datos. Si el contenedor o el puerto ya existen,
no reemplazarlos sin comprobar a qué entorno pertenecen.

## Relación con el plan de pruebas general

El [reporte del script del 06/10/2026 16:14](../../../pruebas/resultados_2026-10-06_1614.md)
contiene 32 casos aprobados: 17 integración, 12 seguridad y 3 rendimiento.
Es una ejecución distinta, con comportamientos que se solapan con este panel.
No se suman las dos suites como 83 requisitos únicos.

Este informe no acredita conversación real de Twilio, generación de croquis
por IA, modo offline móvil ni aprobación de la empresa. La prueba de firma del
webhook y la validación de Rodrigo Quiroga pertenecen a evidencias separadas.
