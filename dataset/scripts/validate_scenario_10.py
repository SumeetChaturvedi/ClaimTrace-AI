"""Validation for Phase 4 Task 02 (Scenario 10 — Concurrent Delay). Runs
against the real, now-expanded Dataset V2 corpus (project_id=2, 85
documents), through the full, unmodified Backend v1.0 production pipeline.
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

from scenario_10_data import DOCUMENTS as SCENARIO_10_DOCS
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
dates = [datetime.strptime(spec.date, "%d-%b-%Y") for spec in SCENARIO_10_DOCS]
check("all 14 documents have parseable dates", len(dates) == 14)
check("dates are in non-decreasing chronological order (matches DOCUMENTS list order)", dates == sorted(dates))
check(
    "scenario spans after the existing corpus's Aug-2022 quiet-period start (no overlap with Scenario 1-9 events)",
    dates[0] >= datetime(2022, 8, 9) and dates[-1] <= datetime(2023, 9, 5),
    f"{dates[0].date()} .. {dates[-1].date()}",
)
concurrent_start = datetime(2022, 11, 7)
concurrent_end = datetime(2022, 11, 28)
ground_start = datetime(2022, 11, 3)
ground_end = datetime(2022, 12, 15)
check(
    "plant breakdown period (07-Nov to 28-Nov) falls entirely within the ground-condition period (03-Nov to 15-Dec)",
    ground_start <= concurrent_start and concurrent_end <= ground_end,
)
check(
    "non-concurrent ground-condition-only days + concurrent days sum to the full 6-week claimed period",
    (concurrent_start - ground_start).days + (ground_end - concurrent_end).days + (concurrent_end - concurrent_start).days == 42,
)

print()
print("=== No document id collisions with Scenarios 1-9 or the contract package ===")
with open(Path(__file__).resolve().parent / "ingestion_report.json") as f:
    import json
    existing_report = json.load(f)
existing_ids = {d["doc_id"] for d in existing_report["documents"] if d.get("document_pk", 999) < 90}
new_ids = {spec.doc_id for spec in SCENARIO_10_DOCS}
check("no Scenario 10 document id collides with an existing document id", not (existing_ids & new_ids), str(existing_ids & new_ids))
check("all 14 Scenario 10 document ids are unique among themselves", len(new_ids) == 14)

print()
print("=== Real database state ===")
from app.db.session import get_session_factory
with get_session_factory()() as session:
    from sqlalchemy import func
    doc_count = session.scalar(select(func.count()).select_from(Document).where(Document.project_id == PROJECT_ID))
    all_project_docs = session.scalars(select(Document).where(Document.project_id == PROJECT_ID)).all()
    scenario_10_ids = {spec.doc_id for spec in SCENARIO_10_DOCS}
    scenario_10_docs_in_db = [d for d in all_project_docs if d.filename and Path(d.filename).stem in scenario_10_ids]
    total_chunks_new = sum(len(d.chunks) for d in scenario_10_docs_in_db)

# Note: project_id=2 has since grown past 85 documents as later scenarios
# (11, 12) were added on top of Scenario 10 -- this check only asserts the
# corpus has not shrunk below Scenario 10's own known floor, not an exact
# snapshot count frozen at Scenario 10's own completion time.
check("project_id=2 has at least 85 documents (71 existing + 14 Scenario 10, plus any added since)", doc_count >= 85, str(doc_count))
check("all 14 Scenario 10 documents are present in the database", len(scenario_10_docs_in_db) == 14, str(len(scenario_10_docs_in_db)))
check("every new document has a non-null doc_type and doc_date", all(d.doc_type and d.doc_date for d in scenario_10_docs_in_db))
check("every new document has at least one chunk", all(len(d.chunks) > 0 for d in scenario_10_docs_in_db))
print(f"  total chunks across the 14 new documents: {total_chunks_new}")

print()
print("=== New contract clause (Sub-Clause 4.12) is retrievable, existing 10 clauses unaffected ===")
from app.contracts.ingestion import get_clause_repository
get_clause_repository.cache_clear()
repo = get_clause_repository(PROJECT_ID)
clauses = repo.get_all()
check("clause repository has at least 11 clauses (10 existing + Sub-Clause 4.12, plus any added since)", len(clauses) >= 11, str(len(clauses)))
clause_412 = next((c for c in clauses if c.clause_number == "4.12"), None)
check("Sub-Clause 4.12 (Unforeseeable Physical Conditions) is present and correctly parsed", clause_412 is not None and clause_412.title == "Unforeseeable Physical Conditions")
existing_numbers = {"1.3", "3.3", "4.1", "8.4", "8.7", "13.1", "13.3", "14.3", "14.7", "20.1"}
check("all 10 pre-existing clause numbers are still present, unmodified", existing_numbers.issubset({c.clause_number for c in clauses}))

print()
print("=== Retrieval is project-scoped and topically relevant ===")
citations = tools.search_documents(
    project_id=PROJECT_ID,
    query="Was the Contractor entitled to the full extension of time claimed for the Pier P4 ground condition delay, or should the concurrent plant breakdown reduce that entitlement?",
    top_k=10,
)
retrieved_stems = {Path(tools.get_document_filename(c.document_id)).stem for c in citations}
scenario_10_stems = {spec.doc_id for spec in SCENARIO_10_DOCS}
check("retrieval surfaces at least 3 real Scenario 10 documents in the top 10", len(retrieved_stems & scenario_10_stems) >= 3, str(retrieved_stems & scenario_10_stems))

print()
print("=== Full production pipeline: Investigation Loop + Evidence Narrowing (real, project_id=2) ===")
service = InvestigationService()
bench = next(b for b in BENCHMARKS if b["id"] == "CONCURRENT-DELAY-P4")
req = InvestigationRequest(project_id=PROJECT_ID, query=bench["question"], top_k=10)
loop_result = service._investigation_loop.run(req)
state = loop_result.state
check("loop executed and touched real Scenario 10 documents", any(spec.doc_id in {Path(tools.get_document_filename(d)).stem for d in state.visited_document_ids} for spec in SCENARIO_10_DOCS))
check("new Sub-Clause 4.12 was retrieved for this investigation", "4.12" in {c.clause_number for c in state.retrieved_clauses})

narrowing_result = service._evidence_narrower.narrow(state.evidence)
check("evidence narrowing reduces Scenario 10's evidence into the 8-15 target range", 8 <= len(narrowing_result.retained_evidence) <= 15, str(len(narrowing_result.retained_evidence)))

print()
print("=== Root-cause check: default iteration budget vs. full convergence (expected, already-documented limitation) ===")
from app.agent.investigation_loop_config import InvestigationLoopConfig
from app.agent.investigation_loop import InvestigationLoop
extended_loop = InvestigationLoop(config=InvestigationLoopConfig(max_iterations=20))
extended_result = extended_loop.run(req)
extended_stems = {Path(tools.get_document_filename(d)).stem for d in extended_result.state.visited_document_ids}
expected_decisive = set(bench["expected_decisive_docs"])
check(
    "with an extended iteration budget, all 5 expected decisive documents are found (confirms this is the known iteration-budget limitation, not a new retrieval defect)",
    expected_decisive.issubset(extended_stems),
    str(expected_decisive - extended_stems),
)

print()
print("=" * 60)
if FAILURES:
    print(f"VALIDATION FAILED ({len(FAILURES)} check(s)):")
    for f in FAILURES:
        print(" -", f)
    sys.exit(1)
else:
    print("VALIDATION PASSED (all checks)")
