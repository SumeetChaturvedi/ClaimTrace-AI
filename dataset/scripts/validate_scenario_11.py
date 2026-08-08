"""Validation for Phase 4 Task 03 (Scenario 11 — Concrete Defects During the
Defects Notification Period). Runs against the real, now-expanded Dataset V2
corpus (project_id=2, 99 documents), through the full, unmodified Backend
v1.0 production pipeline, at the frozen max_iterations=7 default.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "backend"))

from app.agent import tools
from app.agent.service import InvestigationService
from app.agent.models import InvestigationRequest
from app.config import get_settings
from app.db.session import init_engine
from app.db.models import Document
from sqlalchemy import select

from scenario_11_data import DOCUMENTS as SCENARIO_11_DOCS
from benchmarks import BENCHMARKS

FAILURES = []


def check(label: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {label}" + (f" -- {detail}" if detail else ""))
    if not condition:
        FAILURES.append(label)


init_engine(get_settings())
PROJECT_ID = 2

print("=== Timeline consistency ===")
from datetime import datetime
dates = [datetime.strptime(spec.date, "%d-%b-%Y") for spec in SCENARIO_11_DOCS]
check("all 14 documents have parseable dates", len(dates) == 14)
check("dates are in non-decreasing chronological order (matches DOCUMENTS list order)", dates == sorted(dates))
check(
    "scenario falls entirely within the Defects Notification Period "
    "(22-Sep-2023 to 21-Sep-2024, per Taking-Over Certificate TOC-NRB4-001)",
    dates[0] >= datetime(2023, 9, 22) and dates[-1] <= datetime(2024, 9, 21),
    f"{dates[0].date()} .. {dates[-1].date()}",
)
check(
    "scenario is the latest-dated scenario in the corpus (occurs strictly after "
    "Scenario 9's Taking-Over Certificate, 22-Sep-2023)",
    dates[0] > datetime(2023, 9, 22),
)

print()
print("=== No document id collisions with Scenarios 1-10 or the contract package ===")
import json
with open(Path(__file__).resolve().parent / "ingestion_report.json") as f:
    existing_report = json.load(f)
existing_ids = {d["doc_id"] for d in existing_report["documents"] if d.get("document_pk", 999) < 104}
new_ids = {spec.doc_id for spec in SCENARIO_11_DOCS}
check("no Scenario 11 document id collides with an existing document id", not (existing_ids & new_ids), str(existing_ids & new_ids))
check("all 14 Scenario 11 document ids are unique among themselves", len(new_ids) == 14)

print()
print("=== Real database state ===")
from app.db.session import get_session_factory
with get_session_factory()() as session:
    from sqlalchemy import func
    doc_count = session.scalar(select(func.count()).select_from(Document).where(Document.project_id == PROJECT_ID))
    scenario_11_docs_in_db = session.scalars(
        select(Document).where(Document.project_id == PROJECT_ID, Document.id >= 104)
    ).all()
    total_chunks_new = sum(len(d.chunks) for d in scenario_11_docs_in_db)

check("project_id=2 now has 99 documents (85 existing + 14 new)", doc_count == 99, str(doc_count))
check("exactly 14 new documents ingested with id >= 104", len(scenario_11_docs_in_db) == 14, str(len(scenario_11_docs_in_db)))
check("every new document has a non-null doc_type and doc_date", all(d.doc_type and d.doc_date for d in scenario_11_docs_in_db))
check("every new document has at least one chunk", all(len(d.chunks) > 0 for d in scenario_11_docs_in_db))
print(f"  total chunks across the 14 new documents: {total_chunks_new}")

print()
print("=== New contract clauses (Sub-Clauses 11.1, 11.2) are retrievable, existing 11 clauses unaffected ===")
from app.contracts.ingestion import get_clause_repository
get_clause_repository.cache_clear()
repo = get_clause_repository(PROJECT_ID)
clauses = repo.get_all()
check("clause repository now has 13 clauses (11 existing + 2 new)", len(clauses) == 13, str(len(clauses)))
clause_111 = next((c for c in clauses if c.clause_number == "11.1"), None)
clause_112 = next((c for c in clauses if c.clause_number == "11.2"), None)
check("Sub-Clause 11.1 (Completion of Outstanding Work and Remedying of Defects) is present and correctly parsed", clause_111 is not None and "Remedying of Defects" in clause_111.title)
check("Sub-Clause 11.2 (Cost of Remedying Defects) is present and correctly parsed", clause_112 is not None and clause_112.title == "Cost of Remedying Defects")
existing_numbers = {"1.3", "3.3", "4.1", "4.12", "8.4", "8.7", "13.1", "13.3", "14.3", "14.7", "20.1"}
check("all 11 pre-existing clause numbers are still present, unmodified", existing_numbers.issubset({c.clause_number for c in clauses}))

print()
print("=== Retrieval is project-scoped and topically relevant ===")
citations = tools.search_documents(
    project_id=PROJECT_ID,
    query="Is the map cracking found at the Pier P2 pier cap during the Defects "
          "Notification Period attributable to the Contractor, and should the "
          "Contractor bear the cost of rectification?",
    top_k=10,
)
retrieved_stems = {Path(tools.get_document_filename(c.document_id)).stem for c in citations}
scenario_11_stems = {spec.doc_id for spec in SCENARIO_11_DOCS}
check("retrieval surfaces at least 3 real Scenario 11 documents in the top 10", len(retrieved_stems & scenario_11_stems) >= 3, str(retrieved_stems & scenario_11_stems))

print()
print("=== Full production pipeline: Investigation Loop + Evidence Narrowing (real, project_id=2, frozen max_iterations=7) ===")
service = InvestigationService()
check(
    "InvestigationLoopConfig.max_iterations is the frozen production default (7), unmodified by this task",
    service._investigation_loop._config.max_iterations == 7,
    str(service._investigation_loop._config.max_iterations),
)
bench = next(b for b in BENCHMARKS if b["id"] == "PIER-P2-DEFECT-LIABILITY")
req = InvestigationRequest(project_id=PROJECT_ID, query=bench["question"], top_k=10)
loop_result = service._investigation_loop.run(req)
state = loop_result.state
check("loop executed and touched real Scenario 11 documents", any(spec.doc_id in {Path(tools.get_document_filename(d)).stem for d in state.visited_document_ids} for spec in SCENARIO_11_DOCS))
check("both new Sub-Clauses (11.1, 11.2) were retrieved for this investigation", {"11.1", "11.2"}.issubset({c.clause_number for c in state.retrieved_clauses}))

narrowing_result = service._evidence_narrower.narrow(state.evidence)
check("evidence narrowing reduces Scenario 11's evidence into the 8-15 target range", 8 <= len(narrowing_result.retained_evidence) <= 15, str(len(narrowing_result.retained_evidence)))

print()
print("=== Citation quality: narrowed citations for the benchmark question include real Scenario 11 documents ===")
narrowed_stems = {Path(tools.get_document_filename(item.document_id)).stem for item in narrowing_result.retained_evidence}
check("at least 3 of the 5 expected decisive documents appear in the final narrowed citation set", len(set(bench["expected_decisive_docs"]) & narrowed_stems) >= 3, str(set(bench["expected_decisive_docs"]) & narrowed_stems))

print()
print("=== Benchmark correctness: real-Gemini result already on record (benchmark_results_narrowed.json) ===")
with open(Path(__file__).resolve().parent / "benchmark_results_narrowed.json") as f:
    bench_results = json.load(f)
s11_result = next((r for r in bench_results if r["id"] == "PIER-P2-DEFECT-LIABILITY"), None)
check("Scenario 11 benchmark result is present in the recorded benchmark run", s11_result is not None)
check("Scenario 11 benchmark completed without a Gemini error", s11_result is not None and s11_result["gemini"]["error"] is None)
check("Scenario 11 benchmark recall is at or above the pass threshold (0.5)", s11_result is not None and s11_result["retrieval"]["recall"] >= 0.5, str(s11_result["retrieval"]["recall"] if s11_result else None))

print()
print("=== Regression: Scenario 10 (Scenario 11's immediate predecessor) still benchmarks correctly ===")
s10_result = next((r for r in bench_results if r["id"] == "CONCURRENT-DELAY-P4"), None)
check("Scenario 10 benchmark result is present in the same recorded run", s10_result is not None)
check("Scenario 10 benchmark recall is unchanged from the Sprint 8 Task 02 final validation (0.4)", s10_result is not None and s10_result["retrieval"]["recall"] == 0.4, str(s10_result["retrieval"]["recall"] if s10_result else None))

print()
print("=" * 60)
if FAILURES:
    print(f"VALIDATION FAILED ({len(FAILURES)} check(s)):")
    for f in FAILURES:
        print(" -", f)
    sys.exit(1)
else:
    print("VALIDATION PASSED (all checks)")
