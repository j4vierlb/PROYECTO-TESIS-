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
    email = credentials.usuario.strip().lower()

    operator = fetch_operator_by_email(db, email)
    if operator is not None:
        user_id, rol, password_hash = operator["id"], "operador", operator["password_hash"]
    else:
        web_user = fetch_web_user_by_email(db, email)
        if web_user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario o clave incorrectos")
        user_id, rol, password_hash = web_user["id"], web_user["rol"], web_user["password_hash"]

    if not verify_password(credentials.clave, password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario o clave incorrectos")

    return TokenResponse(
        access_token=create_token(user_id, rol, timedelta(minutes=ACCESS_TOKEN_MINUTES), "access", settings.jwt_secret),
        refresh_token=create_token(user_id, rol, timedelta(days=REFRESH_TOKEN_DAYS), "refresh", settings.jwt_secret),
    )
