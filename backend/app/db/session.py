from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, get_settings
from app.db.models import Base


def create_db_engine(database_url: str) -> Engine:
    """Build a SQLAlchemy engine with dead-connection detection enabled."""
    return create_engine(database_url, pool_pre_ping=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def init_engine(settings: Settings | None = None) -> Engine:
    """Create the process-wide engine and session factory. Called once at app startup."""
    global _engine, _session_factory

    resolved_settings = settings or get_settings()
    _engine = create_db_engine(resolved_settings.database_url)
    _session_factory = create_session_factory(_engine)
    return _engine


def dispose_engine() -> None:
    """Release pooled connections. Called at app shutdown."""
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None


def get_engine() -> Engine:
    if _engine is None:
        return init_engine()
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    if _session_factory is None:
        init_engine()
    assert _session_factory is not None
    return _session_factory


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a request-scoped session, closed after the request."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def check_database_connection(engine: Engine) -> None:
    """Raise if the database is unreachable; used by the health endpoint."""
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
