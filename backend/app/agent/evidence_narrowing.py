"""EvidenceNarrower — the Evidence Narrowing layer (Sprint 8 Task 01). Runs
after the Investigation Loop (Phase 3 Task 06/07) has finished gathering
evidence and before InvestigationPackageBuilder / PromptBuilder ever see it,
narrowing a real investigation's evidence set (measured at ~59 items on
average after Task 07's integration) down to the subset that materially
supports the answer -- deterministically, with no Gemini/LLM call and no
semantic reranking, exactly as this task requires.

Not the same thing as app/agent/citation_verification.py's existing
verify_citations() (Sprint 4 Task 03), and doesn't touch or duplicate it.
That module runs AFTER Gemini has answered, checking that whatever
citations ReasoningEngine is about to return are well-formed and really
backed by a database row (a defense-in-depth integrity check on the
output). This module runs BEFORE Gemini is ever called, reducing how much
evidence reaches the prompt in the first place (a noise-reduction step on
the input). The two are complementary and independently useful; neither
needs to know the other exists, and reasoning.py is untouched by this task.

Not a retrieval step either: nothing here queries the database, calls
search_chunks(), or discovers new evidence. It only reorganizes and prunes
the Evidence list InvestigationState already accumulated, using metadata
that already exists on each Evidence/Citation object plus one reused
heuristic (see _is_decisive below) -- no new judgment about what evidence
"means" is introduced beyond what EvidenceSufficiencyAssessor already
established.

Pipeline (four deterministic stages, each producing explainable discard
reasons):

    1. Deduplicate exact-text duplicates.
    2. Merge same-document, same-page, consecutive-chunk evidence into one
       combined item per contiguous run (chunking.py's sliding window
       guarantees these chunks share literal overlapping text -- this
       stitches them back into one continuous passage rather than showing
       the same paragraph twice under two different chunk_ids).
    3. Drop low-confidence, non-decisive evidence (a citation-layer
       confidence floor; decisive evidence -- see _is_decisive -- is never
       dropped by this stage alone).
    4. Cap citations per document, then cap the total, ranking by
       (decisive, confidence) -- both existing signals, not new ones.

"Decisive" reuses EvidenceSufficiencyAssessor's own
_has_determination_content() heuristic (evidence_sufficiency.py) verbatim,
so "prioritize decisive evidence" here means exactly what "the dominant
document lacks determination content" already means everywhere else in
this codebase -- not a second, competing definition of what counts as
decisive.
"""

from pydantic import BaseModel, Field

from app.agent.evidence_narrowing_config import DEFAULT_EVIDENCE_NARROWING_CONFIG, EvidenceNarrowingConfig
from app.agent.evidence_sufficiency import _has_determination_content
from app.agent.models import Citation, Evidence
from app.agent.service import CONTEXT_CHARS, EXCERPT_CHARS, _clamp_confidence, _truncate


def _normalized_text(evidence: Evidence) -> str:
    """Whitespace/case-normalized excerpt, used only as a dedup key -- never
    shown to a user or a model."""
    return " ".join(evidence.excerpt.split()).lower()


def _is_decisive(evidence: Evidence) -> bool:
    """Whether `evidence` itself states an outcome/determination, reusing
    EvidenceSufficiencyAssessor's own heuristic (evidence_sufficiency.py) --
    the same "at least one digit plus a determination word" check already
    used to decide whether a dominant document needs a full read. Checked
    against excerpt and surrounding_context separately (rather than
    concatenated), since surrounding_context is a superset of excerpt and
    may contain determination language excerpt's shorter truncation cut
    off."""
    return _has_determination_content(evidence.excerpt) or _has_determination_content(evidence.surrounding_context)


# Remediation executors whose confidence is a fixed, documented stand-in
# rather than a genuine per-item relevance measurement -- see
# reference_expansion_executor.py's REFERENCE_EXPANSION_CONFIDENCE (0.75)
# and full_document_read_executor.py's FULL_DOCUMENT_READ_CONFIDENCE (0.8),
# both explicitly documented as "not independently verified as the most
# relevant passage the way a top semantic match is." Comparing these flat
# numbers directly against real cosine-similarity confidence as plain
# floats is an apples-to-oranges comparison: a first version of this
# module's ranking did exactly that and, confirmed against the real
# Dataset V2 benchmark, systematically buried genuinely well-matched real
# retrieval results (e.g. real matches scoring 0.63-0.79) beneath a large
# tied cluster of flatly-scored remediation evidence sitting at 0.75/0.8,
# dropping average recall from 0.806 to 0.22-0.36. _priority_score below
# fixes this by treating "real retrieval vs. remediation" as the primary
# ranking signal, not the raw confidence number.
_REMEDIATION_SOURCES = {"reference_expansion", "full_document_read"}


def _origin_source(evidence: Evidence) -> str:
    """The source that originally produced this evidence -- 'retrieval' for
    anything from the real, semantically-scored search path (the initial
    pass or Focused Retrieval), or a remediation executor's own metadata
    tag. A merged item (stage 2) carries this forward from its
    representative chunk's original source (set at merge time in
    _merge_same_document), so merging never loses the distinction."""
    return evidence.metadata.get("origin_source") or evidence.metadata.get("source") or "retrieval"


def _is_real_retrieval(evidence: Evidence) -> bool:
    return _origin_source(evidence) not in _REMEDIATION_SOURCES


def _priority_score(evidence: Evidence) -> tuple[bool, bool, float]:
    """Deterministic composite rank for stages 4a/4b, a lexicographic
    tuple: real retrieval before remediation (see module note above),
    decisive evidence preferred within a tier, confidence as the
    within-tier tiebreak (real discriminating signal for real-retrieval
    evidence; a documented fixed stand-in for remediation evidence)."""
    return (_is_real_retrieval(evidence), _is_decisive(evidence), evidence.confidence)


def _merge_chunk_texts(texts: list[str], max_word_search: int) -> str:
    """Stitch consecutive, literally-overlapping chunk texts into one
    continuous passage by detecting each pair's actual shared
    suffix/prefix words -- not a fixed-offset assumption about
    chunking.py's own overlap size, so this stays correct even if that
    changes. `texts` must already be in chunk order."""
    combined_words = texts[0].split()
    for text in texts[1:]:
        next_words = text.split()
        max_check = min(len(combined_words), len(next_words), max_word_search)
        overlap = 0
        for k in range(max_check, 0, -1):
            if combined_words[-k:] == next_words[:k]:
                overlap = k
                break
        combined_words.extend(next_words[overlap:])
    return " ".join(combined_words)


class DiscardedEvidence(BaseModel):
    """One discarded Evidence item, for internal debugging/explainability
    only -- never shown to a user or passed to PromptBuilder."""

    document_id: int
    chunk_id: int
    reason: str = Field(
        description=(
            "'duplicate' | 'merged_into:<chunk_id>' | 'below_confidence_threshold' | "
            "'per_document_cap_exceeded' | 'exceeded_max_citations'"
        )
    )


class EvidenceNarrowingStats(BaseModel):
    """Aggregate counts for one narrow() call, for explainability and for
    reporting citation-count reduction."""

    evidence_before: int
    evidence_after: int
    duplicates_removed: int
    merged_groups: int
    items_absorbed_by_merge: int
    below_confidence_removed: int
    per_document_cap_removed: int
    over_max_removed: int
    documents_before: int
    documents_after: int


class EvidenceNarrowingResult(BaseModel):
    """narrow()'s complete output: the filtered evidence PromptBuilder
    should actually see, the discarded list (debugging only), and summary
    statistics."""

    retained_evidence: list[Evidence]
    discarded_evidence: list[DiscardedEvidence]
    statistics: EvidenceNarrowingStats


class EvidenceNarrower:
    """Deterministically narrows an investigation's full Evidence list down
    to the subset that materially supports the answer. Holds no state of
    its own -- safe to share a single instance or construct fresh per call."""

    def __init__(self, config: EvidenceNarrowingConfig | None = None) -> None:
        self._config = config or DEFAULT_EVIDENCE_NARROWING_CONFIG

    def narrow(self, evidence: list[Evidence]) -> EvidenceNarrowingResult:
        if not evidence:
            return EvidenceNarrowingResult(
                retained_evidence=[],
                discarded_evidence=[],
                statistics=EvidenceNarrowingStats(
                    evidence_before=0,
                    evidence_after=0,
                    duplicates_removed=0,
                    merged_groups=0,
                    items_absorbed_by_merge=0,
                    below_confidence_removed=0,
                    per_document_cap_removed=0,
                    over_max_removed=0,
                    documents_before=0,
                    documents_after=0,
                ),
            )

        discarded: list[DiscardedEvidence] = []
        documents_before = len({item.document_id for item in evidence})

        deduped, duplicates_removed = self._deduplicate(evidence)
        discarded.extend(duplicates_removed)

        merged, merge_discards, merged_groups = self._merge_same_document(deduped)
        discarded.extend(merge_discards)

        confident, confidence_discards = self._filter_low_confidence(merged)
        discarded.extend(confidence_discards)

        capped, cap_discards = self._cap_per_document(confident)
        discarded.extend(cap_discards)

        retained, over_max_discards = self._cap_total(capped)
        discarded.extend(over_max_discards)

        stats = EvidenceNarrowingStats(
            evidence_before=len(evidence),
            evidence_after=len(retained),
            duplicates_removed=len(duplicates_removed),
            merged_groups=merged_groups,
            items_absorbed_by_merge=len(merge_discards),
            below_confidence_removed=len(confidence_discards),
            per_document_cap_removed=len(cap_discards),
            over_max_removed=len(over_max_discards),
            documents_before=documents_before,
            documents_after=len({item.document_id for item in retained}),
        )
        return EvidenceNarrowingResult(retained_evidence=retained, discarded_evidence=discarded, statistics=stats)

    # -- Stage 1: exact-text deduplication -------------------------------

    def _deduplicate(self, evidence: list[Evidence]) -> tuple[list[Evidence], list[DiscardedEvidence]]:
        seen: set[str] = set()
        kept: list[Evidence] = []
        discarded: list[DiscardedEvidence] = []
        for item in evidence:
            key = _normalized_text(item)
            if key in seen:
                discarded.append(
                    DiscardedEvidence(document_id=item.document_id, chunk_id=item.citation.chunk_id, reason="duplicate")
                )
                continue
            seen.add(key)
            kept.append(item)
        return kept, discarded

    # -- Stage 2: merge consecutive same-document, same-page chunks -----

    def _merge_same_document(
        self, evidence: list[Evidence]
    ) -> tuple[list[Evidence], list[DiscardedEvidence], int]:
        by_document: dict[int, list[Evidence]] = {}
        for item in evidence:
            by_document.setdefault(item.document_id, []).append(item)

        merged_result: list[Evidence] = []
        discarded: list[DiscardedEvidence] = []
        merged_group_count = 0

        for document_id, items in by_document.items():
            items_sorted = sorted(items, key=lambda e: (e.citation.page or 0, e.citation.chunk_id))

            groups: list[list[Evidence]] = [[items_sorted[0]]]
            for previous, current in zip(items_sorted, items_sorted[1:]):
                same_page = previous.citation.page == current.citation.page
                consecutive_chunks = current.citation.chunk_id - previous.citation.chunk_id == 1
                if same_page and consecutive_chunks:
                    groups[-1].append(current)
                else:
                    groups.append([current])

            for group in groups:
                if len(group) == 1:
                    merged_result.append(group[0])
                    continue

                merged_group_count += 1
                # Representative chosen by the same priority used for final
                # ranking (real retrieval, then decisive, then confidence),
                # not raw confidence alone -- so a group mixing a real,
                # genuinely-scored chunk with a flatly-scored remediation
                # chunk anchors its citation/origin on the more trustworthy
                # one (see _priority_score's module note).
                representative = max(group, key=_priority_score)
                merged_text = _merge_chunk_texts(
                    [item.citation.chunk_text or item.surrounding_context for item in group],
                    self._config.adjacent_chunk_merge_word_search,
                )
                surrounding_context = _truncate(merged_text, CONTEXT_CHARS)
                excerpt = _truncate(surrounding_context, EXCERPT_CHARS)
                merged_evidence = Evidence(
                    citation=Citation(
                        document_id=document_id,
                        chunk_id=representative.citation.chunk_id,
                        page=representative.citation.page,
                        relevance_score=representative.citation.relevance_score,
                        chunk_text=merged_text,
                    ),
                    document_id=document_id,
                    document_name=representative.document_name,
                    excerpt=excerpt,
                    surrounding_context=surrounding_context,
                    confidence=_clamp_confidence(max(item.confidence for item in group)),
                    metadata={
                        "source": "evidence_narrowing_merge",
                        "merged_chunk_ids": [item.citation.chunk_id for item in group],
                        "origin_source": _origin_source(representative),
                    },
                )
                merged_result.append(merged_evidence)
                discarded.extend(
                    DiscardedEvidence(
                        document_id=document_id,
                        chunk_id=item.citation.chunk_id,
                        reason=f"merged_into:{representative.citation.chunk_id}",
                    )
                    for item in group
                    if item.citation.chunk_id != representative.citation.chunk_id
                )

        return merged_result, discarded, merged_group_count

    # -- Stage 3: confidence floor (decisive evidence exempt) -----------

    def _filter_low_confidence(self, evidence: list[Evidence]) -> tuple[list[Evidence], list[DiscardedEvidence]]:
        kept: list[Evidence] = []
        discarded: list[DiscardedEvidence] = []
        for item in evidence:
            if item.confidence >= self._config.min_confidence_to_retain or _is_decisive(item):
                kept.append(item)
            else:
                discarded.append(
                    DiscardedEvidence(
                        document_id=item.document_id,
                        chunk_id=item.citation.chunk_id,
                        reason="below_confidence_threshold",
                    )
                )
        return kept, discarded

    # -- Stage 4a: per-document cap --------------------------------------

    def _cap_per_document(self, evidence: list[Evidence]) -> tuple[list[Evidence], list[DiscardedEvidence]]:
        by_document: dict[int, list[Evidence]] = {}
        for item in evidence:
            by_document.setdefault(item.document_id, []).append(item)

        kept: list[Evidence] = []
        discarded: list[DiscardedEvidence] = []
        for document_id, items in by_document.items():
            ranked = sorted(
                items, key=lambda e: (_priority_score(e), e.citation.chunk_id), reverse=True
            )
            within_cap = ranked[: self._config.max_citations_per_document]
            over_cap = ranked[self._config.max_citations_per_document :]
            kept.extend(within_cap)
            discarded.extend(
                DiscardedEvidence(document_id=document_id, chunk_id=item.citation.chunk_id, reason="per_document_cap_exceeded")
                for item in over_cap
            )
        return kept, discarded

    # -- Stage 4b: total cap ---------------------------------------------

    def _cap_total(self, evidence: list[Evidence]) -> tuple[list[Evidence], list[DiscardedEvidence]]:
        ranked = sorted(
            evidence,
            key=lambda e: (_priority_score(e), e.document_id, e.citation.chunk_id),
            reverse=True,
        )
        within_cap = ranked[: self._config.max_citations]
        over_cap = ranked[self._config.max_citations :]
        discarded = [
            DiscardedEvidence(document_id=item.document_id, chunk_id=item.citation.chunk_id, reason="exceeded_max_citations")
            for item in over_cap
        ]
        return within_cap, discarded
