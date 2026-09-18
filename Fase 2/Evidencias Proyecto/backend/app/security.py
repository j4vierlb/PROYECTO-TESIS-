from datetime import datetime, timedelta, timezone
from uuid import UUID

from jose import jwt
from passlib.context import CryptContext

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 8 * 60  # el access_token dura 8 horas (turno de un operador)
REFRESH_TOKEN_DAYS = 30

# bcrypt hashea la clave con un salt aleatorio por contraseña (distinto del
# hash mock anterior, que usaba un salt fijo solo para pruebas en memoria).
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def utc_now() -> datetime:
    """Hora actual en UTC, para que todas las fechas del sistema queden en
    el mismo huso horario sin importar dónde corra el servidor."""
    return datetime.now(timezone.utc)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Compara la clave en texto plano contra el hash guardado en la base.
    passlib hace la comparación de forma segura (resistente a timing attacks)."""
    return pwd_context.verify(password, password_hash)


def create_token(user_id: UUID, rol: str, expires_delta: timedelta, token_type: str, secret: str) -> str:
    """Genera un JWT firmado. El payload lleva el id del usuario (sub), su
    rol, si es access o refresh token, y la expiración (exp)."""
    expires_at = utc_now() + expires_delta
    payload = {"sub": str(user_id), "rol": rol, "type": token_type, "exp": expires_at}
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)


def decode_token(token: str, secret: str) -> dict:
    return jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
