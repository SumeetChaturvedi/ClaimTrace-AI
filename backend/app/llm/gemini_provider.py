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
from app.llm.provider import LLMProvider, LLMProviderError, Prompt

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

    def generate(self, prompt: Prompt) -> str:
        """Send `prompt` to the configured Gemini model and return its text
        response verbatim. Raises LLMProviderError if no API key is
        configured, or if the call fails."""
        settings = get_settings()
        if not settings.gemini_api_key:
            raise LLMProviderError(
                "No LLM is configured — set GEMINI_API_KEY in backend/.env "
                "to enable LLM-backed reasoning."
            )

        client = self._get_client(settings.gemini_api_key)

        try:
            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=prompt.user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=prompt.system_prompt,
                    max_output_tokens=MAX_OUTPUT_TOKENS,
                ),
            )
        except APIError as exc:
            raise LLMProviderError(f"Gemini call failed: {exc}") from exc

        text = (response.text or "").strip()
        if not text:
            raise LLMProviderError("Gemini returned an empty response")
        return text

    def _get_client(self, api_key: str) -> genai.Client:
        if self._client is None:
            self._client = genai.Client(api_key=api_key)
        return self._client
