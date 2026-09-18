from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Connection

from app.config import settings

# pool_pre_ping evita usar una conexión "muerta" del pool (ej: si Postgres
# se reinició) — SQLAlchemy la descarta y abre una nueva automáticamente.
engine = create_engine(settings.database_url, pool_pre_ping=True)


def get_db() -> Generator[Connection, None, None]:
    """Dependencia de FastAPI: abre una conexión por request y la cierra al
    terminar, incluso si el endpoint lanza una excepción."""
    with engine.connect() as connection:
        yield connection
