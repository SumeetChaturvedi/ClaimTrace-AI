"""Semantic retrieval over indexed document chunks.

This is the deterministic pgvector-similarity primitive behind the future
`search_documents` agent tool (PROJECT_PLAN.md Part D §18) — it does not call
an LLM and is not itself the tool; Deliverable 5 wraps this for the agent.
Ranking is vector similarity only, no keyword fallback (deliberately deferred
per Part D §18's "optional keyword fallback").

RetrievalScorer (scoring.py) is called per candidate and can change which
documents are returned, not just their order: the DB query below retrieves a
widened candidate pool (CANDIDATE_POOL_MULTIPLIER * top_k, floored at
CANDIDATE_POOL_MINIMUM), every candidate is scored, and only then is the pool
sorted by final score and truncated to top_k. A chunk that ranked outside the
old top_k on semantic similarity alone can now survive if its entity/doctype
bonus is enough to outscore chunks inside the original cutoff (Sprint 4 Task
01). Semantic similarity itself, and RetrievalScorer's own logic, are
unchanged — only the point in the pipeline where the LIMIT is applied moved
from before scoring to after it.
"""

from dataclasses import dataclass, replace
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentChunk
from app.ingestion.embeddings import embed_texts
from app.retrieval.context import RetrievalContext
from app.retrieval.scoring import RetrievalScorer

DEFAULT_TOP_K = 5

# How much wider than top_k the initial semantic candidate pool is, before
# RetrievalScorer runs and the result is truncated back down to top_k
# (Sprint 4 Task 01). CANDIDATE_POOL_MINIMUM is a floor for small top_k
# values, so scoring always has a meaningfully wider pool to work with than
# just top_k itself.
CANDIDATE_POOL_MULTIPLIER = 3
CANDIDATE_POOL_MINIMUM = 15


@dataclass(frozen=True)
class ChunkSearchResult:
    chunk_id: int
    document_id: int
    filename: str
    doc_type: str | None
    doc_date: date | None
    page_number: int | None
    chunk_text: str
    similarity: float


def search_chunks(
    session: Session,
    query: str,
    top_k: int = DEFAULT_TOP_K,
    retrieval_context: RetrievalContext | None = None,
) -> list[ChunkSearchResult]:
    """Embed `query` with the same model used at indexing time and return the
    top_k most similar chunks (cosine similarity, most relevant first) with
    their source document's metadata attached.

    Returns an empty list for an empty corpus or a query with no chunks to
    match against — never raises for that case. Raises ValueError for an
    empty query string or a non-positive top_k.

    `retrieval_context` is optional; when supplied, it's forwarded to
    RetrievalScorer and can change which chunks end up in the returned
    top_k, not just their order (Sprint 4 Task 01) — see candidate_k below.
    """
    if not query or not query.strip():
        raise ValueError("query must not be empty")
    if top_k < 1:
        raise ValueError("top_k must be >= 1")

    query_vector = embed_texts([query.strip()])[0]
    distance = DocumentChunk.embedding.cosine_distance(query_vector).label("distance")

    # Widen the semantic candidate pool before scoring, so RetrievalScorer's
    # bonuses can promote a chunk that ranked outside the old top_k on
    # semantic similarity alone, instead of only re-weighting a set the SQL
    # LIMIT already fixed (Sprint 4 Task 01).
    candidate_k = max(top_k * CANDIDATE_POOL_MULTIPLIER, CANDIDATE_POOL_MINIMUM)

    stmt = (
        select(DocumentChunk, Document, distance)
        .join(Document, DocumentChunk.document_id == Document.id)
        .where(DocumentChunk.embedding.is_not(None))
        .order_by(distance)
        .limit(candidate_k)
    )

    candidates = [
        ChunkSearchResult(
            chunk_id=chunk.id,
            document_id=document.id,
            filename=document.filename,
            doc_type=document.doc_type,
            doc_date=document.doc_date,
            page_number=chunk.page_number,
            chunk_text=chunk.chunk_text,
            similarity=1.0 - float(distance_value),
        )
        for chunk, document, distance_value in session.execute(stmt).all()
    ]

    context = retrieval_context or RetrievalContext()
    scorer = RetrievalScorer()
    scored = [
        replace(
            result,
            similarity=scorer.score(semantic_score=result.similarity, retrieval_context=context, chunk=result),
        )
        for result in candidates
    ]

    scored.sort(key=lambda result: result.similarity, reverse=True)
    return scored[:top_k]
