"""Request/response contracts for the Investigation Engine.

These types are the boundary between the API layer and InvestigationService
(app/agent/service.py). They intentionally carry no behavior — just shape —
so the agent's future internals can change without changing this contract.
"""

from pydantic import BaseModel, Field

DEFAULT_TOP_K = 5


class InvestigationRequest(BaseModel):
    """A natural-language investigation question scoped to one project."""

    project_id: int
    query: str = Field(min_length=1, description="Natural-language investigation question")
    top_k: int = Field(default=DEFAULT_TOP_K, gt=0, description="Max supporting chunks to consider")


class Citation(BaseModel):
    """A single piece of evidence grounding a claim in a specific document chunk.

    Mirrors the source_document_id/source_page fields on the (not yet used)
    dossier_findings table in app/db/models.py, plus the chunk_id needed to
    trace a citation back to its exact retrieved chunk.
    """

    document_id: int
    page: int | None = Field(default=None, description="Page number the citation was found on, if known")
    chunk_id: int
    relevance_score: float = Field(description="Similarity/relevance score from retrieval, higher is more relevant")


class InvestigationResponse(BaseModel):
    """The result of an investigation: an answer grounded in citations, plus
    the step-by-step trail that produced it (empty until the agent loop is
    implemented)."""

    answer: str
    citations: list[Citation] = Field(default_factory=list)
    reasoning_steps: list[str] = Field(
        default_factory=list,
        description="Ordered trail of agent reasoning/tool-call steps; populated once the agent loop exists",
    )
