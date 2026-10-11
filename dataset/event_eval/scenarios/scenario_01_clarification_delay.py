"""Scenario 1 — Design clarification request followed by a delayed response.

Entirely fictional: "Kestrel Causeway" project, fictional firms and people.

Two real, distinct events: the request and the (much later) response. Tests
that both are extracted as SEPARATE events from separate messages, each
with its own correct date, rather than collapsed into one.
"""

from dataset.event_eval.email_builder import build_eml
from dataset.event_eval.gold_schema import GoldEvent, GoldSourceLocator

SCENARIO_ID = "S01"

_M1_BODY = (
    "We require clarification on the bearing plate detail shown on Drawing "
    "KC-203 Rev B at Pier C7 before we can proceed with the steelwork "
    "fabrication order. Please confirm the plate thickness and anchor bolt "
    "pattern as a matter of priority."
)

_M2_BODY = (
    "Apologies for the delay in responding. Please find the clarification "
    "below: the bearing plate at Pier C7 should be 25mm thick mild steel "
    "with a 4-bolt M24 anchor pattern as per the standard detail in the "
    "Employer's Requirements Appendix D. You may proceed on this basis."
)

MESSAGES = {
    "S01-M01": build_eml(
        message_id="<s01-m01@kestrel-causeway.example>",
        from_="Priya Nandan <priya.nandan@sagara-contracting.example>",
        to="Design Office <design@meridian-consult.example>",
        subject="Clarification required — Pier C7 bearing plate detail",
        date="Fri, 01 Mar 2024 09:30:00 +0000",
        body=_M1_BODY,
    ),
    "S01-M02": build_eml(
        message_id="<s01-m02@kestrel-causeway.example>",
        in_reply_to="<s01-m01@kestrel-causeway.example>",
        references="<s01-m01@kestrel-causeway.example>",
        from_="David Okonkwo <david.okonkwo@meridian-consult.example>",
        to="Priya Nandan <priya.nandan@sagara-contracting.example>",
        subject="Re: Clarification required — Pier C7 bearing plate detail",
        date="Fri, 22 Mar 2024 14:05:00 +0000",
        body=_M2_BODY,
    ),
}

NOISE_MESSAGE_KEYS: tuple[str, ...] = ()

GOLD_EVENTS = [
    GoldEvent(
        event_id="S01-E01",
        scenario_id=SCENARIO_ID,
        expected_result="event",
        event_type="CLARIFICATION_REQUESTED",
        assertion_type="request",
        description="Contractor requests clarification of the Pier C7 bearing plate detail.",
        event_date="2024-03-01",
        event_date_basis="explicit",
        attributed_party="Priya Nandan (Sagara Contracting)",
        sources=(GoldSourceLocator("S01-M01", _M1_BODY),),
        must_not_infer=(
            "that the fabrication order was actually delayed by this request",
            "any specific duration of delay caused by waiting for the answer",
        ),
        notes="The request itself is undisputed — this is the contractor's own ask, not a claim about another party.",
    ),
    GoldEvent(
        event_id="S01-E02",
        scenario_id=SCENARIO_ID,
        expected_result="event",
        event_type="CLARIFICATION_PROVIDED",
        assertion_type="recorded_action",
        description="Engineer provides the bearing plate clarification, 21 days after the request.",
        event_date="2024-03-22",
        event_date_basis="explicit",
        attributed_party="David Okonkwo (Meridian Consult)",
        sources=(GoldSourceLocator("S01-M02", _M2_BODY),),
        must_not_infer=(
            "that the 21-day gap was unreasonable or caused any programme impact",
            "that the clarification itself was technically correct or complete",
        ),
        notes="event_date is this message's own sent date (2024-03-22), not the request's date — the two events must remain separately dated.",
    ),
]
