"""ContractContext — the canonical context object that will later drive
contract-clause retrieval (Sprint 6 Task 05).

Pure shape, no behavior — mirrors app/retrieval/context.py's RetrievalContext
precedent exactly: a model-only task, not consumed by anything yet.
Constructing one has no effect on ClauseSearchService or anything else;
no builder exists yet to produce one from an InvestigationPlan or a
question, and nothing in the codebase constructs one.
"""

from pydantic import BaseModel, Field

from app.contracts.models import ClauseTopic


class ContractContext(BaseModel):
    """Optional hints a future clause-retrieval implementation could use to
    shape a search — unused by anything today."""

    clause_numbers: list[str] = Field(
        default_factory=list, description="Specific clause numbers extracted or requested"
    )
    clause_topics: list[ClauseTopic] = Field(default_factory=list, description="Preferred contract topics")
    keywords: list[str] = Field(default_factory=list, description="Additional free-text search terms")
