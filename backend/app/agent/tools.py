"""Interface placeholders for the agent's future tools (PROJECT_PLAN.md Part D
§18: search_documents, read_document, get_document_metadata,
find_related_documents, verify_citation).

None of these are implemented yet. Signatures are typed and documented ahead
of time so InvestigationService can eventually be written against a stable
tool interface; each will later delegate to app/retrieval/service.py and
app/ingestion/ rather than containing logic of its own.
"""

from app.agent.models import Citation


def search_documents(query: str, top_k: int = 5) -> list[Citation]:
    """Return the top_k chunks most relevant to `query`, ranked by similarity.

    Will wrap app/retrieval/service.py's search_chunks() as the agent's
    primary evidence-gathering tool.
    """
    raise NotImplementedError


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
