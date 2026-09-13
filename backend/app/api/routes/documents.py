"""Document upload and listing endpoints. V0 has exactly one project, seeded
at startup, so uploads always attach to it — see app/db/init_db.py."""

from datetime import date, datetime

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.models import Document, Project
from app.db.session import get_db
from app.ingestion.pipeline import IngestionError, ingest_document

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    doc_type: str | None
    doc_date: date | None
    referenced_ids: list[str] | None
    status: str
    processing_error: str | None = None
    uploaded_at: datetime
    updated_at: datetime


class UploadResult(BaseModel):
    filename: str
    status: str
    document: DocumentSummary | None = None
    error: str | None = None


class UploadResponse(BaseModel):
    results: list[UploadResult]


def _get_default_project(db: Session) -> Project:
    project = db.scalar(select(Project).order_by(Project.id).limit(1))
    if project is None:
        raise RuntimeError("Default project is missing — DB was not initialized correctly")
    return project


@router.post("/upload", response_model=UploadResponse)
async def upload_documents(
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> UploadResponse:
    """Upload one or more PDFs. Each file is stored, text-extracted, and
    recorded independently — a corrupted or invalid file in the batch is
    reported as a per-file error without blocking the rest."""
    project = _get_default_project(db)

    results: list[UploadResult] = []
    for upload in files:
        name = upload.filename or "unnamed.pdf"
        content = await upload.read()
        try:
            document = ingest_document(
                session=db,
                storage_root=settings.storage_root,
                project_id=project.id,
                filename=name,
                content=content,
            )
        except IngestionError as exc:
            # Pre-flight validation only now (unsupported file type, empty, oversized) —
            # ingest_document() itself persists a 'failed' Document for any
            # failure past that point, so this file couldn't be accepted at
            # all rather than having failed while processing.
            results.append(UploadResult(filename=name, status="error", error=str(exc)))
            continue
        except SQLAlchemyError as exc:
            db.rollback()
            results.append(UploadResult(filename=name, status="error", error=f"database error: {exc}"))
            continue

        # document.status is 'ready' or 'failed' — reflected honestly here
        # rather than hardcoding "success", since ingest_document() no
        # longer raises for a processing (as opposed to validation) failure.
        results.append(
            UploadResult(
                filename=name,
                status=document.status,
                document=DocumentSummary.model_validate(document),
                error=document.processing_error,
            )
        )

    return UploadResponse(results=results)


@router.get("", response_model=list[DocumentSummary])
def list_documents(db: Session = Depends(get_db)) -> list[Document]:
    """List all ingested documents, most recently uploaded first."""
    return list(db.scalars(select(Document).order_by(Document.uploaded_at.desc())))
