"""ContractContextBuilder — pure mapping from an InvestigationPlan onto a
ContractContext (Sprint 6 Task 06). No searching, no retrieval, no AI, no
database access — mirrors app/retrieval/context_builder.py's
RetrievalContextBuilder precedent exactly: the same InvestigationPlan,
translated into a different target context for future contract-clause
retrieval.

Field note: InvestigationPlan has no literal `search_terms` attribute.
`primary_entities` is the field that plays that role — it's exactly what
RetrievalContextBuilder already copies into RetrievalContext.search_terms.
This builder copies the same source field into ContractContext.keywords,
for the same reason.

Not integrated anywhere: nothing in the codebase constructs a
ContractContextBuilder yet.
"""

from app.contracts.context import ContractContext
from app.contracts.models import ClauseTopic
from app.investigation.models import InvestigationPlan

# Deterministic investigation_type -> preferred ClauseTopic mapping
# (Sprint 6 Task 06's own explicit mapping). Keys are exactly
# app/investigation/classifier.py's SUPPORTED_TYPES (minus "unknown",
# handled via .get()'s default below) — no other investigation type is
# handled, and none should ever be produced by the classifier.
_CLAUSE_TOPICS_BY_INVESTIGATION_TYPE: dict[str, list[ClauseTopic]] = {
    "approval": [ClauseTopic.GENERAL, ClauseTopic.ENGINEER],
    "delay": [ClauseTopic.DELAY, ClauseTopic.CLAIMS],
    "variation": [ClauseTopic.VARIATION, ClauseTopic.ENGINEER],
    "payment": [ClauseTopic.PAYMENT, ClauseTopic.CLAIMS],
    "entitlement": [ClauseTopic.CLAIMS, ClauseTopic.DELAY, ClauseTopic.VARIATION],
    "compliance": [ClauseTopic.GENERAL, ClauseTopic.CONTRACTOR],
    "evidence": [],
    "unknown": [],
}


class ContractContextBuilder:
    """Builds a ContractContext from an InvestigationPlan. Pure mapping —
    no searching, no retrieval, no AI, no database access."""

    def build(self, investigation_plan: InvestigationPlan) -> ContractContext:
        """Map investigation_plan.primary_entities -> keywords, verbatim,
        preserving order; map investigation_plan.investigation_type ->
        clause_topics via the fixed lookup above (falling back to [] for
        any type not in that lookup — a defensive guard only, since the
        classifier never produces one); clause_numbers is always [] —
        clause-number extraction is out of scope for this task."""
        return ContractContext(
            clause_numbers=[],
            clause_topics=_CLAUSE_TOPICS_BY_INVESTIGATION_TYPE.get(investigation_plan.investigation_type, []),
            keywords=investigation_plan.primary_entities,
        )
