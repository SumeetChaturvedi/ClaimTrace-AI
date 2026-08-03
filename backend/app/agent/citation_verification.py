"""Deterministic citation verification (Sprint 4 Task 03) — the missing
integrity control flagged repeatedly across this project's audits
(PROJECT_PLAN.md Part D §19): every citation ReasoningEngine is about to
return is checked against the database before it reaches
InvestigationResponse, instead of being trusted at face value.

This is a narrower guarantee than §19's original "does the LLM's claimed
excerpt match the source text" hallucination guard (that remains
unimplemented, see app/agent/tools.py's verify_citation stub, and is out of
scope here) — reasoning.py's own safety invariant already establishes that
citations are never parsed out of the LLM's answer text; supporting_evidence
is always built directly from InvestigationPackage.evidence. What this module
checks instead is that those citations are themselves well-formed and really
correspond to what's in the database, as a defense-in-depth check of that
invariant rather than a guard against a known way it's violated today: chunk
existence, non-empty chunk text, internally-consistent metadata, no
duplicates, and provenance back to evidence actually retrieved for this
investigation.

No LLM call, no new retrieval, no answer rewriting, no inferred
replacements — invalid citations are dropped, never repaired.
"""

from app.agent.models import Citation
from app.db.models import DocumentChunk
from app.db.session import get_session_factory


def verify_citations(citations: list[Citation], retrieved_evidence: list[Citation]) -> list[Citation]:
    """Return the subset of `citations` that pass every check below, in
    their original order, with duplicates (by document_id + chunk_id)
    collapsed to their first occurrence. Returns an empty list if `citations`
    is empty or if none pass — never fabricates a replacement.

    `retrieved_evidence` is the citation set actually produced by retrieval
    for this investigation (e.g. InvestigationPackage.evidence's citations);
    a candidate citation not present there fails verification regardless of
    whether it's otherwise well-formed, since this layer's job is confirming
    citations refer to evidence that was really retrieved, not evidence that
    merely could exist.

    For each surviving candidate:
    - its (document_id, chunk_id) pair must appear in `retrieved_evidence`
    - a DocumentChunk row with that chunk_id must actually exist
    - that row's document_id must match the citation's document_id (catches
      a chunk_id/document_id pair that doesn't actually belong together;
      also transitively confirms document_id exists, since DocumentChunk's
      document_id is a non-nullable foreign key — no separate Document query
      is needed for that)
    - that row's stored chunk_text must be non-empty
    - if the citation claims a page, it must be a positive number and match
      the chunk's own recorded page_number
    """
    if not citations:
        return []

    retrieved_keys = {(citation.document_id, citation.chunk_id) for citation in retrieved_evidence}

    verified: list[Citation] = []
    seen_keys: set[tuple[int, int]] = set()

    with get_session_factory()() as session:
        for citation in citations:
            key = (citation.document_id, citation.chunk_id)

            if key in seen_keys:
                continue
            if key not in retrieved_keys:
                continue

            chunk = session.get(DocumentChunk, citation.chunk_id)
            if chunk is None or chunk.document_id != citation.document_id:
                continue
            if not chunk.chunk_text or not chunk.chunk_text.strip():
                continue
            if citation.page is not None and (citation.page < 1 or citation.page != chunk.page_number):
                continue

            seen_keys.add(key)
            verified.append(citation)

    return verified
