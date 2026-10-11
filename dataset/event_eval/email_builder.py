"""Deterministic .eml construction helper, shared by every scenario module
under scenarios/.

Mirrors the exact pattern already established and tested in
backend/tests/test_email_ingestion.py's `_build_eml` helper: real .eml
bytes built via Python's own stdlib `email.message.EmailMessage`, the same
library `backend/app/email_ingestion/parsing.py` itself reads them back
with — never a hand-written raw string masquerading as a MIME message.
This module does not import anything from backend/app/ (the evaluation
harness is intentionally independent of the production application — see
gold_schema.py's module docstring), it just reuses the same *technique*.
"""

from __future__ import annotations

from email.message import EmailMessage


def build_eml(
    *,
    message_id: str | None = None,
    in_reply_to: str | None = None,
    references: str | None = None,
    from_: str,
    to: str | None = None,
    cc: str | None = None,
    subject: str,
    date: str,
    body: str,
) -> bytes:
    """Build one real .eml message. `date` must already be a valid RFC 5322
    date string (callers use `email.utils.format_datetime`/`formatdate`
    with an explicit, fictional, fixed date — never "now" — so the dataset
    stays fully deterministic across runs)."""
    msg = EmailMessage()
    if message_id:
        msg["Message-ID"] = message_id
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
    if references:
        msg["References"] = references
    msg["From"] = from_
    if to:
        msg["To"] = to
    if cc:
        msg["Cc"] = cc
    msg["Subject"] = subject
    msg["Date"] = date
    msg.set_content(body)
    return msg.as_bytes()
