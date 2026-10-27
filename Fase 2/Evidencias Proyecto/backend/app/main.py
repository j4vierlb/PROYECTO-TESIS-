# =============================================================================
# main.py — Punto de entrada del backend
# -----------------------------------------------------------------------------
# Este archivo "arma" la aplicación: crea el servidor FastAPI, configura la
# seguridad de navegadores (CORS) y conecta los routers, que son los archivos
# de la carpeta routers/ donde vive cada grupo de endpoints.
#
# Se levanta con:   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
#   - "app.main"  = este archivo (carpeta app, archivo main.py)
#   - ":app"      = la variable `app` definida más abajo
# =============================================================================

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, conversaciones, croquis, dispositivos, panel, password_reset, visitas, whatsapp
from app.whatsapp_saliente import ejecutar_recordatorios

# Muestra en consola los mensajes de log del backend (logger.info, .warning,
# .exception). Sin esto, uvicorn solo imprime sus propios logs y los errores
# del agente de WhatsApp no se verían.
logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s - %(message)s")
# httpx registra cada URL pedida, y las de Google Maps llevan la clave en
# "?key=...": se silencia para que la clave no quede escrita en los logs.
logging.getLogger("httpx").setLevel(logging.WARNING)
# Lo mismo con el cliente de Twilio: registra cada request con su URL.
logging.getLogger("twilio.http_client").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Cada cuánto se revisa si hay recordatorios de WhatsApp por enviar.
REMINDER_INTERVAL_SECONDS = 600


async def _reminder_loop() -> None:
    """Cada 10 minutos envía los recordatorios de las visitas de mañana que
    falten (solo desde WHATSAPP_RECORDATORIO_HORA). Si el servidor estuvo
    apagado a esa hora, los envía al volver. recordatorio_enviado_at evita
    duplicados aunque corran varios procesos del backend."""
    while True:
        await asyncio.sleep(REMINDER_INTERVAL_SECONDS)
        try:
            # Twilio y la base son síncronos: se ejecuta en un hilo aparte.
            await asyncio.to_thread(ejecutar_recordatorios)
        except Exception:
            logger.exception("Falló el envío de recordatorios de WhatsApp")


@asynccontextmanager
async def lifespan(_: FastAPI):
    task = asyncio.create_task(_reminder_loop())
    yield
    task.cancel()

# Crea la aplicación. El título, la versión y la descripción aparecen en la
# documentación automática que FastAPI genera en /docs (Swagger).
app = FastAPI(
    title="Kill Bichos IA API",
    version="0.2.0",
    description="Backend conectado a PostgreSQL/PostGIS para la operación de control de plagas",
    lifespan=lifespan,
)

# CORS: regla de seguridad de los navegadores. Un sitio web solo puede llamar
# a esta API si su dirección está en la lista permitida (ALLOWED_ORIGINS en el
# archivo .env). Nunca se usa "*" (cualquier sitio), para no exponer la API.
# La app móvil nativa no pasa por CORS: esto solo afecta a navegadores.
app.add_middleware(
    CORSMiddleware,
    # Convierte "http://localhost:3000,http://localhost:5173" en una lista.
    allow_origins=[origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# Registra cada grupo de endpoints en la aplicación.
app.include_router(auth.router)
app.include_router(password_reset.router)
app.include_router(visitas.router)       # agenda del día, historial y visitas
app.include_router(panel.router)         # panel web: clientes y agendamiento
app.include_router(croquis.router)       # croquis de la visita y agregar trampas
app.include_router(dispositivos.router)  # acciones y fotos de una trampa
app.include_router(whatsapp.router)      # POST /webhooks/whatsapp (Twilio)
app.include_router(conversaciones.router)  # bandeja de WhatsApp del panel


@app.get("/health", tags=["sistema"])
def health() -> dict[str, str]:
    """Confirma que el servidor está vivo (no requiere login)."""
    return {"status": "ok"}
