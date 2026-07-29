"""Investigation Engine — orchestration layer between the API, retrieval
services, and future LLM integrations. See app/agent/service.py."""

from app.agent.service import InvestigationService

__all__ = ["InvestigationService"]
