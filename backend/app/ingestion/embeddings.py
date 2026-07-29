"""Embedding generation via a local sentence-transformers model.

Model choice matches PROJECT_PLAN.md Part F §28-31 ("Local model (e.g.
sentence-transformers/all-MiniLM-L6-v2) — free, runs on CPU") and the
Vector(384) column already declared on DocumentChunk in app/db/models.py.
"""

from functools import lru_cache

from sentence_transformers import SentenceTransformer

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSIONS = 384


@lru_cache
def get_embedding_model() -> SentenceTransformer:
    """Load the embedding model once per process and reuse it thereafter —
    mirrors the get_settings()/get_engine() singleton pattern in app/config.py
    and app/db/session.py."""
    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of chunk texts, returning one 384-dim vector per text."""
    if not texts:
        return []
    model = get_embedding_model()
    vectors = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    return vectors.tolist()
