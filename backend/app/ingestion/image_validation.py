"""Source-neutral image validation (Phase W2.0: Shared Image Preservation
Foundation).

Used by app/email_ingestion/pipeline.py (Gmail image attachments) and the
new direct project-image-upload path (app/api/routes/project_images.py).
Deliberately NOT wired into app/whatsapp_ingestion/pipeline.py — that
module already has its own, already-reviewed W1 content-signature
detection (_detect_media_type) and preservation contract
('stored_pending_processing'); duplicating or replacing it here would be
exactly the kind of disproportionate, unnecessary redesign this phase is
told to avoid, for zero behavioral benefit.

Detection is by real file signature, never by the caller's claimed
filename extension or an untrusted, client-supplied MIME type — the same
principle app/whatsapp_ingestion/pipeline.py's own _detect_media_type
already established for this codebase, applied here specifically to the
four image formats this phase accepts.

Validation never raises: every outcome, including "not an image at all"
and every rejection reason, comes back as a plain ImageValidationResult a
caller can inspect, mirroring this project's established
_MediaResolution/ImportResult-style "never guess, never silently drop"
conventions (see app/whatsapp_ingestion/pipeline.py's _MediaResolution).
"""

from __future__ import annotations

import io
import warnings
from dataclasses import dataclass

from PIL import Image, UnidentifiedImageError

# Mirrors app/ingestion/pipeline.py's MAX_UPLOAD_BYTES -- the same
# synchronous, in-request processing budget every other format already
# uses; images get no special allowance.
MAX_IMAGE_BYTES = 25 * 1024 * 1024  # 25 MB

# A generous per-side cap for real-world site photos/scans (even a modern
# phone camera's largest dimension is well under this) while still
# rejecting a deliberately or accidentally pathological image before any
# further decoding is attempted.
MAX_IMAGE_DIMENSION_PX = 12_000

# ~50 megapixels -- catches an extreme aspect ratio (e.g. a very wide but
# not very tall image) that could individually pass the per-side check
# above while still being enormous in total pixel count.
MAX_IMAGE_TOTAL_PIXELS = 50_000_000

# (signature bytes, extension, content_type). Checked in order; the first
# match wins. Deliberately only the four common, unambiguous image
# formats this phase supports -- anything else (including a real but
# unsupported image format) is reported as "not a recognized image
# format", never guessed at.
_IMAGE_SIGNATURES: tuple[tuple[bytes, str, str], ...] = (
    (b"\xff\xd8\xff", ".jpg", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", ".png", "image/png"),
    (b"GIF87a", ".gif", "image/gif"),
    (b"GIF89a", ".gif", "image/gif"),
)


def sniff_image_signature(content: bytes) -> tuple[str, str] | None:
    """Cheap, no-decode check of `content`'s own leading bytes against
    known image signatures. Returns (extension, content_type), or None if
    `content` doesn't start with any of them -- including WEBP's RIFF
    container, which needs a second offset check beyond a simple prefix.
    This is intentionally the ONLY thing callers use to decide "is this
    even plausibly an image" before attempting the more expensive full
    validate_image() below, so a non-image attachment (e.g. a .csv or
    .zip) is routed to the existing unsupported-format handling with zero
    image-specific work done on it."""
    if content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return ".webp", "image/webp"
    for signature, extension, content_type in _IMAGE_SIGNATURES:
        if content.startswith(signature):
            return extension, content_type
    return None


@dataclass(frozen=True)
class ImageValidationResult:
    """The outcome of validate_image() below. `valid=False` always carries
    a human-readable `error`; `valid=True` always carries the real,
    server-detected extension/content_type/width/height -- never the
    caller's claimed filename or MIME type."""

    valid: bool
    extension: str | None = None
    content_type: str | None = None
    width: int | None = None
    height: int | None = None
    error: str | None = None


def validate_image(content: bytes) -> ImageValidationResult:
    """Validate `content` as a storable image: real signature, real byte
    size, real decodability, real dimensions -- in that order, cheapest
    checks first, so a trivially-oversized or non-image upload never
    reaches Pillow at all.

    Reads MAX_IMAGE_BYTES/MAX_IMAGE_DIMENSION_PX/MAX_IMAGE_TOTAL_PIXELS
    from this module's own globals AT CALL TIME (not as bound default
    argument values) specifically so a test can monkeypatch
    `app.ingestion.image_validation.MAX_IMAGE_BYTES` etc. and have it
    actually take effect — the same pattern
    app/whatsapp_ingestion/zip_import.py's own MAX_ENTRY_BYTES/
    MAX_TOTAL_BYTES already use for the identical reason.

    Dimensions are read from the image's own header via Image.open(),
    which Pillow parses lazily without decoding full pixel data -- this
    and the byte-size check above both run BEFORE Image.verify() (which
    does touch the compressed stream to confirm it isn't truncated/
    corrupt), so a deliberately huge image is rejected on its declared
    dimensions without this process ever allocating a full pixel buffer
    for it.

    Pre-commit review fix: Pillow has its OWN decompression-bomb guard
    (Image.MAX_IMAGE_PIXELS), independent of and checked BEFORE this
    function ever gets to read img.size -- it fires inside Image.open()
    itself, as a DecompressionBombWarning for a declared pixel count
    somewhat over that threshold, or a DecompressionBombError for one far
    over it. Signature checking and this function's own
    MAX_IMAGE_TOTAL_PIXELS limit alone are NOT sufficient: a small,
    highly-compressible file (e.g. a solid-color PNG) can legitimately
    pass the byte-size check above while still declaring an enormous
    pixel count, and Image.open() raises/warns on that BEFORE this
    function's own dimension checks ever run. Both outcomes are
    converted into the same clean, non-raising ImageValidationResult
    every other rejection uses -- never left to propagate and crash the
    caller's batch, and never silently ignored either. The
    warnings-to-error conversion is scoped to this one call via
    warnings.catch_warnings(), never a global warnings.simplefilter()
    that would affect unrelated code elsewhere in the process."""
    if not content:
        return ImageValidationResult(valid=False, error="empty file")
    if len(content) > MAX_IMAGE_BYTES:
        return ImageValidationResult(
            valid=False, error=f"image exceeds the {MAX_IMAGE_BYTES // (1024 * 1024)} MB size limit"
        )

    signature = sniff_image_signature(content)
    if signature is None:
        return ImageValidationResult(valid=False, error="not a recognized image format (JPEG, PNG, GIF, or WEBP)")
    extension, content_type = signature

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as img:
                width, height = img.size
                if width <= 0 or height <= 0:
                    return ImageValidationResult(valid=False, error="image reports no visible dimensions")
                if width > MAX_IMAGE_DIMENSION_PX or height > MAX_IMAGE_DIMENSION_PX:
                    return ImageValidationResult(
                        valid=False,
                        error=f"image dimensions ({width}x{height}) exceed the {MAX_IMAGE_DIMENSION_PX}px per-side limit",
                    )
                if width * height > MAX_IMAGE_TOTAL_PIXELS:
                    return ImageValidationResult(
                        valid=False,
                        error=f"image ({width}x{height}) exceeds the {MAX_IMAGE_TOTAL_PIXELS:,} total-pixel limit",
                    )
                img.verify()
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        SyntaxError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as exc:
        # A real image signature with bytes Pillow still can't decode --
        # truncated, corrupted, a signature collision with non-image
        # data, or (DecompressionBombError/-Warning) a declared pixel
        # count Pillow itself refuses to open. Never treated as valid;
        # the specific exception text is preserved as the rejection
        # reason.
        return ImageValidationResult(valid=False, error=f"could not read image ({exc})")

    return ImageValidationResult(
        valid=True, extension=extension, content_type=content_type, width=width, height=height
    )
