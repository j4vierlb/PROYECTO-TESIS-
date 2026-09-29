# =============================================================================
# routers/auth.py — Inicio de sesión
# -----------------------------------------------------------------------------
#   POST /auth/login   recibe usuario y clave, y si son correctos entrega los
#                      tokens de sesión (access_token y refresh_token).
# =============================================================================

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.engine import Connection

from app.config import settings
from app.database import get_db
from app.repositories import fetch_operator_by_email, fetch_web_user_by_email
from app.schemas import LoginRequest, TokenResponse
from app.security import ACCESS_TOKEN_MINUTES, REFRESH_TOKEN_DAYS, create_token, verify_password

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
    operator = fetch_operator_by_email(db, email)
    if operator is not None:
        user_id, rol, password_hash = operator["id"], "operador", operator["password_hash"]
    else:
        # 2) Si no, ¿es un usuario del panel web?
        web_user = fetch_web_user_by_email(db, email)
        if web_user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario o clave incorrectos")
        user_id, rol, password_hash = web_user["id"], web_user["rol"], web_user["password_hash"]

    # 3) Compara la clave escrita con el hash guardado en la base.
    if not verify_password(credentials.clave, password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario o clave incorrectos")

    # 4) Todo correcto: se generan los dos tokens firmados.
    #    - access_token: se manda en cada request, dura 8 horas.
    #    - refresh_token: dura 30 días, pensado para renovar el anterior.
    return TokenResponse(
        access_token=create_token(user_id, rol, timedelta(minutes=ACCESS_TOKEN_MINUTES), "access", settings.jwt_secret),
        refresh_token=create_token(user_id, rol, timedelta(days=REFRESH_TOKEN_DAYS), "refresh", settings.jwt_secret),
    )
