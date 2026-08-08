"""InvestigationState — the working memory of one iterative investigation
(Phase 3 Task 01, foundation for the not-yet-built Investigation Agent
described in the approved architecture specification).

This module is a pure state container plus mechanical bookkeeping (dedup,
counters). It contains no decisions: nothing here decides whether evidence
is enough, what to search for next, or when to stop — that is
EvidenceSufficiencyAssessor's job (evidence_sufficiency.py) and, later, the
Investigation Agent's own control loop, neither of which this module knows
about. InvestigationState is not wired into InvestigationService or any
other production path; nothing currently constructs or consumes it.

One instance is meant to exist per investigation (request-scoped, in-process,
discarded when the investigation completes) — the same lifecycle
InvestigationService.investigate() already has, just with more to remember
along the way than a single linear pass needs.

Field-by-field correspondence to the approved architecture's State Model:
    investigation plan        -> plan
    accumulated evidence      -> evidence
    visited chunk IDs         -> visited_chunk_ids
    visited document IDs      -> visited_document_ids
    fully read document IDs   -> fully_read_document_ids
    followed reference IDs    -> followed_reference_ids
    retrieved clause numbers  -> retrieved_clause_numbers
    retrieved clauses         -> retrieved_clauses
    timeline context          -> timeline_context
    search history            -> search_history
    iteration count           -> iteration_count
    stopping reason           -> stopping_reason
"""

from enum import Enum

from pydantic import BaseModel, Field

from app.agent.models import Evidence
from app.contracts.models import ContractClause
from app.investigation.models import InvestigationPlan


class RemediationType(str, Enum):
    """The vocabulary of remediation actions an evidence gap can call for —
    shared between SearchHistoryEntry.trigger_reason (this module) and
    EvidenceSufficiencyAssessor's decisions (evidence_sufficiency.py), so
    both speak the same terms. Defined here, not in the assessor module,
    because SearchHistoryEntry needs it and is part of the state shape;
    the assessor imports it from here rather than the other way around."""

    INITIAL_RETRIEVAL = "initial_retrieval"
    REFERENCE_EXPANSION = "reference_expansion"
    CLAUSE_TOP_UP = "clause_top_up"
    FOCUSED_RETRIEVAL = "focused_retrieval"
    FULL_DOCUMENT_READ = "full_document_read"


class SearchHistoryEntry(BaseModel):
    """One row of the investigation's explainability trail: what was done,
    why, and what it produced. Appended by record_search() below — never
    constructed or interpreted elsewhere in this module."""

    iteration: int
    trigger_reason: RemediationType
    query_text: str | None = Field(
        default=None,
        description="The search query used, if this step involved a query (None for e.g. a clause lookup by number)",
    )
    results_returned: int = Field(description="Total results this step returned, before dedup against state")
    new_evidence_count: int = Field(description="How many of those results were genuinely new (not already visited)")


class InvestigationState(BaseModel):
    """The accumulated memory of one investigation. Carries no behavior
    beyond dedup-safe accumulation and simple counters/setters — see the
    module docstring for what deliberately does NOT live here."""

    plan: InvestigationPlan

    evidence: list[Evidence] = Field(default_factory=list)
    visited_chunk_ids: set[int] = Field(default_factory=set)
    visited_document_ids: set[int] = Field(default_factory=set)
    fully_read_document_ids: set[int] = Field(default_factory=set)
    followed_reference_ids: set[str] = Field(default_factory=set)

    retrieved_clauses: list[ContractClause] = Field(default_factory=list)
    retrieved_clause_numbers: set[str] = Field(default_factory=set)

    timeline_context: str = ""

    search_history: list[SearchHistoryEntry] = Field(default_factory=list)
    iteration_count: int = 0
    stopping_reason: str | None = None

    def add_evidence(self, items: list[Evidence]) -> int:
        """Append the items in `items` whose citation.chunk_id has not
        already been seen, updating visited_chunk_ids/visited_document_ids
        for each one added. Returns how many were genuinely new — the
        caller (future orchestrator) uses this to tell whether a step made
        any progress. Order of `items` is preserved; duplicates within
        `items` itself are also collapsed, not just duplicates against
        prior state."""
        added = 0
        for item in items:
            chunk_id = item.citation.chunk_id
            if chunk_id in self.visited_chunk_ids:
                continue
            self.evidence.append(item)
            self.visited_chunk_ids.add(chunk_id)
            self.visited_document_ids.add(item.document_id)
            added += 1
        return added

    def mark_document_fully_read(self, document_id: int) -> None:
        """Record that `document_id` has been opened in full (via
        read_document()), separately from whatever chunk-level evidence it
        may also have contributed. Also counts as having visited the
        document, for callers that only track visited_document_ids."""
        self.fully_read_document_ids.add(document_id)
        self.visited_document_ids.add(document_id)

    def mark_reference_followed(self, reference: str) -> None:
        """Record that `reference` (a document-reference-shaped string, e.g.
        "VPGC-NRB4-0012") has been considered and acted on — regardless of
        whether it resolved to a new document, an already-visited one, or
        nothing at all. This is the authoritative "already considered" set
        EvidenceSufficiencyAssessor checks against; the caller is
        responsible for calling this for every reference it processes, not
        only the ones that turned out to matter, so the assessor never
        re-flags a reference that was already looked at."""
        self.followed_reference_ids.add(reference)

    def add_clauses(self, clauses: list[ContractClause]) -> int:
        """Append the clauses in `clauses` whose clause_number has not
        already been seen. Returns how many were genuinely new, mirroring
        add_evidence()'s return convention."""
        added = 0
        for clause in clauses:
            if clause.clause_number in self.retrieved_clause_numbers:
                continue
            self.retrieved_clauses.append(clause)
            self.retrieved_clause_numbers.add(clause.clause_number)
            added += 1
        return added

    def update_timeline_context(self, timeline_context: str) -> None:
        """Replace the current timeline context wholesale (it is always a
        fresh TimelineFormatter.format() call over the current
        visited-document set, never an incremental append)."""
        self.timeline_context = timeline_context

    def record_search(
        self,
        trigger_reason: RemediationType,
        results_returned: int,
        new_evidence_count: int,
        query_text: str | None = None,
    ) -> None:
        """Append one SearchHistoryEntry recording a step that was already
        performed and already folded into state via add_evidence()/
        add_clauses(). Does not itself perform any search, retrieval, or
        state mutation beyond appending the record."""
        self.search_history.append(
            SearchHistoryEntry(
                iteration=self.iteration_count,
                trigger_reason=trigger_reason,
                query_text=query_text,
                results_returned=results_returned,
                new_evidence_count=new_evidence_count,
            )
        )

    def advance_iteration(self) -> int:
        """Increment and return the iteration counter. Bounds-checking
        against a maximum iteration count is a loop-control decision, not
        state bookkeeping — left to the future orchestrator, not enforced
        here."""
        self.iteration_count += 1
        return self.iteration_count

    def stop(self, reason: str) -> None:
        """Record why the investigation stopped iterating. Does not itself
        decide that the investigation should stop — only records the
        decision once made elsewhere."""
        self.stopping_reason = reason
