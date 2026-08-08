"""The canonical document taxonomy — the single vocabulary the application
is meant to eventually use internally for document types.

DocumentType is the target; normalize_document_type() maps the current
ingestion pipeline's auto-generated doc_type slugs (see
app/ingestion/metadata.py's extract_doc_type(), a deterministic slugify of
each document's own "DOCUMENT TYPE:" header text) onto it.

Not integrated anywhere yet — ingestion, InvestigationPlanner,
RetrievalContextBuilder, and RetrievalScorer all still use the raw
ingestion-pipeline strings unchanged.

Sprint 7 Task 4 — generalized beyond one dataset: normalization used to be a
single exhaustive dict keyed on the exact 14 raw slugs observed in the
original fictional dataset (Dataset V1) — any other dataset's document
types, however sensibly named, simply returned None. That dict is kept
below, unchanged, as _LEGACY_RAW_TO_CANONICAL: it is checked first and is
the reason Dataset V1's classification is byte-for-byte unchanged by this
change. Anything not an exact match falls through to a second, general
mechanism: _CANONICAL_KEYWORDS maps each canonical DocumentType to a short
list of natural-language keywords/phrases (e.g. APPROVAL: "approval",
"determination", "certification"), and a raw slug is normalized by checking
whether any keyword appears in it, in DocumentType's own declared order
(first match wins, the same "declaration order is priority order"
convention already used by app/investigation/classifier.py). This is a
small, principled table keyed by the canonical 17-value enum itself — not a
per-dataset table of exact raw strings — so a new dataset's document types
map onto DocumentType naturally as long as its own "DOCUMENT TYPE:" header
text contains recognisable words, with no dataset-specific entries required.
"""

import re
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


# Legacy exact-match table, unchanged: the literal raw doc_type slugs
# observed in Dataset V1 (17 documents, 14 distinct raw values — see the
# Sprint 3 Research Task audit). Checked first by normalize_document_type()
# so Dataset V1's classification is guaranteed unchanged; not extended for
# any later dataset — that's _CANONICAL_KEYWORDS' job below.
_LEGACY_RAW_TO_CANONICAL: dict[str, DocumentType] = {
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

# General-purpose fallback (Sprint 7 Task 4): natural-language keywords for
# each canonical type, checked against a raw slug (underscores treated as
# spaces) via substring containment. The longest matching keyword wins
# (ties broken by DocumentType's own declaration order) rather than
# whichever type happens to be declared first — otherwise a generic
# CORRESPONDENCE keyword like "letter" would beat a more specific APPROVAL
# keyword like "determination" whenever both appear, just because
# CORRESPONDENCE is declared earlier in the enum. This is what lets e.g. an
# "approval certification letter"-shaped raw value resolve to APPROVAL
# rather than CORRESPONDENCE even though it also contains "letter".
_CANONICAL_KEYWORDS: dict[DocumentType, list[str]] = {
    DocumentType.CONTRACT: ["contract", "general conditions", "particular conditions", "employer's requirements"],
    DocumentType.SITE_INSTRUCTION: ["site instruction"],
    DocumentType.MEETING_MINUTES: ["meeting minutes", "minutes"],
    DocumentType.NOTICE: ["notice", "dissatisfaction"],
    DocumentType.VARIATION: ["variation"],
    DocumentType.DRAWING: ["drawing"],
    DocumentType.PROGRESS_REPORT: ["progress report", "daily progress", "weekly progress"],
    DocumentType.PROGRAMME: ["programme", "program", "recovery schedule", "resource loading"],
    DocumentType.PAYMENT: ["payment", "interim payment certificate", "statement", "bank transfer"],
    DocumentType.CLAIM: ["claim"],
    DocumentType.APPROVAL: ["approval", "determination", "certification", "assessment", "certificate", "close-out"],
    DocumentType.MEASUREMENT: ["measurement"],
    DocumentType.PHOTO_RECORD: ["photo"],
    DocumentType.TECHNICAL_REPORT: [
        "technical report", "report", "memorandum", "inspection", "root cause",
        "laboratory", "non-conformance", "register",
    ],
    DocumentType.PROCUREMENT: ["procurement", "delivery"],
    DocumentType.INVOICE: ["invoice"],
    DocumentType.CORRESPONDENCE: ["correspondence", "letter", "email"],
}


# Whole-word/whole-phrase matching, not plain substring containment — the
# same fix, for the same reason, as app/investigation/classifier.py's
# _KEYWORD_PATTERNS_BY_TYPE (Sprint 4 Task 02): a plain `in` check would let
# CONTRACT's keyword "contract" match inside "contractor" ("CONTRACTOR
# COMMERCIAL NOTICE" would wrongly resolve to CONTRACT instead of NOTICE).
# Compiled once at import time, mirroring that module's own pattern.
_KEYWORD_PATTERNS: dict[DocumentType, list[re.Pattern[str]]] = {
    canonical_type: [re.compile(rf"\b{re.escape(keyword)}\b") for keyword in keywords]
    for canonical_type, keywords in _CANONICAL_KEYWORDS.items()
}


def _keyword_match(raw_doc_type: str) -> DocumentType | None:
    """Normalize `raw_doc_type` to space-separated lowercase words and
    return the DocumentType whose matching keyword is longest (most
    specific), or None if nothing matches as a whole word/phrase. Ties
    (equal-length keywords from different types) resolve to whichever type
    DocumentType declares first."""
    normalized = raw_doc_type.replace("_", " ").replace("-", " ").lower()
    best_type: DocumentType | None = None
    best_keyword_len = -1
    for canonical_type in DocumentType:
        for keyword, pattern in zip(_CANONICAL_KEYWORDS.get(canonical_type, []), _KEYWORD_PATTERNS[canonical_type]):
            if len(keyword) > best_keyword_len and pattern.search(normalized):
                best_type = canonical_type
                best_keyword_len = len(keyword)
    return best_type


def normalize_document_type(raw_doc_type: str | None) -> DocumentType | None:
    """Map a raw ingestion doc_type string onto the canonical DocumentType.

    Checks the legacy Dataset V1 exact-match table first (guaranteeing
    Dataset V1's classification is unchanged), then falls back to
    keyword-in-slug matching against the canonical taxonomy itself
    (_CANONICAL_KEYWORDS) so a differently-labelled dataset's document
    types still map onto DocumentType without needing dataset-specific
    entries. Returns None for None input or a raw value that matches
    neither mechanism — still no fuzzy matching, no inference beyond
    substring containment against a fixed, principled keyword table."""
    if raw_doc_type is None:
        return None
    return _LEGACY_RAW_TO_CANONICAL.get(raw_doc_type) or _keyword_match(raw_doc_type)
