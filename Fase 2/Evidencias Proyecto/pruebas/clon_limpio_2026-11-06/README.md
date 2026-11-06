# Prueba de instalación desde un clon limpio — 06/11/2026

Responsable: Pedro Vergiu. Objetivo: comprobar que el proyecto levanta completo
con un solo comando a partir de un clon nuevo del repositorio, copiando solo
`.env.example` a `.env`.

## Pasos

```bash
git clone https://github.com/j4vierlb/PROYECTO-TESIS-.git   # main, commit 95a2844
cd PROYECTO-TESIS-
cp .env.example .env                                         # sin editar
docker compose up --build
```

El `.env` se usó tal como viene en `.env.example`: sin claves de OpenAI ni de
Twilio y con la contraseña de ejemplo de la base.

## Resultado

**OK.** Con un solo `docker compose up --build` se construyeron las imágenes
del backend y del panel, se creó la base y los tres servicios quedaron
arriba (`db` healthy, `backend` y `web` Up). Tiempo total: 3 min 50 s
(01:00:08 a 01:03:58, hora de Chile).

| Comprobación | Resultado |
|---|---|
| Scripts de la base (`1_schema` a `7_migracion_sesion_tecnicos`) | Los 7 se ejecutaron, 0 errores ([db_init.log](db_init.log)) |
| Datos de prueba | 1 empresa, 1 usuario del panel, 1 técnico, 2 clientes, 3 visitas |
| Panel web (`/`) | 200 |
| API (`/docs`) | 200 (el backend tarda unos 10 s en responder después de arrancar) |
| Login `admin@killbichos.cl` / `demo1234` | 200 con tokens |
| Login `tecnico1@killbichos.cl` / `demo1234` | 200 con tokens |
| Login con clave incorrecta | 401 |
| CORS desde el panel | `access-control-allow-origin` del panel |

Evidencia: [compose_up.log](compose_up.log) y [verificacion.txt](verificacion.txt)
(los tokens se reemplazaron por `<oculto>`).

## Diferencias con un PC realmente limpio

Se hizo en el mismo computador de desarrollo, no en otro equipo:

1. **Puertos.** El stack de uso diario (`killbichos`) estaba corriendo y
   ocupa 5432, 8000 y 8080. Para no detenerlo, el clon limpio se levantó con
   otro nombre de proyecto (`docker compose -p killbichos-limpio`) y con
   [docker-compose.override.usado.yml](docker-compose.override.usado.yml),
   que solo cambia los puertos a 15432, 18000 y 18080. Al `.env` se le agregó
   `http://localhost:18080` a `ALLOWED_ORIGINS` por ese mismo cambio de
   puerto. El override **no está en el repositorio**; en un PC limpio no hace
   falta.
2. **Volúmenes.** Por el nombre de proyecto distinto, la base y las fotos se
   crearon en volúmenes nuevos (`killbichos-limpio_db_data`), sin tocar los de
   uso diario. Si se ejecuta `docker compose up --build` tal cual en un equipo
   que ya tiene el volumen `killbichos_db_data`, Docker reutiliza esa base y
   no corre los scripts de inicio.
3. **Imágenes base.** `postgis/postgis:16-3.4`, `python:3.12-slim` y
   `node:22-alpine` ya estaban descargadas. En un PC limpio la primera vez
   tarda más por la descarga.

Pendiente para Pedro: repetir el comando literal (sin override) en otro
equipo, o en este con el stack diario detenido, y anotar el resultado aquí.

## Uso posterior

Con este mismo stack (sin `OPENAI_API_KEY`) se ejecutó el caso 8 de HU-18.
Ver [`docs/evidencias/HU-18/HU18_08_sin_openai.txt`](../../docs/evidencias/HU-18/HU18_08_sin_openai.txt).
Al terminar se eliminó con `docker compose -p killbichos-limpio down -v`.
