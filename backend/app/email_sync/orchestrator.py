"""Manual sync orchestrator (Phase 1: Gmail Integration) — the thin layer
that turns "a page of Gmail message ids" into calls to the EXISTING,
completely unmodified `ingest_email_bytes()` (app/email_ingestion/
pipeline.py). This module owns NONE of parsing, deduplication, threading,
document indexing, or attachment ingestion — it only decides WHICH raw
bytes to fetch and feeds them into that one call, exactly like
project_emails.py's manual `.eml`/ZIP upload route already does.

No background scheduler, no webhooks (out of scope for Phase 1) — this
runs synchronously inside one "Sync now" HTTP request, bounded by
MAX_MESSAGES_PER_CALL/MAX_PAGES_PER_CALL so a single click can't hang the
request indefinitely against a very large mailbox.

Cursor encoding (ConnectedMailbox.sync_cursor, a single Text column, no
new schema needed):
  - None            -> never synced, or a previous historyId expired and a
                       fresh full sync is required
  - "page:<token>"  -> a full listing was started but not finished within
                       one call; resume from this Gmail pageToken
  - "history:<id>"  -> at least one full sync has completed; <id> is the
                       Gmail historyId baseline for incremental sync

Safety invariant this module depends on, not reimplements: dedup
(Message-ID / content_hash, enforced inside ingest_email_bytes() itself,
backed by real DB unique constraints) makes re-processing an
already-imported message from a stale/rewound cursor always safe — it
comes back as a 'duplicate' outcome, never a second row. This is what
lets a failed batch be retried without duplicating messages: on any
mid-run failure, the cursor is simply left unchanged (or at its
last-fully-confirmed value) rather than attempting to compute a "partial
credit" cursor, and the next sync call safely re-covers the same ground.

Design decision, made deliberately and not changed by the Phase 1 code
review passes (documented here so it isn't mistaken for an oversight):
once a full listing reaches its natural end, `status="completed"` is
returned WITHOUT this same call immediately replaying history.list from
the just-captured baseline to "catch up" on anything that arrived DURING
that full listing. Recovery of such a message is deferred to the NEXT
manual sync call, which starts from that exact baseline and is guaranteed
to find it (see the correctness fix in _collect_message_ids below for
why the baseline is captured BEFORE listing begins). This is safe — never
a permanent loss, never a duplicate — but it means "completed" describes
"this listing operation reached its end," not "the mailbox is now
provably 100% in sync at this instant." Nothing in this module's own API
(SyncResult) or the frontend's copy claims the stronger guarantee, so a
same-call catch-up isn't required to meet the product's own documented
contract; it would add real complexity (an extra, budget-consuming
history.list pass inside the same bounded HTTP request) for a gap that
already self-heals on the very next "Sync now" click. See
FullSyncHistoryBaselineTests/DeferredRecoveryTests in
tests/test_mailbox_sync.py for the behavior this paragraph describes,
proven end-to-end rather than only asserted here.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import ConnectedMailbox
from app.email_ingestion.pipeline import ingest_email_bytes
from app.email_sync import gmail_source
from app.email_sync.gmail_oauth import (
    GmailCredentialsRevokedError,
    GmailOAuthError,
    GmailTransientError,
    refresh_access_token,
)
from app.email_sync.gmail_source import (
    GmailApiError,
    GmailAuthError,
    GmailMessageNotFoundError,
    HistoryExpiredError,
)
from app.email_sync.token_crypto import (
    TokenDecryptionError,
    TokenEncryptionNotConfigured,
    decrypt_refresh_token,
)

logger = logging.getLogger(__name__)

MAX_MESSAGES_PER_CALL = 200
MAX_PAGES_PER_CALL = 10


class MailboxNotSyncableError(Exception):
    """Raised before any Gmail API call for a mailbox that structurally
    cannot be synced right now (disconnected, or encryption unavailable)
    — distinct from a Gmail-side failure, so callers never confuse "we
    didn't even try" with "we tried and Google rejected it"."""


@dataclass(frozen=True)
class SyncResult:
    status: str  # 'completed' | 'partial' | 'needs_reauth' | 'error'
    imported: int = 0
    duplicate: int = 0
    rejected: int = 0
    skipped_not_found: int = 0
    error: str | None = None


def sync_mailbox(
    session: Session,
    storage_root: Path,
    mailbox: ConnectedMailbox,
    settings: Settings,
) -> SyncResult:
    """Run one bounded manual sync pass for `mailbox`. Never raises for a
    Gmail-side or credential failure — those are reported via
    SyncResult.status/.error, exactly like ingest_email_bytes() itself
    never raises for a processing (as opposed to validation) failure.
    Only raises MailboxNotSyncableError for a precondition this caller
    should have already checked (mailbox disconnected)."""
    if mailbox.status == "disconnected" or not mailbox.encrypted_refresh_token:
        raise MailboxNotSyncableError("This mailbox is disconnected and has no stored credentials to sync with")

    try:
        refresh_token = decrypt_refresh_token(mailbox.encrypted_refresh_token, settings)
    except (TokenEncryptionNotConfigured, TokenDecryptionError) as exc:
        mailbox.last_sync_error = str(exc)
        session.commit()
        return SyncResult(status="error", error=str(exc))

    try:
        access_token, _ = refresh_access_token(settings, refresh_token)
    except GmailCredentialsRevokedError as exc:
        mailbox.status = "needs_reauth"
        mailbox.last_sync_error = str(exc)
        session.commit()
        return SyncResult(status="needs_reauth", error=str(exc))
    except (GmailTransientError, GmailOAuthError) as exc:
        mailbox.last_sync_error = str(exc)
        session.commit()
        return SyncResult(status="error", error=str(exc))

    try:
        message_ids, new_cursor, fully_listed = _collect_message_ids(access_token, mailbox.sync_cursor)
    except GmailAuthError as exc:
        # The access token we just minted was rejected by the Gmail API
        # itself (distinct from the token endpoint) — treat as a hard
        # stop for this attempt rather than looping; a second "Sync now"
        # click gets a fresh access_token from the refresh above.
        mailbox.last_sync_error = str(exc)
        session.commit()
        return SyncResult(status="error", error=str(exc))
    except GmailTransientError as exc:
        # Code review fix: a 429/5xx/network failure during profile
        # retrieval, full-list pagination, or history listing (all three
        # funnel through this one call to _collect_message_ids) was
        # previously left uncaught here — GmailTransientError extends
        # GmailOAuthError, a completely separate hierarchy from
        # GmailApiError/GmailAuthError below, so neither existing except
        # clause matched it, and it escaped as an unhandled exception,
        # violating this function's own documented contract ("Never
        # raises for a Gmail-side... failure"). Reported as a plain
        # status="error" — explicitly NOT 'needs_reauth': a rate limit or
        # a transient server/network blip says nothing about whether the
        # stored credentials are still valid, and reauthorizing with
        # Google would do nothing to fix it. mailbox.sync_cursor is left
        # completely untouched (we never reach the assignment below), so
        # a retry safely re-lists exactly the same range.
        mailbox.last_sync_error = str(exc)
        session.commit()
        return SyncResult(status="error", error=str(exc))
    except GmailApiError as exc:
        mailbox.last_sync_error = str(exc)
        session.commit()
        return SyncResult(status="error", error=str(exc))

    counts = _IngestCounts()
    stopped_early = False
    stop_reason: str | None = None

    for message_id in message_ids:
        try:
            raw = gmail_source.fetch_raw_message(access_token, message_id)
        except GmailMessageNotFoundError:
            counts.skipped_not_found += 1
            continue
        except (GmailAuthError, GmailApiError, GmailTransientError) as exc:
            stopped_early = True
            stop_reason = str(exc)
            break

        outcome = ingest_email_bytes(
            session=session,
            storage_root=storage_root,
            project_id=mailbox.project_id,
            source_name=f"gmail:{mailbox.external_email}:{message_id}",
            raw_bytes=raw.raw_bytes,
        )
        counts.record(outcome.status)

    # Only advance the cursor when the listing itself was not cut short by
    # a mid-message failure — on `stopped_early`, the cursor is left at
    # its PREVIOUS value (mailbox.sync_cursor, unchanged) rather than
    # `new_cursor`, so the next sync call re-lists (and, thanks to dedup,
    # safely re-skips) exactly the same range instead of silently moving
    # past messages this call never actually fetched.
    if not stopped_early:
        mailbox.sync_cursor = new_cursor

    mailbox.last_synced_at = datetime.now(timezone.utc)
    mailbox.last_sync_error = stop_reason
    session.commit()

    if stopped_early:
        return SyncResult(
            status="partial",
            imported=counts.imported,
            duplicate=counts.duplicate,
            rejected=counts.rejected,
            skipped_not_found=counts.skipped_not_found,
            error=stop_reason,
        )

    return SyncResult(
        status="completed" if fully_listed else "partial",
        imported=counts.imported,
        duplicate=counts.duplicate,
        rejected=counts.rejected,
        skipped_not_found=counts.skipped_not_found,
    )


@dataclass
class _IngestCounts:
    imported: int = 0
    duplicate: int = 0
    rejected: int = 0
    skipped_not_found: int = 0

    def record(self, outcome_status: str) -> None:
        if outcome_status == "imported":
            self.imported += 1
        elif outcome_status == "duplicate":
            self.duplicate += 1
        elif outcome_status == "rejected":
            self.rejected += 1


def _collect_message_ids(access_token: str, cursor: str | None) -> tuple[list[str], str | None, bool]:
    """Return (message_ids, new_cursor, fully_listed) for one bounded sync
    pass. `fully_listed` is True only when this call reached the natural
    end of whatever it was listing (no more pages) — False means the
    MAX_MESSAGES_PER_CALL/MAX_PAGES_PER_CALL bound was hit first and a
    further "Sync now" click is needed to finish this range."""
    if cursor is None:
        # Correctness fix (code review): the historyId baseline for every
        # future incremental sync MUST be captured BEFORE the full listing
        # starts, not after. A message that arrives DURING a multi-page
        # (or just slow) full sync can otherwise be missed entirely: it
        # may never appear in the listing itself (messages.list typically
        # returns newest-first, so a message arriving after we've already
        # fetched the first page is simply never seen by this call), and
        # a baseline captured AFTER listing completes is already past that
        # message's own history entry — so the next incremental sync,
        # which only returns changes strictly after its startHistoryId,
        # would never surface it either. Capturing the baseline first
        # guarantees the opposite, safe direction: anything that arrives
        # during or after the full listing has a history entry AT OR AFTER
        # this baseline, so the very next incremental sync will catch it
        # even if this particular full listing happened to miss it.
        baseline_history_id = gmail_source.fetch_profile(access_token).history_id
        return _collect_full_listing(access_token, baseline_history_id=baseline_history_id, page_token=None)

    if cursor.startswith("page:"):
        # Carries the SAME baseline forward across however many "Sync now"
        # clicks it takes to finish one full listing — never re-captured
        # mid-listing, which would reopen the exact gap just described.
        baseline_history_id, _, page_token = cursor[len("page:"):].partition(":")
        return _collect_full_listing(
            access_token, baseline_history_id=baseline_history_id, page_token=page_token or None
        )

    if cursor.startswith("history:"):
        history_id = cursor[len("history:"):]
        try:
            return _collect_incremental(access_token, start_history_id=history_id)
        except HistoryExpiredError:
            logger.info("Gmail history cursor expired; falling back to a fresh full sync")
            baseline_history_id = gmail_source.fetch_profile(access_token).history_id
            return _collect_full_listing(access_token, baseline_history_id=baseline_history_id, page_token=None)

    # Unrecognized cursor shape (shouldn't happen outside a bug or manual
    # DB edit) — never crash on it, just treat it as "no cursor".
    baseline_history_id = gmail_source.fetch_profile(access_token).history_id
    return _collect_full_listing(access_token, baseline_history_id=baseline_history_id, page_token=None)


def _collect_full_listing(
    access_token: str, *, baseline_history_id: str, page_token: str | None
) -> tuple[list[str], str | None, bool]:
    message_ids: list[str] = []
    pages = 0
    while pages < MAX_PAGES_PER_CALL and len(message_ids) < MAX_MESSAGES_PER_CALL:
        page = gmail_source.list_message_ids(access_token, page_token=page_token)
        message_ids.extend(page.message_ids)
        pages += 1
        page_token = page.next_page_token
        if page_token is None:
            break

    if page_token is not None:
        # Not finished — carry the SAME baseline (captured before this
        # listing began) forward to the next "Sync now" click, alongside
        # where to resume. partition(":") on read tolerates page_token
        # itself containing a colon; baseline_history_id (a Gmail-assigned
        # numeric id) never does, so splitting on the first colon is safe.
        return message_ids, f"page:{baseline_history_id}:{page_token}", False

    return message_ids, f"history:{baseline_history_id}", True


def _collect_incremental(access_token: str, *, start_history_id: str) -> tuple[list[str], str | None, bool]:
    message_ids: list[str] = []
    page_token: str | None = None
    latest_history_id = start_history_id
    pages = 0
    while pages < MAX_PAGES_PER_CALL and len(message_ids) < MAX_MESSAGES_PER_CALL:
        page = gmail_source.list_changed_message_ids(
            access_token, start_history_id=start_history_id, page_token=page_token
        )
        message_ids.extend(page.message_ids)
        if page.new_history_id:
            latest_history_id = page.new_history_id
        pages += 1
        page_token = page.next_page_token
        if page_token is None:
            break

    fully_listed = page_token is None
    return message_ids, f"history:{latest_history_id}", fully_listed
