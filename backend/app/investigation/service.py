"""InvestigationPlanner — the public contract for the Investigation Planning
subsystem: given a question, produce an InvestigationPlan describing how it
should be investigated.

investigation_type, primary_entities, and likely_evidence_sources are now
real, built by reusing the existing classifier (classifier.py) and extractor
(extractor.py) plus a small fixed investigation_type -> evidence-source-types
mapping — no retrieval, no LLM, just a static lookup. expected_answer_type,
likely_contract_areas, and investigation_steps remain fixed placeholders.
Not yet integrated with InvestigationService.
"""

from app.domain.document_types import DocumentType
from app.investigation.classifier import classify_investigation_type
from app.investigation.extractor import ConstructionEntityExtractor
from app.investigation.models import InvestigationPlan

# Which canonical document types are typically relevant for each
# investigation type. Static domain knowledge, not retrieval — no documents
# are looked up here. Values are DocumentType members (Sprint 3 Task 08),
# not free text, so this speaks the same vocabulary the database now
# persists (app/ingestion/pipeline.py) and RetrievalContext expects.
#
# "evidence" previously used a wildcard-ish "All Document Types" placeholder
# that isn't a real DocumentType — per Sprint 3 Task 10, replaced with an
# empty list rather than inventing a category or adding wildcard behavior.
_EVIDENCE_SOURCES_BY_TYPE: dict[str, list[DocumentType]] = {
    "approval": [
        DocumentType.APPROVAL,
        DocumentType.CORRESPONDENCE,
        DocumentType.MEETING_MINUTES,
        DocumentType.SITE_INSTRUCTION,
    ],
    "delay": [
        DocumentType.PROGRESS_REPORT,
        DocumentType.PROGRAMME,
        DocumentType.NOTICE,
        DocumentType.MEETING_MINUTES,
    ],
    "variation": [
        DocumentType.SITE_INSTRUCTION,
        DocumentType.VARIATION,
        DocumentType.DRAWING,
        DocumentType.CORRESPONDENCE,
    ],
    "entitlement": [
        DocumentType.CONTRACT,
        DocumentType.NOTICE,
        DocumentType.SITE_INSTRUCTION,
        DocumentType.CORRESPONDENCE,
    ],
    "payment": [
        DocumentType.PAYMENT,
        DocumentType.INVOICE,
        DocumentType.CORRESPONDENCE,
    ],
    "evidence": [],
    "compliance": [
        DocumentType.CONTRACT,
        DocumentType.NOTICE,
        DocumentType.CORRESPONDENCE,
    ],
    "unknown": [],
}


class InvestigationPlanner:
    """Produces an InvestigationPlan for a question. Does not answer
    questions, retrieve evidence, or reason about anything — that's
    app/agent/'s job. Stateless; independent of retrieval, the database, the
    API layer, and any LLM provider."""

    def __init__(self, extractor: ConstructionEntityExtractor | None = None) -> None:
        self._extractor = extractor or ConstructionEntityExtractor()

    def create_plan(self, question: str) -> InvestigationPlan:
        """Classify `question`'s investigation type, extract construction
        entities using that type, look up likely evidence sources for that
        type, and assemble an InvestigationPlan. expected_answer_type,
        likely_contract_areas, and investigation_steps are still fixed
        placeholders."""
        investigation_type = classify_investigation_type(question)
        extraction = self._extractor.extract(question, investigation_type)

        return InvestigationPlan(
            goal=question,
            investigation_type=investigation_type,
            expected_answer_type="unknown",
            primary_entities=[entity.name for entity in extraction.entities],
            likely_evidence_sources=_EVIDENCE_SOURCES_BY_TYPE.get(investigation_type, []),
            likely_contract_areas=[],
            investigation_steps=["Investigation planning is not yet implemented."],
        )
