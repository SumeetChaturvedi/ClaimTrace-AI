"""The provider-independent LLM interface.

ReasoningEngine (app/agent/reasoning.py) depends only on what's in this
file — never on a specific provider's SDK, request format, or response
format. Adding a new provider (OpenAI, Anthropic, Ollama, Azure OpenAI, ...)
means creating one new module in this package that implements LLMProvider;
nothing outside app/llm/ should need to change.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ImagePart:
    """One raw image to attach to a prompt (Phase W2.3: Multimodal Image
    Understanding) -- `data` is the already-validated original image
    bytes, `mime_type` the real, server-detected content type (never a
    caller's claimed/guessed one). Provider-agnostic: how (or whether) a
    given LLMProvider actually sends this to its own API is entirely that
    provider's own concern."""

    data: bytes
    mime_type: str


@dataclass(frozen=True)
class Prompt:
    """A provider-agnostic prompt: fixed behavioral instructions
    (system_prompt) plus the actual investigation content to reason over
    (user_prompt). No provider-specific formatting lives here — each
    LLMProvider is responsible for translating this into whatever request
    shape its own API requires.

    max_output_tokens (Phase 8B.2 Quality Remediation): optional, per-call
    override of a provider's own default output budget. None (the default,
    and what ReasoningEngine's prompt always leaves it as) means "use the
    provider's own default" — GeminiProvider's shared, configurable
    Settings.gemini_max_output_tokens, unchanged, so ReasoningEngine's
    behavior/cost is completely unaffected by this field's existence. It
    exists so a caller with a
    genuinely different, structured-output task (EventExtractor, whose
    response is a JSON array that can legitimately need more room than a
    prose answer) can ask for more room WITHOUT silently raising the
    shared constant every other caller also relies on.

    images (Phase W2.3 Multimodal Image Understanding): optional, defaults
    to an empty tuple -- every existing caller (ReasoningEngine,
    EventExtractor) never sets this, so their requests are completely
    unaffected, byte-for-byte, by this field's existence. Only
    app/vision/gemini_vision.py constructs a Prompt with images set."""

    system_prompt: str
    user_prompt: str
    max_output_tokens: int | None = None
    images: tuple[ImagePart, ...] = ()


class LLMProviderError(Exception):
    """A clean, provider-agnostic generation failure: not configured, auth,
    network, empty response, etc. Providers catch their own SDK's exceptions
    and raise this instead, so callers never see a provider-specific
    exception type."""


@dataclass(frozen=True)
class GenerationResult:
    """A provider's response to one generate() call: the text itself, plus
    whether the provider's own metadata indicates the response was cut off
    before it naturally finished (e.g. an output-token-limit finish reason)
    — never inferred from the text's length or shape, only from the
    provider actually reporting it. `truncated` defaults to False, which is
    the correct, safe value whenever a provider has no such metadata to
    report at all (see GeminiProvider.generate() for the one concrete
    example of how this is populated); a caller must never treat `False`
    here as proof the response is complete if the provider genuinely can't
    tell, only as "nothing indicated otherwise."""

    text: str
    truncated: bool = False


class LLMProvider(ABC):
    """Minimal interface every LLM provider implements. Deliberately tiny —
    one method, one input type, one output type, no model-specific
    arguments, no provider-specific options — so swapping providers never
    requires changing anything that depends on this interface."""

    @abstractmethod
    def generate(self, prompt: Prompt) -> GenerationResult:
        """Generate a response for `prompt`. Raises LLMProviderError on any
        failure (not configured, auth, network, empty response, ...)."""
        raise NotImplementedError
