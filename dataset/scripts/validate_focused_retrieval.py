"""Validation for Phase 3 Task 04's FocusedRetrievalExecutor. Runs against
the real, already-ingested Dataset V2 corpus (project_id=2) -- real
embeddings, real retrieval, zero Gemini calls. Uses InvestigationAgent
(Task 02) to produce a realistic starting InvestigationState, and calls
EvidenceSufficiencyAssessor's own stage-3 method directly
(_check_coverage_and_confidence) to obtain a genuine, non-fabricated
FOCUSED_RETRIEVAL SufficiencyDecision from real evidence -- the same
technique validate_reference_expansion.py used for stage 1, applied here to
stage 3. A small top_k on the initial pass is used deliberately, so stage 3
actually fires on real data instead of always finding coverage/confidence
already sufficient. The executor itself is exercised directly.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "backend"))

from app.agent.evidence_sufficiency import EvidenceSufficiencyAssessor
from app.agent.focused_retrieval_config import FocusedRetrievalConfig
from app.agent.focused_retrieval_executor import FocusedRetrievalExecutor, _build_focused_query
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
executor = FocusedRetrievalExecutor()
PROJECT_ID = 2

print("=== Setup: real investigation state with a genuine stage-3 (coverage/confidence) gap ===")
req = InvestigationRequest(
    project_id=PROJECT_ID,
    query="What did Vantara Power Grid Corporation say about the tower relocation timeline for Pier P3?",
    top_k=1,
)
run_result = agent.run(req)
state = run_result.state
decision = assessor._check_coverage_and_confidence(state)

check("a real top_k=1 pass produces a genuine FOCUSED_RETRIEVAL decision", decision is not None)
check("decision names the real uncovered entity 'Pier P3'", decision.details.get("uncovered_entities") == ["Pier P3"])

evidence_count_before = len(state.evidence)
visited_chunks_before = set(state.visited_chunk_ids)
visited_documents_before = set(state.visited_document_ids)
history_len_before = len(state.search_history)
iteration_before = state.iteration_count

print()
print("=== Deterministic query construction (no Gemini, no LLM) ===")
query = _build_focused_query(state, decision)
check("query includes the original user question", req.query in query)
check("query includes the uncovered entity 'Pier P3'", "Pier P3" in query)
check("query includes the investigation type", state.plan.investigation_type in query)
check("query includes the decision's own reason", decision.reason in query)
query_again = _build_focused_query(state, decision)
check("query construction is deterministic (identical state+decision -> identical query)", query == query_again)

print()
print("=== Focused retrieval discovers additional evidence (real retrieval pass) ===")
result = executor.retrieve(state, decision)
print(f"  query_used: {result.query_used}")
print(f"  citations_retrieved={result.citations_retrieved}, new_evidence_count={result.new_evidence_count}, "
      f"duplicates_ignored={result.duplicates_ignored}, termination_reason={result.termination_reason}")

check("at least one citation was retrieved", result.citations_retrieved > 0)
check("at least one new Evidence item was added", result.new_evidence_count > 0)
check("termination_reason is 'evidence_added' for a clean successful pass", result.termination_reason == "evidence_added")

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
check("visited_document_ids did not shrink", set(state.visited_document_ids) >= visited_documents_before)
check("iteration_count advanced by exactly 1", state.iteration_count == iteration_before + 1)
check(
    "newly added evidence uses real chunk ids (verifiable against the database)",
    all(item.citation.chunk_id is not None for item in state.evidence[evidence_count_before:]),
)

print()
print("=== Search history is complete ===")
check("exactly one new search_history entry was added", len(state.search_history) == history_len_before + 1)
entry = state.search_history[-1]
check("new entry has trigger_reason FOCUSED_RETRIEVAL", entry.trigger_reason == RemediationType.FOCUSED_RETRIEVAL)
check("new entry's query_text records the query actually used", entry.query_text.startswith(result.query_used))
check("new entry's results_returned matches citations_retrieved", entry.results_returned == result.citations_retrieved)
check("new entry's new_evidence_count matches what was actually added", entry.new_evidence_count == result.new_evidence_count)

print()
print("=== Duplicate evidence is rejected (same query, same state, called again) ===")
citations_before_repeat = result.citations_retrieved
repeat_result = executor.retrieve(state, decision)
print(f"  repeat call: citations_retrieved={repeat_result.citations_retrieved}, "
      f"duplicates_ignored={repeat_result.duplicates_ignored}, new_evidence_count={repeat_result.new_evidence_count}, "
      f"termination_reason={repeat_result.termination_reason}")
check(
    "the repeat call retrieves the same citations (deterministic retrieval)",
    repeat_result.citations_retrieved == citations_before_repeat,
)
check("the repeat call finds zero new evidence (all duplicates)", repeat_result.new_evidence_count == 0)
check(
    "the repeat call reports every citation as a duplicate",
    repeat_result.duplicates_ignored == repeat_result.citations_retrieved,
)
check("the repeat call's termination_reason is 'no_new_evidence'", repeat_result.termination_reason == "no_new_evidence")
check("evidence count is unchanged after the duplicate-only repeat call", len(state.evidence) == evidence_count_before + result.new_evidence_count)

print()
print("=== Retrieval budget is respected ===")
req_budget = InvestigationRequest(
    project_id=PROJECT_ID,
    query="What quality non-conformance issues were raised regarding the bridge deck concrete by Meridian Engineering Consultants?",
    top_k=1,
)
budget_run = agent.run(req_budget)
budget_state = budget_run.state
budget_decision = assessor._check_coverage_and_confidence(budget_state)
check("a second real scenario also produces a genuine FOCUSED_RETRIEVAL decision", budget_decision is not None)

tight_executor = FocusedRetrievalExecutor(config=FocusedRetrievalConfig(retrieval_top_k=10, max_new_evidence_added=1))
budget_result = tight_executor.retrieve(budget_state, budget_decision)
print(f"  tight budget (max_new_evidence_added=1): citations_retrieved={budget_result.citations_retrieved}, "
      f"new_evidence_count={budget_result.new_evidence_count}, new_evidence_deferred={budget_result.new_evidence_deferred}, "
      f"termination_reason={budget_result.termination_reason}")
check("new_evidence_count never exceeds the configured budget", budget_result.new_evidence_count <= 1)
if budget_result.new_evidence_deferred > 0:
    check("budget_exhausted is reported when more evidence existed than the cap allowed", budget_result.termination_reason == "budget_exhausted")

print()
print("=== Deterministic behaviour across repeated, independent runs ===")
req_det = InvestigationRequest(
    project_id=PROJECT_ID,
    query="Was the Contractor entitled to an extension of time for the Pier 3 utility conflict, and if so, for how long?",
    top_k=1,
)
run_a = agent.run(req_det)
run_b = agent.run(req_det)
decision_a = assessor._check_coverage_and_confidence(run_a.state)
decision_b = assessor._check_coverage_and_confidence(run_b.state)
check("two independent agent.run() calls for the same query produce the same stage-3 decision", decision_a is not None and decision_b is not None and decision_a.details == decision_b.details)

fresh_executor_a = FocusedRetrievalExecutor()
fresh_executor_b = FocusedRetrievalExecutor()
result_a = fresh_executor_a.retrieve(run_a.state, decision_a)
result_b = fresh_executor_b.retrieve(run_b.state, decision_b)
check("two independent retrieve() calls on equivalent fresh state produce the same query_used", result_a.query_used == result_b.query_used)
check(
    "two independent retrieve() calls on equivalent fresh state retrieve the same number of citations",
    result_a.citations_retrieved == result_b.citations_retrieved,
)
check(
    "two independent retrieve() calls on equivalent fresh state add the same amount of new evidence",
    result_a.new_evidence_count == result_b.new_evidence_count,
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
