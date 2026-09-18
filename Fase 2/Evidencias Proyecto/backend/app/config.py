from pydantic_settings import BaseSettings, SettingsConfigDict


# Lee JWT_SECRET, DATABASE_URL y ALLOWED_ORIGINS desde el archivo .env (o
# desde variables de entorno reales en producción). Así ningún secreto queda
# escrito en el código fuente.
class Settings(BaseSettings):
    jwt_secret: str = "desarrollo-cambia-esta-clave"
    database_url: str = "postgresql+psycopg://killbichos:killbichos_dev@localhost:5432/killbichos"
    allowed_origins: str = "http://localhost:3000,http://localhost:5173"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
