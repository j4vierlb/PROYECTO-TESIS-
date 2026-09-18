from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, croquis, dispositivos, visitas

app = FastAPI(
    title="Kill Bichos IA API",
    version="0.2.0",
    description="Backend conectado a PostgreSQL/PostGIS para la operación de control de plagas",
)

# CORS restringido: solo el frontend corriendo en localhost puede llamar a
# esta API desde el navegador. Nunca se usa "*" para no exponer la API a
# cualquier sitio web.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth.router)
app.include_router(visitas.router)
app.include_router(croquis.router)
app.include_router(dispositivos.router)


@app.get("/health", tags=["sistema"])
def health() -> dict[str, str]:
    """Confirma que el servidor está vivo (no requiere login)."""
    return {"status": "ok"}
