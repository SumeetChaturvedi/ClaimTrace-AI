"""Scenario 6 — Important evidence contained in an email attachment, not
the covering email's own body.

Fictional "Kestrel Causeway" project. Mirrors Phase 8A's real architecture:
an attachment is its own indexed source with its own text, never merged
into the covering email's body. The attachment fixture here is represented
as plain extracted text (ATTACHMENT_TEXTS), the fixture-level analog of
what app/ingestion extraction would have produced from a real PDF/DOCX
attachment — not a second .eml, since an attachment is not itself an email
message.

This scenario is also the clean test of event_date (the attachment's own
stated inspection date) vs. document_sent_date (the covering email's Date
header) staying genuinely different and non-conflated.
"""

from dataset.event_eval.email_builder import build_eml
from dataset.event_eval.gold_schema import GoldEvent, GoldSourceLocator

SCENARIO_ID = "S06"

_COVER_BODY = (
    "Please find attached our inspection report for the Pier C9 pile cap "
    "pour. Let us know if you have any queries."
)

_ATTACHMENT_TEXT = (
    "PIER C9 PILE CAP — CONCRETE PLACEMENT INSPECTION RECORD\n"
    "Inspection date: 02-Aug-2024\n"
    "Inspecting Engineer: Thomas Delacroix, Meridian Consult\n\n"
    "Concrete placement for the Pier C9 pile cap was completed and visually "
    "inspected. Minor honeycombing was noted at the north face, "
    "approximately 150mm x 80mm, requiring remedial grouting before "
    "backfill proceeds."
)

MESSAGES = {
    "S06-M01": build_eml(
        message_id="<s06-m01@kestrel-causeway.example>",
        from_="Priya Nandan <priya.nandan@sagara-contracting.example>",
        to="David Okonkwo <david.okonkwo@meridian-consult.example>",
        subject="Pier C9 pile cap — inspection report attached",
        date="Sat, 03 Aug 2024 09:00:00 +0000",
        body=_COVER_BODY,
    ),
}

# Attachment-derived fixtures: plain extracted text, not a second .eml —
# mirrors how a real PDF/DOCX attachment becomes an indexed Document with
# its own text, not an email. See dataset.py for how these are merged
# into one resolved-text registry alongside MESSAGES.
ATTACHMENT_TEXTS = {
    "S06-ATT01": _ATTACHMENT_TEXT,
}

# Who supplied the attachment, for provenance display only (not used by
# the scorer in this phase) — mirrors EmailAttachment.message_id's real
# parent-message link.
ATTACHMENT_PARENT = {
    "S06-ATT01": "S06-M01",
}

NOISE_MESSAGE_KEYS: tuple[str, ...] = ()

GOLD_EVENTS = [
    GoldEvent(
        event_id="S06-E01",
        scenario_id=SCENARIO_ID,
        expected_result="event",
        event_type="INSPECTION_RECORDED",
        assertion_type="recorded_action",
        description="Inspection records minor honeycombing at the Pier C9 pile cap north face, requiring remedial grouting.",
        event_date="2024-08-02",
        event_date_basis="explicit",
        attributed_party="Thomas Delacroix (Meridian Consult)",
        sources=(GoldSourceLocator("S06-ATT01", _ATTACHMENT_TEXT),),
        must_not_infer=(
            "that the honeycombing constitutes a contractual defect requiring remedy under any specific clause",
            "the covering email's sent date (2024-08-03) as the event date — the inspection itself occurred 2024-08-02, per the attachment's own text",
        ),
        notes=(
            "The correct source is the attachment (S06-ATT01), not the covering email "
            "(S06-M01) — a candidate citing S06-M01 as the source must fail the exact "
            "source-link check even though S06-M01 does genuinely exist and does relate to "
            "this event."
        ),
    ),
]
