"""Aggregates all 12 scenario modules into one flat, validated registry.

Deliberately independent of backend/app/ (see gold_schema.py's module
docstring) — .eml bodies are resolved to plain text here using Python's
own stdlib `email` package directly, the same technique
backend/app/email_ingestion/parsing.py uses, not an import of that module.

Validates, at import time, that every GoldSourceLocator's `passage` is a
genuine, verbatim substring of its claimed source's actual resolved text —
this is what gold_schema.py's module docstring promises ("a gold
annotation can never itself drift from the fixture text it claims to
cite"). A gold authoring mistake (a passage that doesn't actually appear
in the message/attachment it claims to) fails loudly here, at dataset
load time, rather than silently corrupting the evaluation.
"""

from __future__ import annotations

import email
import email.policy
from dataclasses import dataclass

from dataset.event_eval.gold_schema import GoldEvent
from dataset.event_eval.scenarios import (
    scenario_01_clarification_delay as s01,
    scenario_02_instruction_revised_drawing as s02,
    scenario_03_contractor_notice as s03,
    scenario_04_commitment_follow_up as s04,
    scenario_05_conflicting_accounts as s05,
    scenario_06_attachment_evidence as s06,
    scenario_07_late_received_email as s07,
    scenario_08_ambiguous_date as s08,
    scenario_09_broken_threading as s09,
    scenario_10_similar_subjects as s10,
    scenario_11_unsupported_assertion as s11,
    scenario_12_irrelevant_noise as s12,
)

_SCENARIO_MODULES = [s01, s02, s03, s04, s05, s06, s07, s08, s09, s10, s11, s12]


@dataclass(frozen=True)
class EventEvalDataset:
    scenario_ids: tuple[str, ...]
    gold_events: tuple[GoldEvent, ...]
    message_scenario: dict[str, str]  # message_key (email or attachment) -> scenario_id
    resolved_text: dict[str, str]  # message_key -> plain text body, for passage/substring verification
    noise_message_keys: frozenset[str]  # message_keys that must never produce an event
    attachment_parent: dict[str, str]  # attachment message_key -> its originating email's message_key


def _extract_plain_text(raw_eml: bytes) -> str:
    """Resolve a raw .eml's plain-text body — the same `get_body` approach
    backend/app/email_ingestion/parsing.py uses, inlined here (not
    imported) to keep this evaluation harness independent of the
    production application. Every scenario fixture in this dataset is
    plain-text-only by construction, so no HTML-fallback branch is needed
    here (unlike the production parser, which must handle real-world
    HTML-only mail)."""
    msg = email.message_from_bytes(raw_eml, policy=email.policy.default)
    body_part = msg.get_body(preferencelist=("plain",))
    if body_part is None:
        raise ValueError("fixture .eml has no plain-text body — check the scenario module")
    return body_part.get_content()


def load_dataset() -> EventEvalDataset:
    scenario_ids: list[str] = []
    gold_events: list[GoldEvent] = []
    message_scenario: dict[str, str] = {}
    resolved_text: dict[str, str] = {}
    noise_message_keys: set[str] = set()
    attachment_parent: dict[str, str] = {}

    for module in _SCENARIO_MODULES:
        scenario_id = module.SCENARIO_ID
        scenario_ids.append(scenario_id)

        for message_key, raw_eml in module.MESSAGES.items():
            if message_key in resolved_text:
                raise ValueError(f"duplicate message_key across scenarios: {message_key}")
            message_scenario[message_key] = scenario_id
            resolved_text[message_key] = _extract_plain_text(raw_eml)

        attachment_texts = getattr(module, "ATTACHMENT_TEXTS", {})
        for message_key, text in attachment_texts.items():
            if message_key in resolved_text:
                raise ValueError(f"duplicate message_key across scenarios: {message_key}")
            message_scenario[message_key] = scenario_id
            resolved_text[message_key] = text

        attachment_parent.update(getattr(module, "ATTACHMENT_PARENT", {}))
        noise_message_keys.update(module.NOISE_MESSAGE_KEYS)
        gold_events.extend(module.GOLD_EVENTS)

    # Gold-authoring integrity check (see module docstring): every gold
    # passage must be a real, verbatim substring of its claimed source's
    # actual resolved text.
    for event in gold_events:
        for source in event.sources:
            if source.message_key not in resolved_text:
                raise ValueError(f"{event.event_id} cites unknown message_key {source.message_key!r}")
            if source.passage not in resolved_text[source.message_key]:
                raise ValueError(
                    f"{event.event_id}'s passage for {source.message_key!r} is not a verbatim "
                    "substring of that source's actual fixture text — gold annotation has "
                    "drifted from the fixture it claims to cite"
                )

    # A message_key must not be both a real gold source and a declared
    # noise key — that would be a self-contradictory scenario definition.
    sourced_keys = {source.message_key for event in gold_events for source in event.sources}
    contradictions = sourced_keys & noise_message_keys
    if contradictions:
        raise ValueError(f"message_key(s) both cited as a gold source and declared noise: {sorted(contradictions)}")

    return EventEvalDataset(
        scenario_ids=tuple(scenario_ids),
        gold_events=tuple(gold_events),
        message_scenario=message_scenario,
        resolved_text=resolved_text,
        noise_message_keys=frozenset(noise_message_keys),
        attachment_parent=attachment_parent,
    )


DATASET = load_dataset()
