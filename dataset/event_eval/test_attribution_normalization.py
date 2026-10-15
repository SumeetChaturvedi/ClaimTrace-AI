"""Tests for attribution_accuracy_normalized (scorer.py, Phase 8B.2 Quality
Remediation) — a separate, additive function alongside score()'s own
exact-string attribution_accuracy, not a modification of it. See that
function's own docstring for the rationale (the gold dataset's
"(Organization)" suffix is a labeling convention, not something every
fixture's evidence text explicitly restates).

Kept in its own file rather than appended to the already-committed
test_scorer.py, so that file's own diff for this task stays zero.

Run with (from the repository root):
    python3 -m unittest dataset.event_eval.test_attribution_normalization -v
"""

import unittest

from dataset.event_eval.gold_schema import CandidateEvent, GoldEvent, GoldSourceLocator
from dataset.event_eval.scorer import EvaluationReport, MatchedPair, attribution_accuracy_normalized


def _gold(event_id: str, attributed_party: str | None) -> GoldEvent:
    return GoldEvent(
        event_id=event_id,
        scenario_id="SX",
        expected_result="event",
        event_type=None,
        assertion_type=None,
        description="fixture",
        event_date=None,
        event_date_basis="unknown",
        attributed_party=attributed_party,
        sources=(GoldSourceLocator("SX-M01", "fixture passage"),),
    )


def _candidate(attributed_party: str | None) -> CandidateEvent:
    return CandidateEvent(
        source_message_key="SX-M01",
        excerpt="fixture passage",
        event_type=None,
        assertion_type=None,
        event_date=None,
        event_date_basis=None,
        attributed_party=attributed_party,
    )


def _report_with_pairs(pairs: list[tuple[GoldEvent, CandidateEvent]]) -> EvaluationReport:
    matched = [MatchedPair(gold=g, candidate=c, matched_source_message_key="SX-M01") for g, c in pairs]
    return EvaluationReport(scenario_ids=("SX",), total_gold_events=len(pairs), total_candidates=len(pairs), matched_pairs=matched)


class BareNameMatchesOrgSuffixTests(unittest.TestCase):
    def test_bare_name_matches_gold_with_org_suffix(self):
        report = _report_with_pairs([
            (_gold("E1", "Priya Nandan (Sagara Contracting)"), _candidate("Priya Nandan")),
        ])
        self.assertEqual(attribution_accuracy_normalized(report), 1.0)

    def test_exact_match_with_org_suffix_still_matches(self):
        report = _report_with_pairs([
            (_gold("E1", "Priya Nandan (Sagara Contracting)"), _candidate("Priya Nandan (Sagara Contracting)")),
        ])
        self.assertEqual(attribution_accuracy_normalized(report), 1.0)


class DoesNotConflatePartiesTests(unittest.TestCase):
    def test_different_person_still_fails_even_after_stripping_suffix(self):
        report = _report_with_pairs([
            (_gold("E1", "Priya Nandan (Sagara Contracting)"), _candidate("David Okonkwo")),
        ])
        self.assertEqual(attribution_accuracy_normalized(report), 0.0)

    def test_null_attribution_still_fails(self):
        report = _report_with_pairs([
            (_gold("E1", "Priya Nandan (Sagara Contracting)"), _candidate(None)),
        ])
        self.assertEqual(attribution_accuracy_normalized(report), 0.0)

    def test_wrong_party_entirely_still_fails(self):
        report = _report_with_pairs([
            (_gold("E1", "Priya Nandan (Sagara Contracting)"), _candidate("Employer's Representative")),
        ])
        self.assertEqual(attribution_accuracy_normalized(report), 0.0)


class VacuousAndMixedTests(unittest.TestCase):
    def test_no_gold_attribution_at_all_returns_none(self):
        report = _report_with_pairs([(_gold("E1", None), _candidate("Anyone"))])
        self.assertIsNone(attribution_accuracy_normalized(report))

    def test_mixed_correct_and_incorrect_averages_correctly(self):
        report = _report_with_pairs([
            (_gold("E1", "Priya Nandan (Sagara Contracting)"), _candidate("Priya Nandan")),
            (_gold("E2", "David Okonkwo (Meridian Consult)"), _candidate("Someone Else")),
        ])
        self.assertEqual(attribution_accuracy_normalized(report), 0.5)


if __name__ == "__main__":
    unittest.main()
