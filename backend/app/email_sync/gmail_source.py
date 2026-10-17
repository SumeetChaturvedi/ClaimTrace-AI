"""Gmail message-source adapter (Phase 1: Gmail Integration) — the ONLY
module that knows Gmail's own REST shapes (messages.list, history.list,
messages.get). Its entire output contract is "a page of raw RFC 822
bytes plus pagination/cursor state"; nothing downstream (the sync
orchestrator, ingest_email_bytes()) needs to know anything Gmail-specific.

Two listing modes, matching Gmail's own two mechanisms:
  - Full list (`list_message_ids`): used when a mailbox has no sync_cursor
    yet (first sync, or a previous cursor expired — see
    HistoryExpiredError below). Paginates via Gmail's own `pageToken`.
  - Incremental (`list_changed_message_ids`): used once a historyId cursor
    exists, via Gmail's `history.list`. Returns only messages added since
    that historyId, plus Gmail's own new historyId to persist as the next
    cursor.

Every function here takes a bare access_token string — token refresh and
storage are the orchestrator's job, not this module's.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass

import httpx

from app.email_sync.gmail_oauth import GmailTransientError

MESSAGES_LIST_ENDPOINT = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
HISTORY_LIST_ENDPOINT = "https://gmail.googleapis.com/gmail/v1/users/me/history"
MESSAGE_GET_ENDPOINT = "https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}"
PROFILE_ENDPOINT = "https://gmail.googleapis.com/gmail/v1/users/me/profile"

# A manual "Sync now" click must return in a bounded time, not silently
# hang processing an enormous mailbox — see orchestrator.py's own page-
# count cap, which uses this as its per-call default. Not a Gmail API
# limit, a ClaimTrace-side one.
DEFAULT_PAGE_SIZE = 100

_HTTP_TIMEOUT_SECONDS = 30.0


class GmailApiError(Exception):
    """Raised for any Gmail API response this module can't interpret as
    one of the specific, typed errors below. Callers (the orchestrator)
    treat this as a hard stop for the current sync attempt, never a
    reason to mark needs_reauth (that's reserved for an actual auth
    failure) or to silently skip messages."""


class GmailAuthError(GmailApiError):
    """401 from the Gmail API itself (as opposed to the token endpoint,
    see gmail_oauth.GmailCredentialsRevokedError) — the access token was
    rejected. The orchestrator should attempt exactly one refresh-and-
    retry for this; a second occurrence after a fresh refresh indicates a
    real credentials problem."""


class HistoryExpiredError(GmailApiError):
    """Gmail's history.list returns 404 with reason 'notFound' when the
    requested startHistoryId is too old (Gmail retains history for a
    limited, provider-controlled window). The orchestrator must treat
    this as "reset sync_cursor to None and perform a fresh full sync" —
    never as a reason to mark needs_reauth, and never silently give up
    syncing this mailbox."""


@dataclass(frozen=True)
class MessagePage:
    message_ids: list[str]
    next_page_token: str | None


@dataclass(frozen=True)
class HistoryPage:
    message_ids: list[str]
    next_page_token: str | None
    # Gmail's own current historyId as of this response, when present in
    # the payload (not independently verified against live Gmail API
    # behavior in this phase — no live Google credentials were used; see
    # this phase's own report). The orchestrator treats it defensively:
    # it only ever advances its own tracked cursor forward from whatever
    # value it last saw, never regresses it, and never assumes every page
    # of a multi-page response carries this field.
    new_history_id: str | None = None


@dataclass(frozen=True)
class RawMessage:
    message_id: str
    raw_bytes: bytes


@dataclass(frozen=True)
class GmailProfile:
    email_address: str
    history_id: str


def _get(url: str, access_token: str, params: dict) -> httpx.Response:
    try:
        response = httpx.get(
            url,
            headers={"Authorization": f"Bearer {access_token}"},
            params={k: v for k, v in params.items() if v is not None},
            timeout=_HTTP_TIMEOUT_SECONDS,
        )
    except httpx.HTTPError as exc:
        raise GmailTransientError(f"Could not reach the Gmail API: {exc}") from exc

    if response.status_code == 401:
        raise GmailAuthError("Gmail API rejected the access token")
    if response.status_code == 429 or response.status_code >= 500:
        raise GmailTransientError(f"Gmail API returned a transient error (HTTP {response.status_code})")
    return response


def list_message_ids(access_token: str, *, page_token: str | None, page_size: int = DEFAULT_PAGE_SIZE) -> MessagePage:
    """One page of a full mailbox listing — used for the initial sync, or
    after a HistoryExpiredError forces a fresh full sync. Paginate by
    repeatedly calling this with the returned next_page_token until it is
    None."""
    response = _get(
        MESSAGES_LIST_ENDPOINT,
        access_token,
        {"maxResults": page_size, "pageToken": page_token},
    )
    if response.status_code != 200:
        raise GmailApiError(f"Gmail messages.list failed (HTTP {response.status_code})")

    body = response.json()
    message_ids = [m["id"] for m in body.get("messages", [])]
    return MessagePage(message_ids=message_ids, next_page_token=body.get("nextPageToken"))


def list_changed_message_ids(
    access_token: str, *, start_history_id: str, page_token: str | None = None, page_size: int = DEFAULT_PAGE_SIZE
) -> HistoryPage:
    """One page of messages added since `start_history_id`. Raises
    HistoryExpiredError if Gmail has aged out that cursor (see that
    class's own docstring) — the orchestrator must fall back to a full
    sync, not treat this as any other kind of failure."""
    response = _get(
        HISTORY_LIST_ENDPOINT,
        access_token,
        {
            "startHistoryId": start_history_id,
            "historyTypes": "messageAdded",
            "maxResults": page_size,
            "pageToken": page_token,
        },
    )
    if response.status_code == 404:
        raise HistoryExpiredError(f"Gmail history cursor {start_history_id!r} has expired")
    if response.status_code != 200:
        raise GmailApiError(f"Gmail history.list failed (HTTP {response.status_code})")

    body = response.json()
    message_ids: list[str] = []
    for entry in body.get("history", []):
        for added in entry.get("messagesAdded", []):
            message_id = added.get("message", {}).get("id")
            if message_id:
                message_ids.append(message_id)

    return HistoryPage(
        message_ids=message_ids,
        next_page_token=body.get("nextPageToken"),
        new_history_id=body.get("historyId"),
    )


def fetch_raw_message(access_token: str, message_id: str) -> RawMessage:
    """Fetch one message's raw RFC 822 bytes — the exact shape
    parse_eml() (app/email_ingestion/parsing.py) already expects, so this
    is the only format-translation Gmail integration needs to do."""
    response = _get(MESSAGE_GET_ENDPOINT.format(message_id=message_id), access_token, {"format": "raw"})
    if response.status_code == 404:
        # The message was deleted/moved between listing and fetching it —
        # not a failure of this sync attempt, the orchestrator skips it
        # and continues with the rest of the page.
        raise GmailMessageNotFoundError(message_id)
    if response.status_code != 200:
        raise GmailApiError(f"Gmail messages.get failed for {message_id} (HTTP {response.status_code})")

    raw_field = response.json().get("raw")
    if not raw_field:
        raise GmailApiError(f"Gmail messages.get response for {message_id} had no raw payload")
    raw_bytes = base64.urlsafe_b64decode(raw_field + "=" * (-len(raw_field) % 4))
    return RawMessage(message_id=message_id, raw_bytes=raw_bytes)


def fetch_profile(access_token: str) -> GmailProfile:
    """Fetch the connected account's own address and its CURRENT
    historyId. Used both right after connecting (to display which
    account was connected — covered by the gmail.readonly scope already
    requested, no additional scope needed) and by the sync orchestrator,
    which captures history_id at the start of a full sync as the baseline
    cursor for every incremental sync afterward (see orchestrator.py)."""
    response = _get(PROFILE_ENDPOINT, access_token, {})
    if response.status_code != 200:
        raise GmailApiError(f"Gmail users.getProfile failed (HTTP {response.status_code})")

    body = response.json()
    email_address = body.get("emailAddress")
    history_id = body.get("historyId")
    if not email_address or not history_id:
        raise GmailApiError("Gmail profile response was missing emailAddress or historyId")
    return GmailProfile(email_address=email_address, history_id=str(history_id))


class GmailMessageNotFoundError(GmailApiError):
    """The specific, recoverable case of fetch_raw_message() targeting a
    message that no longer exists — a normal race (user deleted it
    between list and get), not an error worth stopping the whole sync
    for."""

    def __init__(self, message_id: str) -> None:
        super().__init__(f"Message {message_id} no longer exists")
        self.message_id = message_id
