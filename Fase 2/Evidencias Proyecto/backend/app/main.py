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

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, croquis, dispositivos, visitas, whatsapp

# Muestra en consola los mensajes de log del backend (logger.info, .warning,
# .exception). Sin esto, uvicorn solo imprime sus propios logs y los errores
# del agente de WhatsApp no se verían.
logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s - %(message)s")

# Crea la aplicación. El título, la versión y la descripción aparecen en la
# documentación automática que FastAPI genera en /docs (Swagger).
app = FastAPI(
    title="Kill Bichos IA API",
    version="0.2.0",
    description="Backend conectado a PostgreSQL/PostGIS para la operación de control de plagas",
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
    # Solo los métodos HTTP que la API realmente usa.
    allow_methods=["GET", "POST", "PATCH"],
    # Solo los encabezados necesarios: el token y el tipo de contenido (JSON).
    allow_headers=["Authorization", "Content-Type"],
)

# Registra cada grupo de endpoints en la aplicación.
app.include_router(auth.router)          # POST /auth/login
app.include_router(visitas.router)       # agenda del día, historial y visitas
app.include_router(croquis.router)       # GET /croquis/{visita_id}
app.include_router(dispositivos.router)  # PATCH /dispositivos-trampa/{id}
app.include_router(whatsapp.router)      # POST /webhooks/whatsapp (Twilio)


@app.get("/health", tags=["sistema"])
def health() -> dict[str, str]:
    """Confirma que el servidor está vivo (no requiere login)."""
    return {"status": "ok"}
