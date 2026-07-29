"""The Reasoning Engine — the component that decides what an investigation's
evidence means. Kept fully independent of InvestigationService
(app/agent/service.py): it takes a question and evidence in, returns a
ReasoningResult out, and knows nothing about search, tools, or the DB.
InvestigationService orchestrates the pipeline but never reasons itself.

This first implementation is deliberately not AI-powered — no LLM calls, no
prompt templates, no summarization, no contract interpretation, no fabricated
conclusions. It exists to establish the architecture and data flow that a
future LLM-backed engine will slot into behind the same reason() signature.
"""

from app.agent.models import Evidence, ReasoningResult


class ReasoningEngine:
    """Turns a question and its supporting Evidence into a ReasoningResult.
    Stateless — safe to reuse across calls, testable in isolation from
    InvestigationService."""

    def reason(self, question: str, evidence: list[Evidence]) -> ReasoningResult:
        """Deterministic baseline: rank evidence by confidence and report
        that AI-based reasoning hasn't been implemented yet. Never fabricates
        a conclusion, summarizes documents, or infers contractual meaning —
        only describes what evidence exists and how it was ranked."""
        if not evidence:
            return ReasoningResult(
                answer="No relevant evidence was found for this investigation question.",
                reasoning_steps=[
                    "Searched for relevant evidence.",
                    "No supporting evidence was found for this question.",
                ],
                supporting_evidence=[],
            )

        ranked = sorted(evidence, key=lambda item: item.confidence, reverse=True)

        answer = (
            f"Found {len(ranked)} supporting evidence item(s) for the question: "
            f"'{question}'. This is a deterministic placeholder answer, ranked by "
            "confidence — AI-based reasoning has not yet been implemented."
        )

        return ReasoningResult(
            answer=answer,
            reasoning_steps=[
                "Retrieved relevant evidence.",
                "Ranked evidence by confidence.",
                "Selected the highest-confidence supporting evidence.",
            ],
            supporting_evidence=[item.citation for item in ranked],
        )
