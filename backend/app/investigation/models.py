"""The Investigation Plan — a structured description of HOW an investigation
should be carried out, produced by InvestigationPlanner (service.py).

This is shape only, no behavior: a plan for an investigation, not the result
of one. It says nothing about answers or evidence — that remains entirely
app/agent/'s concern. Depends on nothing but Pydantic, deliberately, so it
can be reused by any future planning, agent, or reporting component without
dragging in retrieval, the database, or a specific LLM provider.
"""

from pydantic import BaseModel, Field


class InvestigationPlan(BaseModel):
    """A plan for how to investigate a question — not an answer, not
    evidence, just an upfront description of what kind of investigation this
    is and how it should be approached."""

    goal: str = Field(description="What this investigation is trying to establish")
    investigation_type: str = Field(description="The category of investigation this is, e.g. approval, timeline, causation")
    expected_answer_type: str = Field(description="The shape of answer this investigation should produce, e.g. a person, a date, a yes/no")
    primary_entities: list[str] = Field(default_factory=list, description="Key entities the investigation centers on, e.g. document IDs, piers, parties")
    likely_evidence_sources: list[str] = Field(default_factory=list, description="Document types expected to be relevant, e.g. site instructions, approval letters")
    likely_contract_areas: list[str] = Field(default_factory=list, description="Contractual topics the investigation may touch, e.g. notice periods, variations")
    investigation_steps: list[str] = Field(default_factory=list, description="The planned sequence of steps to carry out this investigation")
