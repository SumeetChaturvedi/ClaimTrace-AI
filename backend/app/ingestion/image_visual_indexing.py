"""Bridges AI-generated visual descriptions into the existing,
unmodified Document/DocumentChunk indexing pipeline (Phase W2.3:
Multimodal Image Understanding) -- a deliberate SIBLING of
app/ingestion/image_ocr_indexing.py, not a shared/parameterized version
of it: this module writes to a parent's `visual_document_id` (never
`document_id`), and marks the Document it creates/reuses with
`derivation_kind="visual_description"` (never "ocr_transcription" and
never left NULL). Reuses index_document() exactly as OCR's own bridge
does -- no new chunking/embedding/retrieval/citation logic.

Called from app/vision/process_pending.py's own _process_claimed_result,
inside that function's own lease-scoped transaction, with the exact same
stage-then-commit-together discipline image_ocr_indexing.py's own module
docstring documents (never committed independently of the caller's own
lease-scoped row count check) -- see that module's docstring for the
full correctness rationale, which applies here unchanged.

Because this writes to a SEPARATE column (`visual_document_id`) on the
SAME parent row `document_id` (OCR) already uses, and to a SEPARATE
Document row, OCR and vision reprocessing can never corrupt each other:
index_document()'s own delete-then-reinsert is always scoped to whichever
one Document id THIS call was given, never the other derivation's."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Union

from sqlalchemy.orm import Session

from app.db.models import Document, EmailAttachment, ImageVisualDescriptionResult, ProjectImageAsset, WhatsAppMediaAttachment
from app.ingestion.indexing import index_document

VisualParent = Union[ProjectImageAsset, EmailAttachment, WhatsAppMediaAttachment]

DERIVATION_KIND_VISUAL_DESCRIPTION = "visual_description"


@dataclass(frozen=True)
class VisualIndexOutcome:
    """What the caller must then write onto the PARENT row
    (visual_document_id/status), in the SAME transaction as everything
    this module staged -- never applied here (see module docstring)."""

    visual_document_id: int | None
    parent_status: str


def resolve_visual_parent(session: Session, result: ImageVisualDescriptionResult) -> VisualParent | None:
    """Fetch the ORM row that owns this visual-description result -- the
    exact same three-way branch app/ingestion/image_ocr_indexing.py's own
    resolve_ocr_parent() uses, applied to ImageVisualDescriptionResult's
    own three parent FKs instead of ImageOcrResult's."""
    if result.project_image_asset_id is not None:
        return session.get(ProjectImageAsset, result.project_image_asset_id)
    if result.email_attachment_id is not None:
        return session.get(EmailAttachment, result.email_attachment_id)
    if result.whatsapp_media_attachment_id is not None:
        return session.get(WhatsAppMediaAttachment, result.whatsapp_media_attachment_id)
    return None


def index_visual_description(
    session: Session,
    *,
    parent: VisualParent,
    project_id: int,
    filename: str,
    description_text: str,
    description_text_path: Path,
) -> VisualIndexOutcome:
    """Stage (never commits) whatever Document/DocumentChunk changes are
    needed for one generated visual description. Mirrors
    image_ocr_indexing.py's index_ocr_text() exactly, with two
    differences: it reads/writes `parent.visual_document_id` (never
    `parent.document_id`), and it ALWAYS sets `derivation_kind` on the
    Document it touches -- to "visual_description" for non-empty text,
    and left as "visual_description" (not cleared to None) even when the
    text is empty, since an existing visual-description Document being
    re-described-as-empty is still, unambiguously, a visual-description
    Document, never an ordinary one.

    No doc_type/doc_date/referenced_ids classification is attempted here
    (unlike OCR's own bridge): extract_metadata()'s "DOCUMENT TYPE:"-
    header-based extraction is meaningless for a model-generated
    description sentence, and running it would risk a false-positive
    match on ordinary prose."""
    stripped = description_text.strip()

    if not stripped and parent.visual_document_id is None:
        return VisualIndexOutcome(visual_document_id=None, parent_status="processed")

    document = session.get(Document, parent.visual_document_id) if parent.visual_document_id is not None else None
    if document is None:
        document = Document(project_id=project_id, filename=filename, status="ready")
        session.add(document)

    document.raw_text_path = str(description_text_path)
    document.status = "ready"
    document.processing_error = None
    document.derivation_kind = DERIVATION_KIND_VISUAL_DESCRIPTION
    document.doc_type = None
    document.doc_date = None
    document.referenced_ids = []

    session.flush()  # assigns document.id if this is a brand-new row, before index_document needs it
    index_document(session, document)

    return VisualIndexOutcome(visual_document_id=document.id, parent_status="processed")
