"""Centralized configuration for Reference Expansion (Phase 3 Task 03A
hardening). Every tunable knob used by tools.find_related_documents() and
ReferenceExpansionExecutor lives here, so limits/thresholds are declared once
and never repeated as inline literals elsewhere.

Phase 3 Task 03 found a real, corpus-scale problem in the reused
find_related_documents() tool: on Dataset V2, the project code ("NRB-4") and
a contract-number fragment ("2020-01") appear in the metadata box of every
one of the project's 71 documents. Both are the same letters/digits/hyphens
shape as a genuine document identifier (e.g. "VPGC-NRB4-0012"), so
extract_document_references() (unchanged, reused as-is) correctly extracts
them as references -- they just happen to be project-level boilerplate
rather than document-to-document references. A single expansion hop driven
by them pulled in 64 of the corpus's 71 documents.

max_document_frequency_ratio (below) fixes this the same way IDF-style
stopword filtering works in information retrieval: a token common to nearly
every document in a project carries no information about which *specific*
documents are related, so it's excluded from the join. This is computed live
against whatever corpus is in scope at call time -- no Dataset-V2-specific
token is named anywhere in this file or in find_related_documents(), so the
same mechanism will correctly identify a *different* project's own
boilerplate (its own project code, its own contract number) without any code
change.

The remaining fields are the expansion-safety budget requested separately:
hard caps on how much work and how much new evidence one
ReferenceExpansionExecutor.expand() call is allowed to produce, so that a
future iterative loop built on top of this executor cannot ingest an
unbounded fraction of the corpus in a single remediation step.
"""

from pydantic import BaseModel, Field


class ReferenceExpansionConfig(BaseModel):
    max_document_frequency_ratio: float = Field(
        default=0.5,
        description=(
            "A reference token present in more than this fraction of the documents in scope "
            "(the active project, when known) is treated as project/contract-level boilerplate "
            "rather than a genuine cross-document identifier, and is excluded from the expansion "
            "join before it runs."
        ),
    )
    max_references_processed: int = Field(
        default=10,
        description=(
            "Maximum unresolved references one expand() call will credit as attempted, taken in "
            "deterministic (sorted) order. Any remainder is left unresolved for a future call."
        ),
    )
    max_documents_added: int = Field(
        default=5,
        description=(
            "Maximum newly-discovered related documents one expand() call will fetch and fold "
            "into evidence, taken in deterministic (sorted-by-id) order."
        ),
    )
    max_new_evidence_added: int = Field(
        default=30,
        description=(
            "Maximum new Evidence items one expand() call will add to InvestigationState, across "
            "all newly-fetched documents combined, taken in deterministic "
            "(sorted-by-document-then-chunk-id) order."
        ),
    )


DEFAULT_REFERENCE_EXPANSION_CONFIG = ReferenceExpansionConfig()
