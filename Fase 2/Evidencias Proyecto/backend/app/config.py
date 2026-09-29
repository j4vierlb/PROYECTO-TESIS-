# =============================================================================
# config.py — Configuración del backend
# -----------------------------------------------------------------------------
# Reúne en un solo lugar los valores que cambian según dónde corra el sistema
# (el computador de un desarrollador o un servidor real): la clave secreta de
# los tokens, la dirección de la base de datos y los sitios web permitidos.
# =============================================================================

from pydantic_settings import BaseSettings, SettingsConfigDict


# Settings lee JWT_SECRET, DATABASE_URL y ALLOWED_ORIGINS desde el archivo .env
# (o desde variables de entorno reales en producción). Así ningún secreto
# queda escrito en el código fuente que se sube a git.
#
# Los valores escritos aquí son solo "por defecto", para desarrollo local: si
# el .env trae su propio valor, ese es el que se usa.
class Settings(BaseSettings):
    # Clave con la que se firman los tokens de sesión (JWT). Quien la conozca
    # podría fabricar tokens falsos, por eso en un servidor real debe ser larga
    # y aleatoria (por ejemplo: openssl rand -hex 32).
    jwt_secret: str = "desarrollo-cambia-esta-clave"
    # Dirección de PostgreSQL: driver+tipo://usuario:clave@servidor:puerto/base
    database_url: str = "postgresql+psycopg://killbichos:killbichos_dev@localhost:5432/killbichos"
    # Sitios web que pueden llamar a la API desde un navegador (ver CORS en main.py).
    allowed_origins: str = "http://localhost:3000,http://localhost:5173,http://127.0.0.1:5173"
    # env_file=".env": busca los valores en ese archivo.
    # extra="ignore": si el .env trae variables que no se usan aquí, no falla.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# Instancia única que el resto del backend importa (from app.config import settings).
settings = Settings()
