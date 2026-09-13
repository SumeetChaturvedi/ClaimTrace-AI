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


def ensure_document_lifecycle_columns(engine: Engine) -> None:
    """Retrofit the status/processing_error/updated_at columns (Phase 3:
    Project + Document Foundation) onto an already-existing, already-populated
    `documents` table via a safe, additive, idempotent ALTER — not a rebuild,
    and never destructive. This project has no migration tool, and
    Base.metadata.create_all() only creates tables that don't exist yet; it
    never alters one that already does, so a real ALTER is the only way to
    add columns to the real, populated `documents` table without dropping
    and recreating it. No-op in effect on a clean database (create_tables()
    above already creates the table with these columns from the start, so
    every `IF NOT EXISTS`/conditional guard here simply finds nothing to do).

    Every document that existed before this phase is backfilled to
    status='ready' — true, since it was already fully extracted, chunked,
    and embedded under the old all-or-nothing synchronous pipeline — with
    updated_at defaulted from its own uploaded_at. Nothing pre-existing is
    ever shown as uploaded/processing/failed just because this ran."""
    with engine.connect() as connection:
        connection.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS status TEXT"))
        connection.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS processing_error TEXT"))
        connection.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ"))
        connection.execute(text("UPDATE documents SET status = 'ready' WHERE status IS NULL"))
        connection.execute(text("UPDATE documents SET updated_at = uploaded_at WHERE updated_at IS NULL"))
        connection.execute(text("ALTER TABLE documents ALTER COLUMN status SET DEFAULT 'ready'"))
        connection.execute(text("ALTER TABLE documents ALTER COLUMN status SET NOT NULL"))
        connection.execute(text("ALTER TABLE documents ALTER COLUMN updated_at SET DEFAULT now()"))
        connection.execute(text("ALTER TABLE documents ALTER COLUMN updated_at SET NOT NULL"))
        connection.execute(text("ALTER TABLE documents ALTER COLUMN raw_text_path DROP NOT NULL"))
        connection.execute(
            text(
                """
                DO $$ BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_documents_status') THEN
                        ALTER TABLE documents ADD CONSTRAINT ck_documents_status
                            CHECK (status IN ('uploaded', 'processing', 'ready', 'failed'));
                    END IF;
                END $$;
                """
            )
        )
        connection.commit()


def ensure_investigation_timeline_column(engine: Engine) -> None:
    """Retrofit the `timeline` JSONB column (Phase 4: Timeline
    Productization) onto an already-existing, already-populated
    `investigation_records` table via a safe, additive, idempotent ALTER —
    same reasoning and same pattern as ensure_document_lifecycle_columns
    above: no migration tool exists, and Base.metadata.create_all() never
    alters a table that already exists. No-op in effect on a clean database.

    Every investigation that ran before this phase is left with
    timeline = NULL, not []; the API layer (app/api/routes/investigations.py)
    treats NULL identically to an empty timeline, so old, already-completed
    investigations keep opening successfully without a timeline rather than
    being backfilled with a fabricated one."""
    with engine.connect() as connection:
        connection.execute(text("ALTER TABLE investigation_records ADD COLUMN IF NOT EXISTS timeline JSONB"))
        connection.commit()


def ensure_investigation_contract_clauses_column(engine: Engine) -> None:
    """Retrofit the `contract_clauses` JSONB column (Phase 5: Contract
    Intelligence Productization) onto an already-existing, already-populated
    `investigation_records` table — same safe, additive, idempotent ALTER
    pattern as ensure_investigation_timeline_column above. No-op in effect
    on a clean database.

    Every investigation that ran before this phase is left with
    contract_clauses = NULL, not []; the API layer
    (app/api/routes/investigations.py) treats NULL identically to an empty
    list, so old investigations keep opening successfully without contract
    data rather than being backfilled with fabricated clauses."""
    with engine.connect() as connection:
        connection.execute(text("ALTER TABLE investigation_records ADD COLUMN IF NOT EXISTS contract_clauses JSONB"))
        connection.commit()


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
    ensure_document_lifecycle_columns(engine)
    ensure_investigation_timeline_column(engine)
    ensure_investigation_contract_clauses_column(engine)
    ensure_storage_root(settings.storage_root)

    with get_session_factory()() as session:
        return seed_default_project(session, settings.default_project_name)
