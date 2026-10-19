"""Local OCR via Tesseract, through the pytesseract wrapper (Phase W2.1:
Local OCR Foundation).

pytesseract is a thin subprocess wrapper around the real Tesseract OS
executable -- installing the `pytesseract` pip package does NOT install
that executable (macOS: `brew install tesseract`; Debian/Ubuntu:
`apt-get install tesseract-ocr`; see the README's own installation
section). Every function here checks for the executable explicitly and
returns a clean, non-raising failure when it's absent, rather than
assuming it's there -- the application itself must still start and run
every non-OCR code path with Tesseract completely missing.

Exception/timeout behavior below is verified against the actual installed
pytesseract==0.3.13 package (see .venv/lib/*/site-packages/pytesseract/
pytesseract.py), not guessed from documentation:
  - TesseractNotFoundError (a subclass of OSError) when the executable
    itself can't be found (subprocess.Popen raises ENOENT).
  - TesseractError(status, message) (a subclass of RuntimeError) when the
    executable runs but exits non-zero -- this is how an unavailable
    language ('Error opening data file ...') or a Tesseract-level image
    problem is reported.
  - On a subprocess timeout, pytesseract raises a PLAIN RuntimeError with
    the literal message 'Tesseract process timeout' -- there is no
    dedicated TimeoutError/RunTimeoutError class in this version. Caught
    here as a RuntimeError that is specifically NOT a TesseractError.

No shell command is ever constructed: pytesseract invokes Tesseract via
subprocess.Popen with an argv LIST (confirmed by reading its own
run_tesseract()), never shell=True or a formatted string -- `language` is
this application's own configured value, never user-supplied, and no
other caller-controlled string reaches the command line here.

Never logs image bytes or OCR text -- only paths, language, and exception
text, mirroring every other logger.warning() call already in this
codebase (see app/email_ingestion/pipeline.py, app/whatsapp_ingestion/
pipeline.py)."""

from __future__ import annotations

import io
import logging
import shutil
from dataclasses import dataclass

import pytesseract
from PIL import Image, UnidentifiedImageError
from pytesseract import TesseractError, TesseractNotFoundError

logger = logging.getLogger(__name__)

OCR_ENGINE_NAME = "tesseract"
DEFAULT_OCR_LANGUAGE = "eng"
# Mirrors app/email_sync/gmail_oauth.py's own _HTTP_TIMEOUT_SECONDS
# convention (an explicit timeout constant for the one external-process
# call this codebase makes) -- bounds Tesseract's own CPU/wall-clock time
# on a legitimately-sized but dense/complex image; the byte/pixel caps in
# app/ingestion/image_validation.py already bound memory, not CPU time.
OCR_TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class OcrRunResult:
    """The outcome of run_ocr() below. `status='completed'` always
    carries `text` (possibly empty -- a genuine, honest "no readable
    text found" result, never an error) and `engine_version` when it
    could be determined; `status='failed'` always carries `error`.
    Never raises; every outcome comes back as one of these."""

    status: str  # 'completed' | 'failed'
    text: str | None = None
    error: str | None = None
    engine: str = OCR_ENGINE_NAME
    engine_version: str | None = None
    language: str = DEFAULT_OCR_LANGUAGE


def _resolve_tesseract_cmd(tesseract_cmd: str | None) -> str:
    """None means "search PATH", pytesseract's own default behavior
    (its module-level `tesseract_cmd` variable defaults to the bare
    string 'tesseract', resolved via the OS's own PATH lookup inside
    subprocess.Popen) -- never a hardcoded path."""
    return tesseract_cmd or "tesseract"


def is_tesseract_available(*, tesseract_cmd: str | None = None) -> bool:
    """A cheap, non-raising check for whether the configured (or PATH-
    resolved) Tesseract executable actually exists -- used by the batch
    processor (app/ocr/process_pending.py) to exit cleanly up front
    rather than attempting, and failing, a whole batch one row at a
    time."""
    return shutil.which(_resolve_tesseract_cmd(tesseract_cmd)) is not None


def get_engine_version(*, tesseract_cmd: str | None = None) -> str | None:
    """The installed Tesseract version string (e.g. '5.3.4'), or None if
    it can't be determined (missing executable, or any other failure) --
    never raises. Provenance metadata only; never logged verbatim beyond
    this short version string."""
    resolved_cmd = _resolve_tesseract_cmd(tesseract_cmd)
    pytesseract.pytesseract.tesseract_cmd = resolved_cmd
    try:
        return str(pytesseract.get_tesseract_version())
    except Exception:  # noqa: BLE001 -- version lookup is best-effort metadata, never worth crashing over
        return None


def run_ocr(
    content: bytes,
    *,
    language: str = DEFAULT_OCR_LANGUAGE,
    tesseract_cmd: str | None = None,
    timeout: int = OCR_TIMEOUT_SECONDS,
) -> OcrRunResult:
    """Run Tesseract OCR on `content` -- already-validated, already-
    preserved image bytes (the caller, app/ocr/process_pending.py, is
    responsible for re-running app/ingestion/image_validation.py's
    validate_image() immediately before this call; this function does
    not re-validate on its own, to keep validation and OCR invocation as
    two separately testable responsibilities).

    Never raises: every outcome -- missing executable, unavailable
    language, timeout, a Tesseract-level image problem, or a genuinely
    successful-but-empty result -- comes back as a plain OcrRunResult,
    mirroring this project's established "never guess, never silently
    drop, never crash the caller's batch" convention (see
    app/ingestion/image_validation.py's own docstring for the same
    principle applied to image validation)."""
    resolved_cmd = _resolve_tesseract_cmd(tesseract_cmd)
    pytesseract.pytesseract.tesseract_cmd = resolved_cmd

    if shutil.which(resolved_cmd) is None:
        return OcrRunResult(
            status="failed",
            error=f"Tesseract executable not found (looked for {resolved_cmd!r} on PATH)",
            language=language,
        )

    engine_version = get_engine_version(tesseract_cmd=resolved_cmd)

    try:
        with Image.open(io.BytesIO(content)) as img:
            text = pytesseract.image_to_string(img, lang=language, timeout=timeout)
    except TesseractNotFoundError as exc:
        return OcrRunResult(status="failed", error=f"Tesseract executable not found: {exc}", engine_version=engine_version, language=language)
    except TesseractError as exc:
        # Covers an unavailable/misconfigured language ("Error opening
        # data file ...") and any other Tesseract-CLI-reported failure.
        return OcrRunResult(status="failed", error=f"Tesseract reported an error: {exc.message}", engine_version=engine_version, language=language)
    except RuntimeError as exc:
        # pytesseract's own subprocess-timeout path raises a plain
        # RuntimeError (no dedicated exception class in this version) --
        # see this module's own docstring for the verified source
        # location. TesseractError (also a RuntimeError) is caught above
        # first, so this branch is specifically the timeout/other-runtime
        # case.
        return OcrRunResult(status="failed", error=f"OCR did not complete: {exc}", engine_version=engine_version, language=language)
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        return OcrRunResult(status="failed", error=f"could not read image for OCR ({exc})", engine_version=engine_version, language=language)

    return OcrRunResult(status="completed", text=text or "", engine_version=engine_version, language=language)
