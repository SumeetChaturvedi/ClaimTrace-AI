from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = (
        "postgresql+psycopg2://claimtrace:claimtrace@localhost:5432/claimtrace"
    )
    storage_root: Path = Path("./storage")
    app_env: str = "development"

    default_project_name: str = "Delhi Metro Viaduct Package DMV-7 (fictional)"

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-flash-lite-latest"

    # Phase 1: Gmail Integration. All optional/None by default so the app
    # keeps starting and running exactly as before for anyone who hasn't
    # configured Gmail — every Gmail-specific code path checks for these
    # explicitly and fails with a clear error rather than silently
    # proceeding with an empty client id/secret.
    gmail_client_id: str | None = None
    gmail_client_secret: str | None = None
    # Must exactly match a redirect URI registered in Google Cloud Console
    # for this OAuth client. Points at this backend's own callback route,
    # never at the frontend directly — Google redirects here first so the
    # authorization code exchange (which needs the client secret) happens
    # server-side.
    gmail_oauth_redirect_uri: str = "http://127.0.0.1:8000/mailboxes/gmail/callback"
    # Where the backend redirects the browser after completing (or
    # failing) the OAuth flow — the frontend's own project page, never a
    # bare API response, since this leg of the flow is a top-level browser
    # navigation initiated by Google's own redirect.
    frontend_base_url: str = "http://127.0.0.1:5173"

    # Fernet key (32 url-safe base64-encoded bytes, e.g. via
    # `python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`)
    # used ONLY to encrypt/decrypt ConnectedMailbox.encrypted_refresh_token
    # at rest. None by default: every code path that would store or read a
    # refresh token must check this explicitly and fail closed (refuse to
    # store a token in plaintext, refuse to proceed) rather than falling
    # back to an unencrypted or hardcoded key — see
    # app/email_sync/token_crypto.py.
    mailbox_token_encryption_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
