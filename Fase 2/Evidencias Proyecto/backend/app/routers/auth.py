# =============================================================================
# routers/auth.py — Inicio de sesión
# -----------------------------------------------------------------------------
#   POST /auth/login     recibe usuario y clave, y si son correctos entrega los
#                        tokens de sesión (access_token y refresh_token).
#   POST /auth/refresh   recibe el refresh_token y entrega tokens nuevos, para
#                        que la app no pida la clave cada vez que se abre.
# =============================================================================

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.engine import Connection

from app.config import settings
from app.database import get_db
from uuid import UUID

from jose import JWTError

from app.repositories import fetch_operator_by_email, fetch_operator_by_id, fetch_web_user_by_email, fetch_web_user_by_id
from app.schemas import LoginRequest, RefreshRequest, TokenResponse
from app.security import ACCESS_TOKEN_MINUTES, REFRESH_TOKEN_DAYS, create_token, decode_token, verify_password

router = APIRouter(tags=["autenticación"])


@router.post("/auth/login", response_model=TokenResponse)
def login(credentials: LoginRequest, db: Connection = Depends(get_db)) -> TokenResponse:
    """Valida usuario/clave contra la base real. Primero busca en
    'operadores' (app móvil); si no hay coincidencia, busca en 'usuarios'
    (panel web, roles admin/coordinador). Si fallan las credenciales
    devuelve 401 genérico, sin decir cuál de las dos estaba mala (evita
    filtrar si el usuario existe)."""
    # Se normaliza el email: sin espacios y en minúsculas, igual que en la base.
    email = credentials.usuario.strip().lower()

    # 1) ¿Es un operador de terreno?
    session_version = 0
    operator = fetch_operator_by_email(db, email)
    if operator is not None:
        user_id, rol, password_hash = operator["id"], "operador", operator["password_hash"]
        session_version = operator.get("session_version", 0)
    else:
        # 2) Si no, ¿es un usuario del panel web?
        web_user = fetch_web_user_by_email(db, email)
        if web_user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario o clave incorrectos")
        user_id, rol, password_hash = web_user["id"], web_user["rol"], web_user["password_hash"]
        session_version = web_user.get("session_version", 0)

    # 3) Compara la clave escrita con el hash guardado en la base.
    if not verify_password(credentials.clave, password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario o clave incorrectos")

    # 4) Todo correcto: se generan los dos tokens firmados.
    return _tokens_for(user_id, rol, session_version)


def _tokens_for(user_id: UUID, rol: str, session_version: int = 0) -> TokenResponse:
    """Genera el par de tokens firmados:
    - access_token: se manda en cada request, dura 8 horas.
    - refresh_token: dura 30 días y sirve para pedir un par nuevo."""
    return TokenResponse(
        access_token=create_token(user_id, rol, timedelta(minutes=ACCESS_TOKEN_MINUTES), "access", settings.jwt_secret, session_version),
        refresh_token=create_token(user_id, rol, timedelta(days=REFRESH_TOKEN_DAYS), "refresh", settings.jwt_secret, session_version),
    )


@router.post("/auth/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Connection = Depends(get_db)) -> TokenResponse:
    """Renueva la sesión sin pedir la clave. Responde 401 si el refresh_token
    es falso, venció (30 días), es un access_token o si la cuenta ya no
    existe o fue desactivada.

    Cada renovación entrega también un refresh_token nuevo: mientras el
    técnico use la app al menos una vez cada 30 días, no vuelve a escribir
    su clave."""
    invalid = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión vencida: vuelve a iniciar sesión")
    try:
        data = decode_token(payload.refresh_token, settings.jwt_secret)
        if data.get("type") != "refresh":
            raise invalid  # un access_token no sirve para renovar
        user_id = UUID(data["sub"])
        rol = data["rol"]
    except (JWTError, KeyError, ValueError):
        raise invalid
    # La cuenta tiene que seguir existiendo y activa (igual que en cada request).
    user = fetch_operator_by_id(db, user_id) if rol == "operador" else fetch_web_user_by_id(db, user_id)
    if user is None:
        raise invalid
    if data.get("sv", 0) != user.get("session_version", 0) or (
        rol != "operador" and rol != user.get("rol", rol)
    ):
        raise invalid
    return _tokens_for(user_id, rol, user.get("session_version", 0))
