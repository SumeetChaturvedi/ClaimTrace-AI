"""Validation for Sprint 8 Task 03 (Backend Patch v1.0.1) — Project-Scoped
Contract Intelligence.

Root cause fixed: get_default_clause_repository() (app/contracts/ingestion.py)
was a single, process-wide, zero-argument functools.lru_cache that built one
ClauseRepository from EVERY contract package file found under
backend/storage/contracts/, regardless of which project an investigation
concerned. InvestigationService resolved it once, at singleton construction
time (before any request/project_id exists), and reused it for every
request. Document retrieval (tools.search_documents) was, and remains,
correctly project-scoped by project_id at the database level -- only
Contract Intelligence lacked any equivalent scoping. First made observable
by Phase 4 Task 04 (Scenario 12), which added a second, genuinely
independent project (project_id=3, KFI2) with its own Sub-Clauses (15.1-
15.4): every investigation, on either project, could retrieve the other
project's clauses.

Fix: each project's contract package now lives in its own subdirectory,
storage/contracts/{project_id}/, mirroring the per-project layout
app/ingestion/storage.py already used for PDFs/extracted text.
get_clause_repository(project_id) (replacing get_default_clause_repository())
is memoized per project_id and resolves only that project's own directory.
InvestigationService no longer resolves a single fixed ClauseRepository/
ClauseRetriever at construction time; instead,
_clause_retriever_for_project(project_id) resolves one per request, called
from InvestigationAgent.run() with that request's own request.project_id
(the sole call site of contract clause retrieval in the whole per-request
pipeline). ClauseParser, ClauseRepository, ClauseRetriever,
ClauseSearchService, ContractContextBuilder are entirely unchanged.

This script performs the validation the task itself specifies: bidirectional
contract-clause isolation between project_id=2 (NRB4) and project_id=3
(KFI2), plus confirmation that document retrieval, evidence narrowing, and
the Investigation Loop are unaffected (a full benchmark regression is run
separately via run_benchmarks_narrowed.py; see the final report)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "backend"))

from app.agent import tools
from app.agent.service import InvestigationService
from app.agent.models import InvestigationRequest
from app.config import get_settings
from app.db.session import init_engine
from app.contracts.ingestion import get_clause_repository, ContractPackageLoader

from benchmarks import BENCHMARKS

FAILURES = []


def check(label: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {label}" + (f" -- {detail}" if detail else ""))
    if not condition:
        FAILURES.append(label)


init_engine(get_settings())

NRB4_CLAUSES = {"1.3", "3.3", "4.1", "4.12", "8.4", "8.7", "11.1", "11.2", "13.1", "13.3", "14.3", "14.7", "20.1"}
KFI2_CLAUSES = {"15.1", "15.2", "15.3", "15.4"}

print("=== Storage layout: per-project contract package subdirectories ===")
storage_root = get_settings().storage_root
check("storage/contracts/2/ (NRB4) exists", (storage_root / "contracts" / "2").is_dir())
check("storage/contracts/3/ (KFI2) exists", (storage_root / "contracts" / "3").is_dir())
check(
    "storage/contracts/ root directory itself has no loose contract files left "
    "(everything moved into per-project subdirectories)",
    not any(p.is_file() for p in (storage_root / "contracts").iterdir()) if (storage_root / "contracts").is_dir() else True,
)

print()
print("=== get_clause_repository(project_id): each project resolves only its own package ===")
get_clause_repository.cache_clear()
repo_1 = get_clause_repository(1)
repo_2 = get_clause_repository(2)
repo_3 = get_clause_repository(3)
clauses_1 = {c.clause_number for c in repo_1.get_all()}
clauses_2 = {c.clause_number for c in repo_2.get_all()}
clauses_3 = {c.clause_number for c in repo_3.get_all()}
check("project_id=1 (DMV-7, no contract package) resolves to an empty repository, not an error", clauses_1 == set(), str(clauses_1))
check("project_id=2 (NRB4) resolves to exactly its own 13 clauses", clauses_2 == NRB4_CLAUSES, str(clauses_2))
check("project_id=3 (KFI2) resolves to exactly its own 4 clauses", clauses_3 == KFI2_CLAUSES, str(clauses_3))
check("project 2's repository contains zero KFI2 clause numbers", not (clauses_2 & KFI2_CLAUSES))
check("project 3's repository contains zero NRB4 clause numbers", not (clauses_3 & NRB4_CLAUSES))

print()
print("=== Memoization preserved: repeated calls for the same project_id return the same cached object ===")
check("get_clause_repository(2) is memoized (identical object on a second call)", get_clause_repository(2) is repo_2)
check("get_clause_repository(3) is memoized (identical object on a second call)", get_clause_repository(3) is repo_3)

print()
print("=== ContractPackageLoader itself is unchanged: still a plain single-directory loader ===")
manual_repo_2 = ContractPackageLoader(contract_package_dir=storage_root / "contracts" / "2").load()
check(
    "ContractPackageLoader, called directly with an explicit directory, reproduces the same clause set "
    "get_clause_repository(2) resolves (confirms the fix is purely in directory/cache-key selection, "
    "not in ContractPackageLoader/ClauseParser/ClauseRepository themselves)",
    {c.clause_number for c in manual_repo_2.get_all()} == clauses_2,
)

print()
print("=== Bidirectional Investigation Loop isolation (real, frozen max_iterations=7, per-request resolution) ===")
service = InvestigationService()
check(
    "InvestigationLoopConfig.max_iterations is the frozen production default (7), untouched by this task",
    service._investigation_loop._config.max_iterations == 7,
    str(service._investigation_loop._config.max_iterations),
)

nrb4_bench = next(b for b in BENCHMARKS if b["id"] == "CONCURRENT-DELAY-P4")
req_2 = InvestigationRequest(project_id=2, query=nrb4_bench["question"], top_k=10)
loop_result_2 = service._investigation_loop.run(req_2)
retrieved_clauses_2 = {c.clause_number for c in loop_result_2.state.retrieved_clauses}
check("a real project_id=2 investigation retrieves zero KFI2 clause numbers", not (retrieved_clauses_2 & KFI2_CLAUSES), str(retrieved_clauses_2 & KFI2_CLAUSES))
check("a real project_id=2 investigation retrieves at least one genuine NRB4 clause", bool(retrieved_clauses_2 & NRB4_CLAUSES), str(retrieved_clauses_2))

kfi2_bench = next(b for b in BENCHMARKS if b["id"] == "KFI2-TERMINATION-FINAL-ACCOUNT")
req_3 = InvestigationRequest(project_id=3, query=kfi2_bench["question"], top_k=10)
loop_result_3 = service._investigation_loop.run(req_3)
retrieved_clauses_3 = {c.clause_number for c in loop_result_3.state.retrieved_clauses}
check("a real project_id=3 investigation retrieves zero NRB4 clause numbers", not (retrieved_clauses_3 & NRB4_CLAUSES), str(retrieved_clauses_3 & NRB4_CLAUSES))
check("a real project_id=3 investigation retrieves at least one genuine KFI2 clause", bool(retrieved_clauses_3 & KFI2_CLAUSES), str(retrieved_clauses_3))

print()
print("=== Same InvestigationService singleton correctly serves BOTH projects in sequence (the actual production shape) ===")
# The bug could only have existed because the service is a long-lived
# singleton reused across every request (app/api/routes/investigate.py's
# get_investigation_service() is @lru_cache'd). This section proves the fix
# holds under exactly that shape: one already-constructed `service`, called
# with project_id=2 and then project_id=3 back to back (as it would be in
# production, request after request), each still resolving only its own
# clauses -- not the fix "working" only because of a fresh instance per call.
req_2_again = InvestigationRequest(project_id=2, query=nrb4_bench["question"], top_k=10)
loop_result_2_again = service._investigation_loop.run(req_2_again)
retrieved_again_2 = {c.clause_number for c in loop_result_2_again.state.retrieved_clauses}
check("the SAME singleton service, called again for project 2 after having just served project 3, still returns zero KFI2 clauses", not (retrieved_again_2 & KFI2_CLAUSES), str(retrieved_again_2 & KFI2_CLAUSES))

print()
print("=== Document retrieval, evidence, and citations are untouched by this fix ===")
citations_2 = tools.search_documents(project_id=2, query=nrb4_bench["question"], top_k=10)
citations_3 = tools.search_documents(project_id=3, query=kfi2_bench["question"], top_k=10)
check("project 2 document search still returns real NRB4 documents", len(citations_2) > 0, str(len(citations_2)))
check("project 3 document search still returns real KFI2 documents", len(citations_3) > 0, str(len(citations_3)))
narrowing_2 = service._evidence_narrower.narrow(loop_result_2.state.evidence)
narrowing_3 = service._evidence_narrower.narrow(loop_result_3.state.evidence)
check("Evidence Narrowing still reduces project 2 evidence into the 8-15 target range", 8 <= len(narrowing_2.retained_evidence) <= 15, str(len(narrowing_2.retained_evidence)))
check("Evidence Narrowing still reduces project 3 evidence into the 8-15 target range", 8 <= len(narrowing_3.retained_evidence) <= 15, str(len(narrowing_3.retained_evidence)))

print()
print("=" * 60)
if FAILURES:
    print(f"VALIDATION FAILED ({len(FAILURES)} check(s)):")
    for f in FAILURES:
        print(" -", f)
    sys.exit(1)
else:
    print("VALIDATION PASSED (all checks) — Contract Intelligence is now project-scoped, "
          "bidirectionally, under real singleton-service production conditions.")
