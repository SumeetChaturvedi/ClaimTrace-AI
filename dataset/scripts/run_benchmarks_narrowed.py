"""Run the same 9 approved Dataset V2 benchmark questions (benchmarks.py,
unchanged since Sprint 7) end-to-end against the ingested corpus
(project_id=2), through the NEW, Evidence-Narrowing-integrated production
pipeline (Sprint 8 Task 01), with real Gemini calls.

Calls InvestigationService's own internals directly (self._investigation_loop,
self._build_timeline_context, self._evidence_narrower, self._package_builder,
self._reasoning_engine) in the exact sequence investigate() itself now runs --
the same pipeline a real POST /investigate request executes, called
step-by-step instead of as one opaque async call, purely so each stage's
intermediate output (narrowing statistics, evidence/document/clause counts)
can be captured for the report. Nothing about the production code path is
bypassed, reimplemented, or duplicated.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.agent import tools
from app.agent.reasoning import ReasoningError
from app.agent.service import InvestigationService
from app.agent.models import InvestigationRequest
from app.config import get_settings
from app.db.session import init_engine

from benchmarks import BENCHMARKS

PROJECT_ID = 2  # default for every benchmark question that doesn't state its own project_id
TOP_K = 10


def run_one(service: InvestigationService, bench: dict) -> dict:
    query = bench["question"]
    project_id = bench.get("project_id", PROJECT_ID)
    request = InvestigationRequest(project_id=project_id, query=query, top_k=TOP_K)

    # Exactly what investigate() now does internally (Sprint 8 Task 01),
    # called directly so the loop's and narrower's own metadata is
    # inspectable here.
    loop_result = service._investigation_loop.run(request)
    state = loop_result.state

    final_timeline_context = service._build_timeline_context([item.citation for item in state.evidence])
    narrowing_result = service._evidence_narrower.narrow(state.evidence)

    package = service._package_builder.build(
        query,
        narrowing_result.retained_evidence,
        timeline_context=final_timeline_context,
        retrieved_clauses=list(state.retrieved_clauses),
    )

    ranked_evidence = sorted(package.evidence, key=lambda item: item.confidence, reverse=True)
    ranked_package = package.model_copy(update={"evidence": ranked_evidence})
    prompt = service._reasoning_engine._prompt_builder.build_reasoning_prompt(ranked_package)

    error = None
    try:
        result = service._reasoning_engine.reason(package)
    except ReasoningError as exc:
        error = str(exc)
        result = None

    retrieved_doc_ids = sorted({item.document_id for item in narrowing_result.retained_evidence})
    retrieved_filenames = [tools.get_document_filename(did) for did in retrieved_doc_ids]
    retrieved_stems = sorted({Path(f).stem for f in retrieved_filenames})

    expected = set(bench["expected_decisive_docs"])
    retrieved_set = set(retrieved_stems)
    hits = expected & retrieved_set
    misses = expected - retrieved_set
    precision_at_expected = len(hits) / len(retrieved_set) if retrieved_set else 0.0
    recall = len(hits) / len(expected) if expected else 1.0

    clause_numbers = sorted({c.clause_number for c in state.retrieved_clauses})

    return {
        "scenario": bench["scenario"],
        "project_id": project_id,
        "id": bench["id"],
        "question": query,
        "expected_outcome": bench["expected_outcome"],
        "loop": {
            "iterations_executed": loop_result.iterations_executed,
            "stopping_reason": loop_result.stopping_reason,
        },
        "narrowing": {
            "evidence_before": narrowing_result.statistics.evidence_before,
            "evidence_after": narrowing_result.statistics.evidence_after,
            "duplicates_removed": narrowing_result.statistics.duplicates_removed,
            "merged_groups": narrowing_result.statistics.merged_groups,
            "items_absorbed_by_merge": narrowing_result.statistics.items_absorbed_by_merge,
            "below_confidence_removed": narrowing_result.statistics.below_confidence_removed,
            "per_document_cap_removed": narrowing_result.statistics.per_document_cap_removed,
            "over_max_removed": narrowing_result.statistics.over_max_removed,
            "documents_before": narrowing_result.statistics.documents_before,
            "documents_after": narrowing_result.statistics.documents_after,
        },
        "retrieval": {
            "retrieved_document_ids": retrieved_doc_ids,
            "retrieved_document_stems": retrieved_stems,
            "evidence_count": len(narrowing_result.retained_evidence),
            "documents_visited": len(state.visited_document_ids),
            "expected_decisive_docs": sorted(expected),
            "hits": sorted(hits),
            "misses": sorted(misses),
            "precision_at_expected": round(precision_at_expected, 2),
            "recall": round(recall, 2),
        },
        "timeline": {
            "timeline_context_chars": len(final_timeline_context),
            "timeline_nonempty": bool(final_timeline_context.strip()),
        },
        "contract_clauses": {
            "clause_numbers_retrieved": clause_numbers,
            "clause_count": len(state.retrieved_clauses),
            "expected_clause_hint": bench["expected_clause_hint"],
        },
        "prompt": {
            "system_prompt_chars": len(prompt.system_prompt),
            "user_prompt_chars": len(prompt.user_prompt),
        },
        "gemini": {
            "error": error,
            "answer": result.answer if result else None,
            "citation_count_returned": len(result.supporting_evidence) if result else 0,
            "reasoning_steps": result.reasoning_steps if result else [],
        },
    }


def main() -> None:
    settings = get_settings()
    init_engine(settings)

    service = InvestigationService()

    results = []
    for bench in BENCHMARKS:
        print(f"Running scenario {bench['scenario']} — {bench['id']} ...")
        t0 = time.time()
        try:
            r = run_one(service, bench)
        except Exception as exc:  # noqa: BLE001 — capture and continue
            print(f"  EXCEPTION: {exc}")
            r = {
                "scenario": bench["scenario"],
                "id": bench["id"],
                "question": bench["question"],
                "exception": str(exc),
            }
        r["elapsed_seconds"] = round(time.time() - t0, 1)
        results.append(r)
        print(
            f"  done in {r['elapsed_seconds']}s"
            + (f" | citations {r['narrowing']['evidence_before']} -> {r['narrowing']['evidence_after']}" if "narrowing" in r else "")
        )

    out_path = Path(__file__).resolve().parent / "benchmark_results_narrowed.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
