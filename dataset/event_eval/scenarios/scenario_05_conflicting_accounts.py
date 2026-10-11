"""Scenario 5 — Two parties describing the same alleged happening
differently.

Fictional "Kestrel Causeway" project. The two messages are NOT a reply
chain (deliberately: real conflicting accounts often arrive via separate,
unlinked correspondence, not a thread) — they are linked only by both
describing the same alleged 18 July gate-access incident. Both sides must
be preserved as separate events; neither is the "correct" one.
"""

from dataset.event_eval.email_builder import build_eml
from dataset.event_eval.gold_schema import GoldEvent, GoldSourceLocator

SCENARIO_ID = "S05"

_M1_BODY = (
    "We wish to record that on 18 July a concrete delivery truck was "
    "refused entry at the site gate by the Engineer's security guard, "
    "resulting in a half-day delay to the Pier C8 pour. We reserve our "
    "rights in respect of any resulting cost or time impact."
)

_M2_BODY = (
    "We are aware of a claim that a concrete delivery was refused entry at "
    "the site gate on 18 July. Having reviewed our gate log for that date, "
    "no vehicle was refused entry and no incident of this kind is recorded."
)

MESSAGES = {
    "S05-M01": build_eml(
        message_id="<s05-m01@kestrel-causeway.example>",
        from_="Priya Nandan <priya.nandan@sagara-contracting.example>",
        to="David Okonkwo <david.okonkwo@meridian-consult.example>",
        subject="Gate access incident — 18 July",
        date="Fri, 19 Jul 2024 17:10:00 +0000",
        body=_M1_BODY,
    ),
    "S05-M02": build_eml(
        message_id="<s05-m02@kestrel-causeway.example>",
        from_="David Okonkwo <david.okonkwo@meridian-consult.example>",
        to="Priya Nandan <priya.nandan@sagara-contracting.example>",
        subject="Re: Gate access — query on 18 July record",
        date="Thu, 25 Jul 2024 09:50:00 +0000",
        body=_M2_BODY,
    ),
}

NOISE_MESSAGE_KEYS: tuple[str, ...] = ()

GOLD_EVENTS = [
    GoldEvent(
        event_id="S05-E01",
        scenario_id=SCENARIO_ID,
        expected_result="conflict",
        event_type="SITE_CONDITION_REPORTED",
        assertion_type="allegation",
        description="Contractor alleges a delivery truck was refused gate entry on 18 July, delaying the Pier C8 pour.",
        event_date="2024-07-18",
        event_date_basis="explicit",
        attributed_party="Priya Nandan (Sagara Contracting)",
        sources=(GoldSourceLocator("S05-M01", _M1_BODY),),
        conflict_group_id="S05-C1",
        must_not_infer=("that the refusal actually occurred", "that it caused the alleged half-day delay"),
    ),
    GoldEvent(
        event_id="S05-E02",
        scenario_id=SCENARIO_ID,
        expected_result="conflict",
        event_type="SITE_CONDITION_REPORTED",
        assertion_type="allegation",
        description="Engineer states its gate log shows no vehicle refused entry on 18 July, contradicting the contractor's account.",
        event_date="2024-07-18",
        event_date_basis="explicit",
        attributed_party="David Okonkwo (Meridian Consult)",
        sources=(GoldSourceLocator("S05-M02", _M2_BODY),),
        conflict_group_id="S05-C1",
        must_not_infer=("that the gate log is accurate or complete", "that no incident occurred"),
        notes=(
            "Both S05-E01 and S05-E02 must be extracted and preserved — the system must not "
            "resolve the conflict by keeping only one side or by silently preferring the "
            "Engineer's record over the Contractor's claim (or vice versa)."
        ),
    ),
]
