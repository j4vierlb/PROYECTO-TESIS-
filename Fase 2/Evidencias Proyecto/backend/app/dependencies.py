from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.engine import Connection

from app.config import settings
from app.database import get_db
from app.repositories import fetch_operator_by_id, fetch_web_user_by_id
from app.schemas import CurrentUser
from app.security import decode_token

security = HTTPBearer(auto_error=False)  # extrae el header "Authorization: Bearer <token>"


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Connection = Depends(get_db),
) -> CurrentUser:
    """Dependencia de FastAPI que se inyecta en cada endpoint protegido.
    Lee el header Authorization, valida el JWT y busca al usuario real en
    Postgres (operadores si el rol es 'operador', usuarios en caso contrario).
    Si algo falla responde 401 con el formato de error {"detail": "..."}."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de acceso requerido")
    try:
        payload = decode_token(credentials.credentials, settings.jwt_secret)
        if payload.get("type") != "access":
            raise JWTError  # un refresh_token no debe servir para autenticar requests
        user_id = UUID(payload["sub"])
        rol = payload["rol"]
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido o expirado")

    if rol == "operador":
        user = fetch_operator_by_id(db, user_id)
    else:
        user = fetch_web_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado")
    return CurrentUser(id=user["id"], nombre=user["nombre"], rol=rol, empresa_id=user["empresa_id"])


def require_operator(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Igual que get_current_user, pero además exige que el rol sea 'operador'.
    Se usa en los endpoints exclusivos del técnico en terreno."""
    if user.rol != "operador":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Se requiere un operador")
    return user


def ensure_visit_access(user: CurrentUser, visit: dict) -> None:
    """Un operador solo puede ver/editar sus propias visitas; un admin puede
    ver cualquiera. Se reutiliza en los routers de visitas y croquis, ya que
    el croquis hereda el control de acceso de su visita."""
    if user.rol == "operador" and visit["operador_id"] != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="La visita no pertenece al operador")
