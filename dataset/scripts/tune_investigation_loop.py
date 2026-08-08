"""Sprint 8 Task 02 — Investigation Loop Configuration Tuning. A pure
measurement harness: runs the complete, real 10-question benchmark corpus
(project_id=2) at each of 6 InvestigationLoopConfig.max_iterations values,
through the real, unmodified Investigation Loop and Evidence Narrowing.

No backend code is touched or reconfigured globally -- each run swaps the
`_config` attribute on one InvestigationService's own InvestigationLoop
instance (the same instance the service already wires to itself, agent, and
FocusedRetrievalExecutor), a test-harness-level attribute assignment, not a
change to any component's default or logic.

Gemini is deliberately NOT called during this sweep: the metrics this task
asks for (recall, iterations, evidence/document/citation counts, prompt
size, stopping reasons) are all determined before reasoning ever runs --
Gemini's own answer content doesn't depend on max_iterations except through
the prompt it's given, and prompt size is measured directly via
PromptBuilder without an actual LLMProvider.generate() call. This keeps a
60-run sweep (6 configs x 10 questions) fast and avoids 60 needless real API
calls; the chosen production configuration is separately re-validated with
real Gemini calls after this sweep picks it.

Two recall metrics, deliberately kept separate: `recall_raw` (did the loop
even visit the expected document, out of everything InvestigationState
accumulated) and `recall_narrowed` (did the expected document's evidence
survive Evidence Narrowing's fixed 15-citation cap to actually reach the
final answer -- the same definition dataset/scripts/run_benchmarks_narrowed.py
already uses, i.e. what a real user actually sees). These can diverge: a
larger max_iterations means more raw evidence for the SAME fixed cap to
choose among, so `recall_raw` improving does not guarantee `recall_narrowed`
improves too. `recall_narrowed` is the metric that determines the
production recommendation, since it reflects what actually reaches Gemini
and the end user; `recall_raw` is kept as a diagnostic to distinguish "the
loop never found it" from "the loop found it but narrowing dropped it."
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.agent import tools
from app.agent.investigation_loop_config import InvestigationLoopConfig
from app.agent.models import InvestigationRequest
from app.agent.prompt_builder import PromptBuilder
from app.agent.service import InvestigationService
from app.config import get_settings
from app.db.session import init_engine

from benchmarks import BENCHMARKS

TEST_VALUES = [5, 7, 10, 12, 15, 20]
PROJECT_ID = 2
TOP_K = 10


def run_one(service: InvestigationService, bench: dict, prompt_builder: PromptBuilder) -> dict:
    request = InvestigationRequest(project_id=PROJECT_ID, query=bench["question"], top_k=TOP_K)

    t0 = time.time()
    loop_result = service._investigation_loop.run(request)
    state = loop_result.state

    narrowing_result = service._evidence_narrower.narrow(state.evidence)

    timeline_context = service._build_timeline_context([item.citation for item in state.evidence])
    package = service._package_builder.build(
        bench["question"],
        narrowing_result.retained_evidence,
        timeline_context=timeline_context,
        retrieved_clauses=list(state.retrieved_clauses),
    )
    prompt = prompt_builder.build_reasoning_prompt(package)
    elapsed = time.time() - t0

    # Two distinct recall measures -- see the module docstring's "two
    # recall metrics" note. visited_stems is what the loop found at all;
    # narrowed_stems is what actually survived Evidence Narrowing's fixed
    # 15-citation cap to reach the final answer. These can diverge: more
    # raw evidence competing for the same fixed cap can mean a document
    # the loop DID find still doesn't end up cited.
    expected = set(bench["expected_decisive_docs"])
    visited_stems = {Path(tools.get_document_filename(d)).stem for d in state.visited_document_ids}
    narrowed_stems = {Path(tools.get_document_filename(item.document_id)).stem for item in narrowing_result.retained_evidence}
    recall_raw = len(expected & visited_stems) / len(expected) if expected else 1.0
    recall_narrowed = len(expected & narrowed_stems) / len(expected) if expected else 1.0

    return {
        "id": bench["id"],
        "recall_raw": round(recall_raw, 3),
        "recall_narrowed": round(recall_narrowed, 3),
        "elapsed_seconds": round(elapsed, 2),
        "iterations_executed": loop_result.iterations_executed,
        "stopping_reason": loop_result.stopping_reason,
        "evidence_count": len(state.evidence),
        "documents_visited": len(state.visited_document_ids),
        "citations_after_narrowing": len(narrowing_result.retained_evidence),
        "prompt_chars": len(prompt.user_prompt),
    }


def main() -> None:
    init_engine(get_settings())
    prompt_builder = PromptBuilder()

    all_results: dict[int, list[dict]] = {}

    for max_iter in TEST_VALUES:
        print(f"\n=== max_iterations = {max_iter} ===")
        service = InvestigationService()
        service._investigation_loop._config = InvestigationLoopConfig(max_iterations=max_iter)

        results = []
        for bench in BENCHMARKS:
            r = run_one(service, bench, prompt_builder)
            results.append(r)
            print(
                f"  {r['id']:24s} recall_raw={r['recall_raw']:.2f} recall_narrowed={r['recall_narrowed']:.2f} "
                f"iters={r['iterations_executed']:2d} stop={r['stopping_reason']:28s} "
                f"evidence={r['evidence_count']:3d} docs={r['documents_visited']:3d} "
                f"citations={r['citations_after_narrowing']:2d} prompt={r['prompt_chars']:5d} t={r['elapsed_seconds']:.2f}s"
            )
        all_results[max_iter] = results

    out_path = Path(__file__).resolve().parent / "loop_tuning_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\nWrote {out_path}")

    print("\n" + "=" * 100)
    print("AGGREGATE SUMMARY")
    print("=" * 100)
    header = (
        f"{'max_iter':>8s} {'pass_raw':>9s} {'pass_narr':>10s} {'recall_raw':>11s} {'recall_narr':>12s} "
        f"{'avg_lat_s':>9s} {'avg_iters':>9s} {'avg_evid':>8s} {'avg_docs':>8s} {'avg_cite':>8s} {'avg_prompt':>10s}"
    )
    print(header)
    for max_iter in TEST_VALUES:
        rows = all_results[max_iter]
        n = len(rows)
        passed_raw = sum(1 for r in rows if r["recall_raw"] >= 0.5)
        passed_narrowed = sum(1 for r in rows if r["recall_narrowed"] >= 0.5)
        avg_recall_raw = sum(r["recall_raw"] for r in rows) / n
        avg_recall_narrowed = sum(r["recall_narrowed"] for r in rows) / n
        avg_lat = sum(r["elapsed_seconds"] for r in rows) / n
        avg_iters = sum(r["iterations_executed"] for r in rows) / n
        avg_evid = sum(r["evidence_count"] for r in rows) / n
        avg_docs = sum(r["documents_visited"] for r in rows) / n
        avg_cite = sum(r["citations_after_narrowing"] for r in rows) / n
        avg_prompt = sum(r["prompt_chars"] for r in rows) / n
        stop_dist = Counter(r["stopping_reason"] for r in rows)
        print(
            f"{max_iter:>8d} {passed_raw}/{n:<7d} {passed_narrowed}/{n:<8d} {avg_recall_raw:>11.3f} "
            f"{avg_recall_narrowed:>12.3f} {avg_lat:>9.2f} {avg_iters:>9.1f} {avg_evid:>8.1f} "
            f"{avg_docs:>8.1f} {avg_cite:>8.1f} {avg_prompt:>10.0f}   {dict(stop_dist)}"
        )


if __name__ == "__main__":
    main()
