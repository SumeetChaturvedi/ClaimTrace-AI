"""Sanity/integrity tests for the gold dataset itself (dataset.py) —
separate from test_scorer.py, which tests the scoring logic. These tests
would fail loudly if a future scenario edit introduced a gold-authoring
mistake (e.g. a passage that doesn't actually appear in its claimed
source) that dataset.py's own load-time validation didn't already catch
by raising.

Run with:
    cd "ClaimTrace AI" && python3 -m unittest dataset.event_eval.test_dataset -v
"""

import unittest

from dataset.event_eval.dataset import DATASET


class DatasetIntegrityTests(unittest.TestCase):
    def test_all_twelve_scenarios_present(self):
        self.assertEqual(
            DATASET.scenario_ids,
            ("S01", "S02", "S03", "S04", "S05", "S06", "S07", "S08", "S09", "S10", "S11", "S12"),
        )

    def test_every_gold_event_has_at_least_one_source(self):
        for event in DATASET.gold_events:
            self.assertGreater(len(event.sources), 0, event.event_id)

    def test_every_gold_source_message_key_is_a_real_fixture(self):
        for event in DATASET.gold_events:
            for source in event.sources:
                self.assertIn(source.message_key, DATASET.resolved_text, f"{event.event_id} -> {source.message_key}")

    def test_every_gold_passage_is_a_real_substring_of_its_source(self):
        # Redundant with dataset.load_dataset()'s own load-time check (which
        # would have already raised), but asserted again explicitly here so
        # this specific guarantee has its own named, independently-readable
        # test rather than relying solely on "the module imported without
        # raising."
        for event in DATASET.gold_events:
            for source in event.sources:
                self.assertIn(source.passage, DATASET.resolved_text[source.message_key], event.event_id)

    def test_scenario_12_has_no_gold_events(self):
        s12_events = [e for e in DATASET.gold_events if e.scenario_id == "S12"]
        self.assertEqual(s12_events, [])

    def test_noise_keys_are_never_cited_as_a_gold_source(self):
        sourced_keys = {source.message_key for event in DATASET.gold_events for source in event.sources}
        self.assertEqual(sourced_keys & DATASET.noise_message_keys, set())

    def test_conflict_scenario_has_two_events_sharing_one_conflict_group(self):
        conflict_events = [e for e in DATASET.gold_events if e.expected_result == "conflict"]
        self.assertEqual(len(conflict_events), 2)
        group_ids = {e.conflict_group_id for e in conflict_events}
        self.assertEqual(len(group_ids), 1)

    def test_attributed_assertion_scenarios_present_and_not_typed_as_fact(self):
        # The brief explicitly requires cases where the correct result is
        # an attributed allegation/assertion, not an absence of events —
        # confirm both S03 and S11 are represented this way, and neither
        # was (mis)typed as assertion_type="recorded_action".
        for scenario_id in ("S03", "S11"):
            events = [e for e in DATASET.gold_events if e.scenario_id == scenario_id]
            self.assertEqual(len(events), 1, scenario_id)
            self.assertEqual(events[0].expected_result, "attributed_assertion")
            self.assertEqual(events[0].assertion_type, "allegation")

    def test_attachment_event_sourced_from_attachment_not_covering_email(self):
        s06_event = next(e for e in DATASET.gold_events if e.scenario_id == "S06")
        self.assertEqual(s06_event.sources[0].message_key, "S06-ATT01")
        self.assertEqual(DATASET.attachment_parent["S06-ATT01"], "S06-M01")

    def test_unresolved_ambiguity_scenario_has_no_date(self):
        s08_event = next(e for e in DATASET.gold_events if e.scenario_id == "S08")
        self.assertIsNone(s08_event.event_date)
        self.assertEqual(s08_event.event_date_basis, "unknown")

    def test_event_date_differs_from_document_sent_date_in_late_report_scenario(self):
        s07_event = next(e for e in DATASET.gold_events if e.scenario_id == "S07")
        self.assertEqual(s07_event.event_date, "2024-02-10")
        # The message's own Date header (2024-03-15, visible in
        # scenario_07_late_received_email.py's build_eml call) is never
        # stored on GoldEvent at all in this phase's minimal schema — only
        # the body-stated event_date is — confirming the two dates are
        # genuinely never conflated anywhere in this dataset.
        self.assertNotEqual(s07_event.event_date, "2024-03-15")


if __name__ == "__main__":
    unittest.main()
