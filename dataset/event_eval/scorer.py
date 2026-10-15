"""Standalone scoring harness for candidate event predictions against the
Phase 8B.1 gold-standard dataset (dataset.py).

No Gemini call, no database, no dependency on backend/app/ — see
gold_schema.py's module docstring for why. Candidate predictions are
supplied as a plain list of CandidateEvent (see candidate_fixtures.py for
deterministic examples used by test_scorer.py, and for how a future real
extractor's output would be adapted into this same shape).

-------------------------------------------------------------------------
Matching algorithm (required to be explicit — see the Phase 8B.1 brief)
-------------------------------------------------------------------------

Two-stage, deliberately separating "did we find the right underlying
happening" from "did we cite the right source for it":

Stage 1 — CONTENT matching (determines recall/precision/duplicates).
A candidate matches a gold event if its excerpt sufficiently overlaps
(after whitespace/case normalization, exact-substring in either
direction — see `_passages_overlap`) at least one of that gold event's
source passages, REGARDLESS of which message_key the candidate itself
claims as its source. This is deliberately NOT source+passage-joint
matching: making source identity part of the matching key would make a
"right content, wrong message" mistake invisible to recall/precision
(the gold event would simply look unmatched, exactly like a genuine
miss), which would prevent "exact source-link accuracy" from ever being a
meaningfully distinct metric. Matching on content alone, then checking the
source separately in Stage 2, is what lets a "plausible event linked to
the wrong message" fail the source-link check specifically, as the brief
requires, rather than disappearing into an undifferentiated miss.

This design is safe for THIS curated dataset because every gold passage
is distinctive, real correspondence text, never generic boilerplate that
could coincidentally overlap an unrelated passage — see dataset.py's
load-time check that every gold passage is a genuine substring of its
claimed source, and each scenario's own docstring for why its passages
don't collide with any other scenario's.

Assignment is 1:1 (one candidate claims at most one gold event, one gold
event is satisfied by at most one candidate) via a deterministic greedy
algorithm: all (gold, candidate) content-compatible pairs are sorted by
overlap length descending (longest, most specific overlap wins ties),
then assigned in that order, skipping any pair where either side is
already claimed. This is a documented, deterministic approximation of
optimal bipartite matching, not a general solver — adequate for a dataset
this size where each gold event has at most a small number of plausible
candidates.

Stage 2 — PER-MATCH field scoring, computed only for Stage-1-matched
pairs: source-link correctness, event-type accuracy, date accuracy,
date-basis accuracy, and attribution accuracy are each scored
independently per pair. A wrong date or type never turns an otherwise
correct match into a complete miss (the brief's explicit requirement) —
it only affects that one field's own accuracy metric.

-------------------------------------------------------------------------
Duplicate-event-rate formula
-------------------------------------------------------------------------

For every gold event that was matched (Stage 1) by at least one
candidate, count how many ADDITIONAL candidates were also content-
compatible with it but lost the 1:1 assignment (i.e. were "extra" claims
on an already-satisfied gold event). Sum these across all matched gold
events, divide by the number of matched gold events:

    duplicate_event_rate = sum(extra_compatible_candidates_per_matched_gold)
                            / max(1, count_of_matched_gold_events)

This is 0 whenever every matched gold event had exactly one compatible
candidate. It is NOT affected by two candidates matching two DIFFERENT
gold events in the same source document (e.g. Scenario 1's two separate
events in two different messages, or — more pointedly — any future
scenario with two real, distinct events in the SAME message) — that case
is two separate 1:1 matches, not a duplicate, because each gold event's
own distinct passage only overlaps its own candidate.

-------------------------------------------------------------------------
Unsupported-event rate
-------------------------------------------------------------------------

Computed independently of gold matching, over EVERY candidate: a
candidate is "unsupported" if its own excerpt is not a genuine substring
of the resolved text of the message it itself claims as its source
(`dataset.resolved_text[candidate.source_message_key]`). This catches a
fabricated/hallucinated excerpt — distinct from "wrong source link"
(§Stage 2), where the excerpt is real but mis-attributed; the two often
co-occur (a mis-attributed excerpt frequently also fails to verify
against the wrong source it was pinned to) but are checked independently,
as the brief requires.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from dataset.event_eval.dataset import EventEvalDataset
from dataset.event_eval.gold_schema import CandidateEvent, GoldEvent


def _normalize(text: str) -> str:
    return " ".join(text.split()).lower()


def _passages_overlap(candidate_excerpt: str, gold_passage: str) -> bool:
    """True if one normalized string contains the other. Deterministic,
    dependency-free (no fuzzy-matching library) — adequate because a
    correct candidate is expected to retain the supporting passage close
    to verbatim (see the Phase 8B audit's extraction rules: "exact source
    passage retention"), not paraphrase it."""
    a, b = _normalize(candidate_excerpt), _normalize(gold_passage)
    if not a or not b:
        return False
    return a in b or b in a


@dataclass(frozen=True)
class MatchedPair:
    gold: GoldEvent
    candidate: CandidateEvent
    matched_source_message_key: str  # which of gold.sources actually overlapped


@dataclass
class EvaluationReport:
    scenario_ids: tuple[str, ...]
    total_gold_events: int
    total_candidates: int

    matched_pairs: list[MatchedPair] = field(default_factory=list)
    unmatched_gold: list[GoldEvent] = field(default_factory=list)
    unmatched_candidates: list[CandidateEvent] = field(default_factory=list)

    precision: float = 0.0
    recall: float = 0.0
    event_type_accuracy: float | None = None
    date_accuracy: float | None = None
    date_basis_accuracy: float = 0.0
    attribution_accuracy: float | None = None
    source_link_accuracy: float = 0.0
    duplicate_event_rate: float = 0.0
    unsupported_event_rate: float = 0.0
    conflict_groups_total: int = 0
    conflict_groups_preserved: int = 0
    conflict_preservation_rate: float | None = None
    noise_keys_total: int = 0
    noise_keys_correctly_abstained: int = 0
    abstention_rate: float | None = None

    # Per-candidate unsupported flags, keyed by the candidate's position
    # in the input list — exposed for test assertions and reporting, not
    # part of any aggregate metric's own computation above this point.
    unsupported_candidate_indices: list[int] = field(default_factory=list)
    wrong_source_link_pairs: list[MatchedPair] = field(default_factory=list)


def _match(gold_events: list[GoldEvent], candidates: list[CandidateEvent]) -> tuple[list[MatchedPair], list[GoldEvent], list[CandidateEvent]]:
    """Stage 1: deterministic greedy 1:1 content matching. See module
    docstring for the full algorithm definition and rationale.

    Pre-commit review fix: candidate identity during assignment is tracked
    by each candidate's actual POSITION in `candidates` (via `enumerate`,
    carried through every tuple from the moment pairs are built), never by
    `candidates.index(candidate)`. CandidateEvent is a frozen dataclass
    with field-value equality, so two independently-submitted candidates
    that happen to carry identical field values (e.g. two real predictions
    that both quote the same short, generic phrase) are `==` to each
    other; `list.index()` cannot tell them apart and always resolves to
    the FIRST such value, silently reassigning every reference to the
    second, genuinely distinct candidate onto the first one's position.
    Reproduced concretely during review: two distinct, value-equal
    candidates that should legitimately satisfy two DIFFERENT gold events
    each (one per candidate) caused one gold event to be wrongly reported
    as unmatched, because the second candidate's bookkeeping collapsed
    onto the first candidate's already-claimed index. Carrying the real
    index from `enumerate()` throughout removes any dependency on
    CandidateEvent's `__eq__` for identity tracking."""
    candidate_pairs: list[tuple[int, GoldEvent, int, CandidateEvent, str]] = []
    for gold in gold_events:
        for candidate_index, candidate in enumerate(candidates):
            for source in gold.sources:
                if _passages_overlap(candidate.excerpt, source.passage):
                    overlap_len = min(len(_normalize(candidate.excerpt)), len(_normalize(source.passage)))
                    candidate_pairs.append((overlap_len, gold, candidate_index, candidate, source.message_key))
                    break  # one source is enough to establish a candidate pair for this (gold, candidate)

    # Longest/most-specific overlap first; stable sort preserves input
    # order (gold-list order, then candidate-index order) as the tie-break,
    # keeping assignment fully deterministic.
    candidate_pairs.sort(key=lambda item: item[0], reverse=True)

    claimed_gold: set[str] = set()
    claimed_candidates: set[int] = set()
    matched: list[MatchedPair] = []
    for _, gold, candidate_index, candidate, source_key in candidate_pairs:
        if gold.event_id in claimed_gold or candidate_index in claimed_candidates:
            continue
        claimed_gold.add(gold.event_id)
        claimed_candidates.add(candidate_index)
        matched.append(MatchedPair(gold=gold, candidate=candidate, matched_source_message_key=source_key))

    unmatched_gold = [g for g in gold_events if g.event_id not in claimed_gold]
    unmatched_candidates = [c for i, c in enumerate(candidates) if i not in claimed_candidates]
    return matched, unmatched_gold, unmatched_candidates


def _duplicate_event_rate(gold_events: list[GoldEvent], candidates: list[CandidateEvent], matched: list[MatchedPair]) -> float:
    matched_gold_ids = {pair.gold.event_id for pair in matched}
    if not matched_gold_ids:
        return 0.0
    extras = 0
    for gold in gold_events:
        if gold.event_id not in matched_gold_ids:
            continue
        compatible = sum(
            1
            for candidate in candidates
            if any(_passages_overlap(candidate.excerpt, source.passage) for source in gold.sources)
        )
        extras += max(0, compatible - 1)
    return extras / len(matched_gold_ids)


def _unsupported_candidates(dataset: EventEvalDataset, candidates: list[CandidateEvent]) -> list[int]:
    indices = []
    for i, candidate in enumerate(candidates):
        source_text = dataset.resolved_text.get(candidate.source_message_key)
        if source_text is None or not _normalize(candidate.excerpt) or _normalize(candidate.excerpt) not in _normalize(source_text):
            indices.append(i)
    return indices


def score(dataset: EventEvalDataset, gold_events: list[GoldEvent], candidates: list[CandidateEvent]) -> EvaluationReport:
    matched, unmatched_gold, unmatched_candidates = _match(gold_events, candidates)

    report = EvaluationReport(
        scenario_ids=dataset.scenario_ids,
        total_gold_events=len(gold_events),
        total_candidates=len(candidates),
        matched_pairs=matched,
        unmatched_gold=unmatched_gold,
        unmatched_candidates=unmatched_candidates,
    )

    report.recall = len(matched) / len(gold_events) if gold_events else 1.0
    report.precision = len(matched) / len(candidates) if candidates else 1.0

    # Stage 2: per-matched-pair field scoring.
    type_total = type_correct = 0
    date_total = date_correct = 0
    basis_total = basis_correct = 0
    attribution_total = attribution_correct = 0
    source_link_correct = 0

    for pair in matched:
        gold, candidate = pair.gold, pair.candidate

        if gold.event_type is not None:
            type_total += 1
            if candidate.event_type == gold.event_type:
                type_correct += 1

        if gold.event_date is not None:
            date_total += 1
            if candidate.event_date == gold.event_date:
                date_correct += 1

        basis_total += 1
        if candidate.event_date_basis == gold.event_date_basis:
            basis_correct += 1

        if gold.attributed_party is not None:
            attribution_total += 1
            if candidate.attributed_party == gold.attributed_party:
                attribution_correct += 1

        if candidate.source_message_key == pair.matched_source_message_key:
            source_link_correct += 1
        else:
            report.wrong_source_link_pairs.append(pair)

    report.event_type_accuracy = (type_correct / type_total) if type_total else None
    report.date_accuracy = (date_correct / date_total) if date_total else None
    report.date_basis_accuracy = (basis_correct / basis_total) if basis_total else 1.0
    report.attribution_accuracy = (attribution_correct / attribution_total) if attribution_total else None
    report.source_link_accuracy = (source_link_correct / len(matched)) if matched else 1.0

    report.duplicate_event_rate = _duplicate_event_rate(gold_events, candidates, matched)

    report.unsupported_candidate_indices = _unsupported_candidates(dataset, candidates)
    report.unsupported_event_rate = (len(report.unsupported_candidate_indices) / len(candidates)) if candidates else 0.0

    conflict_groups: dict[str, list[GoldEvent]] = {}
    for gold in gold_events:
        if gold.conflict_group_id is not None:
            conflict_groups.setdefault(gold.conflict_group_id, []).append(gold)
    matched_gold_ids = {pair.gold.event_id for pair in matched}
    report.conflict_groups_total = len(conflict_groups)
    report.conflict_groups_preserved = sum(
        1 for members in conflict_groups.values() if all(m.event_id in matched_gold_ids for m in members)
    )
    report.conflict_preservation_rate = (
        report.conflict_groups_preserved / report.conflict_groups_total if conflict_groups else None
    )

    noise_keys = dataset.noise_message_keys
    report.noise_keys_total = len(noise_keys)
    false_positive_noise_keys = {c.source_message_key for c in candidates if c.source_message_key in noise_keys}
    report.noise_keys_correctly_abstained = len(noise_keys) - len(false_positive_noise_keys)
    report.abstention_rate = (report.noise_keys_correctly_abstained / len(noise_keys)) if noise_keys else None

    return report


_ORG_SUFFIX_PATTERN = re.compile(r"\s*\([^()]*\)\s*$")


def _strip_org_suffix(value: str) -> str:
    """Strip one trailing parenthetical, e.g. "Priya Nandan (Sagara "
    "Contracting)" -> "Priya Nandan". Used only by
    attribution_accuracy_normalized below — score()'s own
    attribution_accuracy is untouched and keeps doing exact-string
    comparison (see that function and Thresholds.min_attribution_accuracy's
    own "needs calibration" flag in README.md)."""
    return _ORG_SUFFIX_PATTERN.sub("", value).strip()


def attribution_accuracy_normalized(report: EvaluationReport) -> float | None:
    """Phase 8B.2 Quality Remediation: an alternate attribution_accuracy
    computed over the SAME matched pairs score() already found, comparing
    each pair's attributed_party after stripping gold's own trailing
    "(Organization)" parenthetical from BOTH sides before comparing.

    This exists because the gold dataset's own convention always appends a
    firm name in parentheses (e.g. "Priya Nandan (Sagara Contracting)") for
    human readability, but that affiliation is frequently NOT itself
    explicit anywhere in a scenario's message bodies or sender display
    names (verified directly against the fixtures before adding this: the
    firm name is only recoverable from the sender's EMAIL DOMAIN, e.g.
    priya.nandan@sagara-contracting.example) — synthesizing a human-
    readable company name out of a domain string is itself a form of
    inference the Phase 8B.2 brief explicitly warns against ("never invent
    a party's organization or identity"), so EventExtractor is not asked
    to do it. A candidate that correctly names "Priya Nandan" and nothing
    more is not treating a different party as having made the statement
    — it has simply omitted optional context the gold happens to include.

    This does NOT conflate different parties: stripping only removes a
    trailing parenthetical, so "Priya Nandan" vs "David Okonkwo (Meridian "
    "Consult)" still correctly fails to match (different name), and a
    candidate that attributes to the wrong person, or omits attribution
    entirely (null), still correctly fails regardless of normalization.
    Only the OPTIONAL organizational suffix is treated as not required for
    a match — the person/entity name itself must still match exactly.

    score()'s own `report.attribution_accuracy` is left completely
    unchanged by this function; callers that want the normalized view call
    this separately and should report BOTH, never substitute one for the
    other silently."""
    total = correct = 0
    for pair in report.matched_pairs:
        gold, candidate = pair.gold, pair.candidate
        if gold.attributed_party is None:
            continue
        total += 1
        if candidate.attributed_party is None:
            continue
        if _strip_org_suffix(candidate.attributed_party) == _strip_org_suffix(gold.attributed_party):
            correct += 1
    return (correct / total) if total else None


@dataclass(frozen=True)
class Thresholds:
    """Provisional acceptance gates (Phase 8B.1 brief §6) — configurable,
    not hardcoded assumptions of production readiness. Every value here is
    explicitly flagged in README.md as either "reasonably confident" or
    "needs calibration against a larger corpus" — this dataclass only
    carries the numbers, not the justification; see README.md."""

    min_recall: float = 0.70
    min_precision: float = 0.80
    min_event_type_accuracy: float = 0.85
    min_date_accuracy: float = 0.90
    min_date_basis_accuracy: float = 0.90
    min_attribution_accuracy: float = 0.90
    min_source_link_accuracy: float = 1.00
    max_unsupported_event_rate: float = 0.0
    min_conflict_preservation_rate: float = 1.00
    min_abstention_rate: float = 1.00


DEFAULT_THRESHOLDS = Thresholds()


def passes_thresholds(report: EvaluationReport, thresholds: Thresholds = DEFAULT_THRESHOLDS) -> dict[str, bool]:
    """Per-metric pass/fail against `thresholds`. A None metric (nothing
    in the gold set exercised it — e.g. no gold event had a determinable
    date) is reported as passing vacuously (`True`) rather than failing,
    since there was nothing to get wrong."""
    return {
        "recall": report.recall >= thresholds.min_recall,
        "precision": report.precision >= thresholds.min_precision,
        "event_type_accuracy": report.event_type_accuracy is None or report.event_type_accuracy >= thresholds.min_event_type_accuracy,
        "date_accuracy": report.date_accuracy is None or report.date_accuracy >= thresholds.min_date_accuracy,
        "date_basis_accuracy": report.date_basis_accuracy >= thresholds.min_date_basis_accuracy,
        "attribution_accuracy": report.attribution_accuracy is None or report.attribution_accuracy >= thresholds.min_attribution_accuracy,
        "source_link_accuracy": report.source_link_accuracy >= thresholds.min_source_link_accuracy,
        "unsupported_event_rate": report.unsupported_event_rate <= thresholds.max_unsupported_event_rate,
        "conflict_preservation_rate": report.conflict_preservation_rate is None or report.conflict_preservation_rate >= thresholds.min_conflict_preservation_rate,
        "abstention_rate": report.abstention_rate is None or report.abstention_rate >= thresholds.min_abstention_rate,
    }
