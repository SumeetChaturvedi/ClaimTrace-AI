"""Run the 9 approved Dataset V2 benchmark questions end-to-end against the
ingested corpus (project_id=2), through every subsystem, with real Gemini
calls. Uses InvestigationService's own sub-component instances directly
(planner, contract context builder, clause retriever, package builder,
reasoning engine / prompt builder) so each stage's intermediate output can
be inspected -- this is the same pipeline investigate() runs, called
step-by-step instead of as one opaque call, so nothing about the actual
production code path is bypassed or reimplemented.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.agent import tools
from app.agent.investigation_package import InvestigationPackageBuilder
from app.agent.reasoning import ReasoningEngine, ReasoningError
from app.agent.service import InvestigationService
from app.config import get_settings
from app.db.session import get_session_factory, init_engine
from app.investigation import InvestigationPlanner
from app.investigation.timeline import TimelineBuilder, TimelineFormatter

from benchmarks import BENCHMARKS

PROJECT_ID = 2
TOP_K = 10


def run_one(service: InvestigationService, bench: dict) -> dict:
    query = bench["question"]

    plan = service._planner.create_plan(query)

    contract_context = service._contract_context_builder.build(plan)
    retrieved_clauses = service._clause_retriever.retrieve(contract_context)

    citations = tools.search_documents(
        project_id=PROJECT_ID, query=query, top_k=TOP_K, investigation_plan=plan
    )
    evidence = service._build_evidence(citations)
    timeline_context = service._build_timeline_context(citations)

    package = service._package_builder.build(
        query, evidence, timeline_context=timeline_context, retrieved_clauses=retrieved_clauses
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

    retrieved_doc_ids = sorted({c.document_id for c in citations})
    retrieved_filenames = [tools.get_document_filename(did) for did in retrieved_doc_ids]
    retrieved_stems = sorted({Path(f).stem for f in retrieved_filenames})

    expected = set(bench["expected_decisive_docs"])
    retrieved_set = set(retrieved_stems)
    hits = expected & retrieved_set
    misses = expected - retrieved_set
    precision_at_expected = len(hits) / len(retrieved_set) if retrieved_set else 0.0
    recall = len(hits) / len(expected) if expected else 1.0

    clause_numbers = sorted({c.clause_number for c in retrieved_clauses})

    return {
        "scenario": bench["scenario"],
        "id": bench["id"],
        "question": query,
        "expected_outcome": bench["expected_outcome"],
        "planner": {
            "investigation_type": plan.investigation_type,
            "goal": plan.goal,
            "primary_entities": plan.primary_entities,
            "likely_evidence_sources": [str(t) for t in plan.likely_evidence_sources],
        },
        "retrieval": {
            "retrieved_document_ids": retrieved_doc_ids,
            "retrieved_document_stems": retrieved_stems,
            "citation_count": len(citations),
            "expected_decisive_docs": sorted(expected),
            "hits": sorted(hits),
            "misses": sorted(misses),
            "precision_at_expected": round(precision_at_expected, 2),
            "recall": round(recall, 2),
        },
        "timeline": {
            "timeline_context_chars": len(timeline_context),
            "timeline_nonempty": bool(timeline_context.strip()),
            "timeline_preview": timeline_context[:500],
        },
        "contract_clauses": {
            "clause_numbers_retrieved": clause_numbers,
            "clause_count": len(retrieved_clauses),
            "expected_clause_hint": bench["expected_clause_hint"],
        },
        "prompt": {
            "system_prompt_chars": len(prompt.system_prompt),
            "user_prompt_chars": len(prompt.user_prompt),
            "has_evidence_section": "Supporting Evidence" in prompt.user_prompt,
            "has_timeline_section": "TIMELINE" in prompt.user_prompt,
            "has_contract_clause_section": "CONTRACT CLAUSE" in prompt.user_prompt,
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
        print(f"  done in {r['elapsed_seconds']}s")

    out_path = Path(__file__).resolve().parent / "benchmark_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
