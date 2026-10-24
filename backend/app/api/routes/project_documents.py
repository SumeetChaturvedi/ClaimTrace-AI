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
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes.documents import DocumentSummary
from app.config import Settings, get_settings
from app.db.models import (
    Document,
    EmailAttachment,
    EmailMessage,
    Project,
    ProjectImageAsset,
    WhatsAppMediaAttachment,
    WhatsAppMessage,
)
from app.api.routes.project_images import ProjectImageAssetSummary, ingest_project_image, to_project_image_summary
from app.db.session import get_db
from app.ingestion.image_validation import sniff_image_signature
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


class WhatsAppSourceInfo(BaseModel):
    """Present only on a document that is a real, successfully-processed
    WHATSAPP MEDIA ATTACHMENT (see WhatsAppMediaAttachment.document_id) —
    the covering message it came from. Mirrors EmailSourceInfo exactly,
    following the same existing email-attachment provenance pattern
    (Phase W1: WhatsApp Export Ingestion)."""

    message_document_id: int
    chat_id: int
    sender_name: str | None
    sent_at: datetime | None
    sent_at_ambiguous: bool


class ImageSourceInfo(BaseModel):
    """Present only on a document whose text was derived by locally
    running OCR against a preserved image (Phase W2.2: OCR Evidence
    Integration — see ImageOcrResult and app/ingestion/image_ocr_indexing.py),
    across all three places an image can come from. Lets the frontend
    identify this document's text as DERIVED from an image, never the
    original itself, and link to the real preserved bytes at the
    existing, unmodified file-serving route for that source kind:
      - 'project_image'      -> GET /projects/{project_id}/images/{image_id}/file
      - 'email_attachment'   -> GET /projects/{project_id}/emails/attachments/{image_id}/file
      - 'whatsapp_attachment'-> GET /projects/{project_id}/whatsapp/attachments/{image_id}/file
    No new file-serving code is added for this — these three routes
    already exist and already serve exactly these rows' original bytes."""

    source_kind: Literal["project_image", "email_attachment", "whatsapp_attachment"]
    image_id: int


class ProjectDocumentSummary(DocumentSummary):
    """DocumentSummary plus the project-scoped email_source/whatsapp_source/
    image_source enrichment — deliberately NOT added to the shared,
    project-agnostic DocumentSummary in app/api/routes/documents.py (that
    route has no project_id to scope the join by, and keeping these fields
    project-scoped avoids the global /documents route needing to know
    about email/WhatsApp/image attachments at all)."""

    email_source: EmailSourceInfo | None = None
    whatsapp_source: WhatsAppSourceInfo | None = None
    image_source: ImageSourceInfo | None = None


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


def _whatsapp_sources_for(db: Session, project_id: int, document_ids: list[int]) -> dict[int, WhatsAppSourceInfo]:
    """Mirrors _email_sources_for exactly, for WhatsApp media attachments
    -- a single join, scoped to this project via WhatsAppMessage.project_id,
    keyed by the ATTACHMENT's own document_id."""
    if not document_ids:
        return {}

    rows = db.execute(
        select(
            WhatsAppMediaAttachment.document_id,
            WhatsAppMessage.document_id,
            WhatsAppMessage.chat_id,
            WhatsAppMessage.sender_name,
            WhatsAppMessage.sent_at,
            WhatsAppMessage.sent_at_ambiguous,
        )
        .join(WhatsAppMessage, WhatsAppMessage.document_id == WhatsAppMediaAttachment.message_id)
        .where(
            WhatsAppMediaAttachment.document_id.in_(document_ids),
            WhatsAppMessage.project_id == project_id,
        )
    ).all()

    return {
        attachment_document_id: WhatsAppSourceInfo(
            message_document_id=message_document_id,
            chat_id=chat_id,
            sender_name=sender_name,
            sent_at=sent_at,
            sent_at_ambiguous=sent_at_ambiguous,
        )
        for attachment_document_id, message_document_id, chat_id, sender_name, sent_at, sent_at_ambiguous in rows
    }


def _image_sources_for(db: Session, project_id: int, document_ids: list[int]) -> dict[int, ImageSourceInfo]:
    """Look up which of `document_ids` were derived from an image, across
    all three image sources, keyed by the DOCUMENT's own id. Checks BOTH
    `document_id` (OCR, Phase W2.2) and `visual_document_id` (AI-generated
    visual description, Phase W2.3) on each parent table -- a document can
    only ever match one of these six (id, column) combinations, since a
    parent's own document_id/visual_document_id point at two DIFFERENT
    Document rows (see Document.derivation_kind's own docstring), so no
    ordering between the loops below matters. One query per (source kind,
    column) pair, each scoped to this project the same way
    _email_sources_for/_whatsapp_sources_for already are."""
    if not document_ids:
        return {}

    sources: dict[int, ImageSourceInfo] = {}

    for column in (ProjectImageAsset.document_id, ProjectImageAsset.visual_document_id):
        for document_id, image_id in db.execute(
            select(column, ProjectImageAsset.id).where(column.in_(document_ids), ProjectImageAsset.project_id == project_id)
        ).all():
            sources[document_id] = ImageSourceInfo(source_kind="project_image", image_id=image_id)

    for column in (EmailAttachment.document_id, EmailAttachment.visual_document_id):
        for document_id, image_id in db.execute(
            select(column, EmailAttachment.id)
            .join(EmailMessage, EmailMessage.document_id == EmailAttachment.message_id)
            .where(column.in_(document_ids), EmailMessage.project_id == project_id)
        ).all():
            sources[document_id] = ImageSourceInfo(source_kind="email_attachment", image_id=image_id)

    for column in (WhatsAppMediaAttachment.document_id, WhatsAppMediaAttachment.visual_document_id):
        for document_id, image_id in db.execute(
            select(column, WhatsAppMediaAttachment.id)
            .join(WhatsAppMessage, WhatsAppMessage.document_id == WhatsAppMediaAttachment.message_id)
            .where(column.in_(document_ids), WhatsAppMessage.project_id == project_id)
        ).all():
            sources[document_id] = ImageSourceInfo(source_kind="whatsapp_attachment", image_id=image_id)

    return sources


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
    # Phase W2.0 (Shared Image Preservation Foundation): a recognized
    # image in the same upload batch, preserved rather than run through
    # ingest_document() -- additive field, old clients that don't read it
    # are unaffected; existing PDF/DOCX behavior and the `documents`/
    # `rejected` fields are completely unchanged by its presence.
    images: list[ProjectImageAssetSummary] = []


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
    document_ids = [d.id for d in documents]
    email_sources = _email_sources_for(db, project_id, document_ids)
    whatsapp_sources = _whatsapp_sources_for(db, project_id, document_ids)
    image_sources = _image_sources_for(db, project_id, document_ids)
    return [
        ProjectDocumentSummary(
            **DocumentSummary.model_validate(d).model_dump(),
            email_source=email_sources.get(d.id),
            whatsapp_source=whatsapp_sources.get(d.id),
            image_source=image_sources.get(d.id),
        )
        for d in documents
    ]


@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_project_documents(
    project_id: int,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> UploadResponse:
    """Upload one or more PDF, DOCX, or image (JPEG/PNG/GIF/WEBP) files to
    this project. Each file is processed independently through the real,
    unmodified ingestion pipeline — a corrupted or invalid file in the batch
    doesn't block the rest. A file that fails pre-flight validation
    (unsupported file type, empty, oversized) is reported under `rejected`
    with no Document row created; anything past that point always gets a
    persisted Document, with `status` reflecting the real outcome ('ready'
    or 'failed') — never silently dropped.

    Phase W2.0 (Shared Image Preservation Foundation): a file is routed to
    image preservation (reported under `images`, never `documents` or
    `rejected`) ONLY when its own bytes sniff as a recognized image
    signature (see app/ingestion/image_validation.py) — never by filename
    extension or the upload's claimed content type. Everything else
    (including a real but corrupt/oversized image, which is still reported
    under `images` with status='rejected' and a specific reason) falls
    through to the existing ingest_document() path exactly as before."""
    _get_project_or_404(db, project_id)

    documents: list[DocumentSummary] = []
    rejected: list[RejectedUpload] = []
    images: list[ProjectImageAssetSummary] = []

    for upload in files:
        name = upload.filename or "unnamed.pdf"
        content = await upload.read()

        if sniff_image_signature(content) is not None:
            image_asset = ingest_project_image(
                session=db,
                storage_root=settings.storage_root,
                project_id=project_id,
                filename=name,
                content=content,
            )
            images.append(to_project_image_summary(image_asset))
            continue

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

    return UploadResponse(documents=documents, rejected=rejected, images=images)


@router.get("/{document_id}", response_model=ProjectDocumentSummary)
def get_project_document(project_id: int, document_id: int, db: Session = Depends(get_db)) -> ProjectDocumentSummary:
    _get_project_or_404(db, project_id)
    document = db.scalar(select(Document).where(Document.id == document_id))
    if document is None or document.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    email_sources = _email_sources_for(db, project_id, [document_id])
    whatsapp_sources = _whatsapp_sources_for(db, project_id, [document_id])
    image_sources = _image_sources_for(db, project_id, [document_id])
    return ProjectDocumentSummary(
        **DocumentSummary.model_validate(document).model_dump(),
        email_source=email_sources.get(document_id),
        whatsapp_source=whatsapp_sources.get(document_id),
        image_source=image_sources.get(document_id),
    )
