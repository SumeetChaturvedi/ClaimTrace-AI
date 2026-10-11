"""Scenario 3 — A contractor notice/assertion requiring professional
interpretation, not automatic acceptance as fact.

Fictional "Kestrel Causeway" project. Direct test of the product's core
principle: the contractor's own characterization of a contractual
entitlement must not be elevated to an established fact by the extractor.
"""

from dataset.event_eval.email_builder import build_eml
from dataset.event_eval.gold_schema import GoldEvent, GoldSourceLocator

SCENARIO_ID = "S03"

_M1_BODY = (
    "We hereby give notice that we consider the unforeseen rock encountered "
    "during excavation at Pier C5 constitutes a change in ground conditions "
    "under Clause 4.12 of the Conditions of Contract. We are assessing our "
    "entitlement to an extension of time and additional cost and will "
    "submit full particulars in due course."
)

MESSAGES = {
    "S03-M01": build_eml(
        message_id="<s03-m01@kestrel-causeway.example>",
        from_="Priya Nandan <priya.nandan@sagara-contracting.example>",
        to="David Okonkwo <david.okonkwo@meridian-consult.example>",
        subject="Notice — Unforeseen ground conditions, Pier C5",
        date="Tue, 14 May 2024 10:15:00 +0000",
        body=_M1_BODY,
    ),
}

NOISE_MESSAGE_KEYS: tuple[str, ...] = ()

GOLD_EVENTS = [
    GoldEvent(
        event_id="S03-E01",
        scenario_id=SCENARIO_ID,
        expected_result="attributed_assertion",
        event_type="NOTICE_SUBMITTED",
        assertion_type="allegation",
        description=(
            "Contractor asserts that rock encountered at Pier C5 is an unforeseen change in "
            "ground conditions under Clause 4.12, and states it is assessing entitlement to "
            "time and cost."
        ),
        event_date="2024-05-14",
        event_date_basis="explicit",
        attributed_party="Priya Nandan (Sagara Contracting)",
        sources=(GoldSourceLocator("S03-M01", _M1_BODY),),
        must_not_infer=(
            "that the ground condition was in fact unforeseen",
            "that a change in ground conditions under Clause 4.12 is established",
            "that entitlement to extension of time or additional cost exists",
            "any specific quantum of time or cost",
        ),
        notes=(
            "The only established fact is that the contractor submitted this notice on this "
            "date. assertion_type must stay 'allegation', never 'recorded_action' — the rock "
            "being 'unforeseen' and the Clause 4.12 characterization are the contractor's own "
            "claims, not facts this message establishes."
        ),
    ),
]
