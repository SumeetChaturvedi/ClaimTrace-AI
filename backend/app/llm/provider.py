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
class Prompt:
    """A provider-agnostic prompt: fixed behavioral instructions
    (system_prompt) plus the actual investigation content to reason over
    (user_prompt). No provider-specific formatting lives here — each
    LLMProvider is responsible for translating this into whatever request
    shape its own API requires."""

    system_prompt: str
    user_prompt: str


class LLMProviderError(Exception):
    """A clean, provider-agnostic generation failure: not configured, auth,
    network, empty response, etc. Providers catch their own SDK's exceptions
    and raise this instead, so callers never see a provider-specific
    exception type."""


class LLMProvider(ABC):
    """Minimal interface every LLM provider implements. Deliberately tiny —
    one method, one input type, one output type, no model-specific
    arguments, no provider-specific options — so swapping providers never
    requires changing anything that depends on this interface."""

    @abstractmethod
    def generate(self, prompt: Prompt) -> str:
        """Generate a text response for `prompt`. Raises LLMProviderError on
        any failure (not configured, auth, network, empty response, ...)."""
        raise NotImplementedError
