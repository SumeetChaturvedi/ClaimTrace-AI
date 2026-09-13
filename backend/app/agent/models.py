"""Request/response contracts for the Investigation Engine, plus Evidence —
the core domain object for ClaimTrace.

InvestigationRequest/InvestigationResponse/Citation are the boundary between
the API layer and InvestigationService (app/agent/service.py). Evidence is
broader: it's the standard unit meant to be exchanged between investigation
components generally (Investigation Engine today; Contract Engine, Timeline
Engine, Reasoning Engine, and Report Generator later), not tied to any
specific LLM or retrieval implementation.

All of these types intentionally carry no behavior — just shape — so the
agent's future internals can change without changing this contract.
"""

from datetime import date
from typing import Any

from pydantic import BaseModel, Field

from app.contracts.models import ContractClause

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

    `page` (Phase 7: Multi-Format Evidence): a straight passthrough of
    DocumentChunk.page_number, so its meaning depends on the cited
    document's own file format exactly as that field's docstring describes
    — a true page number for a PDF, a 1-based paragraph ordinal for a DOCX.
    Deliberately not renamed or split into format-specific fields: both are
    a single real, honest, nullable integer position in the source file,
    and the existing shape already tolerates "unknown" via None, which is
    all a new format needs. The frontend decides whether to display it as
    "Page N" or "Paragraph N" from the citing document's filename."""

    document_id: int
    page: int | None = Field(default=None, description="Page number (PDF) or paragraph ordinal (DOCX) the citation was found on, if known")
    chunk_id: int
    relevance_score: float = Field(description="Similarity/relevance score from retrieval, higher is more relevant")
    chunk_text: str | None = Field(
        default=None,
        description=(
            "The actual matched chunk text, when available — populated by search_documents() "
            "straight from the semantic search result. None for citations built without going "
            "through search (no such path exists yet, but nothing should assume this is always set)."
        ),
    )


class Evidence(BaseModel):
    """A single piece of evidence used during an investigation — the standard
    object meant to be passed between investigation components (and later,
    the Contract/Timeline/Reasoning Engines and Report Generator). Carries no
    behavior: just a typed shape around a citation plus the text it points to.

    document_id duplicates citation.document_id deliberately, as a
    convenience accessor so callers don't need to reach into `citation` for
    the common case; nothing enforces the two stay consistent, since that
    would be validation logic and this model is shape only.
    """

    citation: Citation = Field(description="Where this evidence came from — document, page, and chunk")
    document_id: int = Field(description="Id of the source document (mirrors citation.document_id)")
    document_name: str = Field(description="Human-readable source filename, for display without a DB lookup")
    excerpt: str = Field(description="The specific text supporting this piece of evidence")
    surrounding_context: str = Field(description="Broader text around the excerpt, for reading it in context")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence that this evidence is relevant/reliable")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Open-ended extensibility slot for future engines; empty until something needs it",
    )


class TimelineEntry(BaseModel):
    """One document's place in an investigation's chronology (Phase 4:
    Timeline Productization) — mirrors app.investigation.timeline.TimelineEvent's
    own fields exactly (document_id/document_date/document_type/event_label,
    all deterministic, no LLM, no inference) plus `citations`: this
    investigation's own real Citation objects for that document, so the
    frontend can open the exact cited passage (via the existing Inspector/
    Source Viewer) without a second evidence lookup or any fabricated
    reference. `citations` added here rather than on TimelineEvent itself,
    since citation-attachment is specific to how a timeline is exposed on an
    investigation's response, not to timeline construction itself."""

    document_id: int
    document_date: date | None = Field(default=None, description="Mirrors Document.doc_date; None if the document has no extracted date")
    document_type: str | None = Field(default=None, description="Mirrors Document.doc_type")
    event_label: str = Field(description="Deterministic label derived solely from document_type")
    citations: list[Citation] = Field(
        default_factory=list,
        description="This investigation's own citations for this document — real evidence, never fabricated",
    )


class ReasoningResult(BaseModel):
    """The output of ReasoningEngine.reason() (app/agent/reasoning.py) — an
    answer derived from a set of Evidence, plus the trail of how it was
    produced. Internal only: not exposed through any API route yet.
    InvestigationService maps this 1:1 onto InvestigationResponse
    (answer -> answer, reasoning_steps -> reasoning_steps,
    supporting_evidence -> citations)."""

    answer: str
    reasoning_steps: list[str] = Field(default_factory=list)
    supporting_evidence: list[Citation] = Field(default_factory=list)


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
    timeline: list[TimelineEntry] = Field(
        default_factory=list,
        description="Chronological, document-level timeline for this investigation's evidence (Phase 4), each entry linked to its own real citations",
    )
    contract_clauses: list[ContractClause] = Field(
        default_factory=list,
        description=(
            "Phase 5 (Contract Intelligence Productization): the real ContractClause objects "
            "retrieved for this investigation from its own project's contract package "
            "(app/contracts/), exposed as-is instead of being discarded once the reasoning "
            "prompt is built. clause_number/title/topic/text only — a ContractClause carries "
            "no document_id, chunk_id, or page (see app/contracts/models.py), so unlike "
            "Citation/TimelineEntry there is no source-document or page linkage to expose here; "
            "nothing is fabricated to manufacture one."
        ),
    )
