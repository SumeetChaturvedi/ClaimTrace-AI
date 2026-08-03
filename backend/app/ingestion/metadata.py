"""Deterministic metadata extraction from extracted document text.

PROJECT_PLAN.md Part C step 4 specifies doc type / date / referenced-ID
extraction as an AI classification call. That step is deliberately deferred —
this module instead extracts what's mechanically parseable from the fictional
dataset's structured letter-style headers (`DOCUMENT TYPE: ...`, `DATE: ...`,
and ID-like cross-references such as `SI-088` or `Rev 1`) with no model call
involved. It's a stand-in for the real classification step, not a replacement
for it: doc_type/doc_date/referenced_ids stay overwritable by an AI step later.

Two PDF layouts exist in the frozen fictional dataset (monospace-with-newlines
vs. justified-and-wrapped), so header fields aren't reliably newline-delimited
— e.g. "DOCUMENT TYPE: Contractor Letter (Acknowledgment) LETTER REF:" can
appear on one physical line. `_DOC_TYPE_RE` therefore stops at the first
following "ALL-CAPS LABEL:" pattern rather than assuming a line break.

Document references vs. location references (Sprint 4 Task 04): the same
_ID_CODE_RE that catches genuine document identifiers (SI-088,
CTR-DMV7-0412, DPR-0703-2019, drawing IDs, ...) also catches bare
Pier/location tags (P-42, P-15) — they're the same "letters-digits-hyphens"
shape. That's a problem one level up: find_related_documents()
(app/agent/tools.py) uses referenced_ids to find related documents via
shared tokens, and a location tag like "P-42" appears in nearly every
document about the same subject, so treating it the same as a genuine
document identifier causes reference expansion to pull in most of the
corpus (Sprint 3.5 finding). extract_document_references() and
extract_location_references() split the same underlying match set into the
two concepts so callers can treat them differently; extract_referenced_ids()
is kept, unchanged in output, as the union of both — ingestion still stores
everything it always did in Document.referenced_ids, since which of those
stored ids are location tags is still derivable later via
is_location_reference() (used by find_related_documents() to exclude them
from expansion, not by ingestion itself).
"""

import re
from dataclasses import dataclass
from datetime import date, datetime

_DOC_TYPE_RE = re.compile(r"DOCUMENT TYPE:\s*(.+?)(?=\s+[A-Z][A-Z /]{2,24}:|\n|$)")
_DATE_RE = re.compile(r"\bDATE(?:\s*RANGE)?:\s*(\d{1,2}-[A-Za-z]{3,9}-\d{4})")
_ID_CODE_RE = re.compile(r"\b[A-Z0-9]{1,8}(?:-[A-Z0-9]{1,10}){1,5}\b")
_REV_RE = re.compile(r"\bRev\.?\s*\d+\b", re.IGNORECASE)

# Bare construction/location identifiers — a label letter directly followed
# by a short number (Pier P-42, P-15, ...). Deliberately narrow: only the
# shape the task calls out (Pier identifiers), not every short numeric code,
# since anything wider risks reclassifying genuine document identifiers.
_LOCATION_PATTERN = re.compile(r"\bP-\d{1,4}\b")

_DATE_FORMATS = ("%d-%b-%Y", "%d-%B-%Y")


@dataclass(frozen=True)
class ExtractedMetadata:
    doc_type: str | None
    doc_date: date | None
    referenced_ids: list[str]


def _slugify(label: str) -> str | None:
    slug = re.sub(r"[^a-z0-9]+", "_", label.strip().lower()).strip("_")
    return slug or None


def _parse_date(raw: str) -> date | None:
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def extract_doc_type(text: str) -> str | None:
    match = _DOC_TYPE_RE.search(text)
    return _slugify(match.group(1)) if match else None


def extract_doc_date(text: str) -> date | None:
    match = _DATE_RE.search(text)
    return _parse_date(match.group(1)) if match else None


def extract_document_references(text: str) -> list[str]:
    """Document identifiers only (site instructions, contractor/engineer
    letters, drawings, daily progress reports, measurement books,
    geotechnical reports, etc.) — the same ID-code/revision patterns as
    extract_referenced_ids(), minus whatever extract_location_references()
    would also match. This is the set find_related_documents()
    (app/agent/tools.py) should use to drive reference expansion."""
    ids = set(_ID_CODE_RE.findall(text))
    ids.update(m.group(0) for m in _REV_RE.finditer(text))
    location_refs = set(_LOCATION_PATTERN.findall(text))
    return sorted(ids - location_refs)


def extract_location_references(text: str) -> list[str]:
    """Bare construction/location identifiers only (e.g. Pier P-42, P-15) —
    tracked separately because, unlike a genuine document identifier, a
    shared location tag doesn't mean two documents are meaningfully related,
    just that they mention the same place. Still stored in
    Document.referenced_ids via extract_referenced_ids() below; just not
    meant to drive expansion."""
    return sorted(set(_LOCATION_PATTERN.findall(text)))


def is_location_reference(reference: str) -> bool:
    """Whether an already-extracted referenced_ids entry is a bare
    location/construction tag (e.g. "P-42") rather than a document
    identifier. Used by find_related_documents() (app/agent/tools.py) to
    exclude location tags from the reference-expansion join, since
    Document.referenced_ids stores both kinds of reference together."""
    return bool(_LOCATION_PATTERN.fullmatch(reference))


def extract_referenced_ids(text: str) -> list[str]:
    """All referenced ids — document references and location references
    together, exactly as before Sprint 4 Task 04 split the concepts apart.
    This is still what gets stored in Document.referenced_ids; nothing about
    ingestion or what's persisted has changed, only that callers needing
    just one kind of reference now have extract_document_references() /
    extract_location_references() (or is_location_reference() for an
    already-extracted id) instead of having to re-derive the distinction
    themselves."""
    return sorted(set(extract_document_references(text)) | set(extract_location_references(text)))


def extract_metadata(text: str) -> ExtractedMetadata:
    """Run all deterministic extraction rules against a document's full text."""
    return ExtractedMetadata(
        doc_type=extract_doc_type(text),
        doc_date=extract_doc_date(text),
        referenced_ids=extract_referenced_ids(text),
    )
