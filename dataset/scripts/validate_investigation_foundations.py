"""Standalone validation for Phase 3 Task 01's two new foundation modules
(InvestigationState, EvidenceSufficiencyAssessor). Not part of the backend;
run manually, imports only from the backend package. Constructs fixtures by
hand (no DB, no retrieval, no LLM) -- exactly the "independently testable"
property the task required.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "backend"))

from app.agent.evidence_sufficiency import EvidenceSufficiencyAssessor
from app.agent.investigation_state import InvestigationState, RemediationType
from app.agent.models import Citation, Evidence
from app.contracts.models import ClauseTopic, ContractClause
from app.domain.document_types import DocumentType
from app.investigation.models import InvestigationPlan

FAILURES = []


def check(label: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {label}" + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def make_evidence(document_id: int, chunk_id: int, excerpt: str, confidence: float = 0.8) -> Evidence:
    return Evidence(
        citation=Citation(document_id=document_id, chunk_id=chunk_id, page=1, relevance_score=confidence, chunk_text=excerpt),
        document_id=document_id,
        document_name=f"DOC-{document_id}.pdf",
        excerpt=excerpt,
        surrounding_context=excerpt,
        confidence=confidence,
    )


def make_plan(entities: list[str]) -> InvestigationPlan:
    return InvestigationPlan(
        goal="test goal",
        investigation_type="delay",
        expected_answer_type="duration",
        primary_entities=entities,
        likely_evidence_sources=[DocumentType.APPROVAL],
    )


# ---------------------------------------------------------------------------
print("=== InvestigationState: initialization ===")
plan = make_plan(["Contractor", "Pier P3"])
state = InvestigationState(plan=plan)

check("initializes with empty evidence", state.evidence == [])
check("initializes with empty visited_chunk_ids", state.visited_chunk_ids == set())
check("initializes with empty visited_document_ids", state.visited_document_ids == set())
check("initializes with empty fully_read_document_ids", state.fully_read_document_ids == set())
check("initializes with empty followed_reference_ids", state.followed_reference_ids == set())
check("initializes with empty retrieved_clauses", state.retrieved_clauses == [])
check("initializes with empty retrieved_clause_numbers", state.retrieved_clause_numbers == set())
check("initializes with empty timeline_context", state.timeline_context == "")
check("initializes with empty search_history", state.search_history == [])
check("initializes with iteration_count == 0", state.iteration_count == 0)
check("initializes with stopping_reason is None", state.stopping_reason is None)
check("plan is preserved", state.plan is plan)

# Two independently-constructed states must not share mutable defaults.
state_a = InvestigationState(plan=plan)
state_b = InvestigationState(plan=plan)
state_a.visited_chunk_ids.add(999)
check("mutable defaults are not shared across instances", 999 not in state_b.visited_chunk_ids)

print()
print("=== InvestigationState: updates and duplicate tracking ===")
e1 = make_evidence(document_id=101, chunk_id=1, excerpt="First excerpt about the Contractor.")
e2 = make_evidence(document_id=101, chunk_id=2, excerpt="Second excerpt, same document.")
e1_dup = make_evidence(document_id=101, chunk_id=1, excerpt="Duplicate of the first chunk.")

added = state.add_evidence([e1, e2])
check("add_evidence returns count of newly added items", added == 2, f"got {added}")
check("evidence list grows", len(state.evidence) == 2)
check("visited_chunk_ids updated", state.visited_chunk_ids == {1, 2})
check("visited_document_ids updated", state.visited_document_ids == {101})

added_again = state.add_evidence([e1_dup, e2])
check("duplicate chunk_id is not re-added", added_again == 0, f"got {added_again}")
check("evidence list unchanged after duplicate add", len(state.evidence) == 2)

added_within_batch = InvestigationState(plan=plan).add_evidence([e1, e1_dup])
check("duplicates within a single batch are also collapsed", added_within_batch == 1, f"got {added_within_batch}")

state.mark_document_fully_read(101)
check("fully_read_document_ids updated", 101 in state.fully_read_document_ids)
check("marking fully read also visits the document", 101 in state.visited_document_ids)

state.mark_reference_followed("VPGC-NRB4-0012")
state.mark_reference_followed("VPGC-NRB4-0012")  # idempotent
check("followed_reference_ids records a reference", "VPGC-NRB4-0012" in state.followed_reference_ids)
check("marking the same reference twice does not duplicate (it's a set)", len(state.followed_reference_ids) == 1)

clause_84 = ContractClause(clause_number="8.4", title="Extension of Time", topic=ClauseTopic.DELAY, text="...")
clause_84_dup = ContractClause(clause_number="8.4", title="Extension of Time", topic=ClauseTopic.DELAY, text="...")
clause_201 = ContractClause(clause_number="20.1", title="Contractor's Claims", topic=ClauseTopic.CLAIMS, text="...")

added_clauses = state.add_clauses([clause_84, clause_84_dup, clause_201])
check("add_clauses dedups by clause_number", added_clauses == 2, f"got {added_clauses}")
check("retrieved_clauses has 2 entries", len(state.retrieved_clauses) == 2)
check("retrieved_clause_numbers has 2 entries", state.retrieved_clause_numbers == {"8.4", "20.1"})

state.update_timeline_context("2021-01-28 -- Discovery")
check("timeline_context updates", state.timeline_context == "2021-01-28 -- Discovery")
state.update_timeline_context("2021-01-28 -- Discovery\n2021-02-10 -- Notice")
check("timeline_context replaces, does not append", "2021-02-10" in state.timeline_context and state.timeline_context.count("2021-01-28") == 1)

n_before = state.iteration_count
returned = state.advance_iteration()
check("advance_iteration increments counter", state.iteration_count == n_before + 1)
check("advance_iteration returns the new count", returned == state.iteration_count)

state.record_search(RemediationType.FOCUSED_RETRIEVAL, results_returned=5, new_evidence_count=3, query_text="Pier P3 utility")
check("record_search appends to search_history", len(state.search_history) == 1)
entry = state.search_history[0]
check("search history entry has correct iteration", entry.iteration == state.iteration_count)
check("search history entry has correct trigger_reason", entry.trigger_reason == RemediationType.FOCUSED_RETRIEVAL)
check("search history entry has correct query_text", entry.query_text == "Pier P3 utility")

check("stopping_reason starts unset", InvestigationState(plan=plan).stopping_reason is None)
state.stop("sufficient")
check("stop() records the reason", state.stopping_reason == "sufficient")

print()
print("=== EvidenceSufficiencyAssessor: four remediation types + stop ===")
assessor = EvidenceSufficiencyAssessor()

# --- Stage 1: unresolved document reference ---
s1 = InvestigationState(plan=make_plan(["Contractor"]))
s1.add_evidence([
    make_evidence(1, 1, "We refer to your Notice CTR-NRB4-0021 dated 10-Feb-2021 and the Engineer's "
                         "determination in ENG-NRB4-0019, which references VPGC-NRB4-0012 for the "
                         "relocation timeline.", confidence=0.9),
])
d1 = assessor.assess(s1)
check("stage 1 fires on unresolved references", not d1.sufficient and d1.remediation == RemediationType.REFERENCE_EXPANSION)
check("stage 1 details lists the unresolved references", "unresolved_references" in d1.details and len(d1.details["unresolved_references"]) > 0)

# same evidence, but references already followed -> stage 1 must not re-fire
s1b = InvestigationState(plan=make_plan(["Contractor"]))
s1b.add_evidence(s1.evidence)
for ref in d1.details["unresolved_references"]:
    s1b.mark_reference_followed(ref)
d1b = assessor.assess(s1b)
check("stage 1 does not re-fire once references are marked followed", d1b.remediation != RemediationType.REFERENCE_EXPANSION)

# --- Stage 2: named clause not retrieved ---
s2 = InvestigationState(plan=make_plan(["Contractor", "Engineer"]))
s2.add_evidence([
    make_evidence(2, 10, "Pursuant to Sub-Clause 20.1 the Contractor gave notice, and the Engineer's "
                          "determination under Sub-Clause 8.4 granted an extension.", confidence=0.9),
    make_evidence(2, 11, "The Contractor and the Engineer agreed the position.", confidence=0.9),
])
d2 = assessor.assess(s2)
check("stage 2 fires on clauses named but not retrieved", not d2.sufficient and d2.remediation == RemediationType.CLAUSE_TOP_UP)
check("stage 2 details lists both missing clause numbers", set(d2.details["missing_clause_numbers"]) == {"20.1", "8.4"})

s2b = InvestigationState(plan=s2.plan)
s2b.add_evidence(s2.evidence)
s2b.add_clauses([
    ContractClause(clause_number="20.1", title="Contractor's Claims", topic=ClauseTopic.CLAIMS, text="..."),
    ContractClause(clause_number="8.4", title="Extension of Time", topic=ClauseTopic.DELAY, text="..."),
])
d2b = assessor.assess(s2b)
check("stage 2 does not fire once the named clauses are retrieved", d2b.remediation != RemediationType.CLAUSE_TOP_UP)

# --- Stage 3: low entity coverage / confidence ---
s3 = InvestigationState(plan=make_plan(["Contractor", "Vantara Power Grid Corporation"]))
s3.add_evidence([make_evidence(3, 20, "A short excerpt mentioning the Contractor only.", confidence=0.5)])
d3 = assessor.assess(s3)
check(
    "stage 3 fires on low entity coverage / low confidence",
    not d3.sufficient and d3.remediation == RemediationType.FOCUSED_RETRIEVAL,
)
check(
    "stage 3 details identify the uncovered entity",
    "Vantara Power Grid Corporation" in d3.details.get("uncovered_entities", []),
)

# --- Stage 4: dominant document, no determination content ---
s4 = InvestigationState(plan=make_plan([]))
s4.add_evidence([
    make_evidence(4, 30, "The Contractor notified the Engineer of the utility conflict at Pier P3.", confidence=0.9),
    make_evidence(4, 31, "The Engineer acknowledged receipt of the notice without further comment.", confidence=0.9),
])
d4 = assessor.assess(s4)
check(
    "stage 4 fires when one document dominates with no determination content",
    not d4.sufficient and d4.remediation == RemediationType.FULL_DOCUMENT_READ,
)
check("stage 4 details identify the dominant document", d4.details.get("document_id") == 4)

# same shape, but the dominant document has already been fully read -> must not re-fire
s4b = InvestigationState(plan=make_plan([]))
s4b.add_evidence(s4.evidence)
s4b.mark_document_fully_read(4)
d4b = assessor.assess(s4b)
check("stage 4 does not recommend re-reading an already fully-read document", d4b.remediation != RemediationType.FULL_DOCUMENT_READ)

# same shape, but with determination content present -> must not fire
s4c = InvestigationState(plan=make_plan([]))
s4c.add_evidence([
    make_evidence(4, 30, "The Contractor notified the Engineer of the utility conflict at Pier P3.", confidence=0.9),
    make_evidence(4, 31, "The Engineer determined that an extension of 10 weeks is granted.", confidence=0.9),
])
d4c = assessor.assess(s4c)
check("stage 4 does not fire once determination content is present", d4c.remediation != RemediationType.FULL_DOCUMENT_READ)

# --- Sufficient case: everything satisfied (including a digit alongside
# the determination word, so stage 4's coarse heuristic is genuinely met) ---
s5_evidence = [
    make_evidence(5, 40, "The Contractor's position was confirmed, no outstanding matters remain.", confidence=0.9),
    make_evidence(5, 41, "The Engineer determined that the matter was resolved within 10 days.", confidence=0.9),
]
s5 = InvestigationState(plan=make_plan(["Contractor"]))
s5.add_evidence(s5_evidence)
d5 = assessor.assess(s5)
check("sufficient state returns sufficient=True", d5.sufficient is True)
check("sufficient state returns remediation=None", d5.remediation is None)
check("assess() does not mutate state", s5.evidence == s5_evidence)

# --- Priority ordering: when multiple stages could fire, stage 1 wins ---
s6 = InvestigationState(plan=make_plan(["Vantara Power Grid Corporation"]))  # would also fail stage 3
s6.add_evidence([
    make_evidence(6, 50, "See VPGC-NRB4-0012 for details, referenced under Sub-Clause 8.4.", confidence=0.9),
])
d6 = assessor.assess(s6)
check("stage 1 (references) takes priority over stage 2/3 when multiple would fire", d6.remediation == RemediationType.REFERENCE_EXPANSION)

print()
print("=" * 60)
if FAILURES:
    print(f"VALIDATION FAILED ({len(FAILURES)} check(s)):")
    for f in FAILURES:
        print(" -", f)
    sys.exit(1)
else:
    print("VALIDATION PASSED (all checks)")
