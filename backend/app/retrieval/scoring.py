"""RetrievalScorer — combines semantic similarity with two independent,
deterministic scoring signals: entity matching and document-type matching.

Entity matching (Sprint 3 Task 06): a case-insensitive exact substring match
of each RetrievalContext.search_term against chunk.chunk_text, each match
adding a fixed ENTITY_MATCH_WEIGHT. No fuzzy matching, no regex, no
stemming, no synonym expansion.

Document-type matching (Sprint 3 Task 11): chunk.doc_type is compared, as a
canonical DocumentType value (not a raw string), against
RetrievalContext.preferred_document_types. A match adds a fixed
DOCUMENT_TYPE_MATCH_WEIGHT. Since app/ingestion/pipeline.py normalizes
doc_type at persistence time (Sprint 3 Task 09), chunk.doc_type is already
expected to hold a canonical value (e.g. "APPROVAL") — DocumentType(raw)
reconstructs the enum member from that string directly. This is a type
conversion of an already-canonical value, not the raw-slug normalization
app/domain/document_types.normalize_document_type() performs; using that
function here would be wrong; its mapping keys are the old raw ingestion
slugs, not canonical values, and would never match.

The ChunkSearchResult import below is TYPE_CHECKING-only, not a runtime
dependency: RetrievalService (service.py) needs to import RetrievalScorer
from this module, and service.py is also where ChunkSearchResult is
defined, so a real runtime import here would be circular. score() reads
`chunk.chunk_text`/`chunk.doc_type` off the real object passed in at call
time — the TYPE_CHECKING guard only affects how the type is imported for
the annotation, not attribute access on the instance.
"""

from typing import TYPE_CHECKING

from app.domain.document_types import DocumentType
from app.retrieval.context import RetrievalContext

if TYPE_CHECKING:
    from app.retrieval.service import ChunkSearchResult

ENTITY_MATCH_WEIGHT = 0.05
DOCUMENT_TYPE_MATCH_WEIGHT = 0.05


class RetrievalScorer:
    """Scores a single retrieved chunk: semantic similarity plus an entity
    bonus and a document-type bonus, each independently computed and
    applied only when relevant context is available."""

    def score(
        self,
        semantic_score: float,
        retrieval_context: RetrievalContext | None,
        chunk: "ChunkSearchResult",
    ) -> float:
        """Return semantic_score plus ENTITY_MATCH_WEIGHT per matching
        search_term plus DOCUMENT_TYPE_MATCH_WEIGHT if chunk.doc_type is one
        of retrieval_context.preferred_document_types. Returns semantic_score
        unchanged if retrieval_context is None; each bonus independently
        contributes nothing if its own relevant field is empty or absent."""
        if retrieval_context is None:
            return semantic_score

        entity_bonus = self._entity_bonus(retrieval_context, chunk)
        document_type_bonus = self._document_type_bonus(retrieval_context, chunk)
        return semantic_score + entity_bonus + document_type_bonus

    def _entity_bonus(self, retrieval_context: RetrievalContext, chunk: "ChunkSearchResult") -> float:
        if not retrieval_context.search_terms:
            return 0.0
        chunk_text_lower = chunk.chunk_text.lower()
        matches = sum(
            1 for term in retrieval_context.search_terms if term.lower() in chunk_text_lower
        )
        return matches * ENTITY_MATCH_WEIGHT

    def _document_type_bonus(self, retrieval_context: RetrievalContext, chunk: "ChunkSearchResult") -> float:
        if not retrieval_context.preferred_document_types:
            return 0.0
        chunk_doc_type = _as_document_type(chunk.doc_type)
        if chunk_doc_type is not None and chunk_doc_type in retrieval_context.preferred_document_types:
            return DOCUMENT_TYPE_MATCH_WEIGHT
        return 0.0


def _as_document_type(raw: str | None) -> DocumentType | None:
    """Reconstruct a DocumentType from an already-canonical stored value.
    Returns None for None, or for any string that isn't a valid DocumentType
    (e.g. a pre-Task-09 legacy raw slug that was never re-ingested) —
    graceful, not an error, since this only gates an optional score bonus."""
    if raw is None:
        return None
    try:
        return DocumentType(raw)
    except ValueError:
        return None
