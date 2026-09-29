# =============================================================================
# security.py — Contraseñas y tokens de sesión
# -----------------------------------------------------------------------------
# Dos responsabilidades:
#   1. Cifrar y verificar contraseñas (con bcrypt, a través de passlib).
#   2. Crear y leer los tokens JWT que la app usa como "pase" de sesión.
# =============================================================================

from datetime import datetime, timedelta, timezone
from uuid import UUID

from jose import jwt
from passlib.context import CryptContext

# Algoritmo de firma del JWT: HS256 = HMAC con SHA-256, usando JWT_SECRET.
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 8 * 60  # el access_token dura 8 horas (turno de un operador)
REFRESH_TOKEN_DAYS = 30        # el refresh_token dura 30 días

# bcrypt hashea la clave con un salt aleatorio por contraseña (distinto del
# hash mock anterior, que usaba un salt fijo solo para pruebas en memoria).
# "Hashear" = transformar la clave en un texto irreversible: en la base nunca
# se guarda "demo1234", sino algo como "$2b$12$Pmmaj...". Así, si alguien
# roba la base de datos, no puede leer las contraseñas.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def utc_now() -> datetime:
    """Hora actual en UTC, para que todas las fechas del sistema queden en
    el mismo huso horario sin importar dónde corra el servidor."""
    return datetime.now(timezone.utc)


def hash_password(password: str) -> str:
    """Convierte una contraseña en su hash bcrypt (para guardarla en la base)."""
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Compara la clave en texto plano contra el hash guardado en la base.
    passlib hace la comparación de forma segura (resistente a timing attacks)."""
    return pwd_context.verify(password, password_hash)


def create_token(user_id: UUID, rol: str, expires_delta: timedelta, token_type: str, secret: str) -> str:
    """Genera un JWT firmado. El payload lleva el id del usuario (sub), su
    rol, si es access o refresh token, y la expiración (exp)."""
    expires_at = utc_now() + expires_delta
    # El payload es la información que viaja dentro del token. Cualquiera puede
    # leerla, pero nadie puede modificarla sin invalidar la firma.
    payload = {"sub": str(user_id), "rol": rol, "type": token_type, "exp": expires_at}
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)


def decode_token(token: str, secret: str) -> dict:
    """Verifica la firma y la expiración del token y devuelve su payload.
    Si el token es falso o ya venció, lanza un error (JWTError)."""
    return jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
