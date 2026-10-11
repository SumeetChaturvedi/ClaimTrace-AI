"""Deterministic .eml parsing (Phase 8A: Email Thread Intelligence).

Uses only Python's standard library `email` package (policy.default, the
modern EmailMessage-based API) — no new dependency. policy.default already
handles the hard parts correctly and without custom code: RFC 2047
encoded-word decoding for Subject/From/To/Cc (`str(header)` yields the
already-decoded text), structured address parsing via `.addresses` on an
address header, multipart MIME traversal, per-part charset decoding, and
`iter_attachments()` to distinguish real attachments from the message body
itself (and from an inline image referenced by the HTML body via `cid:`,
which `iter_attachments()` correctly excludes).

Nothing here talks to the database, touches storage, or makes a threading/
dedup decision — this module's only job is "raw .eml bytes in, a plain
ParsedEmail out," so it can be tested in complete isolation.
"""

from __future__ import annotations

import email
import email.policy
import email.utils
from dataclasses import dataclass, field
from datetime import datetime, timezone


class EmailParseError(Exception):
    """Raised for input that isn't recognizable as an email message at all —
    e.g. empty bytes, or content with no headers, no body, and no
    attachments whatsoever. Python's `email` package is extremely lenient
    (it will return *something* for almost any input), so this is a last
    line of defense, not the primary validation; most malformed input still
    parses "successfully" into a ParsedEmail with mostly-empty fields, which
    is itself useful information (preserved, not hidden) rather than an
    error."""


@dataclass(frozen=True)
class ParsedAttachment:
    filename: str
    content_type: str | None
    content: bytes


@dataclass(frozen=True)
class ParsedEmail:
    message_id: str | None
    in_reply_to: list[str]
    references: list[str]
    sender_name: str | None
    sender_email: str | None
    to_recipients: list[str]
    cc_recipients: list[str]
    subject: str | None
    sent_at: datetime | None
    sent_at_timezone_unknown: bool
    plain_body: str
    html_body: str | None
    attachments: list[ParsedAttachment] = field(default_factory=list)
    # Raw header values this parser couldn't confidently use (e.g. a Date
    # header present but unparseable) — not surfaced to the user as an
    # error, just preserved for debugging/tests. Never affects import
    # success: a message with no usable date is still imported, with
    # sent_at=None, never a fabricated date.
    parse_notes: list[str] = field(default_factory=list)


def _strip_message_id(raw: str) -> str:
    return raw.strip().strip("<>").strip()


def _parse_id_list(raw: str | None) -> list[str]:
    """Split a References/In-Reply-To header value into individual
    Message-ID tokens, angle brackets stripped. Returns [] for a missing or
    empty header — never fabricates an id."""
    if not raw:
        return []
    return [_strip_message_id(token) for token in raw.split() if token.strip()]


def _format_address(name: str | None, addr_spec: str | None) -> str | None:
    if not addr_spec:
        return None
    if name:
        return f"{name} <{addr_spec}>"
    return addr_spec


def _address_list(header_value) -> list[str]:  # noqa: ANN001 -- email.headerregistry.AddressHeader, not a public type to import cleanly
    if header_value is None:
        return []
    try:
        addresses = header_value.addresses
    except AttributeError:
        # Malformed address header that policy.default couldn't structure —
        # fall back to its raw decoded string as a single entry rather than
        # silently dropping it.
        text = str(header_value).strip()
        return [text] if text else []
    results = []
    for addr in addresses:
        formatted = _format_address(addr.display_name or None, addr.addr_spec or None)
        if formatted:
            results.append(formatted)
    return results


def _parse_sent_at(msg) -> tuple[datetime | None, bool, list[str]]:  # noqa: ANN001
    notes: list[str] = []
    date_header = msg.get("Date")
    if date_header is None:
        return None, False, notes
    raw = str(date_header)
    try:
        parsed = email.utils.parsedate_to_datetime(raw)
    except (TypeError, ValueError) as exc:
        notes.append(f"unparseable Date header ({raw!r}): {exc}")
        return None, False, notes

    if parsed.tzinfo is None:
        # A Date header with no offset at all (rare, but real exports
        # vary) — treated as UTC so it's still a usable, comparable
        # timestamp, with the uncertainty surfaced via the returned flag
        # rather than silently implied as precise.
        notes.append(f"Date header {raw!r} had no timezone offset; assumed UTC")
        return parsed.replace(tzinfo=timezone.utc), True, notes
    return parsed, False, notes


def _extract_body(msg) -> tuple[str, str | None, list[str]]:  # noqa: ANN001
    notes: list[str] = []
    plain_part = msg.get_body(preferencelist=("plain",))
    html_part = msg.get_body(preferencelist=("html",))

    plain_text = ""
    if plain_part is not None:
        try:
            plain_text = plain_part.get_content()
        except (LookupError, UnicodeError) as exc:
            notes.append(f"could not decode plain-text body: {exc}")

    html_text: str | None = None
    if html_part is not None:
        try:
            html_text = html_part.get_content()
        except (LookupError, UnicodeError) as exc:
            notes.append(f"could not decode HTML body: {exc}")

    # No plain-text part at all, but there is an HTML one (Phase 8A spec:
    # "HTML-only or HTML-dominant email" must still be searchable). A real
    # HTML-to-text conversion library is out of scope for this phase — a
    # minimal, deterministic tag-stripping pass is enough to make the text
    # retrievable, never claimed to be a faithful rendering.
    if not plain_text.strip() and html_text:
        plain_text = _strip_html_tags(html_text)
        notes.append("plain-text body derived from HTML (no text/plain part present)")

    return plain_text, html_text, notes


def _strip_html_tags(html: str) -> str:
    """Minimal, deterministic HTML-to-text fallback: drop tags, collapse
    whitespace. Not a rendering engine and not meant to be one — just
    enough that an HTML-only message's content is still searchable text
    rather than being silently dropped."""
    import re

    import html as _html_module

    without_scripts = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    without_tags = re.sub(r"(?s)<[^>]+>", " ", without_scripts)
    unescaped = _html_module.unescape(without_tags)
    return re.sub(r"\s+", " ", unescaped).strip()


def _extract_attachments(msg) -> list[ParsedAttachment]:  # noqa: ANN001
    attachments: list[ParsedAttachment] = []
    for part in msg.iter_attachments():
        try:
            content = part.get_content()
        except (LookupError, UnicodeError, TypeError):
            # get_content() on a binary part should return bytes directly;
            # this guards the rare case of a malformed/undecodable part
            # rather than letting one bad attachment abort the whole parse.
            payload = part.get_payload(decode=True)
            content = payload if payload is not None else b""
        if isinstance(content, str):
            content = content.encode("utf-8", errors="replace")
        filename = part.get_filename() or "unnamed-attachment"
        attachments.append(
            ParsedAttachment(
                filename=filename,
                content_type=part.get_content_type(),
                content=content,
            )
        )
    return attachments


def parse_eml(raw_bytes: bytes) -> ParsedEmail:
    """Parse raw .eml bytes into a ParsedEmail. Deterministic: the same
    bytes always produce the same result. Raises EmailParseError only for
    input with no recognizable email structure at all (see that class's
    docstring) — a message missing individual optional fields (Message-ID,
    Date, ...) is not an error, it's a ParsedEmail with those fields left
    None/empty."""
    if not raw_bytes or not raw_bytes.strip():
        raise EmailParseError("empty input")

    try:
        msg = email.message_from_bytes(raw_bytes, policy=email.policy.default)
    except Exception as exc:  # noqa: BLE001 -- the stdlib parser is lenient; a genuine raise here means truly unparseable input
        raise EmailParseError(f"could not parse as an email message: {exc}") from exc

    message_id_header = msg.get("Message-ID")
    message_id = _strip_message_id(str(message_id_header)) if message_id_header else None

    in_reply_to = _parse_id_list(str(msg.get("In-Reply-To")) if msg.get("In-Reply-To") else None)
    references = _parse_id_list(str(msg.get("References")) if msg.get("References") else None)

    from_header = msg.get("From")
    sender_name: str | None = None
    sender_email: str | None = None
    if from_header is not None:
        try:
            first = from_header.addresses[0] if from_header.addresses else None
        except AttributeError:
            first = None
        if first is not None:
            sender_name = first.display_name or None
            sender_email = first.addr_spec or None
        elif str(from_header).strip():
            # Malformed From header policy.default couldn't structure —
            # preserve its raw text as the sender email rather than
            # dropping the sender entirely.
            sender_email = str(from_header).strip()

    to_recipients = _address_list(msg.get("To"))
    cc_recipients = _address_list(msg.get("Cc"))

    subject_header = msg.get("Subject")
    subject = str(subject_header).strip() if subject_header else None

    sent_at, tz_unknown, date_notes = _parse_sent_at(msg)
    plain_body, html_body, body_notes = _extract_body(msg)
    attachments = _extract_attachments(msg)

    notes = [*date_notes, *body_notes]

    has_any_signal = bool(
        message_id or subject or sender_email or to_recipients or plain_body.strip() or html_body or attachments
    )
    if not has_any_signal:
        raise EmailParseError("input parsed but contains no headers, body, or attachments recognizable as an email")

    return ParsedEmail(
        message_id=message_id,
        in_reply_to=in_reply_to,
        references=references,
        sender_name=sender_name,
        sender_email=sender_email,
        to_recipients=to_recipients,
        cc_recipients=cc_recipients,
        subject=subject,
        sent_at=sent_at,
        sent_at_timezone_unknown=tz_unknown,
        plain_body=plain_body,
        html_body=html_body,
        attachments=attachments,
        parse_notes=notes,
    )
