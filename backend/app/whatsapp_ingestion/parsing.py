"""Deterministic parsing of a WhatsApp chat export's plain-text transcript
(Phase W1: WhatsApp Export Ingestion).

Nothing here talks to the database, touches storage, or makes a
dedup/indexing decision — exactly like app/email_ingestion/parsing.py, this
module's only job is "raw export text in, a plain ParsedWhatsAppChat out,"
testable in complete isolation.

Supported line shapes (the two dominant real-world exports):
  iOS:     [DD/MM/YY, HH:MM:SS] Sender Name: message text
  Android: DD/MM/YY, HH:MM - Sender Name: message text

A line that matches neither shape is treated as a continuation of the
previous message's text (a genuine multiline message body) — never
silently dropped, never treated as a new, sender-less message of its own.

Date ambiguity (the task's own explicit requirement): WhatsApp's exported
date has no locale tag. Given two numeric groups D and M with a 2- or
4-digit year, this parser:
  - treats a value > 12 as unambiguously the DAY (the other must be the
    month), so a date like 25/03/24 is unambiguous (day=25, month=3);
  - falls back to a documented default (day-first, WhatsApp's own
    international default) ONLY when both numbers are <= 12, in which case
    the result is explicitly flagged ambiguous rather than silently
    guessed as certain;
  - treats a date where BOTH numbers are > 12 as unparseable (sent_at=None,
    original text preserved, a parse note recorded) rather than guessing.

No timezone information exists anywhere in a WhatsApp export — sent_at is
a naive datetime (the device's own local time, of unknown offset), never
coerced to a fabricated UTC instant.

Sender identification: every genuine user message is exported as
"Name: text"; a system/group-event line (participant added/removed,
encryption notice, pin changed, etc.) never has that shape at all. The
split on ": " is therefore the sender signal itself, not a guess — a line
with no such split is classified as a system message with sender_name=None,
never a fabricated attribution.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime


class WhatsAppParseError(Exception):
    """Raised only when the input has no recognizable WhatsApp export
    structure at all (empty, or not a single line matches the expected
    date-prefixed shape even as a continuation target) — mirrors
    EmailParseError's own "last line of defense" role. A real export with
    some malformed/truncated lines mixed in is NOT an error; those lines
    are preserved as best-effort continuations or dropped individually
    with a parse note, never aborting the whole import."""


@dataclass(frozen=True)
class ParsedWhatsAppMessage:
    sequence_index: int  # 0-based position in this export, as exported -- the one ordering signal that is always reliable, even when sent_at is ambiguous or missing
    sender_name: str | None  # None for a system/group-event message
    raw_timestamp_text: str  # exactly as it appeared in the export, e.g. "25/03/24, 10:00:00" -- never discarded even when sent_at below is None
    sent_at: datetime | None  # naive local datetime; None if unparseable -- never fabricated
    sent_at_ambiguous: bool  # True when day/month ordering could not be disambiguated from the date alone
    message_type: str  # 'text' | 'system' | 'deleted' | 'media'
    text: str  # the message's own text (for 'system'/'deleted', the system-generated line itself)
    media_filename: str | None  # the filename referenced by a media placeholder in the export text, if any -- None does not mean "no media", only "no filename was referenced in the text export"


@dataclass(frozen=True)
class ParsedWhatsAppChat:
    chat_title: str | None  # derived only from the uploaded filename (see pipeline.py) -- never fabricated from message content
    messages: list[ParsedWhatsAppMessage] = field(default_factory=list)
    parse_notes: list[str] = field(default_factory=list)


# Zero-width/invisible characters real exports sometimes include around a
# sender name or media placeholder (e.g. iOS's left-to-right/right-to-left
# marks) -- stripped before any pattern matching, never left to silently
# break a match.
_INVISIBLE_CHARS_RE = re.compile("[‎‏﻿]")

_IOS_PREFIX_RE = re.compile(
    r"^\[(?P<date>\d{1,2}/\d{1,2}/\d{2,4}),\s*(?P<time>\d{1,2}:\d{2}(?::\d{2})?(?:\s?[AaPp][Mm])?)\]\s(?P<rest>.*)$"
)
_ANDROID_PREFIX_RE = re.compile(
    r"^(?P<date>\d{1,2}/\d{1,2}/\d{2,4}),\s*(?P<time>\d{1,2}:\d{2}(?::\d{2})?(?:\s?[AaPp][Mm])?)\s[-–]\s(?P<rest>.*)$"
)

_DELETED_MARKERS = (
    "this message was deleted",
    "you deleted this message",
)
_MEDIA_OMITTED_MARKERS = (
    "image omitted",
    "video omitted",
    "audio omitted",
    "sticker omitted",
    "gif omitted",
    "document omitted",
    "contact card omitted",
)
_MEDIA_ATTACHED_RE = re.compile(r"<attached:\s*(?P<filename>[^>]+)>", re.IGNORECASE)
_MEDIA_FILE_ATTACHED_RE = re.compile(r"^(?P<filename>\S+\.\w+)\s*\(file attached\)$", re.IGNORECASE)


def _strip_invisible(text: str) -> str:
    return _INVISIBLE_CHARS_RE.sub("", text)


def _parse_date(date_text: str) -> tuple[int | None, int | None, int | None, bool]:
    """Return (year, month, day, ambiguous) or (None, None, None, False) if
    the two non-year numbers can't both be valid day/month values at all
    (e.g. both > 12). See module docstring for the full disambiguation
    rule."""
    parts = date_text.split("/")
    if len(parts) != 3:
        return None, None, None, False
    try:
        first, second, year_raw = (int(p) for p in parts)
    except ValueError:
        return None, None, None, False

    year = year_raw + 2000 if year_raw < 100 else year_raw
    if not (1 <= first <= 31 and 1 <= second <= 31):
        return None, None, None, False

    first_could_be_month = first <= 12
    second_could_be_month = second <= 12

    if first_could_be_month and second_could_be_month:
        # Genuinely ambiguous -- default to day-first (WhatsApp's own
        # international default), explicitly flagged as a guess.
        return year, second, first, True
    if second_could_be_month:
        # first > 12, so first must be the day; second is the month.
        return year, second, first, False
    if first_could_be_month:
        # second > 12, so second must be the day; first is the month.
        return year, first, second, False
    # Both > 12 -- not a valid calendar date either way.
    return None, None, None, False


def _parse_time(time_text: str) -> tuple[int, int, int] | None:
    match = re.match(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?\s?([AaPp][Mm])?$", time_text.strip())
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2))
    second = int(match.group(3) or 0)
    meridiem = match.group(4)
    if meridiem:
        meridiem = meridiem.lower()
        if hour == 12:
            hour = 0
        if meridiem == "pm":
            hour += 12
    if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
        return None
    return hour, minute, second


def _parse_timestamp(date_text: str, time_text: str) -> tuple[datetime | None, bool, str | None]:
    year, month, day, ambiguous = _parse_date(date_text)
    if year is None:
        return None, False, f"unparseable date {date_text!r}"
    time_parts = _parse_time(time_text)
    if time_parts is None:
        return None, ambiguous, f"unparseable time {time_text!r}"
    hour, minute, second = time_parts
    try:
        return datetime(year, month, day, hour, minute, second), ambiguous, None
    except ValueError as exc:
        return None, ambiguous, f"invalid calendar date/time ({date_text!r} {time_text!r}): {exc}"


def _split_sender_and_text(rest: str) -> tuple[str | None, str]:
    """A real user message is always "Name: text"; a system/group-event
    line never has that shape. Split on the FIRST ": " -- the earliest
    point a real sender name could end -- never searched further into the
    text, which would risk splitting a message that merely CONTAINS a
    colon into a fake "sender"."""
    sep = ": "
    idx = rest.find(sep)
    if idx == -1:
        return None, rest
    name = rest[:idx].strip()
    text = rest[idx + len(sep) :]
    if not name:
        return None, rest
    return name, text


def _classify(text: str) -> tuple[str, str | None]:
    """Return (message_type, media_filename) for a message whose sender
    split already happened. 'media_filename' is only ever a real filename
    actually referenced in the export text -- never guessed."""
    normalized = text.strip()
    lowered = normalized.lower()

    if lowered in _DELETED_MARKERS:
        return "deleted", None

    attached_match = _MEDIA_ATTACHED_RE.search(normalized)
    if attached_match:
        return "media", attached_match.group("filename").strip()

    file_attached_match = _MEDIA_FILE_ATTACHED_RE.match(normalized)
    if file_attached_match:
        return "media", file_attached_match.group("filename").strip()

    if any(marker in lowered for marker in _MEDIA_OMITTED_MARKERS):
        return "media", None

    return "text", None


def parse_whatsapp_export(raw_text: str) -> ParsedWhatsAppChat:
    """Parse a WhatsApp chat export's plain-text transcript. Deterministic:
    the same text always produces the same result. Raises
    WhatsAppParseError only when the input has no recognizable WhatsApp
    export structure at all (see that class's own docstring) -- a real
    export with some malformed lines mixed in still parses, with those
    lines folded into the nearest preceding message and a parse note
    recorded, never silently dropped and never aborting the whole import."""
    if not raw_text or not raw_text.strip():
        raise WhatsAppParseError("empty input")

    lines = raw_text.splitlines()
    messages: list[ParsedWhatsAppMessage] = []
    notes: list[str] = []
    pending_text_lines: list[str] = []

    def _flush_pending(*, more_messages_follow: bool) -> None:
        if pending_text_lines and messages:
            extra = "\n".join(pending_text_lines)
            last = messages[-1]
            messages[-1] = ParsedWhatsAppMessage(
                sequence_index=last.sequence_index,
                sender_name=last.sender_name,
                raw_timestamp_text=last.raw_timestamp_text,
                sent_at=last.sent_at,
                sent_at_ambiguous=last.sent_at_ambiguous,
                message_type=last.message_type,
                text=f"{last.text}\n{extra}" if last.text else extra,
                media_filename=last.media_filename,
            )
        elif pending_text_lines and more_messages_follow:
            # Continuation lines before ANY recognized message exist --
            # preserved as a sender-less, timestamp-less leading message
            # rather than discarded (e.g. an export that was truncated
            # before its first real line, or exported from an unsupported
            # client variant). Only done when at least one real match
            # follows (more_messages_follow=True) -- the final, end-of-
            # input flush (more_messages_follow=False) never manufactures
            # a message this way, so input with NO recognizable WhatsApp
            # line anywhere correctly falls through to the "no messages at
            # all" WhatsAppParseError below instead of fabricating one.
            notes.append("leading content before any recognizable message line was preserved as a bodiless entry")
            messages.append(
                ParsedWhatsAppMessage(
                    sequence_index=0,
                    sender_name=None,
                    raw_timestamp_text="",
                    sent_at=None,
                    sent_at_ambiguous=False,
                    message_type="system",
                    text="\n".join(pending_text_lines),
                    media_filename=None,
                )
            )
        pending_text_lines.clear()

    for line in lines:
        cleaned = _strip_invisible(line).rstrip("\r")
        if not cleaned.strip():
            continue

        match = _IOS_PREFIX_RE.match(cleaned) or _ANDROID_PREFIX_RE.match(cleaned)
        if match is None:
            # Not a new message -- a continuation of whatever came before.
            pending_text_lines.append(cleaned)
            continue

        _flush_pending(more_messages_follow=True)

        date_text = match.group("date")
        time_text = match.group("time")
        rest = match.group("rest")
        sent_at, ambiguous, note = _parse_timestamp(date_text, time_text)
        if note:
            notes.append(f"message {len(messages) + 1}: {note}")

        sender_name, text = _split_sender_and_text(rest)
        message_type, media_filename = _classify(text)
        if sender_name is None and message_type == "text":
            message_type = "system"

        messages.append(
            ParsedWhatsAppMessage(
                sequence_index=len(messages),
                sender_name=sender_name,
                raw_timestamp_text=f"{date_text}, {time_text}",
                sent_at=sent_at,
                sent_at_ambiguous=ambiguous,
                message_type=message_type,
                text=text,
                media_filename=media_filename,
            )
        )

    _flush_pending(more_messages_follow=False)

    if not messages:
        raise WhatsAppParseError(
            "input contains no line matching a recognizable WhatsApp export message format"
        )

    return ParsedWhatsAppChat(chat_title=None, messages=messages, parse_notes=notes)
