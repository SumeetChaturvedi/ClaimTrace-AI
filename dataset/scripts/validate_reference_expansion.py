"""Validation for Phase 3 Task 03's ReferenceExpansionExecutor. Runs against
the real, already-ingested Dataset V2 corpus (project_id=2) -- real
retrieval, real reference expansion, zero Gemini calls. Uses
InvestigationAgent (Task 02) only to produce a realistic starting
InvestigationState; the executor itself is exercised directly.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "backend"))

from app.agent.investigation_agent import InvestigationAgent
from app.agent.investigation_state import InvestigationState, RemediationType
from app.agent.models import InvestigationRequest
from app.agent.reference_expansion_executor import ReferenceExpansionExecutor
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
PROJECT_ID = 2

print("=== Reference expansion discovers new evidence (real EOT-01 investigation) ===")
req = InvestigationRequest(
    project_id=PROJECT_ID,
    query="Was the Contractor entitled to an extension of time for the Pier 3 utility conflict, and if so, for how long?",
    top_k=10,
)
run_result = agent.run(req)
state = run_result.state

check(
    "initial run has an unresolved-reference decision (precondition for this test)",
    run_result.decision.remediation == RemediationType.REFERENCE_EXPANSION,
    f"got {run_result.decision.remediation}",
)
unresolved_before = set(run_result.decision.details.get("unresolved_references", []))
visited_before = set(state.visited_document_ids)
evidence_count_before = len(state.evidence)
history_len_before = len(state.search_history)
iteration_before = state.iteration_count

expansion_result = executor.expand(state)

check("expand() reports which references it attempted", set(expansion_result.references_attempted) == unresolved_before)
check("expand() discovered at least one new document", len(expansion_result.documents_added) > 0, str(expansion_result.documents_added))

# Resolve filenames for the newly added documents directly via the DB, to
# confirm the expected real Dataset V2 documents were the ones found.
from app.agent import tools as _tools  # noqa: E402

added_filenames = {_tools.get_document_filename(doc_id) for doc_id in expansion_result.documents_added}
check(
    "the specific documents VPGC-NRB4-0012.pdf / VPGC-NRB4-0045.pdf were discovered",
    {"VPGC-NRB4-0012.pdf", "VPGC-NRB4-0045.pdf"}.issubset(added_filenames),
    str(added_filenames),
)

print()
print("=== InvestigationState updates correctly ===")
check("evidence list grew", len(state.evidence) > evidence_count_before)
check("visited_document_ids grew to include the newly discovered documents", set(state.visited_document_ids) > visited_before)
check(
    "newly added evidence is tagged with its source",
    all(item.metadata.get("source") == "reference_expansion" for item in state.evidence if item.document_id in expansion_result.documents_added),
)
check(
    "newly added evidence uses real chunk ids (verifiable against the database)",
    all(item.citation.chunk_id is not None for item in state.evidence[evidence_count_before:]),
)
check(
    "previously unresolved references are now marked followed",
    unresolved_before.issubset(state.followed_reference_ids),
)
check("iteration_count advanced by exactly 1", state.iteration_count == iteration_before + 1)

print()
print("=== Search history records the expansion, successful case ===")
check("exactly one new search_history entry was added", len(state.search_history) == history_len_before + 1)
entry = state.search_history[-1]
check("new entry has trigger_reason REFERENCE_EXPANSION", entry.trigger_reason == RemediationType.REFERENCE_EXPANSION)
check("new entry's new_evidence_count matches what was actually added", entry.new_evidence_count == expansion_result.new_evidence_count)
check("new entry's query_text names the attempted references", all(ref in entry.query_text for ref in unresolved_before))

print()
print("=== Historical note: Task 03's original promiscuity finding, now hardened (Task 03A) ===")
# This section originally documented an unfixed finding: nearly every
# Dataset V2 document's metadata box shares boilerplate tokens ("NRB-4",
# the contract number "2020-01") that extract_document_references() (reused
# unchanged) treats as document identifiers, so a single expand() call
# discovered 64 of the corpus's 71 documents. Phase 3 Task 03A fixed this at
# the find_related_documents() layer (project scoping + document-frequency
# boilerplate filtering, app/agent/reference_expansion_config.py) -- this
# script now exercises the hardened tool, so the count below is the *after*
# number. See dataset/scripts/validate_reference_expansion_hardening.py for
# the full before/after measurement and the rest of Task 03A's validation.
print(f"  First expand() call (10 initially-visited documents) discovered {len(expansion_result.documents_added)} new documents (was 64 before Task 03A hardening).")

print()
print("=== Repeated/duplicate references terminate immediately (controlled fixture) ===")
# Hand-built, not relying on the real corpus's expansion breadth above, so
# this isolates exactly the required behaviour: a reference already in
# followed_reference_ids must not be re-attempted, and a call with nothing
# unresolved must do zero retrieval.
from app.agent.models import Citation as _Citation, Evidence as _Evidence  # noqa: E402
from app.investigation.models import InvestigationPlan as _Plan  # noqa: E402

repeat_state = InvestigationState(
    plan=_Plan(goal="test", investigation_type="delay", expected_answer_type="duration")
)
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
# Simulate the reference having already been resolved in an earlier call.
repeat_state.mark_reference_followed("VPGC-NRB4-0012")

no_op_result = executor.expand(repeat_state)
check("a fully-followed state finds nothing new to attempt", no_op_result.references_attempted == [])
check("a fully-followed state adds zero new evidence", no_op_result.new_evidence_count == 0)
check("evidence count unchanged for a fully-followed state", len(repeat_state.evidence) == 1)
check("a search_history entry is still recorded for the no-op call (explainable)", len(repeat_state.search_history) == 1)
check("the no-op entry's query_text explains there was nothing unresolved", repeat_state.search_history[-1].query_text == "(no unresolved references)")

print()
print("=== Missing / unresolvable references terminate cleanly (no crash) ===")
# find_related_documents() empirically has no project boundary (see the
# corpus-scale finding above) and, on this corpus, no document's own
# referenced_ids are reliably isolated enough to guarantee a genuinely
# empty result -- so this test isolates the property directly: stub the
# reused tool's return value at the call site (not modifying tools.py
# itself, just substituting what this one test run calls) to confirm the
# executor itself handles "nothing was found" cleanly, independent of
# whatever find_related_documents() happens to return for real input.
import app.agent.reference_expansion_executor as _executor_module  # noqa: E402

missing_state = InvestigationState(
    plan=_Plan(goal="test", investigation_type="delay", expected_answer_type="duration")
)
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

check("expand() does not raise when the expansion tool finds nothing", True)  # reaching here means no exception
check("the reference was attempted", "NOPE-DOES-NOT-EXIST-0001" in missing_result.references_attempted)
check("no documents were added", missing_result.documents_added == [])
check("no new evidence was added", missing_result.new_evidence_count == 0)
check(
    "the reference is still marked followed despite not resolving",
    "NOPE-DOES-NOT-EXIST-0001" in missing_state.followed_reference_ids,
)
check("a search_history entry was still recorded", len(missing_state.search_history) == 1)
check("the recorded entry reflects zero new evidence", missing_state.search_history[-1].new_evidence_count == 0)

print()
print("=" * 60)
if FAILURES:
    print(f"VALIDATION FAILED ({len(FAILURES)} check(s)):")
    for f in FAILURES:
        print(" -", f)
    sys.exit(1)
else:
    print("VALIDATION PASSED (all checks)")
