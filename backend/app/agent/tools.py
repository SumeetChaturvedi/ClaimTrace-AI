"""Interface placeholders for the agent's future tools (PROJECT_PLAN.md Part D
§18: search_documents, read_document, get_document_metadata,
find_related_documents, verify_citation).

search_documents() and read_document() are implemented; the rest are still
stubs. Each delegates to app/retrieval/service.py, app/db/models.py, and
app/ingestion/ rather than containing logic of its own — this module's job is
translating between the agent's Citation model and whatever those lower
layers return, never leaking their internal types (e.g. ChunkSearchResult)
out to the rest of app/agent/.

get_document_filename() is a small internal helper (not one of the four
tools above) that InvestigationService uses alongside read_document() to
populate Evidence.document_name — see its docstring for why it exists.
"""

from pathlib import Path

from app.agent.models import Citation
from app.db.models import Document
from app.db.session import get_session_factory
from app.retrieval.service import search_chunks


class DocumentNotFoundError(Exception):
    """Raised by read_document() when no document exists for the given id,
    or its extracted text can't be found on disk."""


def search_documents(project_id: int, query: str, top_k: int = 5) -> list[Citation]:
    """Return the top_k chunks most relevant to `query`, ranked by similarity,
    as Citation objects — the agent's primary evidence-gathering tool.

    Wraps app/retrieval/service.py's search_chunks(); opens and closes its
    own DB session so callers only need to pass plain values. `project_id` is
    accepted for interface stability but not yet used to scope results:
    search_chunks() has no project filter, and V0 has exactly one project, so
    there is nothing to scope against without changing the retrieval module,
    which is out of scope for this task.

    Each Citation carries the matched chunk's own text (chunk_text), taken
    directly from the search result — ChunkSearchResult already includes it,
    so no separate lookup is needed. This is what lets Evidence be built from
    the actual retrieved passage instead of reconstructed from the full
    document (see InvestigationService._build_evidence).
    """
    with get_session_factory()() as session:
        results = search_chunks(session, query, top_k=top_k)

    return [
        Citation(
            document_id=result.document_id,
            page=result.page_number,
            chunk_id=result.chunk_id,
            relevance_score=result.similarity,
            chunk_text=result.chunk_text,
        )
        for result in results
    ]


def read_document(document_id: int) -> str:
    """Return the full extracted text of a document, for the agent to read
    in detail after finding it via search.

    Reads the file at the document's raw_text_path (see app/db/models.py
    Document, written by app/ingestion/storage.py at ingestion time) and
    returns it verbatim — no summarization, no reasoning, no LLM call, and
    no modification of stored data.

    Raises DocumentNotFoundError if no document exists for `document_id`, or
    if its extracted text file is missing from disk.
    """
    with get_session_factory()() as session:
        document = session.get(Document, document_id)

    if document is None:
        raise DocumentNotFoundError(f"No document with id={document_id}")

    text_path = Path(document.raw_text_path)
    try:
        return text_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise DocumentNotFoundError(
            f"Document {document_id} exists but its extracted text file is missing: {text_path}"
        ) from exc


def get_document_filename(document_id: int) -> str:
    """Look up a document's filename — needed to populate Evidence.document_name
    (app/agent/models.py), since Citation carries only document_id and
    read_document() returns text only, neither of which includes the
    filename. Internal helper alongside the four public tools, not one of
    them itself; reuses the same session/model pattern as read_document()
    rather than introducing a new one.
    """
    with get_session_factory()() as session:
        document = session.get(Document, document_id)

    if document is None:
        raise DocumentNotFoundError(f"No document with id={document_id}")

    return document.filename


def find_related_documents(document_id: int) -> list[int]:
    """Return the ids of documents that share referenced IDs or entities with
    `document_id`, for following cross-references during an investigation.

    Will be a deterministic metadata join on Document.referenced_ids, not an
    LLM call.
    """
    raise NotImplementedError


def verify_citation(citation: Citation, quote: str) -> bool:
    """Check whether `quote` actually appears in the cited document/page,
    deterministically. The hallucination-guard tool described in
    PROJECT_PLAN.md Part D §19 — never trust a claimed citation at face value.
    """
    raise NotImplementedError
