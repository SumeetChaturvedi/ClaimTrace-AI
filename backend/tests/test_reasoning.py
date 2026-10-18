"""Offline tests for ReasoningEngine's answer_truncated propagation (Phase 1
fix: Detect main-answer truncation), exercised against a FakeProvider that
returns a scripted GenerationResult instead of calling Gemini.

No network access, no database, no real LLM call — real-Gemini coverage of
GeminiProvider's own finish_reason detection lives in test_gemini_provider.py;
this file only checks that ReasoningEngine faithfully passes whatever the
provider reports through to ReasoningResult, without inferring anything of
its own from the answer text.

Run with:
    cd backend && source .venv/bin/activate
    PYTHONPATH=. python3 -m unittest tests.test_reasoning -v
"""

import unittest
from datetime import datetime, timezone

from app.agent.investigation_package import InvestigationPackage
from app.agent.models import Citation, Evidence
from app.agent.reasoning import ReasoningEngine, ReasoningError
from app.llm.provider import GenerationResult, LLMProvider, LLMProviderError, Prompt


class FakeProvider(LLMProvider):
    """Returns a pre-scripted GenerationResult (or raises) instead of
    calling Gemini."""

    def __init__(self, result: GenerationResult | None = None, error: str | None = None):
        self._result = result
        self._error = error

    def generate(self, prompt: Prompt) -> GenerationResult:
        if self._error is not None:
            raise LLMProviderError(self._error)
        return self._result


def _evidence() -> Evidence:
    return Evidence(
        citation=Citation(document_id=1, chunk_id=10, relevance_score=0.9, chunk_text="Relevant excerpt."),
        document_id=1,
        document_name="doc-1.pdf",
        excerpt="Relevant excerpt.",
        surrounding_context="Relevant excerpt.",
        confidence=0.9,
        metadata={},
    )


def _package(evidence: list[Evidence]) -> InvestigationPackage:
    return InvestigationPackage(
        question="What happened?",
        evidence=evidence,
        total_evidence=len(evidence),
        documents_considered=len({item.document_id for item in evidence}),
        generated_at=datetime.now(timezone.utc),
    )


class AnswerTruncationPropagationTests(unittest.TestCase):
    def test_provider_reported_truncation_sets_answer_truncated_true(self):
        provider = FakeProvider(result=GenerationResult(text="A cut-off answer", truncated=True))
        engine = ReasoningEngine(provider=provider)

        result = engine.reason(_package([_evidence()]))

        self.assertTrue(result.answer_truncated)
        self.assertEqual(result.answer, "A cut-off answer")

    def test_normal_completion_leaves_answer_truncated_false(self):
        provider = FakeProvider(result=GenerationResult(text="A complete answer", truncated=False))
        engine = ReasoningEngine(provider=provider)

        result = engine.reason(_package([_evidence()]))

        self.assertFalse(result.answer_truncated)

    def test_no_evidence_shortcut_is_never_marked_truncated(self):
        """The no-evidence path makes no provider call at all -- there is
        nothing for a provider to report truncation about."""
        provider = FakeProvider(error="should never be called")
        engine = ReasoningEngine(provider=provider)

        result = engine.reason(_package([]))

        self.assertFalse(result.answer_truncated)

    def test_provider_error_is_not_confused_with_truncation(self):
        """A hard provider failure raises ReasoningError; it must never be
        reported as a (silently empty/truncated) answer instead."""
        provider = FakeProvider(error="Gemini call failed: simulated outage")
        engine = ReasoningEngine(provider=provider)

        with self.assertRaises(ReasoningError):
            engine.reason(_package([_evidence()]))


if __name__ == "__main__":
    unittest.main()
