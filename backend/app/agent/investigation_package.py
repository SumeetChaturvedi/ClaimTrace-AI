"""The Investigation Package — the single, model-agnostic snapshot of
investigation state that any future reasoning model (Claude, GPT, Gemini, or
otherwise) will consume identically. ReasoningEngine (app/agent/reasoning.py)
takes one of these in; nothing about how reasoning is invoked should depend
on which model eventually does the reasoning — only ReasoningEngine's
internals should ever need to change for that.

timeline_context (Sprint 5 Task 05): a pre-formatted, already-chronological
text block — the output of TimelineFormatter.format() over a timeline
TimelineBuilder already built from this investigation's retrieved documents
(app/investigation/timeline.py). Built entirely upstream, in
InvestigationService; this module just carries it through unchanged, the
same way it carries `evidence` through unchanged — no timeline logic lives
here.

retrieved_clauses (Sprint 6 Task 07): ContractClause objects retrieved via
ClauseRetriever (app/contracts/clause_retrieval.py) from this investigation's
ContractContext, built entirely upstream in InvestigationService — this
module just carries them through unchanged, the same way it carries
`evidence` and `timeline_context` through unchanged. Not yet read by
PromptBuilder or ReasoningEngine: retrieval only, no exposure to reasoning
yet.
"""

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app.agent.models import Evidence
from app.contracts.models import ContractClause


class InvestigationPackage(BaseModel):
    """A complete snapshot of an investigation's state at the point
    reasoning is about to happen. Carries no behavior — just the question,
    every piece of evidence gathered for it (unfiltered, unranked, in
    whatever order it arrived), a few precomputed descriptive totals, an
    optional pre-built timeline context string, and any contract clauses
    retrieved alongside the document evidence."""

    question: str
    evidence: list[Evidence]
    total_evidence: int = Field(description="len(evidence)")
    documents_considered: int = Field(description="Number of unique source documents among `evidence`")
    highest_confidence: float | None = Field(
        default=None,
        description="Highest Evidence.confidence among `evidence`, or None if evidence is empty",
    )
    generated_at: datetime = Field(description="UTC timestamp this package was built")
    timeline_context: str = Field(
        default="",
        description=(
            "Pre-formatted chronological text (TimelineFormatter output) built from this "
            "investigation's retrieved documents; empty string if no timeline was built."
        ),
    )
    retrieved_clauses: list[ContractClause] = Field(
        default_factory=list,
        description=(
            "Contract clauses retrieved via ClauseRetriever for this investigation's "
            "ContractContext; not yet read by PromptBuilder or ReasoningEngine."
        ),
    )


class InvestigationPackageBuilder:
    """Builds an InvestigationPackage from a question and its evidence. Pure
    bookkeeping over what InvestigationService already gathered — no
    reasoning, filtering, ranking, or summarization happens here."""

    def build(
        self,
        question: str,
        evidence: list[Evidence],
        timeline_context: str = "",
        retrieved_clauses: list[ContractClause] | None = None,
    ) -> InvestigationPackage:
        """Preserve `question` and every item in `evidence` exactly as
        given (same objects, same order — no ranking or filtering), compute
        simple descriptive totals over them, and carry `timeline_context`
        and `retrieved_clauses` through unchanged (both already built
        upstream — this method doesn't touch timeline or clause-retrieval
        logic itself)."""
        confidences = [item.confidence for item in evidence]

        return InvestigationPackage(
            question=question,
            evidence=evidence,
            total_evidence=len(evidence),
            documents_considered=len({item.document_id for item in evidence}),
            highest_confidence=max(confidences) if confidences else None,
            generated_at=datetime.now(timezone.utc),
            timeline_context=timeline_context,
            retrieved_clauses=retrieved_clauses if retrieved_clauses is not None else [],
        )
