from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from sqlalchemy.exc import OperationalError

from app.api.router import api_router
from app.config import get_settings
from app.db.init_db import initialize_database
from app.db.session import dispose_engine, init_engine


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Prepare the database on startup and release connections on shutdown."""
    settings = get_settings()
    engine = init_engine(settings)
    try:
        initialize_database(engine, settings)
    except OperationalError as exc:
        raise RuntimeError(
            f"Could not connect to the database at {settings.database_url}. "
            "Is the Postgres container running? From backend/, run: "
            "docker compose up -d"
        ) from exc
    yield
    dispose_engine()


def create_app() -> FastAPI:
    """Construct and configure the FastAPI application instance."""
    settings = get_settings()

    app = FastAPI(
        title="ClaimTrace AI",
        description="Construction Claims Evidence Investigator — V0",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(api_router)

    @app.get("/", tags=["root"])
    def root() -> dict[str, str]:
        return {
            "message": "ClaimTrace AI backend is running",
            "environment": settings.app_env,
        }

    return app


app = create_app()
