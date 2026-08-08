"""Centralized configuration for the Focused Retrieval remediation (Phase 3
Task 04), mirroring reference_expansion_config.py's pattern: every tunable
knob FocusedRetrievalExecutor uses lives here, not as inline literals in the
executor itself.

Focused Retrieval performs exactly one additional, targeted retrieval pass
per call -- it is not a loop. The two knobs below bound the size of that one
pass: how many candidates to ask the existing retrieval pipeline for, and
how many of the genuinely-new ones to actually fold into InvestigationState.
"""

from pydantic import BaseModel, Field


class FocusedRetrievalConfig(BaseModel):
    retrieval_top_k: int = Field(
        default=10,
        description="How many results to request from the existing retrieval service in this one focused pass.",
    )
    max_new_evidence_added: int = Field(
        default=10,
        description=(
            "Maximum new Evidence items this one pass will add to InvestigationState, after "
            "removing already-visited chunks, taken in relevance-ranked order (the order the "
            "retrieval service already returns)."
        ),
    )


DEFAULT_FOCUSED_RETRIEVAL_CONFIG = FocusedRetrievalConfig()
