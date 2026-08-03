"""Deterministic document-level timeline reconstruction (Sprint 5 Task 01;
event labels made DocumentType-driven in Sprint 5 Task 02; querying added in
Sprint 5 Task 03 via TimelineQueryService; text rendering added in Sprint 5
Task 04 via TimelineFormatter).

The Sprint 5 Research Task (Timeline Reconstruction Audit) confirmed every
document in the dataset already carries a usable doc_date, that sorting
documents by that field alone produces a chronologically consistent
sequence, and that PROJECT_PLAN.md's own original design for chronology
building is exactly this: no new parsing, no LLM call, just sorting
already-extracted facts by their already-extracted date. This module is
that first step — infrastructure only, not wired into any investigation
flow yet.

No LLM, no summarization, no inference, no filename parsing: event_label is
looked up from a single static DocumentType -> label mapping
(_EVENT_LABEL_BY_TYPE), keyed only on the document's own canonical doc_type
(Sprint 3 Task 08/09) — never its text, filename, or any other content.
DocumentType values with no document in the current dataset (CONTRACT,
VARIATION, PROGRAMME, PAYMENT, CLAIM) are still mapped, so the table is
complete regardless of what's actually been ingested. A doc_type that's
None, or a raw string that isn't a valid canonical DocumentType, falls back
to the generic "Project Event" label rather than raising.
"""

from datetime import date

from pydantic import BaseModel, Field

from app.db.models import Document
from app.domain.document_types import DocumentType

_DEFAULT_EVENT_LABEL = "Project Event"

# One label per canonical DocumentType (Sprint 5 Task 02) — exhaustive over
# the enum, not just the types the current dataset happens to contain, so
# the mapping stays complete as new document types are ingested.
_EVENT_LABEL_BY_TYPE: dict[DocumentType, str] = {
    DocumentType.CONTRACT: "Contract Executed",
    DocumentType.CORRESPONDENCE: "Correspondence Sent",
    DocumentType.SITE_INSTRUCTION: "Site Instruction Issued",
    DocumentType.MEETING_MINUTES: "Meeting Held",
    DocumentType.NOTICE: "Contractor Notice Submitted",
    DocumentType.VARIATION: "Variation Issued",
    DocumentType.DRAWING: "Drawing Issued",
    DocumentType.PROGRESS_REPORT: "Progress Report Recorded",
    DocumentType.PROGRAMME: "Programme Issued",
    DocumentType.PAYMENT: "Payment Recorded",
    DocumentType.CLAIM: "Claim Submitted",
    DocumentType.APPROVAL: "Approval Granted",
    DocumentType.MEASUREMENT: "Measurement Recorded",
    DocumentType.PHOTO_RECORD: "Site Photo Recorded",
    DocumentType.TECHNICAL_REPORT: "Technical Report Issued",
    DocumentType.PROCUREMENT: "Material Delivery Recorded",
    DocumentType.INVOICE: "Invoice Issued",
}


def _event_label_for(doc_type: str | None) -> str:
    """Look up the deterministic event label for a document's raw doc_type
    string. Returns _DEFAULT_EVENT_LABEL for None or any value that isn't a
    valid canonical DocumentType (e.g. a pre-Task-09 legacy raw slug) —
    graceful, not an error, matching the same pattern RetrievalScorer's
    _as_document_type() already uses for the same reconstruction."""
    if doc_type is None:
        return _DEFAULT_EVENT_LABEL
    try:
        canonical = DocumentType(doc_type)
    except ValueError:
        return _DEFAULT_EVENT_LABEL
    return _EVENT_LABEL_BY_TYPE[canonical]


class TimelineEvent(BaseModel):
    """One document's place in a chronology — shape only, no behavior.
    event_label is deterministically derived from document_type alone (see
    _EVENT_LABEL_BY_TYPE), never from document text, filename, or an LLM."""

    document_id: int
    document_date: date | None = Field(description="Mirrors Document.doc_date; None if a document has no extracted date")
    document_type: str | None = Field(description="Mirrors Document.doc_type")
    event_label: str = Field(description="Deterministic label derived solely from document_type — see _EVENT_LABEL_BY_TYPE")


class TimelineBuilder:
    """Builds a chronological timeline from documents already gathered
    elsewhere. Pure bookkeeping: one TimelineEvent per document, sorted
    ascending by document_date — no filtering, no scoring, no reasoning."""

    def build(self, documents: list[Document]) -> list[TimelineEvent]:
        """Return one TimelineEvent per document in `documents`, sorted
        ascending by document_date. Uses Python's stable sort, so documents
        sharing the same date (or missing one entirely) keep their relative
        input order rather than being reordered arbitrarily."""
        events = [
            TimelineEvent(
                document_id=document.id,
                document_date=document.doc_date,
                document_type=document.doc_type,
                event_label=_event_label_for(document.doc_type),
            )
            for document in documents
        ]
        return sorted(events, key=_sort_key)


def _sort_key(event: TimelineEvent) -> tuple[int, date]:
    """Sort ascending by document_date; a missing date sorts last rather
    than crashing the comparison (date has no natural ordering against
    None)."""
    if event.document_date is None:
        return (1, date.max)
    return (0, event.document_date)


def _index_of(timeline: list[TimelineEvent], document_id: int) -> int | None:
    """Position of the event for `document_id` within `timeline`, or None if
    no event for that id is present. A pure lookup over the list as given —
    assumes `timeline` is already sorted, never re-sorts or re-derives
    anything from dates."""
    for index, event in enumerate(timeline):
        if event.document_id == document_id:
            return index
    return None


class TimelineQueryService:
    """Deterministic, position-based queries over an already-built,
    already-sorted timeline. Pure list operations only: no database access,
    no re-sorting, no date comparison or inference — "before"/"after"/
    "between" are defined entirely by each event's position in the list
    `TimelineBuilder.build()` already sorted, not recomputed from
    document_date here. Not wired into any investigation flow yet — query
    infrastructure only (Sprint 5 Task 03)."""

    def events_before(self, timeline: list[TimelineEvent], document_id: int) -> list[TimelineEvent]:
        """Every event positioned before `document_id`'s event. Returns []
        if `document_id` has no event in `timeline` (including an empty
        timeline) — never raises."""
        index = _index_of(timeline, document_id)
        if index is None:
            return []
        return timeline[:index]

    def events_after(self, timeline: list[TimelineEvent], document_id: int) -> list[TimelineEvent]:
        """Every event positioned after `document_id`'s event. Returns [] if
        `document_id` has no event in `timeline` — never raises."""
        index = _index_of(timeline, document_id)
        if index is None:
            return []
        return timeline[index + 1 :]

    def events_between(
        self,
        timeline: list[TimelineEvent],
        start_document_id: int,
        end_document_id: int,
    ) -> list[TimelineEvent]:
        """Every event from `start_document_id`'s position to
        `end_document_id`'s position, inclusive of both ends. Order-agnostic
        in which id comes first in `timeline` — the earlier-positioned id is
        always treated as the start of the slice. Returns [] if either id
        has no event in `timeline` — never raises."""
        start_index = _index_of(timeline, start_document_id)
        end_index = _index_of(timeline, end_document_id)
        if start_index is None or end_index is None:
            return []
        lower, upper = sorted((start_index, end_index))
        return timeline[lower : upper + 1]


class TimelineFormatter:
    """Deterministic, one-line-per-event text rendering of a timeline —
    formatting only, no summarization, no merging, no date inference, no
    document text, no AI. Prepares timeline context for future reasoning
    (Sprint 5 Task 04) but isn't wired into any reasoning/investigation flow
    yet."""

    def format(self, events: list[TimelineEvent]) -> str:
        """Render `events` as "YYYY-MM-DD — Event Label" lines, one per
        event, joined with newlines, in exactly the order given (never
        re-sorted — callers pass an already-ordered timeline). A missing
        document_date renders as "Unknown Date" rather than being inferred
        or omitted. Returns "" for an empty list."""
        if not events:
            return ""
        return "\n".join(
            f"{event.document_date.isoformat() if event.document_date is not None else 'Unknown Date'} — {event.event_label}"
            for event in events
        )
