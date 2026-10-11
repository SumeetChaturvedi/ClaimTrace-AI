"""Scenario 9 — A reply chain with incomplete threading headers.

Fictional "Kestrel Causeway" project. S09-M02 is a genuine reply (its body
makes that clear) but — simulating an incomplete export or a broken mail
client — carries no In-Reply-To/References headers at all. Event
extraction must not depend on thread reconstruction (Phase 8A's own
concern) to correctly source-link a message's own content: each message
is identified and scored purely by its own message_key, independent of
whether Phase 8A's threading would have linked it to anything.

S09-M02 is also deliberately content-thin (a bare acknowledgement) — it
must not produce a fabricated "acknowledgement" event just because it
exists; see NOISE_MESSAGE_KEYS.
"""

from dataset.event_eval.email_builder import build_eml
from dataset.event_eval.gold_schema import GoldEvent, GoldSourceLocator

SCENARIO_ID = "S09"

_M1_BODY = (
    "Site Instruction SI-021: You are instructed to install additional "
    "temporary shoring at the Pier C6 excavation prior to any further "
    "deepening works."
)

_M2_BODY = "Acknowledged, we will comply with SI-021."

MESSAGES = {
    "S09-M01": build_eml(
        message_id="<s09-m01@kestrel-causeway.example>",
        from_="David Okonkwo <david.okonkwo@meridian-consult.example>",
        to="Priya Nandan <priya.nandan@sagara-contracting.example>",
        subject="Site Instruction SI-021 — Pier C6 temporary shoring",
        date="Tue, 01 Oct 2024 10:00:00 +0000",
        body=_M1_BODY,
    ),
    # Deliberately NO Message-ID/In-Reply-To/References — simulates an
    # export that lost its threading headers, even though this is clearly
    # a reply by content.
    "S09-M02": build_eml(
        from_="Priya Nandan <priya.nandan@sagara-contracting.example>",
        to="David Okonkwo <david.okonkwo@meridian-consult.example>",
        subject="SI-021",
        date="Thu, 03 Oct 2024 08:15:00 +0000",
        body=_M2_BODY,
    ),
}

NOISE_MESSAGE_KEYS: tuple[str, ...] = ("S09-M02",)

GOLD_EVENTS = [
    GoldEvent(
        event_id="S09-E01",
        scenario_id=SCENARIO_ID,
        expected_result="event",
        event_type="INSTRUCTION_ISSUED",
        assertion_type="instruction",
        description="Engineer issues Site Instruction SI-021 requiring additional temporary shoring at Pier C6.",
        event_date="2024-10-01",
        event_date_basis="explicit",
        attributed_party="David Okonkwo (Meridian Consult)",
        sources=(GoldSourceLocator("S09-M01", _M1_BODY),),
        must_not_infer=("that the shoring was actually installed",),
        notes="S09-M02 is a bare acknowledgement and contributes no gold event (see NOISE_MESSAGE_KEYS) — a correct extractor finds exactly one event in this scenario, regardless of thread linkage.",
    ),
]
