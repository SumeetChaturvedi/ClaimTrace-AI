"""Scenario 11 — A material assertion without sufficient supporting
documentation.

Fictional "Kestrel Causeway" project. The contractor asserts a verbal
instruction was given, with no corroborating document, no named date for
the alleged instruction, and no reference any reviewer could check. This
is the clearest test of assertion_type staying "allegation" and of
event_date_basis staying "unknown" for the underlying alleged instruction
(the email's own send date is known and explicit, but that is a different
date from the alleged verbal instruction's date, which is never stated).
"""

from dataset.event_eval.email_builder import build_eml
from dataset.event_eval.gold_schema import GoldEvent, GoldSourceLocator

SCENARIO_ID = "S11"

_M1_BODY = (
    "Our records show that the Employer's Representative verbally "
    "instructed us on site to proceed with the variation works ahead of "
    "written confirmation. We are proceeding on this basis and will submit "
    "costs in due course."
)

MESSAGES = {
    "S11-M01": build_eml(
        message_id="<s11-m01@kestrel-causeway.example>",
        from_="Priya Nandan <priya.nandan@sagara-contracting.example>",
        to="David Okonkwo <david.okonkwo@meridian-consult.example>",
        subject="Proceeding with variation works — verbal instruction",
        date="Mon, 02 Dec 2024 12:00:00 +0000",
        body=_M1_BODY,
    ),
}

NOISE_MESSAGE_KEYS: tuple[str, ...] = ()

GOLD_EVENTS = [
    GoldEvent(
        event_id="S11-E01",
        scenario_id=SCENARIO_ID,
        expected_result="attributed_assertion",
        event_type="CLAIM_ASSERTED",
        assertion_type="allegation",
        description="Contractor asserts it received a verbal instruction to proceed with variation works, with no corroborating documentation and no date given for the alleged instruction.",
        event_date=None,
        event_date_basis="unknown",
        attributed_party="Priya Nandan (Sagara Contracting)",
        sources=(GoldSourceLocator("S11-M01", _M1_BODY),),
        must_not_infer=(
            "that a verbal instruction was actually given",
            "that the Employer's Representative has authority to verbally instruct variations",
            "that entitlement to the cost of the variation works exists",
            "any date for the alleged verbal instruction — only this email's own sent date (2024-12-02) is known, and that is NOT the instruction's date",
        ),
        notes=(
            "This is the sharpest test of 'an extracted event is a proposed interpretation of "
            "evidence, not an established fact' — the message is real and the assertion is "
            "real, but the underlying verbal instruction it describes is wholly uncorroborated."
        ),
    ),
]
