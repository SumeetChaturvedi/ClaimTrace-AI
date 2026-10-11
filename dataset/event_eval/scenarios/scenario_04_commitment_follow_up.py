"""Scenario 4 — A promise/commitment followed by a later follow-up.

Fictional "Kestrel Causeway" project. Tests that a commitment and a later
message referencing it are extracted as two distinct events, and that the
follow-up's ASSERTION ("still not been carried out") is not elevated to an
established fact — only that the follow-up was sent is established.
"""

from dataset.event_eval.email_builder import build_eml
from dataset.event_eval.gold_schema import GoldEvent, GoldSourceLocator

SCENARIO_ID = "S04"

_M1_BODY = (
    "Further to our conversation on site this morning, I will arrange for "
    "the temporary access road repair near the batching plant to be "
    "completed by the end of next week (w/c 10 June)."
)

_M2_BODY = (
    "The temporary access road repair promised for w/c 10 June has still "
    "not been carried out, and the condition of the road is now affecting "
    "our concrete delivery schedule. Please advise on when this will be "
    "actioned."
)

MESSAGES = {
    "S04-M01": build_eml(
        message_id="<s04-m01@kestrel-causeway.example>",
        from_="David Okonkwo <david.okonkwo@meridian-consult.example>",
        to="Priya Nandan <priya.nandan@sagara-contracting.example>",
        subject="Temporary access road — batching plant",
        date="Mon, 03 Jun 2024 15:45:00 +0000",
        body=_M1_BODY,
    ),
    "S04-M02": build_eml(
        message_id="<s04-m02@kestrel-causeway.example>",
        from_="Priya Nandan <priya.nandan@sagara-contracting.example>",
        to="David Okonkwo <david.okonkwo@meridian-consult.example>",
        subject="Re: Temporary access road — batching plant",
        date="Tue, 25 Jun 2024 08:30:00 +0000",
        body=_M2_BODY,
    ),
}

NOISE_MESSAGE_KEYS: tuple[str, ...] = ()

GOLD_EVENTS = [
    GoldEvent(
        event_id="S04-E01",
        scenario_id=SCENARIO_ID,
        expected_result="event",
        event_type="COMMITMENT_MADE",
        assertion_type="commitment",
        description="Engineer's representative commits to completing the temporary access road repair by w/c 10 June.",
        event_date="2024-06-03",
        event_date_basis="explicit",
        attributed_party="David Okonkwo (Meridian Consult)",
        sources=(GoldSourceLocator("S04-M01", _M1_BODY),),
        must_not_infer=("that the repair was or was not subsequently completed",),
    ),
    GoldEvent(
        event_id="S04-E02",
        scenario_id=SCENARIO_ID,
        expected_result="attributed_assertion",
        event_type="FOLLOW_UP_SENT",
        assertion_type="allegation",
        description="Contractor asserts the promised repair has still not been carried out and requests an update.",
        event_date="2024-06-25",
        event_date_basis="explicit",
        attributed_party="Priya Nandan (Sagara Contracting)",
        sources=(GoldSourceLocator("S04-M02", _M2_BODY),),
        must_not_infer=(
            "that the repair was in fact not completed — only that the contractor asserts this",
            "any quantified impact on the concrete delivery schedule",
        ),
        notes="assertion_type stays 'allegation': whether the repair was actually outstanding is not independently established by this message alone.",
    ),
]
