"""Gmail OAuth 2.0 authorization-code flow (Phase 1: Gmail Integration).

Raw REST calls via httpx — no google-auth/google-auth-oauthlib/
google-api-python-client dependency. Those libraries are convenience
wrappers over exactly the handful of HTTP calls this module makes
directly; adding them would be a second way to do what httpx (already a
transitive dependency of this project via FastAPI's own test client, now
pinned directly — see requirements.txt) already does.

Read-only scope only (SCOPE below) — this module never requests, and
would reject at review time, a broader Gmail scope.

CSRF protection (`state` parameter, mandatory per the Phase 1 security
requirements): implemented as a stateless, HMAC-signed, time-limited
token — NOT a server-side session or a new database table. There is no
session/login mechanism anywhere in this application to hang CSRF state
off of (see ConnectedMailbox's own docstring), so the state token itself
carries everything needed to verify it: the project_id it was issued for,
an issuance timestamp (checked against a short expiry), and a random
nonce, all covered by an HMAC-SHA256 signature keyed on the Gmail OAuth
client secret (a server-only secret this app already requires to be
configured for Gmail integration to work at all — this intentionally
avoids introducing a THIRD secret purely for state-signing). Tampering
with the project_id, timestamp, or nonce invalidates the signature;
replaying an old, otherwise-valid state past its expiry is rejected
separately. Replay of a *fresh* captured state is still bounded by
Google's own authorization `code` being single-use — a replayed callback
URL fails at the token-exchange step even if the state itself were still
valid.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time
from dataclasses import dataclass

import httpx

from app.config import Settings

SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
REVOKE_ENDPOINT = "https://oauth2.googleapis.com/revoke"

STATE_MAX_AGE_SECONDS = 600  # 10 minutes — long enough for a real consent flow, short enough to bound replay risk
_HTTP_TIMEOUT_SECONDS = 15.0


class GmailOAuthError(Exception):
    """Raised for any configuration, state-validation, or Google-API
    failure in this module. Callers (project_mailboxes.py) translate this
    into a clean HTTP error — never a raw traceback, never a leaked
    secret in the message."""


class GmailCredentialsRevokedError(GmailOAuthError):
    """Raised specifically when Google reports `invalid_grant` on a
    refresh attempt — the refresh token itself is no longer usable
    (revoked by the user outside ClaimTrace, expired, or the app's own
    access was removed). Callers must mark the mailbox 'needs_reauth',
    never retry this error as if it were transient."""


class GmailTransientError(GmailOAuthError):
    """Raised for a rate limit (429) or server-side (5xx) response —
    distinct from GmailCredentialsRevokedError so callers retry/back off
    rather than demanding reconnection for what is not a credential
    problem."""


@dataclass(frozen=True)
class GmailTokens:
    access_token: str
    refresh_token: str | None
    expires_in: int
    granted_scope: str


def _require_gmail_config(settings: Settings) -> tuple[str, str]:
    client_id = (settings.gmail_client_id or "").strip()
    client_secret = (settings.gmail_client_secret or "").strip()
    if not client_id or not client_secret:
        raise GmailOAuthError(
            "Gmail integration is not configured — set GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET."
        )
    return client_id, client_secret


def _state_secret(settings: Settings) -> bytes:
    _, client_secret = _require_gmail_config(settings)
    return client_secret.encode("utf-8")


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + padding)


def build_oauth_state(settings: Settings, project_id: int) -> str:
    """Build a signed, time-limited state token binding this OAuth
    attempt to `project_id`. See module docstring for the full rationale."""
    nonce = base64.urlsafe_b64encode(os.urandom(16)).rstrip(b"=").decode("ascii")
    payload = f"{project_id}:{int(time.time())}:{nonce}"
    signature = hmac.new(_state_secret(settings), payload.encode("utf-8"), hashlib.sha256).digest()
    return f"{_b64url_encode(payload.encode('utf-8'))}.{_b64url_encode(signature)}"


def verify_oauth_state(settings: Settings, state: str) -> int:
    """Verify `state` and return the project_id it was issued for. Raises
    GmailOAuthError for a missing/malformed/tampered/expired state —
    callers must reject the whole callback, never fall back to trusting
    an unverified project id from anywhere else (e.g. a query parameter
    an attacker could also control)."""
    try:
        payload_b64, signature_b64 = state.split(".", 1)
        payload_bytes = _b64url_decode(payload_b64)
        signature = _b64url_decode(signature_b64)
    except Exception as exc:  # noqa: BLE001 -- any malformed input (bad base64, missing '.') is a rejection, not a 500
        raise GmailOAuthError("Invalid OAuth state") from exc

    expected_signature = hmac.new(_state_secret(settings), payload_bytes, hashlib.sha256).digest()
    if not hmac.compare_digest(signature, expected_signature):
        raise GmailOAuthError("OAuth state signature did not match — possible CSRF or tampering")

    try:
        project_id_str, issued_at_str, _nonce = payload_bytes.decode("utf-8").split(":", 2)
        project_id = int(project_id_str)
        issued_at = int(issued_at_str)
    except (ValueError, UnicodeDecodeError) as exc:
        raise GmailOAuthError("Invalid OAuth state payload") from exc

    if time.time() - issued_at > STATE_MAX_AGE_SECONDS:
        raise GmailOAuthError("OAuth state has expired — please restart the connection")

    return project_id


def build_authorization_url(settings: Settings, project_id: int) -> str:
    """Build the Google consent-screen URL for connecting a mailbox to
    `project_id`. access_type=offline + prompt=consent together are what
    guarantee Google returns a refresh_token even if this exact Google
    account previously granted (and later revoked, or was never asked to
    re-grant) access — without prompt=consent, a returning user can get a
    code exchange with no refresh_token in the response at all."""
    client_id, _ = _require_gmail_config(settings)
    state = build_oauth_state(settings, project_id)
    params = {
        "client_id": client_id,
        "redirect_uri": settings.gmail_oauth_redirect_uri,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    query = httpx.QueryParams(params)
    return f"{AUTH_ENDPOINT}?{query}"


def exchange_code_for_tokens(settings: Settings, code: str) -> GmailTokens:
    """Exchange a one-time authorization `code` for access/refresh
    tokens. Raises GmailOAuthError if Google rejects the code (e.g.
    already used, expired) or returns no refresh_token (meaning consent
    wasn't actually (re-)granted — see build_authorization_url's own
    prompt=consent note)."""
    client_id, client_secret = _require_gmail_config(settings)
    try:
        response = httpx.post(
            TOKEN_ENDPOINT,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": settings.gmail_oauth_redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=_HTTP_TIMEOUT_SECONDS,
        )
    except httpx.HTTPError as exc:
        raise GmailOAuthError(f"Could not reach Google's token endpoint: {exc}") from exc

    if response.status_code != 200:
        # Never include response body verbatim in the raised message if it
        # could echo back anything sensitive; Google's error responses here
        # are {"error": "...", "error_description": "..."} with no token
        # material, so surfacing the error code is safe and useful.
        raise GmailOAuthError(f"Google rejected the authorization code (HTTP {response.status_code})")

    body = response.json()
    refresh_token = body.get("refresh_token")
    if not refresh_token:
        raise GmailOAuthError(
            "Google did not return a refresh token for this authorization — reconnect and approve "
            "the consent screen again"
        )

    return GmailTokens(
        access_token=body["access_token"],
        refresh_token=refresh_token,
        expires_in=int(body.get("expires_in", 3600)),
        granted_scope=body.get("scope", SCOPE),
    )


def refresh_access_token(settings: Settings, refresh_token: str) -> tuple[str, int]:
    """Exchange a stored refresh_token for a fresh access_token. Raises
    GmailCredentialsRevokedError on `invalid_grant` (the refresh token
    itself is no longer usable), GmailTransientError on 429/5xx, or
    GmailOAuthError for anything else unexpected."""
    client_id, client_secret = _require_gmail_config(settings)
    try:
        response = httpx.post(
            TOKEN_ENDPOINT,
            data={
                "refresh_token": refresh_token,
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "refresh_token",
            },
            timeout=_HTTP_TIMEOUT_SECONDS,
        )
    except httpx.HTTPError as exc:
        raise GmailTransientError(f"Could not reach Google's token endpoint: {exc}") from exc

    if response.status_code == 400 and response.json().get("error") == "invalid_grant":
        raise GmailCredentialsRevokedError(
            "Gmail access has been revoked or the refresh token is no longer valid"
        )
    if response.status_code == 429 or response.status_code >= 500:
        raise GmailTransientError(f"Google's token endpoint returned a transient error (HTTP {response.status_code})")
    if response.status_code != 200:
        raise GmailOAuthError(f"Could not refresh the Gmail access token (HTTP {response.status_code})")

    body = response.json()
    return body["access_token"], int(body.get("expires_in", 3600))


def revoke_token(settings: Settings, token: str) -> bool:
    """Best-effort revocation of `token` at Google (either the refresh
    token or an access token derived from it — Google accepts either and
    revokes the whole grant). Returns True on success, False on any
    failure — callers must disconnect locally regardless (null the stored
    token, mark status) since the user's intent to disconnect must always
    succeed from ClaimTrace's side even if Google's revoke endpoint is
    unreachable."""
    try:
        response = httpx.post(REVOKE_ENDPOINT, data={"token": token}, timeout=_HTTP_TIMEOUT_SECONDS)
        return response.status_code == 200
    except httpx.HTTPError:
        return False
