"""Shared "ensure a pending ImageOcrResult row exists" helper (Phase
W2.1: Local OCR Foundation) -- called from each of the three image-
preservation paths (app/api/routes/project_images.py,
app/email_ingestion/pipeline.py, app/whatsapp_ingestion/pipeline.py)
right after a `stored_pending_processing` attachment row is durably
committed, AND reused by app/ocr/process_pending.py's own discovery step
for any preserved image that somehow has no row yet (e.g. one preserved
before this phase existed) -- one implementation, not three copies of the
same get-or-create logic."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import ImageOcrResult

logger = logging.getLogger(__name__)

# The only extensions app/ingestion/image_validation.py's validate_image()
# ever assigns (see its own _IMAGE_SIGNATURES/WEBP check) -- the same,
# single source of truth for "which image formats this application
# understands" that every other OCR-eligibility check in this phase
# reuses, rather than a second, possibly-drifting list.
OCR_ELIGIBLE_EXTENSIONS = frozenset({".jpg", ".png", ".gif", ".webp"})


def ensure_pending_ocr_result(
    session: Session,
    *,
    project_image_asset_id: int | None = None,
    email_attachment_id: int | None = None,
    whatsapp_media_attachment_id: int | None = None,
    default_language: str,
) -> None:
    """Idempotently ensure exactly one `pending` ImageOcrResult row exists
    for the given source attachment -- a no-op if one already exists
    (checked first, then backstopped by the real
    ux_image_ocr_results_*_id unique constraints for a concurrent-create
    race, mirroring every other get-or-create pattern already in this
    codebase). Exactly one of the three id arguments must be given; this
    is an internal helper with callers fully under this codebase's own
    control, so that is asserted rather than defensively handled as if it
    were untrusted input.

    Never raises, never aborts the caller's own ingestion flow: a failure
    here (including a genuine, unexpected database error) is logged and
    swallowed -- this row is a secondary bookkeeping record, and
    app/ocr/process_pending.py's own discovery step will find and create
    it on a later run if this attempt didn't stick. The already-committed
    attachment row's own `stored_pending_processing` status is never at
    risk from a failure in this function, since that commit already
    happened, in its own, separate, already-finished transaction, before
    this function is ever called."""
    given = [
        value
        for value in (project_image_asset_id, email_attachment_id, whatsapp_media_attachment_id)
        if value is not None
    ]
    assert len(given) == 1, "exactly one source id must be given"

    try:
        existing = session.scalar(
            select(ImageOcrResult).where(
                ImageOcrResult.project_image_asset_id == project_image_asset_id,
                ImageOcrResult.email_attachment_id == email_attachment_id,
                ImageOcrResult.whatsapp_media_attachment_id == whatsapp_media_attachment_id,
            )
        )
        if existing is not None:
            return

        session.add(
            ImageOcrResult(
                project_image_asset_id=project_image_asset_id,
                email_attachment_id=email_attachment_id,
                whatsapp_media_attachment_id=whatsapp_media_attachment_id,
                status="pending",
                ocr_engine="tesseract",
                ocr_language=default_language,
            )
        )
        session.commit()
    except IntegrityError:
        # A concurrent call for the SAME attachment already won the race
        # between our existence check and this commit -- the unique
        # constraint is the real backstop, this is simply the expected
        # outcome of losing it, never a failure to report.
        session.rollback()
    except Exception as exc:  # noqa: BLE001 -- see docstring: never let this abort the caller's own ingestion flow
        session.rollback()
        logger.warning(
            "Could not create a pending ImageOcrResult row (project_image_asset_id=%s, "
            "email_attachment_id=%s, whatsapp_media_attachment_id=%s); the batch processor's "
            "own discovery step will retry this: %s",
            project_image_asset_id,
            email_attachment_id,
            whatsapp_media_attachment_id,
            exc,
        )
