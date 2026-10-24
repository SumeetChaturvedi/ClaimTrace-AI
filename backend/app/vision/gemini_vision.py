"""Local wrapper around the configured LLMProvider for one-image visual
description (Phase W2.3: Multimodal Image Understanding) -- the ONLY
place in this phase that actually calls out to Gemini with image bytes.
Mirrors app/ocr/tesseract_provider.py's own shape (a single run_*()
function returning a plain, never-raising outcome dataclass) so
app/vision/process_pending.py can reuse the exact same claim/lease/
commit/restore structure app/ocr/process_pending.py already uses for
Tesseract -- this module is the one thing that's genuinely different
between the two phases.

Model compatibility (deliberately NOT assumed): settings.gemini_model
defaults to "gemini-flash-lite-latest". Whether this specific model
accepts image input is NOT verified by this module, and no live API call
is made to check it -- that must be confirmed against Google's own,
current Gemini API model-capability documentation before this is relied
on in production. If the configured model does not actually support
image input, Gemini's own API will reject the request; this module
treats that exactly like any other provider failure (see
generate_visual_description()'s own docstring) -- a clean 'failed'
outcome, never a crash, and never a fabricated description.

Never logs image bytes, the constructed prompt text, or the full model
response -- only the outcome status and a short, provider-reported error
string, mirroring every other logger.warning() call already in this
codebase (see tesseract_provider.py's own docstring for the same
principle)."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.config import get_settings
from app.llm.gemini_provider import GeminiProvider
from app.llm.provider import ImagePart, LLMProvider, LLMProviderError, Prompt

logger = logging.getLogger(__name__)

VISION_MODEL_NAME = "gemini"

# A single, fixed system prompt -- not user- or investigation-specific,
# since this runs once per image, independent of any particular
# investigation question (see the W2.3 architecture report's own
# "Option B" rationale: a persisted, reusable description, not an
# on-demand one). Explicitly instructed to describe only what is
# directly observable and to avoid every category of unsupported
# inference the product objective calls out.
_SYSTEM_PROMPT = (
    "You are describing a photograph preserved as evidence in a construction-claims "
    "investigation. Describe only what is directly, visually observable in the image: "
    "objects, equipment, materials, visible damage or defects, incomplete work, and general "
    "site conditions. Be concise (2-4 sentences).\n\n"
    "Do not state or guess: dates, times, locations, the identity of any person, exact "
    "measurements, the cause of anything you see, who is responsible for anything, or any "
    "contractual meaning or conclusion. If something is unclear, ambiguous, or you are not "
    "confident, say so explicitly rather than guessing. If the image contains no construction-"
    "relevant visual content, say that plainly instead of inventing a description."
)
_USER_PROMPT = "Describe the directly observable visual content of this image."


@dataclass(frozen=True)
class VisionRunResult:
    """The outcome of generate_visual_description() below. Mirrors
    app/ocr/tesseract_provider.py's OcrRunResult shape exactly.
    `status='completed'` always carries `text` (possibly empty/
    whitespace-only -- a genuine, honest "nothing describable" result,
    never an error); `status='failed'` always carries `error`. Never
    raises."""

    status: str  # 'completed' | 'failed'
    text: str | None = None
    error: str | None = None
    model: str = VISION_MODEL_NAME
    model_version: str | None = None


def generate_visual_description(
    content: bytes,
    *,
    mime_type: str,
    provider: LLMProvider | None = None,
) -> VisionRunResult:
    """Ask the configured LLMProvider to describe `content` (already-
    validated, already-preserved image bytes; the caller -- app/vision/
    process_pending.py -- is responsible for re-running
    app/ingestion/image_validation.py's validate_image() immediately
    before this call, mirroring run_ocr()'s own division of
    responsibility) and the configured image-size limit
    (settings.vision_max_image_bytes) BEFORE this call.

    `provider` defaults to a fresh GeminiProvider; injectable for tests
    only -- production code never passes it.

    Never raises: a missing API key, a provider/network error, or (if
    the configured model genuinely doesn't accept image input) an API
    rejection all come back as a plain, honest `status='failed'`
    VisionRunResult, exactly mirroring run_ocr()'s own "never guess,
    never crash the caller's batch" convention."""
    settings = get_settings()
    model_version = settings.gemini_model
    llm_provider = provider if provider is not None else GeminiProvider()

    prompt = Prompt(
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=_USER_PROMPT,
        images=(ImagePart(data=content, mime_type=mime_type),),
    )

    try:
        result = llm_provider.generate(prompt)
    except LLMProviderError as exc:
        logger.warning("Visual description request failed: %s", exc)
        return VisionRunResult(status="failed", error=str(exc), model_version=model_version)

    return VisionRunResult(status="completed", text=result.text or "", model_version=model_version)
