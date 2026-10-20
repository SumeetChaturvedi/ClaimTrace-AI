"""Bridges locally-OCR'd image text into the existing, unmodified
Document/DocumentChunk indexing pipeline (Phase W2.2: OCR Evidence
Integration) -- reuses index_document(), extract_metadata(), and
normalize_document_type() exactly as PDF/DOCX ingestion and the email/
WhatsApp message-body indexing functions already do (see
app/ingestion/pipeline.py and app/email_ingestion/pipeline.py's own
body-indexing function); this module adds no new chunking, embedding,
retrieval, or citation logic of its own.

Called from app/ocr/process_pending.py's _process_claimed_result, inside
that function's own lease-scoped transaction. Every write this module
makes is staged (added/flushed), NEVER committed -- the caller decides,
only after also checking its own lease-scoped row count, whether to
commit everything together or roll all of it back. This ordering is the
one correctness requirement of this phase: see process_pending.py's own
module docstring for why committing this module's work independently of
that check would reintroduce the exact stale-write problem the W2.1
lease mechanism exists to prevent.

document_id/status on ProjectImageAsset, EmailAttachment, and
WhatsAppMediaAttachment are pre-existing columns (see each model's own
docstring in app/db/models.py), reserved for exactly this purpose since
Phase W2.0 -- no schema change is made or needed here.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Union

from sqlalchemy.orm import Session

from app.db.models import Document, EmailAttachment, ImageOcrResult, ProjectImageAsset, WhatsAppMediaAttachment
from app.domain.document_types import normalize_document_type
from app.ingestion.indexing import index_document
from app.ingestion.metadata import extract_metadata

OcrParent = Union[ProjectImageAsset, EmailAttachment, WhatsAppMediaAttachment]


@dataclass(frozen=True)
class OcrIndexOutcome:
    """What the caller must then write onto the PARENT row
    (document_id/status), in the SAME transaction as everything this
    module staged -- never applied here, since this module has no
    lease-ownership context of its own (see module docstring)."""

    document_id: int | None
    parent_status: str


def resolve_ocr_parent(session: Session, result: ImageOcrResult) -> OcrParent | None:
    """Fetch the ORM row that owns this OCR result -- the exact same
    three-way branch app/ocr/process_pending.py's own
    _resolve_source_image already uses to find the preserved image
    bytes, but returning the parent ROW itself (so its document_id/
    status can be updated), not its file contents. Returns None only if
    the parent has somehow vanished since _resolve_source_image's own,
    moments-earlier check in the same transaction -- the caller treats
    that as an error, not a silent no-op."""
    if result.project_image_asset_id is not None:
        return session.get(ProjectImageAsset, result.project_image_asset_id)
    if result.email_attachment_id is not None:
        return session.get(EmailAttachment, result.email_attachment_id)
    if result.whatsapp_media_attachment_id is not None:
        return session.get(WhatsAppMediaAttachment, result.whatsapp_media_attachment_id)
    return None


def index_ocr_text(
    session: Session,
    *,
    parent: OcrParent,
    project_id: int,
    filename: str,
    ocr_text: str,
    ocr_text_path: Path,
) -> OcrIndexOutcome:
    """Stage (never commits) whatever Document/DocumentChunk changes are
    needed for one OCR result's just-written text. Only ever called once
    OCR has genuinely completed (see process_pending.py's own call
    site); parent_status is therefore always 'processed', never a
    transient or failed state.

    - Non-empty text: reuses `parent.document_id`'s existing Document if
      one is already set, else creates a new one; sets raw_text_path to
      the OCR text file already written to disk (no duplicate write),
      classifies doc_type/doc_date/referenced_ids via the EXISTING
      extract_metadata()/normalize_document_type() (the same, unmodified
      machinery PDF/DOCX/email/WhatsApp documents already go through --
      None is the expected, fully-supported outcome for a source with no
      literal "DOCUMENT TYPE:" text, which is the common case for a
      generic site photo. This deliberately does NOT default to
      DocumentType.PHOTO_RECORD: that canonical type's only existing
      precedent (see app/domain/document_types.py) is a TEXT LOG
      *describing* photos, explicitly with no images in it -- the
      opposite of text *extracted from* an image -- so reusing it here
      would misrepresent the evidence, not merely leave it unclassified),
      then calls the existing index_document() unchanged.
    - Empty/whitespace-only text with no existing Document (parent.
      document_id is None): creates nothing. No Document, no
      DocumentChunk, for text with nothing to search.
    - Empty/whitespace-only text with an existing Document (a force/
      config-change reprocess that now finds nothing): the Document is
      KEPT (document_id stays set) -- nothing in this codebase deletes a
      single Document in isolation -- but index_document() is still
      called with the empty text, so the EXISTING delete-then-reinsert
      clears its now-stale chunks to zero. doc_type/doc_date are cleared
      to None (there is no longer any text to have derived them from),
      and referenced_ids is cleared to [] -- not None -- matching the
      type every other ingestion path already stores there
      (extract_referenced_ids() always returns list[str], never None;
      see app/ingestion/metadata.py and its callers in pipeline.py/
      email_ingestion/pipeline.py/whatsapp_ingestion/pipeline.py). None
      would be the only place in the codebase where this column held
      that value instead of an empty list for "nothing found"."""
    stripped = ocr_text.strip()

    if not stripped and parent.document_id is None:
        return OcrIndexOutcome(document_id=None, parent_status="processed")

    document = session.get(Document, parent.document_id) if parent.document_id is not None else None
    if document is None:
        document = Document(project_id=project_id, filename=filename, status="ready")
        session.add(document)

    document.raw_text_path = str(ocr_text_path)
    document.status = "ready"
    document.processing_error = None

    if stripped:
        metadata = extract_metadata(ocr_text)
        canonical_doc_type = normalize_document_type(metadata.doc_type)
        document.doc_type = canonical_doc_type.value if canonical_doc_type is not None else None
        document.doc_date = metadata.doc_date
        document.referenced_ids = metadata.referenced_ids
    else:
        document.doc_type = None
        document.doc_date = None
        document.referenced_ids = []

    session.flush()  # assigns document.id if this is a brand-new row, before index_document needs it
    index_document(session, document)

    return OcrIndexOutcome(document_id=document.id, parent_status="processed")
