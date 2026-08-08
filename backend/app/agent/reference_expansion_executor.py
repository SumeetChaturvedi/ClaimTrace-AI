"""ReferenceExpansionExecutor — the Reference Expansion remediation from the
approved Investigation Agent architecture (Phase 3 Task 03). Resolves the
unresolved document references an InvestigationState's evidence names but
doesn't yet include, and folds any newly-discovered evidence back into that
same state. Not the investigation loop (which would decide WHEN to call
this and what to do with the result) and not integrated into
InvestigationService or InvestigationAgent -- nothing calls this module
outside itself and its own validation script.

Reuses, rather than reimplements, every piece of real work:

    - Identifying unresolved references: EvidenceSufficiencyAssessor's
      existing stage-1 check (evidence_sufficiency.py), which itself calls
      the existing extract_document_references() (app/ingestion/metadata.py)
      -- not re-derived here.
    - Finding matching documents: tools.find_related_documents()
      (app/agent/tools.py, Sprint 4 Task 04), the existing one-hop,
      referenced_ids-array-overlap expansion tool -- exactly the mechanism
      the architecture spec named for this remediation. No new query, no
      new ranking, no new retrieval algorithm.
    - Fetching a newly-discovered document's chunks: tools.get_documents()
      (existing) returns Document ORM rows with their `.chunks` relationship
      already available -- these are the same DocumentChunk rows the
      existing indexing pipeline already created and search_chunks()
      already searches over, just looked up by document id instead of by
      embedding similarity, since a reference-driven fetch already knows
      exactly which document it wants.
    - Building Evidence from those chunks: InvestigationService's existing
      _truncate()/_clamp_confidence() module-level helpers (app/agent/
      service.py), the same ones _build_evidence() already uses -- not a
      second truncation/clamping implementation.
    - Deduplication: InvestigationState.add_evidence() (Task 01), which
      already refuses a chunk_id it has seen before; find_related_documents()
      itself already excludes ids already in the visited set. No new dedup
      logic is added here beyond calling what already exists.

REFERENCE_EXPANSION_CONFIDENCE (below) is the one genuinely new piece of
judgment this module introduces: evidence discovered by explicit reference
was never semantically ranked, so it has no RetrievalScorer-produced
similarity score to reuse. A fixed, documented confidence stands in for
one -- deliberately high (this document was explicitly named by evidence
already trusted enough to be in the investigation), but not maximal
(it wasn't independently verified as the most relevant passage the way a
top semantic match is).

Phase 3 Task 03A hardening: this executor now (1) scopes every
find_related_documents() call to the investigation's own project, inferred
from the documents already visited in `state` rather than a new field on
InvestigationState (see _infer_project_id below), and (2) enforces the
centralized safety budget in reference_expansion_config.py -- bounded
references processed, documents added, and new evidence added per call --
so a future iterative loop cannot have a single expand() call ingest an
unbounded share of the corpus. Both changes are entirely internal to this
module and tools.find_related_documents(); the public expand() signature is
unchanged.
"""

from pydantic import BaseModel, Field
from sqlalchemy import select

from app.agent import tools
from app.agent.evidence_sufficiency import EvidenceSufficiencyAssessor
from app.agent.investigation_state import InvestigationState, RemediationType
from app.agent.models import Citation, Evidence
from app.agent.reference_expansion_config import DEFAULT_REFERENCE_EXPANSION_CONFIG, ReferenceExpansionConfig
from app.agent.service import CONTEXT_CHARS, EXCERPT_CHARS, _clamp_confidence, _truncate
from app.db.models import Document, DocumentChunk
from app.db.session import get_session_factory

# Confidence assigned to evidence discovered via reference expansion rather
# than semantic ranking -- see module docstring for the reasoning. Chosen
# to sit above EvidenceSufficiencyAssessor.CONFIDENCE_THRESHOLD (0.6) by a
# comfortable margin, so newly-expanded evidence can itself count toward a
# future "confident evidence" check rather than needing yet another round
# to be trusted.
REFERENCE_EXPANSION_CONFIDENCE = 0.75


class ReferenceExpansionResult(BaseModel):
    """What one expand() call did, for the caller (a future orchestrator)
    and for tests -- not itself part of InvestigationState, which already
    has everything durable (evidence, visited ids, followed references,
    search_history) updated directly."""

    references_attempted: list[str] = Field(
        default_factory=list, description="Unresolved references this call actually tried to resolve, within budget"
    )
    references_resolved: list[str] = Field(
        default_factory=list,
        description="Subset of references_attempted for which at least one new document was found",
    )
    references_deferred: list[str] = Field(
        default_factory=list,
        description=(
            "Unresolved references beyond max_references_processed -- not attempted this call, "
            "still unresolved for a future call."
        ),
    )
    documents_added: list[int] = Field(default_factory=list, description="Document ids newly fetched this call")
    documents_deferred: list[int] = Field(
        default_factory=list,
        description=(
            "Newly-discovered related document ids beyond max_documents_added -- not fetched this "
            "call."
        ),
    )
    new_evidence_count: int = Field(description="How many new Evidence items were actually added (post-dedup)")
    new_evidence_deferred: int = Field(
        default=0,
        description=(
            "How many additional candidate evidence items (chunks from fetched documents) existed "
            "beyond max_new_evidence_added and were not added this call."
        ),
    )


def _fetch_chunks(document_ids: list[int]) -> list[DocumentChunk]:
    """Fetch every DocumentChunk row for `document_ids`, in a session this
    function owns and closes itself -- the same open-a-session-per-call
    convention every function in tools.py already uses. A plain foreign-key
    lookup (document_id IN (...)), not a retrieval algorithm: no embedding
    similarity, no scoring, no ranking -- those remain exclusively
    search_chunks()'s concern. Needed because tools.get_documents() closes
    its session before returning, so a Document's `.chunks` relationship
    (lazy-loaded) cannot be traversed afterward without triggering a
    DetachedInstanceError; this fetches the same rows directly instead of
    relying on that relationship post-return."""
    if not document_ids:
        return []
    with get_session_factory()() as session:
        return list(
            session.scalars(select(DocumentChunk).where(DocumentChunk.document_id.in_(document_ids))).all()
        )


def _infer_project_id(state: InvestigationState) -> int | None:
    """Best-effort project scope for this expansion, derived from the
    documents already visited in `state` -- not a new field on
    InvestigationState, which this task does not modify. Every currently
    visited document is expected to belong to the same project, since
    tools.search_documents() has been project-scoped since Sprint 7 Task 1;
    that shared project id is what scopes the find_related_documents() call
    (Phase 3 Task 03A). Returns None -- unscoped, this tool's original
    behaviour -- if `state` has no visited documents yet, or if they
    unexpectedly span more than one project id (defensive; should not
    happen given upstream scoping, but this function must never guess)."""
    if not state.visited_document_ids:
        return None
    with get_session_factory()() as session:
        project_ids = set(
            session.scalars(
                select(Document.project_id).where(Document.id.in_(state.visited_document_ids)).distinct()
            ).all()
        )
    return project_ids.pop() if len(project_ids) == 1 else None


class ReferenceExpansionExecutor:
    """Resolves an InvestigationState's currently-unresolved document
    references by one hop of reference expansion. Holds no state of its
    own -- safe to share a single instance or construct fresh each call."""

    def __init__(
        self,
        assessor: EvidenceSufficiencyAssessor | None = None,
        config: ReferenceExpansionConfig | None = None,
    ) -> None:
        self._assessor = assessor or EvidenceSufficiencyAssessor()
        self._config = config or DEFAULT_REFERENCE_EXPANSION_CONFIG

    def expand(self, state: InvestigationState) -> ReferenceExpansionResult:
        """Identify `state`'s currently-unresolved document references,
        attempt to resolve each via the existing one-hop expansion tool,
        fold any newly-discovered evidence into `state`, and record one
        search_history entry regardless of outcome -- a call that finds
        nothing is exactly as explainable as one that finds evidence.

        Every reference this call looks at is marked followed in `state`
        before returning, whether or not it resolved to a document,
        fulfilling the mark-as-followed-regardless-of-outcome contract
        EvidenceSufficiencyAssessor's stage 1 already documents. This is
        also what makes repeated references terminate immediately: calling
        expand() again with nothing newly unresolved does no retrieval at
        all (see the early-return below)."""
        decision = self._assessor._check_unresolved_references(state)

        if decision is None:
            # Nothing unresolved -- terminate cleanly, no retrieval, no
            # state mutation beyond recording that this was checked.
            state.advance_iteration()
            state.record_search(
                RemediationType.REFERENCE_EXPANSION,
                results_returned=0,
                new_evidence_count=0,
                query_text="(no unresolved references)",
            )
            return ReferenceExpansionResult(new_evidence_count=0)

        unresolved_references: list[str] = decision.details["unresolved_references"]

        # Budget (Phase 3 Task 03A): credit at most max_references_processed
        # references to this call, in the deterministic order
        # extract_document_references() already produces (sorted). The rest
        # stay unresolved -- EvidenceSufficiencyAssessor will surface them
        # again on a future call, exactly as if this call had never seen
        # them.
        references_to_process = unresolved_references[: self._config.max_references_processed]
        references_deferred = unresolved_references[self._config.max_references_processed :]

        # Project scoping (Phase 3 Task 03A): infer the active project from
        # state's own visited documents rather than a new field on
        # InvestigationState, and forward it into the hardened tool so a
        # document from a different project can never be returned.
        project_id = _infer_project_id(state)

        # "Search for matching documents": the existing one-hop expansion
        # tool, now project-scoped and boilerplate-filtered (Phase 3 Task
        # 03A). Still operates on the currently visited document set, not on
        # the raw reference strings directly -- see module docstring for why
        # this still finds the right documents (a visited document's own
        # extracted referenced_ids already contains these same reference
        # strings, and a target document's own metadata-box self-reference
        # means its referenced_ids contains its own id, so the array overlap
        # this tool already performs connects the two).
        related_document_ids = tools.find_related_documents(list(state.visited_document_ids), project_id=project_id)

        # Never re-fetch a document already visited (defensive: the tool
        # above already excludes these, this is belt-and-braces against
        # duplicate retrieval, not a second source of truth). Sorted for a
        # deterministic budget cut below.
        new_document_ids_all = sorted(
            doc_id for doc_id in related_document_ids if doc_id not in state.visited_document_ids
        )
        new_document_ids = new_document_ids_all[: self._config.max_documents_added]
        documents_deferred = new_document_ids_all[self._config.max_documents_added :]

        # Document metadata (filename) via the existing tool -- its scalar
        # columns remain valid after the session closes, unlike a lazy
        # relationship. Chunk rows are fetched separately (see
        # _fetch_chunks' docstring for why).
        documents = tools.get_documents(new_document_ids) if new_document_ids else []
        filenames_by_document_id = {document.id: document.filename for document in documents}
        chunks = sorted(_fetch_chunks(new_document_ids), key=lambda chunk: (chunk.document_id, chunk.id))

        chunks_within_budget = chunks[: self._config.max_new_evidence_added]
        new_evidence_deferred = len(chunks) - len(chunks_within_budget)

        new_evidence: list[Evidence] = []
        for chunk in chunks_within_budget:
            surrounding_context = _truncate(chunk.chunk_text, CONTEXT_CHARS)
            excerpt = _truncate(surrounding_context, EXCERPT_CHARS)
            new_evidence.append(
                Evidence(
                    citation=Citation(
                        document_id=chunk.document_id,
                        chunk_id=chunk.id,
                        page=chunk.page_number,
                        relevance_score=REFERENCE_EXPANSION_CONFIDENCE,
                        chunk_text=chunk.chunk_text,
                    ),
                    document_id=chunk.document_id,
                    document_name=filenames_by_document_id.get(chunk.document_id, f"document-{chunk.document_id}"),
                    excerpt=excerpt,
                    surrounding_context=surrounding_context,
                    confidence=_clamp_confidence(REFERENCE_EXPANSION_CONFIDENCE),
                    metadata={"source": "reference_expansion"},
                )
            )

        added_count = state.add_evidence(new_evidence)

        # Every reference this call actually processed is now followed,
        # regardless of whether it personally resolved to a document -- a
        # reference that matched nothing (dataset boilerplate, a reference
        # to something outside this corpus, ...) must not be re-flagged as
        # unresolved next time. A deferred reference (beyond budget) is NOT
        # marked followed, so it remains unresolved and eligible for a
        # future call.
        for reference in references_to_process:
            state.mark_reference_followed(reference)

        state.advance_iteration()
        query_text = "references: " + ", ".join(references_to_process)
        if references_deferred:
            query_text += f" (deferred: {len(references_deferred)})"
        state.record_search(
            RemediationType.REFERENCE_EXPANSION,
            results_returned=len(new_evidence),
            new_evidence_count=added_count,
            query_text=query_text,
        )

        # A reference counts as "resolved" if this call ended up with at
        # least one new document, without attributing which specific
        # reference led to which specific document -- find_related_documents()
        # doesn't preserve that mapping, and inventing one would mean
        # re-deriving its logic rather than reusing it.
        references_resolved = references_to_process if new_document_ids else []

        return ReferenceExpansionResult(
            references_attempted=references_to_process,
            references_resolved=references_resolved,
            references_deferred=references_deferred,
            documents_added=[document.id for document in documents],
            documents_deferred=documents_deferred,
            new_evidence_count=added_count,
            new_evidence_deferred=new_evidence_deferred,
        )
