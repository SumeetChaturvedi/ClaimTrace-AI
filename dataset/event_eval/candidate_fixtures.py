"""Deterministic candidate-prediction fixtures used by test_scorer.py.

No Gemini call, no production EventExtractor (none exists yet — Phase
8B.2). These are hand-built CandidateEvent lists standing in for what a
real extractor's output would look like, specifically shaped to exercise
each required edge case from the Phase 8B.1 brief §5: missing dates,
wrong source links, incorrect attribution, a correct event with an
incorrect date, a gold event predicted multiple times, unsupported event
descriptions, one side of a conflict omitted, and incorrect no-event
abstention.
"""

from __future__ import annotations

from dataset.event_eval.dataset import DATASET
from dataset.event_eval.gold_schema import CandidateEvent


def _candidate_from_gold(event_id: str, **overrides) -> CandidateEvent:
    """Build a candidate that would exactly match the named gold event,
    then apply field overrides — the standard way these fixtures introduce
    one deliberate flaw at a time while leaving everything else correct,
    so a test can attribute a metric change to exactly one cause."""
    gold = next(e for e in DATASET.gold_events if e.event_id == event_id)
    source = gold.sources[0]
    base = dict(
        source_message_key=source.message_key,
        excerpt=source.passage,
        event_type=gold.event_type,
        assertion_type=gold.assertion_type,
        event_date=gold.event_date,
        event_date_basis=gold.event_date_basis,
        attributed_party=gold.attributed_party,
    )
    base.update(overrides)
    return CandidateEvent(**base)


# -- A full, correct prediction set: one accurate candidate per gold event,
# covering every scenario (including S01/S02/S04/S05's "two legitimate
# events in one scenario/thread" cases, and S06's attachment-sourced
# event) and zero predictions for any noise message_key. Used as the
# "everything should score perfectly" baseline.
GOOD_CANDIDATES: list[CandidateEvent] = [_candidate_from_gold(event.event_id) for event in DATASET.gold_events]


# -- Individual edge-case fixtures, each GOOD_CANDIDATES with exactly one
# deliberate flaw (or a response to a different prompt entirely), so each
# test can isolate exactly one failure mode.

MISSING_DATE_CANDIDATES: list[CandidateEvent] = [
    _candidate_from_gold(e.event_id) if e.event_id != "S01-E01" else _candidate_from_gold("S01-E01", event_date=None)
    for e in DATASET.gold_events
]

WRONG_SOURCE_LINK_CANDIDATES: list[CandidateEvent] = [
    # Same real excerpt text as S06-E01's gold passage, but attributed to
    # the covering email (S06-M01) instead of the attachment (S06-ATT01)
    # that passage actually came from — genuinely "a plausible event
    # linked to the wrong message," not a fabricated excerpt: the text is
    # real, just mis-attributed. (It also will not independently verify
    # against S06-M01's own body, so this single fixture exercises both
    # the source-link check and, incidentally, demonstrates why the two
    # checks usually co-fail — see scorer.py's module docstring.)
    _candidate_from_gold("S06-E01", source_message_key="S06-M01"),
]

WRONG_ATTRIBUTION_CANDIDATES: list[CandidateEvent] = [
    _candidate_from_gold(e.event_id) if e.event_id != "S02-E01" else _candidate_from_gold("S02-E01", attributed_party="Priya Nandan (Sagara Contracting)")
    for e in DATASET.gold_events
]

CORRECT_EVENT_WRONG_DATE_CANDIDATES: list[CandidateEvent] = [
    _candidate_from_gold(e.event_id) if e.event_id != "S04-E01" else _candidate_from_gold("S04-E01", event_date="2024-06-04")
    for e in DATASET.gold_events
]

DUPLICATE_PREDICTION_CANDIDATES: list[CandidateEvent] = [
    *GOOD_CANDIDATES,
    # A second, independent candidate for the already-matched S01-E01 —
    # same source and passage, re-worded event_type casing is irrelevant
    # here since the point is the duplicate CLAIM on one gold event, not
    # a field accuracy issue.
    _candidate_from_gold("S01-E01"),
]

UNSUPPORTED_EVENT_CANDIDATES: list[CandidateEvent] = [
    *GOOD_CANDIDATES,
    # A fabricated event: real, valid source message_key, but an excerpt
    # that never actually appears in that message's text at all.
    CandidateEvent(
        source_message_key="S01-M01",
        excerpt="The contractor also confirmed the Pier C7 steelwork had already been fabricated and delivered to site.",
        event_type="DRAWING_REVISED",
        assertion_type="recorded_action",
        event_date="2024-03-01",
        event_date_basis="explicit",
        attributed_party="Priya Nandan (Sagara Contracting)",
    ),
]

ONE_SIDE_OF_CONFLICT_OMITTED_CANDIDATES: list[CandidateEvent] = [
    candidate for candidate in GOOD_CANDIDATES if candidate.source_message_key != "S05-M02"
]

INCORRECT_NO_EVENT_ABSTENTION_CANDIDATES: list[CandidateEvent] = [
    *GOOD_CANDIDATES,
    # Wrongly treats the purely social S12 message as event-bearing.
    CandidateEvent(
        source_message_key="S12-M01",
        excerpt="Thanks for organising the site visit yesterday",
        event_type="NOTICE_SUBMITTED",
        assertion_type="recorded_action",
        event_date="2025-01-06",
        event_date_basis="explicit",
        attributed_party="David Okonkwo (Meridian Consult)",
    ),
]

EMPTY_CANDIDATES: list[CandidateEvent] = []
