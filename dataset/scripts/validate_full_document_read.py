"""Validation for Phase 3 Task 05's FullDocumentReadExecutor. Runs against
the real, already-ingested Dataset V2 corpus (project_id=2) -- real chunks,
real documents, zero Gemini calls. Uses InvestigationAgent (Task 02) to
produce a realistic starting InvestigationState, and calls
EvidenceSufficiencyAssessor's own stage-4 method directly
(_check_dominant_document) to obtain a genuine, non-fabricated
FULL_DOCUMENT_READ SufficiencyDecision from real evidence -- the same
technique Task 03/04's validation used for stages 1 and 3. The executor
itself is exercised directly.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "backend"))

from app.agent.evidence_sufficiency import EvidenceSufficiencyAssessor, SufficiencyDecision
from app.agent.full_document_read_config import FullDocumentReadConfig
from app.agent.full_document_read_executor import FullDocumentReadExecutor, _fetch_all_chunks
from app.agent.investigation_agent import InvestigationAgent
from app.agent.investigation_state import RemediationType
from app.agent.models import InvestigationRequest
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
assessor = EvidenceSufficiencyAssessor()
executor = FullDocumentReadExecutor()
PROJECT_ID = 2

print("=== Setup: real investigation state with a genuine stage-4 (dominant document) gap ===")
req = InvestigationRequest(
    project_id=PROJECT_ID,
    query="What was the outcome of the practical completion inspection?",
    top_k=2,
)
run_result = agent.run(req)
state = run_result.state
decision = assessor._check_dominant_document(state)

check("a real top_k=2 pass produces a genuine FULL_DOCUMENT_READ decision", decision is not None)
dominant_document_id = decision.details.get("document_id") if decision else None
print(f"  dominant_document_id={dominant_document_id}, reason={decision.reason if decision else None}")

evidence_count_before = len(state.evidence)
visited_chunks_before = set(state.visited_chunk_ids)
history_len_before = len(state.search_history)
iteration_before = state.iteration_count

# Ground truth: exactly how many chunks this document actually has, and how
# many of them the initial retrieval pass had already visited -- computed
# directly from the database, independent of the executor, so "evidence
# expands correctly" below is checked against a real, external number.
all_chunks = _fetch_all_chunks(dominant_document_id)
already_visited_chunk_ids = {c.id for c in all_chunks if c.id in visited_chunks_before}
expected_new_chunks = len(all_chunks) - len(already_visited_chunk_ids)
print(f"  document has {len(all_chunks)} total chunks; {len(already_visited_chunk_ids)} already visited; "
      f"{expected_new_chunks} expected new")

print()
print("=== Complete document retrieval works (real full read) ===")
result = executor.read(state, decision)
print(f"  documents_read={result.documents_read}, new_evidence_count={result.new_evidence_count}, "
      f"duplicates_ignored={result.duplicates_ignored}, termination_reason={result.termination_reason}")

check("the dominant document was read", result.documents_read == [dominant_document_id])
check("documents_requested reflects the decision", result.documents_requested == [dominant_document_id])
check("new_evidence_count matches the externally-computed expected count", result.new_evidence_count == expected_new_chunks)
check("duplicates_ignored matches the externally-computed already-visited count", result.duplicates_ignored == len(already_visited_chunk_ids))
check("termination_reason is 'evidence_added' for a clean successful read", result.termination_reason == "evidence_added")

print()
print("=== Before vs after evidence count ===")
print(f"  BEFORE: {evidence_count_before} evidence items")
print(f"  AFTER:  {len(state.evidence)} evidence items")
check("evidence count strictly increased", len(state.evidence) > evidence_count_before)
check(
    "evidence count increase matches the reported new_evidence_count",
    len(state.evidence) - evidence_count_before == result.new_evidence_count,
)

print()
print("=== InvestigationState updates correctly ===")
check("visited_chunk_ids grew", set(state.visited_chunk_ids) > visited_chunks_before)
check("the dominant document is now recorded as fully read", dominant_document_id in state.fully_read_document_ids)
check("the dominant document is also in visited_document_ids", dominant_document_id in state.visited_document_ids)
check("iteration_count advanced by exactly 1", state.iteration_count == iteration_before + 1)
check(
    "newly added evidence is tagged with its source",
    all(item.metadata.get("source") == "full_document_read" for item in state.evidence[evidence_count_before:]),
)
check(
    "newly added evidence uses real chunk ids from the dominant document",
    all(item.document_id == dominant_document_id for item in state.evidence[evidence_count_before:]),
)

print()
print("=== Search history is complete ===")
check("exactly one new search_history entry was added", len(state.search_history) == history_len_before + 1)
entry = state.search_history[-1]
check("new entry has trigger_reason FULL_DOCUMENT_READ", entry.trigger_reason == RemediationType.FULL_DOCUMENT_READ)
check("new entry's query_text names the document", str(dominant_document_id) in entry.query_text)
check("new entry's new_evidence_count matches what was actually added", entry.new_evidence_count == result.new_evidence_count)

print()
print("=== Duplicate rereads are prevented (same document, same state, read again) ===")
repeat_result = executor.read(state, decision)
print(f"  repeat call: documents_read={repeat_result.documents_read}, "
      f"already_fully_read={repeat_result.already_fully_read}, new_evidence_count={repeat_result.new_evidence_count}, "
      f"termination_reason={repeat_result.termination_reason}")
check("the repeat call does not reopen the document", repeat_result.documents_read == [])
check("the repeat call reports it as already fully read", repeat_result.already_fully_read == [dominant_document_id])
check("the repeat call adds zero new evidence", repeat_result.new_evidence_count == 0)
check("the repeat call's termination_reason is 'already_fully_read'", repeat_result.termination_reason == "already_fully_read")
check("evidence count is unchanged after the duplicate-reread attempt", len(state.evidence) == evidence_count_before + result.new_evidence_count)

print()
print("=== Budgets are respected (max_documents_per_call + max_new_evidence_added) ===")
req2 = InvestigationRequest(
    project_id=PROJECT_ID,
    query="What quality non-conformance issues were raised regarding the bridge deck concrete by Meridian Engineering Consultants?",
    top_k=2,
)
run2 = agent.run(req2)
decision2 = assessor._check_dominant_document(run2.state)
check("a second real scenario also produces a genuine FULL_DOCUMENT_READ decision", decision2 is not None)
second_document_id = decision2.details["document_id"]
check("the two real scenarios name different dominant documents", second_document_id != dominant_document_id)

# Multi-document request (deterministic, real document ids), constructed
# directly per _document_ids_from_decision()'s documented forward-compat
# contract (details['document_ids'], plural) -- exercises
# max_documents_per_call using two genuinely different real documents.
multi_decision = SufficiencyDecision(
    sufficient=False,
    remediation=RemediationType.FULL_DOCUMENT_READ,
    reason="test: two dominant documents",
    details={"document_ids": [dominant_document_id, second_document_id]},
)
one_doc_executor = FullDocumentReadExecutor(config=FullDocumentReadConfig(max_documents_per_call=1, max_new_evidence_added=100))
fresh_state = agent.run(req).state  # fresh state re-derived from the same original query
multi_result = one_doc_executor.read(fresh_state, multi_decision)
print(f"  max_documents_per_call=1: documents_read={multi_result.documents_read}, "
      f"documents_deferred={multi_result.documents_deferred}, termination_reason={multi_result.termination_reason}")
check("only one document is opened when max_documents_per_call=1", len(multi_result.documents_read) == 1)
check("the second document is reported as deferred, not silently dropped", multi_result.documents_deferred == [second_document_id])
check("a deferred document is NOT marked fully read", second_document_id not in fresh_state.fully_read_document_ids)
check("budget_exhausted is the termination reason when a document is deferred", multi_result.termination_reason == "budget_exhausted")

tight_evidence_executor = FullDocumentReadExecutor(config=FullDocumentReadConfig(max_documents_per_call=5, max_new_evidence_added=1))
fresh_state_2 = agent.run(req).state
tight_result = tight_evidence_executor.read(fresh_state_2, decision)
print(f"  max_new_evidence_added=1 (document has {expected_new_chunks} new chunks): "
      f"documents_read={tight_result.documents_read}, documents_deferred={tight_result.documents_deferred}, "
      f"new_evidence_deferred={tight_result.new_evidence_deferred}, termination_reason={tight_result.termination_reason}")
if expected_new_chunks > 1:
    check("a document whose full chunk set exceeds the evidence budget is deferred whole, not partially added", tight_result.documents_read == [])
    check("the whole document's candidate evidence is reported as deferred", tight_result.new_evidence_deferred == expected_new_chunks)
    check("a budget-deferred document is not marked fully read", dominant_document_id not in fresh_state_2.fully_read_document_ids)
    check("new_evidence_count is 0 when the only candidate document is deferred whole", tight_result.new_evidence_count == 0)

print()
print("=== Deterministic behaviour across repeated, independent runs ===")
run_a = agent.run(req)
run_b = agent.run(req)
decision_a = assessor._check_dominant_document(run_a.state)
decision_b = assessor._check_dominant_document(run_b.state)
check(
    "two independent agent.run() calls for the same query produce the same stage-4 decision",
    decision_a is not None and decision_b is not None and decision_a.details == decision_b.details,
)
result_a = FullDocumentReadExecutor().read(run_a.state, decision_a)
result_b = FullDocumentReadExecutor().read(run_b.state, decision_b)
check("two independent read() calls on equivalent fresh state read the same document(s)", result_a.documents_read == result_b.documents_read)
check(
    "two independent read() calls on equivalent fresh state add the same amount of new evidence",
    result_a.new_evidence_count == result_b.new_evidence_count,
)
check(
    "two independent read() calls on equivalent fresh state agree on duplicates_ignored",
    result_a.duplicates_ignored == result_b.duplicates_ignored,
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
