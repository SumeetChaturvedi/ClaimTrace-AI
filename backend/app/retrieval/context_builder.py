"""RetrievalContextBuilder — pure mapping from an InvestigationPlan onto a
RetrievalContext. No filtering, no transformation, no retrieval: just reads
two fields off the plan and copies them across. Not consumed by retrieval
anywhere yet.
"""

from app.investigation.models import InvestigationPlan
from app.retrieval.context import RetrievalContext


class RetrievalContextBuilder:
    """Builds a RetrievalContext from an InvestigationPlan."""

    def build(self, investigation_plan: InvestigationPlan) -> RetrievalContext:
        """Map investigation_plan.primary_entities -> search_terms and
        investigation_plan.likely_evidence_sources -> preferred_document_types,
        verbatim — no filtering or transformation."""
        return RetrievalContext(
            search_terms=investigation_plan.primary_entities,
            preferred_document_types=investigation_plan.likely_evidence_sources,
        )
