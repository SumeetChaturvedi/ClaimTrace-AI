"""Orchestration entry point for the Investigation Engine.

InvestigationService is the intended seam between the API layer and future
retrieval/LLM integrations. It currently contains no investigation logic —
just request validation and a placeholder response — so that the API can be
wired against a stable interface before the agent loop exists.
"""

from app.agent.models import InvestigationRequest, InvestigationResponse


class InvestigationService:
    """Coordinates an investigation. Today: validates the request and returns
    a placeholder response. Later: will drive the agent loop (plan -> search
    -> read -> follow references -> verify citations -> answer) described in
    PROJECT_PLAN.md Part C step 7 and Part D."""

    async def investigate(self, request: InvestigationRequest) -> InvestigationResponse:
        """Run an investigation for `request`. Placeholder implementation:
        validates the request and returns a fixed, uncited response — no
        retrieval or reasoning is performed yet."""
        self._validate(request)

        return InvestigationResponse(
            answer="Investigation Engine is not yet implemented.",
            citations=[],
            reasoning_steps=[],
        )

    def _validate(self, request: InvestigationRequest) -> None:
        """Defense-in-depth beyond pydantic's own field constraints on
        InvestigationRequest."""
        if not request.query.strip():
            raise ValueError("query must not be empty")
