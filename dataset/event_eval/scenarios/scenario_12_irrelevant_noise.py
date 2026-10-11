"""Scenario 12 — Irrelevant correspondence that should not produce
significant events.

Fictional "Kestrel Causeway" project. Purely social/administrative
content. This scenario's gold event list is intentionally empty — the
entire message is noise. A correct extractor abstains completely; any
extracted event here is a false positive.
"""

from dataset.event_eval.email_builder import build_eml

SCENARIO_ID = "S12"

_M1_BODY = (
    "Thanks for organising the site visit yesterday — good to catch up in "
    "person for once. See you at the progress meeting next Tuesday."
)

MESSAGES = {
    "S12-M01": build_eml(
        message_id="<s12-m01@kestrel-causeway.example>",
        from_="David Okonkwo <david.okonkwo@meridian-consult.example>",
        to="Priya Nandan <priya.nandan@sagara-contracting.example>",
        subject="Good to catch up",
        date="Mon, 06 Jan 2025 16:45:00 +0000",
        body=_M1_BODY,
    ),
}

# The entire scenario is noise — every message key here must produce zero
# gold events (expected_result = "no_event", represented by GOLD_EVENTS
# being empty rather than by a placeholder row — see gold_schema.py's
# module docstring).
NOISE_MESSAGE_KEYS: tuple[str, ...] = ("S12-M01",)

GOLD_EVENTS = []
