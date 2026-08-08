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

Project scoping (Sprint 7 Task 1): `project_id` is an optional hard filter
applied directly in the SQL query, before the candidate pool is even
assembled — a document belonging to a different project is never a
candidate, never scored, and never returned. This is unrelated to
RetrievalContext/RetrievalScorer (which only ever re-weight an already
project-scoped candidate set); it's the fix for a real, previously-known gap
(this module's own prior docstring said project scoping "has no project
filter" and "there is nothing to scope against" back when V0 had exactly one
project). `project_id=None` preserves the exact prior behaviour (search
across every project) — the /search API route still calls search_chunks()
without a project_id and is intentionally unaffected.

Result diversity (Sprint 7 Task 2): after scoring and sorting, results are
walked in score order and capped at MAX_CHUNKS_PER_DOCUMENT per document_id
before truncating to top_k (see _apply_diversity_cap below) — a document
that would otherwise contribute several of the highest-scoring chunks no
longer crowds out other, otherwise-lower-scoring-but-still-in-pool
documents. This only changes which chunks are dropped at the final
truncation step; the widened candidate pool and every chunk's score are
computed exactly as before.
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

# Maximum number of chunks any single document may contribute to a result
# set (Sprint 7 Task 2). Chosen to still let a genuinely central document
# supply more than one piece of evidence (unlike a hard cap of 1), while
# preventing it from dominating a small top_k the way a single 3-chunk
# document previously could.
MAX_CHUNKS_PER_DOCUMENT = 2


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
    project_id: int | None = None,
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

    `project_id` is optional; when supplied, only chunks belonging to that
    project are ever considered a candidate (Sprint 7 Task 1). `None`
    (the default) searches across every project, exactly as before this
    parameter existed — existing callers that don't pass it see no change
    in behaviour.
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
    )
    if project_id is not None:
        # Hard filter, applied before the candidate pool is assembled — a
        # document outside this project is never a candidate, never scored,
        # never returned (Sprint 7 Task 1).
        stmt = stmt.where(Document.project_id == project_id)
    stmt = stmt.order_by(distance).limit(candidate_k)

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
    return _apply_diversity_cap(scored, top_k, MAX_CHUNKS_PER_DOCUMENT)


def _apply_diversity_cap(
    results: list[ChunkSearchResult],
    top_k: int,
    max_per_document: int,
) -> list[ChunkSearchResult]:
    """Walk `results` (already sorted by score, most relevant first) and
    return up to top_k of them, skipping any chunk whose document has
    already contributed max_per_document chunks to the selection (Sprint 7
    Task 2). This is the new final truncation step: relative ranking is
    otherwise untouched — a chunk is only ever skipped for diversity, never
    reordered or rescored."""
    selected: list[ChunkSearchResult] = []
    counts: dict[int, int] = {}

    for result in results:
        if counts.get(result.document_id, 0) >= max_per_document:
            continue
        selected.append(result)
        counts[result.document_id] = counts.get(result.document_id, 0) + 1
        if len(selected) >= top_k:
            break

    return selected
