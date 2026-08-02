"""Semantic retrieval over indexed document chunks.

This is the deterministic pgvector-similarity primitive behind the future
`search_documents` agent tool (PROJECT_PLAN.md Part D §18) — it does not call
an LLM and is not itself the tool; Deliverable 5 wraps this for the agent.
Ranking is vector similarity only, no keyword fallback (deliberately deferred
per Part D §18's "optional keyword fallback").

RetrievalScorer (scoring.py) is now called per result, but only ever returns
its semantic_score input unchanged today — so ranking order and similarity
values are unaffected. It's a pass-through applied after the DB query has
already ordered results by distance, not a re-ranking step.
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

    `retrieval_context` is optional and, today, has no effect: each result's
    similarity is passed through RetrievalScorer, which currently just
    returns it unchanged. Ranking order is set by the DB query above and is
    never re-sorted afterward, so this is a scoring pass, not a re-ranking
    step.
    """
    if not query or not query.strip():
        raise ValueError("query must not be empty")
    if top_k < 1:
        raise ValueError("top_k must be >= 1")

    query_vector = embed_texts([query.strip()])[0]
    distance = DocumentChunk.embedding.cosine_distance(query_vector).label("distance")

    stmt = (
        select(DocumentChunk, Document, distance)
        .join(Document, DocumentChunk.document_id == Document.id)
        .where(DocumentChunk.embedding.is_not(None))
        .order_by(distance)
        .limit(top_k)
    )

    results = [
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
    return [
        replace(
            result,
            similarity=scorer.score(semantic_score=result.similarity, retrieval_context=context, chunk=result),
        )
        for result in results
    ]
