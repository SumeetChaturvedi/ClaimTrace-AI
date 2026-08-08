"""InvestigationLoop — the deterministic Investigation Loop from the
approved Investigation Agent architecture (Phase 3 Task 06). Orchestrates
the six already-built, already-validated components (InvestigationAgent,
EvidenceSufficiencyAssessor, InvestigationState, and the three remediation
executors) exactly as implemented -- this module contains no retrieval,
scoring, evidence-building, timeline, contract, or reasoning logic of its
own, only the control flow that decides which existing piece to call next
and when to stop. Not integrated into InvestigationService or any API
route -- nothing calls this module outside itself and its own validation
script, and it never calls Gemini (ReasoningEngine.reason() is never
invoked here; Gemini only ever runs after an investigation the loop
produced is handed to something else, which this task does not do).

Workflow (exactly as specified):

    1. InvestigationAgent.run()            -- one InvestigationState,
                                               one initial retrieval pass,
                                               one SufficiencyDecision
    2. (assess -- already done by run())
    3. if decision.sufficient: STOP
    4. else: execute exactly ONE remediation, chosen by decision.remediation
    5. (state updated -- the executor itself does this)
    6. EvidenceSufficiencyAssessor.assess(state) again
    7. repeat from 3

Remediation dispatch (Task 06's SUPPORTED REMEDIATIONS section):

    REFERENCE_EXPANSION   -> ReferenceExpansionExecutor.expand(state)
    FOCUSED_RETRIEVAL     -> FocusedRetrievalExecutor.retrieve(state, decision)
    FULL_DOCUMENT_READ    -> FullDocumentReadExecutor.read(state, decision)

CLAUSE_TOP_UP has no executor (Task 06 explicitly forbids building one
"unless the loop proves it is genuinely required" -- see
investigation_loop's own validation and the final report for whether real
Dataset V2 data ever makes that necessary). Any remediation with no
registered executor -- CLAUSE_TOP_UP today, or a hypothetical future
enum value -- is handled identically: the loop stops safely with
stopping_reason="unsupported_remediation" rather than crashing or guessing.

Executor result normalization: ReferenceExpansionResult (Task 03) predates
the termination_reason convention Task 04/05 established on
FocusedRetrievalResult/FullDocumentReadResult, so it has no such field.
_run_reference_expansion() below derives an equivalent signal from its
existing references_deferred/documents_deferred fields, purely by reading
them -- reference_expansion_executor.py itself is not modified, per this
task's "reuse exactly as implemented" requirement.

Search history: every remediation call already appends its own complete
SearchHistoryEntry (each executor does this internally, unchanged) --
the loop does not add a second, redundant entry for a step an executor
already recorded. The loop adds its own entry only for the two stopping
paths where no executor ever got to run: 'unsupported_remediation' and
'executor_failure' (see run() below), so the explainability trail has no
gap for what was attempted immediately before the loop stopped.
"""

from typing import Callable

from pydantic import BaseModel, Field

from app.agent.evidence_sufficiency import EvidenceSufficiencyAssessor, SufficiencyDecision
from app.agent.focused_retrieval_executor import FocusedRetrievalExecutor
from app.agent.full_document_read_executor import FullDocumentReadExecutor
from app.agent.investigation_agent import InvestigationAgent
from app.agent.investigation_loop_config import DEFAULT_INVESTIGATION_LOOP_CONFIG, InvestigationLoopConfig
from app.agent.investigation_state import InvestigationState, RemediationType
from app.agent.models import InvestigationRequest
from app.agent.reference_expansion_executor import ReferenceExpansionExecutor

# Remediation types for which no executor exists. CLAUSE_TOP_UP is the only
# member of RemediationType with no registered dispatch entry today (see
# InvestigationLoop._executors, built in __init__) -- listed here only for
# documentation; the actual "unsupported" determination is a plain
# dict-membership check against _executors, not a second source of truth.
_UNSUPPORTED_REMEDIATIONS = (RemediationType.CLAUSE_TOP_UP,)


class LoopRunResult(BaseModel):
    """The result of one InvestigationLoop.run() call: the final
    accumulated state, the final SufficiencyDecision (sufficient=True, or
    the decision that could not be acted on further), and why the loop
    stopped. Carries no behavior."""

    state: InvestigationState
    decision: SufficiencyDecision
    stopping_reason: str = Field(
        description=(
            "One of: 'sufficient', 'max_iterations_reached', 'no_progress', "
            "'same_remediation_no_progress', 'budget_exhausted', "
            "'unsupported_remediation', 'executor_failure'"
        )
    )
    iterations_executed: int = Field(description="state.iteration_count at the moment the loop stopped")


class InvestigationLoop:
    """Repeatedly assesses an InvestigationState and executes exactly one
    remediation per iteration, until EvidenceSufficiencyAssessor reports
    sufficiency, the configured iteration budget is exhausted, or no
    remediation can make further progress. Holds instances of the six
    reused components purely as a source of already-correct behaviour --
    never reimplements any of it."""

    def __init__(
        self,
        agent: InvestigationAgent | None = None,
        assessor: EvidenceSufficiencyAssessor | None = None,
        reference_expansion_executor: ReferenceExpansionExecutor | None = None,
        focused_retrieval_executor: FocusedRetrievalExecutor | None = None,
        full_document_read_executor: FullDocumentReadExecutor | None = None,
        config: InvestigationLoopConfig | None = None,
    ) -> None:
        self._agent = agent or InvestigationAgent()
        self._assessor = assessor or EvidenceSufficiencyAssessor()
        self._reference_expansion_executor = reference_expansion_executor or ReferenceExpansionExecutor()
        self._focused_retrieval_executor = focused_retrieval_executor or FocusedRetrievalExecutor()
        self._full_document_read_executor = full_document_read_executor or FullDocumentReadExecutor()
        self._config = config or DEFAULT_INVESTIGATION_LOOP_CONFIG

        # RemediationType -> (state, decision) -> (new_evidence_count, termination_reason | None).
        # Built once per instance so each dispatch entry is a bound method
        # closing over this instance's own executor instances.
        self._executors: dict[
            RemediationType, Callable[[InvestigationState, SufficiencyDecision], tuple[int, str | None]]
        ] = {
            RemediationType.REFERENCE_EXPANSION: self._run_reference_expansion,
            RemediationType.FOCUSED_RETRIEVAL: self._run_focused_retrieval,
            RemediationType.FULL_DOCUMENT_READ: self._run_full_document_read,
        }

    def run(self, request: InvestigationRequest) -> LoopRunResult:
        """Execute the full deterministic loop for one investigation
        request: one initial InvestigationAgent pass, then repeated
        assess-and-remediate iterations until a stopping condition fires.
        Never calls Gemini/ReasoningEngine."""
        run_result = self._agent.run(request)
        state = run_result.state
        decision = run_result.decision

        previous_remediation: RemediationType | None = None

        while True:
            if decision.sufficient:
                state.stop("sufficient")
                return self._finish(state, decision, "sufficient")

            if state.iteration_count >= self._config.max_iterations:
                state.stop("max_iterations_reached")
                return self._finish(state, decision, "max_iterations_reached")

            remediation = decision.remediation
            executor_call = self._executors.get(remediation)

            if executor_call is None:
                state.advance_iteration()
                state.record_search(
                    remediation,
                    results_returned=0,
                    new_evidence_count=0,
                    query_text=f"No executor is registered for remediation '{remediation}'; loop terminated.",
                )
                state.stop("unsupported_remediation")
                return self._finish(state, decision, "unsupported_remediation")

            try:
                new_evidence_count, termination_reason = executor_call(state, decision)
            except Exception as exc:  # noqa: BLE001 -- deliberately broad: any executor failure must stop safely
                state.advance_iteration()
                state.record_search(
                    remediation,
                    results_returned=0,
                    new_evidence_count=0,
                    query_text=f"Executor for '{remediation}' raised {exc.__class__.__name__}: {exc}",
                )
                state.stop("executor_failure")
                return self._finish(state, decision, "executor_failure")

            if new_evidence_count == 0:
                if termination_reason == "budget_exhausted":
                    stopping_reason = "budget_exhausted"
                elif remediation == previous_remediation:
                    stopping_reason = "same_remediation_no_progress"
                else:
                    stopping_reason = "no_progress"
                state.stop(stopping_reason)
                return self._finish(state, decision, stopping_reason)

            previous_remediation = remediation
            decision = self._assessor.assess(state)

    @staticmethod
    def _finish(state: InvestigationState, decision: SufficiencyDecision, stopping_reason: str) -> LoopRunResult:
        return LoopRunResult(
            state=state,
            decision=decision,
            stopping_reason=stopping_reason,
            iterations_executed=state.iteration_count,
        )

    # -- Per-remediation dispatch, normalizing each executor's own result
    # shape down to (new_evidence_count, termination_reason | None) --------

    def _run_reference_expansion(
        self, state: InvestigationState, decision: SufficiencyDecision
    ) -> tuple[int, str | None]:
        result = self._reference_expansion_executor.expand(state)
        # ReferenceExpansionResult predates the termination_reason
        # convention (Task 03) -- derived here, from its existing public
        # fields only, not added to the executor itself.
        termination_reason = "budget_exhausted" if (result.references_deferred or result.documents_deferred) else None
        return result.new_evidence_count, termination_reason

    def _run_focused_retrieval(
        self, state: InvestigationState, decision: SufficiencyDecision
    ) -> tuple[int, str | None]:
        result = self._focused_retrieval_executor.retrieve(state, decision)
        return result.new_evidence_count, result.termination_reason

    def _run_full_document_read(
        self, state: InvestigationState, decision: SufficiencyDecision
    ) -> tuple[int, str | None]:
        result = self._full_document_read_executor.read(state, decision)
        return result.new_evidence_count, result.termination_reason
