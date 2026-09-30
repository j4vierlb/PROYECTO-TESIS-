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
    # 8080 = panel web en Docker; 5173 = panel en modo desarrollo (npm run dev).
    allowed_origins: str = "http://localhost:8080,http://localhost:3000,http://localhost:5173,http://127.0.0.1:5173"

    # --- Agente de WhatsApp (ver README, sección "Agente de WhatsApp + IA") ---
    # Clave y modelo de OpenAI. Vacía = el agente responde un mensaje de
    # contingencia ("un operador te contactará").
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    # Credenciales de Twilio. TWILIO_WEBHOOK_URL debe ser exactamente la URL
    # pública configurada en Twilio, porque con ella se valida la firma.
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_number: str = ""
    twilio_webhook_url: str = ""
    # true en producción. false solo para probar en local con curl.
    twilio_validate_signature: bool = True
    # Empresa que recibe las visitas agendadas por WhatsApp.
    killbichos_empresa_id: str = "11111111-1111-1111-1111-111111111111"
    # Operador fijo para esas visitas. Vacío = el operador libre con menos
    # visitas ese día.
    killbichos_operador_id: str = ""
    # Horario de atención (hora de Chile). Días: 0=lunes ... 6=domingo.
    killbichos_open_time: str = "08:00"
    killbichos_close_time: str = "18:00"
    killbichos_operating_days: str = "0,1,2,3,4,5"

    # env_file=".env": busca los valores en ese archivo.
    # extra="ignore": si el .env trae variables que no se usan aquí, no falla.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# Instancia única que el resto del backend importa (from app.config import settings).
settings = Settings()
