"""Project-scoped Gmail mailbox connections (Phase 1: Gmail Integration).

Mirrors project_emails.py's own conventions: project-scoping enforced on
every read/write, a uniform 404 for "doesn't exist" and "belongs to a
different project" alike. Import itself (the actual parse/dedup/thread/
index work) delegates entirely to the EXISTING, unmodified
app/email_ingestion/pipeline.py via app/email_sync/orchestrator.py — this
module is a thin HTTP translation layer, exactly as project_emails.py is
over the same pipeline for manual uploads.

Authorization note (see ConnectedMailbox's own docstring for the full
discussion): every endpoint here checks project_id exactly like every
other project-scoped endpoint in this app, which is the strongest
authorization boundary that exists anywhere in ClaimTrace today — there
is no user/session layer to check anything stronger against. This is a
pre-existing, structural property of the whole application, not
something introduced here.

No refresh token, access token, or authorization code ever appears in
any response model in this file, any log statement in this module or
anything it calls, or any URL this module constructs for the FRONTEND
(the one secret-bearing exchange — the authorization `code` — travels
only from Google to this backend's own callback endpoint, never through
the frontend)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.models import ConnectedMailbox, Project
from app.db.session import get_db
from app.email_sync import gmail_source
from app.email_sync.gmail_oauth import (
    GmailOAuthError,
    build_authorization_url,
    exchange_code_for_tokens,
    revoke_token,
    verify_oauth_state,
)
from app.email_sync.orchestrator import MailboxNotSyncableError, SyncResult, sync_mailbox
from app.email_sync.token_crypto import (
    TokenDecryptionError,
    TokenEncryptionNotConfigured,
    decrypt_refresh_token,
    encrypt_refresh_token,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["mailboxes"])
project_router = APIRouter(prefix="/projects/{project_id}/mailboxes", tags=["mailboxes"])


def _get_project_or_404(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def _get_mailbox_or_404(db: Session, project_id: int, mailbox_id: int) -> ConnectedMailbox:
    """Uniform 404 for "doesn't exist" and "belongs to a different
    project" alike — matches every other project-scoped lookup in this
    app (see project_emails.py's own _get_thread_or_404 etc.): confirming
    a mailbox id exists under some OTHER project would itself be a
    cross-project information leak."""
    mailbox = db.get(ConnectedMailbox, mailbox_id)
    if mailbox is None or mailbox.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connected mailbox not found")
    return mailbox


# -- Response models ---------------------------------------------------
# None of these carry encrypted_refresh_token, access tokens, or anything
# derived from them.


class ConnectAuthorizationResponse(BaseModel):
    authorization_url: str


class ConnectedMailboxSummary(BaseModel):
    id: int
    provider: str
    external_email: str
    status: str
    last_synced_at: str | None = None
    last_sync_error: str | None = None
    connected_at: str

    @classmethod
    def from_model(cls, mailbox: ConnectedMailbox) -> "ConnectedMailboxSummary":
        return cls(
            id=mailbox.id,
            provider=mailbox.provider,
            external_email=mailbox.external_email,
            status=mailbox.status,
            last_synced_at=mailbox.last_synced_at.isoformat() if mailbox.last_synced_at else None,
            last_sync_error=mailbox.last_sync_error,
            connected_at=mailbox.connected_at.isoformat(),
        )


class SyncResultResponse(BaseModel):
    status: str
    imported: int
    duplicate: int
    rejected: int
    skipped_not_found: int
    error: str | None = None

    @classmethod
    def from_result(cls, result: SyncResult) -> "SyncResultResponse":
        return cls(
            status=result.status,
            imported=result.imported,
            duplicate=result.duplicate,
            rejected=result.rejected,
            skipped_not_found=result.skipped_not_found,
            error=result.error,
        )


# -- Connect / callback --------------------------------------------------


@project_router.post("/gmail/connect", response_model=ConnectAuthorizationResponse)
def start_gmail_connect(
    project_id: int,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ConnectAuthorizationResponse:
    """Build the Google consent-screen URL for connecting a Gmail mailbox
    to this project. The frontend performs a full browser navigation to
    the returned URL — this is never fetched via XHR/fetch, since the
    whole point is for the person's own browser to interact with
    Google's consent screen directly."""
    _get_project_or_404(db, project_id)
    try:
        url = build_authorization_url(settings, project_id)
    except GmailOAuthError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return ConnectAuthorizationResponse(authorization_url=url)


@router.get("/mailboxes/gmail/callback")
def gmail_oauth_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    """Google redirects the browser here after the consent screen. Not
    project-scoped in the URL (Google only knows the fixed, registered
    redirect_uri) — the project_id is recovered from the verified `state`
    parameter instead, never trusted from anywhere else. Always ends in a
    redirect back to the frontend's project page, with only a coarse
    success/failure indicator in the query string — never any token,
    code, or detailed error that could itself be sensitive."""
    if error:
        # The person denied consent, or Google reported some other
        # provider-side issue — not a ClaimTrace bug. No project_id is
        # trustworthy here (state may not even be present), so this can
        # only redirect to a generic landing point.
        return RedirectResponse(f"{settings.frontend_base_url}/?gmail_connect=denied")

    if not code or not state:
        return RedirectResponse(f"{settings.frontend_base_url}/?gmail_connect=error")

    try:
        project_id = verify_oauth_state(settings, state)
    except GmailOAuthError:
        logger.warning("Gmail OAuth callback received an invalid or expired state")
        return RedirectResponse(f"{settings.frontend_base_url}/?gmail_connect=error")

    # Code review fix: the project could have been deleted in the window
    # between starting the connect flow and Google redirecting back here
    # (narrow, but real — a bare ConnectedMailbox insert below would then
    # hit the project_id foreign key constraint and raise an unhandled
    # IntegrityError, surfacing as a raw 500 to the browser instead of a
    # graceful redirect). Checked explicitly, failing the same way every
    # other error in this handler does.
    if db.get(Project, project_id) is None:
        logger.warning("Gmail OAuth callback for a project that no longer exists: project_id=%s", project_id)
        return RedirectResponse(f"{settings.frontend_base_url}/?gmail_connect=error")

    try:
        tokens = exchange_code_for_tokens(settings, code)
        profile = gmail_source.fetch_profile(tokens.access_token)
        encrypted = encrypt_refresh_token(tokens.refresh_token, settings)
    except (GmailOAuthError, gmail_source.GmailApiError, TokenEncryptionNotConfigured) as exc:
        logger.warning("Gmail connect failed for project_id=%s: %s", project_id, exc)
        return RedirectResponse(
            f"{settings.frontend_base_url}/projects/{project_id}?gmail_connect=error"
        )

    existing = db.scalar(
        select(ConnectedMailbox).where(
            ConnectedMailbox.project_id == project_id,
            ConnectedMailbox.external_email == profile.email_address,
        )
    )
    if existing is not None:
        # Reconnecting the same mailbox to the same project (e.g. after a
        # disconnect, or to re-grant consent following needs_reauth) —
        # update in place rather than violating the
        # (project_id, external_email) uniqueness constraint.
        existing.encrypted_refresh_token = encrypted
        existing.granted_scope = tokens.granted_scope
        existing.status = "connected"
        existing.last_sync_error = None
        existing.sync_cursor = None  # a reconnect always starts from a fresh full sync
    else:
        db.add(
            ConnectedMailbox(
                project_id=project_id,
                provider="gmail",
                external_email=profile.email_address,
                encrypted_refresh_token=encrypted,
                granted_scope=tokens.granted_scope,
                status="connected",
            )
        )
    db.commit()

    return RedirectResponse(f"{settings.frontend_base_url}/projects/{project_id}?gmail_connect=success")


# -- List / sync / disconnect -------------------------------------------


@project_router.get("", response_model=list[ConnectedMailboxSummary])
def list_connected_mailboxes(project_id: int, db: Session = Depends(get_db)) -> list[ConnectedMailboxSummary]:
    _get_project_or_404(db, project_id)
    mailboxes = db.scalars(
        select(ConnectedMailbox).where(ConnectedMailbox.project_id == project_id).order_by(ConnectedMailbox.id)
    ).all()
    return [ConnectedMailboxSummary.from_model(m) for m in mailboxes]


@project_router.post("/{mailbox_id}/sync", response_model=SyncResultResponse)
def sync_connected_mailbox(
    project_id: int,
    mailbox_id: int,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SyncResultResponse:
    """Run one bounded, synchronous sync pass against this mailbox,
    feeding every fetched message into the existing, unmodified
    ingest_email_bytes() pipeline. May take several seconds for a mailbox
    with many new messages (bounded by orchestrator.MAX_MESSAGES_PER_CALL)
    — there is no background job queue in this phase, so the HTTP request
    itself does the work and returns when it's done or bounded."""
    _get_project_or_404(db, project_id)
    mailbox = _get_mailbox_or_404(db, project_id, mailbox_id)

    try:
        result = sync_mailbox(db, settings.storage_root, mailbox, settings)
    except MailboxNotSyncableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return SyncResultResponse.from_result(result)


@project_router.post("/{mailbox_id}/disconnect", response_model=ConnectedMailboxSummary)
def disconnect_mailbox(
    project_id: int,
    mailbox_id: int,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ConnectedMailboxSummary:
    """Disconnect this mailbox: best-effort revoke at Google, then ALWAYS
    null out the stored encrypted refresh token and mark status
    'disconnected' locally regardless of whether the Google-side revoke
    succeeded — the person's intent to disconnect must take effect in
    ClaimTrace even if Google's revoke endpoint is briefly unreachable.
    Once nulled, no subsequent sync can use this mailbox's credentials
    (sync_mailbox() checks for a stored token before making any Gmail API
    call at all — see orchestrator.py)."""
    _get_project_or_404(db, project_id)
    mailbox = _get_mailbox_or_404(db, project_id, mailbox_id)

    if mailbox.encrypted_refresh_token:
        try:
            plain = decrypt_refresh_token(mailbox.encrypted_refresh_token, settings)
            revoked = revoke_token(settings, plain)
            if not revoked:
                logger.warning("Gmail revoke call did not succeed for mailbox_id=%s; disconnecting locally anyway", mailbox_id)
        except (TokenEncryptionNotConfigured, TokenDecryptionError) as exc:
            logger.warning("Could not decrypt token to revoke at Google for mailbox_id=%s: %s", mailbox_id, exc)

    mailbox.encrypted_refresh_token = None
    mailbox.status = "disconnected"
    mailbox.sync_cursor = None
    db.commit()

    return ConnectedMailboxSummary.from_model(mailbox)
