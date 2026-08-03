"""The Reasoning Engine — the component that decides what an investigation's
evidence means. Kept fully independent of InvestigationService
(app/agent/service.py) AND of any specific LLM provider: it depends only on
the LLMProvider interface (app/llm/provider.py), never on a provider's SDK,
request format, or response format.

Swapping providers (Gemini -> OpenAI, Anthropic, Ollama, Azure OpenAI, ...)
means creating one new app/llm/<provider>_provider.py module implementing
LLMProvider, then changing the one default-construction line below (or
simply injecting a different provider via the constructor) — nothing else in
this file, or anywhere upstream of it, needs to change. That default import
is the only place this module references a concrete provider; reason()
itself calls only LLMProvider.generate(), never anything Gemini-specific.

Prompt text lives entirely in PromptBuilder (app/agent/prompt_builder.py) —
this module never constructs prompt strings itself, only calls
build_reasoning_prompt() and passes the resulting Prompt to the provider.

Safety invariant: the LLM only ever generates the natural-language `answer`
string. Citations/supporting_evidence always come from the
InvestigationPackage that was built deterministically upstream — the
provider's response is never parsed for citations, evidence, or facts beyond
that one string, so it cannot fabricate or select evidence.

Citation verification (Sprint 4 Task 03): before supporting_evidence is
returned, it's passed through verify_citations()
(app/agent/citation_verification.py) — a deterministic, LLM-free check that
each citation is well-formed and really backed by a database row, dropping
any that aren't. Citations here always originate from package.evidence
anyway (per the safety invariant above), so this is defense-in-depth against
that invariant ever being violated, not a response to a known way it
currently is.
"""

from app.agent.citation_verification import verify_citations
from app.agent.investigation_package import InvestigationPackage
from app.agent.models import ReasoningResult
from app.agent.prompt_builder import PromptBuilder
from app.llm.gemini_provider import GeminiProvider
from app.llm.provider import LLMProvider, LLMProviderError


class ReasoningError(Exception):
    """Raised when reasoning can't complete: no provider configured, or the
    generation call itself failed. Wraps LLMProviderError so callers outside
    this module never need to know a provider-specific exception type
    exists — this is the one exception type ReasoningEngine has ever raised,
    unchanged since before providers were pluggable."""


class ReasoningEngine:
    """Turns an InvestigationPackage into a ReasoningResult by ranking its
    evidence, building a provider-agnostic Prompt (via PromptBuilder), and
    asking the configured LLMProvider to generate an answer grounded in that
    evidence. Depends only on the LLMProvider interface — never imports or
    references any provider's SDK, request shape, or exception types."""

    def __init__(
        self,
        provider: LLMProvider | None = None,
        prompt_builder: PromptBuilder | None = None,
    ) -> None:
        self._provider = provider or GeminiProvider()
        self._prompt_builder = prompt_builder or PromptBuilder()

    def reason(self, package: InvestigationPackage) -> ReasoningResult:
        """Rank package.evidence by confidence and, if there is any, ask the
        configured provider to answer package.question grounded in that
        evidence. With no evidence, returns the same deterministic "no
        evidence" result as before and makes no provider call at all —
        there would be nothing for the model to ground an answer in."""
        if not package.evidence:
            return ReasoningResult(
                answer="No relevant evidence was found for this investigation question.",
                reasoning_steps=[
                    "Searched for relevant evidence.",
                    "No supporting evidence was found for this question.",
                ],
                supporting_evidence=[],
            )

        ranked_evidence = sorted(package.evidence, key=lambda item: item.confidence, reverse=True)
        ranked_package = package.model_copy(update={"evidence": ranked_evidence})

        prompt = self._prompt_builder.build_reasoning_prompt(ranked_package)

        try:
            answer = self._provider.generate(prompt)
        except LLMProviderError as exc:
            raise ReasoningError(str(exc)) from exc

        candidate_citations = [item.citation for item in ranked_evidence]
        verified_citations = verify_citations(candidate_citations, retrieved_evidence=candidate_citations)

        return ReasoningResult(
            answer=answer,
            reasoning_steps=[
                "Retrieved relevant evidence.",
                "Ranked evidence by confidence.",
                "Selected the highest-confidence supporting evidence.",
                "Generated an answer using the configured language model, grounded in that evidence.",
                "Verified each citation against the database before returning it.",
            ],
            supporting_evidence=verified_citations,
        )
