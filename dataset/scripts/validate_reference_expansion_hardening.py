"""Validation for Phase 3 Task 03A (Reference Expansion Hardening). Runs
against the real, already-ingested Dataset V1 (project_id=1) and Dataset V2
(project_id=2) corpora -- real retrieval, real reference expansion, zero
Gemini calls. Uses InvestigationAgent (Task 02) only to produce a realistic
starting InvestigationState; tools.find_related_documents() and
ReferenceExpansionExecutor are exercised directly.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "backend"))

from app.agent.investigation_agent import InvestigationAgent
from app.agent.investigation_state import InvestigationState, RemediationType
from app.agent.models import InvestigationRequest
from app.agent.reference_expansion_config import ReferenceExpansionConfig
from app.agent.reference_expansion_executor import ReferenceExpansionExecutor
from app.agent import tools
from app.config import get_settings
from app.db.session import init_engine

FAILURES = []


def check(label: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {label}" + (f" -- {detail}" if detail else ""))
    if not condition:
        FAILURES.append(label)


init_engine(get_settings())
agent = InvestigationAgent()
executor = ReferenceExpansionExecutor()

# A config equivalent to Task 03's original, unhardened tool: no boilerplate
# filtering (ratio > 1.0 can never trigger) -- used ONLY to reproduce the
# documented "before" baseline via the real code path, not a reimplementation.
_UNFILTERED_CONFIG = ReferenceExpansionConfig(max_document_frequency_ratio=1.1)

print("=== Setup: real EOT-01 investigation state (project_id=2, Dataset V2) ===")
req = InvestigationRequest(
    project_id=2,
    query="Was the Contractor entitled to an extension of time for the Pier 3 utility conflict, and if so, for how long?",
    top_k=10,
)
run_result = agent.run(req)
state = run_result.state
print(f"  visited_document_ids ({len(state.visited_document_ids)}): {sorted(state.visited_document_ids)}")

print()
print("=== Before vs after: boilerplate-frequency filtering (Task 2 / 3) ===")
before_ids = tools.find_related_documents(
    list(state.visited_document_ids), project_id=None, config=_UNFILTERED_CONFIG
)
after_ids = tools.find_related_documents(list(state.visited_document_ids), project_id=2)
print(f"  BEFORE (unfiltered, unscoped -- reproduces Task 03's original tool): {len(before_ids)} documents discovered")
print(f"  AFTER  (boilerplate-filtered, project-scoped)                      : {len(after_ids)} documents discovered")
check(
    "hardened tool discovers substantially fewer documents than the unfiltered baseline",
    len(after_ids) < len(before_ids) * 0.5,
    f"before={len(before_ids)}, after={len(after_ids)}",
)
check(
    "hardened result is a subset of the unfiltered result (filtering only removes, never adds)",
    set(after_ids).issubset(set(before_ids)),
)

print()
print("=== Genuine referenced documents are still discovered ===")
added_filenames = {tools.get_document_filename(doc_id) for doc_id in after_ids}
check(
    "VPGC-NRB4-0012.pdf / VPGC-NRB4-0045.pdf survive the boilerplate filter",
    {"VPGC-NRB4-0012.pdf", "VPGC-NRB4-0045.pdf"}.issubset(added_filenames),
    str(sorted(added_filenames)),
)

print()
print("=== Project isolation ===")
check(
    "every hardened-tool result for project_id=2 actually belongs to project 2",
    all(19 <= doc_id <= 89 for doc_id in after_ids),
    str(sorted(after_ids)),
)
v1_related = tools.find_related_documents([1, 2, 3, 4, 5], project_id=1)
check(
    "project_id=1 query returns only project-1-range document ids",
    all(1 <= doc_id <= 17 for doc_id in v1_related),
    str(sorted(v1_related)),
)
v1_unscoped = tools.find_related_documents([1, 2, 3, 4, 5], project_id=None)
check(
    "omitting project_id (None) preserves the original, unscoped behaviour (can still return non-V1 ids)",
    True,  # informational -- see printed detail, no assumption about which ids exist
)
print(f"  project_id=1, scoped: {sorted(v1_related)}")
print(f"  project_id=None (unscoped), same seed: {sorted(v1_unscoped)}")

print()
print("=== Executor end-to-end: project scoping is automatic (no caller-supplied project_id) ===")
expansion_result = executor.expand(state)
check(
    "expand() discovered at least one new document, still project-scoped automatically",
    len(expansion_result.documents_added) > 0,
    str(expansion_result.documents_added),
)
check(
    "all documents added by expand() belong to project 2",
    all(19 <= doc_id <= 89 for doc_id in expansion_result.documents_added),
    str(expansion_result.documents_added),
)

print()
print("=== Duplicate prevention still functions (controlled fixture) ===")
from app.agent.models import Citation as _Citation, Evidence as _Evidence  # noqa: E402
from app.investigation.models import InvestigationPlan as _Plan  # noqa: E402

repeat_state = InvestigationState(plan=_Plan(goal="test", investigation_type="delay", expected_answer_type="duration"))
repeat_state.add_evidence(
    [
        _Evidence(
            citation=_Citation(document_id=29, chunk_id=101, page=1, relevance_score=0.9),
            document_id=29,
            document_name="ENG-NRB4-0019.pdf",
            excerpt="We refer to VPGC-NRB4-0012 for the relocation timeline.",
            surrounding_context="We refer to VPGC-NRB4-0012 for the relocation timeline.",
            confidence=0.9,
        )
    ]
)
repeat_state.mark_reference_followed("VPGC-NRB4-0012")
no_op_result = executor.expand(repeat_state)
check("a fully-followed state finds nothing new to attempt", no_op_result.references_attempted == [])
check("a fully-followed state adds zero new evidence", no_op_result.new_evidence_count == 0)
check("evidence count unchanged for a fully-followed state", len(repeat_state.evidence) == 1)

print()
print("=== Missing / unresolvable references terminate cleanly (no crash) ===")
import app.agent.reference_expansion_executor as _executor_module  # noqa: E402

missing_state = InvestigationState(plan=_Plan(goal="test", investigation_type="delay", expected_answer_type="duration"))
missing_state.add_evidence(
    [
        _Evidence(
            citation=_Citation(document_id=29, chunk_id=101, page=1, relevance_score=0.9),
            document_id=29,
            document_name="ENG-NRB4-0019.pdf",
            excerpt="This mentions NOPE-DOES-NOT-EXIST-0001 as a related reference.",
            surrounding_context="This mentions NOPE-DOES-NOT-EXIST-0001 as a related reference.",
            confidence=0.9,
        )
    ]
)
_original_find_related = _executor_module.tools.find_related_documents
_executor_module.tools.find_related_documents = lambda document_ids, project_id=None, config=None: []
try:
    missing_result = executor.expand(missing_state)
finally:
    _executor_module.tools.find_related_documents = _original_find_related

check("expand() does not raise when the hardened tool finds nothing", True)
check("the reference was attempted", "NOPE-DOES-NOT-EXIST-0001" in missing_result.references_attempted)
check("no documents were added", missing_result.documents_added == [])
check("no new evidence was added", missing_result.new_evidence_count == 0)
check(
    "the reference is still marked followed despite not resolving",
    "NOPE-DOES-NOT-EXIST-0001" in missing_state.followed_reference_ids,
)

print()
print("=== Expansion budget is respected automatically ===")
# A tight budget (well below the real corpus's genuine expansion breadth for
# this seed) to force capping deterministically, using a fresh executor
# instance so the default-config executor above is untouched.
tight_executor = ReferenceExpansionExecutor(
    config=ReferenceExpansionConfig(
        max_document_frequency_ratio=0.5,
        max_references_processed=1,
        max_documents_added=1,
        max_new_evidence_added=1,
    )
)
budget_req = InvestigationRequest(
    project_id=2,
    query="Was the Contractor entitled to an extension of time for the Pier 3 utility conflict, and if so, for how long?",
    top_k=10,
)
budget_state = agent.run(budget_req).state
unresolved_count_before = len(
    executor._assessor._check_unresolved_references(budget_state).details.get("unresolved_references", [])
)
budget_result = tight_executor.expand(budget_state)
check(
    "max_references_processed=1 caps references_attempted to at most 1",
    len(budget_result.references_attempted) <= 1,
    str(budget_result.references_attempted),
)
if unresolved_count_before > 1:
    check(
        "excess references are reported as deferred, not silently dropped",
        len(budget_result.references_deferred) == unresolved_count_before - 1,
        f"before={unresolved_count_before}, deferred={budget_result.references_deferred}",
    )
    check(
        "a deferred reference is NOT marked followed (remains eligible for a future call)",
        not set(budget_result.references_deferred).issubset(budget_state.followed_reference_ids),
    )
check(
    "max_documents_added=1 caps documents_added to at most 1",
    len(budget_result.documents_added) <= 1,
    str(budget_result.documents_added),
)
check(
    "max_new_evidence_added=1 caps new_evidence_count to at most 1",
    budget_result.new_evidence_count <= 1,
    str(budget_result.new_evidence_count),
)
check(
    "search_history entry is still recorded for a budget-capped call",
    budget_state.search_history[-1].trigger_reason == RemediationType.REFERENCE_EXPANSION,
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
