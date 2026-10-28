"""Offline tests for EventExtractor (Phase 8B.2) — the deterministic
parsing/validation logic in app/agent/event_extraction.py, exercised against
a FakeProvider that returns pre-scripted text instead of calling Gemini.
No network access, no database, no real LLM call: these tests validate the
contract "never trust document_id/chunk_id/excerpt without checking them
against the evidence actually supplied" directly, by constructing
adversarial model responses no real extraction-quality test could reliably
reproduce on demand.

Real-Gemini integration (does extraction actually work end-to-end against
a real investigation) is covered separately in test_investigations.py
(which already runs two real investigations end-to-end) and in the Phase
8B.2 production evaluation run against dataset/event_eval's fixtures.

Run with:
    cd backend && source .venv/bin/activate
    PYTHONPATH=. python3 -m unittest tests.test_event_extraction -v
"""

import json
import unittest

from app.agent.event_extraction import EventExtractionError, EventExtractor
from app.agent.models import Citation, Evidence
from app.llm.provider import GenerationResult, LLMProvider, LLMProviderError, Prompt


class FakeProvider(LLMProvider):
    """Returns pre-scripted text (or raises) instead of calling Gemini."""

    def __init__(self, response: str | None = None, error: str | None = None):
        self._response = response
        self._error = error

    def generate(self, prompt: Prompt) -> GenerationResult:
        if self._error is not None:
            raise LLMProviderError(self._error)
        return GenerationResult(text=self._response)


def _evidence(document_id: int, chunk_id: int, chunk_text: str) -> Evidence:
    return Evidence(
        citation=Citation(document_id=document_id, chunk_id=chunk_id, relevance_score=0.9, chunk_text=chunk_text),
        document_id=document_id,
        document_name=f"doc-{document_id}.pdf",
        excerpt=chunk_text[:50],
        surrounding_context=chunk_text,
        confidence=0.9,
        metadata={},
    )


GOOD_EVIDENCE = _evidence(1, 10, "We request clarification on drawing A-101 by March 3, 2024.")


class NoEvidenceTests(unittest.TestCase):
    def test_empty_evidence_returns_empty_list_without_calling_provider(self):
        extractor = EventExtractor(provider=FakeProvider(error="should never be called"))
        self.assertEqual(extractor.extract("question", []).events, [])


class ProviderFailureTests(unittest.TestCase):
    def test_provider_error_raises_event_extraction_error(self):
        extractor = EventExtractor(provider=FakeProvider(error="no API key"))
        with self.assertRaises(EventExtractionError):
            extractor.extract("question", [GOOD_EVIDENCE])

    def test_non_json_prose_response_raises_event_extraction_error(self):
        extractor = EventExtractor(provider=FakeProvider(response="I cannot find any events here."))
        with self.assertRaises(EventExtractionError):
            extractor.extract("question", [GOOD_EVIDENCE])


class ValidExtractionTests(unittest.TestCase):
    def test_well_formed_single_event_is_returned(self):
        response = json.dumps([{
            "document_id": 1, "chunk_id": 10,
            "excerpt": "We request clarification on drawing A-101 by March 3, 2024.",
            "event_type": "CLARIFICATION_REQUESTED", "assertion_type": "request",
            "description": "Clarification requested", "event_date": "2024-03-03",
            "event_date_basis": "explicit", "attributed_party": "Contractor",
        }])
        extractor = EventExtractor(provider=FakeProvider(response=response))
        events = extractor.extract("question", [GOOD_EVIDENCE]).events
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].document_id, 1)
        self.assertEqual(events[0].chunk_id, 10)
        self.assertEqual(events[0].event_type, "CLARIFICATION_REQUESTED")

    def test_empty_array_response_is_zero_events_not_an_error(self):
        extractor = EventExtractor(provider=FakeProvider(response="[]"))
        self.assertEqual(extractor.extract("question", [GOOD_EVIDENCE]).events, [])

    def test_response_wrapped_in_markdown_fence_is_still_parsed(self):
        response = "```json\n[]\n```"
        extractor = EventExtractor(provider=FakeProvider(response=response))
        self.assertEqual(extractor.extract("question", [GOOD_EVIDENCE]).events, [])

    def test_multiple_events_from_one_source_chunk_are_all_returned(self):
        text = "The contractor sent a notice on March 1. The engineer replied on March 10."
        evidence = _evidence(2, 20, text)
        response = json.dumps([
            {"document_id": 2, "chunk_id": 20, "excerpt": "The contractor sent a notice on March 1.",
             "event_type": "NOTICE_SUBMITTED", "assertion_type": "recorded_action",
             "description": "Notice sent", "event_date": "2024-03-01",
             "event_date_basis": "explicit", "attributed_party": "Contractor"},
            {"document_id": 2, "chunk_id": 20, "excerpt": "The engineer replied on March 10.",
             "event_type": "CLARIFICATION_PROVIDED", "assertion_type": "recorded_action",
             "description": "Engineer replied", "event_date": "2024-03-10",
             "event_date_basis": "explicit", "attributed_party": "Engineer"},
        ])
        extractor = EventExtractor(provider=FakeProvider(response=response))
        events = extractor.extract("question", [evidence]).events
        self.assertEqual(len(events), 2)


class SourceVerificationTests(unittest.TestCase):
    """Phase 8B.2's core safety requirement: never trust a candidate's
    document_id/chunk_id/excerpt without checking it against evidence that
    was really supplied for this call."""

    def test_candidate_citing_a_document_id_not_in_the_supplied_evidence_is_dropped(self):
        response = json.dumps([{
            "document_id": 999, "chunk_id": 10, "excerpt": "fabricated",
            "event_type": None, "assertion_type": None, "description": "x",
            "event_date": None, "event_date_basis": "unknown", "attributed_party": None,
        }])
        extractor = EventExtractor(provider=FakeProvider(response=response))
        self.assertEqual(extractor.extract("question", [GOOD_EVIDENCE]).events, [])

    def test_candidate_with_real_document_id_but_wrong_chunk_id_is_dropped(self):
        response = json.dumps([{
            "document_id": 1, "chunk_id": 999, "excerpt": "We request clarification",
            "event_type": None, "assertion_type": None, "description": "x",
            "event_date": None, "event_date_basis": "unknown", "attributed_party": None,
        }])
        extractor = EventExtractor(provider=FakeProvider(response=response))
        self.assertEqual(extractor.extract("question", [GOOD_EVIDENCE]).events, [])

    def test_candidate_whose_excerpt_is_not_a_genuine_substring_is_dropped(self):
        response = json.dumps([{
            "document_id": 1, "chunk_id": 10, "excerpt": "This text does not appear anywhere in the chunk.",
            "event_type": None, "assertion_type": None, "description": "x",
            "event_date": None, "event_date_basis": "unknown", "attributed_party": None,
        }])
        extractor = EventExtractor(provider=FakeProvider(response=response))
        self.assertEqual(extractor.extract("question", [GOOD_EVIDENCE]).events, [])

    def test_one_valid_and_one_fabricated_candidate_keeps_only_the_valid_one(self):
        response = json.dumps([
            {"document_id": 1, "chunk_id": 10, "excerpt": "We request clarification on drawing A-101",
             "event_type": "CLARIFICATION_REQUESTED", "assertion_type": "request", "description": "ok",
             "event_date": "2024-03-03", "event_date_basis": "explicit", "attributed_party": "Contractor"},
            {"document_id": 1, "chunk_id": 10, "excerpt": "fabricated text not in the chunk at all",
             "event_type": None, "assertion_type": None, "description": "bad",
             "event_date": None, "event_date_basis": "unknown", "attributed_party": None},
        ])
        extractor = EventExtractor(provider=FakeProvider(response=response))
        events = extractor.extract("question", [GOOD_EVIDENCE]).events
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].excerpt, "We request clarification on drawing A-101")

    def test_candidate_missing_a_required_key_is_dropped(self):
        response = json.dumps([{"document_id": 1, "chunk_id": 10}])  # no excerpt
        extractor = EventExtractor(provider=FakeProvider(response=response))
        self.assertEqual(extractor.extract("question", [GOOD_EVIDENCE]).events, [])


class VocabularyNormalizationTests(unittest.TestCase):
    def test_unrecognized_event_type_is_normalized_to_none_not_dropped(self):
        response = json.dumps([{
            "document_id": 1, "chunk_id": 10, "excerpt": "We request clarification",
            "event_type": "SOMETHING_NOT_IN_THE_VOCABULARY", "assertion_type": "request",
            "description": "x", "event_date": None, "event_date_basis": "unknown", "attributed_party": None,
        }])
        extractor = EventExtractor(provider=FakeProvider(response=response))
        events = extractor.extract("question", [GOOD_EVIDENCE]).events
        self.assertEqual(len(events), 1)
        self.assertIsNone(events[0].event_type)

    def test_unparseable_date_falls_back_to_unknown_basis_and_null_date(self):
        response = json.dumps([{
            "document_id": 1, "chunk_id": 10, "excerpt": "We request clarification",
            "event_type": None, "assertion_type": None, "description": "x",
            "event_date": "next Tuesday", "event_date_basis": "explicit", "attributed_party": None,
        }])
        extractor = EventExtractor(provider=FakeProvider(response=response))
        events = extractor.extract("question", [GOOD_EVIDENCE]).events
        self.assertEqual(len(events), 1)
        self.assertIsNone(events[0].event_date)
        self.assertEqual(events[0].event_date_basis, "unknown")


class TruncationToleranceTests(unittest.TestCase):
    """Gemini's shared output-token cap (Settings.gemini_max_output_tokens)
    can truncate a long array mid-object (observed against real
    investigation evidence during this phase's own regression run).
    Complete leading objects must be kept."""

    def test_truncated_array_salvages_complete_leading_objects(self):
        complete_object = (
            '{"document_id": 1, "chunk_id": 10, "excerpt": "We request clarification on drawing A-101", '
            '"event_type": "CLARIFICATION_REQUESTED", "assertion_type": "request", "description": "ok", '
            '"event_date": "2024-03-03", "event_date_basis": "explicit", "attributed_party": "Contractor"}'
        )
        truncated_tail = '{"document_id": 1, "chunk_id": 10, "exce'  # cut off mid-string
        response = f"[{complete_object}, {truncated_tail}"  # no closing ']' at all
        extractor = EventExtractor(provider=FakeProvider(response=response))
        result = extractor.extract("question", [GOOD_EVIDENCE])
        self.assertEqual(len(result.events), 1)

    def test_truncated_with_no_complete_object_at_all_raises(self):
        response = '[{"document_id": 1, "chunk_id'
        extractor = EventExtractor(provider=FakeProvider(response=response))
        with self.assertRaises(EventExtractionError):
            extractor.extract("question", [GOOD_EVIDENCE])

    def test_truncated_result_sets_truncated_flag_true(self):
        """Quality Remediation requirement: a partial result must be
        distinguishable from a complete one, not just logged."""
        complete_object = (
            '{"document_id": 1, "chunk_id": 10, "excerpt": "We request clarification on drawing A-101", '
            '"event_type": "CLARIFICATION_REQUESTED", "assertion_type": "request", "description": "ok", '
            '"event_date": "2024-03-03", "event_date_basis": "explicit", "attributed_party": "Contractor"}'
        )
        response = f"[{complete_object}, {{\"document_id\": 1, \"chunk_id\": 10, \"exce"
        extractor = EventExtractor(provider=FakeProvider(response=response))
        result = extractor.extract("question", [GOOD_EVIDENCE])
        self.assertTrue(result.truncated)

    def test_complete_array_sets_truncated_flag_false(self):
        extractor = EventExtractor(provider=FakeProvider(response="[]"))
        result = extractor.extract("question", [GOOD_EVIDENCE])
        self.assertFalse(result.truncated)

    def test_empty_evidence_result_is_not_truncated(self):
        extractor = EventExtractor(provider=FakeProvider(error="should never be called"))
        result = extractor.extract("question", [])
        self.assertFalse(result.truncated)


class OutputBudgetTests(unittest.TestCase):
    """Quality Remediation §6: EventExtractor must request a larger,
    extraction-specific output budget via Prompt.max_output_tokens, without
    touching the shared constant ReasoningEngine relies on (that constant
    lives in app/llm/gemini_provider.py and is never imported or modified
    by this module)."""

    def test_extract_requests_a_larger_than_default_output_budget(self):
        captured: dict[str, Prompt] = {}

        class CapturingProvider(LLMProvider):
            def generate(self, prompt: Prompt) -> GenerationResult:
                captured["prompt"] = prompt
                return GenerationResult(text="[]")

        extractor = EventExtractor(provider=CapturingProvider())
        extractor.extract("question", [GOOD_EVIDENCE])
        self.assertIsNotNone(captured["prompt"].max_output_tokens)
        self.assertGreater(captured["prompt"].max_output_tokens, 1024)


class AmbiguousAndSourceDateTests(unittest.TestCase):
    """Email sent-date-vs-event-date and ambiguity requirements are enforced
    by the PROMPT (instructing the model never to equate the two and never
    to resolve a relative date) rather than by this layer re-deriving dates
    itself — this layer's job is only to validate whatever date/basis the
    model returned is well-formed, which these cases check."""

    def test_event_date_basis_unknown_forces_event_date_to_none_even_if_model_supplied_one(self):
        response = json.dumps([{
            "document_id": 1, "chunk_id": 10, "excerpt": "We request clarification",
            "event_type": None, "assertion_type": None, "description": "x",
            "event_date": "2024-03-03", "event_date_basis": "unknown", "attributed_party": None,
        }])
        extractor = EventExtractor(provider=FakeProvider(response=response))
        events = extractor.extract("question", [GOOD_EVIDENCE]).events
        self.assertIsNone(events[0].event_date)

    def test_invalid_date_basis_value_normalizes_to_unknown(self):
        response = json.dumps([{
            "document_id": 1, "chunk_id": 10, "excerpt": "We request clarification",
            "event_type": None, "assertion_type": None, "description": "x",
            "event_date": None, "event_date_basis": "sometime", "attributed_party": None,
        }])
        extractor = EventExtractor(provider=FakeProvider(response=response))
        events = extractor.extract("question", [GOOD_EVIDENCE]).events
        self.assertEqual(events[0].event_date_basis, "unknown")


class DuplicateCandidateTests(unittest.TestCase):
    """Design decision (Phase 8B.2 report §10): EventExtractor does not
    deduplicate candidates itself. Duplicate-event RATE is an evaluation-
    time quality metric (dataset/event_eval/scorer.py's own
    duplicate_event_rate, computed against gold matches) describing how
    often a real extractor over-produces for one gold event — collapsing
    duplicates here, before that measurement, would hide the exact signal
    that metric exists to surface. Each independently-verified candidate
    is kept, even if two are identical."""

    def test_two_identical_candidates_are_both_kept_not_deduplicated(self):
        candidate = {
            "document_id": 1, "chunk_id": 10, "excerpt": "We request clarification on drawing A-101",
            "event_type": "CLARIFICATION_REQUESTED", "assertion_type": "request", "description": "ok",
            "event_date": "2024-03-03", "event_date_basis": "explicit", "attributed_party": "Contractor",
        }
        response = json.dumps([candidate, dict(candidate)])
        extractor = EventExtractor(provider=FakeProvider(response=response))
        events = extractor.extract("question", [GOOD_EVIDENCE]).events
        self.assertEqual(len(events), 2)


if __name__ == "__main__":
    unittest.main()
