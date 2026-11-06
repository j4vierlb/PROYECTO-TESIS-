# Pruebas del backend (y frontend) para el cierre — 06/11/2026

Responsable: Pedro Vergiu. Rama `pedro`, al día con `main` (commit `95a2844`,
después de las PR #33 a #37).

## Resultado

**Backend: 251/251**, sin fallas, errores ni omisiones (`Ran 251 tests in 69.684s — OK`).
Evidencia: [backend_regression.log](backend_regression.log).

Las dos líneas `ERROR:` que aparecen en el log son mensajes del logger de pruebas
que simulan a propósito una falla (IA del croquis y recordatorio de WhatsApp);
ambas pruebas terminan en `ok`.

## Frontend (verificación de la cifra)

Para confirmar la cifra del panel también se ejecutó `vitest run` en un
contenedor, con `frontend/` y `app-movil/` copiados (las pruebas de marca leen
el logo y el tema de la app).

- **Node 24 (v24.22.2): 174/174.** Evidencia: [frontend_vitest_node24.log](frontend_vitest_node24.log).
- **Node 22 (v22.23.4 y v22.12.0): 173/174.** Falla `CRW08 muestra una foto
  autenticada como blob`: el `Response(new Blob(...))` del mock no se puede leer
  en Node 22 con jsdom y el visor muestra "No se pudo conectar con el servidor".
  La misma prueba pasa en Node 24, así que depende de la versión de Node y no
  del código del panel. Evidencia: [frontend_vitest_node22.log](frontend_vitest_node22.log).
  Conviene fijar la versión de Node para las pruebas (por ejemplo con
  `engines` en `package.json`) o ajustar el mock.

## Entorno aislado

- PostgreSQL/PostGIS 16-3.4 temporal (contenedor `kb-cierre-db`, en una red
  Docker propia y **sin puerto publicado**), creado solo para esta prueba y
  eliminado al terminar. No se usó la base de trabajo ni el `.env`.
- Bases `panel_regression` y `croquis_regression` creadas igual que
  `docker compose`: `schema.sql` y después las migraciones 4 a 7, sin datos de
  `seed.sql`. Evidencia: [preparacion_bases.log](preparacion_bases.log).
- Las pruebas corrieron en un contenedor `python:3.12-slim` (Python 3.12.15) con
  Node v20.19.2, porque varias pruebas del panel llaman a `node`.

## Primer intento (no válido)

El primer intento se hizo con las bases creadas **solo con `schema.sql`** y dio
60 errores, todos por la misma causa: `column "foto_path" of relation
"dispositivos_trampa" does not exist`. Esa columna está únicamente en
`migracion_croquis_terreno.sql`; las otras migraciones ya están incluidas en
`schema.sql`, pero esta no. En Docker no afecta porque `docker compose` aplica
todas las migraciones al crear la base. Se dejó el log como registro:
[intento1_solo_schema.log](intento1_solo_schema.log).

Recomendación: agregar `foto_path` (y los índices de esa migración) a
`schema.sql`, o indicar en el README del backend que la base de prueba necesita
también las migraciones.

## Reproducción

```bash
docker network create kb-cierre-test
docker run --rm -d --name kb-cierre-db --network kb-cierre-test \
  -e POSTGRES_USER=cierretest -e POSTGRES_PASSWORD=cierretest-local \
  -e POSTGRES_DB=postgres postgis/postgis:16-3.4
# por cada base (panel_regression y croquis_regression):
#   CREATE DATABASE ...; luego schema.sql y migracion_message_sid,
#   migracion_croquis_terreno, migracion_whatsapp_saliente y
#   migracion_sesion_tecnicos, en ese orden, con psql -v ON_ERROR_STOP=1
docker run --rm --network kb-cierre-test -v "<repo>/Fase 2/Evidencias Proyecto:/repo:ro" -w /repo/backend \
  -e PANEL_TEST_DATABASE_URL=postgresql+psycopg://cierretest:cierretest-local@kb-cierre-db:5432/panel_regression \
  -e CROQUIS_TEST_DATABASE_URL=postgresql+psycopg://cierretest:cierretest-local@kb-cierre-db:5432/croquis_regression \
  python:3.12-slim sh -c 'apt-get update && apt-get install -y nodejs && pip install -r requirements.txt && python -m unittest discover -v tests'
docker stop kb-cierre-db && docker network rm kb-cierre-test
```
