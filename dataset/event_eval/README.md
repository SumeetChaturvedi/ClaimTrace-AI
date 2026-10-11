# Phase 8B.1 — Event Evaluation Dataset & Scoring Harness

Evaluation foundation only. **No production `EventExtractor` exists yet**
(that is Phase 8B.2) — nothing in this directory calls Gemini, touches the
database, or integrates with `backend/app/`. It is deliberately
independent of the production application; see `gold_schema.py`'s module
docstring for the rationale.

## What this validates, and what it does not

This proves the **scoring logic** is correct against deterministic,
hand-built candidate fixtures (`candidate_fixtures.py`) covering every
required edge case. It does **not** validate extraction quality — there is
no extractor to evaluate yet. Running `run_event_eval.py` against the
`GOOD_CANDIDATES` fixture demonstrates the harness end-to-end, not a
production result.

## Layout

```
gold_schema.py       Dataclasses: GoldSourceLocator, GoldEvent, CandidateEvent.
                      Also documents the event_type / assertion_type taxonomy decision.
email_builder.py      Shared .eml construction helper (mirrors Phase 8A's test pattern).
scenarios/             12 scenario modules, one file each — real fixture content + gold annotations.
dataset.py             Aggregates all 12 scenarios into one validated registry (DATASET).
scorer.py               Matching algorithm + metrics + configurable Thresholds.
candidate_fixtures.py   Deterministic candidate predictions, including one fixture per required edge case.
run_event_eval.py       CLI: score a named fixture, print + write a JSON report.
test_dataset.py         Gold-dataset integrity tests.
test_scorer.py           Scorer correctness tests (one class per edge case).
```

## The 12 scenarios

All fictional ("Kestrel Causeway" project, fictional firms/people — no
resemblance to the real `dataset/scripts/` investigation-benchmark
dataset, which this task does not touch).

| ID | Scenario | Expected result(s) |
|---|---|---|
| S01 | Clarification request + 21-day-delayed response | 2× `event` |
| S02 | Instruction + revised drawing issued in response | 2× `event` |
| S03 | Contractor notice asserting a contractual entitlement | 1× `attributed_assertion` |
| S04 | Commitment + later follow-up asserting it wasn't honoured | `event` + `attributed_assertion` |
| S05 | Two parties giving contradictory accounts of one incident | 2× `conflict` (same `conflict_group_id`) |
| S06 | Evidence in an attachment, not the covering email | 1× `event`, sourced from the attachment, not the cover message |
| S07 | Email received ~5 weeks after the incident it describes | 1× `attributed_assertion`; event_date ≠ message sent date |
| S08 | "Earlier this month" — no determinable date | 1× `unresolved_ambiguity`; event_date=None |
| S09 | Reply with no In-Reply-To/References headers at all | 1× `event`; the content-thin reply itself produces no event |
| S10 | Two unrelated messages sharing an identical subject line | 1× `event`; the unrelated message produces no event |
| S11 | Uncorroborated claim of a verbal instruction, no date given | 1× `attributed_assertion`; event_date=None |
| S12 | Purely social/administrative correspondence | zero events (`no_event`) |

Every scenario module's own docstring explains its construction-claims
reasoning in full; this table is a navigation aid, not the specification.

## Gold-standard format

```python
GoldEvent(
    event_id="S01-E01", scenario_id="S01",
    expected_result="event",                 # event | attributed_assertion | conflict | unresolved_ambiguity | no_event
    event_type="CLARIFICATION_REQUESTED",     # bottom-up vocabulary, see gold_schema.EVENT_TYPES
    assertion_type="request",                 # recorded_action | request | instruction | commitment | allegation | interpretation_needed
    description="...",                        # human-readable, NOT used for scoring/matching
    event_date="2024-03-01", event_date_basis="explicit",   # explicit | inferred | unknown
    attributed_party="Priya Nandan (Sagara Contracting)",
    sources=(GoldSourceLocator(message_key="S01-M01", passage="<verbatim excerpt>"),),
    conflict_group_id=None,                   # set only for expected_result="conflict"
    must_not_infer=("...",),                  # documented, not scored in this phase
)
```

`event_type` vs. `assertion_type` are **two independent dimensions**, not
one combined enum — see `gold_schema.py`'s module docstring for the full
rationale (short version: "what happened" and "how certain are we this
happened" are genuinely different questions, and the product principle —
*"an extracted event is a proposed interpretation of evidence, not
automatically an established fact"* — depends on keeping them separate).

`expected_result="no_event"` is represented by a scenario (or specific
message within one — see `NOISE_MESSAGE_KEYS` in S09/S10) contributing
**zero** `GoldEvent` rows, not a placeholder row.

Every `GoldSourceLocator.passage` is verified, at `dataset.py` import
time, to be a genuine verbatim substring of its claimed source's actual
fixture text — a gold-authoring mistake fails loudly at load time, not
silently during scoring.

`CandidateEvent` is deliberately a **subset** of `GoldEvent`'s fields — no
`event_id` (candidates are matched to gold by content, never a
pre-assigned identity) and no `conflict_group_id` (not required of a
candidate in this phase; see below).

## Matching algorithm (summary — full detail in `scorer.py`'s module docstring)

Two stages, kept deliberately separate:

1. **Content matching** (recall/precision/duplicates): a candidate matches
   a gold event if its excerpt sufficiently overlaps (normalized
   substring, either direction) at least one of that gold event's source
   passages — **regardless of which message the candidate itself claims
   as its source**. Assignment is 1:1, via a deterministic greedy
   algorithm (longest/most-specific overlap wins, ties broken by input
   order).
2. **Field scoring**, computed only for matched pairs: source-link
   correctness, event-type accuracy, date accuracy, date-basis accuracy,
   and attribution accuracy are each scored independently. **A wrong date
   or type never turns a correct match into a complete miss** — this is
   an explicit, tested requirement (see `MatchingRuleTests` in
   `test_scorer.py`).

Matching on content *before* checking source separately is what makes
"exact source-link accuracy" a real, distinct metric: a candidate with the
right (real, verbatim) excerpt attributed to the wrong message still
counts as a correct *match*, but fails the *source-link* check
specifically — see `WrongSourceLinkTests`.

### Duplicate-event-rate formula

```
duplicate_event_rate = (extra content-compatible candidates on each matched gold event, summed)
                        / max(1, number of gold events that were matched at all)
```

Two candidates matching two *different* gold events (even within the same
scenario or message) are never counted as duplicates — only surplus
candidates competing for the *same* already-satisfied gold event are. See
`DuplicateEventRateTests.test_two_legitimate_events_in_different_messages_of_one_scenario_are_not_duplicates`.

### Unsupported-event rate

Computed independently of gold matching: a candidate is unsupported if its
own excerpt is not a genuine substring of the resolved text of the
message *it itself* claims as its source. This is distinct from, though
often co-occurs with, a wrong source link (a real excerpt mis-attributed
to the wrong message) — both are tested separately.

### Conflict preservation

For each gold `conflict_group_id`, preserved only if **every** member of
that group was independently matched. The scorer never requires a
candidate to output its own `conflict_group_id` — the Phase 8B
architecture audit left automated conflict-grouping as an unresolved
production design question, so this phase checks only that both sides of
a known conflict were *found*, not that they were *correctly grouped* by
the (nonexistent) extractor.

### Abstention

For every fixture-level "noise" message key (a message, or an entire
scenario, with zero gold events), correct abstention means zero
candidates cite it as their source. A false positive here is scored
against both `abstention_rate` and `precision`.

## Metric definitions and initial thresholds

| Metric | Default threshold | Confidence |
|---|---|---|
| Event recall | ≥ 0.70 | **Needs calibration** — no prior data exists for this task |
| Event precision | ≥ 0.80 | Needs calibration |
| Event-type accuracy | ≥ 0.85 | Needs calibration |
| Date accuracy (gold events with a determinable date only) | ≥ 0.90 | Needs calibration |
| Date-basis accuracy | ≥ 0.90 | Reasonably confident — a narrow 3-way classification |
| Attribution accuracy (gold events with determinable attribution only) | ≥ 0.90 | Needs calibration |
| Exact source-link accuracy | = 1.00 | High confidence — mechanical, not a judgment call |
| Unsupported-event rate | ≤ 0.00 | High confidence — zero tolerance by design |
| Conflict preservation | = 1.00 | High confidence |
| Correct abstention | = 1.00 | High confidence |

These are **provisional evaluation gates for this 12-scenario dataset,
not evidence of production readiness** — they are the audit's own
proposed starting points (Phase 8B report §6), carried over unchanged, and
are only meaningful once a real extractor's output is scored against a
materially larger, independently-sourced corpus. `scorer.Thresholds` is a
plain dataclass precisely so these numbers can be revisited without
touching the scoring logic itself — see
`ThresholdConfigurabilityTests.test_thresholds_are_configurable_not_hardcoded`.

The four "high confidence" metrics are zero-tolerance/binary by design:
they catch a fluent-but-wrong extraction (a well-written but fabricated or
mis-sourced event, or a silently-dropped conflicting account) regardless
of how plausible the prose reads — see the Phase 8B audit report §6 for
the full argument.

## Results file (`event_eval_results.json`) — generated, not tracked

Running `run_event_eval.py` writes `event_eval_results.json` into this
directory. **This file is gitignored, deliberately, not committed as a
reference baseline.** Confirmed fully reproducible — two consecutive runs
against the same fixture produce byte-identical output — but
reproducibility is exactly why there is nothing to gain from tracking it:

- It involves no Gemini call and no extractor (none exists yet), so unlike
  `dataset/scripts/benchmark_results_narrowed.json` (real, somewhat
  variable Gemini output, deliberately tracked as a before/after
  comparison baseline), this file can be regenerated identically, in well
  under a second, from the code alone — a git diff of it would only ever
  show noise from unrelated code changes, never a meaningful result
  drift.
- Every value it would contain is already asserted precisely, field by
  field, by `test_scorer.py` — the tracked tests are the actual source of
  truth for "does the harness score correctly," not a snapshot JSON file.
- Once Phase 8B.2 produces a real `EventExtractor`, a genuine extraction
  run's results (non-deterministic, Gemini-backed, worth comparing run to
  run) would be the appropriate thing to track as a baseline — exactly
  mirroring `benchmark_results_narrowed.json`'s own role. This fixture-only
  file is not that, and tracking it now would not establish a meaningful
  precedent for that future file.

## Running it

```bash
cd "ClaimTrace AI"
python3 -m unittest dataset.event_eval.test_dataset dataset.event_eval.test_scorer -v
python3 -m dataset.event_eval.run_event_eval                              # scores GOOD_CANDIDATES
python3 -m dataset.event_eval.run_event_eval --fixture WRONG_SOURCE_LINK_CANDIDATES
```
