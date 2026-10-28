from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Pre-commit review fix: the shared fallback output-token budget for any
# Gemini call that doesn't set its own Prompt.max_output_tokens override
# (today: ReasoningEngine's main investigation answer, and
# app/vision/gemini_vision.py's visual descriptions — NOT EventExtractor,
# which already overrides this per-call via EVENT_EXTRACTION_MAX_OUTPUT_
# TOKENS=4096, see app/agent/event_extraction.py). Previously a hardcoded
# 1024 constant in app/llm/gemini_provider.py; a real, thorough,
# multi-section investigative answer can exceed that and gets cut off
# mid-sentence by Gemini's own finish_reason=MAX_TOKENS signal (still
# correctly detected and surfaced via answer_truncated either way — this
# constant changes how OFTEN that happens, not whether it's detected).
# Doubled from 1024 and made configurable via GEMINI_MAX_OUTPUT_TOKENS so
# a future adjustment needs no code change. Deliberately still well below
# EventExtractor's own 4096 — a structured JSON array of discrete events
# genuinely needs more room than prose, and this value is shared with
# vision's own "2-4 sentences" descriptions, which never need anywhere
# near this much headroom.
DEFAULT_GEMINI_MAX_OUTPUT_TOKENS = 2048


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
    gemini_max_output_tokens: int = DEFAULT_GEMINI_MAX_OUTPUT_TOKENS

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

    # Phase W2.1: Local OCR Foundation. None (the default) means "find
    # the `tesseract` executable on PATH" -- the normal case on any host
    # that has it installed (brew/apt), never a hardcoded path. Set this
    # explicitly only for a non-standard install location. The APPLICATION
    # itself must still start with this unset and no Tesseract installed
    # at all -- every OCR-specific code path (app/ocr/tesseract_provider.py)
    # checks for the executable explicitly and reports a clear per-item
    # failure rather than assuming it's present.
    tesseract_cmd: str | None = None
    # Tesseract's own trained-language-data code (not an app locale) --
    # "eng" is Tesseract's own default language and the only one
    # guaranteed present in a standard install.
    ocr_language: str = "eng"

    # Phase W2.3: Multimodal Image Understanding. An explicit, app-level
    # cap on how large an image this process will ever attach to a
    # Gemini request -- independent of, and smaller than,
    # app/ingestion/image_validation.py's own MAX_IMAGE_BYTES (25 MB,
    # the limit for what gets PRESERVED at all). Preservation and
    # "sent to an external provider" are different risk levels: a large
    # image this application is happy to store is not automatically one
    # it should hand to a third-party API uninspected. Configurable
    # rather than hardcoded, since the right value depends on the
    # configured model's own real request-size limits (see
    # app/vision/gemini_vision.py's own docstring for why that is NOT
    # assumed here).
    vision_max_image_bytes: int = 8 * 1024 * 1024
    # Explicit opt-in kill switch, OFF by default, checked ONLY by
    # app/vision/process_pending.py's own CLI entrypoint (main()) --
    # never by OCR or by any text-only Gemini caller (ReasoningEngine,
    # EventExtractor), and never by process_pending() itself, so a test
    # or a future orchestrator that calls process_pending() directly is
    # unaffected. Exists because gemini_api_key/gemini_model are shared
    # with those unrelated, already-working callers, so neither can
    # double as a vision-specific switch: unsetting either to "disable
    # vision" would also break OCR's reprocess-stale-engine-version
    # check and every existing text investigation. Flip to true only
    # after confirming the configured gemini_model actually accepts
    # image input (see gemini_vision.py's own docstring) -- this
    # application makes no such claim on its own.
    vision_processing_enabled: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
