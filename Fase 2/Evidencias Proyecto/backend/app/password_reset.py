"""Recuperación exclusiva del panel. Nunca se registran enlaces ni claves."""
import hashlib
import hmac
import logging
import re
import secrets
import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import urlsplit

from fastapi import HTTPException
from sqlalchemy import text

from app.config import settings
from app.security import hash_password

RESET_MINUTES = 15
GENERIC_MESSAGE = "Si el correo corresponde a una cuenta activa del panel, recibirás un enlace para restablecer tu contraseña."
INVALID_LINK = "El enlace no es válido o ya venció. Solicita uno nuevo."
logger = logging.getLogger(__name__)


def mail_ready() -> bool:
    """Falla cerrada: HTTPS fuera de loopback y transporte SMTP con TLS."""
    try:
        url = urlsplit(settings.password_reset_panel_url)
        valid_url = (
            bool(url.hostname) and not url.username and not url.password
            and not url.query and not url.fragment
            and (url.port is None or 1 <= url.port <= 65535)
            and (url.scheme == "https" or (
                url.scheme == "http" and url.hostname in {"localhost", "127.0.0.1", "::1"}
            ))
        )
        return bool(
            settings.password_reset_enabled and valid_url
            and settings.smtp_host and 1 <= settings.smtp_port <= 65535
            and re.fullmatch(r"[^@\s<>]+@[^@\s<>]+\.[^@\s<>]+", settings.smtp_from)
            and settings.smtp_security in {"starttls", "ssl"}
            and bool(settings.smtp_user) == bool(settings.smtp_password)
        )
    except ValueError:
        return False


def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def enforce_limit(db, scope: str, maximum: int) -> None:
    # No usar X-Forwarded-For suministrado por el cliente. Un proxy de confianza
    # debe configurar la IP real del ASGI server; documentado en README.
    key = hmac.new(settings.jwt_secret.encode(), scope.encode(), hashlib.sha256).hexdigest()
    db.execute(text("DELETE FROM password_reset_limits WHERE expires_at < now()"))
    count = db.execute(text("""
        INSERT INTO password_reset_limits(scope_hash, attempts, expires_at)
        VALUES (:key, 1, now() + interval '15 minutes')
        ON CONFLICT (scope_hash) DO UPDATE
        SET attempts = LEAST(password_reset_limits.attempts + 1, :ceiling)
        RETURNING attempts
    """), {"key": key, "ceiling": maximum + 1}).scalar_one()
    db.commit()
    if count > maximum:
        raise HTTPException(429, "Demasiados intentos. Espera 15 minutos antes de volver a intentar.",
                            headers={"Retry-After": "900"})


def issue_token(db, email: str) -> tuple[str, str] | None:
    # Se guarda solo el hash SHA256 de 256 bits aleatorios. Nunca el enlace.
    db.execute(text("DELETE FROM password_reset_tokens WHERE expires_at < now()"))
    user = db.execute(text("""
        SELECT id, email, session_version FROM usuarios
        WHERE email = :email AND activo = TRUE AND rol IN ('admin', 'coordinador')
    """), {"email": email}).mappings().first()
    if not user:
        db.commit()
        return None
    token = secrets.token_urlsafe(32)
    db.execute(text("""
        INSERT INTO password_reset_tokens(token_hash, usuario_id, session_version, expires_at)
        VALUES (:hash, :id, :version, now() + interval '15 minutes')
    """), {"hash": digest(token), "id": user["id"], "version": user["session_version"]})
    db.commit()
    # El fragmento no se envía al servidor web ni en Referer. El panel lo borra
    # de la barra/historial y solo lo transmite en el cuerpo del POST a la API.
    link = f"{settings.password_reset_panel_url.rstrip('/')}#restablecer={token}"
    return user["email"], link


def send_reset_email(delivery: tuple[str, str] | None) -> None:
    if delivery is None:
        return
    recipient, link = delivery
    message = EmailMessage()
    message["Subject"] = "Restablecer contraseña — Kill Bichos"
    message["From"] = settings.smtp_from
    message["To"] = recipient
    message.set_content(
        f"Recibimos una solicitud para restablecer tu contraseña del panel Kill Bichos.\n\n"
        f"Abre este enlace (válido por {RESET_MINUTES} minutos y un solo uso):\n{link}\n\n"
        "Si no lo solicitaste, ignora este correo. Tu contraseña no ha cambiado.\n"
        "Después del cambio se cerrarán tus sesiones anteriores del panel.\n"
    )
    try:
        context = ssl.create_default_context()
        if settings.smtp_security == "ssl":
            client = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=10, context=context)
        else:
            client = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10)
        with client:
            if settings.smtp_security == "starttls":
                client.starttls(context=context)
            if settings.smtp_user:
                client.login(settings.smtp_user, settings.smtp_password)
            client.send_message(message)
    except (OSError, smtplib.SMTPException):
        # No incluir excepción, destinatario o message: pueden contener secretos.
        logger.warning("No se pudo entregar un correo de recuperación; revisar configuración SMTP.")


def redeem_token(db, token: str, password: str) -> None:
    token_hash = digest(token)
    owner = db.execute(text("SELECT usuario_id FROM password_reset_tokens WHERE token_hash = :hash"),
                       {"hash": token_hash}).scalar_one_or_none()
    if owner is None:
        raise HTTPException(400, INVALID_LINK)
    # Serializa todos los canjes de una cuenta. Se consulta el token NUEVAMENTE
    # después del lock para impedir reutilización incluso en solicitudes paralelas.
    user = db.execute(text("""
        SELECT id, session_version FROM usuarios WHERE id = :id AND activo = TRUE
        AND rol IN ('admin', 'coordinador') FOR UPDATE
    """), {"id": owner}).mappings().first()
    valid = db.execute(text("""
        SELECT session_version FROM password_reset_tokens
        WHERE token_hash = :hash AND expires_at > clock_timestamp()
    """), {"hash": token_hash}).scalar_one_or_none()
    if not user or valid is None or valid != user["session_version"]:
        db.rollback()
        raise HTTPException(400, INVALID_LINK)
    try:
        db.execute(text("""
            UPDATE usuarios SET password_hash = :password, session_version = session_version + 1
            WHERE id = :id
        """), {"password": hash_password(password), "id": owner})
        db.execute(text("DELETE FROM password_reset_tokens WHERE usuario_id = :id"), {"id": owner})
        db.commit()
    except Exception:
        db.rollback()
        raise
