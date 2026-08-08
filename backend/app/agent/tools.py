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

from sqlalchemy import func, select

from app.agent.models import Citation
from app.agent.reference_expansion_config import DEFAULT_REFERENCE_EXPANSION_CONFIG, ReferenceExpansionConfig
from app.db.models import Document
from app.db.session import get_session_factory
from app.ingestion.metadata import is_location_reference
from app.investigation.models import InvestigationPlan
from app.retrieval.context_builder import RetrievalContextBuilder
from app.retrieval.service import search_chunks


class DocumentNotFoundError(Exception):
    """Raised by read_document() when no document exists for the given id,
    or its extracted text can't be found on disk."""


def search_documents(
    project_id: int,
    query: str,
    top_k: int = 5,
    investigation_plan: InvestigationPlan | None = None,
) -> list[Citation]:
    """Return the top_k chunks most relevant to `query`, ranked by similarity,
    as Citation objects — the agent's primary evidence-gathering tool.

    Wraps app/retrieval/service.py's search_chunks(); opens and closes its
    own DB session so callers only need to pass plain values. `project_id` is
    forwarded to search_chunks() as a hard filter (Sprint 7 Task 1), so a
    document belonging to a different project is never a candidate for this
    investigation's evidence — this is what keeps multiple ingested projects
    (e.g. Dataset V1 and Dataset V2) from contaminating each other's
    retrieval results.

    `investigation_plan`, when supplied, is converted to a RetrievalContext
    via RetrievalContextBuilder (reused as-is — no mapping logic duplicated
    here) and forwarded into search_chunks(), which forwards it to
    RetrievalScorer (app/retrieval/scoring.py). This is what makes the
    deterministic entity-match bonus actually active during real
    investigations: the plan's primary_entities become search_terms, and
    any chunk whose text contains one gets a small score bump. Without a
    plan, retrieval behaves exactly as before (semantic ranking only).

    Each Citation carries the matched chunk's own text (chunk_text), taken
    directly from the search result — ChunkSearchResult already includes it,
    so no separate lookup is needed. This is what lets Evidence be built from
    the actual retrieved passage instead of reconstructed from the full
    document (see InvestigationService._build_evidence).
    """
    retrieval_context = (
        RetrievalContextBuilder().build(investigation_plan) if investigation_plan is not None else None
    )

    with get_session_factory()() as session:
        results = search_chunks(
            session,
            query,
            top_k=top_k,
            retrieval_context=retrieval_context,
            project_id=project_id,
        )

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


def get_documents(document_ids: list[int]) -> list[Document]:
    """Return the Document rows for `document_ids` — used to build a
    timeline from evidence already retrieved for an investigation
    (app/investigation/timeline.py, Sprint 5 Task 05), not a new retrieval
    step: the ids passed in are always ones search_documents() already
    surfaced for this same investigation. Returns [] for an empty input.
    Result order is whatever the database returns it in; ordering it into a
    chronology is TimelineBuilder's job, not this function's."""
    if not document_ids:
        return []
    with get_session_factory()() as session:
        return list(session.scalars(select(Document).where(Document.id.in_(document_ids))).all())


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


def find_related_documents(
    document_ids: list[int],
    project_id: int | None = None,
    config: ReferenceExpansionConfig | None = None,
) -> list[int]:
    """Given a set of already-retrieved document ids, return the ids of
    additional documents (not already in `document_ids`) that share at
    least one identifier with any of them, via Document.referenced_ids —
    the deterministic metadata join described in PROJECT_PLAN.md Part D
    §18, not an LLM call, not embeddings.

    Widened from the originally-stubbed single-document signature
    (`find_related_documents(document_id) -> list[int]`) to take a
    collection: excluding documents "already retrieved" only makes sense
    against the full retrieved set, not one document at a time. Nothing in
    the codebase called this stub before this change, so there's no
    existing caller to break.

    One expansion hop only: matches are found directly against
    `document_ids`' referenced_ids, never against the referenced_ids of the
    documents this call itself returns — no recursion. No ranking, no
    scoring: the result is an unordered set of ids.

    Document references only (Sprint 4 Task 04): Document.referenced_ids
    mixes a document's own identifiers (SI-088, drawing IDs, ...) together
    with bare location tags (e.g. "P-42") that appear in most documents
    about the same subject — joining on the full mixed set connected
    documents through those shared generic tags too, expanding to nearly the
    whole corpus (Sprint 3.5 finding). is_location_reference()
    (app/ingestion/metadata.py) now filters location tags out of the join
    key before the overlap query runs, so expansion is driven only by
    genuine document identifiers. Location tags are still present in
    Document.referenced_ids exactly as before — filtered here at the point
    of use, not removed from storage.

    project_id (Phase 3 Task 03A): when supplied, both the boilerplate
    frequency computation below and the final candidate query are scoped to
    that project only — a document belonging to a different project can
    never be returned, mirroring search_chunks()'s existing project_id
    filter (Sprint 7 Task 1). None (the default) preserves this function's
    original, project-unscoped behaviour.

    Boilerplate/document-frequency filtering (Phase 3 Task 03A): Sprint 7 /
    Phase 3 Task 03 found that on Dataset V2, a project code ("NRB-4") and a
    contract-number fragment ("2020-01") appear in nearly every document's
    header and are the same letters/digits/hyphens shape as a genuine
    document identifier, so a single expansion hop pulled in 64 of 71
    documents. Before the overlap query runs, any collected reference token
    present in more than `config.max_document_frequency_ratio` of the
    documents in scope is dropped — see reference_expansion_config.py for
    why this generalizes to any future project's own boilerplate without a
    hardcoded token list.
    """
    if not document_ids:
        return []

    config = config or DEFAULT_REFERENCE_EXPANSION_CONFIG

    def _scoped(query):
        return query.where(Document.project_id == project_id) if project_id is not None else query

    with get_session_factory()() as session:
        retrieved_documents = session.scalars(
            select(Document).where(Document.id.in_(document_ids))
        ).all()

        collected_ids: set[str] = set()
        for document in retrieved_documents:
            if document.referenced_ids:
                collected_ids.update(
                    reference for reference in document.referenced_ids if not is_location_reference(reference)
                )

        if not collected_ids:
            return []

        total_in_scope = session.scalar(_scoped(select(func.count(Document.id))))
        if total_in_scope:
            # Postgres array-overlap ("&&"): Document.referenced_ids is
            # mapped via the generic sqlalchemy.ARRAY, whose comparator
            # doesn't expose .overlap() — .op("&&") applies the same
            # operator directly, no column/model change needed. Restricting
            # to documents that already overlap collected_ids (rather than
            # unnesting the whole scope) is equivalent for this purpose: any
            # document containing one of our candidate tokens necessarily
            # overlaps collected_ids by definition.
            reference_column = func.unnest(Document.referenced_ids).label("reference")
            frequency_rows = session.execute(
                _scoped(
                    select(reference_column, func.count(func.distinct(Document.id))).where(
                        Document.referenced_ids.op("&&")(list(collected_ids))
                    )
                ).group_by(reference_column)
            ).all()
            boilerplate = {
                reference
                for reference, doc_count in frequency_rows
                if reference in collected_ids and doc_count / total_in_scope > config.max_document_frequency_ratio
            }
            collected_ids -= boilerplate

        if not collected_ids:
            return []

        related_ids = session.scalars(
            _scoped(
                select(Document.id)
                .where(Document.id.notin_(document_ids))
                .where(Document.referenced_ids.op("&&")(list(collected_ids)))
            )
        ).all()

    return list(related_ids)


def verify_citation(citation: Citation, quote: str) -> bool:
    """Check whether `quote` actually appears in the cited document/page,
    deterministically. The hallucination-guard tool described in
    PROJECT_PLAN.md Part D §19 — never trust a claimed citation at face value.
    """
    raise NotImplementedError
