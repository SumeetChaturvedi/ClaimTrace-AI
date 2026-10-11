"""Scenario 8 — An event with an ambiguous or missing date.

Fictional "Kestrel Causeway" project. "Earlier this month" does not name a
specific date. The correct gold annotation is event_date=None,
event_date_basis="unknown" — a candidate that confidently guesses a
specific calendar date here must fail the date-accuracy check, and a
candidate that quietly reuses the message's own Date header as the event
date must also fail (that would be event_date_basis="explicit" when the
true basis is "unknown").
"""

from dataset.event_eval.email_builder import build_eml
from dataset.event_eval.gold_schema import GoldEvent, GoldSourceLocator

SCENARIO_ID = "S08"

_M1_BODY = (
    "We experienced a dispute with the adjacent landowner over access "
    "rights earlier this month, which held up mobilisation of the piling "
    "rig for several days. This has now been resolved and the rig is on "
    "site."
)

MESSAGES = {
    "S08-M01": build_eml(
        message_id="<s08-m01@kestrel-causeway.example>",
        from_="Priya Nandan <priya.nandan@sagara-contracting.example>",
        to="David Okonkwo <david.okonkwo@meridian-consult.example>",
        subject="Piling rig mobilisation — update",
        date="Fri, 20 Sep 2024 11:30:00 +0000",
        body=_M1_BODY,
    ),
}

NOISE_MESSAGE_KEYS: tuple[str, ...] = ()

GOLD_EVENTS = [
    GoldEvent(
        event_id="S08-E01",
        scenario_id=SCENARIO_ID,
        expected_result="unresolved_ambiguity",
        event_type="INCIDENT_REPORTED",
        assertion_type="allegation",
        description="Contractor reports an access-rights dispute with an adjacent landowner, said to have delayed piling rig mobilisation by several days, with no specific date given.",
        event_date=None,
        event_date_basis="unknown",
        attributed_party="Priya Nandan (Sagara Contracting)",
        sources=(GoldSourceLocator("S08-M01", _M1_BODY),),
        must_not_infer=(
            "a specific calendar date for 'earlier this month' (e.g. defaulting to the 1st, or to the message's own Date header)",
            "an exact number of days of delay — the source only says 'several'",
            "that the dispute was resolved on any particular date",
        ),
        notes="Correct extraction means correctly representing the ambiguity, not resolving it with a plausible guess.",
    ),
]
