"""Shape definitions for the Phase 8B.1 event-evaluation gold dataset and
scorer (ClaimTrace Chronology & Event Extraction — evaluation foundation
only; see the Phase 8B architecture audit for the full design rationale).

This module defines DATA SHAPES ONLY — no extraction logic, no database
access, no Gemini call. It is deliberately independent of
`backend/app/`: the production `EventExtractor` does not exist yet (Phase
8B.2), and this evaluation harness must be runnable, and testable, without
it — see `candidate_fixtures.py` for deterministic stand-ins.

-------------------------------------------------------------------------
Taxonomy decision (required by the Phase 8B.1 brief, §2): two separate,
orthogonal dimensions, not one combined enum.
-------------------------------------------------------------------------

`event_type` answers "what kind of thing happened" (CLARIFICATION_REQUESTED,
INSTRUCTION_ISSUED, DRAWING_REVISED, ...) — a small, concrete vocabulary
derived bottom-up from the actual 12 gold scenarios (see EVENT_TYPES below),
not a speculative construction-claims taxonomy designed in the abstract.

`assertion_type` answers "what is the epistemic status of this content" —
is it something that demonstrably happened (a recorded action), something
one party is asking for (a request), telling another party to do
(an instruction), promising to do (a commitment), or merely claiming,
without this record establishing it as true (an allegation)? A sixth value,
`interpretation_needed`, covers content that is real and attributable but
whose significance a human reviewer must judge (e.g. a notice whose
contractual effect isn't mechanically determinable from the text alone).

These two dimensions are independent on purpose: an INSTRUCTION_ISSUED
event_type is always assertion_type=instruction (the two happen to be
correlated for that one type), but a NOTICE_SUBMITTED event_type can be
assertion_type=allegation (an unsubstantiated claim) in one scenario and
assertion_type=recorded_action (the notice itself, as a document, was
genuinely submitted — that part is not in dispute) in another, depending on
what exactly the gold annotation is asserting is true. Collapsing these
into one enum would force a choice between "what happened" and "how
certain are we this happened," which are genuinely different questions —
exactly the distinction the product principle in the Phase 8B brief turns
on ("an extracted event is a proposed interpretation of evidence, not
automatically an established fact").

`expected_result` is a THIRD, evaluation-routing-only field (not part of
the production event model) that classifies what kind of gold item this
is for scoring purposes:
    - "event": a real event the extractor should find, un-controversially.
    - "attributed_assertion": a real event the extractor should find, but
      whose assertion_type must not be elevated to recorded_action.
    - "conflict": one of two (or more) gold events describing the same
      underlying happening differently; see conflict_group_id below.
    - "unresolved_ambiguity": a real event whose date and/or other details
      are genuinely not determinable from the source — correct extraction
      means correctly representing the ambiguity (event_date_basis =
      "unknown"), not guessing confidently.
    - "no_event": there is no gold event for this correspondence at all.
      Represented by a scenario (or a specific message within one)
      contributing zero GoldEvent rows — see dataset.py's
      NOISE_MESSAGE_KEYS for messages that exist as realistic clutter but
      must not produce any event.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

EventType = str  # see EVENT_TYPES below — intentionally a small closed set, not a Python Enum, so a new scenario can introduce one more concrete value without touching this module.

AssertionType = Literal[
    "recorded_action",
    "request",
    "instruction",
    "commitment",
    "allegation",
    "interpretation_needed",
]

ExpectedResult = Literal[
    "event",
    "attributed_assertion",
    "conflict",
    "unresolved_ambiguity",
    "no_event",
]

DateBasis = Literal["explicit", "inferred", "unknown"]

# The event-type vocabulary, derived bottom-up from the 12 gold scenarios
# actually authored in scenarios/ — not a speculative construction-claims
# taxonomy. Extend only when a real scenario demonstrates a genuine new
# category; do not pre-populate with plausible-sounding types no scenario
# uses.
EVENT_TYPES: tuple[EventType, ...] = (
    "CLARIFICATION_REQUESTED",      # Scenario 1
    "CLARIFICATION_PROVIDED",       # Scenario 1
    "INSTRUCTION_ISSUED",           # Scenario 2, 9
    "DRAWING_REVISED",              # Scenario 2
    "NOTICE_SUBMITTED",             # Scenario 3, 10, 11
    "COMMITMENT_MADE",              # Scenario 4
    "FOLLOW_UP_SENT",               # Scenario 4
    "SITE_CONDITION_REPORTED",      # Scenario 5 (both conflicting sides)
    "INSPECTION_RECORDED",          # Scenario 6 (attachment-derived)
    "INCIDENT_REPORTED",            # Scenario 7, 8
    "CLAIM_ASSERTED",               # Scenario 11
)


@dataclass(frozen=True)
class GoldSourceLocator:
    """A fixture-level analog of the production `(document_id, chunk_id)`
    pair (see the Phase 8B audit, §3/§4) — there is no database in this
    evaluation harness, so a message is identified by its own stable
    fixture key (assigned in scenarios/*.py, never regenerated) and the
    supporting passage is the exact, verbatim substring of that message's
    plain-text body the gold annotation is grounded in, rather than a
    numeric chunk id. `scorer.py` verifies this passage is a genuine
    substring of the fixture's real body at load time (see
    dataset.py's `validate_gold_passages_are_real`), so a gold annotation
    can never itself drift from the fixture text it claims to cite."""

    message_key: str
    passage: str


@dataclass(frozen=True)
class GoldEvent:
    """One hand-authored gold-standard event. Authored independently of
    any model output — see each scenarios/*.py module's own docstring for
    the construction-correspondence reasoning behind each annotation."""

    event_id: str
    scenario_id: str
    expected_result: ExpectedResult
    event_type: EventType | None
    assertion_type: AssertionType | None
    description: str
    event_date: str | None  # ISO 8601 date, or None if not determinable
    event_date_basis: DateBasis
    attributed_party: str | None
    sources: tuple[GoldSourceLocator, ...]
    # Non-None only for expected_result == "conflict": gold events sharing
    # a conflict_group_id describe the same underlying happening from
    # different accounts. Hand-assigned here (gold authoring), never
    # required of a candidate prediction — the Phase 8B audit left
    # automated conflict-grouping as an explicitly unresolved production
    # design question, so the scorer checks conflict PRESERVATION (were
    # both sides independently found) without requiring the candidate to
    # output any conflict_group_id of its own. See scorer.py's
    # `score_conflict_preservation`.
    conflict_group_id: str | None = None
    must_not_infer: tuple[str, ...] = field(default_factory=tuple)
    notes: str = ""

    def __post_init__(self) -> None:
        if self.expected_result != "no_event" and not self.sources:
            raise ValueError(f"{self.event_id}: every gold event except 'no_event' placeholders must cite at least one source")
        if self.expected_result == "conflict" and self.conflict_group_id is None:
            raise ValueError(f"{self.event_id}: expected_result='conflict' requires a conflict_group_id")


@dataclass(frozen=True)
class CandidateEvent:
    """One candidate (extracted or, in this phase, fixture-supplied)
    event prediction. Deliberately a SUBSET of GoldEvent's fields: no
    event_id (candidates are matched to gold by content, never by a
    pre-assigned identity — see scorer.py), no conflict_group_id (not
    required of a candidate in this phase — see GoldEvent's docstring),
    and exactly one source (the production model proposed in the Phase 8B
    audit allows a gold event to have several independent sources, but
    nothing requires a single candidate prediction to cite more than the
    one passage it is actually grounded in)."""

    source_message_key: str
    excerpt: str
    event_type: EventType | None
    assertion_type: AssertionType | None
    event_date: str | None
    event_date_basis: DateBasis | None
    attributed_party: str | None
