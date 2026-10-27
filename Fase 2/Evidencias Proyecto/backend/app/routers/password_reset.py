from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.engine import Connection

from app.database import get_db
from app.password_reset import GENERIC_MESSAGE, enforce_limit, issue_token, mail_ready, redeem_token, send_reset_email

router = APIRouter(prefix="/auth", tags=["autenticación"])


class ForgotPassword(BaseModel):
    email: str = Field(min_length=3, max_length=150, pattern=r"^[^@\s<>]+@[^@\s<>]+\.[^@\s<>]+$")

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        if isinstance(value, str):
            value = value.strip().lower()
            if any(ord(char) < 32 or ord(char) == 127 for char in value):
                raise ValueError("El correo contiene caracteres no válidos.")
        return value


class ResetPassword(BaseModel):
    token: str = Field(min_length=43, max_length=43, pattern=r"^[A-Za-z0-9_-]+$")
    password: str = Field(min_length=12, max_length=72)

    @field_validator("password")
    @classmethod
    def password_bytes(cls, value):
        if "\x00" in value:
            raise ValueError("La contraseña contiene un carácter nulo no permitido por bcrypt.")
        if len(value.encode("utf-8")) > 72:
            raise ValueError("La contraseña no debe superar 72 bytes UTF-8.")
        return value


@router.post("/forgot-password", status_code=202)
def forgot_password(payload: ForgotPassword, request: Request, response: Response,
                    background_tasks: BackgroundTasks, db: Connection = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    if not mail_ready():
        raise HTTPException(503, "La recuperación por correo aún no está habilitada. Contacta al soporte.")
    enforce_limit(db, f"request-ip:{request.client.host if request.client else 'unknown'}", 20)
    enforce_limit(db, f"request-email:{payload.email}", 3)
    # La entrega se hace después de responder; no revela por latencia SMTP si
    # la cuenta existe. Tanto inexistentes como inactivas/operadores reciben 202.
    background_tasks.add_task(send_reset_email, issue_token(db, payload.email))
    return {"message": GENERIC_MESSAGE}


@router.post("/reset-password")
def reset_password(payload: ResetPassword, request: Request, response: Response,
                   db: Connection = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    enforce_limit(db, f"redeem-ip:{request.client.host if request.client else 'unknown'}", 30)
    redeem_token(db, payload.token, payload.password)
    return {"message": "Contraseña actualizada. Inicia sesión con tu nueva contraseña."}
