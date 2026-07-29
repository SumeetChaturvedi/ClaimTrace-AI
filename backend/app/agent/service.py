"""Orchestration entry point for the Investigation Engine.

InvestigationService is the intended seam between the API layer and future
retrieval/LLM integrations. It performs real semantic retrieval (via
app/agent/tools.py) but no reasoning yet — no LLM calls, no summarization, no
document reading — so that the API can be wired against a stable interface
while the rest of the agent loop is built out incrementally.
"""

from app.agent import tools
from app.agent.models import InvestigationRequest, InvestigationResponse


class InvestigationService:
    """Coordinates an investigation. Today: validates the request, retrieves
    relevant chunks via search_documents(), and returns them as citations
    with a placeholder answer — no reasoning over them yet. Later: will drive
    the full agent loop (plan -> search -> read -> follow references ->
    verify citations -> answer) described in PROJECT_PLAN.md Part C step 7
    and Part D."""

    async def investigate(self, request: InvestigationRequest) -> InvestigationResponse:
        """Run an investigation for `request`. Retrieves supporting evidence
        via semantic search and returns it as citations; does not read
        documents, verify citations, or call an LLM yet."""
        self._validate(request)

        citations = tools.search_documents(
            project_id=request.project_id,
            query=request.query,
            top_k=request.top_k,
        )

        if not citations:
            return InvestigationResponse(
                answer="No relevant evidence was found for this investigation question.",
                citations=[],
                reasoning_steps=[],
            )

        return InvestigationResponse(
            answer="Relevant evidence was found. Investigation reasoning is not yet implemented.",
            citations=citations,
            reasoning_steps=[],
        )

    def _validate(self, request: InvestigationRequest) -> None:
        """Defense-in-depth beyond pydantic's own field constraints on
        InvestigationRequest."""
        if not request.query.strip():
            raise ValueError("query must not be empty")
