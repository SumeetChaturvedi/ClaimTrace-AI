"""Scenario 7 — An email received well after the event it describes.

Fictional "Kestrel Causeway" project. The message's own sent date
(2024-03-15) and the date of the incident it describes (2024-02-10) are
over a month apart — a direct test that event_date is read from the
content, never defaulted to the message's Date header.
"""

from dataset.event_eval.email_builder import build_eml
from dataset.event_eval.gold_schema import GoldEvent, GoldSourceLocator

SCENARIO_ID = "S07"

_M1_BODY = (
    "This is to formally record that on 10 February a temporary power "
    "outage halted batching plant operations for approximately six hours. "
    "We apologise that this report is delayed due to an administrative "
    "oversight on our part."
)

MESSAGES = {
    "S07-M01": build_eml(
        message_id="<s07-m01@kestrel-causeway.example>",
        from_="Priya Nandan <priya.nandan@sagara-contracting.example>",
        to="David Okonkwo <david.okonkwo@meridian-consult.example>",
        subject="Belated record — batching plant power outage",
        date="Fri, 15 Mar 2024 13:00:00 +0000",
        body=_M1_BODY,
    ),
}

NOISE_MESSAGE_KEYS: tuple[str, ...] = ()

GOLD_EVENTS = [
    GoldEvent(
        event_id="S07-E01",
        scenario_id=SCENARIO_ID,
        expected_result="attributed_assertion",
        event_type="INCIDENT_REPORTED",
        assertion_type="allegation",
        description="Contractor reports a six-hour batching plant power outage said to have occurred on 10 February, reported over a month later.",
        event_date="2024-02-10",
        event_date_basis="explicit",
        attributed_party="Priya Nandan (Sagara Contracting)",
        sources=(GoldSourceLocator("S07-M01", _M1_BODY),),
        must_not_infer=(
            "that the message's own sent date (2024-03-15) is the event date",
            "that the outage actually lasted exactly six hours, or occurred at all, given the unexplained ~5-week reporting delay",
        ),
        notes=(
            "event_date (2024-02-10, from the body) and document_sent_date (2024-03-15, "
            "from the Date header) must both be representable and must not be conflated. "
            "assertion_type stays 'allegation' rather than 'recorded_action' precisely "
            "because of the unexplained delay — the delay itself is a reason for caution, "
            "not something the extractor should silently smooth over."
        ),
    ),
]
