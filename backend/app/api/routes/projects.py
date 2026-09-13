"""Project register endpoints (Phase 3: Project + Document Foundation).

Before this phase, no project-listing or project-creation endpoint existed
at all — GET /health returned exactly one Project (the database's first
row) and nothing else, and the frontend worked around this with a static,
explicitly-labeled-as-not-live local directory fixture
(frontend/src/lib/projectDirectory.ts). This is the real replacement: a
project is a genuine, creatable, listable entity, backing the "see existing
projects / create a project / open a project" capability this phase asks
for. Project administration beyond that (rename, archive, per-project
settings) is out of scope for this phase.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Project
from app.db.session import get_db

router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, description="Project name")


@router.get("", response_model=list[ProjectResponse])
def list_projects(db: Session = Depends(get_db)) -> list[Project]:
    """List every project, oldest first (matches the order projects were
    established in, and keeps the seeded default project first)."""
    return list(db.scalars(select(Project).order_by(Project.id)))


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(body: ProjectCreateRequest, db: Session = Depends(get_db)) -> Project:
    project = Project(name=body.name.strip())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: int, db: Session = Depends(get_db)) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project
