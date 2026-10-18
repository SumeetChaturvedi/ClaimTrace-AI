"""EventExtractor — the Phase 8B.2 component that turns an investigation's
own already-retrieved evidence into zero or more ExtractedEvent candidates.

Deliberately a SEPARATE component from TimelineBuilder
(app/investigation/timeline.py): TimelineBuilder is a small, deterministic,
no-LLM document-level chronology (one entry per cited document, sorted by
Document.doc_date) that already exists and is unchanged by this module.
EventExtractor is LLM-backed, event-level (a single document/email may yield
several events spanning past/current/future/request content), and investigation-
scoped — it runs once per investigation, not once per email import, and never
touches TimelineBuilder, InvestigationResponse.timeline, or retrieval behavior.

Structurally this mirrors ReasoningEngine (app/agent/reasoning.py): depends
only on the LLMProvider interface, builds its prompt via PromptBuilder
(never constructs prompt text itself), and raises one clean, provider-
agnostic exception type. The critical difference is what happens to the
provider's response: ReasoningEngine's answer string is returned to the
caller verbatim and is never treated as structured data, whereas
EventExtractor's response IS expected to be structured (a JSON array) and is
therefore parsed and then deterministically re-verified against the same
evidence that was supplied — document_id/chunk_id/excerpt are never trusted
on the model's word alone (see _validate_candidate below), mirroring the
existing verify_citations() defense-in-depth pattern
(app/agent/citation_verification.py) one level earlier in the pipeline: a
citation is checked against real DocumentChunk rows; an extracted event's
source is checked against the real evidence this very call was given.

Source identifiers are always (document_id, chunk_id) — the same stable
locator Citation already uses — never thread_id, which app/email_ingestion/
threading.py can reassign via a later thread merge (see EmailThread's own
docstring); a durable event source must not depend on something mutable.

Failure isolation: extract() raises EventExtractionError on any failure
(no provider configured, the generate() call itself failing, or a response
that cannot be parsed as a JSON array at all) — never silently returns []
for a failure it should instead report. A response that parses but whose
individual candidates are partly invalid is NOT a failure: each candidate
is validated independently, and invalid ones are dropped while valid ones
are still returned (see _validate_candidates). It is the caller's
responsibility (app/agent/service.py's investigate()) to catch
EventExtractionError and keep it from failing the overall investigation —
this module itself makes no such allowance; it either returns a valid list
or raises.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field

from app.agent.models import ASSERTION_TYPES, DATE_BASIS_VALUES, EVENT_TYPES, Evidence, ExtractedEvent
from app.agent.prompt_builder import PromptBuilder, SourceContext
from app.db.models import Document, EmailMessage
from app.db.session import get_session_factory
from app.llm.gemini_provider import GeminiProvider
from app.llm.provider import LLMProvider, LLMProviderError

logger = logging.getLogger(__name__)

# Extraction-specific output budget (Phase 8B.2 Quality Remediation),
# threaded through Prompt.max_output_tokens (app/llm/provider.py) rather
# than raising the shared GeminiProvider.MAX_OUTPUT_TOKENS constant
# ReasoningEngine also relies on. A structured JSON array of several
# events, each with a verbatim excerpt, legitimately needs more room than
# a prose answer; this was sized against the production evaluation's own
# observed truncation (6-9 events cut off at 1024 tokens) with headroom,
# not tuned to any specific fixture's exact size.
EVENT_EXTRACTION_MAX_OUTPUT_TOKENS = 4096

# A markdown fence can wrap the array despite the prompt's "no markdown
# fences" instruction — models don't always follow format instructions
# exactly. This finds the opening `[` to start scanning from; it does not
# require a matching closing `]` (see _parse_json_array), because even the
# raised extraction-specific budget above is still finite and can still be
# exceeded by a sufficiently evidence-rich investigation, truncating
# mid-object.
_ARRAY_START_PATTERN = re.compile(r"\[")

_REQUIRED_KEYS = {"document_id", "chunk_id", "excerpt"}


@dataclass(frozen=True)
class ExtractionResult:
    """extract()'s return shape (Phase 8B.2 Quality Remediation) —
    distinguishes a complete extraction from one where Gemini's response
    was truncated mid-array and some candidates had to be dropped as
    incomplete (see _parse_json_array). `events` always holds only
    complete, schema-valid, source-verified candidates either way; this
    exists purely so a caller can tell "this is everything there was" from
    "this is a possibly-partial result" rather than conflating the two
    into one plain list."""

    events: list[ExtractedEvent] = field(default_factory=list)
    truncated: bool = False


class EventExtractionError(Exception):
    """Raised when event extraction cannot complete at all: no provider
    configured, the generate() call itself failing, or a response with no
    parseable JSON array in it. Never raised merely because some individual
    candidates failed validation — those are dropped, not a hard failure
    (see this module's own docstring)."""


class EventExtractor:
    """Extracts ExtractedEvent candidates from an investigation's own
    evidence via the configured LLMProvider, then deterministically
    verifies every candidate against that same evidence before returning
    it. Depends only on the LLMProvider interface — never a provider SDK."""

    def __init__(
        self,
        provider: LLMProvider | None = None,
        prompt_builder: PromptBuilder | None = None,
    ) -> None:
        self._provider = provider or GeminiProvider()
        self._prompt_builder = prompt_builder or PromptBuilder()

    def extract(self, question: str, evidence: list[Evidence]) -> ExtractionResult:
        """Return the event candidates supported by `evidence`. With no
        evidence, returns an empty, non-truncated ExtractionResult and
        makes no provider call at all — there is nothing to extract an
        event from, mirroring ReasoningEngine's own no-evidence shortcut.
        Raises EventExtractionError if the provider call fails or its
        response has no parseable JSON array at all."""
        if not evidence:
            return ExtractionResult(events=[], truncated=False)

        source_context = _load_source_context({item.document_id for item in evidence})
        prompt = self._prompt_builder.build_event_extraction_prompt(
            question, evidence, source_context, max_output_tokens=EVENT_EXTRACTION_MAX_OUTPUT_TOKENS
        )

        try:
            # .truncated (the provider's own output-token-limit signal) is
            # deliberately not used here -- this module keeps its own,
            # separate structural truncation check below (_parse_json_array:
            # did the JSON array ever reach a closing "]"), unchanged by
            # this field's addition, so the two truncation signals (main
            # answer vs. event extraction) are never conflated.
            raw_text = self._provider.generate(prompt).text
        except LLMProviderError as exc:
            raise EventExtractionError(str(exc)) from exc

        raw_candidates, truncated = _parse_json_array(raw_text)
        evidence_by_key = {(item.document_id, item.citation.chunk_id): item for item in evidence}

        events: list[ExtractedEvent] = []
        for raw in raw_candidates:
            event = _validate_candidate(raw, evidence_by_key)
            if event is not None:
                events.append(event)
        return ExtractionResult(events=events, truncated=truncated)


def _load_source_context(document_ids: set[int]) -> dict[int, SourceContext]:
    """Deterministically look up each document's own real, stored sent/
    authored date and sender identity — never inferred from body text,
    never trusted from the model. For an email body Document (EmailMessage
    shares its primary key with Document — see EmailMessage's own
    docstring), this is EmailMessage.sent_at/sender_name/sender_email,
    exactly the verified field the Phase 8B.2 brief requires ("never assume
    Document.doc_date is the email's sent date; use EmailMessage.sent_at").
    For any other document, this falls back to the generic, already-
    deterministic Document.doc_date (no sender concept applies).

    This exists specifically so the model is given the message's own date/
    sender as separate, labeled, read-only context — distinct from
    whatever date an event itself turns out to have — rather than being
    asked to infer them from body prose that, as this phase's own
    production evaluation found, frequently doesn't restate them at all."""
    if not document_ids:
        return {}

    context: dict[int, SourceContext] = {}
    with get_session_factory()() as session:
        for document_id in document_ids:
            email_message = session.get(EmailMessage, document_id)
            if email_message is not None:
                context[document_id] = SourceContext(
                    sent_or_authored_date=email_message.sent_at.date().isoformat() if email_message.sent_at else None,
                    sender=email_message.sender_name or email_message.sender_email,
                    is_email=True,
                )
                continue

            document = session.get(Document, document_id)
            if document is not None and document.doc_date is not None:
                context[document_id] = SourceContext(
                    sent_or_authored_date=document.doc_date.isoformat(),
                    sender=None,
                    is_email=False,
                )

    return context


def _parse_json_array(raw_text: str) -> tuple[list[dict], bool]:
    """Parse `raw_text` as a sequence of JSON objects inside a `[...]` array,
    tolerating a leading markdown fence/prose before the `[` and, critically,
    an array that was never properly closed because generation hit the
    output token cap mid-object (see the module docstring). Each element is
    decoded independently via json.JSONDecoder.raw_decode(), so every
    COMPLETE leading object is kept even if a later one is cut off — nothing
    is fabricated to complete a truncated object; it is simply dropped,
    exactly like any other invalid individual candidate.

    Returns (items, truncated) — `truncated` is True whenever the array
    never reached a proper closing `]` (ExtractionResult.truncated surfaces
    this to callers, rather than only a log line, per the Quality
    Remediation requirement that a partial result be distinguishable from
    a complete one).

    Raises EventExtractionError only if no array start is found at all, or
    if not even the FIRST object/element can be parsed (that case cannot be
    distinguished from the model returning genuine prose instead of JSON —
    the brief's own "do not convert a failure into a misleading zero-events
    success" principle applies, so this is reported as a failure, not an
    empty result)."""
    start_match = _ARRAY_START_PATTERN.search(raw_text)
    if start_match is None:
        raise EventExtractionError("Model response contained no JSON array")

    decoder = json.JSONDecoder()
    text = raw_text[start_match.end():]  # position just after the opening '['
    items: list[dict] = []
    index = 0
    truncated = False

    while True:
        stripped = text[index:].lstrip()
        if not stripped:
            truncated = True
            break
        skip = len(text[index:]) - len(stripped)
        index += skip

        if stripped[0] in "]":
            break  # the array closed normally
        if stripped[0] == ",":
            index += 1
            continue

        try:
            obj, offset = decoder.raw_decode(text, index)
        except json.JSONDecodeError:
            if not items:
                raise EventExtractionError("Model response's first array element was not valid JSON")
            truncated = True
            break

        if isinstance(obj, dict):
            items.append(obj)
        index = offset

    if truncated:
        logger.warning(
            "Event extraction response was truncated mid-array (likely the output token "
            "cap) — kept %d complete candidate(s) preceding the cut-off, dropped the rest.",
            len(items),
        )

    return items, truncated


def _validate_candidate(raw: dict, evidence_by_key: dict[tuple[int, int], Evidence]) -> ExtractedEvent | None:
    """Return a verified ExtractedEvent for `raw`, or None if it fails any
    check below — individually dropped, never raised, per this module's
    own abstain-don't-fabricate contract. Every check is deterministic;
    nothing here calls the LLM again or trusts `raw` on its own word."""
    if not _REQUIRED_KEYS.issubset(raw.keys()):
        return None

    document_id = raw.get("document_id")
    chunk_id = raw.get("chunk_id")
    if not isinstance(document_id, int) or not isinstance(chunk_id, int):
        return None

    evidence = evidence_by_key.get((document_id, chunk_id))
    if evidence is None:
        # The model named a document_id/chunk_id pair that was never
        # actually offered to it as evidence — never trusted, always
        # dropped, regardless of how plausible the rest of the candidate
        # looks.
        return None

    source_text = evidence.citation.chunk_text or evidence.surrounding_context or ""
    excerpt = raw.get("excerpt")
    if not isinstance(excerpt, str) or not excerpt.strip():
        return None
    if excerpt.strip() not in source_text:
        # Not a genuine verbatim substring of the one chunk this candidate
        # itself claims as its source — abstain rather than persist an
        # unsupported event (Phase 8B.2 brief, "Source traceability").
        return None

    event_type = raw.get("event_type")
    if event_type is not None and event_type not in EVENT_TYPES:
        event_type = None

    assertion_type = raw.get("assertion_type")
    if assertion_type not in ASSERTION_TYPES:
        assertion_type = None

    event_date_basis = raw.get("event_date_basis")
    if event_date_basis not in DATE_BASIS_VALUES:
        event_date_basis = "unknown"

    event_date = raw.get("event_date")
    if event_date_basis == "unknown" or not isinstance(event_date, str) or not event_date.strip():
        event_date = None
    else:
        event_date = _parse_iso_date(event_date)
        if event_date is None:
            event_date_basis = "unknown"

    description = raw.get("description")
    if not isinstance(description, str) or not description.strip():
        description = excerpt.strip()

    attributed_party = raw.get("attributed_party")
    if not isinstance(attributed_party, str) or not attributed_party.strip():
        attributed_party = None

    try:
        return ExtractedEvent(
            document_id=document_id,
            chunk_id=chunk_id,
            excerpt=excerpt.strip(),
            event_type=event_type,
            assertion_type=assertion_type,
            description=description.strip(),
            event_date=event_date,
            event_date_basis=event_date_basis,
            attributed_party=attributed_party,
        )
    except ValueError:
        # Defense-in-depth against a pydantic validation error on a field
        # this function didn't anticipate (e.g. a malformed date reaching
        # the model despite the parse above) — dropped, not raised.
        return None


def _parse_iso_date(value: str):
    from datetime import date

    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None
