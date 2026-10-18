"""Project-scoped email import and inspection (Phase 8A: Email Thread
Intelligence).

Mirrors app/api/routes/project_documents.py's conventions exactly:
project-scoping enforced on every read, a uniform 404 for "doesn't exist"
and "belongs to a different project" alike (never a 403 — confirming a
thread/message/attachment id exists under some *other* project would
itself be a cross-project information leak), and a per-file import report
that never silently drops a failure.

Import itself delegates entirely to app/email_ingestion/pipeline.py and
app/email_ingestion/zip_import.py — this module is a thin HTTP translation
layer over that real logic, exactly as project_documents.py is a thin
layer over app/ingestion/pipeline.py's ingest_document()."""

from datetime import date, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.models import Document, EmailAttachment, EmailMessage, EmailThread, Project
from app.db.session import get_db
from app.email_ingestion.pipeline import EmailImportOutcome, ingest_email_bytes
from app.email_ingestion.zip_import import ZipImportError, extract_eml_entries
from app.ingestion.storage import image_storage_dir

router = APIRouter(prefix="/projects/{project_id}/emails", tags=["emails"])


def _get_project_or_404(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


# -- Response models --------------------------------------------------------


class EmailImportResult(BaseModel):
    source_name: str
    status: str  # 'imported' | 'duplicate' | 'rejected'
    document_id: int | None = None
    thread_id: int | None = None
    subject: str | None = None
    message_id: str | None = None
    error: str | None = None


class EmailImportResponse(BaseModel):
    results: list[EmailImportResult]


class EmailThreadSummary(BaseModel):
    id: int
    subject: str | None
    message_count: int
    first_sent_at: datetime | None
    last_sent_at: datetime | None


class EmailMessageSummary(BaseModel):
    document_id: int
    message_id: str | None
    subject: str | None
    sender_name: str | None
    sender_email: str | None
    sent_at: datetime | None
    sent_at_timezone_unknown: bool
    status: str
    attachment_count: int


class EmailThreadDetail(BaseModel):
    id: int
    subject: str | None
    messages: list[EmailMessageSummary]


class EmailAttachmentSummary(BaseModel):
    id: int
    filename: str
    content_type: str | None
    size_bytes: int
    status: str
    document_id: int | None
    processing_error: str | None


class EmailMessageDetail(BaseModel):
    document_id: int
    thread_id: int
    message_id: str | None
    in_reply_to: str | None
    references: str | None
    sender_name: str | None
    sender_email: str | None
    to_recipients: list[str]
    cc_recipients: list[str]
    subject: str | None
    sent_at: datetime | None
    sent_at_timezone_unknown: bool
    status: str
    processing_error: str | None
    doc_date: date | None
    plain_body: str | None
    has_html_body: bool
    attachments: list[EmailAttachmentSummary]


# -- Import -------------------------------------------------------------


@router.post("/import", response_model=EmailImportResponse, status_code=status.HTTP_201_CREATED)
async def import_project_emails(
    project_id: int,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> EmailImportResponse:
    """Import one or more .eml files, or ZIP archives of .eml files, into
    this project. Each top-level upload and each ZIP member is reported
    independently: 'imported' (a new message was persisted and indexed),
    'duplicate' (a message with the same Message-ID or content was already
    imported for this project — never re-created, never overwritten), or
    'rejected' (couldn't be processed — malformed, empty, oversized, or an
    unsafe ZIP entry)."""
    _get_project_or_404(db, project_id)

    results: list[EmailImportResult] = []

    for upload in files:
        name = upload.filename or "unnamed"
        content = await upload.read()
        extension = Path(name).suffix.lower()

        if extension == ".zip":
            try:
                extraction = extract_eml_entries(content)
            except ZipImportError as exc:
                results.append(EmailImportResult(source_name=name, status="rejected", error=str(exc)))
                continue

            for rejected_entry in extraction.rejected:
                results.append(
                    EmailImportResult(
                        source_name=f"{name}:{rejected_entry.name}",
                        status="rejected",
                        error=rejected_entry.error,
                    )
                )
            for entry in extraction.entries:
                outcome = ingest_email_bytes(
                    session=db,
                    storage_root=settings.storage_root,
                    project_id=project_id,
                    source_name=f"{name}:{entry.name}",
                    raw_bytes=entry.content,
                )
                results.append(_to_import_result(outcome))

        elif extension == ".eml":
            outcome = ingest_email_bytes(
                session=db,
                storage_root=settings.storage_root,
                project_id=project_id,
                source_name=name,
                raw_bytes=content,
            )
            results.append(_to_import_result(outcome))

        else:
            results.append(
                EmailImportResult(
                    source_name=name,
                    status="rejected",
                    error=f"{name}: not a supported file type (.eml or .zip of .eml files only)",
                )
            )

    return EmailImportResponse(results=results)


def _to_import_result(outcome: EmailImportOutcome) -> EmailImportResult:
    return EmailImportResult(
        source_name=outcome.source_name,
        status=outcome.status,
        document_id=outcome.document_id,
        thread_id=outcome.thread_id,
        subject=outcome.subject,
        message_id=outcome.message_id,
        error=outcome.error,
    )


# -- Threads / messages ---------------------------------------------------


@router.get("/threads", response_model=list[EmailThreadSummary])
def list_email_threads(project_id: int, db: Session = Depends(get_db)) -> list[EmailThreadSummary]:
    """List every email thread for this project, most recently active
    first. message_count/first_sent_at/last_sent_at are real aggregates
    over this thread's actual messages — never estimated."""
    _get_project_or_404(db, project_id)

    rows = db.execute(
        select(
            EmailThread.id,
            EmailThread.subject,
            func.count(EmailMessage.document_id),
            func.min(EmailMessage.sent_at),
            func.max(EmailMessage.sent_at),
        )
        .join(EmailMessage, EmailMessage.thread_id == EmailThread.id)
        .where(EmailThread.project_id == project_id)
        .group_by(EmailThread.id, EmailThread.subject)
        .order_by(func.max(EmailMessage.sent_at).desc().nulls_last())
    ).all()

    return [
        EmailThreadSummary(id=thread_id, subject=subject, message_count=count, first_sent_at=first, last_sent_at=last)
        for thread_id, subject, count, first, last in rows
    ]


def _get_thread_or_404(db: Session, project_id: int, thread_id: int) -> EmailThread:
    thread = db.get(EmailThread, thread_id)
    if thread is None or thread.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email thread not found")
    return thread


@router.get("/threads/{thread_id}", response_model=EmailThreadDetail)
def get_email_thread(project_id: int, thread_id: int, db: Session = Depends(get_db)) -> EmailThreadDetail:
    _get_project_or_404(db, project_id)
    thread = _get_thread_or_404(db, project_id, thread_id)

    rows = db.execute(
        select(EmailMessage, Document.status, func.count(EmailAttachment.id))
        .join(Document, Document.id == EmailMessage.document_id)
        .outerjoin(EmailAttachment, EmailAttachment.message_id == EmailMessage.document_id)
        .where(EmailMessage.thread_id == thread_id)
        .group_by(EmailMessage.document_id, Document.status)
        .order_by(EmailMessage.sent_at.asc().nulls_last())
    ).all()

    messages = [
        EmailMessageSummary(
            document_id=message.document_id,
            message_id=message.message_id,
            subject=message.subject,
            sender_name=message.sender_name,
            sender_email=message.sender_email,
            sent_at=message.sent_at,
            sent_at_timezone_unknown=message.sent_at_timezone_unknown,
            status=doc_status,
            attachment_count=attachment_count,
        )
        for message, doc_status, attachment_count in rows
    ]
    return EmailThreadDetail(id=thread.id, subject=thread.subject, messages=messages)


@router.get("/messages/{document_id}", response_model=EmailMessageDetail)
def get_email_message(
    project_id: int,
    document_id: int,
    db: Session = Depends(get_db),
) -> EmailMessageDetail:
    """Full detail for one email message, keyed by its own Document id —
    the same id a Citation.document_id already points at, so tracing a
    citation back to its message needs no second lookup table. 404s
    uniformly for "not an email message", "doesn't exist", and "belongs to
    a different project", matching every other project-scoped lookup in
    this app."""
    _get_project_or_404(db, project_id)

    message = db.get(EmailMessage, document_id)
    if message is None or message.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email message not found")

    document = db.get(Document, document_id)
    assert document is not None  # EmailMessage.document_id is a non-nullable FK to this exact row

    attachments = list(
        db.scalars(
            select(EmailAttachment).where(EmailAttachment.message_id == document_id).order_by(EmailAttachment.id)
        )
    )

    plain_body: str | None = None
    if document.raw_text_path:
        try:
            plain_body = Path(document.raw_text_path).read_text(encoding="utf-8")
        except OSError:
            plain_body = None

    return EmailMessageDetail(
        document_id=document.id,
        thread_id=message.thread_id,
        message_id=message.message_id,
        in_reply_to=message.in_reply_to,
        references=message.references,
        sender_name=message.sender_name,
        sender_email=message.sender_email,
        to_recipients=message.to_recipients or [],
        cc_recipients=message.cc_recipients or [],
        subject=message.subject,
        sent_at=message.sent_at,
        sent_at_timezone_unknown=message.sent_at_timezone_unknown,
        status=document.status,
        processing_error=document.processing_error,
        doc_date=document.doc_date,
        plain_body=plain_body,
        has_html_body=bool(message.html_body),
        attachments=[
            EmailAttachmentSummary(
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


# -- Preserved-image file serving (Phase W2.0) -----------------------------
#
# A PDF/DOCX attachment (document_id set) is already served by the
# existing, unmodified GET /projects/{project_id}/documents/{document_id}/file
# endpoint (app/api/routes/document_file.py) -- reused as-is, never
# duplicated. This endpoint exists ONLY for an image attachment preserved
# as bytes with no Document row at all (status='stored_pending_processing'
# -- see app/email_ingestion/pipeline.py's _ingest_image_attachment),
# located by its own storage_key/detected_extension rather than anything
# derived from a Document. Mirrors
# app/api/routes/project_whatsapp.py's get_whatsapp_attachment_file
# exactly.


@router.get("/attachments/{attachment_id}/file")
def get_email_attachment_file(
    project_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    """Serve the preserved original bytes of one email image attachment
    that has no indexed Document (status='stored_pending_processing').
    Project scope is verified via the owning message's own project_id —
    never trusted from the URL alone. Content-type is served from the
    attachment's own server-detected `content_type` (real file-signature
    sniffing at import time, see app/ingestion/image_validation.py), never
    guessed from the filename at serve time. 404s uniformly for "doesn't
    exist", "belongs to a different project", and "no preserved original
    to serve" (e.g. a PDF/DOCX or 'unsupported_format'/'rejected'
    attachment that was never stored under this path)."""
    _get_project_or_404(db, project_id)

    attachment = db.get(EmailAttachment, attachment_id)
    if attachment is None or attachment.message.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email attachment not found")
    if not attachment.storage_key or not attachment.detected_extension:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No preserved original file for this attachment")

    file_path = image_storage_dir(settings.storage_root, project_id) / f"{attachment.storage_key}{attachment.detected_extension}"
    if not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preserved original file is missing")

    return FileResponse(
        path=file_path,
        media_type=attachment.content_type or "application/octet-stream",
        filename=attachment.filename,
    )
