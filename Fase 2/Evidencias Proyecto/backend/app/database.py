# =============================================================================
# database.py — Conexión con PostgreSQL
# -----------------------------------------------------------------------------
# Crea el "motor" de SQLAlchemy (el objeto que sabe conectarse a la base de
# datos) y una función que entrega una conexión a cada endpoint que la pida.
# =============================================================================

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Connection

from app.config import settings

# El engine mantiene un "pool": un grupo de conexiones abiertas que se reutilizan
# entre requests, en vez de abrir una conexión nueva cada vez (que es lento).
# pool_pre_ping evita usar una conexión "muerta" del pool (ej: si Postgres
# se reinició) — SQLAlchemy la descarta y abre una nueva automáticamente.
engine = create_engine(settings.database_url, pool_pre_ping=True)


def get_db() -> Generator[Connection, None, None]:
    """Dependencia de FastAPI: abre una conexión por request y la cierra al
    terminar, incluso si el endpoint lanza una excepción."""
    # `with` garantiza que la conexión se devuelva al pool al salir.
    # `yield` entrega la conexión al endpoint y espera a que termine antes de
    # continuar (y cerrarla).
    with engine.connect() as connection:
        yield connection
