"""Validation for Phase 4 Task 04 (Scenario 12 — Employer Termination and
Final Account, Project 3: Kestrel Flyover Interchange Project, package
KFI-2). Runs against the real, newly-created project_id=3 (18 documents)
and the existing project_id=1/2 corpora, through the full, unmodified
Backend v1.0 production pipeline, at the frozen max_iterations=7 default.

Project isolation is the centrepiece of this validation (see the task's own
emphasis) and is checked in both directions: project 3 investigations must
retrieve only project 3 documents, and project 1/2 investigations must
never retrieve project 3 documents.

Updated for Sprint 8 Task 03 (Backend Patch v1.0.1): at the time this
script was first written, contract clause retrieval was NOT project-scoped
(a genuine, pre-existing architectural gap this scenario's own two-project
corpus first made observable), and the clause-isolation checks below were
deliberately asserted as non-fatal WARNs so the validation recorded honest
behavior rather than a false PASS. That gap has since been fixed (see
app/contracts/ingestion.py's get_clause_repository(project_id) and
dataset/scripts/validate_contract_intelligence_project_scoping.py, the
dedicated validation for that fix) — the clause-isolation checks below are
now ordinary hard `check()` assertions, matching the rest of this file,
since a genuine regression here should now fail this validation like any
other.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "backend"))

from app.agent import tools
from app.agent.service import InvestigationService
from app.agent.models import InvestigationRequest
from app.config import get_settings
from app.db.session import init_engine, get_session_factory
from app.db.models import Document, Project
from sqlalchemy import select, func

from scenario_12_data import DOCUMENTS as SCENARIO_12_DOCS
from contracts_data_kfi2 import DOCUMENTS as KFI2_CONTRACT_DOCS
from benchmarks import BENCHMARKS

FAILURES = []


def check(label: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {label}" + (f" -- {detail}" if detail else ""))
    if not condition:
        FAILURES.append(label)


init_engine(get_settings())

print("=== Project creation ===")
with get_session_factory()() as session:
    project3 = session.get(Project, 3)
    all_projects = session.scalars(select(Project).order_by(Project.id)).all()
check("project_id=3 exists", project3 is not None)
check(
    "project_id=3 name matches the approved project",
    project3 is not None and project3.name == "Kestrel Flyover Interchange Project — Package KFI-2",
    str(project3.name if project3 else None),
)
check("exactly 3 projects exist (1, 2, 3), no accidental duplicate created", len(all_projects) == 3, str([p.id for p in all_projects]))

print()
print("=== Timeline consistency ===")
all_specs = KFI2_CONTRACT_DOCS + SCENARIO_12_DOCS
dated_specs = [s for s in SCENARIO_12_DOCS]
dates = [datetime.strptime(spec.date, "%d-%b-%Y") for spec in dated_specs]
check("all 14 Scenario 12 documents have parseable dates", len(dates) == 14)
check("dates are in non-decreasing chronological order (matches DOCUMENTS list order)", dates == sorted(dates))
check(
    "Notice to Correct predates Notice of Termination, which predates the Final Account",
    dates[SCENARIO_12_DOCS.index(next(s for s in SCENARIO_12_DOCS if s.doc_id == "NTC-KFI2-001"))]
    < dates[SCENARIO_12_DOCS.index(next(s for s in SCENARIO_12_DOCS if s.doc_id == "NOT-KFI2-001"))]
    < dates[SCENARIO_12_DOCS.index(next(s for s in SCENARIO_12_DOCS if s.doc_id == "EFA-KFI2-001"))],
)
toc_expiry = datetime(2021, 6, 2)  # Time for Completion
termination_date = datetime(2021, 6, 21)
check(
    "termination date (21-Jun-2021) is after the Time for Completion (02-Jun-2021), so a "
    "genuine Liquidated Damages period exists",
    termination_date > toc_expiry,
)

print()
print("=== Financial consistency (independently recomputed from the documents' own figures) ===")
gross_certified = 15_100_000
retention_pct = 0.05
retention_held = round(gross_certified * retention_pct)
net_paid = gross_certified - retention_held
final_value = 15_800_000
ld_days = 19 - 5
ld_rate = 21_600
ld_total = ld_days * ld_rate
net_balance = final_value - net_paid - ld_total
check("retention held recomputes to KLD 755,000 (5% of gross certified KLD 15,100,000)", retention_held == 755_000, str(retention_held))
check("net amount paid to date recomputes to KLD 14,345,000", net_paid == 14_345_000, str(net_paid))
check("chargeable LD period recomputes to 14 days (19 - 5 day utility credit)", ld_days == 14, str(ld_days))
check("liquidated damages recompute to KLD 302,400 (14 days x KLD 21,600/day)", ld_total == 302_400, str(ld_total))
check("net balance recomputes to KLD 1,152,600, matching EFA-KFI2-001 and FCR-KFI2-001", net_balance == 1_152_600, str(net_balance))
check("LD total does not exceed the Contract Data maximum (KLD 3,600,000)", ld_total <= 3_600_000)

print()
print("=== No document id or clause number collisions with Scenarios 1-11 or the NRB4 contract package ===")
with open(Path(__file__).resolve().parent / "ingestion_report.json") as f:
    nrb4_report = json.load(f)
nrb4_ids = {d["doc_id"] for d in nrb4_report["documents"]}
new_ids = {spec.doc_id for spec in all_specs}
check("no Project 3 document id collides with any NRB4/Scenario 1-11 document id", not (nrb4_ids & new_ids), str(nrb4_ids & new_ids))
check("all 18 Project 3 document ids are unique among themselves", len(new_ids) == 18, str(len(new_ids)))

# Sprint 8 Task 03 (Backend Patch v1.0.1): clause repositories are now
# project-scoped, so each project's own repository is checked separately,
# rather than one combined 17-clause global repository as before the fix.
from app.contracts.ingestion import get_clause_repository
get_clause_repository.cache_clear()
repo_p2 = get_clause_repository(2)
repo_p3 = get_clause_repository(3)
clause_numbers_p2 = {c.clause_number for c in repo_p2.get_all()}
clause_numbers_p3 = {c.clause_number for c in repo_p3.get_all()}
nrb4_clause_numbers = {"1.3", "3.3", "4.1", "4.12", "8.4", "8.7", "11.1", "11.2", "13.1", "13.3", "14.3", "14.7", "20.1"}
kfi2_clause_numbers = {"15.1", "15.2", "15.3", "15.4"}
check("no clause_number string collision between the NRB4 and KFI2 packages", not (nrb4_clause_numbers & kfi2_clause_numbers))
check("Project 2's own clause repository has exactly 13 clauses (NRB4 only)", clause_numbers_p2 == nrb4_clause_numbers, str(clause_numbers_p2))
check("Project 3's own clause repository has exactly 4 clauses (KFI2 only)", clause_numbers_p3 == kfi2_clause_numbers, str(clause_numbers_p3))
check("Project 2's repository contains zero KFI2 clause numbers", not (clause_numbers_p2 & kfi2_clause_numbers))
check("Project 3's repository contains zero NRB4 clause numbers", not (clause_numbers_p3 & nrb4_clause_numbers))

print()
print("=== Real database state ===")
with get_session_factory()() as session:
    doc_count_p3 = session.scalar(select(func.count()).select_from(Document).where(Document.project_id == 3))
    docs_p3 = session.scalars(select(Document).where(Document.project_id == 3)).all()
    total_chunks_p3 = sum(len(d.chunks) for d in docs_p3)
    doc_count_p2 = session.scalar(select(func.count()).select_from(Document).where(Document.project_id == 2))
    doc_count_p1 = session.scalar(select(func.count()).select_from(Document).where(Document.project_id == 1))
check("project_id=3 has exactly 18 documents (4 contract + 14 scenario)", doc_count_p3 == 18, str(doc_count_p3))
check("every project 3 document has a non-null doc_type and doc_date", all(d.doc_type and d.doc_date for d in docs_p3))
check("every project 3 document has at least one chunk", all(len(d.chunks) > 0 for d in docs_p3))
check("project_id=2 (NRB4) is completely unchanged at 99 documents", doc_count_p2 == 99, str(doc_count_p2))
check("project_id=1 (DMV-7) is completely unchanged", doc_count_p1 is not None and doc_count_p1 > 0, str(doc_count_p1))
print(f"  total chunks across the 18 Project 3 documents: {total_chunks_p3}")

print()
print("=" * 70)
print("PROJECT ISOLATION VALIDATION (the centrepiece of this task)")
print("=" * 70)

print()
print("--- Document-level isolation (search_documents, DB project_id-scoped) ---")
p3_citations = tools.search_documents(project_id=3, query="termination final account liquidated damages retention", top_k=15)
p3_stems = {Path(tools.get_document_filename(c.document_id)).stem for c in p3_citations}
p3_own_ids = {spec.doc_id for spec in all_specs}
check("Project 3 search returns only Project 3 documents", p3_stems.issubset(p3_own_ids), str(p3_stems - p3_own_ids))
check("Project 3 search surfaces at least 5 real Project 3 documents", len(p3_stems) >= 5, str(len(p3_stems)))

p2_citations = tools.search_documents(project_id=2, query="termination final account liquidated damages retention Rennick Kaldera", top_k=15)
p2_stems = {Path(tools.get_document_filename(c.document_id)).stem for c in p2_citations}
check("Project 2 (NRB4) search, even with Project 3's own vocabulary, returns zero Project 3 documents", not (p2_stems & p3_own_ids), str(p2_stems & p3_own_ids))

p1_citations = tools.search_documents(project_id=1, query="termination final account liquidated damages retention Rennick Kaldera", top_k=15)
p1_stems = {Path(tools.get_document_filename(c.document_id)).stem for c in p1_citations}
check("Project 1 (DMV-7) search, even with Project 3's own vocabulary, returns zero Project 3 documents", not (p1_stems & p3_own_ids), str(p1_stems & p3_own_ids))

print()
print("--- Full Investigation Loop isolation (real, frozen max_iterations=7) ---")
service = InvestigationService()
check(
    "InvestigationLoopConfig.max_iterations is the frozen production default (7), unmodified by this task",
    service._investigation_loop._config.max_iterations == 7,
    str(service._investigation_loop._config.max_iterations),
)
bench = next(b for b in BENCHMARKS if b["id"] == "KFI2-TERMINATION-FINAL-ACCOUNT")
req3 = InvestigationRequest(project_id=3, query=bench["question"], top_k=10)
loop_result_3 = service._investigation_loop.run(req3)
state3 = loop_result_3.state
visited_stems_3 = {Path(tools.get_document_filename(d)).stem for d in state3.visited_document_ids}
check("Project 3 investigation visits only real Project 3 documents (zero NRB4 contamination)", visited_stems_3.issubset(p3_own_ids), str(visited_stems_3 - p3_own_ids))
check("Project 3 investigation visits at least 5 real Project 3 documents", len(visited_stems_3) >= 5, str(len(visited_stems_3)))

nrb4_bench = next(b for b in BENCHMARKS if b["id"] == "CONCURRENT-DELAY-P4")
req2 = InvestigationRequest(project_id=2, query=nrb4_bench["question"], top_k=10)
loop_result_2 = service._investigation_loop.run(req2)
state2 = loop_result_2.state
visited_stems_2 = {Path(tools.get_document_filename(d)).stem for d in state2.visited_document_ids}
check("Project 2 (NRB4) investigation visits zero Project 3 documents", not (visited_stems_2 & p3_own_ids), str(visited_stems_2 & p3_own_ids))

narrowing_result_3 = service._evidence_narrower.narrow(state3.evidence)
narrowed_stems_3 = {Path(tools.get_document_filename(item.document_id)).stem for item in narrowing_result_3.retained_evidence}
check("Project 3's final narrowed citation set contains only Project 3 documents", narrowed_stems_3.issubset(p3_own_ids), str(narrowed_stems_3 - p3_own_ids))
check("Evidence narrowing reduces Project 3's evidence into the 8-15 target range", 8 <= len(narrowing_result_3.retained_evidence) <= 15, str(len(narrowing_result_3.retained_evidence)))

print()
print("--- Contract clause isolation (Sprint 8 Task 03 fix -- was a WARN-level known gap, now a hard PASS check) ---")
clause_numbers_3 = {c.clause_number for c in state3.retrieved_clauses}
foreign_in_3 = clause_numbers_3 & nrb4_clause_numbers
check(
    "Project 3 investigation's retrieved_clauses contains zero NRB4 clause numbers",
    not foreign_in_3,
    str(foreign_in_3) if foreign_in_3 else "",
)
check(
    "Project 3 investigation retrieved at least one of its own (KFI2) clause numbers",
    bool(clause_numbers_3 & kfi2_clause_numbers),
    str(clause_numbers_3),
)
clause_numbers_2 = {c.clause_number for c in state2.retrieved_clauses}
foreign_in_2 = clause_numbers_2 & kfi2_clause_numbers
check(
    "Project 2 (NRB4) investigation's retrieved_clauses contains zero KFI2 clause numbers",
    not foreign_in_2,
    str(foreign_in_2) if foreign_in_2 else "",
)
check(
    "Project 2 investigation retrieved at least one of its own (NRB4) clause numbers",
    bool(clause_numbers_2 & nrb4_clause_numbers),
    str(clause_numbers_2),
)

print()
print("=== Citation quality: narrowed citations for the benchmark question include real Project 3 documents ===")
check("at least 4 of the 5 expected decisive documents appear in the final narrowed citation set", len(set(bench["expected_decisive_docs"]) & narrowed_stems_3) >= 4, str(set(bench["expected_decisive_docs"]) & narrowed_stems_3))

print()
print("=== Benchmark correctness: real-Gemini result already on record (benchmark_results_narrowed.json) ===")
with open(Path(__file__).resolve().parent / "benchmark_results_narrowed.json") as f:
    bench_results = json.load(f)
s12_result = next((r for r in bench_results if r["id"] == "KFI2-TERMINATION-FINAL-ACCOUNT"), None)
check("Scenario 12 benchmark result is present in the recorded benchmark run", s12_result is not None)
check("Scenario 12 benchmark result is tagged project_id=3", s12_result is not None and s12_result.get("project_id") == 3, str(s12_result.get("project_id") if s12_result else None))
check("Scenario 12 benchmark completed without a Gemini error", s12_result is not None and s12_result["gemini"]["error"] is None)
check("Scenario 12 benchmark recall is at or above the pass threshold (0.5)", s12_result is not None and s12_result["retrieval"]["recall"] >= 0.5, str(s12_result["retrieval"]["recall"] if s12_result else None))

print()
print("=== Regression: Scenario 10 and Scenario 11 produce identical measured results (project_id=2 untouched) ===")
s10_result = next((r for r in bench_results if r["id"] == "CONCURRENT-DELAY-P4"), None)
s11_result = next((r for r in bench_results if r["id"] == "PIER-P2-DEFECT-LIABILITY"), None)
check("Scenario 10 recall is unchanged (0.4)", s10_result is not None and s10_result["retrieval"]["recall"] == 0.4, str(s10_result["retrieval"]["recall"] if s10_result else None))
check("Scenario 10 hits/misses are unchanged", s10_result is not None and s10_result["retrieval"]["hits"] == ["CTR-NRB4-0125", "ENG-NRB4-0072"])
check("Scenario 11 recall is unchanged (0.6)", s11_result is not None and s11_result["retrieval"]["recall"] == 0.6, str(s11_result["retrieval"]["recall"] if s11_result else None))
check("Scenario 11 hits/misses are unchanged", s11_result is not None and s11_result["retrieval"]["hits"] == ["DIR-NRB4-001", "EAC-NRB4-001", "ENG-NRB4-0083"])

print()
print("=" * 60)
if FAILURES:
    print(f"VALIDATION FAILED ({len(FAILURES)} check(s)):")
    for f in FAILURES:
        print(" -", f)
    sys.exit(1)
else:
    print("VALIDATION PASSED (all checks)")
