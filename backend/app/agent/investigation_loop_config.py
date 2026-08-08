"""Centralized configuration for the Investigation Loop (Phase 3 Task 06),
mirroring the per-executor config modules' pattern. The loop's own budget
knob lives here; each executor's own budget continues to live in its own
config module (reference_expansion_config.py, focused_retrieval_config.py,
full_document_read_config.py) and is respected automatically by reusing
those executors unmodified -- this module does not duplicate or override
any of them.

max_iterations default (Sprint 8 Task 02): measured against the complete
10-question benchmark corpus (project_id=2, 85 documents) at six values (5,
7, 10, 12, 15, 20), tracking two distinct recall metrics -- see
dataset/scripts/tune_investigation_loop.py. `recall_raw` (did the loop ever
visit the expected document) climbs cleanly from 0.765 at 5 iterations to
1.000 at 15+, exactly as Scenario 10's finding suggested. But
`recall_narrowed` (did that document's evidence survive Evidence Narrowing's
fixed 15-citation cap to actually reach the final answer -- what a real
user sees) does NOT climb with it: it is highest at 5-7 iterations (0.675)
and *drops* to a flat 0.650 from 10 iterations onward, with the final
benchmark pass rate flat at 8/10 across all six tested values. Once the
loop gathers enough raw evidence, additional real-retrieval-tier evidence
increasingly crowds out the same expected documents under Evidence
Narrowing's fixed cap -- Evidence Narrowing was itself validated (Sprint 8
Task 01) against the smaller evidence pool the old default of 5 produces,
and does not visibly benefit from a much larger one. Since Evidence
Narrowing is out of this task's scope to change, the right default is the
smallest value that reaches the best *narrowed* outcome, not the smallest
value that reaches "complete" raw retrieval convergence. 7 matches 5's
narrowed recall/pass rate exactly while reaching meaningfully higher raw
recall (0.815 vs 0.765, cheap headroom against future corpus growth) for a
negligible cost (+24 evidence items, +1.5% prompt size, no measurable
latency change) -- see IMPLEMENTATION_LOG.md for the full comparison table.
"""

from pydantic import BaseModel, Field


class InvestigationLoopConfig(BaseModel):
    max_iterations: int = Field(
        default=7,
        description=(
            "Upper bound on InvestigationState.iteration_count (which already counts the initial "
            "retrieval pass as iteration 1, and every remediation call as one more) before the loop "
            "stops with stopping_reason='max_iterations_reached', regardless of whether evidence is "
            "still being found."
        ),
    )


DEFAULT_INVESTIGATION_LOOP_CONFIG = InvestigationLoopConfig()
