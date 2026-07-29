"""Chunk + embed + persist stage — ties chunking.py and embeddings.py to the
document_chunks table (PROJECT_PLAN.md Part C step 5).

Idempotent by construction: indexing a document always deletes any chunks it
already has before inserting the freshly computed set, in the same
transaction. Reprocessing therefore replaces rather than duplicates, and a
crash partway through never leaves a mix of old and new chunks.
"""

from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentChunk
from app.ingestion.chunking import chunk_document
from app.ingestion.embeddings import embed_texts


def index_document(session: Session, document: Document) -> list[DocumentChunk]:
    """Chunk a document's extracted text, embed each chunk, and stage the
    resulting rows on the session (flushed, not committed — the caller owns
    the transaction boundary)."""
    full_text = Path(document.raw_text_path).read_text(encoding="utf-8")
    chunks = chunk_document(full_text)

    session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))

    if not chunks:
        session.flush()
        return []

    embeddings = embed_texts([chunk.chunk_text for chunk in chunks])

    rows = [
        DocumentChunk(
            document_id=document.id,
            page_number=chunk.page_number,
            chunk_text=chunk.chunk_text,
            embedding=embedding,
        )
        for chunk, embedding in zip(chunks, embeddings)
    ]
    session.add_all(rows)
    session.flush()
    return rows
