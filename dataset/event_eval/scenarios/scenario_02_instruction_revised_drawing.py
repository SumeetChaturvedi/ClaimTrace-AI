"""Scenario 2 — An instruction followed by a revised drawing.

Fictional "Kestrel Causeway" project. Tests that an instruction and the
document issued in response to it are extracted as two distinct, correctly
ordered events, each attributed to the party that actually issued it.
"""

from dataset.event_eval.email_builder import build_eml
from dataset.event_eval.gold_schema import GoldEvent, GoldSourceLocator

SCENARIO_ID = "S02"

_M1_BODY = (
    "Site Instruction SI-014: You are instructed to revise the foundation "
    "layout at Pier C3 to accommodate the relocated utility duct identified "
    "during excavation. Please issue a revised drawing for our review within "
    "10 working days."
)

_M2_BODY = (
    "Please find attached, for your records, Drawing DWG-203 Revision C, "
    "issued in response to Site Instruction SI-014. The foundation layout "
    "at Pier C3 has been revised to route around the relocated utility duct."
)

MESSAGES = {
    "S02-M01": build_eml(
        message_id="<s02-m01@kestrel-causeway.example>",
        from_="David Okonkwo <david.okonkwo@meridian-consult.example>",
        to="Priya Nandan <priya.nandan@sagara-contracting.example>",
        subject="Site Instruction SI-014 — Pier C3 foundation layout",
        date="Tue, 02 Apr 2024 11:00:00 +0000",
        body=_M1_BODY,
    ),
    "S02-M02": build_eml(
        message_id="<s02-m02@kestrel-causeway.example>",
        in_reply_to="<s02-m01@kestrel-causeway.example>",
        references="<s02-m01@kestrel-causeway.example>",
        from_="Drawing Office <drawings@sagara-contracting.example>",
        to="David Okonkwo <david.okonkwo@meridian-consult.example>",
        subject="Re: Site Instruction SI-014 — Pier C3 foundation layout",
        date="Wed, 10 Apr 2024 16:20:00 +0000",
        body=_M2_BODY,
    ),
}

NOISE_MESSAGE_KEYS: tuple[str, ...] = ()

GOLD_EVENTS = [
    GoldEvent(
        event_id="S02-E01",
        scenario_id=SCENARIO_ID,
        expected_result="event",
        event_type="INSTRUCTION_ISSUED",
        assertion_type="instruction",
        description="Engineer issues Site Instruction SI-014 to revise the Pier C3 foundation layout.",
        event_date="2024-04-02",
        event_date_basis="explicit",
        attributed_party="David Okonkwo (Meridian Consult)",
        sources=(GoldSourceLocator("S02-M01", _M1_BODY),),
        must_not_infer=("that the utility duct relocation was itself a compensable or unforeseen event",),
    ),
    GoldEvent(
        event_id="S02-E02",
        scenario_id=SCENARIO_ID,
        expected_result="event",
        event_type="DRAWING_REVISED",
        assertion_type="recorded_action",
        description="Contractor's drawing office issues Drawing DWG-203 Revision C in response to SI-014.",
        event_date="2024-04-10",
        event_date_basis="explicit",
        attributed_party="Drawing Office (Sagara Contracting)",
        sources=(GoldSourceLocator("S02-M02", _M2_BODY),),
        must_not_infer=(
            "that the revised drawing fully and correctly complies with SI-014's requirements",
            "that the revision was issued within the 10-working-day period SI-014 requested",
        ),
    ),
]
