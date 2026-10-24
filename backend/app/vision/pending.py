"""Shared "ensure a pending ImageVisualDescriptionResult row exists"
helper (Phase W2.3: Multimodal Image Understanding) -- mirrors
app/ocr/pending.py's ensure_pending_ocr_result() exactly, for the
SEPARATE visual-description table. Deliberately not wired into the three
ingestion paths (app/api/routes/project_images.py,
app/email_ingestion/pipeline.py, app/whatsapp_ingestion/pipeline.py) the
way OCR's own version is -- app/vision/process_pending.py's own discovery
step (mirroring app/ocr/process_pending.py's _discover_missing_pending_rows)
is the only caller, so this phase touches zero bytes of those
already-reviewed ingestion modules."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import ImageVisualDescriptionResult
from app.ocr.pending import OCR_ELIGIBLE_EXTENSIONS  # same "which image formats" source of truth, reused

__all__ = ["OCR_ELIGIBLE_EXTENSIONS", "ensure_pending_visual_result"]

logger = logging.getLogger(__name__)


def ensure_pending_visual_result(
    session: Session,
    *,
    project_image_asset_id: int | None = None,
    email_attachment_id: int | None = None,
    whatsapp_media_attachment_id: int | None = None,
) -> None:
    """Idempotently ensure exactly one `pending` ImageVisualDescriptionResult
    row exists for the given source attachment -- mirrors
    ensure_pending_ocr_result() exactly (see its own docstring for the
    full rationale: existence-check first, backstopped by the real
    ux_image_visual_description_results_*_id unique constraints for a
    concurrent-create race). Exactly one of the three id arguments must
    be given. Never raises."""
    given = [
        value
        for value in (project_image_asset_id, email_attachment_id, whatsapp_media_attachment_id)
        if value is not None
    ]
    assert len(given) == 1, "exactly one source id must be given"

    try:
        existing = session.scalar(
            select(ImageVisualDescriptionResult).where(
                ImageVisualDescriptionResult.project_image_asset_id == project_image_asset_id,
                ImageVisualDescriptionResult.email_attachment_id == email_attachment_id,
                ImageVisualDescriptionResult.whatsapp_media_attachment_id == whatsapp_media_attachment_id,
            )
        )
        if existing is not None:
            return

        session.add(
            ImageVisualDescriptionResult(
                project_image_asset_id=project_image_asset_id,
                email_attachment_id=email_attachment_id,
                whatsapp_media_attachment_id=whatsapp_media_attachment_id,
                status="pending",
                vision_model="gemini",
            )
        )
        session.commit()
    except IntegrityError:
        session.rollback()
    except Exception as exc:  # noqa: BLE001 -- see ensure_pending_ocr_result's own docstring: never abort the caller
        session.rollback()
        logger.warning(
            "Could not create a pending ImageVisualDescriptionResult row (project_image_asset_id=%s, "
            "email_attachment_id=%s, whatsapp_media_attachment_id=%s); the batch processor's own "
            "discovery step will retry this: %s",
            project_image_asset_id,
            email_attachment_id,
            whatsapp_media_attachment_id,
            exc,
        )
