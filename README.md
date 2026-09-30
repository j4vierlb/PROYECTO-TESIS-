# Kill Bichos IA

Sistema de agendamiento y croquis asistido por IA para Kill Bichos, empresa de control de plagas (Macul, Santiago). Proyecto de título — Capstone DUOC UC.

El código está en `Fase 2/Evidencias Proyecto/`:

| Carpeta | Qué es | Tecnología |
|---|---|---|
| `database/` | Base de datos | PostgreSQL 16 + PostGIS |
| `backend/` | API: login, agenda, croquis, panel y webhook de WhatsApp con IA | Python, FastAPI |
| `frontend/` | Panel web para administradores | React + Vite |
| `app-movil/` | App para los técnicos en terreno | Flutter |

## Levantar todo con Docker

Requisito: [Docker Desktop](https://www.docker.com/products/docker-desktop/) abierto.

```bash
cp .env.example .env
docker compose up --build
```

La primera vez tarda unos minutos (descarga imágenes, instala dependencias y crea la base con datos de prueba). Cuando termine:

| Qué | Dirección | Usuario de prueba |
|---|---|---|
| Panel web | http://localhost:8080 | `admin@killbichos.cl` / `demo1234` |
| API (documentación) | http://localhost:8000/docs | `tecnico1@killbichos.cl` / `demo1234` |
| Base de datos | `localhost:5432` | los de `.env` |

Comandos útiles:

```bash
docker compose up -d --build   # levantar en segundo plano
docker compose ps              # ver qué está corriendo
docker compose logs -f backend # ver los logs del backend
docker compose down            # apagar (los datos se conservan)
docker compose down -v         # apagar y BORRAR la base (vuelve a cero)
```

### Claves y variables

- Todas las variables están en `.env`, que **no se sube a git** (`.gitignore`).
- `.env.example` es la plantilla: se sube al repo y **no tiene valores reales**. Las claves de Twilio y OpenAI van vacías ahí.
- Las claves reales se escriben **solo en `.env`**.
- Si cambias `VITE_API_URL`, reconstruye el panel con `docker compose up --build`: esa dirección se fija al compilar.

## App móvil (Flutter): no va en Docker

La app de los técnicos **no corre en Docker**: es una app que se compila e instala en el teléfono (o en el simulador). Docker levanta el backend al que la app se conecta.

La app necesita saber **en qué dirección está el backend**, y se le indica al compilar con `--dart-define=API_BASE_URL=...`:

| Dónde corre la app | Qué dirección usar | Por qué |
|---|---|---|
| **iPhone real** (misma WiFi que el computador) | `http://IP-DEL-COMPUTADOR:8000` | El teléfono es otro equipo de la red: `localhost` sería el propio teléfono |
| **Simulador de iPhone** | `http://127.0.0.1:8000` | El simulador comparte la red del computador |
| **Emulador de Android** | `http://10.0.2.2:8000` | Así ve el emulador al computador |
| **Chrome** | `http://127.0.0.1:8000` | Además: `--web-port=5173` (puerto permitido por CORS) |

Ejemplo con un iPhone real conectado por cable (en macOS, `ipconfig getifaddr en0` entrega la IP):

```bash
cd "Fase 2/Evidencias Proyecto/app-movil"
flutter run --release --dart-define=API_BASE_URL=http://$(ipconfig getifaddr en0):8000
```

El backend de Docker ya escucha en la red (puerto 8000), así que el teléfono lo alcanza sin configurar nada más. Detalles en el README de `app-movil`.

## Más información

- `Fase 2/Evidencias Proyecto/database/README.md` — scripts de la base y tareas frecuentes
- `Fase 2/Evidencias Proyecto/backend/README.md` — API, pruebas y agente de WhatsApp (Twilio + OpenAI)
- `Fase 2/Evidencias Proyecto/frontend/README.md` — panel web en modo desarrollo
