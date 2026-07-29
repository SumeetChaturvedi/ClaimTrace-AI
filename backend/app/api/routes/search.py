"""Semantic search endpoint over indexed document chunks."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.retrieval.service import DEFAULT_TOP_K, search_chunks

router = APIRouter(tags=["search"])


class SearchResultItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    chunk_id: int
    document_id: int
    filename: str
    doc_type: str | None
    doc_date: date | None
    page_number: int | None
    chunk_text: str
    similarity: float


class SearchResponse(BaseModel):
    query: str
    top_k: int
    results: list[SearchResultItem]


@router.get("/search", response_model=SearchResponse)
def search(
    q: str = Query(..., min_length=1, description="Natural-language search query"),
    top_k: int = Query(DEFAULT_TOP_K, ge=1, le=50, description="Number of chunks to return"),
    db: Session = Depends(get_db),
) -> SearchResponse:
    """Semantic search over indexed document chunks via pgvector cosine
    similarity. Returns an empty results list rather than an error when the
    corpus is empty or nothing matches."""
    if not q.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="q must not be empty")

    results = search_chunks(db, q, top_k=top_k)
    return SearchResponse(
        query=q,
        top_k=top_k,
        results=[SearchResultItem.model_validate(r) for r in results],
    )
