"""Orchestrates one WhatsApp chat export's full ingestion (Phase W1:
WhatsApp Export Ingestion): parse -> find/create chat -> per-message dedup
check -> Document (one per message, indexed through the EXISTING,
unmodified chunk/embed/index pipeline) -> WhatsAppMessage -> media
attachments (PDF/DOCX through the EXISTING, unmodified
app/ingestion/pipeline.py's ingest_document(); everything else preserved
as bytes, never discarded, never indexed as text it doesn't actually have).

Deliberately mirrors app/email_ingestion/pipeline.py's own structure and
error-handling conventions (processing lifecycle on Document: 'processing'
committed before extraction/indexing runs, then 'ready' or 'failed';
IntegrityError-on-concurrent-duplicate recovery) rather than inventing a
new pattern.

Chat identity (a real, disclosed limitation): a WhatsApp export carries no
analogue of a stable group/chat id. A re-upload is matched to an existing
WhatsAppChat by EXACT (project_id, source_export_filename) -- the one
honest, non-fabricated signal available. A real re-export of the "same"
chat under a DIFFERENT filename creates a separate WhatsAppChat rather
than being merged into the existing one; this is a deliberate, documented
scope boundary, not an oversight (merging by fuzzy title/content matching
would risk silently combining two actually-different conversations)."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Document, WhatsAppChat, WhatsAppMediaAttachment, WhatsAppMessage
from app.ingestion.indexing import index_document
from app.ingestion.metadata import extract_referenced_ids
from app.ingestion.pipeline import IngestionError, ingest_document
from app.ingestion.storage import new_storage_key, save_extracted_text, save_whatsapp_media
from app.ocr.pending import OCR_ELIGIBLE_EXTENSIONS, ensure_pending_ocr_result
from app.whatsapp_ingestion.dedup import compute_content_hash, find_existing_by_content_hash
from app.whatsapp_ingestion.parsing import ParsedWhatsAppMessage, WhatsAppParseError, parse_whatsapp_export
from app.whatsapp_ingestion.zip_import import WhatsAppZipImportError, extract_whatsapp_entries

logger = logging.getLogger(__name__)

# Mirrors app/email_ingestion/pipeline.py's MAX_EML_BYTES -- a single .txt
# transcript's own size cap, applied before anything is parsed.
MAX_EXPORT_BYTES = 25 * 1024 * 1024

_SUPPORTED_DOCUMENT_EXTENSIONS = (".pdf", ".docx")  # reuse ingest_document()'s own supported set, unmodified

# Minimal file-signature detection -- the authority for what gets stored/
# served as, NEVER the claimed filename extension (see this module's own
# _detect_media_type docstring).
_SIGNATURES: list[tuple[bytes, str, str]] = [
    (b"\xff\xd8\xff", ".jpg", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", ".png", "image/png"),
    (b"GIF87a", ".gif", "image/gif"),
    (b"GIF89a", ".gif", "image/gif"),
    (b"%PDF-", ".pdf", "application/pdf"),
    (b"OggS", ".ogg", "audio/ogg"),
    (b"ID3", ".mp3", "audio/mpeg"),
    (b"#!AMR", ".amr", "audio/amr"),
    (b"\x1a\x45\xdf\xa3", ".webm", "video/webm"),
]


class WhatsAppIngestionError(Exception):
    """Raised only for pre-flight validation failures on the raw export
    itself (empty, oversized, unreadable archive, no chat transcript
    found at all) -- mirrors app/email_ingestion/pipeline.py's
    EmailIngestionError exactly: no row of any kind is created for these."""


@dataclass(frozen=True)
class WhatsAppImportResult:
    chat_id: int
    chat_title: str | None
    imported: int = 0
    duplicate: int = 0
    attachments_processed: int = 0
    attachments_pending: int = 0
    attachments_unsupported: int = 0
    attachments_rejected: int = 0
    attachments_failed: int = 0
    # Pre-commit review fix: counted separately from attachments_rejected
    # -- "rejected" means no candidate file was found at all; "ambiguous"
    # means MULTIPLE files in the archive share the referenced basename
    # and none was selected, since guessing would risk attaching the
    # wrong evidence to this message (see _resolve_media_candidate below).
    attachments_ambiguous: int = 0
    parse_warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class _MediaResolution:
    """The result of resolving a message's bare media-filename reference
    against the archive's actual entries. `status` is one of:
    'missing' (no entry has this basename), 'unique' (exactly one does --
    `content` is its bytes), or 'ambiguous' (more than one entry shares
    this basename -- `candidate_count` records how many; `content` is
    always None, since picking any one of them would risk silently
    attaching the wrong evidence to this message -- see the pre-commit
    review fix this type exists for)."""

    status: str
    content: bytes | None = None
    candidate_count: int = 0


def _resolve_media_candidate(media_entries: dict[str, list[bytes]], basename: str) -> _MediaResolution:
    """Pre-commit review fix: a WhatsApp transcript placeholder only ever
    references a bare basename (WhatsApp's own export format has no
    concept of a directory path for an attachment reference) -- but the
    ARCHIVE can legitimately contain more than one entry sharing that
    basename, whether in different directories or even at the identical
    flat path (Python's own zipfile permits duplicate entry names; a
    careless or deliberately crafted re-packaging can easily produce
    this). `media_entries` therefore maps each basename to the FULL list
    of matching entries' content (built by _collect_media_entries below,
    never collapsed to "the last one seen") -- this function is the only
    place that list is ever narrowed down to a single candidate, and it
    refuses to guess: a basename matching more than one entry is reported
    as 'ambiguous', never resolved by archive order, first-match, or any
    other heuristic."""
    candidates = media_entries.get(basename)
    if not candidates:
        return _MediaResolution(status="missing")
    if len(candidates) > 1:
        return _MediaResolution(status="ambiguous", candidate_count=len(candidates))
    return _MediaResolution(status="unique", content=candidates[0])


def _derive_chat_title(source_filename: str) -> str:
    """A display title for the chat -- the uploaded export's own filename
    with its extension and WhatsApp's own common export-name boilerplate
    stripped, never fabricated from message content (a WhatsApp text
    export has no analogue of an email Subject header naming the
    conversation)."""
    stem = Path(source_filename).stem
    for prefix in ("WhatsApp Chat with ", "WhatsApp Chat - ", "_chat"):
        if stem.startswith(prefix):
            stem = stem[len(prefix) :]
            break
    return stem.strip() or source_filename


def _find_or_create_chat(session: Session, project_id: int, source_filename: str) -> WhatsAppChat:
    existing = session.scalar(
        select(WhatsAppChat).where(
            WhatsAppChat.project_id == project_id,
            WhatsAppChat.source_export_filename == source_filename,
        )
    )
    if existing is not None:
        return existing

    chat = WhatsAppChat(
        project_id=project_id,
        title=_derive_chat_title(source_filename),
        source_export_filename=source_filename,
    )
    session.add(chat)
    session.commit()
    session.refresh(chat)
    return chat


def _next_sequence_index(session: Session, chat_id: int) -> int:
    """The next whole-chat sequence position to assign to a genuinely new
    message -- continues the running count across imports (see module
    docstring's "Chat identity" note on why overlap is only handled
    correctly when a later export's new content is a chronological suffix
    of what's already stored)."""
    current_max = session.scalar(
        select(func.max(WhatsAppMessage.sequence_index)).where(WhatsAppMessage.chat_id == chat_id)
    )
    return 0 if current_max is None else current_max + 1


def _detect_media_type(content: bytes) -> tuple[str, str]:
    """Return (extension, content_type) from the ACTUAL bytes' own file
    signature -- never from a claimed filename, which is untrusted,
    attacker-controllable metadata. Falls back to a generic, SAFE
    'application/octet-stream'/'.bin' when no known signature matches --
    this is the deliberately conservative default: never serve unknown
    bytes under a guessed, possibly-misleading content type."""
    if content.startswith(b"PK\x03\x04"):
        # DOCX is itself a ZIP container -- confirmed, not guessed, by
        # checking for the one entry every real DOCX file has.
        import zipfile
        import io

        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                if "word/document.xml" in zf.namelist():
                    return ".docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        except zipfile.BadZipFile:
            pass
        return ".bin", "application/octet-stream"

    if content[4:8] == b"ftyp":
        return ".mp4", "video/mp4"
    if content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return ".webp", "image/webp"

    for signature, extension, content_type in _SIGNATURES:
        if content.startswith(signature):
            return extension, content_type

    return ".bin", "application/octet-stream"


def ingest_whatsapp_export(
    *,
    session: Session,
    storage_root: Path,
    project_id: int,
    source_filename: str,
    raw_bytes: bytes,
) -> WhatsAppImportResult:
    """Ingest one WhatsApp export (.txt transcript, or .zip containing a
    transcript plus media) into `project_id`. Raises WhatsAppIngestionError
    only for pre-flight validation; past that point, every message and
    attachment is processed independently and reported in the returned
    result -- one bad message or attachment never aborts the rest."""
    if not raw_bytes:
        raise WhatsAppIngestionError(f"{source_filename}: empty upload")

    extension = Path(source_filename).suffix.lower()
    # Pre-commit review fix: a list per basename, never a single value --
    # preserves EVERY entry sharing a basename instead of silently
    # overwriting earlier ones, so _resolve_media_candidate above can
    # detect and refuse an ambiguous reference instead of one candidate
    # invisibly winning by archive order.
    media_entries: dict[str, list[bytes]] = {}
    zip_warnings: list[str] = []

    if extension == ".zip":
        try:
            extraction = extract_whatsapp_entries(raw_bytes)
        except WhatsAppZipImportError as exc:
            raise WhatsAppIngestionError(f"{source_filename}: {exc}") from exc

        chat_entry = None
        for entry in extraction.entries:
            if entry.name.lower().endswith(".txt") and (chat_entry is None or len(entry.content) > len(chat_entry.content)):
                chat_entry = entry
        if chat_entry is None:
            raise WhatsAppIngestionError(f"{source_filename}: no chat transcript (.txt) file found in the archive")

        chat_bytes = chat_entry.content
        for entry in extraction.entries:
            if entry is chat_entry:
                continue
            media_entries.setdefault(Path(entry.name).name, []).append(entry.content)
        for rejected in extraction.rejected:
            zip_warnings.append(f"{rejected.name}: {rejected.error}")
    elif extension == ".txt":
        chat_bytes = raw_bytes
    else:
        raise WhatsAppIngestionError(f"{source_filename}: not a supported file type (.txt transcript or .zip export)")

    if len(chat_bytes) > MAX_EXPORT_BYTES:
        raise WhatsAppIngestionError(
            f"{source_filename}: chat transcript exceeds the {MAX_EXPORT_BYTES // (1024 * 1024)} MB limit"
        )

    try:
        parsed_chat = parse_whatsapp_export(chat_bytes.decode("utf-8", errors="replace"))
    except WhatsAppParseError as exc:
        raise WhatsAppIngestionError(f"{source_filename}: {exc}") from exc

    chat = _find_or_create_chat(session, project_id, source_filename)

    imported = 0
    duplicate = 0
    attachments_processed = 0
    attachments_pending = 0
    attachments_unsupported = 0
    attachments_rejected = 0
    attachments_failed = 0
    attachments_ambiguous = 0

    for parsed_message in parsed_chat.messages:
        outcome = _ingest_message(
            session=session,
            storage_root=storage_root,
            project_id=project_id,
            chat=chat,
            parsed_message=parsed_message,
            media_entries=media_entries,
        )
        if outcome == "duplicate":
            duplicate += 1
            continue
        imported += 1
        for attachment_status in outcome:
            if attachment_status == "processed":
                attachments_processed += 1
            elif attachment_status == "stored_pending_processing":
                attachments_pending += 1
            elif attachment_status == "unsupported_format":
                attachments_unsupported += 1
            elif attachment_status == "rejected":
                attachments_rejected += 1
            elif attachment_status == "failed":
                attachments_failed += 1
            elif attachment_status == "ambiguous":
                attachments_ambiguous += 1

    return WhatsAppImportResult(
        chat_id=chat.id,
        chat_title=chat.title,
        imported=imported,
        duplicate=duplicate,
        attachments_processed=attachments_processed,
        attachments_pending=attachments_pending,
        attachments_unsupported=attachments_unsupported,
        attachments_rejected=attachments_rejected,
        attachments_failed=attachments_failed,
        attachments_ambiguous=attachments_ambiguous,
        parse_warnings=[*parsed_chat.parse_notes, *zip_warnings],
    )


def _ingest_message(
    *,
    session: Session,
    storage_root: Path,
    project_id: int,
    chat: WhatsAppChat,
    parsed_message: ParsedWhatsAppMessage,
    media_entries: dict[str, list[bytes]],
) -> str | list[str]:
    """Returns "duplicate", or a list of attachment statuses (possibly
    empty) for a newly-imported message."""
    content_hash = compute_content_hash(parsed_message)
    existing = find_existing_by_content_hash(session, chat.id, content_hash)
    if existing is not None:
        return "duplicate"

    sequence_index = _next_sequence_index(session, chat.id)

    document = Document(
        project_id=project_id,
        filename=f"{chat.title or chat.source_export_filename} — message {sequence_index + 1}.txt",
        doc_type="WHATSAPP_MESSAGE",
        status="processing",
    )
    session.add(document)
    session.commit()
    session.refresh(document)

    try:
        full_text = parsed_message.text or ""
        storage_key = new_storage_key(f"whatsapp_{chat.id}_{sequence_index}")
        text_path = save_extracted_text(storage_root, project_id, storage_key, full_text)

        document.raw_text_path = str(text_path)
        document.doc_date = parsed_message.sent_at.date() if parsed_message.sent_at else None
        document.referenced_ids = extract_referenced_ids(full_text)

        index_document(session, document)

        document.status = "ready"
        document.processing_error = None
        session.commit()
        session.refresh(document)
    except Exception as exc:  # noqa: BLE001 -- any failure here must end in 'failed', never propagate and lose the row
        session.rollback()
        session.refresh(document)
        document.status = "failed"
        document.processing_error = str(exc)
        session.add(document)
        session.commit()
        session.refresh(document)
        logger.warning("WhatsApp message indexing failed (document_id=%s): %s", document.id, exc)

    message = WhatsAppMessage(
        document_id=document.id,
        project_id=project_id,
        chat_id=chat.id,
        sequence_index=sequence_index,
        sender_name=parsed_message.sender_name,
        raw_timestamp_text=parsed_message.raw_timestamp_text,
        sent_at=parsed_message.sent_at,
        sent_at_ambiguous=parsed_message.sent_at_ambiguous,
        message_type=parsed_message.message_type,
        content_hash=content_hash,
    )
    session.add(message)
    try:
        session.commit()
    except IntegrityError:
        # Pre-commit review fix pattern reused from email_ingestion/
        # pipeline.py: a concurrent import of the exact same message raced
        # past the dedup pre-check above. Roll back, discard the orphaned
        # Document this attempt just created, and report this message as
        # a duplicate of whichever request actually won the race -- never
        # a 500, never a silently duplicated evidence record.
        session.rollback()
        session.delete(document)
        session.commit()
        return "duplicate"
    session.refresh(message)

    attachment_statuses: list[str] = []
    if parsed_message.media_filename:
        resolution = _resolve_media_candidate(media_entries, parsed_message.media_filename)
        attachment_statuses.append(
            _ingest_media_attachment(
                session=session,
                storage_root=storage_root,
                project_id=project_id,
                message_document_id=message.document_id,
                filename=parsed_message.media_filename,
                resolution=resolution,
            )
        )

    return attachment_statuses


def _ingest_media_attachment(
    *,
    session: Session,
    storage_root: Path,
    project_id: int,
    message_document_id: int,
    filename: str,
    resolution: _MediaResolution,
) -> str:
    """Process one media reference, already resolved against the
    archive's actual entries by _resolve_media_candidate.

    'missing' means the export's text referenced a filename that wasn't
    actually present among the archive's extracted entries (e.g. a
    text-only export, or a media file that was itself rejected by the ZIP
    safety layer) -- recorded honestly as 'rejected'.

    'ambiguous' (pre-commit review fix) means MORE THAN ONE archive entry
    shares this basename -- recorded as its own distinct outcome, with no
    bytes ever read and no file ever written for it: selecting any one of
    the candidates would risk silently attaching the wrong evidence to
    this message, which this function refuses to do."""
    if resolution.status == "missing":
        row = WhatsAppMediaAttachment(
            message_id=message_document_id,
            document_id=None,
            filename=filename,
            content_type=None,
            size_bytes=0,
            content_hash="",
            status="rejected",
            processing_error="referenced media file was not present in the uploaded export",
        )
        session.add(row)
        session.commit()
        return "rejected"

    if resolution.status == "ambiguous":
        row = WhatsAppMediaAttachment(
            message_id=message_document_id,
            document_id=None,
            filename=filename,
            content_type=None,
            size_bytes=0,
            content_hash="",
            status="rejected",
            processing_error=(
                f"ambiguous reference: {resolution.candidate_count} files named {filename!r} were found in "
                "the archive; ClaimTrace cannot determine which one this message attached, so none was used"
            ),
        )
        session.add(row)
        session.commit()
        return "ambiguous"

    content = resolution.content
    if not content:
        row = WhatsAppMediaAttachment(
            message_id=message_document_id,
            document_id=None,
            filename=filename,
            content_type=None,
            size_bytes=0,
            content_hash="",
            status="rejected",
            processing_error="empty attachment",
        )
        session.add(row)
        session.commit()
        return "rejected"

    content_hash = hashlib.sha256(content).hexdigest()
    size_bytes = len(content)
    extension, content_type = _detect_media_type(content)

    if extension in _SUPPORTED_DOCUMENT_EXTENSIONS:
        try:
            document = ingest_document(
                session=session,
                storage_root=storage_root,
                project_id=project_id,
                filename=f"{Path(filename).stem}{extension}",
                content=content,
            )
        except IngestionError as exc:
            row = WhatsAppMediaAttachment(
                message_id=message_document_id,
                document_id=None,
                filename=filename,
                content_type=content_type,
                size_bytes=size_bytes,
                content_hash=content_hash,
                status="rejected",
                processing_error=str(exc),
            )
            session.add(row)
            session.commit()
            return "rejected"

        row = WhatsAppMediaAttachment(
            message_id=message_document_id,
            document_id=document.id,
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
            content_hash=content_hash,
            status="processed" if document.status == "ready" else "failed",
            processing_error=document.processing_error,
        )
        session.add(row)
        try:
            session.commit()
        except Exception as exc:  # noqa: BLE001 -- see the narrow, documented limitation below
            # Pre-commit review fix (partial): `document` was already
            # committed by ingest_document() in its OWN, separate,
            # already-finished transaction -- it is real, successfully-
            # persisted, indexed evidence. It must NOT be deleted here:
            # discarding already-committed evidence to "clean up" would
            # be worse than leaving it unlinked. This is therefore a
            # genuinely unresolved, narrow limitation (documented, not
            # silently assumed away): the Document exists and remains
            # fully searchable/citable, but its WhatsAppMediaAttachment
            # provenance row -- the link back to which message attached
            # it -- is lost, not its content. Fixing this fully would
            # require deferring ingest_document()'s own internal commit
            # into this same transaction, a broader change to that
            # shared, unmodified pipeline this task's scope does not
            # call for. Reported honestly via the 'failed' outcome below
            # rather than silently retried or assumed to have succeeded.
            session.rollback()
            logger.warning(
                "WhatsApp attachment row commit failed for already-indexed document_id=%s "
                "(document retained; its message-level provenance link is missing): %s",
                document.id,
                exc,
            )
            return "failed"
        return row.status

    # Not a supported-for-indexing document type -- preserve the ORIGINAL
    # bytes safely regardless (W1's explicit requirement, deliberately
    # different from the email-attachment precedent of discarding
    # unsupported bytes). No Document, no citation, no fabricated
    # understanding -- just a real, openable original awaiting the
    # multimodal processing phases this task establishes the contract for.
    storage_key = new_storage_key(filename)
    file_path = save_whatsapp_media(storage_root, project_id, storage_key, content, extension)
    row = WhatsAppMediaAttachment(
        message_id=message_document_id,
        document_id=None,
        filename=filename,
        content_type=content_type,
        size_bytes=size_bytes,
        content_hash=content_hash,
        status="stored_pending_processing",
        processing_error=None,
        storage_key=storage_key,
        detected_extension=extension,
    )
    session.add(row)
    try:
        session.commit()
    except Exception as exc:  # noqa: BLE001 -- compensating cleanup for the file just written above
        # Pre-commit review fix: unlike the PDF/DOCX branch above, the
        # file this just wrote (`file_path`) is NOT shared or referenced
        # anywhere else -- it was created fresh, under its own
        # freshly-generated storage_key, exclusively for this attachment
        # row, which never got durably persisted. Removing it is
        # therefore safe and correct, not a deletion of successfully-
        # committed or shared evidence.
        session.rollback()
        file_path.unlink(missing_ok=True)
        logger.warning(
            "WhatsApp media attachment commit failed after writing %s; removed the now-orphaned file: %s",
            file_path,
            exc,
        )
        return "failed"

    # Phase W2.1 (Local OCR Foundation): WhatsApp preserves ALL
    # unsupported media as bytes (images, audio, video, other -- see this
    # function's own docstring above), unlike Gmail/direct-upload, which
    # only ever reach this status for images. OCR must NEVER be attempted
    # on non-image media -- `extension` here is the real, server-detected
    # type from _detect_media_type() above, never the claimed filename, so
    # this check is reliable, not a guess from the attachment's name.
    if extension in OCR_ELIGIBLE_EXTENSIONS:
        ensure_pending_ocr_result(
            session,
            whatsapp_media_attachment_id=row.id,
            default_language=get_settings().ocr_language,
        )
    return "stored_pending_processing"
