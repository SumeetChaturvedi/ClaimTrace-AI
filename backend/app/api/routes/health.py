from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models import Project
from app.db.session import check_database_connection, get_db, get_engine

router = APIRouter(tags=["health"])


class ProjectSummary(BaseModel):
    id: int
    name: str
    created_at: datetime


class HealthResponse(BaseModel):
    status: str
    app: str
    database: str
    project: ProjectSummary


@router.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)) -> HealthResponse:
    try:
        check_database_connection(get_engine())
        project = db.scalar(select(Project).limit(1))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database unavailable: {exc}",
        ) from exc

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connected but default project is missing",
        )

    return HealthResponse(
        status="ok",
        app="running",
        database="connected",
        project=ProjectSummary(
            id=project.id,
            name=project.name,
            created_at=project.created_at,
        ),
    )
