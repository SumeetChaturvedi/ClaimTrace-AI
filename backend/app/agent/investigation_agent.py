"""InvestigationAgent — the orchestration skeleton from the approved
Investigation Agent architecture (Phase 3 Task 02). Runs exactly one
retrieval pass, populates an InvestigationState (Task 01) from it, and asks
EvidenceSufficiencyAssessor (Task 01) whether that's enough. It does not
loop, does not perform any remediation, and is not called from anywhere in
production — nothing imports this module outside itself and its own
validation script.

This module intentionally contains no retrieval, timeline, contract, or
Gemini logic of its own. Every piece of real work is delegated to an
existing, unmodified component:

    - InvestigationPlanner.create_plan()         (app/investigation/service.py)
    - tools.search_documents()                    (app/agent/tools.py)
    - ContractContextBuilder.build() +
      ClauseRetriever.retrieve()                  (app/contracts/)
    - TimelineBuilder / TimelineFormatter,
      via InvestigationService._build_timeline_context()

Evidence assembly (turning Citations into Evidence: filename lookup,
excerpt/surrounding_context, confidence clamping) and timeline-context
assembly already exist only as InvestigationService's own methods
(_build_evidence, _build_timeline_context). Reusing them directly --
rather than writing a second implementation of the same logic here, which
"no duplicate logic" rules out, or editing InvestigationService to expose
them differently, which this task rules out -- means InvestigationAgent
holds an InvestigationService instance purely as a source of already-built
logic to call. This is the same pattern already used by
dataset/scripts/run_benchmarks.py (Sprint 7) to introspect the same
pipeline without going through InvestigationResponse. Constructing an
InvestigationService (and, transitively, a ReasoningEngine/GeminiProvider)
does not itself make a Gemini call -- nothing in this module ever calls
reason()/generate() -- so "no Gemini calls" holds even though a
GeminiProvider object exists in memory once this agent is constructed.

The dependency direction matters: InvestigationAgent depends on
InvestigationService's existing methods; InvestigationService does not
depend on, import, or know about InvestigationAgent. Nothing here changes
InvestigationService's behaviour for its existing callers.
"""

from pydantic import BaseModel

from app.agent import tools
from app.agent.evidence_sufficiency import EvidenceSufficiencyAssessor, SufficiencyDecision
from app.agent.investigation_state import InvestigationState, RemediationType
from app.agent.models import InvestigationRequest
from app.agent.service import InvestigationService


class AgentRunResult(BaseModel):
    """The result of one InvestigationAgent.run() call: the accumulated
    state and the assessor's decision about it. Carries no behaviour. Both
    fields are themselves Pydantic models, so this nests natively with no
    special configuration."""

    state: InvestigationState
    decision: SufficiencyDecision


class InvestigationAgent:
    """Orchestrates existing components through one retrieval pass and one
    sufficiency assessment. Does not loop and does not remediate -- see the
    module docstring and the approved architecture spec (Phase 3 Task 01
    conversation) for what a future task would add here.

    Holds an InvestigationService purely as a source of reusable,
    already-correct sub-component calls (planner, contract context/clause
    retrieval, evidence assembly, timeline assembly) -- never calls its
    reasoning-related methods, and never calls investigate() itself, which
    would run the full existing single-pass pipeline instead of this one."""

    def __init__(
        self,
        service: InvestigationService | None = None,
        assessor: EvidenceSufficiencyAssessor | None = None,
    ) -> None:
        self._service = service or InvestigationService()
        self._assessor = assessor or EvidenceSufficiencyAssessor()

    def run(self, request: InvestigationRequest) -> AgentRunResult:
        """Execute the orchestration skeleton described in the approved
        architecture's Task 02 scope:

        1. Create a new InvestigationState from a freshly-planned
           InvestigationPlan.
        2. Execute exactly one retrieval pass via the existing retrieval
           service (tools.search_documents()).
        3. Populate the state with evidence, retrieved clauses, timeline
           context, and one search_history entry.
        4. Invoke EvidenceSufficiencyAssessor.
        5. Return the resulting state and decision -- no remediation is
           performed even if the decision says more evidence is needed."""
        plan = self._service._planner.create_plan(request.query)
        state = InvestigationState(plan=plan)

        contract_context = self._service._contract_context_builder.build(plan)
        initial_clauses = self._service._clause_retriever.retrieve(contract_context)
        state.add_clauses(initial_clauses)

        citations = tools.search_documents(
            project_id=request.project_id,
            query=request.query,
            top_k=request.top_k,
            investigation_plan=plan,
        )
        evidence = self._service._build_evidence(citations)
        new_evidence_count = state.add_evidence(evidence)

        timeline_context = self._service._build_timeline_context(citations)
        state.update_timeline_context(timeline_context)

        state.advance_iteration()
        state.record_search(
            RemediationType.INITIAL_RETRIEVAL,
            results_returned=len(citations),
            new_evidence_count=new_evidence_count,
            query_text=request.query,
        )

        decision = self._assessor.assess(state)
        if decision.sufficient:
            state.stop("sufficient")
        # If not sufficient, `state.stopping_reason` is deliberately left
        # unset: no stopping decision has actually been made yet, since
        # nothing has attempted remediation. Recording a reason here would
        # misrepresent an unfinished investigation as a concluded one.

        return AgentRunResult(state=state, decision=decision)
