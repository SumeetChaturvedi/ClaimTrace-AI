"""Independently runnable batch OCR processor (Phase W2.1: Local OCR
Foundation) -- the ONLY place Tesseract is ever invoked in this phase.
Upload/Gmail-sync/WhatsApp-import paths only ever create a `pending`
ImageOcrResult row (see app/ocr/pending.py); this module is what actually
runs OCR against them, on demand, outside any request.

No new CLI framework: a plain stdlib `argparse` entrypoint, run as a
module exactly like this project's own ASGI entrypoint is invoked by
path (`uvicorn app.main:app`) --

    cd backend && source .venv/bin/activate
    python -m app.ocr.process_pending [--batch-size N] [--limit N]
        [--retry-failed] [--force] [--language eng] [--tesseract-cmd PATH]

Concurrency: uses `SELECT ... FOR UPDATE SKIP LOCKED` (mirrors
app/api/routes/investigations.py's own `with_for_update(nowait=True)`
row-locking precedent for a single row; SKIP LOCKED is this module's own
addition, appropriate for claiming a BATCH of rows where some may
already be locked by a concurrent run of this same command, rather than
failing the whole batch over one contended row) to claim a batch and
mark it 'processing' in one short transaction, which commits (and so
releases the lock) BEFORE the actual OCR subprocess calls run -- never
holding a database lock for the duration of a 30-second-capable
subprocess call.

Stale-'processing' recovery -- database-backed lease (final fix; see
below for why the original, simpler design was insufficient): a row
claimed by a run that is then killed (OOM, SIGKILL, host crash, lost DB
connection) before it writes back a final 'completed'/'failed' status is
left in 'processing' with its row lock already released (by design, per
the paragraph above). Such a row is indistinguishable, by status alone,
from one a currently-live invocation is still legitimately working
through -- the lock itself was already released right after the claim,
so "is anyone still holding a lock on it" can't be the test.

The ORIGINAL design (pre-commit review fix, Section 1) used
`processing_started_at < now - STALE_PROCESSING_SECONDS` as the
reclaim test: a single, fixed-age threshold applied to the timestamp an
entire BATCH was stamped with at claim time. That is unsound. Because
`_claim_specific_rows` claims a whole batch at once but
`process_pending` then processes it sequentially, any row queued behind
enough earlier rows -- large `--batch-size`, or slow per-row OCR -- can
age past that fixed threshold before this SAME, still-live invocation
ever reaches it, letting a second, concurrent invocation "reclaim" and
double-process a row the first invocation was still legitimately going
to process. The threshold comment's own claim of safety up to "tens of
thousands of rows" was itself wrong: the real crossover was
`STALE_PROCESSING_SECONDS / OCR_TIMEOUT_SECONDS` rows (60, with the
30-minute/30-second values this module used) -- three orders of
magnitude below what the comment claimed, and no enforced limit stopped
an operator from configuring a larger `--batch-size` anyway.

The ACTUAL, current design replaces that single batch-wide timestamp
check with a per-row lease, independent of batch size or how long
earlier rows in the same batch took:

  - Claiming a row (`_claim_specific_rows`) assigns it a fresh, random
    `lease_token` and a `lease_expires_at` of `now +
    LEASE_DURATION_SECONDS` -- exactly one row's own worst-case
    processing time, never the whole batch's.
  - Immediately before actually working on a specific claimed row (the
    per-row loop in `process_pending`, at the top of
    `_process_claimed_result`), the worker RENEWS that row's own lease
    (`_renew_lease`): a conditional `UPDATE ... WHERE id = :id AND
    lease_token = :token` that extends `lease_expires_at` to a fresh
    `now + LEASE_DURATION_SECONDS`. This is what makes the design
    independent of batch size -- row #500 in a huge batch gets the SAME
    full lease window as row #1, granted at the moment work on IT
    actually starts, not inherited from whenever the whole batch was
    originally claimed. If this renewal fails to match (0 rows --
    another worker already reclaimed this specific row because its
    previous lease had genuinely expired), processing stops immediately
    for this row -- Tesseract is never even invoked for it.
  - Only a 'processing' row whose `lease_expires_at` has actually passed
    (or is NULL -- see `ensure_image_ocr_result_lease_columns`'s own
    docstring) is eligible for reclaim (`_eligibility_clause`'s
    `abandoned_processing` branch). A worker that keeps renewing a row's
    lease never lets it cross that boundary, no matter how long the rest
    of its batch takes.
  - EVERY write this module makes to an already-claimed row --
    renewal, the final 'completed' commit, marking 'failed', restoring a
    preserved previous result -- is a conditional `UPDATE` keyed on
    `lease_token` (`_update_with_lease` / `_apply_lease_scoped_update`).
    If the token no longer matches (a newer worker's claim already
    replaced it), the write matches zero rows, nothing is overwritten,
    and the outcome is reported as 'skipped', never 'completed' or
    'failed' -- a worker that has lost its lease can never clobber a
    result a newer owner already committed, including one committed
    only moments after this worker's own last successful renewal.
  - No row lock is ever held across a renewal or the Tesseract
    subprocess call: each conditional UPDATE commits (and releases its
    lock) immediately, exactly like the original claim transaction.
"""

from __future__ import annotations

import argparse
import logging
import secrets
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import exists, or_, select, update
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.models import EmailAttachment, EmailMessage, ImageOcrResult, ProjectImageAsset, WhatsAppMediaAttachment, WhatsAppMessage
from app.db.session import get_session_factory
from app.ingestion.image_validation import validate_image
from app.ingestion.storage import image_storage_dir, new_storage_key, ocr_text_storage_dir, save_ocr_text, whatsapp_media_dir
from app.ocr.pending import OCR_ELIGIBLE_EXTENSIONS, ensure_pending_ocr_result
from app.ocr.tesseract_provider import OCR_TIMEOUT_SECONDS, get_engine_version, is_tesseract_available, run_ocr

logger = logging.getLogger(__name__)

DEFAULT_BATCH_SIZE = 20

# How long a row's lease stays valid once granted or renewed, before a
# DIFFERENT invocation is allowed to treat it as abandoned and reclaim
# it. This is a PER-ROW window, granted fresh (via _renew_lease) at the
# moment work on that specific row actually begins -- never inherited
# from however long ago the whole batch containing it was originally
# claimed (see the module docstring above for why that distinction is
# what makes this safe regardless of --batch-size). It only needs to
# comfortably outlast ONE row's own worst-case processing time -- the
# Tesseract subprocess call itself (OCR_TIMEOUT_SECONDS) plus the small,
# fixed overhead of resolving/validating the source image and writing
# the result -- not the whole batch's.
LEASE_DURATION_SECONDS = max(120, OCR_TIMEOUT_SECONDS * 4)  # 120s: 4x OCR_TIMEOUT_SECONDS's 30s


@dataclass(frozen=True)
class _ResolvedImage:
    content: bytes
    project_id: int
    filename: str


def _discover_missing_pending_rows(session: Session, *, default_language: str) -> int:
    """Self-healing discovery: find any already-preserved
    ('stored_pending_processing') image whose ImageOcrResult row is
    missing -- e.g. one preserved before this phase existed, or one whose
    ingestion-time ensure_pending_ocr_result() call failed and was
    swallowed (see that function's own docstring) -- and create it now.
    Returns the number of rows created, purely for the run summary."""
    created = 0

    for asset_id in session.scalars(
        select(ProjectImageAsset.id).where(
            ProjectImageAsset.status == "stored_pending_processing",
            ~exists().where(ImageOcrResult.project_image_asset_id == ProjectImageAsset.id),
        )
    ).all():
        ensure_pending_ocr_result(session, project_image_asset_id=asset_id, default_language=default_language)
        created += 1

    for attachment_id in session.scalars(
        select(EmailAttachment.id).where(
            EmailAttachment.status == "stored_pending_processing",
            ~exists().where(ImageOcrResult.email_attachment_id == EmailAttachment.id),
        )
    ).all():
        ensure_pending_ocr_result(session, email_attachment_id=attachment_id, default_language=default_language)
        created += 1

    # WhatsApp: image-only -- never create an OCR row for preserved
    # audio/video/other media, exactly like the ingestion-time check in
    # app/whatsapp_ingestion/pipeline.py.
    for attachment_id in session.scalars(
        select(WhatsAppMediaAttachment.id).where(
            WhatsAppMediaAttachment.status == "stored_pending_processing",
            WhatsAppMediaAttachment.detected_extension.in_(OCR_ELIGIBLE_EXTENSIONS),
            ~exists().where(ImageOcrResult.whatsapp_media_attachment_id == WhatsAppMediaAttachment.id),
        )
    ).all():
        ensure_pending_ocr_result(session, whatsapp_media_attachment_id=attachment_id, default_language=default_language)
        created += 1

    return created


def _eligibility_clause(
    *,
    retry_failed: bool,
    force: bool,
    current_engine_version: str | None,
    current_language: str,
    now: datetime,
):
    """The single source of truth for "is this row eligible to be
    (re)processed right now", reused by BOTH _list_eligible_ids (the
    initial, unlocked snapshot) and _claim_specific_rows (which re-
    applies this SAME condition at claim time -- see that function's own
    docstring for why re-checking it there, not just checking `id IN
    (...)`, is essential for correctness under real concurrency).

    The stale-'processing' branch is ALWAYS included, regardless of
    --retry-failed/--force -- unlike those two flags, which only ever
    widen what's eligible when explicitly asked for, recovering
    genuinely abandoned work is a baseline correctness guarantee, not an
    opt-in retry mode. A row only qualifies once its LEASE has actually
    expired (`lease_expires_at < now`, or is NULL -- see
    ensure_image_ocr_result_lease_columns's own docstring for why NULL is
    treated as already-expired), never merely because
    `processing_started_at` is old: a live invocation renews a row's
    lease (_renew_lease) at the moment it actually starts working on
    it, so a row it is still genuinely processing never crosses this
    boundary, regardless of batch size (see module docstring)."""
    completed_is_stale = (ImageOcrResult.status == "completed") & (
        (ImageOcrResult.ocr_engine_version.is_distinct_from(current_engine_version))
        | (ImageOcrResult.ocr_language != current_language)
    )
    abandoned_processing = (ImageOcrResult.status == "processing") & (
        ImageOcrResult.lease_expires_at.is_(None) | (ImageOcrResult.lease_expires_at < now)
    )

    eligible = [ImageOcrResult.status == "pending", abandoned_processing]
    if retry_failed or force:
        eligible.append(ImageOcrResult.status == "failed")
    if force:
        eligible.append(ImageOcrResult.status == "completed")
    else:
        eligible.append(completed_is_stale)
    return or_(*eligible)


def _list_eligible_ids(
    session: Session,
    *,
    retry_failed: bool,
    force: bool,
    current_engine_version: str | None,
    current_language: str,
    limit: int | None,
    now: datetime,
) -> list[int]:
    """A FIXED snapshot of currently-eligible row ids, taken once at the
    start of a run (see process_pending's own docstring for why this
    must be a snapshot, not re-queried after each batch): with --force,
    a 'completed' row stays eligible by this same WHERE clause even
    seconds after this run itself just completed it -- re-querying the
    live eligibility condition after every batch would claim that same
    row again, forever. Iterating a fixed snapshot instead bounds one
    invocation to processing each originally-eligible row exactly once,
    while still letting a LATER, separate invocation reprocess it.

    `now` is captured once by the caller (process_pending) and threaded
    through to here and to _claim_specific_rows, so both the snapshot and
    the re-check at claim time agree on the same reference instant for
    staleness -- never recomputed mid-run."""
    clause = _eligibility_clause(
        retry_failed=retry_failed,
        force=force,
        current_engine_version=current_engine_version,
        current_language=current_language,
        now=now,
    )
    query = select(ImageOcrResult.id).where(clause).order_by(ImageOcrResult.id)
    if limit is not None:
        query = query.limit(limit)
    return list(session.scalars(query).all())


def _claim_specific_rows(
    session: Session,
    candidate_ids: list[int],
    *,
    retry_failed: bool,
    force: bool,
    current_engine_version: str | None,
    current_language: str,
    now: datetime,
) -> list[tuple[int, str]]:
    """Attempt to claim exactly these ids (a slice of the fixed
    eligibility snapshot above), marking whichever ones this invocation
    actually acquires the lock on as 'processing' with a fresh lease, and
    commit -- a short transaction that releases the row locks
    immediately, before any OCR subprocess runs. Returns each claimed
    row's id paired with the fresh `lease_token` it was just assigned --
    the caller must present that exact token back to every later
    renewal/commit for that row (see module docstring).

    Re-applies the SAME eligibility condition used to build the initial
    snapshot, not just `id IN (candidate_ids)` -- essential under real
    concurrency: by the time this runs, a sibling invocation may have
    already claimed AND FINISHED one of these ids (moving it to
    'completed'/'failed' and releasing its lock) between this run's own
    snapshot and this claim attempt. Without re-checking eligibility
    here, that already-finished row would still be sitting unlocked and
    would be claimed and reprocessed a second time, the exact double-
    processing this function exists to prevent. SKIP LOCKED additionally
    means a candidate still genuinely eligible but presently
    row-locked by a sibling invocation's own, not-yet-committed claim is
    silently skipped here too (comes back empty for THIS call), never
    waited on."""
    if not candidate_ids:
        return []

    clause = _eligibility_clause(
        retry_failed=retry_failed,
        force=force,
        current_engine_version=current_engine_version,
        current_language=current_language,
        now=now,
    )
    claimed_rows = session.execute(
        select(ImageOcrResult.id, ImageOcrResult.status)
        .where(ImageOcrResult.id.in_(candidate_ids), clause)
        .order_by(ImageOcrResult.id)
        .with_for_update(skip_locked=True)
    ).all()
    if not claimed_rows:
        return []

    claimed_ids = [row_id for row_id, _status in claimed_rows]
    reclaimed_ids = [row_id for row_id, row_status in claimed_rows if row_status == "processing"]
    if reclaimed_ids:
        logger.warning(
            "Reclaiming %d ImageOcrResult row(s) whose lease had expired: %s",
            len(reclaimed_ids),
            reclaimed_ids,
        )

    claim_time = datetime.now(timezone.utc)
    lease_expiry = claim_time + timedelta(seconds=LEASE_DURATION_SECONDS)
    # Each row gets its OWN fresh, random token -- not one token shared
    # across the whole batch -- so a later renewal/commit for one row can
    # never be satisfied by a token that was actually granted for a
    # different row.
    lease_tokens: dict[int, str] = {row_id: secrets.token_hex(16) for row_id in claimed_ids}
    for row_id in claimed_ids:
        session.execute(
            update(ImageOcrResult)
            .where(ImageOcrResult.id == row_id)
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


def _resolve_source_image(session: Session, result: ImageOcrResult, storage_root: Path) -> _ResolvedImage | None:
    """Resolve the real, on-disk preserved original for one OCR result's
    single parent source, verifying along the way that the row is still
    a genuinely eligible, preserved image and that the resolved path
    stays inside this application's own storage root -- never trusting
    `storage_key` alone, even though it is always server-generated."""
    file_path: Path
    filename: str
    project_id: int

    if result.project_image_asset_id is not None:
        asset = session.get(ProjectImageAsset, result.project_image_asset_id)
        if asset is None or asset.status != "stored_pending_processing":
            return None
        if not asset.storage_key or not asset.detected_extension or asset.detected_extension not in OCR_ELIGIBLE_EXTENSIONS:
            return None
        project_id = asset.project_id
        filename = asset.filename
        file_path = image_storage_dir(storage_root, project_id) / f"{asset.storage_key}{asset.detected_extension}"

    elif result.email_attachment_id is not None:
        attachment = session.get(EmailAttachment, result.email_attachment_id)
        if attachment is None or attachment.status != "stored_pending_processing":
            return None
        if not attachment.storage_key or not attachment.detected_extension or attachment.detected_extension not in OCR_ELIGIBLE_EXTENSIONS:
            return None
        message = session.get(EmailMessage, attachment.message_id)
        if message is None:
            return None
        project_id = message.project_id
        filename = attachment.filename
        file_path = image_storage_dir(storage_root, project_id) / f"{attachment.storage_key}{attachment.detected_extension}"

    elif result.whatsapp_media_attachment_id is not None:
        attachment = session.get(WhatsAppMediaAttachment, result.whatsapp_media_attachment_id)
        if attachment is None or attachment.status != "stored_pending_processing":
            return None
        if not attachment.storage_key or not attachment.detected_extension or attachment.detected_extension not in OCR_ELIGIBLE_EXTENSIONS:
            return None
        message = session.get(WhatsAppMessage, attachment.message_id)
        if message is None:
            return None
        project_id = message.project_id
        filename = attachment.filename
        file_path = whatsapp_media_dir(storage_root, project_id) / f"{attachment.storage_key}{attachment.detected_extension}"

    else:
        return None

    resolved_root = storage_root.resolve()
    resolved_path = file_path.resolve()
    if resolved_path != resolved_root and not resolved_path.is_relative_to(resolved_root):
        logger.warning("Resolved OCR source path escaped the storage root for ImageOcrResult id=%s; refusing to read it", result.id)
        return None
    if not resolved_path.is_file():
        return None

    try:
        content = resolved_path.read_bytes()
    except OSError as exc:
        logger.warning("Could not read preserved image for ImageOcrResult id=%s: %s", result.id, exc)
        return None

    return _ResolvedImage(content=content, project_id=project_id, filename=filename)


def _safe_unlink_ocr_text(path_str: str | None, storage_root: Path) -> None:
    """Remove one OCR text file, but ONLY if its resolved path actually
    stays inside storage_root/ocr_text -- the same defense-in-depth
    containment check _resolve_source_image already applies to the
    original images it reads, applied here too before any deletion.
    Never raises: a path outside the expected root, or any OSError while
    unlinking, is logged and otherwise ignored -- this is always
    best-effort cleanup of a file that is, either way, no longer
    referenced by any row."""
    if not path_str:
        return
    try:
        resolved = Path(path_str).resolve()
        allowed_root = (storage_root / "ocr_text").resolve()
        if resolved != allowed_root and not resolved.is_relative_to(allowed_root):
            logger.warning("Refusing to delete OCR text path outside the expected storage root: %s", path_str)
            return
        resolved.unlink(missing_ok=True)
    except OSError as exc:
        logger.warning("Could not remove old OCR text file %s: %s", path_str, exc)


def _update_with_lease(session: Session, result_id: int, lease_token: str, values: dict) -> int:
    """The ONLY way this module ever writes a status onto an
    already-claimed row: a conditional `UPDATE ... WHERE id = :id AND
    lease_token = :lease_token`. Returns the number of matched rows (0
    or 1) -- 0 means this worker no longer owns the row (a newer
    worker's claim already replaced its lease_token, or the row no
    longer exists), in which case `values` were never applied and
    nothing already written by that newer owner was overwritten.
    Callers decide what a 0 means for their own return value (always
    'skipped', never 'failed'/'completed' -- see _process_claimed_result).
    Does not commit; callers control the transaction boundary."""
    result = session.execute(update(ImageOcrResult).where(ImageOcrResult.id == result_id, ImageOcrResult.lease_token == lease_token).values(**values))
    return result.rowcount


def _renew_lease(session: Session, result_id: int, lease_token: str) -> bool:
    """Confirm this worker still owns result_id's lease and extend it
    fresh to `now + LEASE_DURATION_SECONDS` -- called once, right before
    actually starting work on this specific row (see module docstring
    for why this, not the original batch-wide claim time, is what makes
    the lease window independent of --batch-size). Returns False (lease
    already lost) if the token no longer matches, in which case the
    caller must not invoke Tesseract or write any result for this row.

    A database error while attempting the renewal is treated the same
    as a lost lease -- a safe, conservative default: this is a
    non-destructive check, so declining to proceed on an unexpected
    error can never corrupt anything, while proceeding on an
    unverified renewal could."""
    try:
        rowcount = _update_with_lease(
            session,
            result_id,
            lease_token,
            {"lease_expires_at": datetime.now(timezone.utc) + timedelta(seconds=LEASE_DURATION_SECONDS)},
        )
        session.commit()
    except Exception as exc:  # noqa: BLE001 -- deliberately broad: any failure here means "do not proceed", logged below
        session.rollback()
        logger.warning("ImageOcrResult id=%s: lease renewal failed (%s) -- treating as lease lost", result_id, exc)
        return False
    return rowcount == 1


def _apply_lease_scoped_update(session: Session, result_id: int, lease_token: str, values: dict, *, context: str) -> bool:
    """Apply `values` to result_id's row via `_update_with_lease` and
    commit. Returns True if this worker still owned the lease at the
    moment of the write (the update actually applied), False if it had
    already been lost -- 0 rows matched, so `values` were never written
    and nothing a newer owner already committed was overwritten. Callers
    must treat False as 'skipped', never as this attempt having
    succeeded OR failed on this worker's own terms.

    On a genuine database error while applying `values`: rolls back and
    retries with a minimal, STILL lease-scoped 'failed' status instead
    (same recovery this function replaces: see the module's earlier
    _commit_or_raise design). Raises ONLY if that fallback ALSO fails --
    two consecutive commit failures for the same row strongly suggest a
    genuine, ongoing database outage rather than a one-off blip."""
    try:
        rowcount = _update_with_lease(session, result_id, lease_token, values)
        session.commit()
        return rowcount == 1
    except Exception as exc:  # noqa: BLE001 -- narrow, deliberate, logged, with a bounded re-raise below
        session.rollback()
        logger.warning("ImageOcrResult id=%s commit failed (%s): %s", result_id, context, exc)
        try:
            rowcount = _update_with_lease(
                session,
                result_id,
                lease_token,
                {
                    "status": "failed",
                    "error": f"commit failed ({context}): {exc}",
                    "processed_at": datetime.now(timezone.utc),
                    "lease_token": None,
                    "lease_expires_at": None,
                },
            )
            session.commit()
            return rowcount == 1
        except Exception as second_exc:  # noqa: BLE001 -- see docstring: a second failure here is reported, not swallowed
            session.rollback()
            logger.error(
                "ImageOcrResult id=%s: a SECOND consecutive commit failure (%s) after the first (%s) -- "
                "this looks like a genuine database outage, not a one-off blip. Stopping this run rather "
                "than silently reporting further rows as processed under an unverifiable database state.",
                result_id,
                second_exc,
                exc,
            )
            raise


def _process_claimed_result(
    session: Session,
    storage_root: Path,
    result_id: int,
    lease_token: str,
    *,
    language: str,
    tesseract_cmd: str | None,
) -> str:
    """Process exactly one already-claimed ('processing') row, using
    `lease_token` (as returned by _claim_specific_rows for this row) to
    prove ownership of it throughout. Returns one of 'completed',
    'empty', 'failed', 'skipped' for the run summary -- 'skipped' now
    also covers "lost the lease to a newer worker", not just "row
    vanished before we got to it"; either way, this invocation made no
    change to the row's final outcome.

    Renews its lease once, immediately, via _renew_lease -- if that
    fails (another worker already reclaimed this row because this
    worker's previous lease on it had genuinely expired), returns
    'skipped' without ever invoking Tesseract. This is what keeps the
    lease window per-row rather than inherited from the whole batch's
    original claim time (see module docstring).

    Previous-result preservation (pre-commit review fix, Section 2): if
    this row already held a real, previously-'completed' result (e.g. a
    --force or engine/language-change reprocess attempt), a failure in
    the NEW OCR attempt itself, or in committing its result, restores
    that previous, still-valid result and file rather than destroying
    it. A row with no previous completed result (first-ever attempt, or
    reprocessing a previously-'failed' one) has nothing valid to
    preserve, so those cases are simply recorded as 'failed' with the
    new, current error.

    Every status-setting write in this function goes through
    _apply_lease_scoped_update, so a database failure on ANY of them is
    isolated to this one row, AND every one of them is conditioned on
    still owning `lease_token` -- a worker that loses the race at any
    point past the initial renewal reports 'skipped' for this row rather
    than overwriting whatever a newer worker has since committed."""
    result = session.get(ImageOcrResult, result_id)
    if result is None:
        return "skipped"

    # Captured BEFORE any mutation below -- plain Python values, never
    # affected by a later session.rollback() the way ORM-tracked
    # attributes on `result` itself would be.
    #
    # NOT `result.status == "completed"`: by the time this function runs,
    # _claim_specific_rows has ALREADY overwritten this row's status to
    # 'processing' (that UPDATE deliberately never touches
    # ocr_text_path/ocr_engine_version/ocr_language, only status/
    # processing_started_at/error/lease_token/lease_expires_at) -- so
    # status alone can never distinguish "first-ever attempt" from
    # "reprocessing a previously completed row" at this point.
    # ocr_text_path being non-null is the right signal: it is only ever
    # set once, by a real, previously successful OCR run, and never
    # cleared by the claim step.
    previous_text_path = result.ocr_text_path
    previous_engine_version = result.ocr_engine_version
    previous_language = result.ocr_language
    had_previous_completed_result = previous_text_path is not None

    if not _renew_lease(session, result_id, lease_token):
        logger.warning(
            "ImageOcrResult id=%s: lease already lost before processing could begin (a newer worker "
            "reclaimed it after its lease expired) -- skipping without invoking Tesseract",
            result_id,
        )
        return "skipped"

    def _mark_failed(error: str, *, engine_version: str | None = None) -> str:
        values: dict = {
            "status": "failed",
            "error": error,
            "processed_at": datetime.now(timezone.utc),
            "lease_token": None,
            "lease_expires_at": None,
        }
        if engine_version is not None:
            values["ocr_engine_version"] = engine_version
        owned = _apply_lease_scoped_update(session, result_id, lease_token, values, context="marking failed")
        return "failed" if owned else "skipped"

    def _restore_previous_completed_result(reason: str) -> str:
        logger.warning("ImageOcrResult id=%s: %s -- preserving its previous completed result", result_id, reason)
        values = {
            "status": "completed",
            "ocr_text_path": previous_text_path,
            "ocr_engine_version": previous_engine_version,
            "ocr_language": previous_language,
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

    # Reapply the existing image validation before OCR -- defense in
    # depth, never trusting that a file on disk still matches what was
    # true when it was first preserved.
    validation = validate_image(resolved.content)
    if not validation.valid:
        return _mark_failed(f"image failed re-validation before OCR: {validation.error}")

    ocr_outcome = run_ocr(resolved.content, language=language, tesseract_cmd=tesseract_cmd)
    if ocr_outcome.status != "completed":
        if had_previous_completed_result:
            return _restore_previous_completed_result(f"a reprocess OCR attempt failed ({ocr_outcome.error})")
        return _mark_failed(ocr_outcome.error, engine_version=ocr_outcome.engine_version)

    # Safe replacement sequence: write the NEW candidate text file under
    # its own fresh, server-generated key FIRST -- the OLD file (if any)
    # is never touched yet, so a failure from here on can always fall
    # back to it untouched. The write itself can fail too (disk full,
    # permissions) -- nothing has been committed or deleted yet at this
    # point, so there is nothing to roll back or clean up, only the same
    # restore-or-mark-failed decision as every other failure point here.
    storage_key = new_storage_key(resolved.filename)
    try:
        new_text_path = save_ocr_text(storage_root, resolved.project_id, storage_key, ocr_outcome.text or "")
    except OSError as exc:
        logger.warning("ImageOcrResult id=%s: could not write OCR text file: %s", result_id, exc)
        if had_previous_completed_result:
            return _restore_previous_completed_result(f"could not write the new OCR text file ({exc})")
        return _mark_failed(f"could not write OCR text file: {exc}")

    final_values = {
        "ocr_text_path": str(new_text_path),
        "ocr_engine_version": ocr_outcome.engine_version,
        "ocr_language": language,
        "status": "completed",
        "error": None,
        "processed_at": datetime.now(timezone.utc),
        "lease_token": None,
        "lease_expires_at": None,
    }
    try:
        rowcount = _update_with_lease(session, result_id, lease_token, final_values)
        session.commit()
    except Exception as exc:  # noqa: BLE001 -- compensating cleanup for the candidate file just written above
        session.rollback()
        new_text_path.unlink(missing_ok=True)  # never committed to any row -- always safe to discard
        logger.warning(
            "ImageOcrResult id=%s commit failed after writing candidate OCR text %s; removed it: %s",
            result_id,
            new_text_path,
            exc,
        )
        if had_previous_completed_result:
            return _restore_previous_completed_result(f"commit failed after a successful reprocess OCR run ({exc})")
        return _mark_failed(f"commit failed after a successful OCR run: {exc}")

    if rowcount == 0:
        # Lease lost between the renewal above and this final commit -- a
        # newer worker's claim already replaced lease_token, meaning IT
        # now owns (or has already finished) this row. Discard this
        # worker's own just-written candidate file without touching
        # previous_text_path or whatever the newer worker may itself have
        # already written -- never overwrite a result this worker no
        # longer owns.
        new_text_path.unlink(missing_ok=True)
        logger.warning(
            "ImageOcrResult id=%s: lease lost before the final commit could apply -- discarding this "
            "worker's OCR result without overwriting whatever a newer worker already committed",
            result_id,
        )
        return "skipped"

    # The new result is durably committed -- only NOW is it safe to
    # remove the OLD text file, and only if reprocessing actually
    # produced a different one.
    if previous_text_path and previous_text_path != str(new_text_path):
        _safe_unlink_ocr_text(previous_text_path, storage_root)

    return "empty" if not (ocr_outcome.text or "").strip() else "completed"


def process_pending(
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
    retry_failed: bool = False,
    force: bool = False,
    limit: int | None = None,
    language: str,
    tesseract_cmd: str | None,
    storage_root: Path,
) -> dict[str, int]:
    """Run one full batch-processing pass: discover any preserved image
    missing its OCR row, then repeatedly claim and process batches until
    nothing eligible remains or `limit` is reached. Assumes the caller
    has already confirmed Tesseract is available (see main() below) --
    this function does not itself decide whether to run at all, only how
    to process what it's asked to.

    Raises ValueError (before any database query) for a non-positive
    batch_size/limit -- main() validates CLI input before ever reaching
    this function, but this function defends itself too, since it's a
    public entry point other callers (tests, future scripts) can invoke
    directly with values main()'s own parsing never saw."""
    if batch_size <= 0:
        raise ValueError(f"batch_size must be a positive integer, got {batch_size}")
    if limit is not None and limit <= 0:
        raise ValueError(f"limit must be a positive integer when given, got {limit}")

    counts = {"completed": 0, "empty": 0, "failed": 0, "skipped": 0}
    current_engine_version = get_engine_version(tesseract_cmd=tesseract_cmd)
    now = datetime.now(timezone.utc)

    session_factory = get_session_factory()
    with session_factory() as session:
        discovered = _discover_missing_pending_rows(session, default_language=language)
        if discovered:
            logger.info("Discovered %d preserved image(s) with no OCR result row; created pending rows for them", discovered)

        eligible_ids = _list_eligible_ids(
            session,
            retry_failed=retry_failed,
            force=force,
            current_engine_version=current_engine_version,
            current_language=language,
            limit=limit,
            now=now,
        )

        for batch_start in range(0, len(eligible_ids), batch_size):
            candidate_ids = eligible_ids[batch_start : batch_start + batch_size]
            claimed = _claim_specific_rows(
                session,
                candidate_ids,
                retry_failed=retry_failed,
                force=force,
                current_engine_version=current_engine_version,
                current_language=language,
                now=now,
            )
            for result_id, lease_token in claimed:
                outcome = _process_claimed_result(
                    session, storage_root, result_id, lease_token, language=language, tesseract_cmd=tesseract_cmd
                )
                counts[outcome] = counts.get(outcome, 0) + 1

    return counts


def _positive_int(raw: str) -> int:
    """argparse `type=` validator shared by --batch-size and --limit:
    rejects zero, negative, and non-integer values with a concise
    argparse-native error (argparse catches ValueError from a `type=`
    callable itself and exits with status 2 after printing a clean
    usage message -- no database query or row mutation has happened by
    this point, since this runs during parse_args(), before main() does
    anything else)."""
    try:
        value = int(raw)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{raw!r} is not an integer")
    if value <= 0:
        raise argparse.ArgumentTypeError(f"must be a positive integer, got {value}")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.ocr.process_pending",
        description="Process pending ImageOcrResult rows via local Tesseract OCR. "
        "Never run automatically during upload/Gmail-sync/WhatsApp-import -- this is the "
        "only place those rows are actually OCR'd.",
    )
    parser.add_argument(
        "--batch-size", type=_positive_int, default=DEFAULT_BATCH_SIZE, help=f"rows claimed per batch, a positive integer (default: {DEFAULT_BATCH_SIZE})"
    )
    parser.add_argument(
        "--limit", type=_positive_int, default=None, help="stop after this many rows total, a positive integer (default: process all eligible rows)"
    )
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="also reprocess rows currently marked 'failed' (without this, a failed row is left alone on future runs)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="reprocess ALL 'completed' and 'failed' rows regardless of engine-version/language match "
        "(without this, a 'completed' row is only reprocessed when the configured engine version or "
        "language has changed since it last ran)",
    )
    parser.add_argument("--language", default=None, help="override the configured OCR language (settings.ocr_language) for this run")
    parser.add_argument("--tesseract-cmd", default=None, help="override the configured Tesseract executable path (settings.tesseract_cmd) for this run")
    args = parser.parse_args(argv)

    settings: Settings = get_settings()
    language = args.language or settings.ocr_language
    tesseract_cmd = args.tesseract_cmd or settings.tesseract_cmd

    if not is_tesseract_available(tesseract_cmd=tesseract_cmd):
        print(
            f"Tesseract executable not found (looked for {tesseract_cmd or 'tesseract'!r} on PATH). "
            "No rows were touched -- install it (macOS: `brew install tesseract`; "
            "Debian/Ubuntu: `apt-get install tesseract-ocr`) and re-run this command. "
            "The API itself is unaffected and continues to accept and preserve images normally.",
            file=sys.stderr,
        )
        return 1

    counts = process_pending(
        batch_size=args.batch_size,
        retry_failed=args.retry_failed,
        force=args.force,
        limit=args.limit,
        language=language,
        tesseract_cmd=tesseract_cmd,
        storage_root=settings.storage_root,
    )
    total = sum(counts.values())
    print(
        f"OCR batch complete: processed={total} completed={counts['completed']} "
        f"empty={counts['empty']} failed={counts['failed']} skipped={counts['skipped']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
