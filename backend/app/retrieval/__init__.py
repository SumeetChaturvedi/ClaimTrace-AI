"""Retrieval — deterministic pgvector-similarity search over indexed
document chunks. See app/retrieval/service.py, app/retrieval/context.py,
app/retrieval/context_builder.py, and app/retrieval/scoring.py."""

from app.retrieval.context import RetrievalContext
from app.retrieval.context_builder import RetrievalContextBuilder
from app.retrieval.scoring import RetrievalScorer

__all__ = ["RetrievalContext", "RetrievalContextBuilder", "RetrievalScorer"]
