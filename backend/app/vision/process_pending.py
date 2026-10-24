"""Independently runnable batch visual-description processor (Phase
W2.3: Multimodal Image Understanding) -- the ONLY place Gemini is ever
called with image bytes. Mirrors app/ocr/process_pending.py's entire
design -- SELECT ... FOR UPDATE SKIP LOCKED claiming, a database-backed
lease renewed once before work starts and again right after the
provider call returns (see that module's own, extensively-documented
rationale for why this two-renewal design is what makes the lease window
independent of --batch-size), and lease-scoped conditional UPDATEs for
every status-setting write -- applied to the SEPARATE
ImageVisualDescriptionResult table and its own, separate lease, never
ImageOcrResult's. A lost OCR lease and a lost vision lease can never
affect each other: they are different rows in different tables, claimed
and renewed independently.

Indexing (Phase W2.3, mirroring W2.2): a successfully generated,
non-empty description is staged into the shared Document/DocumentChunk
pipeline (app/ingestion/image_visual_indexing.py) inside this SAME
lease-scoped transaction, committed or rolled back together with the
ImageVisualDescriptionResult's own final write -- see
image_ocr_indexing.py's own module docstring for the full correctness
rationale (this module applies it unchanged, to visual_document_id
instead of document_id).

No new CLI framework: a plain stdlib `argparse` entrypoint, run as a
module exactly like app/ocr/process_pending.py's own --

    cd backend && source .venv/bin/activate
    python -m app.vision.process_pending [--batch-size N] [--limit N]
        [--retry-failed] [--force]

Model compatibility is NOT assumed or verified by this module (see
app/vision/gemini_vision.py's own docstring) -- a provider rejection for
an unsupported model/image combination is handled exactly like any other
provider failure: a clean 'failed' outcome for that one row, with the
row's own --retry-failed/--force reprocessing semantics available once
the underlying issue (e.g. a model configuration change) is resolved."""

from __future__ import annotations

import argparse
import logging
import secrets
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import exists, or_, select, update
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.models import EmailAttachment, EmailMessage, ImageVisualDescriptionResult, ProjectImageAsset, WhatsAppMediaAttachment, WhatsAppMessage
from app.db.session import get_session_factory
from app.ingestion.image_validation import validate_image
from app.ingestion.image_visual_indexing import index_visual_description, resolve_visual_parent
from app.ingestion.storage import image_storage_dir, new_storage_key, save_visual_description, whatsapp_media_dir
from app.ocr.pending import OCR_ELIGIBLE_EXTENSIONS
from app.ocr.process_pending import _PRESERVED_IMAGE_STATUSES  # same "OCR/vision can both still see the original" fix, reused
from app.vision.gemini_vision import VISION_MODEL_NAME, generate_visual_description
from app.vision.pending import ensure_pending_visual_result

logger = logging.getLogger(__name__)

DEFAULT_BATCH_SIZE = 20

# Identical rationale to app/ocr/process_pending.py's own
# LEASE_DURATION_SECONDS -- a per-row window, renewed fresh at the moment
# work on that specific row begins, independent of --batch-size. A
# Gemini call has no fixed timeout enforced by this codebase (unlike
# Tesseract's OCR_TIMEOUT_SECONDS); 120s is a generous, explicit margin
# for one image's own request/response round trip.
LEASE_DURATION_SECONDS = 120


class _ResolvedVisualImage:
    __slots__ = ("content", "content_type", "project_id", "filename")

    def __init__(self, content: bytes, content_type: str, project_id: int, filename: str) -> None:
        self.content = content
        self.content_type = content_type
        self.project_id = project_id
        self.filename = filename


def _discover_missing_pending_rows(session: Session) -> int:
    """Self-healing discovery, mirroring app/ocr/process_pending.py's own
    _discover_missing_pending_rows -- but checking BOTH preserved-image
    statuses (_PRESERVED_IMAGE_STATUSES), not only
    'stored_pending_processing': an image that OCR has already finished
    (status='processed') is still a perfectly valid candidate for a
    visual description, since the two are independent derivations of the
    same preserved original."""
    created = 0

    for asset_id in session.scalars(
        select(ProjectImageAsset.id).where(
            ProjectImageAsset.status.in_(_PRESERVED_IMAGE_STATUSES),
            ~exists().where(ImageVisualDescriptionResult.project_image_asset_id == ProjectImageAsset.id),
        )
    ).all():
        ensure_pending_visual_result(session, project_image_asset_id=asset_id)
        created += 1

    for attachment_id in session.scalars(
        select(EmailAttachment.id).where(
            EmailAttachment.status.in_(_PRESERVED_IMAGE_STATUSES),
            ~exists().where(ImageVisualDescriptionResult.email_attachment_id == EmailAttachment.id),
        )
    ).all():
        ensure_pending_visual_result(session, email_attachment_id=attachment_id)
        created += 1

    for attachment_id in session.scalars(
        select(WhatsAppMediaAttachment.id).where(
            WhatsAppMediaAttachment.status.in_(_PRESERVED_IMAGE_STATUSES),
            WhatsAppMediaAttachment.detected_extension.in_(OCR_ELIGIBLE_EXTENSIONS),
            ~exists().where(ImageVisualDescriptionResult.whatsapp_media_attachment_id == WhatsAppMediaAttachment.id),
        )
    ).all():
        ensure_pending_visual_result(session, whatsapp_media_attachment_id=attachment_id)
        created += 1

    return created


def _eligibility_clause(*, retry_failed: bool, force: bool, current_model_version: str | None, now: datetime):
    """Mirrors app/ocr/process_pending.py's own _eligibility_clause
    exactly, keyed on (vision_model_version) instead of
    (ocr_engine_version, ocr_language) -- there is no separate
    "language" concept for a vision description."""
    completed_is_stale = (ImageVisualDescriptionResult.status == "completed") & (
        ImageVisualDescriptionResult.vision_model_version.is_distinct_from(current_model_version)
    )
    abandoned_processing = (ImageVisualDescriptionResult.status == "processing") & (
        ImageVisualDescriptionResult.lease_expires_at.is_(None) | (ImageVisualDescriptionResult.lease_expires_at < now)
    )

    eligible = [ImageVisualDescriptionResult.status == "pending", abandoned_processing]
    if retry_failed or force:
        eligible.append(ImageVisualDescriptionResult.status == "failed")
    if force:
        eligible.append(ImageVisualDescriptionResult.status == "completed")
    else:
        eligible.append(completed_is_stale)
    return or_(*eligible)


def _list_eligible_ids(
    session: Session, *, retry_failed: bool, force: bool, current_model_version: str | None, limit: int | None, now: datetime
) -> list[int]:
    """Fixed snapshot, mirroring app/ocr/process_pending.py's own
    _list_eligible_ids -- see that function's docstring for why this
    must never be re-queried mid-run."""
    clause = _eligibility_clause(retry_failed=retry_failed, force=force, current_model_version=current_model_version, now=now)
    query = select(ImageVisualDescriptionResult.id).where(clause).order_by(ImageVisualDescriptionResult.id)
    if limit is not None:
        query = query.limit(limit)
    return list(session.scalars(query).all())


def _claim_specific_rows(
    session: Session, candidate_ids: list[int], *, retry_failed: bool, force: bool, current_model_version: str | None, now: datetime
) -> list[tuple[int, str]]:
    """Mirrors app/ocr/process_pending.py's own _claim_specific_rows
    exactly -- SELECT ... FOR UPDATE SKIP LOCKED, re-applying the full
    eligibility clause, one fresh random lease_token per claimed row."""
    if not candidate_ids:
        return []

    clause = _eligibility_clause(retry_failed=retry_failed, force=force, current_model_version=current_model_version, now=now)
    claimed_rows = session.execute(
        select(ImageVisualDescriptionResult.id, ImageVisualDescriptionResult.status)
        .where(ImageVisualDescriptionResult.id.in_(candidate_ids), clause)
        .order_by(ImageVisualDescriptionResult.id)
        .with_for_update(skip_locked=True)
    ).all()
    if not claimed_rows:
        return []

    claimed_ids = [row_id for row_id, _status in claimed_rows]
    reclaimed_ids = [row_id for row_id, row_status in claimed_rows if row_status == "processing"]
    if reclaimed_ids:
        logger.warning("Reclaiming %d ImageVisualDescriptionResult row(s) whose lease had expired: %s", len(reclaimed_ids), reclaimed_ids)

    claim_time = datetime.now(timezone.utc)
    lease_expiry = claim_time + timedelta(seconds=LEASE_DURATION_SECONDS)
    lease_tokens: dict[int, str] = {row_id: secrets.token_hex(16) for row_id in claimed_ids}
    for row_id in claimed_ids:
        session.execute(
            update(ImageVisualDescriptionResult)
            .where(ImageVisualDescriptionResult.id == row_id)
            .values(
                status="processing",
                processing_started_at=claim_time,
                error=None,
                lease_token=lease_tokens[row_id],
                lease_expires_at=lease_expiry,
            )
        )
    session.commit()
    return [(row_id, lease_tokens[row_id]) for row_id in claimed_ids]


def _resolve_source_image(session: Session, result: ImageVisualDescriptionResult, storage_root: Path) -> _ResolvedVisualImage | None:
    """Mirrors app/ocr/process_pending.py's own _resolve_source_image
    exactly, including the _PRESERVED_IMAGE_STATUSES check (accepting
    both 'stored_pending_processing' and 'processed'), with the real,
    server-detected content_type also returned (needed as Gemini's own
    mime_type, where OCR had no equivalent need)."""
    file_path: Path
    filename: str
    project_id: int
    content_type: str | None

    if result.project_image_asset_id is not None:
        asset = session.get(ProjectImageAsset, result.project_image_asset_id)
        if asset is None or asset.status not in _PRESERVED_IMAGE_STATUSES:
            return None
        if not asset.storage_key or not asset.detected_extension or asset.detected_extension not in OCR_ELIGIBLE_EXTENSIONS:
            return None
        project_id = asset.project_id
        filename = asset.filename
        content_type = asset.content_type
        file_path = image_storage_dir(storage_root, project_id) / f"{asset.storage_key}{asset.detected_extension}"

    elif result.email_attachment_id is not None:
        attachment = session.get(EmailAttachment, result.email_attachment_id)
        if attachment is None or attachment.status not in _PRESERVED_IMAGE_STATUSES:
            return None
        if not attachment.storage_key or not attachment.detected_extension or attachment.detected_extension not in OCR_ELIGIBLE_EXTENSIONS:
            return None
        message = session.get(EmailMessage, attachment.message_id)
        if message is None:
            return None
        project_id = message.project_id
        filename = attachment.filename
        content_type = attachment.content_type
        file_path = image_storage_dir(storage_root, project_id) / f"{attachment.storage_key}{attachment.detected_extension}"

    elif result.whatsapp_media_attachment_id is not None:
        attachment = session.get(WhatsAppMediaAttachment, result.whatsapp_media_attachment_id)
        if attachment is None or attachment.status not in _PRESERVED_IMAGE_STATUSES:
            return None
        if not attachment.storage_key or not attachment.detected_extension or attachment.detected_extension not in OCR_ELIGIBLE_EXTENSIONS:
            return None
        message = session.get(WhatsAppMessage, attachment.message_id)
        if message is None:
            return None
        project_id = message.project_id
        filename = attachment.filename
        content_type = attachment.content_type
        file_path = whatsapp_media_dir(storage_root, project_id) / f"{attachment.storage_key}{attachment.detected_extension}"

    else:
        return None

    resolved_root = storage_root.resolve()
    resolved_path = file_path.resolve()
    if resolved_path != resolved_root and not resolved_path.is_relative_to(resolved_root):
        logger.warning("Resolved visual-description source path escaped the storage root for ImageVisualDescriptionResult id=%s; refusing to read it", result.id)
        return None
    if not resolved_path.is_file():
        return None

    try:
        content = resolved_path.read_bytes()
    except OSError as exc:
        logger.warning("Could not read preserved image for ImageVisualDescriptionResult id=%s: %s", result.id, exc)
        return None

    # Real, server-detected content_type is always populated for an image
    # that reached 'stored_pending_processing' (see each model's own
    # column docstring in app/db/models.py); re-validated below anyway.
    return _ResolvedVisualImage(content=content, content_type=content_type or "application/octet-stream", project_id=project_id, filename=filename)


def _update_with_lease(session: Session, result_id: int, lease_token: str, values: dict) -> int:
    """Mirrors app/ocr/process_pending.py's own _update_with_lease
    exactly, scoped to ImageVisualDescriptionResult."""
    result = session.execute(
        update(ImageVisualDescriptionResult).where(ImageVisualDescriptionResult.id == result_id, ImageVisualDescriptionResult.lease_token == lease_token).values(**values)
    )
    return result.rowcount


def _renew_lease(session: Session, result_id: int, lease_token: str) -> bool:
    """Mirrors app/ocr/process_pending.py's own _renew_lease exactly."""
    try:
        rowcount = _update_with_lease(
            session, result_id, lease_token, {"lease_expires_at": datetime.now(timezone.utc) + timedelta(seconds=LEASE_DURATION_SECONDS)}
        )
        session.commit()
    except Exception as exc:  # noqa: BLE001 -- any failure here means "do not proceed", logged below
        session.rollback()
        logger.warning("ImageVisualDescriptionResult id=%s: lease renewal failed (%s) -- treating as lease lost", result_id, exc)
        return False
    return rowcount == 1


def _apply_lease_scoped_update(session: Session, result_id: int, lease_token: str, values: dict, *, context: str) -> bool:
    """Mirrors app/ocr/process_pending.py's own _apply_lease_scoped_update exactly."""
    try:
        rowcount = _update_with_lease(session, result_id, lease_token, values)
        session.commit()
        return rowcount == 1
    except Exception as exc:  # noqa: BLE001 -- narrow, deliberate, logged, with a bounded re-raise below
        session.rollback()
        logger.warning("ImageVisualDescriptionResult id=%s commit failed (%s): %s", result_id, context, exc)
        try:
            rowcount = _update_with_lease(
                session,
                result_id,
                lease_token,
                {"status": "failed", "error": f"commit failed ({context}): {exc}", "processed_at": datetime.now(timezone.utc), "lease_token": None, "lease_expires_at": None},
            )
            session.commit()
            return rowcount == 1
        except Exception as second_exc:  # noqa: BLE001 -- a second failure here is reported, not swallowed
            session.rollback()
            logger.error(
                "ImageVisualDescriptionResult id=%s: a SECOND consecutive commit failure (%s) after the first (%s) -- stopping this run.",
                result_id,
                second_exc,
                exc,
            )
            raise


def _process_claimed_result(session: Session, storage_root: Path, result_id: int, lease_token: str) -> str:
    """Processes exactly one already-claimed ('processing') row. Mirrors
    app/ocr/process_pending.py's own _process_claimed_result exactly in
    structure (two renewals, previous-result preservation, lease-scoped
    final write staged in the same transaction as the Document/chunk
    indexing work, rollback on lost lease) -- the only real differences
    are: no OCR-engine-version concept (vision_model_version only), an
    explicit image-byte-size check before the provider call, and writing
    to visual_document_id/image_visual_indexing.py instead of
    document_id/image_ocr_indexing.py. Returns one of 'completed',
    'empty', 'failed', 'skipped'."""
    result = session.get(ImageVisualDescriptionResult, result_id)
    if result is None:
        return "skipped"

    previous_text_path = result.description_text_path
    previous_model_version = result.vision_model_version
    had_previous_completed_result = previous_text_path is not None

    if not _renew_lease(session, result_id, lease_token):
        logger.warning("ImageVisualDescriptionResult id=%s: lease already lost before processing could begin -- skipping without calling the provider", result_id)
        return "skipped"

    def _mark_failed(error: str, *, model_version: str | None = None) -> str:
        values: dict = {"status": "failed", "error": error, "processed_at": datetime.now(timezone.utc), "lease_token": None, "lease_expires_at": None}
        if model_version is not None:
            values["vision_model_version"] = model_version
        owned = _apply_lease_scoped_update(session, result_id, lease_token, values, context="marking failed")
        return "failed" if owned else "skipped"

    def _restore_previous_completed_result(reason: str) -> str:
        logger.warning("ImageVisualDescriptionResult id=%s: %s -- preserving its previous completed result", result_id, reason)
        values = {
            "status": "completed",
            "description_text_path": previous_text_path,
            "vision_model_version": previous_model_version,
            "error": None,
            "processed_at": datetime.now(timezone.utc),
            "lease_token": None,
            "lease_expires_at": None,
        }
        owned = _apply_lease_scoped_update(session, result_id, lease_token, values, context="restoring previous completed result")
        return "failed" if owned else "skipped"

    resolved = _resolve_source_image(session, result, storage_root)
    if resolved is None:
        return _mark_failed("source image could not be resolved (missing, deleted, or not an eligible, still-preserved image)")

    # Defense in depth, mirroring run_ocr()'s own caller contract: never
    # trust that a file on disk still matches what was true when it was
    # first preserved.
    validation = validate_image(resolved.content)
    if not validation.valid:
        return _mark_failed(f"image failed re-validation before visual description: {validation.error}")

    # Explicit, configurable, application-level byte limit -- enforced
    # HERE, before any bytes are handed to generate_visual_description()
    # (and therefore before anything reaches Gemini), independent of
    # app/ingestion/image_validation.py's own, larger preservation limit
    # (see Settings.vision_max_image_bytes's own docstring).
    settings = get_settings()
    if len(resolved.content) > settings.vision_max_image_bytes:
        return _mark_failed(
            f"image ({len(resolved.content)} bytes) exceeds the configured "
            f"{settings.vision_max_image_bytes} byte vision processing limit"
        )

    vision_outcome = generate_visual_description(resolved.content, mime_type=validation.content_type or resolved.content_type)
    if vision_outcome.status != "completed":
        if had_previous_completed_result:
            return _restore_previous_completed_result(f"a reprocess visual-description attempt failed ({vision_outcome.error})")
        return _mark_failed(vision_outcome.error or "visual description failed", model_version=vision_outcome.model_version)

    # Second lease renewal, mirroring app/ocr/process_pending.py's own
    # post-OCR-call renewal exactly -- right after the provider call
    # returns, before any candidate file is written.
    if not _renew_lease(session, result_id, lease_token):
        logger.warning("ImageVisualDescriptionResult id=%s: lease lost after a successful provider call but before saving its result -- discarding this worker's output", result_id)
        return "skipped"

    storage_key = new_storage_key(resolved.filename)
    try:
        new_text_path = save_visual_description(storage_root, resolved.project_id, storage_key, vision_outcome.text or "")
    except OSError as exc:
        logger.warning("ImageVisualDescriptionResult id=%s: could not write description file: %s", result_id, exc)
        if had_previous_completed_result:
            return _restore_previous_completed_result(f"could not write the new description file ({exc})")
        return _mark_failed(f"could not write description file: {exc}")

    final_values = {
        "description_text_path": str(new_text_path),
        "vision_model_version": vision_outcome.model_version,
        "status": "completed",
        "error": None,
        "processed_at": datetime.now(timezone.utc),
        "lease_token": None,
        "lease_expires_at": None,
    }
    try:
        # Stage the Document/DocumentChunk work for this description
        # BEFORE the final lease-scoped write, in the SAME transaction --
        # never committed independently of it (see module docstring and
        # app/ingestion/image_visual_indexing.py's own).
        parent = resolve_visual_parent(session, result)
        if parent is None:
            raise RuntimeError("visual-description result's parent source row could not be resolved for indexing")

        index_outcome = index_visual_description(
            session,
            parent=parent,
            project_id=resolved.project_id,
            filename=resolved.filename,
            description_text=vision_outcome.text or "",
            description_text_path=new_text_path,
        )

        rowcount = _update_with_lease(session, result_id, lease_token, final_values)
        if rowcount == 1:
            parent.visual_document_id = index_outcome.visual_document_id
            parent.status = index_outcome.parent_status
            session.commit()
        else:
            session.rollback()
    except Exception as exc:  # noqa: BLE001 -- compensating cleanup for the candidate file just written above; also covers indexing failures
        session.rollback()
        new_text_path.unlink(missing_ok=True)
        logger.warning("ImageVisualDescriptionResult id=%s commit failed after writing candidate description %s; removed it: %s", result_id, new_text_path, exc)
        if had_previous_completed_result:
            return _restore_previous_completed_result(f"commit failed after a successful reprocess visual-description run ({exc})")
        return _mark_failed(f"commit failed after a successful visual-description run: {exc}")

    if rowcount == 0:
        new_text_path.unlink(missing_ok=True)
        logger.warning("ImageVisualDescriptionResult id=%s: lease lost before the final commit could apply -- discarding this worker's result", result_id)
        return "skipped"

    if previous_text_path and previous_text_path != str(new_text_path):
        try:
            Path(previous_text_path).unlink(missing_ok=True)
        except OSError as exc:
            logger.warning("Could not remove old visual-description file %s: %s", previous_text_path, exc)

    return "empty" if not (vision_outcome.text or "").strip() else "completed"


def process_pending(*, batch_size: int = DEFAULT_BATCH_SIZE, retry_failed: bool = False, force: bool = False, limit: int | None = None, storage_root: Path) -> dict[str, int]:
    """Mirrors app/ocr/process_pending.py's own process_pending() exactly
    in structure. Raises ValueError (before any database query) for a
    non-positive batch_size/limit."""
    if batch_size <= 0:
        raise ValueError(f"batch_size must be a positive integer, got {batch_size}")
    if limit is not None and limit <= 0:
        raise ValueError(f"limit must be a positive integer when given, got {limit}")

    counts = {"completed": 0, "empty": 0, "failed": 0, "skipped": 0}
    current_model_version = get_settings().gemini_model
    now = datetime.now(timezone.utc)

    session_factory = get_session_factory()
    with session_factory() as session:
        discovered = _discover_missing_pending_rows(session)
        if discovered:
            logger.info("Discovered %d preserved image(s) with no visual-description result row; created pending rows for them", discovered)

        eligible_ids = _list_eligible_ids(session, retry_failed=retry_failed, force=force, current_model_version=current_model_version, limit=limit, now=now)

        for batch_start in range(0, len(eligible_ids), batch_size):
            candidate_ids = eligible_ids[batch_start : batch_start + batch_size]
            claimed = _claim_specific_rows(session, candidate_ids, retry_failed=retry_failed, force=force, current_model_version=current_model_version, now=now)
            for result_id, lease_token in claimed:
                outcome = _process_claimed_result(session, storage_root, result_id, lease_token)
                counts[outcome] = counts.get(outcome, 0) + 1

    return counts


def _positive_int(raw: str) -> int:
    """Mirrors app/ocr/process_pending.py's own _positive_int exactly."""
    try:
        value = int(raw)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{raw!r} is not an integer")
    if value <= 0:
        raise argparse.ArgumentTypeError(f"must be a positive integer, got {value}")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.vision.process_pending",
        description="Generate AI visual descriptions for pending ImageVisualDescriptionResult rows via Gemini.",
    )
    parser.add_argument("--batch-size", type=_positive_int, default=DEFAULT_BATCH_SIZE, help=f"rows claimed per batch (default: {DEFAULT_BATCH_SIZE})")
    parser.add_argument("--limit", type=_positive_int, default=None, help="stop after this many rows total")
    parser.add_argument("--retry-failed", action="store_true", help="also reprocess rows currently marked 'failed'")
    parser.add_argument("--force", action="store_true", help="reprocess ALL 'completed' and 'failed' rows regardless of model-version match")
    args = parser.parse_args(argv)

    settings: Settings = get_settings()
    if not settings.vision_processing_enabled:
        print(
            "Visual description processing is disabled (VISION_PROCESSING_ENABLED is not set to "
            "true in backend/.env). This is an explicit opt-in kill switch, separate from "
            "GEMINI_API_KEY/GEMINI_MODEL -- OCR and text investigations are unaffected either way. "
            "Enable it only after confirming the configured Gemini model actually accepts image "
            "input; see app/vision/gemini_vision.py's own docstring. No rows were touched.",
            file=sys.stderr,
        )
        return 1
    if not (settings.gemini_api_key or "").strip():
        print(
            "No Gemini API key configured -- set GEMINI_API_KEY in backend/.env to enable visual "
            "description processing. No rows were touched -- the API itself is unaffected and "
            "continues to accept and preserve images normally.",
            file=sys.stderr,
        )
        return 1

    counts = process_pending(batch_size=args.batch_size, retry_failed=args.retry_failed, force=args.force, limit=args.limit, storage_root=settings.storage_root)
    total = sum(counts.values())
    print(f"Visual description batch complete: processed={total} completed={counts['completed']} empty={counts['empty']} failed={counts['failed']} skipped={counts['skipped']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
