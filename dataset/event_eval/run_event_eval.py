"""Standalone CLI entry point for the Phase 8B.1 event-evaluation harness —
mirrors dataset/scripts/run_benchmarks_narrowed.py's own shape (load a
dataset, score it, print a per-scenario/per-metric summary, write a JSON
results file) without touching that script or its results file at all.

No Gemini call, no production EventExtractor — none exists yet (Phase
8B.2). By default this scores the deterministic GOOD_CANDIDATES fixture
(see candidate_fixtures.py) purely to demonstrate the harness end-to-end;
pass --fixture to score any other named fixture in that module (useful for
manually inspecting a specific edge case's full report). This is NOT a
claim that any extraction quality has been validated — see README.md.

Run with (from the repository root):
    python3 -m dataset.event_eval.run_event_eval
    python3 -m dataset.event_eval.run_event_eval --fixture ONE_SIDE_OF_CONFLICT_OMITTED_CANDIDATES
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dataset.event_eval import candidate_fixtures as fx
from dataset.event_eval.dataset import DATASET
from dataset.event_eval.scorer import DEFAULT_THRESHOLDS, passes_thresholds, score

RESULTS_PATH = Path(__file__).resolve().parent / "event_eval_results.json"


def _report_to_dict(report) -> dict:
    data = {
        "scenario_ids": list(report.scenario_ids),
        "total_gold_events": report.total_gold_events,
        "total_candidates": report.total_candidates,
        "matched_count": len(report.matched_pairs),
        "unmatched_gold_ids": [g.event_id for g in report.unmatched_gold],
        "unmatched_candidate_sources": [c.source_message_key for c in report.unmatched_candidates],
        "metrics": {
            "recall": report.recall,
            "precision": report.precision,
            "event_type_accuracy": report.event_type_accuracy,
            "date_accuracy": report.date_accuracy,
            "date_basis_accuracy": report.date_basis_accuracy,
            "attribution_accuracy": report.attribution_accuracy,
            "source_link_accuracy": report.source_link_accuracy,
            "duplicate_event_rate": report.duplicate_event_rate,
            "unsupported_event_rate": report.unsupported_event_rate,
            "conflict_groups_total": report.conflict_groups_total,
            "conflict_groups_preserved": report.conflict_groups_preserved,
            "conflict_preservation_rate": report.conflict_preservation_rate,
            "noise_keys_total": report.noise_keys_total,
            "noise_keys_correctly_abstained": report.noise_keys_correctly_abstained,
            "abstention_rate": report.abstention_rate,
        },
        "threshold_results": passes_thresholds(report, DEFAULT_THRESHOLDS),
    }
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture",
        default="GOOD_CANDIDATES",
        help="Name of a candidate list in candidate_fixtures.py to score (default: GOOD_CANDIDATES).",
    )
    args = parser.parse_args()

    if not hasattr(fx, args.fixture):
        print(f"Unknown fixture {args.fixture!r} — available: "
              f"{[n for n in dir(fx) if n.isupper()]}", file=sys.stderr)
        return 2
    candidates = getattr(fx, args.fixture)

    report = score(DATASET, list(DATASET.gold_events), candidates)
    result = _report_to_dict(report)

    print(f"Scored fixture: {args.fixture}")
    print(f"Scenarios: {', '.join(report.scenario_ids)}")
    print(f"Gold events: {report.total_gold_events}  Candidates: {report.total_candidates}  Matched: {len(report.matched_pairs)}")
    print()
    for metric, value in result["metrics"].items():
        print(f"  {metric}: {value}")
    print()
    print("Threshold results (provisional — see README.md):")
    for metric, passed in result["threshold_results"].items():
        print(f"  {'PASS' if passed else 'FAIL'}  {metric}")

    RESULTS_PATH.write_text(json.dumps(result, indent=2))
    print(f"\nWrote {RESULTS_PATH}")

    return 0 if all(result["threshold_results"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
