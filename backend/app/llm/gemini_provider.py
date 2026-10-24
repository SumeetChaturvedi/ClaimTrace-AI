"""GeminiProvider — the first LLMProvider implementation, using Google's
official google-genai SDK. All Gemini-specific concerns (client
construction, request/response shapes, SDK exceptions) live in this module;
nothing outside app/llm/ should ever import google.genai.

Structurally this reuses the exact pattern app/agent/reasoning.py used for
its (now-removed) direct Anthropic integration: lazily construct and cache a
client, check configuration only when generate() is actually called (so
constructing a GeminiProvider never itself requires a key), and translate
SDK exceptions into one clean, provider-agnostic error type.
"""

from google import genai
from google.genai import types
from google.genai.errors import APIError

from app.config import get_settings
from app.llm.provider import GenerationResult, LLMProvider, LLMProviderError, Prompt

# Gemini's free API tier is Flash-model-friendly; kept configurable via
# Settings.gemini_model since exact free-tier model availability/naming
# changes over time — verify against current Google AI Studio pricing.
MAX_OUTPUT_TOKENS = 1024


class GeminiProvider(LLMProvider):
    """Generates text via the Gemini API. Lazily constructs and caches its
    client on first use, so instantiating this class never requires a
    configured API key — only calling generate() does."""

    def __init__(self) -> None:
        self._client: genai.Client | None = None

    def generate(self, prompt: Prompt) -> GenerationResult:
        """Send `prompt` to the configured Gemini model and return its text
        response verbatim, plus whether Gemini's own response metadata
        indicates the output was cut off by the model's output-token limit.
        Raises LLMProviderError if no API key is configured, or if the call
        fails."""
        settings = get_settings()
        api_key = (settings.gemini_api_key or "").strip()
        if not api_key:
            raise LLMProviderError(
                "No LLM is configured — set GEMINI_API_KEY in backend/.env "
                "to enable LLM-backed reasoning."
            )

        client = self._get_client(api_key)

        # Phase W2.3 (Multimodal Image Understanding): when no images are
        # attached, `contents` stays the exact bare string every existing
        # caller already sends -- byte-for-byte unchanged request shape,
        # confirmed by this module's own existing tests (test_gemini_provider.py)
        # asserting `kwargs["contents"] == "user-text"`. Only a Prompt with
        # images set (never produced by ReasoningEngine/EventExtractor)
        # builds the list-of-Parts shape the google-genai SDK's own
        # multimodal input mechanism expects (types.Part.from_bytes ->
        # inline_data/Blob -- confirmed present in the installed SDK).
        if prompt.images:
            contents = [types.Part.from_text(text=prompt.user_prompt)] + [
                types.Part.from_bytes(data=image.data, mime_type=image.mime_type) for image in prompt.images
            ]
        else:
            contents = prompt.user_prompt

        try:
            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=prompt.system_prompt,
                    # Per-call override (Phase 8B.2 Quality Remediation) if the
                    # caller set one (see Prompt.max_output_tokens's own
                    # docstring) — ReasoningEngine never sets this, so its
                    # calls are completely unaffected and keep using the
                    # shared MAX_OUTPUT_TOKENS exactly as before.
                    max_output_tokens=prompt.max_output_tokens or MAX_OUTPUT_TOKENS,
                ),
            )
        except APIError as exc:
            raise LLMProviderError(f"Gemini call failed: {exc}") from exc

        text = (response.text or "").strip()
        if not text:
            raise LLMProviderError("Gemini returned an empty response")
        return GenerationResult(text=text, truncated=_hit_output_token_limit(response))

    def _get_client(self, api_key: str) -> genai.Client:
        if self._client is None:
            self._client = genai.Client(api_key=api_key)
        return self._client


def _hit_output_token_limit(response: "types.GenerateContentResponse") -> bool:
    """Whether Gemini's own response metadata reports that the first
    candidate stopped because it hit its output-token budget
    (finish_reason == MAX_TOKENS) — the one reliable, provider-reported
    signal for "this text may be incomplete," as opposed to guessing from
    the text's length or proximity to a character limit. Defensively
    returns False (never raises, never guesses) if `response` doesn't have
    the expected shape at all -- a response missing this metadata is not
    evidence of truncation, only evidence that this signal is unavailable
    for it."""
    try:
        candidates = response.candidates
        if not candidates:
            return False
        return candidates[0].finish_reason == types.FinishReason.MAX_TOKENS
    except (AttributeError, IndexError, TypeError):
        return False
