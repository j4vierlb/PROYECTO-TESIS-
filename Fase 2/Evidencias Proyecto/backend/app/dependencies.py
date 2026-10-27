# =============================================================================
# dependencies.py — Quién está haciendo el request y qué puede hacer
# -----------------------------------------------------------------------------
# Autenticación (¿quién eres?) y autorización (¿puedes hacer esto?).
# Los endpoints las usan con Depends(...): FastAPI las ejecuta antes del
# endpoint, y si fallan cortan el request con el error correspondiente:
#   401 Unauthorized = no hay sesión válida (sin token, vencido o falso)
#   403 Forbidden    = hay sesión, pero no tienes permiso para eso
# =============================================================================

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

# Extrae el header "Authorization: Bearer <token>".
# auto_error=False: si falta, no responde por su cuenta; dejamos que
# get_current_user responda con nuestro propio mensaje de error.
security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Connection = Depends(get_db),
) -> CurrentUser:
    """Dependencia de FastAPI que se inyecta en cada endpoint protegido.
    Lee el header Authorization, valida el JWT y busca al usuario real en
    Postgres (operadores si el rol es 'operador', usuarios en caso contrario).
    Si algo falla responde 401 con el formato de error {"detail": "..."}."""
    # 1) ¿Llegó un token?
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de acceso requerido")
    # 2) ¿El token es auténtico, no venció y es de tipo "access"?
    try:
        payload = decode_token(credentials.credentials, settings.jwt_secret)
        if payload.get("type") != "access":
            raise JWTError  # un refresh_token no debe servir para autenticar requests
        user_id = UUID(payload["sub"])
        rol = payload["rol"]
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido o expirado")

    # 3) ¿La persona sigue existiendo y activa en la base? (Si se desactivó
    #    la cuenta, su token deja de servir aunque no haya vencido.)
    if rol == "operador":
        user = fetch_operator_by_id(db, user_id)
    else:
        user = fetch_web_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado")
    if rol != "operador" and (
        payload.get("sv", 0) != user.get("session_version", 0)
        or rol != user.get("rol", rol)
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión revocada: vuelve a iniciar sesión")
    return CurrentUser(id=user["id"], nombre=user["nombre"], rol=rol, empresa_id=user["empresa_id"])


def require_operator(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Igual que get_current_user, pero además exige que el rol sea 'operador'.
    Se usa en los endpoints exclusivos del técnico en terreno."""
    # Depende de get_current_user: primero valida la sesión y después el rol.
    if user.rol != "operador":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Se requiere un operador")
    return user


def require_web_user(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Restringe el panel web a usuarios administrativos de la empresa."""
    if user.rol not in {"admin", "coordinador"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Se requiere un usuario del panel")
    return user


def ensure_visit_access(user: CurrentUser, visit: dict) -> None:
    """Nadie accede a visitas de otra empresa. Dentro de la propia empresa,
    un operador solo puede ver/editar sus propias visitas, y un admin o
    coordinador puede ver cualquiera. Se reutiliza en los routers de visitas
    y croquis, ya que el croquis hereda el control de acceso de su visita.
    `visit` viene de repositories.fetch_visit (incluye empresa_id)."""
    # Primero la empresa: aplica a todos los roles. Sin esto, un admin de otra
    # empresa podía leer cualquier visita (y su croquis) con solo conocer el id.
    if visit["empresa_id"] != user.empresa_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="La visita no pertenece a la empresa")
    if user.rol == "operador" and visit["operador_id"] != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="La visita no pertenece al operador")


# Estados en los que la visita ya terminó: su croquis queda solo de consulta.
_CLOSED_VISIT_STATES = {"completada", "cancelada"}


def ensure_visit_open(visit_estado: str | None) -> None:
    """Corta con 409 si la visita ya está completada o cancelada: su croquis
    no se puede modificar (mismo criterio que usa la app en modo lectura)."""
    if visit_estado in _CLOSED_VISIT_STATES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La visita ya está cerrada: su croquis es solo de consulta",
        )


def ensure_device_access(user: CurrentUser, device: dict) -> None:
    """Una trampa hereda el control de acceso de la visita de su croquis
    (`device` viene de repositories.fetch_device_context):
    - un operador solo accede a las trampas de sus propias visitas;
    - un usuario del panel, a las de su propia empresa."""
    if user.rol == "operador":
        if device["operador_id"] != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="La trampa no pertenece al operador")
    elif device["empresa_id"] != user.empresa_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="La trampa no pertenece a la empresa")
