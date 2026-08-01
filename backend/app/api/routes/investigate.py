"""Public HTTP entry point into the existing Investigation Engine
(app/agent/). Deliberately thin: validates the request via the existing
InvestigationRequest model, calls InvestigationService.investigate(), and
returns its InvestigationResponse directly. No prompt construction,
retrieval, or evidence manipulation happens in this module — that's
InvestigationService's job (app/agent/service.py) and everything it
delegates to.
"""

import logging
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, status

from app.agent import InvestigationService
from app.agent.models import InvestigationRequest, InvestigationResponse
from app.agent.reasoning import ReasoningError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["investigate"])


@lru_cache
def get_investigation_service() -> InvestigationService:
    """Construct once and reuse for the process lifetime — mirrors the
    get_settings()/get_embedding_model() singleton pattern already used
    elsewhere, so GeminiProvider's cached client (app/llm/gemini_provider.py)
    actually gets reused across requests instead of rebuilt every call."""
    return InvestigationService()


@router.post("/investigate", response_model=InvestigationResponse)
async def investigate(
    request: InvestigationRequest,
    service: InvestigationService = Depends(get_investigation_service),
) -> InvestigationResponse:
    """Run an investigation. request/response are the existing
    InvestigationRequest/InvestigationResponse models, unchanged — this
    endpoint is a thin wrapper over InvestigationService.investigate()."""
    try:
        return await service.investigate(request)
    except ValueError as exc:
        # InvestigationService's own validation beyond pydantic's (e.g. a
        # whitespace-only query, which passes min_length but isn't usable).
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ReasoningError as exc:
        # The LLM provider is unavailable or misconfigured — a downstream
        # dependency failure, not a client error or a code bug.
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception as exc:
        # Anything unanticipated. Logged server-side (with traceback) so
        # it's still debuggable; never returned to the client verbatim.
        logger.exception("Unexpected error during investigation")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing the investigation.",
        ) from exc
