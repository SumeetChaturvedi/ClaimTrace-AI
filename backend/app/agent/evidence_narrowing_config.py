"""Centralized configuration for Evidence Narrowing (Sprint 8 Task 01),
mirroring every other feature-config module's pattern (reference_expansion_config.py,
focused_retrieval_config.py, full_document_read_config.py, investigation_loop_config.py).

None of these are "always return exactly N citations" values -- they are
bounds and thresholds. The actual number of citations retained for any one
investigation emerges from how much genuinely distinct, decisive evidence
that investigation's own evidence set contains after deduplication and
same-document merging; two investigations with the same config can retain
very different counts.
"""

from pydantic import BaseModel, Field


class EvidenceNarrowingConfig(BaseModel):
    max_citations: int = Field(
        default=15,
        description="Upper bound on retained citations after all other filtering, taken by (decisive, confidence) rank.",
    )
    max_citations_per_document: int = Field(
        default=3,
        description=(
            "Upper bound on retained citations from any single document, so one document cannot "
            "dominate the final citation list -- mirrors Sprint 7's retrieval-side diversity cap, "
            "applied here at the citation layer instead."
        ),
    )
    min_confidence_to_retain: float = Field(
        default=0.0,
        description=(
            "Evidence below this confidence is dropped unless it is independently flagged decisive "
            "(see evidence_narrowing.py). Defaults to effectively disabled (0.0): a real cosine "
            "similarity score on this corpus/embedding model legitimately runs as low as ~0.3 for a "
            "genuinely correct match (this general-purpose MiniLM model was never fine-tuned on "
            "construction-claims text), so an earlier default of 0.55 was confirmed, against the real "
            "Dataset V2 benchmark, to silently discard real, ground-truth-correct evidence while never "
            "affecting remediation evidence at all (Reference Expansion / Full Document Read's fixed "
            "confidences, 0.75/0.8, always clear any reasonable floor) -- average benchmark recall rose "
            "from 0.539 to 0.706 once this stopped filtering real low-but-genuine matches. Left "
            "configurable, not removed, for a future corpus/embedding model where real similarity "
            "scores are better calibrated and a floor would do real work."
        ),
    )
    adjacent_chunk_merge_word_search: int = Field(
        default=100,
        description=(
            "Maximum number of trailing/leading words checked when detecting the literal text "
            "overlap between two consecutive same-document, same-page chunks to merge (chunking.py's "
            "sliding window guarantees consecutive chunks share real overlapping text; this bound "
            "just caps the search, it does not assume any fixed overlap size)."
        ),
    )


DEFAULT_EVIDENCE_NARROWING_CONFIG = EvidenceNarrowingConfig()
