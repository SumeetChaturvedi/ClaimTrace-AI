"""Symmetric encryption for refresh tokens at rest (Phase 1: Gmail
Integration) — the ONLY module allowed to encrypt or decrypt
ConnectedMailbox.encrypted_refresh_token. Every other module that needs a
usable refresh token (gmail_oauth.py, orchestrator.py) calls
decrypt_refresh_token() rather than touching the ciphertext itself, and
nothing outside this module ever logs a plaintext token.

Uses `cryptography`'s Fernet (AES-128-CBC + HMAC, authenticated symmetric
encryption) — a deliberate choice over a hand-rolled scheme: Fernet is
the standard, well-reviewed answer for "encrypt this blob with a key from
configuration," and nothing here needs more than that (no per-record key
derivation, no key rotation story yet — a real gap, see this phase's own
report).

Fails closed, not open: if `settings.mailbox_token_encryption_key` is
unset, every function here raises TokenEncryptionNotConfigured rather
than falling back to a hardcoded key, a no-op passthrough, or storing the
token in plaintext. Callers (gmail_oauth.py's token exchange,
project_mailboxes.py's connect endpoint) must let this propagate as a
clear 503-style error, never silently proceed.
"""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.config import Settings


class TokenEncryptionNotConfigured(Exception):
    """Raised when MAILBOX_TOKEN_ENCRYPTION_KEY is missing or malformed.
    Callers must treat this as "Gmail integration is not available in
    this environment," never bypass it."""


class TokenDecryptionError(Exception):
    """Raised when a stored ciphertext can't be decrypted with the
    currently configured key — e.g. the key was rotated/changed after the
    token was stored. Callers must treat the affected mailbox as needing
    reconnection, never attempt to use whatever decrypt() partially
    returns (it returns nothing; this is raised instead)."""


def _fernet(settings: Settings) -> Fernet:
    key = (settings.mailbox_token_encryption_key or "").strip()
    if not key:
        raise TokenEncryptionNotConfigured(
            "MAILBOX_TOKEN_ENCRYPTION_KEY is not configured — Gmail connect/sync is unavailable "
            "until a Fernet key is set. Generate one with: "
            "python3 -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    try:
        return Fernet(key.encode("utf-8"))
    except (ValueError, TypeError) as exc:
        raise TokenEncryptionNotConfigured(
            "MAILBOX_TOKEN_ENCRYPTION_KEY is set but is not a valid Fernet key"
        ) from exc


def encrypt_refresh_token(plain_token: str, settings: Settings) -> str:
    """Encrypt `plain_token` for storage in
    ConnectedMailbox.encrypted_refresh_token. Raises
    TokenEncryptionNotConfigured if no key is configured — never stores
    the token unencrypted as a fallback."""
    if not plain_token:
        raise ValueError("plain_token must not be empty")
    return _fernet(settings).encrypt(plain_token.encode("utf-8")).decode("ascii")


def decrypt_refresh_token(ciphertext: str, settings: Settings) -> str:
    """Decrypt a stored ConnectedMailbox.encrypted_refresh_token. Raises
    TokenEncryptionNotConfigured if no key is configured, or
    TokenDecryptionError if the ciphertext can't be decrypted with the
    configured key (wrong/rotated key, or corrupted data) — never returns
    a partial or fabricated value."""
    fernet = _fernet(settings)
    try:
        return fernet.decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise TokenDecryptionError(
            "Stored refresh token could not be decrypted with the configured encryption key"
        ) from exc
