"""FocusedRetrievalExecutor — the Focused Retrieval remediation from the
approved Investigation Agent architecture (Phase 3 Task 04). Given an
InvestigationState and the SufficiencyDecision that flagged it as
needing more evidence (typically EvidenceSufficiencyAssessor's stage 3:
low entity coverage / not enough confident evidence), performs exactly one
additional, deterministically-constructed retrieval pass and folds any
genuinely new evidence back into that same state. Not the investigation
loop (which would decide WHEN to call this and what to do with the result),
not Full Document Read, not Clause Top-up, and not integrated into
InvestigationService or InvestigationAgent -- nothing calls this module
outside itself and its own validation script.

Reuses, rather than reimplements, every piece of real work:

    - Retrieval itself: tools.search_documents() (app/agent/tools.py),
      exactly the same call InvestigationAgent's initial pass uses --
      same embeddings, same RetrievalScorer, same project scoping. No new
      retrieval algorithm, no scoring change, no embedding change.
    - Building Evidence from citations: InvestigationService's existing
      _build_evidence() (app/agent/service.py) -- the same method
      InvestigationAgent's initial pass and InvestigationService's own
      investigate() both already use. Not a second implementation.
    - Deduplication: InvestigationState.add_evidence() (Task 01), which
      already refuses a chunk_id it has seen before. This executor also
      pre-filters already-visited chunks before calling _build_evidence(),
      purely to keep duplicates_ignored explainable in the result and
      search history -- add_evidence()'s own dedup remains the actual
      source of truth, not a second one.

Query construction (the one genuinely new piece of logic this module
introduces) is plain, deterministic string assembly from data the
investigation already has -- the original user question (recovered from
state's own first search_history entry, since neither InvestigationState
nor InvestigationPlan stores the raw request text separately), the plan's
investigation_type and primary_entities, the decision's uncovered_entities
(when the triggering decision is a coverage gap), and the decision's own
human-readable reason. No Gemini call, no LLM-generated query, anywhere in
this module.
"""

from pydantic import BaseModel, Field
from sqlalchemy import select

from app.agent import tools
from app.agent.evidence_sufficiency import SufficiencyDecision
from app.agent.focused_retrieval_config import DEFAULT_FOCUSED_RETRIEVAL_CONFIG, FocusedRetrievalConfig
from app.agent.investigation_state import InvestigationState, RemediationType
from app.agent.service import InvestigationService
from app.db.models import Document
from app.db.session import get_session_factory


def _infer_project_id(state: InvestigationState) -> int | None:
    """Best-effort project scope for this retrieval, derived from the
    documents already visited in `state` -- not a new field on
    InvestigationState, which this task does not modify. Mirrors
    reference_expansion_executor._infer_project_id() exactly; duplicated
    rather than imported across the two remediation executors so each
    remains independently readable and the architecture's remediation
    strategies stay isolated from one another, per this task's own
    isolation requirement. Returns None -- tools.search_documents() would
    then search unscoped -- only if `state` has no visited documents yet or
    they unexpectedly span more than one project (defensive; should not
    happen given upstream project-scoped retrieval)."""
    if not state.visited_document_ids:
        return None
    with get_session_factory()() as session:
        project_ids = set(
            session.scalars(
                select(Document.project_id).where(Document.id.in_(state.visited_document_ids)).distinct()
            ).all()
        )
    return project_ids.pop() if len(project_ids) == 1 else None


def _original_question(state: InvestigationState) -> str:
    """The raw user question that started this investigation. Neither
    InvestigationState nor InvestigationPlan stores this verbatim, but
    InvestigationAgent.run() always records it as the first search_history
    entry's query_text (RemediationType.INITIAL_RETRIEVAL) -- reused here
    rather than added as a new field. Falls back to the plan's own goal
    (still real, plan-derived text, never invented) for a state built
    without that convention, e.g. a hand-built test fixture."""
    if state.search_history and state.search_history[0].trigger_reason == RemediationType.INITIAL_RETRIEVAL:
        first_query = state.search_history[0].query_text
        if first_query:
            return first_query
    return state.plan.goal


def _build_focused_query(state: InvestigationState, decision: SufficiencyDecision) -> str:
    """Deterministically assemble a targeted retrieval query from data the
    investigation already has -- no Gemini call, no LLM-generated text.
    Prefers the decision's own uncovered_entities (populated by
    EvidenceSufficiencyAssessor's stage 3 for a genuine coverage gap);
    falls back to the plan's primary_entities when the triggering decision
    has none to name (e.g. a confident-evidence-count shortfall with full
    entity coverage). Always includes the original question and
    investigation_type so the query stays anchored to what's actually being
    investigated, not just the gap; appends the decision's own
    human-readable reason last, so it can only add context, never dominate
    the query's semantic content."""
    parts = [_original_question(state)]

    focus_entities = decision.details.get("uncovered_entities") or state.plan.primary_entities
    if focus_entities:
        parts.append("Focus specifically on: " + ", ".join(focus_entities) + ".")

    parts.append(f"Investigation type: {state.plan.investigation_type}.")

    if decision.reason:
        parts.append(f"Reason for this focused search: {decision.reason}")

    return " ".join(parts)


class FocusedRetrievalResult(BaseModel):
    """What one retrieve() call did, for the caller (a future orchestrator)
    and for tests -- not itself part of InvestigationState, which already
    has everything durable (evidence, visited ids, search_history) updated
    directly."""

    query_used: str = Field(description="The deterministically-constructed query actually sent to retrieval")
    citations_retrieved: int = Field(description="Total citations returned by this pass, before dedup")
    duplicates_ignored: int = Field(
        default=0, description="Of those citations, how many were already-visited chunks and were not re-added"
    )
    new_evidence_count: int = Field(description="How many new Evidence items were actually added (post-dedup)")
    new_evidence_deferred: int = Field(
        default=0,
        description="New evidence found beyond max_new_evidence_added and not added this call (budget exhausted)",
    )
    termination_reason: str = Field(
        description="Why this call ended: 'no_results', 'no_new_evidence', 'budget_exhausted', or 'evidence_added'"
    )


class FocusedRetrievalExecutor:
    """Performs one targeted retrieval pass against an InvestigationState,
    guided by the SufficiencyDecision that flagged it as needing more
    evidence. Holds an InvestigationService purely as a source of the
    already-correct _build_evidence() method -- the same
    private-method-reuse pattern InvestigationAgent (Task 02) and
    ReferenceExpansionExecutor (Task 03) already use, so evidence assembly
    is never reimplemented a third time."""

    def __init__(
        self,
        service: InvestigationService | None = None,
        config: FocusedRetrievalConfig | None = None,
    ) -> None:
        self._service = service or InvestigationService()
        self._config = config or DEFAULT_FOCUSED_RETRIEVAL_CONFIG

    def retrieve(self, state: InvestigationState, decision: SufficiencyDecision) -> FocusedRetrievalResult:
        """Build a focused query from `state` and `decision`, run exactly
        one retrieval pass via the existing pipeline, fold any genuinely
        new evidence into `state`, and record one search_history entry
        regardless of outcome -- a pass that finds nothing new is exactly
        as explainable as one that finds evidence."""
        query = _build_focused_query(state, decision)
        project_id = _infer_project_id(state)

        citations = tools.search_documents(
            project_id=project_id,
            query=query,
            top_k=self._config.retrieval_top_k,
            investigation_plan=state.plan,
        )

        # Never retrieve already-visited chunks: filtered here (so
        # duplicates_ignored is explainable) as well as inside
        # add_evidence() (the actual source of truth) -- belt-and-braces,
        # not two competing dedup mechanisms. A document whose chunks are
        # all already visited naturally yields zero new_citations for it,
        # with no separate document-level check needed.
        new_citations = [citation for citation in citations if citation.chunk_id not in state.visited_chunk_ids]
        duplicates_ignored = len(citations) - len(new_citations)

        candidate_evidence = self._service._build_evidence(new_citations) if new_citations else []
        evidence_within_budget = candidate_evidence[: self._config.max_new_evidence_added]
        new_evidence_deferred = len(candidate_evidence) - len(evidence_within_budget)

        added_count = state.add_evidence(evidence_within_budget)

        if not citations:
            termination_reason = "no_results"
        elif not new_citations:
            termination_reason = "no_new_evidence"
        elif new_evidence_deferred > 0:
            termination_reason = "budget_exhausted"
        else:
            termination_reason = "evidence_added"

        state.advance_iteration()
        query_text = query
        if duplicates_ignored or new_evidence_deferred:
            query_text += f" [duplicates_ignored={duplicates_ignored}, deferred={new_evidence_deferred}]"
        state.record_search(
            RemediationType.FOCUSED_RETRIEVAL,
            results_returned=len(citations),
            new_evidence_count=added_count,
            query_text=query_text,
        )

        return FocusedRetrievalResult(
            query_used=query,
            citations_retrieved=len(citations),
            duplicates_ignored=duplicates_ignored,
            new_evidence_count=added_count,
            new_evidence_deferred=new_evidence_deferred,
            termination_reason=termination_reason,
        )
