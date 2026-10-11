"""Scenario 10 — Two unrelated emails with similar subjects.

Fictional "Kestrel Causeway" project. Both messages are titled "Weekly
Progress Update" but come from different, unrelated senders about
unrelated work, in different weeks. Tests that matching/scoring (and,
eventually, extraction) is driven by actual content and source identity,
never by subject-line similarity — S10-M02 must not be treated as
related to, or a duplicate of, S10-M01's event just because the subject
matches.
"""

from dataset.event_eval.email_builder import build_eml
from dataset.event_eval.gold_schema import GoldEvent, GoldSourceLocator

SCENARIO_ID = "S10"

_M1_BODY = (
    "Weekly progress update, civil works: Pier C1-C4 foundations on "
    "programme. We also wish to flag that excavation at Pier C11 has been "
    "suspended pending geotechnical review of a soft layer encountered at "
    "founding level."
)

_M2_BODY = (
    "Weekly progress update, M&E works: cable tray installation in the "
    "pump house continuing to programme. No issues to report this week."
)

MESSAGES = {
    "S10-M01": build_eml(
        message_id="<s10-m01@kestrel-causeway.example>",
        from_="Priya Nandan <priya.nandan@sagara-contracting.example>",
        to="David Okonkwo <david.okonkwo@meridian-consult.example>",
        subject="Weekly Progress Update",
        date="Mon, 04 Nov 2024 17:00:00 +0000",
        body=_M1_BODY,
    ),
    "S10-M02": build_eml(
        message_id="<s10-m02@kestrel-causeway.example>",
        from_="Femi Adeyemi <femi.adeyemi@voltline-me.example>",
        to="David Okonkwo <david.okonkwo@meridian-consult.example>",
        subject="Weekly Progress Update",
        date="Mon, 11 Nov 2024 17:30:00 +0000",
        body=_M2_BODY,
    ),
}

NOISE_MESSAGE_KEYS: tuple[str, ...] = ("S10-M02",)

GOLD_EVENTS = [
    GoldEvent(
        event_id="S10-E01",
        scenario_id=SCENARIO_ID,
        expected_result="event",
        event_type="NOTICE_SUBMITTED",
        assertion_type="recorded_action",
        description="Contractor reports excavation at Pier C11 suspended pending geotechnical review.",
        event_date="2024-11-04",
        event_date_basis="explicit",
        attributed_party="Priya Nandan (Sagara Contracting)",
        sources=(GoldSourceLocator("S10-M01", _M1_BODY),),
        must_not_infer=("the cause or eventual outcome of the geotechnical review",),
        notes=(
            "S10-M02 (same subject, unrelated M&E subcontractor, unrelated content) must not "
            "be matched to S10-E01 and must not itself produce any event — see "
            "NOISE_MESSAGE_KEYS. Scoring events by subject-line similarity would wrongly treat "
            "these as related."
        ),
    ),
]
