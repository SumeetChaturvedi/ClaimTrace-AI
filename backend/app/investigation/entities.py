"""Domain model for construction entities — the people, organizations,
structures, documents, events, and other real-world things an investigation's
evidence may reference.

Pure domain model: shape only, no extraction logic. This establishes the
public contract that future entity extraction, timeline building, evidence
linking, and contract intelligence will build on top of — none of that is
implemented here. Depends on nothing but the standard library and Pydantic,
deliberately, so it can be reused anywhere without dragging in retrieval,
the agent layer, the database, or a specific LLM provider.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EntityType(str, Enum):
    """The kinds of real-world entities an investigation may reference."""

    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION"
    PROJECT = "PROJECT"
    STRUCTURE = "STRUCTURE"
    WORK_ACTIVITY = "WORK_ACTIVITY"
    DOCUMENT = "DOCUMENT"
    EVENT = "EVENT"
    CONTRACT_REFERENCE = "CONTRACT_REFERENCE"
    DATE = "DATE"
    LOCATION = "LOCATION"
    UNKNOWN = "UNKNOWN"


class ConstructionEntity(BaseModel):
    """A single real-world entity referenced somewhere in an investigation's
    evidence — the unit future entity extraction will produce and future
    timeline/evidence-linking/contract-intelligence components will consume."""

    name: str
    entity_type: EntityType
    confidence: float = Field(ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EntityExtractionResult(BaseModel):
    """The output shape of a future entity extraction step — a collection of
    ConstructionEntity. No extraction logic here; this is shape only."""

    entities: list[ConstructionEntity] = Field(default_factory=list)
