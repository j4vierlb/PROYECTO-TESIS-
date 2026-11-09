# =============================================================================
# repositories/auth.py — Consultas de autenticación
# (ver repositories/__init__.py para el patrón general de las consultas)
# =============================================================================

from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Connection


# ---------------------------------------------------------------------------
# Consultas relacionadas a autenticación
# ---------------------------------------------------------------------------
# Hay dos tablas de personas: `operadores` (técnicos de la app móvil) y
# `usuarios` (admin/coordinador del panel web). Todas filtran por
# activo = TRUE, así una cuenta desactivada no puede entrar ni seguir usando
# un token que ya tenía.

def fetch_operator_by_email(db: Connection, email: str) -> dict[str, Any] | None:
    """Busca un operador activo por email (para el login). None si no existe."""
    row = db.execute(
        text(
            "SELECT id, nombre, empresa_id, password_hash, session_version FROM operadores "
            "WHERE email = :email AND activo = TRUE"
        ),
        {"email": email},
    ).mappings().first()
    return dict(row) if row else None


def fetch_web_user_by_email(db: Connection, email: str) -> dict[str, Any] | None:
    """Busca un usuario del panel web activo por email (para el login)."""
    row = db.execute(
        text(
            "SELECT id, nombre, empresa_id, rol, password_hash, session_version FROM usuarios "
            "WHERE email = :email AND activo = TRUE"
        ),
        {"email": email},
    ).mappings().first()
    return dict(row) if row else None


def fetch_operator_by_id(db: Connection, user_id: UUID) -> dict[str, Any] | None:
    """Busca un operador activo por id (para validar el token en cada request)."""
    row = db.execute(
        text("SELECT id, nombre, empresa_id, session_version FROM operadores WHERE id = :id AND activo = TRUE"),
        {"id": str(user_id)},
    ).mappings().first()
    return dict(row) if row else None


def fetch_web_user_by_id(db: Connection, user_id: UUID) -> dict[str, Any] | None:
    """Busca un usuario del panel web activo por id (para validar su token)."""
    row = db.execute(
        text("SELECT id, nombre, empresa_id, rol, session_version FROM usuarios WHERE id = :id AND activo = TRUE"),
        {"id": str(user_id)},
    ).mappings().first()
    return dict(row) if row else None
