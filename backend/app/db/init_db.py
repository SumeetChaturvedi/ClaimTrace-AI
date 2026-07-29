from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import Base, Project
from app.db.session import get_session_factory


def ensure_pgvector_extension(engine: Engine) -> None:
    """Create the pgvector extension if it isn't already installed on this database."""
    with engine.connect() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        connection.commit()


def create_tables(engine: Engine) -> None:
    """Create any tables declared on the ORM Base that don't already exist."""
    Base.metadata.create_all(bind=engine)


def ensure_storage_root(storage_root: Path) -> None:
    storage_root.mkdir(parents=True, exist_ok=True)


def seed_default_project(session: Session, project_name: str) -> Project:
    """Idempotently ensure the single default fictional project exists."""
    existing_project = session.scalar(select(Project).limit(1))
    if existing_project is not None:
        return existing_project

    project = Project(name=project_name)
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


def initialize_database(engine: Engine, settings: Settings) -> Project:
    """Run all startup DB prep: extension, schema, storage dir, default project seed."""
    ensure_pgvector_extension(engine)
    create_tables(engine)
    ensure_storage_root(settings.storage_root)

    with get_session_factory()() as session:
        return seed_default_project(session, settings.default_project_name)
