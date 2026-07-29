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
"""

import re
from dataclasses import dataclass
from datetime import date, datetime

_DOC_TYPE_RE = re.compile(r"DOCUMENT TYPE:\s*(.+?)(?=\s+[A-Z][A-Z /]{2,24}:|\n|$)")
_DATE_RE = re.compile(r"\bDATE(?:\s*RANGE)?:\s*(\d{1,2}-[A-Za-z]{3,9}-\d{4})")
_ID_CODE_RE = re.compile(r"\b[A-Z0-9]{1,8}(?:-[A-Z0-9]{1,10}){1,5}\b")
_REV_RE = re.compile(r"\bRev\.?\s*\d+\b", re.IGNORECASE)

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


def extract_referenced_ids(text: str) -> list[str]:
    ids = set(_ID_CODE_RE.findall(text))
    ids.update(m.group(0) for m in _REV_RE.finditer(text))
    return sorted(ids)


def extract_metadata(text: str) -> ExtractedMetadata:
    """Run all deterministic extraction rules against a document's full text."""
    return ExtractedMetadata(
        doc_type=extract_doc_type(text),
        doc_date=extract_doc_date(text),
        referenced_ids=extract_referenced_ids(text),
    )
