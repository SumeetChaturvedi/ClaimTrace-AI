"""FullDocumentReadExecutor — the Full Document Read remediation from the
approved Investigation Agent architecture (Phase 3 Task 05). Given an
InvestigationState and the SufficiencyDecision that flagged it (stage 4:
a dominant document whose retrieved excerpts lack clear determination
content), opens the complete stored content of the document(s) the
decision itself named and folds any genuinely new evidence back into that
same state. Not the investigation loop, not Reference Expansion, not
Focused Retrieval, and not integrated into InvestigationService or
InvestigationAgent -- nothing calls this module outside itself and its own
validation script.

Document selection is intentionally passive: this executor reads ONLY the
document id(s) present in `decision.details` (see _document_ids_from_decision
below). It never searches, never calls find_related_documents(), and never
constructs a query -- the one input it doesn't need is a query, unlike
Reference Expansion and Focused Retrieval.

"Complete document content" here means every DocumentChunk row already
stored for a document -- not a second, wider top-k search, and not a
re-read of the raw text file truncated to a short prefix (which is what
InvestigationService._build_evidence()'s existing read_document() fallback
does, at CONTEXT_CHARS=800 -- adequate as a citation-less last resort, but
not "complete" for a document that can run to several pages). Ingestion's
existing chunking already covers 100% of a document's extracted text, so
fetching every chunk already stored for it IS reading the complete
document, without re-chunking or re-embedding anything. This also keeps
every resulting Evidence item chunk-accurate (a real chunk_id, real page
number) exactly like every other Evidence object already produced anywhere
else in the system, rather than introducing a document-level citation
shape nothing downstream has ever seen.

Reuses, rather than reimplements, every piece of real work:

    - Identifying which document(s) to read: SufficiencyDecision.details,
      populated entirely by EvidenceSufficiencyAssessor's existing stage 4
      (evidence_sufficiency.py) -- not re-derived here.
    - Fetching a document's stored chunks: the same direct
      DocumentChunk-by-document_id query pattern
      reference_expansion_executor._fetch_chunks() established in Task 03
      (a plain foreign-key lookup, not a retrieval algorithm) -- duplicated
      locally as _fetch_all_chunks(), not imported, so each remediation
      executor stays independently readable (Task 04's precedent).
    - Building Evidence from those chunks: the same
      _truncate()/_clamp_confidence() module-level helpers
      (app/agent/service.py) Task 03 already reuses for the same purpose.
    - Deduplication: InvestigationState.add_evidence() (already-visited
      chunk_ids) and InvestigationState.mark_document_fully_read()
      (already-fully-read documents), both from Task 01 -- no new dedup
      logic added here.

FULL_DOCUMENT_READ_CONFIDENCE (below) is the one genuinely new piece of
judgment this module introduces, for the same reason Task 03's
REFERENCE_EXPANSION_CONFIDENCE exists: a chunk fetched by document id, not
by semantic search, has no RetrievalScorer-produced similarity score to
reuse. Set slightly higher than Task 03's reference-expansion confidence --
this content comes from a document EvidenceSufficiencyAssessor itself
identified as the single most-cited, most-likely-decisive source for the
current question, a stronger signal than "a document merely referenced by
name."
"""

from pydantic import BaseModel, Field
from sqlalchemy import select

from app.agent import tools
from app.agent.evidence_sufficiency import SufficiencyDecision
from app.agent.full_document_read_config import DEFAULT_FULL_DOCUMENT_READ_CONFIG, FullDocumentReadConfig
from app.agent.investigation_state import InvestigationState, RemediationType
from app.agent.models import Citation, Evidence
from app.agent.service import CONTEXT_CHARS, EXCERPT_CHARS, _clamp_confidence, _truncate
from app.db.models import DocumentChunk
from app.db.session import get_session_factory

# Confidence assigned to evidence discovered via a full document read rather
# than semantic ranking -- see module docstring. Set above Task 03's
# REFERENCE_EXPANSION_CONFIDENCE (0.75): a dominant document
# EvidenceSufficiencyAssessor itself flagged as the likely decisive source
# is a stronger signal than a document merely named by reference. Still
# below 1.0 -- content wasn't independently verified as the most relevant
# passage the way a top semantic match is.
FULL_DOCUMENT_READ_CONFIDENCE = 0.8


def _document_ids_from_decision(decision: SufficiencyDecision) -> list[int]:
    """Document id(s) `decision` identified as needing a full read -- never
    derived independently by this executor. EvidenceSufficiencyAssessor's
    stage 4 (_check_dominant_document) currently names exactly one document
    via details['document_id']; details['document_ids'] (plural) is checked
    first, for forward-compatibility with a future decision shape naming
    more than one, per the architecture's "one or more documents" wording.
    Neither key is invented or guessed at when absent -- an empty list
    means this executor has nothing to do."""
    if "document_ids" in decision.details:
        return list(decision.details["document_ids"])
    if "document_id" in decision.details:
        return [decision.details["document_id"]]
    return []


def _fetch_all_chunks(document_id: int) -> list[DocumentChunk]:
    """Every DocumentChunk row stored for one document, in page/chunk order
    -- the same rows the existing chunking/embedding pipeline already
    produced at ingestion time, fetched directly by document_id instead of
    by embedding similarity. Together these rows already cover 100% of the
    document's extracted text (ingestion chunks the whole document, not a
    sample), which is what makes fetching all of them a genuine full
    document read rather than a second, wider search. Opens and closes its
    own session, mirroring every function in tools.py."""
    with get_session_factory()() as session:
        return list(
            session.scalars(
                select(DocumentChunk)
                .where(DocumentChunk.document_id == document_id)
                .order_by(DocumentChunk.page_number, DocumentChunk.id)
            ).all()
        )


class FullDocumentReadResult(BaseModel):
    """What one read() call did, for the caller (a future orchestrator) and
    for tests -- not itself part of InvestigationState, which already has
    everything durable (evidence, fully_read_document_ids, search_history)
    updated directly."""

    documents_requested: list[int] = Field(
        default_factory=list, description="Every document id the triggering decision named"
    )
    documents_read: list[int] = Field(
        default_factory=list, description="Documents actually opened and fully folded into evidence this call"
    )
    already_fully_read: list[int] = Field(
        default_factory=list,
        description="Requested documents that were already in state.fully_read_document_ids -- not reread",
    )
    documents_deferred: list[int] = Field(
        default_factory=list,
        description=(
            "Requested, not-yet-read documents this call did NOT open -- either beyond "
            "max_documents_per_call, or whose full chunk set would not fit within the remaining "
            "max_new_evidence_added budget. Not marked fully read; eligible for a future call."
        ),
    )
    new_evidence_count: int = Field(description="How many new Evidence items were actually added (post-dedup)")
    new_evidence_deferred: int = Field(
        default=0, description="Candidate evidence belonging to a deferred document -- not added this call"
    )
    duplicates_ignored: int = Field(
        default=0, description="Chunks, from documents that WERE read, whose chunk_id was already visited"
    )
    termination_reason: str = Field(
        description=(
            "Why this call ended: 'no_documents_identified', 'already_fully_read', 'no_new_evidence', "
            "'budget_exhausted', or 'evidence_added'"
        )
    )


class FullDocumentReadExecutor:
    """Opens the complete stored content of document(s) named by a
    SufficiencyDecision and folds any genuinely new evidence into an
    InvestigationState. Holds no state of its own -- safe to share a single
    instance across investigations, or construct a fresh one per call."""

    def __init__(self, config: FullDocumentReadConfig | None = None) -> None:
        self._config = config or DEFAULT_FULL_DOCUMENT_READ_CONFIG

    def read(self, state: InvestigationState, decision: SufficiencyDecision) -> FullDocumentReadResult:
        """Identify the document(s) `decision` named, open each (subject to
        the configured budget), and record one search_history entry
        regardless of outcome -- a call that adds nothing new is exactly as
        explainable as one that does."""
        requested_ids = _document_ids_from_decision(decision)

        already_fully_read = [doc_id for doc_id in requested_ids if doc_id in state.fully_read_document_ids]
        candidates = [doc_id for doc_id in requested_ids if doc_id not in state.fully_read_document_ids]

        # Budget stage 1: how many documents this call may even open.
        count_capped = candidates[: self._config.max_documents_per_call]
        documents_deferred = candidates[self._config.max_documents_per_call :]

        documents_read: list[int] = []
        duplicates_ignored = 0
        new_evidence: list[Evidence] = []
        new_evidence_deferred = 0
        budget_remaining = self._config.max_new_evidence_added

        for document_id in count_capped:
            chunks = _fetch_all_chunks(document_id)
            if not chunks:
                # Nothing stored for this document -- nothing to read,
                # nothing to defer; not marked fully read since there was
                # genuinely nothing to open.
                continue

            candidate_evidence: list[Evidence] = []
            document_duplicates = 0
            filename: str | None = None
            for chunk in chunks:
                if chunk.id in state.visited_chunk_ids:
                    document_duplicates += 1
                    continue
                if filename is None:
                    filename = tools.get_document_filename(document_id)
                surrounding_context = _truncate(chunk.chunk_text, CONTEXT_CHARS)
                excerpt = _truncate(surrounding_context, EXCERPT_CHARS)
                candidate_evidence.append(
                    Evidence(
                        citation=Citation(
                            document_id=document_id,
                            chunk_id=chunk.id,
                            page=chunk.page_number,
                            relevance_score=FULL_DOCUMENT_READ_CONFIDENCE,
                            chunk_text=chunk.chunk_text,
                        ),
                        document_id=document_id,
                        document_name=filename,
                        excerpt=excerpt,
                        surrounding_context=surrounding_context,
                        confidence=_clamp_confidence(FULL_DOCUMENT_READ_CONFIDENCE),
                        metadata={"source": "full_document_read"},
                    )
                )

            if not candidate_evidence:
                # Every chunk in this document was already visited -- the
                # document HAS now been fully inspected (every one of its
                # chunks was looked at), so mark it read to avoid ever
                # opening it again for zero possible benefit.
                state.mark_document_fully_read(document_id)
                documents_read.append(document_id)
                duplicates_ignored += document_duplicates
                continue

            if len(candidate_evidence) > budget_remaining:
                # Deferred whole, not partially added: a document is only
                # ever marked fully read once everything it contributed has
                # actually been kept (see FullDocumentReadConfig).
                documents_deferred.append(document_id)
                new_evidence_deferred += len(candidate_evidence)
                continue

            new_evidence.extend(candidate_evidence)
            duplicates_ignored += document_duplicates
            budget_remaining -= len(candidate_evidence)
            state.mark_document_fully_read(document_id)
            documents_read.append(document_id)

        added_count = state.add_evidence(new_evidence)

        if not requested_ids:
            termination_reason = "no_documents_identified"
        elif not candidates:
            termination_reason = "already_fully_read"
        elif documents_deferred:
            termination_reason = "budget_exhausted"
        elif added_count == 0:
            termination_reason = "no_new_evidence"
        else:
            termination_reason = "evidence_added"

        state.advance_iteration()
        query_text = "documents: " + ", ".join(str(doc_id) for doc_id in requested_ids)
        if already_fully_read or documents_deferred:
            query_text += (
                f" [already_fully_read={already_fully_read}, deferred={documents_deferred}, "
                f"duplicates_ignored={duplicates_ignored}]"
            )
        state.record_search(
            RemediationType.FULL_DOCUMENT_READ,
            results_returned=duplicates_ignored + len(new_evidence) + new_evidence_deferred,
            new_evidence_count=added_count,
            query_text=query_text,
        )

        return FullDocumentReadResult(
            documents_requested=requested_ids,
            documents_read=documents_read,
            already_fully_read=already_fully_read,
            documents_deferred=documents_deferred,
            new_evidence_count=added_count,
            new_evidence_deferred=new_evidence_deferred,
            duplicates_ignored=duplicates_ignored,
            termination_reason=termination_reason,
        )
