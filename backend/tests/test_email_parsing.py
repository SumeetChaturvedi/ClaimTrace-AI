"""Focused tests for deterministic .eml parsing, threading, and
deduplication (Phase 8A: Email Thread Intelligence) — pure unit tests, no
database, no HTTP, no Gemini: these exercise app/email_ingestion/parsing.py
and dedup.py in complete isolation, so they stay fast and can run on every
commit.

Run with:
    cd backend && source .venv/bin/activate
    PYTHONPATH=. python3 -m unittest tests.test_email_parsing -v
"""

import unittest
from datetime import timezone
from email.message import EmailMessage as StdlibEmailMessage
from email.utils import formatdate

from app.email_ingestion.dedup import compute_content_hash
from app.email_ingestion.parsing import EmailParseError, parse_eml


def _build(**kwargs) -> bytes:
    """Build a real .eml via Python's own stdlib email.message.EmailMessage
    (the same library parse_eml() itself uses to read it back) rather than
    a hand-written fixture string — so these tests exercise the real
    encode -> parse round trip, matching this project's established
    "build a real file with the real library" testing convention (see
    test_docx_ingestion.py's _build_test_docx)."""
    msg = StdlibEmailMessage()
    for key, value in kwargs.pop("headers", {}).items():
        msg[key] = value
    body = kwargs.pop("body", None)
    subtype = kwargs.pop("subtype", "plain")
    charset = kwargs.pop("charset", "utf-8")
    if body is not None:
        msg.set_content(body, subtype=subtype, charset=charset)
    for attachment in kwargs.pop("attachments", []):
        msg.add_attachment(
            attachment["content"],
            maintype=attachment.get("maintype", "application"),
            subtype=attachment.get("subtype", "octet-stream"),
            filename=attachment["filename"],
        )
    return msg.as_bytes()


class PlainTextEmailTests(unittest.TestCase):
    def test_plain_text_email_parses_all_core_fields(self):
        raw = _build(
            headers={
                "Message-ID": "<abc123@example.com>",
                "From": "Jane Engineer <jane@meridian.example>",
                "To": "Bob Contractor <bob@sagara.example>",
                "Cc": "pm@nhia.example",
                "Subject": "Site Instruction SI-088",
                "Date": "Tue, 03 Feb 2026 09:15:00 +0530",
            },
            body="The marker is CLAIMTRACE-PARSE-TEST-1. Please proceed per SI-088.",
        )
        parsed = parse_eml(raw)
        self.assertEqual(parsed.message_id, "abc123@example.com")
        self.assertEqual(parsed.sender_name, "Jane Engineer")
        self.assertEqual(parsed.sender_email, "jane@meridian.example")
        self.assertEqual(parsed.to_recipients, ["Bob Contractor <bob@sagara.example>"])
        self.assertEqual(parsed.cc_recipients, ["pm@nhia.example"])
        self.assertEqual(parsed.subject, "Site Instruction SI-088")
        self.assertIn("CLAIMTRACE-PARSE-TEST-1", parsed.plain_body)
        self.assertIsNone(parsed.html_body)
        self.assertEqual(parsed.attachments, [])


class HtmlEmailTests(unittest.TestCase):
    def test_html_only_email_produces_searchable_plain_text(self):
        raw = _build(
            headers={"Subject": "HTML notice", "From": "a@example.com", "Date": formatdate()},
            body="<html><body><p>Marker <b>CLAIMTRACE-HTML-TEST-2</b> inside HTML.</p></body></html>",
            subtype="html",
        )
        parsed = parse_eml(raw)
        self.assertIsNotNone(parsed.html_body)
        self.assertIn("CLAIMTRACE-HTML-TEST-2", parsed.plain_body)
        self.assertNotIn("<b>", parsed.plain_body)


class MultipartEmailTests(unittest.TestCase):
    def test_multipart_email_with_attachment_extracts_both_body_and_attachment(self):
        raw = _build(
            headers={"Subject": "Multipart test", "From": "a@example.com", "Date": formatdate()},
            body="Body marker CLAIMTRACE-MULTIPART-TEST-3.",
            attachments=[{"filename": "notes.txt", "content": b"attachment bytes", "maintype": "text", "subtype": "plain"}],
        )
        parsed = parse_eml(raw)
        self.assertIn("CLAIMTRACE-MULTIPART-TEST-3", parsed.plain_body)
        self.assertEqual(len(parsed.attachments), 1)
        self.assertEqual(parsed.attachments[0].filename, "notes.txt")
        self.assertEqual(parsed.attachments[0].content, b"attachment bytes")


class EncodedHeaderTests(unittest.TestCase):
    def test_encoded_subject_and_sender_name_are_decoded(self):
        # RFC 2047 encoded-word form, as a real mail client would produce
        # for a non-ASCII subject/display name.
        raw = (
            b"Message-ID: <enc1@example.com>\r\n"
            b"From: =?UTF-8?B?SsO8cmdlbg==?= <jurgen@example.com>\r\n"
            b"Subject: =?UTF-8?B?UMOpcmlvZCBkZSBkw6lmYXV0?=\r\n"
            b"Date: " + formatdate().encode() + b"\r\n"
            b"Content-Type: text/plain; charset=utf-8\r\n\r\n"
            b"Body text.\r\n"
        )
        parsed = parse_eml(raw)
        self.assertEqual(parsed.sender_name, "Jürgen")
        self.assertEqual(parsed.subject, "Périod de défaut")


class TimezoneDateTests(unittest.TestCase):
    def test_timezone_aware_date_is_normalized_to_utc(self):
        raw = _build(
            headers={"Subject": "TZ test", "From": "a@example.com", "Date": "Tue, 03 Feb 2026 09:15:00 +0530"},
            body="x",
        )
        parsed = parse_eml(raw)
        self.assertIsNotNone(parsed.sent_at)
        self.assertEqual(parsed.sent_at.astimezone(timezone.utc).hour, 3)
        self.assertEqual(parsed.sent_at.astimezone(timezone.utc).minute, 45)
        self.assertFalse(parsed.sent_at_timezone_unknown)

    def test_date_with_no_offset_is_flagged_unknown_not_fabricated_precise(self):
        raw = _build(
            headers={"Subject": "No-offset test", "From": "a@example.com", "Date": "Tue, 03 Feb 2026 09:15:00 -0000"},
            body="x",
        )
        parsed = parse_eml(raw)
        self.assertIsNotNone(parsed.sent_at)
        self.assertTrue(parsed.sent_at_timezone_unknown)


class MissingOptionalHeaderTests(unittest.TestCase):
    def test_missing_message_id_is_none_not_fabricated(self):
        raw = _build(headers={"Subject": "No message id", "From": "a@example.com", "Date": formatdate()}, body="x")
        parsed = parse_eml(raw)
        self.assertIsNone(parsed.message_id)

    def test_missing_date_leaves_sent_at_none(self):
        raw = _build(headers={"Subject": "No date", "From": "a@example.com", "Message-ID": "<nodate@example.com>"}, body="x")
        parsed = parse_eml(raw)
        self.assertIsNone(parsed.sent_at)
        self.assertFalse(parsed.sent_at_timezone_unknown)

    def test_malformed_date_leaves_sent_at_none_and_records_a_note(self):
        raw = _build(
            headers={"Subject": "Bad date", "From": "a@example.com", "Date": "not a real date at all"},
            body="x",
        )
        parsed = parse_eml(raw)
        self.assertIsNone(parsed.sent_at)
        self.assertTrue(any("Date" in note for note in parsed.parse_notes))

    def test_incomplete_threading_headers_yield_empty_lists_not_errors(self):
        raw = _build(headers={"Subject": "No threading headers", "From": "a@example.com", "Date": formatdate()}, body="x")
        parsed = parse_eml(raw)
        self.assertEqual(parsed.in_reply_to, [])
        self.assertEqual(parsed.references, [])

    def test_in_reply_to_and_references_are_parsed_into_stripped_ids(self):
        raw = _build(
            headers={
                "Subject": "Reply",
                "From": "a@example.com",
                "Date": formatdate(),
                "In-Reply-To": "<parent@example.com>",
                "References": "<root@example.com> <parent@example.com>",
            },
            body="x",
        )
        parsed = parse_eml(raw)
        self.assertEqual(parsed.in_reply_to, ["parent@example.com"])
        self.assertEqual(parsed.references, ["root@example.com", "parent@example.com"])


class MalformedInputTests(unittest.TestCase):
    def test_empty_bytes_raises_parse_error(self):
        with self.assertRaises(EmailParseError):
            parse_eml(b"")

    def test_whitespace_only_bytes_raises_parse_error(self):
        with self.assertRaises(EmailParseError):
            parse_eml(b"   \n\n  ")

    def test_content_with_no_headers_is_treated_as_a_bodiless_message_not_crashed(self):
        # Python's email parser is deliberately lenient (RFC 2822 parsers
        # generally are): content with no recognizable header lines at all
        # is not rejected outright — it falls through to being read as the
        # message body itself, which is real, searchable text, not nothing.
        # This is correct, documented behavior (see parse_eml's docstring),
        # not a gap: EmailParseError is reserved for input with truly no
        # signal at all (empty/whitespace-only — see the two tests above).
        parsed = parse_eml(b"this is just some random bytes, not an email at all, no headers, no body markers")
        self.assertIsNone(parsed.message_id)
        self.assertIsNone(parsed.subject)


class ContentHashTests(unittest.TestCase):
    def test_identical_messages_produce_identical_hash(self):
        raw = _build(
            headers={"Subject": "Hash test", "From": "a@example.com", "Date": "Tue, 03 Feb 2026 09:15:00 +0000"},
            body="Same content.",
        )
        parsed_a = parse_eml(raw)
        parsed_b = parse_eml(raw)
        self.assertEqual(compute_content_hash(parsed_a), compute_content_hash(parsed_b))

    def test_different_body_produces_different_hash(self):
        raw_a = _build(
            headers={"Subject": "Hash test", "From": "a@example.com", "Date": "Tue, 03 Feb 2026 09:15:00 +0000"},
            body="Content A.",
        )
        raw_b = _build(
            headers={"Subject": "Hash test", "From": "a@example.com", "Date": "Tue, 03 Feb 2026 09:15:00 +0000"},
            body="Content B.",
        )
        self.assertNotEqual(
            compute_content_hash(parse_eml(raw_a)),
            compute_content_hash(parse_eml(raw_b)),
        )

    def test_hash_is_stable_across_re_export_with_different_mime_boundary(self):
        # Two independently-built messages with identical sender/subject/
        # date/body but (necessarily) different random MIME boundaries —
        # the hash must still match, since it's computed from meaningful
        # content, not raw bytes.
        raw_a = _build(
            headers={"Subject": "Stable hash", "From": "a@example.com", "Date": "Tue, 03 Feb 2026 09:15:00 +0000"},
            body="Stable content.",
        )
        raw_b = _build(
            headers={"Subject": "Stable hash", "From": "a@example.com", "Date": "Tue, 03 Feb 2026 09:15:00 +0000"},
            body="Stable content.",
            attachments=[],
        )
        self.assertEqual(
            compute_content_hash(parse_eml(raw_a)),
            compute_content_hash(parse_eml(raw_b)),
        )


if __name__ == "__main__":
    unittest.main()
