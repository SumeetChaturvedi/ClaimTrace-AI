"""Project-scoped document register: list, upload, and fetch metadata for
one project's documents (Phase 3: Project + Document Foundation).

Reuses the existing, unmodified ingestion pipeline (app/ingestion/pipeline.py's
ingest_document — extraction via PyMuPDF, deterministic chunking, local
sentence-transformers embeddings, pgvector storage) exactly as the
pre-existing global /documents/upload route already does; this module adds
project-scoping and a real per-document response, not a second pipeline.

Complements, rather than duplicates, app/api/routes/document_file.py: that
module serves the raw PDF bytes at .../documents/{document_id}/file; this
one lists/uploads/describes documents at .../documents and
.../documents/{document_id}. Every read here enforces
document.project_id == project_id, returning the same plain 404 (never a
403) for "doesn't exist" and "belongs to a different project" alike, so a
request against the wrong project can't even confirm a document id exists
elsewhere — the same defense-in-depth pattern already used by
document_file.py and app/api/routes/investigations.py.
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes.documents import DocumentSummary
from app.config import Settings, get_settings
from app.db.models import Document, Project
from app.db.session import get_db
from app.ingestion.pipeline import IngestionError, ingest_document

router = APIRouter(prefix="/projects/{project_id}/documents", tags=["documents"])


def _get_project_or_404(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


class RejectedUpload(BaseModel):
    """A file that failed pre-flight validation (unsupported file type, empty,
    oversized) before any Document row was created — distinct from a file
    that was accepted but whose processing then failed, which shows up as
    a real DocumentSummary with status='failed' instead."""

    filename: str
    error: str


class UploadResponse(BaseModel):
    documents: list[DocumentSummary]
    rejected: list[RejectedUpload]


@router.get("", response_model=list[DocumentSummary])
def list_project_documents(project_id: int, db: Session = Depends(get_db)) -> list[Document]:
    """List every document belonging to `project_id`, most recently
    uploaded first — including ones still processing or failed, so the
    document register can show the real, current state of each."""
    _get_project_or_404(db, project_id)
    return list(
        db.scalars(
            select(Document).where(Document.project_id == project_id).order_by(Document.uploaded_at.desc())
        )
    )


@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_project_documents(
    project_id: int,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> UploadResponse:
    """Upload one or more PDF or DOCX files to this project. Each file is
    processed independently through the real, unmodified ingestion pipeline
    — a corrupted or invalid file in the batch doesn't block the rest. A file
    that fails pre-flight validation (unsupported file type, empty, oversized) is
    reported under `rejected` with no Document row created; anything past
    that point always gets a persisted Document, with `status` reflecting
    the real outcome ('ready' or 'failed') — never silently dropped."""
    _get_project_or_404(db, project_id)

    documents: list[DocumentSummary] = []
    rejected: list[RejectedUpload] = []

    for upload in files:
        name = upload.filename or "unnamed.pdf"
        content = await upload.read()
        try:
            document = ingest_document(
                session=db,
                storage_root=settings.storage_root,
                project_id=project_id,
                filename=name,
                content=content,
            )
        except IngestionError as exc:
            rejected.append(RejectedUpload(filename=name, error=str(exc)))
            continue

        documents.append(DocumentSummary.model_validate(document))

    return UploadResponse(documents=documents, rejected=rejected)


@router.get("/{document_id}", response_model=DocumentSummary)
def get_project_document(project_id: int, document_id: int, db: Session = Depends(get_db)) -> Document:
    _get_project_or_404(db, project_id)
    document = db.scalar(select(Document).where(Document.id == document_id))
    if document is None or document.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document
