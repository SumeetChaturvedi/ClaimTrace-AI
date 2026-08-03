"""Contract Intelligence subsystem — canonical domain model for FIDIC
contract clauses (Sprint 6 Task 01). See app/contracts/models.py.

Not yet consumed anywhere: no parser, no retrieval integration, no planner
integration. Nothing in the codebase imports this package yet."""

from app.contracts.models import ClauseTopic, ContractClause

__all__ = [
    "ClauseTopic",
    "ContractClause",
]
