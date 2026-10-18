"""Orchestrates one email message's full ingestion (Phase 8A: Email Thread
Intelligence): parse -> dedup check -> Document (body, indexed through the
EXISTING, unmodified chunk/embed/index pipeline) -> EmailMessage -> thread
resolution -> attachments (each, if PDF/DOCX, through the EXISTING,
unmodified app/ingestion/pipeline.py's ingest_document()).

Deliberately mirrors app/ingestion/pipeline.py's own structure and
error-handling conventions (processing lifecycle on Document: 'processing'
committed before extraction/indexing runs, then 'ready' or 'failed' —
never left stuck, never silently dropped) rather than inventing a new
pattern, and reuses that module's extraction/indexing/metadata helpers
directly wherever the two pipelines overlap (save_extracted_text,
extract_referenced_ids, index_document) instead of a second
implementation of any of them.
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Document, EmailAttachment, EmailMessage
from app.email_ingestion.dedup import (
    compute_content_hash,
    find_existing_by_content_hash,
    find_existing_by_message_id,
)
from app.email_ingestion.parsing import EmailParseError, ParsedAttachment, ParsedEmail, parse_eml
from app.email_ingestion.threading import resolve_thread
from app.ingestion.image_validation import sniff_image_signature, validate_image
from app.ingestion.indexing import index_document
from app.ingestion.metadata import extract_referenced_ids
from app.ingestion.pipeline import IngestionError, ingest_document
from app.ingestion.storage import new_storage_key, save_eml, save_extracted_text, save_image

logger = logging.getLogger(__name__)

# Mirrors app/ingestion/pipeline.py's MAX_UPLOAD_BYTES — applied to the raw
# .eml itself (headers + body + attachments all together, before anything
# is parsed), so a single oversized message is rejected up front rather
# than partially processed.
MAX_EML_BYTES = 25 * 1024 * 1024

_SUPPORTED_ATTACHMENT_EXTENSIONS = (".pdf", ".docx")


class EmailIngestionError(Exception):
    """Raised only for pre-flight validation failures on the raw .eml
    itself (empty, oversized, unparseable) — mirrors
    app/ingestion/pipeline.py's IngestionError exactly: no row of any kind
    is created for these, so a caller processing a batch can report this
    file as rejected and continue with the rest."""


@dataclass(frozen=True)
class EmailImportOutcome:
    status: str  # 'imported' | 'duplicate' | 'rejected'
    source_name: str
    document_id: int | None = None
    thread_id: int | None = None
    subject: str | None = None
    message_id: str | None = None
    error: str | None = None


def ingest_email_bytes(
    *,
    session: Session,
    storage_root: Path,
    project_id: int,
    source_name: str,
    raw_bytes: bytes,
) -> EmailImportOutcome:
    """Ingest one raw .eml file. Never raises for anything past pre-flight
    validation — a parse failure, a dedup hit, or a body-indexing failure
    all come back as a normal EmailImportOutcome, exactly like
    ingest_document() always returns a Document rather than raising for a
    processing (as opposed to validation) failure."""
    if not raw_bytes:
        return EmailImportOutcome(status="rejected", source_name=source_name, error=f"{source_name}: empty upload")
    if len(raw_bytes) > MAX_EML_BYTES:
        return EmailImportOutcome(
            status="rejected",
            source_name=source_name,
            error=f"{source_name}: exceeds the {MAX_EML_BYTES // (1024 * 1024)} MB message size limit",
        )

    try:
        parsed = parse_eml(raw_bytes)
    except EmailParseError as exc:
        return EmailImportOutcome(status="rejected", source_name=source_name, error=f"{source_name}: {exc}")

    content_hash = compute_content_hash(parsed)

    existing = None
    if parsed.message_id:
        existing = find_existing_by_message_id(session, project_id, parsed.message_id)
    if existing is None:
        existing = find_existing_by_content_hash(session, project_id, content_hash)
    if existing is not None:
        # Import retry / overlapping files: never create a second
        # EmailMessage (or re-process its attachments) for a message
        # already known to this project, and never overwrite the existing
        # one's content — the outcome is reported distinctly so the caller
        # can show "already imported" rather than implying nothing
        # happened at all.
        return EmailImportOutcome(
            status="duplicate",
            source_name=source_name,
            document_id=existing.document_id,
            thread_id=existing.thread_id,
            subject=existing.subject,
            message_id=existing.message_id,
        )

    document, eml_path = _ingest_email_body(
        session=session,
        storage_root=storage_root,
        project_id=project_id,
        parsed=parsed,
        raw_bytes=raw_bytes,
        source_name=source_name,
    )

    thread = resolve_thread(session, project_id, parsed)

    message = EmailMessage(
        document_id=document.id,
        project_id=project_id,
        thread_id=thread.id,
        import_source="eml_import",
        message_id=parsed.message_id,
        in_reply_to=" ".join(parsed.in_reply_to) or None,
        references=" ".join(parsed.references) or None,
        sender_name=parsed.sender_name,
        sender_email=parsed.sender_email,
        to_recipients=parsed.to_recipients or None,
        cc_recipients=parsed.cc_recipients or None,
        subject=parsed.subject,
        sent_at=parsed.sent_at,
        sent_at_timezone_unknown=parsed.sent_at_timezone_unknown,
        html_body=parsed.html_body,
        content_hash=content_hash,
        raw_eml_path=str(eml_path),
    )
    session.add(message)
    try:
        session.commit()
    except IntegrityError:
        # Pre-commit review fix: a concurrent request imported the exact
        # same message (same Message-ID, or same content_hash when no
        # Message-ID is present — both now backed by a database-level
        # unique constraint, see EmailMessage.__table_args__) between this
        # request's dedup pre-check and this commit. Without this recovery,
        # the Document body already created above (real, 'ready', chunked,
        # embedded) would be left as a silent, orphaned duplicate — a real,
        # searchable, citable "EMAIL" document with no EmailMessage pointing
        # to it. Roll back, discard that orphan (cascades its chunks), and
        # report this import as a duplicate of whichever request actually
        # won the race, exactly like the non-racing duplicate path already
        # does — never a 500, never a silently duplicated evidence record.
        session.rollback()
        # Capture the paths into plain locals BEFORE delete+commit: once the
        # row is deleted and this commits, `document`'s attributes can no
        # longer be read (SQLAlchemy raises ObjectDeletedError on access to
        # a deleted, expired instance) -- there would be nothing left to
        # read raw_text_path off of to know what to clean up.
        raw_text_path = document.raw_text_path
        session.delete(document)
        session.commit()
        _delete_orphaned_document_files(eml_path, raw_text_path)

        winner = None
        if parsed.message_id:
            winner = find_existing_by_message_id(session, project_id, parsed.message_id)
        if winner is None:
            winner = find_existing_by_content_hash(session, project_id, content_hash)
        if winner is None:
            # Exceptionally unlikely (the constraint that just fired implies
            # a matching row exists) — but never fabricate a result if it
            # can't be found.
            return EmailImportOutcome(
                status="rejected",
                source_name=source_name,
                error=f"{source_name}: a concurrent import conflicted with this one and the resulting record could not be resolved; please retry",
            )
        return EmailImportOutcome(
            status="duplicate",
            source_name=source_name,
            document_id=winner.document_id,
            thread_id=winner.thread_id,
            subject=winner.subject,
            message_id=winner.message_id,
        )
    session.refresh(message)

    for attachment in parsed.attachments:
        _ingest_attachment(
            session=session,
            storage_root=storage_root,
            project_id=project_id,
            message_id=message.document_id,
            attachment=attachment,
        )
    session.commit()

    return EmailImportOutcome(
        status="imported",
        source_name=source_name,
        document_id=document.id,
        thread_id=thread.id,
        subject=parsed.subject,
        message_id=parsed.message_id,
    )


def _delete_orphaned_document_files(eml_path: Path, raw_text_path: str | None) -> None:
    """Best-effort removal of the on-disk files belonging to a Document
    that was just deleted from the database -- the duplicate-import race
    recovery path in ingest_email_bytes() above, the only caller. Never
    raises: a filesystem issue here must never turn an already-successful
    duplicate-recovery outcome into a failure (see the IntegrityError
    handler's own comment).

    `eml_path`/`raw_text_path` are always the exact paths this same call
    just wrote moments earlier for the document being discarded -- passed
    in directly, never re-derived or looked up by a shared key -- so this
    can never touch the retained, canonical document's own files (the
    request that actually won the race) or any other document's or
    project's files: new_storage_key() (app/ingestion/storage.py) gives
    every call its own fresh, UUID-prefixed storage key, so two documents
    never share a filename to begin with. `raw_text_path` is None if
    indexing failed before the extracted-text file was ever written --
    there is then nothing to delete for it, not an error."""
    for path in (eml_path, Path(raw_text_path) if raw_text_path else None):
        if path is None:
            continue
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            logger.warning("Could not remove orphaned file %s for a discarded duplicate import: %s", path, exc)


def _derive_document_filename(parsed: ParsedEmail, source_name: str) -> str:
    """A display filename for the synthetic Document representing this
    message's body — the real Subject when available (what a reviewer
    would actually recognize it by), falling back to the uploaded file's
    own name. Never fabricated beyond these two real sources."""
    base = parsed.subject.strip() if parsed.subject and parsed.subject.strip() else Path(source_name).stem
    return f"{base}.eml"


def _ingest_email_body(
    *,
    session: Session,
    storage_root: Path,
    project_id: int,
    parsed: ParsedEmail,
    raw_bytes: bytes,
    source_name: str,
) -> tuple[Document, Path]:
    """Store the raw .eml and index the message's plain-text body through
    the EXISTING, completely unmodified chunk/embed/index pipeline
    (app/ingestion/indexing.py) — the same function every PDF/DOCX document
    already goes through. This is what makes an email-body citation an
    ordinary Citation with zero schema change (see app/db/models.py's
    EmailMessage docstring)."""
    t_start = time.monotonic()
    storage_key = new_storage_key(_derive_document_filename(parsed, source_name))
    eml_path = save_eml(storage_root, project_id, storage_key, raw_bytes)

    document = Document(
        project_id=project_id,
        filename=_derive_document_filename(parsed, source_name),
        doc_type="EMAIL",
        status="processing",
    )
    session.add(document)
    session.commit()
    session.refresh(document)

    try:
        full_text = parsed.plain_body or ""
        text_path = save_extracted_text(storage_root, project_id, storage_key, full_text)

        document.raw_text_path = str(text_path)
        document.doc_date = parsed.sent_at.date() if parsed.sent_at else None
        # Reused as-is (Sprint 4 Task 04's ID-code pattern): a message body
        # genuinely can reference other project documents ("See CTR-NRB4-0084"),
        # and this is the same deterministic extraction every PDF/DOCX
        # document already gets, not a new heuristic for email.
        document.referenced_ids = extract_referenced_ids(full_text)

        index_document(session, document)

        document.status = "ready"
        document.processing_error = None
        session.commit()
        session.refresh(document)
        logger.info(
            "Ingested email body %s (document_id=%s, project_id=%s) in %.2fs",
            source_name,
            document.id,
            project_id,
            time.monotonic() - t_start,
        )
    except Exception as exc:  # noqa: BLE001 -- any failure here must end in 'failed', never propagate and lose the row
        session.rollback()
        session.refresh(document)
        document.status = "failed"
        document.processing_error = str(exc)
        session.add(document)
        session.commit()
        session.refresh(document)
        logger.warning("Email body indexing failed for %s (document_id=%s): %s", source_name, document.id, exc)

    return document, eml_path


def _ingest_attachment(
    *,
    session: Session,
    storage_root: Path,
    project_id: int,
    message_id: int,
    attachment: ParsedAttachment,
) -> EmailAttachment:
    """Process one attachment. A supported type (PDF/DOCX) goes through the
    EXISTING, unmodified ingest_document() — it becomes a real, indexed
    Document, citable and viewable exactly like any standalone upload.

    Phase W2.0 (Shared Image Preservation Foundation): a recognized image
    (JPEG/PNG/GIF/WEBP, detected by real content signature — see
    app/ingestion/image_validation.py — never by this attachment's
    filename extension or its own untrusted MIME Content-Type header) is
    preserved as bytes via _ingest_image_attachment below, mirroring
    app/whatsapp_ingestion/pipeline.py's 'stored_pending_processing'
    contract: the original is now genuinely available to open/download,
    but this phase makes no claim it has been OCR'd/described/indexed.

    Any other unsupported type (including a non-image attachment, or one
    whose declared filename extension isn't PDF/DOCX/a recognized image)
    is recorded (filename/content_type/size/hash) and explicitly marked as
    such; its bytes are not persisted, exactly as before this phase — no
    second, parallel storage/extraction system is built for formats this
    phase doesn't otherwise support (see module docstring)."""
    content_hash = hashlib.sha256(attachment.content).hexdigest()
    size_bytes = len(attachment.content)
    extension = Path(attachment.filename).suffix.lower()

    # Checked by real content signature BEFORE the claimed extension, even
    # when that extension looks like a "supported" .pdf/.docx -- per this
    # phase's own explicit requirement to detect by content, never by a
    # filename or MIME type an attacker (or a simple naming mistake)
    # fully controls. A genuine PDF/DOCX never collides with a JPEG/PNG/
    # GIF/WEBP signature, so this never misroutes real PDF/DOCX content.
    if sniff_image_signature(attachment.content) is not None:
        return _ingest_image_attachment(
            session=session,
            storage_root=storage_root,
            project_id=project_id,
            message_id=message_id,
            attachment=attachment,
            content_hash=content_hash,
            size_bytes=size_bytes,
        )

    if extension not in _SUPPORTED_ATTACHMENT_EXTENSIONS:
        row = EmailAttachment(
            message_id=message_id,
            document_id=None,
            filename=attachment.filename,
            content_type=attachment.content_type,
            size_bytes=size_bytes,
            content_hash=content_hash,
            status="unsupported_format",
            processing_error=None,
        )
        session.add(row)
        session.flush()
        return row

    try:
        document = ingest_document(
            session=session,
            storage_root=storage_root,
            project_id=project_id,
            filename=attachment.filename,
            content=attachment.content,
        )
    except IngestionError as exc:
        row = EmailAttachment(
            message_id=message_id,
            document_id=None,
            filename=attachment.filename,
            content_type=attachment.content_type,
            size_bytes=size_bytes,
            content_hash=content_hash,
            status="rejected",
            processing_error=str(exc),
        )
        session.add(row)
        session.flush()
        return row

    row = EmailAttachment(
        message_id=message_id,
        document_id=document.id,
        filename=attachment.filename,
        content_type=attachment.content_type,
        size_bytes=size_bytes,
        content_hash=content_hash,
        status="processed" if document.status == "ready" else "failed",
        processing_error=document.processing_error,
    )
    session.add(row)
    session.flush()
    return row


def _ingest_image_attachment(
    *,
    session: Session,
    storage_root: Path,
    project_id: int,
    message_id: int,
    attachment: ParsedAttachment,
    content_hash: str,
    size_bytes: int,
) -> EmailAttachment:
    """Phase W2.0 (Shared Image Preservation Foundation): preserve one
    recognized-image attachment's original bytes, or record a clear
    rejection reason if it only looked like an image by signature but
    failed real validation (corrupt, oversized, or excessive dimensions)
    — never silently treated as a plain 'unsupported_format' in that
    case, since the real reason is more specific and more useful than
    that.

    Mirrors app/whatsapp_ingestion/pipeline.py's own raw-media branch of
    _ingest_media_attachment: the attachment row's own commit is wrapped
    in try/except so a failure after the file is already written deletes
    that now-orphaned file (exclusively owned by this row, under its own
    freshly-generated storage_key — never a previously committed or
    shared asset) rather than leaving it untracked on disk."""
    result = validate_image(attachment.content)
    if not result.valid:
        row = EmailAttachment(
            message_id=message_id,
            document_id=None,
            filename=attachment.filename,
            content_type=attachment.content_type,
            size_bytes=size_bytes,
            content_hash=content_hash,
            status="rejected",
            processing_error=result.error,
        )
        session.add(row)
        session.flush()
        return row

    storage_key = new_storage_key(attachment.filename)
    file_path = save_image(storage_root, project_id, storage_key, attachment.content, result.extension)
    row = EmailAttachment(
        message_id=message_id,
        document_id=None,
        filename=attachment.filename,
        content_type=result.content_type,
        size_bytes=size_bytes,
        content_hash=content_hash,
        status="stored_pending_processing",
        processing_error=None,
        storage_key=storage_key,
        detected_extension=result.extension,
        width_px=result.width,
        height_px=result.height,
    )
    session.add(row)
    try:
        session.commit()
    except Exception as exc:  # noqa: BLE001 -- compensating cleanup for the file just written above
        session.rollback()
        file_path.unlink(missing_ok=True)
        logger.warning(
            "Email image attachment commit failed after writing %s; removed the now-orphaned file: %s",
            file_path,
            exc,
        )
        return EmailAttachment(
            message_id=message_id,
            document_id=None,
            filename=attachment.filename,
            content_type=result.content_type,
            size_bytes=size_bytes,
            content_hash=content_hash,
            status="failed",
            processing_error=str(exc),
        )
    return row
