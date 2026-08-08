"""Centralized configuration for the Investigation Loop (Phase 3 Task 06),
mirroring the per-executor config modules' pattern. The loop's own budget
knob lives here; each executor's own budget continues to live in its own
config module (reference_expansion_config.py, focused_retrieval_config.py,
full_document_read_config.py) and is respected automatically by reusing
those executors unmodified -- this module does not duplicate or override
any of them.
"""

from pydantic import BaseModel, Field


class InvestigationLoopConfig(BaseModel):
    max_iterations: int = Field(
        default=5,
        description=(
            "Upper bound on InvestigationState.iteration_count (which already counts the initial "
            "retrieval pass as iteration 1, and every remediation call as one more) before the loop "
            "stops with stopping_reason='max_iterations_reached', regardless of whether evidence is "
            "still being found."
        ),
    )


DEFAULT_INVESTIGATION_LOOP_CONFIG = InvestigationLoopConfig()
