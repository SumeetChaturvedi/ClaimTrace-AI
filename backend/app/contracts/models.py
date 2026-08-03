"""Domain model for FIDIC contract clauses (Sprint 6 Task 01).

Canonical representation only — no parsing, no retrieval, no integration.
Mirrors app/domain/document_types.py's shape: pure data, no behavior, no
dependency on ingestion, retrieval, the agent layer, the database, or the
API, so future clause-parsing and clause-retrieval work can be built on top
of a stable contract without this module ever needing to change for that.

The clause set and canonical topics follow the minimum useful vocabulary
recommended in the Sprint 6 Research Task 01 (Contract Intelligence Audit):
FIDIC 1999 Red Book, sub-clause as the retrieval unit, topic as the bridge
to InvestigationPlanner's existing investigation_type vocabulary.
"""

from enum import Enum

from pydantic import BaseModel


class ClauseTopic(str, Enum):
    """Canonical topic categories a contract clause may belong to."""

    NOTICE = "NOTICE"
    DELAY = "DELAY"
    EXTENSION_OF_TIME = "EXTENSION_OF_TIME"
    VARIATION = "VARIATION"
    PAYMENT = "PAYMENT"
    CLAIMS = "CLAIMS"
    ENGINEER = "ENGINEER"
    CONTRACTOR = "CONTRACTOR"
    GENERAL = "GENERAL"


class ContractClause(BaseModel):
    """A single FIDIC contract clause (sub-clause granularity) — shape only,
    no behavior."""

    clause_number: str
    title: str
    topic: ClauseTopic
    text: str
