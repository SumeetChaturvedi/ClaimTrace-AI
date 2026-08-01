"""The Investigation Package — the single, model-agnostic snapshot of
investigation state that any future reasoning model (Claude, GPT, Gemini, or
otherwise) will consume identically. ReasoningEngine (app/agent/reasoning.py)
takes one of these in; nothing about how reasoning is invoked should depend
on which model eventually does the reasoning — only ReasoningEngine's
internals should ever need to change for that.
"""

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app.agent.models import Evidence


class InvestigationPackage(BaseModel):
    """A complete snapshot of an investigation's state at the point
    reasoning is about to happen. Carries no behavior — just the question,
    every piece of evidence gathered for it (unfiltered, unranked, in
    whatever order it arrived), and a few precomputed descriptive totals."""

    question: str
    evidence: list[Evidence]
    total_evidence: int = Field(description="len(evidence)")
    documents_considered: int = Field(description="Number of unique source documents among `evidence`")
    highest_confidence: float | None = Field(
        default=None,
        description="Highest Evidence.confidence among `evidence`, or None if evidence is empty",
    )
    generated_at: datetime = Field(description="UTC timestamp this package was built")


class InvestigationPackageBuilder:
    """Builds an InvestigationPackage from a question and its evidence. Pure
    bookkeeping over what InvestigationService already gathered — no
    reasoning, filtering, ranking, or summarization happens here."""

    def build(self, question: str, evidence: list[Evidence]) -> InvestigationPackage:
        """Preserve `question` and every item in `evidence` exactly as
        given (same objects, same order — no ranking or filtering), and
        compute simple descriptive totals over them."""
        confidences = [item.confidence for item in evidence]

        return InvestigationPackage(
            question=question,
            evidence=evidence,
            total_evidence=len(evidence),
            documents_considered=len({item.document_id for item in evidence}),
            highest_confidence=max(confidences) if confidences else None,
            generated_at=datetime.now(timezone.utc),
        )
