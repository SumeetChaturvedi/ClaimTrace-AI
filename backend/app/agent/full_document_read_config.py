"""Centralized configuration for the Full Document Read remediation (Phase 3
Task 05), mirroring reference_expansion_config.py / focused_retrieval_config.py's
pattern: every tunable knob FullDocumentReadExecutor uses lives here, not as
inline literals in the executor itself.

A full document read is the most expensive evidence-acquisition strategy in
the architecture (every stored chunk of a document, not a bounded top-k), so
both knobs below matter: how many documents one call may open at all, and
how much evidence one call may fold into InvestigationState in total.
"""

from pydantic import BaseModel, Field


class FullDocumentReadConfig(BaseModel):
    max_documents_per_call: int = Field(
        default=2,
        description="Maximum documents one read() call will open, taken in the order the triggering SufficiencyDecision named them.",
    )
    max_new_evidence_added: int = Field(
        default=40,
        description=(
            "Maximum new Evidence items one read() call will add to InvestigationState, across all "
            "opened documents combined. A document whose full chunk set would not fit within the "
            "remaining budget is deferred whole (not partially added), so a document is only ever "
            "marked fully read once everything it contributed has actually been kept."
        ),
    )


DEFAULT_FULL_DOCUMENT_READ_CONFIG = FullDocumentReadConfig()
