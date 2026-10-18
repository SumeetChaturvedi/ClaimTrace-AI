"""Project-scoped WhatsApp chat export import and inspection (Phase W1:
WhatsApp Export Ingestion).

Mirrors app/api/routes/project_emails.py's conventions exactly:
project-scoping enforced on every read, a uniform 404 for "doesn't exist"
and "belongs to a different project" alike (never a 403 — confirming a
chat/message/attachment id exists under some *other* project would itself
be a cross-project information leak), and an import response that never
silently implies more success than actually happened.

Import itself delegates entirely to app/whatsapp_ingestion/pipeline.py —
this module is a thin HTTP translation layer, exactly as project_emails.py
is a thin layer over app/email_ingestion/pipeline.py."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.models import Document, Project, WhatsAppChat, WhatsAppMediaAttachment, WhatsAppMessage
from app.db.session import get_db
from app.ingestion.storage import whatsapp_media_dir
from app.whatsapp_ingestion.pipeline import WhatsAppIngestionError, ingest_whatsapp_export

router = APIRouter(prefix="/projects/{project_id}/whatsapp", tags=["whatsapp"])


def _get_project_or_404(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


# -- Response models --------------------------------------------------------


class WhatsAppImportResponse(BaseModel):
    chat_id: int
    chat_title: str | None
    imported: int
    duplicate: int
    attachments_processed: int
    attachments_pending: int
    attachments_unsupported: int
    attachments_rejected: int
    attachments_failed: int
    # Pre-commit review fix: counted separately from attachments_rejected
    # -- an archive containing more than one file sharing the basename a
    # message referenced, where ClaimTrace correctly refused to guess
    # which one was actually attached (see app/whatsapp_ingestion/
    # pipeline.py's _resolve_media_candidate).
    attachments_ambiguous: int
    parse_warnings: list[str]


class WhatsAppChatSummary(BaseModel):
    id: int
    title: str | None
    source_export_filename: str
    message_count: int
    first_sent_at: datetime | None
    last_sent_at: datetime | None
    imported_at: datetime


class WhatsAppMessageSummary(BaseModel):
    document_id: int
    sequence_index: int
    sender_name: str | None
    raw_timestamp_text: str
    sent_at: datetime | None
    sent_at_ambiguous: bool
    message_type: str
    status: str
    attachment_count: int


class WhatsAppChatDetail(BaseModel):
    id: int
    title: str | None
    messages: list[WhatsAppMessageSummary]


class WhatsAppMediaAttachmentSummary(BaseModel):
    id: int
    filename: str
    content_type: str | None
    size_bytes: int
    # 'processed' (a real PDF/DOCX document was created) | 'stored_pending_
    # processing' (original bytes safely preserved; not yet interpreted --
    # W2-W4) | 'unsupported_format' | 'rejected' (missing/empty) | 'failed'
    status: str
    document_id: int | None
    processing_error: str | None


class WhatsAppMessageDetail(BaseModel):
    document_id: int
    chat_id: int
    sequence_index: int
    sender_name: str | None
    raw_timestamp_text: str
    sent_at: datetime | None
    sent_at_ambiguous: bool
    message_type: str
    status: str
    processing_error: str | None
    doc_date: date | None
    text: str | None
    attachments: list[WhatsAppMediaAttachmentSummary]


# -- Import -------------------------------------------------------------


@router.post("/import", response_model=WhatsAppImportResponse, status_code=status.HTTP_201_CREATED)
async def import_whatsapp_export(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> WhatsAppImportResponse:
    """Import one WhatsApp export (.txt transcript, or .zip containing a
    transcript plus media) into this project. imported/duplicate/
    attachment-status counts and parse_warnings (including ambiguous
    timestamps) are always the real, observed outcome — never collapsed
    into a single "success" that could mask a partial failure."""
    _get_project_or_404(db, project_id)
    content = await file.read()
    try:
        result = ingest_whatsapp_export(
            session=db,
            storage_root=settings.storage_root,
            project_id=project_id,
            source_filename=file.filename or "whatsapp_export",
            raw_bytes=content,
        )
    except WhatsAppIngestionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return WhatsAppImportResponse(
        chat_id=result.chat_id,
        chat_title=result.chat_title,
        imported=result.imported,
        duplicate=result.duplicate,
        attachments_processed=result.attachments_processed,
        attachments_pending=result.attachments_pending,
        attachments_unsupported=result.attachments_unsupported,
        attachments_rejected=result.attachments_rejected,
        attachments_failed=result.attachments_failed,
        attachments_ambiguous=result.attachments_ambiguous,
        parse_warnings=result.parse_warnings,
    )


# -- Chats / messages -----------------------------------------------------


@router.get("/chats", response_model=list[WhatsAppChatSummary])
def list_whatsapp_chats(project_id: int, db: Session = Depends(get_db)) -> list[WhatsAppChatSummary]:
    """List every imported WhatsApp chat for this project, most recently
    imported first. message_count/first_sent_at/last_sent_at are real
    aggregates over this chat's actual messages — never estimated."""
    _get_project_or_404(db, project_id)

    rows = db.execute(
        select(
            WhatsAppChat.id,
            WhatsAppChat.title,
            WhatsAppChat.source_export_filename,
            WhatsAppChat.imported_at,
            func.count(WhatsAppMessage.document_id),
            func.min(WhatsAppMessage.sent_at),
            func.max(WhatsAppMessage.sent_at),
        )
        .outerjoin(WhatsAppMessage, WhatsAppMessage.chat_id == WhatsAppChat.id)
        .where(WhatsAppChat.project_id == project_id)
        .group_by(WhatsAppChat.id, WhatsAppChat.title, WhatsAppChat.source_export_filename, WhatsAppChat.imported_at)
        .order_by(WhatsAppChat.imported_at.desc())
    ).all()

    return [
        WhatsAppChatSummary(
            id=chat_id,
            title=title,
            source_export_filename=source_export_filename,
            message_count=count,
            first_sent_at=first,
            last_sent_at=last,
            imported_at=imported_at,
        )
        for chat_id, title, source_export_filename, imported_at, count, first, last in rows
    ]


def _get_chat_or_404(db: Session, project_id: int, chat_id: int) -> WhatsAppChat:
    chat = db.get(WhatsAppChat, chat_id)
    if chat is None or chat.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WhatsApp chat not found")
    return chat


@router.get("/chats/{chat_id}", response_model=WhatsAppChatDetail)
def get_whatsapp_chat(project_id: int, chat_id: int, db: Session = Depends(get_db)) -> WhatsAppChatDetail:
    _get_project_or_404(db, project_id)
    chat = _get_chat_or_404(db, project_id, chat_id)

    rows = db.execute(
        select(WhatsAppMessage, Document.status, func.count(WhatsAppMediaAttachment.id))
        .join(Document, Document.id == WhatsAppMessage.document_id)
        .outerjoin(WhatsAppMediaAttachment, WhatsAppMediaAttachment.message_id == WhatsAppMessage.document_id)
        .where(WhatsAppMessage.chat_id == chat_id)
        .group_by(WhatsAppMessage.document_id, Document.status)
        .order_by(WhatsAppMessage.sequence_index.asc())
    ).all()

    messages = [
        WhatsAppMessageSummary(
            document_id=message.document_id,
            sequence_index=message.sequence_index,
            sender_name=message.sender_name,
            raw_timestamp_text=message.raw_timestamp_text,
            sent_at=message.sent_at,
            sent_at_ambiguous=message.sent_at_ambiguous,
            message_type=message.message_type,
            status=doc_status,
            attachment_count=attachment_count,
        )
        for message, doc_status, attachment_count in rows
    ]
    return WhatsAppChatDetail(id=chat.id, title=chat.title, messages=messages)


@router.get("/messages/{message_id}", response_model=WhatsAppMessageDetail)
def get_whatsapp_message(
    project_id: int,
    message_id: int,
    db: Session = Depends(get_db),
) -> WhatsAppMessageDetail:
    """Full detail for one WhatsApp message, keyed by its own Document id
    — the same id a Citation.document_id already points at, so tracing a
    citation back to its message needs no second lookup table. 404s
    uniformly for "not a WhatsApp message", "doesn't exist", and "belongs
    to a different project"."""
    _get_project_or_404(db, project_id)

    message = db.get(WhatsAppMessage, message_id)
    if message is None or message.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WhatsApp message not found")

    document = db.get(Document, message_id)
    assert document is not None  # WhatsAppMessage.document_id is a non-nullable FK to this exact row

    attachments = list(
        db.scalars(
            select(WhatsAppMediaAttachment)
            .where(WhatsAppMediaAttachment.message_id == message_id)
            .order_by(WhatsAppMediaAttachment.id)
        )
    )

    text: str | None = None
    if document.raw_text_path:
        try:
            text = Path(document.raw_text_path).read_text(encoding="utf-8")
        except OSError:
            text = None

    return WhatsAppMessageDetail(
        document_id=document.id,
        chat_id=message.chat_id,
        sequence_index=message.sequence_index,
        sender_name=message.sender_name,
        raw_timestamp_text=message.raw_timestamp_text,
        sent_at=message.sent_at,
        sent_at_ambiguous=message.sent_at_ambiguous,
        message_type=message.message_type,
        status=document.status,
        processing_error=document.processing_error,
        doc_date=document.doc_date,
        text=text,
        attachments=[
            WhatsAppMediaAttachmentSummary(
                id=a.id,
                filename=a.filename,
                content_type=a.content_type,
                size_bytes=a.size_bytes,
                status=a.status,
                document_id=a.document_id,
                processing_error=a.processing_error,
            )
            for a in attachments
        ],
    )


# -- Preserved-media file serving ------------------------------------------
#
# A PDF/DOCX attachment (document_id set) is already served by the
# existing, unmodified GET /projects/{project_id}/documents/{document_id}/file
# endpoint (app/api/routes/document_file.py) -- reused as-is, never
# duplicated. This endpoint exists ONLY for the media that endpoint
# structurally cannot serve: an attachment preserved as bytes with no
# Document row at all (status='stored_pending_processing'), located by
# its own storage_key/detected_extension rather than anything derived
# from a Document.


@router.get("/attachments/{attachment_id}/file")
def get_whatsapp_attachment_file(
    project_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    """Serve the preserved original bytes of one media attachment that
    has no indexed Document (status='stored_pending_processing' or
    'processed' with a non-indexable-but-storable type — see
    app/whatsapp_ingestion/pipeline.py). Project scope is verified via the
    owning message's own project_id — never trusted from the URL alone.
    Content-type is served from the attachment's own server-detected
    `content_type` (real file-signature sniffing at import time, see
    pipeline.py's _detect_media_type), never guessed from the filename at
    serve time. 404s uniformly for "doesn't exist", "belongs to a
    different project", and "no preserved original to serve" (e.g. a
    'rejected' attachment that was never stored)."""
    _get_project_or_404(db, project_id)

    attachment = db.get(WhatsAppMediaAttachment, attachment_id)
    if attachment is None or attachment.message.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WhatsApp attachment not found")
    if not attachment.storage_key or not attachment.detected_extension:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No preserved original file for this attachment")

    file_path = whatsapp_media_dir(settings.storage_root, project_id) / f"{attachment.storage_key}{attachment.detected_extension}"
    if not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preserved original file is missing")

    return FileResponse(
        path=file_path,
        media_type=attachment.content_type or "application/octet-stream",
        filename=attachment.filename,
    )
