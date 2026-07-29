"""Interface placeholders for the agent's future tools (PROJECT_PLAN.md Part D
§18: search_documents, read_document, get_document_metadata,
find_related_documents, verify_citation).

search_documents() is implemented; the rest are still stubs. Each delegates
to app/retrieval/service.py and app/ingestion/ rather than containing logic
of its own — this module's job is translating between the agent's Citation
model and whatever those lower layers return, never leaking their internal
types (e.g. ChunkSearchResult) out to the rest of app/agent/.
"""

from app.agent.models import Citation
from app.db.session import get_session_factory
from app.retrieval.service import search_chunks


def search_documents(project_id: int, query: str, top_k: int = 5) -> list[Citation]:
    """Return the top_k chunks most relevant to `query`, ranked by similarity,
    as Citation objects — the agent's primary evidence-gathering tool.

    Wraps app/retrieval/service.py's search_chunks(); opens and closes its
    own DB session so callers only need to pass plain values. `project_id` is
    accepted for interface stability but not yet used to scope results:
    search_chunks() has no project filter, and V0 has exactly one project, so
    there is nothing to scope against without changing the retrieval module,
    which is out of scope for this task.
    """
    with get_session_factory()() as session:
        results = search_chunks(session, query, top_k=top_k)

    return [
        Citation(
            document_id=result.document_id,
            page=result.page_number,
            chunk_id=result.chunk_id,
            relevance_score=result.similarity,
        )
        for result in results
    ]


def read_document(document_id: int) -> str:
    """Return the full extracted text of a document, for the agent to read
    in detail after finding it via search.

    Will read the document's raw_text_path (see app/db/models.py Document).
    """
    raise NotImplementedError


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
