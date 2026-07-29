"""Deterministic text chunking.

PROJECT_PLAN.md (Part C step 5, Part F §32) specifies a "chunk + embed + index"
stage and a document_chunks table with a per-chunk page_number, but does not
pin down a chunk size or overlap. This module fills that gap with a
fixed-size sliding window over whitespace-split words, chunked independently
per page (chunks never span a page boundary, since each chunk carries exactly
one page_number). Defaults are sized well under the 256-token limit of
sentence-transformers/all-MiniLM-L6-v2 (see embeddings.py).

Pages are recovered from the form-feed ("\\f") separators that
ingestion/storage.py writes between pages when persisting extracted text.
"""

from dataclasses import dataclass

CHUNK_SIZE_WORDS = 200
CHUNK_OVERLAP_WORDS = 40


@dataclass(frozen=True)
class Chunk:
    page_number: int
    chunk_text: str


def chunk_document(
    full_text: str,
    *,
    chunk_size: int = CHUNK_SIZE_WORDS,
    overlap: int = CHUNK_OVERLAP_WORDS,
) -> list[Chunk]:
    """Split page-separated text into fixed-size, overlapping word windows.

    Deterministic: identical input always yields identical chunks in the same
    order, so callers can safely replace-and-reinsert on reprocessing rather
    than diffing. Blank pages produce no chunks.
    """
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks: list[Chunk] = []
    for page_number, page_text in enumerate(full_text.split("\f"), start=1):
        words = page_text.split()
        if not words:
            continue

        start = 0
        while start < len(words):
            end = min(start + chunk_size, len(words))
            chunks.append(
                Chunk(page_number=page_number, chunk_text=" ".join(words[start:end]))
            )
            if end == len(words):
                break
            start = end - overlap

    return chunks
