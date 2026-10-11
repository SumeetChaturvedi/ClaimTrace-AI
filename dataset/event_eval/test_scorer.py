"""Tests for the standalone event-evaluation scorer (scorer.py), using the
deterministic candidate fixtures in candidate_fixtures.py — no Gemini
call, no production EventExtractor (none exists yet). Each test isolates
exactly one of the required edge cases from the Phase 8B.1 brief §5.

Run with:
    cd "ClaimTrace AI" && python3 -m unittest dataset.event_eval.test_scorer -v
"""

import unittest

from dataset.event_eval import candidate_fixtures as fx
from dataset.event_eval.dataset import DATASET
from dataset.event_eval.gold_schema import CandidateEvent
from dataset.event_eval.scorer import DEFAULT_THRESHOLDS, passes_thresholds, score


class GoodCandidatesScorePerfectlyTests(unittest.TestCase):
    """The baseline: a full, correct prediction set must score perfectly
    on every metric, and pass every default threshold."""

    @classmethod
    def setUpClass(cls):
        cls.report = score(DATASET, list(DATASET.gold_events), fx.GOOD_CANDIDATES)

    def test_perfect_recall_and_precision(self):
        self.assertEqual(self.report.recall, 1.0)
        self.assertEqual(self.report.precision, 1.0)

    def test_perfect_field_accuracies(self):
        self.assertEqual(self.report.event_type_accuracy, 1.0)
        self.assertEqual(self.report.date_accuracy, 1.0)
        self.assertEqual(self.report.date_basis_accuracy, 1.0)
        self.assertEqual(self.report.attribution_accuracy, 1.0)
        self.assertEqual(self.report.source_link_accuracy, 1.0)

    def test_zero_duplicate_and_unsupported_rates(self):
        self.assertEqual(self.report.duplicate_event_rate, 0.0)
        self.assertEqual(self.report.unsupported_event_rate, 0.0)

    def test_conflict_fully_preserved_and_abstention_perfect(self):
        self.assertEqual(self.report.conflict_groups_total, 1)
        self.assertEqual(self.report.conflict_preservation_rate, 1.0)
        self.assertEqual(self.report.abstention_rate, 1.0)

    def test_all_default_thresholds_pass(self):
        results = passes_thresholds(self.report, DEFAULT_THRESHOLDS)
        for metric, passed in results.items():
            self.assertTrue(passed, f"{metric} should pass with a perfect candidate set")

    def test_covers_every_scenario_including_multi_event_ones(self):
        # Every gold event (15, across 11 event-bearing scenarios) must be
        # matched — including S01/S02/S04/S05's two-events-per-scenario
        # cases and S06's attachment-sourced event.
        self.assertEqual(len(self.report.matched_pairs), 15)
        self.assertEqual(self.report.unmatched_gold, [])
        self.assertEqual(self.report.unmatched_candidates, [])


class MatchingRuleTests(unittest.TestCase):
    """Confirms the brief's explicit matching-rule requirement: a wrong or
    missing date/type must not turn an otherwise correctly identified
    event into a complete miss — only the specific field's own accuracy
    metric is affected."""

    def test_missing_date_does_not_cause_a_miss(self):
        report = score(DATASET, list(DATASET.gold_events), fx.MISSING_DATE_CANDIDATES)
        self.assertEqual(report.recall, 1.0, "the event must still be matched despite the missing date")
        self.assertLess(report.date_accuracy, 1.0, "date accuracy must still reflect the missing date")

    def test_correct_event_wrong_date_does_not_cause_a_miss(self):
        report = score(DATASET, list(DATASET.gold_events), fx.CORRECT_EVENT_WRONG_DATE_CANDIDATES)
        self.assertEqual(report.recall, 1.0)
        self.assertLess(report.date_accuracy, 1.0)
        # The event's other fields (type, source) must still score correctly —
        # a wrong date must not be allowed to drag down unrelated metrics.
        self.assertEqual(report.event_type_accuracy, 1.0)
        self.assertEqual(report.source_link_accuracy, 1.0)


class OneToOneMatchingIdentityTests(unittest.TestCase):
    """Pre-commit review regression: candidate identity during 1:1
    assignment must be tracked by each candidate's actual position in the
    input list, never by value equality. CandidateEvent is a frozen
    dataclass (field-value equality by default) — two independently
    submitted candidates that happen to carry identical field values must
    still be treated as two distinct predictions, each able to satisfy its
    own genuinely matching gold event, not silently collapsed onto one
    index via `list.index()`. See scorer.py's `_match` docstring for the
    full repro this test is based on."""

    def test_two_value_equal_candidates_each_satisfy_a_different_gold_event(self):
        from dataset.event_eval.gold_schema import CandidateEvent, GoldEvent, GoldSourceLocator

        g1 = GoldEvent(
            event_id="T1", scenario_id="T", expected_result="event",
            event_type="TYPE", assertion_type="recorded_action", description="d",
            event_date=None, event_date_basis="unknown", attributed_party=None,
            sources=(GoldSourceLocator("MA", "shared phrase plus unique tail A"),),
        )
        g2 = GoldEvent(
            event_id="T2", scenario_id="T", expected_result="event",
            event_type="TYPE", assertion_type="recorded_action", description="d",
            event_date=None, event_date_basis="unknown", attributed_party=None,
            sources=(GoldSourceLocator("MB", "shared phrase plus unique tail B"),),
        )
        # Two DISTINCT candidate objects with IDENTICAL field values —
        # c1 is c2 is False, but c1 == c2 is True.
        kwargs = dict(
            source_message_key="MA", excerpt="shared phrase", event_type="TYPE",
            assertion_type="recorded_action", event_date=None, event_date_basis="unknown", attributed_party=None,
        )
        c1 = CandidateEvent(**kwargs)
        c2 = CandidateEvent(**kwargs)
        self.assertEqual(c1, c2)
        self.assertIsNot(c1, c2)

        class _FakeDataset:
            scenario_ids = ("T",)
            resolved_text = {
                "MA": "shared phrase plus unique tail A",
                "MB": "shared phrase plus unique tail B",
            }
            noise_message_keys = frozenset()

        report = score(_FakeDataset(), [g1, g2], [c1, c2])
        self.assertEqual(report.recall, 1.0, "both gold events are genuinely satisfiable by one candidate each")
        self.assertEqual({pair.gold.event_id for pair in report.matched_pairs}, {"T1", "T2"})
        self.assertEqual(report.unmatched_gold, [])


class WrongSourceLinkTests(unittest.TestCase):
    """A plausible event linked to the wrong message must fail the
    source-link check specifically, separate from semantic event
    matching."""

    def test_wrong_source_link_fails_source_check_but_still_content_matches(self):
        gold = [e for e in DATASET.gold_events if e.scenario_id == "S06"]
        report = score(DATASET, gold, fx.WRONG_SOURCE_LINK_CANDIDATES)
        self.assertEqual(report.recall, 1.0, "content (passage) still overlaps the gold event, so it still matches")
        self.assertEqual(report.source_link_accuracy, 0.0, "but the claimed source is the covering email, not the attachment")
        self.assertEqual(len(report.wrong_source_link_pairs), 1)

    def test_wrong_source_link_also_fails_unsupported_check(self):
        # Documented co-failure (see scorer.py's module docstring): the
        # excerpt genuinely does not appear in the wrongly-claimed source.
        gold = [e for e in DATASET.gold_events if e.scenario_id == "S06"]
        report = score(DATASET, gold, fx.WRONG_SOURCE_LINK_CANDIDATES)
        self.assertEqual(report.unsupported_event_rate, 1.0)


class AttributionTests(unittest.TestCase):
    def test_wrong_attribution_lowers_attribution_accuracy_only(self):
        report = score(DATASET, list(DATASET.gold_events), fx.WRONG_ATTRIBUTION_CANDIDATES)
        self.assertEqual(report.recall, 1.0)
        self.assertLess(report.attribution_accuracy, 1.0)
        self.assertEqual(report.event_type_accuracy, 1.0)


class DuplicateEventRateTests(unittest.TestCase):
    def test_second_prediction_for_an_already_matched_event_counts_as_duplicate(self):
        report = score(DATASET, list(DATASET.gold_events), fx.DUPLICATE_PREDICTION_CANDIDATES)
        self.assertGreater(report.duplicate_event_rate, 0.0)
        self.assertLess(report.precision, 1.0, "the surplus candidate must count against precision")
        self.assertEqual(report.recall, 1.0, "the gold event itself is still correctly found")

    def test_duplicate_rate_formula_is_extras_over_matched_gold_count(self):
        report = score(DATASET, list(DATASET.gold_events), fx.DUPLICATE_PREDICTION_CANDIDATES)
        # Exactly one gold event (S01-E01) received a surplus candidate;
        # all 15 gold events were matched.
        self.assertEqual(report.duplicate_event_rate, 1 / 15)

    def test_two_legitimate_events_in_different_messages_of_one_scenario_are_not_duplicates(self):
        # Scenario 1 has two real, distinct gold events (the request and
        # the later response) in two different messages. Scoring just
        # that scenario's correct candidates must show zero duplicates.
        gold = [e for e in DATASET.gold_events if e.scenario_id == "S01"]
        candidates = [c for c in fx.GOOD_CANDIDATES if c.source_message_key in ("S01-M01", "S01-M02")]
        report = score(DATASET, gold, candidates)
        self.assertEqual(report.duplicate_event_rate, 0.0)
        self.assertEqual(report.recall, 1.0)
        self.assertEqual(report.precision, 1.0)


class UnsupportedEventTests(unittest.TestCase):
    def test_fabricated_excerpt_is_flagged_unsupported(self):
        report = score(DATASET, list(DATASET.gold_events), fx.UNSUPPORTED_EVENT_CANDIDATES)
        self.assertGreater(report.unsupported_event_rate, 0.0)
        last_index = len(fx.UNSUPPORTED_EVENT_CANDIDATES) - 1
        self.assertIn(last_index, report.unsupported_candidate_indices)

    def test_fabricated_excerpt_does_not_falsely_match_a_gold_event(self):
        report = score(DATASET, list(DATASET.gold_events), fx.UNSUPPORTED_EVENT_CANDIDATES)
        # It must not have been counted as a correct match for S01-E01 or
        # S02-E02 just because it shares a source message or plausible
        # wording — it should simply be an unmatched, unsupported extra.
        matched_candidate_excerpts = {pair.candidate.excerpt for pair in report.matched_pairs}
        self.assertNotIn(fx.UNSUPPORTED_EVENT_CANDIDATES[-1].excerpt, matched_candidate_excerpts)


class ConflictPreservationTests(unittest.TestCase):
    def test_omitting_one_side_of_a_conflict_fails_preservation(self):
        report = score(DATASET, list(DATASET.gold_events), fx.ONE_SIDE_OF_CONFLICT_OMITTED_CANDIDATES)
        self.assertEqual(report.conflict_groups_total, 1)
        self.assertEqual(report.conflict_preservation_rate, 0.0)
        # The omitted side must show up as an honest recall miss, not be
        # silently absorbed elsewhere.
        self.assertEqual(report.recall, 14 / 15)
        missed_ids = {g.event_id for g in report.unmatched_gold}
        self.assertEqual(missed_ids, {"S05-E02"})


class AbstentionTests(unittest.TestCase):
    def test_correct_abstention_on_pure_noise_scenario(self):
        report = score(DATASET, list(DATASET.gold_events), fx.GOOD_CANDIDATES)
        self.assertEqual(report.abstention_rate, 1.0)

    def test_incorrect_abstention_is_detected(self):
        report = score(DATASET, list(DATASET.gold_events), fx.INCORRECT_NO_EVENT_ABSTENTION_CANDIDATES)
        self.assertLess(report.abstention_rate, 1.0)
        self.assertLess(report.precision, 1.0, "the false-positive noise prediction must also cost precision")

    def test_empty_candidate_set_abstains_correctly_everywhere(self):
        report = score(DATASET, list(DATASET.gold_events), fx.EMPTY_CANDIDATES)
        self.assertEqual(report.abstention_rate, 1.0)
        self.assertEqual(report.recall, 0.0)
        self.assertEqual(report.precision, 1.0, "precision is vacuously 1.0 by convention when there are zero predictions — see scorer.py")


class ThresholdConfigurabilityTests(unittest.TestCase):
    def test_thresholds_are_configurable_not_hardcoded(self):
        from dataset.event_eval.scorer import Thresholds

        strict = Thresholds(min_recall=0.99)
        report = score(DATASET, list(DATASET.gold_events), fx.ONE_SIDE_OF_CONFLICT_OMITTED_CANDIDATES)
        results_default = passes_thresholds(report, DEFAULT_THRESHOLDS)
        results_strict = passes_thresholds(report, strict)
        # recall = 14/15 ≈ 0.933: passes the default 0.70 gate, fails a
        # stricter 0.99 gate — proves the threshold is actually consulted,
        # not a hardcoded pass/fail.
        self.assertTrue(results_default["recall"])
        self.assertFalse(results_strict["recall"])


class CandidateEventShapeTests(unittest.TestCase):
    def test_candidate_event_has_no_event_id_or_conflict_group_field(self):
        # CandidateEvent is deliberately a subset of GoldEvent's fields
        # (see gold_schema.py) — confirm this stays true rather than
        # silently growing identity/conflict fields no real extractor
        # output is required to supply in this phase.
        candidate = CandidateEvent(
            source_message_key="S01-M01",
            excerpt="x",
            event_type=None,
            assertion_type=None,
            event_date=None,
            event_date_basis=None,
            attributed_party=None,
        )
        self.assertFalse(hasattr(candidate, "event_id"))
        self.assertFalse(hasattr(candidate, "conflict_group_id"))


if __name__ == "__main__":
    unittest.main()
