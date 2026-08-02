"""RetrievalContext — a provider-agnostic structure for future
retrieval-shaping hints (e.g. derived from an InvestigationPlan).

Pure shape, no behavior: not consumed by search_chunks() or anything else
today, and constructing one has no effect on retrieval.

preferred_document_types uses the canonical DocumentType taxonomy (Sprint 3
Task 08) rather than free-text strings — the same vocabulary
InvestigationPlan.likely_evidence_sources now uses and app/ingestion/
persists, so RetrievalContextBuilder's mapping between them stays a pure
copy with nothing to translate.
"""

from pydantic import BaseModel, Field

from app.domain.document_types import DocumentType


class RetrievalContext(BaseModel):
    """Optional hints a future retrieval implementation could use to shape
    search — unused by app/retrieval/service.py today."""

    # Named generically on purpose: retrieval shouldn't know or care whether
    # a term came from an extracted entity, a contract clause, a document
    # number, or any future source — it's just text to search with.
    search_terms: list[str] = Field(default_factory=list)
    preferred_document_types: list[DocumentType] = Field(default_factory=list)
