"""The canonical document taxonomy — the single vocabulary the application
is meant to eventually use internally for document types.

DocumentType is the target; normalize_document_type() maps the current
ingestion pipeline's auto-generated doc_type slugs (see
app/ingestion/metadata.py's extract_doc_type(), a deterministic slugify of
each document's own "DOCUMENT TYPE:" header text) onto it. This is
deliberately narrow: only the values actually observed in the current
fictional dataset (17 documents, 14 distinct raw doc_type values — see the
Sprint 3 Research Task audit) are mapped. Nothing is inferred or
fuzzy-matched; unmapped values return None rather than guessing.

Not integrated anywhere yet — ingestion, InvestigationPlanner,
RetrievalContextBuilder, and RetrievalScorer all still use the raw
ingestion-pipeline strings unchanged.
"""

from enum import Enum


class DocumentType(str, Enum):
    """Canonical construction-claims document categories."""

    CONTRACT = "CONTRACT"
    CORRESPONDENCE = "CORRESPONDENCE"
    SITE_INSTRUCTION = "SITE_INSTRUCTION"
    MEETING_MINUTES = "MEETING_MINUTES"
    NOTICE = "NOTICE"
    VARIATION = "VARIATION"
    DRAWING = "DRAWING"
    PROGRESS_REPORT = "PROGRESS_REPORT"
    PROGRAMME = "PROGRAMME"
    PAYMENT = "PAYMENT"
    CLAIM = "CLAIM"
    APPROVAL = "APPROVAL"
    MEASUREMENT = "MEASUREMENT"
    PHOTO_RECORD = "PHOTO_RECORD"
    TECHNICAL_REPORT = "TECHNICAL_REPORT"
    PROCUREMENT = "PROCUREMENT"
    INVOICE = "INVOICE"


# Explicit, exhaustive mapping from the current dataset's raw ingestion
# doc_type values to the canonical taxonomy. Not a general-purpose
# normalizer — only these exact keys are recognized.
_RAW_TO_CANONICAL: dict[str, DocumentType] = {
    "approval_certification_letter": DocumentType.APPROVAL,
    "contractor_letter": DocumentType.CORRESPONDENCE,
    "contractor_letter_acknowledgment": DocumentType.CORRESPONDENCE,
    "internal_email_contractor_internal_correspondence": DocumentType.CORRESPONDENCE,
    "meeting_minutes": DocumentType.MEETING_MINUTES,
    "site_instruction": DocumentType.SITE_INSTRUCTION,
    "contractor_notice_cost_time_impact": DocumentType.NOTICE,
    "structural_drawing": DocumentType.DRAWING,
    "daily_progress_report": DocumentType.PROGRESS_REPORT,
    "geotechnical_investigation_report": DocumentType.TECHNICAL_REPORT,
    "joint_measurement_record_measurement_book_extract": DocumentType.MEASUREMENT,
    "procurement_delivery_record": DocumentType.PROCUREMENT,
    "site_photograph_log_text_description_no_images_in_this": DocumentType.PHOTO_RECORD,
    "invoice": DocumentType.INVOICE,
}


def normalize_document_type(raw_doc_type: str | None) -> DocumentType | None:
    """Map a raw ingestion doc_type string onto the canonical DocumentType
    via explicit lookup only (no fuzzy matching, no regex, no inference).
    Returns None for None input or any value outside the current dataset's
    known set."""
    if raw_doc_type is None:
        return None
    return _RAW_TO_CANONICAL.get(raw_doc_type)
