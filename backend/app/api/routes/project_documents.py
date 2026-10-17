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

from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes.documents import DocumentSummary
from app.config import Settings, get_settings
from app.db.models import Document, EmailAttachment, EmailMessage, Project
from app.db.session import get_db
from app.ingestion.pipeline import IngestionError, ingest_document

router = APIRouter(prefix="/projects/{project_id}/documents", tags=["documents"])


class EmailSourceInfo(BaseModel):
    """Present only on a document that is a real, successfully-processed
    EMAIL ATTACHMENT (see EmailAttachment.document_id) — the covering
    email it came from. Lets the frontend show "From email: <subject>"
    on an attachment, reusing data that already exists (EmailAttachment's
    own message_id link) rather than inventing a new relationship."""

    message_document_id: int
    thread_id: int
    subject: str | None
    sender_name: str | None
    sender_email: str | None
    sent_at: datetime | None


class ProjectDocumentSummary(DocumentSummary):
    """DocumentSummary plus the project-scoped email_source enrichment —
    deliberately NOT added to the shared, project-agnostic DocumentSummary
    in app/api/routes/documents.py (that route has no project_id to scope
    the join by, and keeping this field project-scoped avoids the global
    /documents route needing to know about email attachments at all)."""

    email_source: EmailSourceInfo | None = None


def _email_sources_for(db: Session, project_id: int, document_ids: list[int]) -> dict[int, EmailSourceInfo]:
    """Look up which of `document_ids` are real email attachments (status
    'processed', per EmailAttachment's own docstring — the only case
    document_id is ever set) and return the covering email's identifying
    info for each, keyed by the ATTACHMENT's own document_id. A single
    join, scoped to this project via EmailMessage.project_id, never a
    second, unscoped lookup."""
    if not document_ids:
        return {}

    rows = db.execute(
        select(
            EmailAttachment.document_id,
            EmailMessage.document_id,
            EmailMessage.thread_id,
            EmailMessage.subject,
            EmailMessage.sender_name,
            EmailMessage.sender_email,
            EmailMessage.sent_at,
        )
        .join(EmailMessage, EmailMessage.document_id == EmailAttachment.message_id)
        .where(
            EmailAttachment.document_id.in_(document_ids),
            EmailMessage.project_id == project_id,
        )
    ).all()

    return {
        attachment_document_id: EmailSourceInfo(
            message_document_id=message_document_id,
            thread_id=thread_id,
            subject=subject,
            sender_name=sender_name,
            sender_email=sender_email,
            sent_at=sent_at,
        )
        for attachment_document_id, message_document_id, thread_id, subject, sender_name, sender_email, sent_at in rows
    }


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


@router.get("", response_model=list[ProjectDocumentSummary])
def list_project_documents(project_id: int, db: Session = Depends(get_db)) -> list[ProjectDocumentSummary]:
    """List every document belonging to `project_id`, most recently
    uploaded first — including ones still processing or failed, so the
    document register can show the real, current state of each. Each
    document that is itself an email attachment carries its covering
    email's identity in `email_source` (see EmailSourceInfo)."""
    _get_project_or_404(db, project_id)
    documents = list(
        db.scalars(
            select(Document).where(Document.project_id == project_id).order_by(Document.uploaded_at.desc())
        )
    )
    email_sources = _email_sources_for(db, project_id, [d.id for d in documents])
    return [
        ProjectDocumentSummary(**DocumentSummary.model_validate(d).model_dump(), email_source=email_sources.get(d.id))
        for d in documents
    ]


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


@router.get("/{document_id}", response_model=ProjectDocumentSummary)
def get_project_document(project_id: int, document_id: int, db: Session = Depends(get_db)) -> ProjectDocumentSummary:
    _get_project_or_404(db, project_id)
    document = db.scalar(select(Document).where(Document.id == document_id))
    if document is None or document.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    email_sources = _email_sources_for(db, project_id, [document_id])
    return ProjectDocumentSummary(
        **DocumentSummary.model_validate(document).model_dump(), email_source=email_sources.get(document_id)
    )
