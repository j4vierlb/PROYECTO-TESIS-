# Clon limpio y corrida completa del backend — 24/11/2026

Responsable: Javier Lara Bustos. Objetivo: comprobar sobre un clon nuevo de `main` (commit `aa648eb`, después del PR #67) que el proyecto levanta completo con un solo comando y que la suite del backend corre **entera**, sin pruebas omitidas.

## 1. Corrida completa de las pruebas del backend

Hasta ahora se habían ejecutado 149 de 288 pruebas: las otras 139 se omiten si no hay una base PostGIS aislada. Esta vez se usaron dos bases desechables.

```bash
git clone https://github.com/j4vierlb/PROYECTO-TESIS-.git          # main, commit aa648eb
# Dos bases PostGIS aisladas (imagen postgis/postgis:16-3.4), una por variable de prueba,
# con el esquema aplicado desde database/schema.sql:
#   panel_regression   en 127.0.0.1:15432
#   croquis_regression en 127.0.0.1:15434
cd "Fase 2/Evidencias Proyecto/backend"
PYTHONPATH=tests:. \
CROQUIS_TEST_DATABASE_URL=postgresql+psycopg://<usuario>:<clave>@127.0.0.1:15434/croquis_regression \
PANEL_TEST_DATABASE_URL=postgresql+psycopg://<usuario>:<clave>@127.0.0.1:15432/panel_regression \
python -m unittest discover -s tests -v
```

Python 3.12.14, dependencias de `requirements.txt` instaladas en un entorno virtual nuevo.

**Resultado: `Ran 288 tests in 59.885s — OK`.** Sin fallas, sin errores y sin omisiones. Evidencia: [backend_completo.log](backend_completo.log).

Las bases eran desechables y no se usó la base de trabajo. Se borraron al terminar.

## 2. Levantar el proyecto desde el clon limpio

```bash
cd PROYECTO-TESIS-
cp .env.example .env     # sin claves de OpenAI ni de Twilio; solo se agregó el puerto del panel a ALLOWED_ORIGINS
docker compose -p killbichos-limpio -f docker-compose.yml -f docker-compose.override.usado.yml up --build -d
```

| Comprobación | Resultado |
|---|---|
| Panel web (`/`) | 200 |
| API (`/docs`) | 200 |
| Login `admin@killbichos.cl` con la clave de demostración | 200 |
| Login `tecnico1@killbichos.cl` con la clave de demostración | 200 |
| Login con clave incorrecta | 401 |
| CORS desde el panel | `access-control-allow-origin` con el origen del panel |
| Datos de prueba | 1 empresa, 1 usuario, 1 técnico, 2 clientes y 3 visitas |
| Tablas en el esquema `public` | 14 (incluye las de PostGIS) |
| Errores en el registro de la base al iniciar | 0 |

Evidencia: [compose_up.log](compose_up.log) y [verificacion.txt](verificacion.txt).

## Diferencias con un computador realmente limpio

1. **Mismo computador de desarrollo, no otro equipo.**
2. **No fue una construcción en frío.** Docker ya tenía en caché las imágenes del backend y del panel, así que el `up --build` tardó unos 13 segundos. Una primera construcción real tarda varios minutos (el 6 de noviembre, en [otra prueba](../clon_limpio_2026-11-06/README.md), tardó 3 min 50 s).
3. **Puertos distintos.** El stack de uso diario ocupa 5432, 8000 y 8080, así que el clon se levantó con otro nombre de proyecto y con [docker-compose.override.usado.yml](docker-compose.override.usado.yml), que cambia los puertos a 25432, 18000 y 18080. Ese archivo no está en el repositorio y en un computador limpio no hace falta.
4. **Las claves de demostración (`demo1234`) son las del Docker local.** En el servidor en la nube se cambiaron.
5. La imagen de PostGIS corre emulada en un Mac con chip Apple (aviso de plataforma de Docker): funciona, más lento.
6. No se probó WhatsApp, OpenAI ni la app móvil: esta prueba cubre solo la base, el backend y el panel.
