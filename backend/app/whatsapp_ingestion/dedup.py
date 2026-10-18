"""Deterministic deduplication for imported WhatsApp messages (Phase W1).

Single-tier, unlike app/email_ingestion/dedup.py's two-tier scheme: a
WhatsApp text export carries no analogue of an RFC 822 Message-ID at all,
so content_hash is the ONLY identity signal available, not a fallback for
a missing primary one. This is a real, disclosed limitation (see module
docstring below), not an oversight.

content_hash is built from (chat_id, sender_name, raw_timestamp_text,
normalized message text) -- deliberately scoped to chat_id (not globally
per-project) so two different chats that happen to contain an identical
line (a common greeting, a repeated boilerplate message) are never
wrongly deduped against each other; two DIFFERENT chats having the exact
same (sender, timestamp, text) combination would be an extraordinary
coincidence, whereas two messages WITHIN one chat sharing that tuple is
both the normal "identical re-import" case this is designed to catch AND
the one real false-negative limitation documented below.

Known limitation (disclosed, not fixed, because WhatsApp exports do not
expose anything better): a genuinely repeated, legitimate message -- the
same sender sending the exact same text at the exact same exported
timestamp (to-the-second) more than once in one chat -- is indistinguishable
from a duplicate import of that one message. sequence_index is
DELIBERATELY EXCLUDED from the hash for this reason: including it would
make dedup worse, not better (a partially-overlapping re-export's
overlapping messages would get different sequence_index values than the
original import, since the new export's own numbering restarts from
whatever range it covers), and would not actually resolve the genuine
same-text-same-timestamp ambiguity anyway.

An import retry is therefore safe for the normal case (re-importing the
identical export, or one that merely extends an earlier one with new
messages) but NOT provably perfect against the rare true-repeat case
above -- this is called out explicitly in the API response documentation
and the W1 final report rather than silently assumed away.
"""

from __future__ import annotations

import hashlib
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import WhatsAppMessage
from app.whatsapp_ingestion.parsing import ParsedWhatsAppMessage


def compute_content_hash(message: ParsedWhatsAppMessage) -> str:
    """A stable fingerprint of one message's meaningful content --
    deliberately NOT including sequence_index (see module docstring)."""
    normalized_text = re.sub(r"\s+", " ", message.text or "").strip()
    parts = [
        (message.sender_name or "").strip().lower(),
        message.raw_timestamp_text.strip(),
        normalized_text,
    ]
    digest_input = "\x1f".join(parts).encode("utf-8", errors="replace")
    return hashlib.sha256(digest_input).hexdigest()


def find_existing_by_content_hash(session: Session, chat_id: int, content_hash: str) -> WhatsAppMessage | None:
    return session.scalar(
        select(WhatsAppMessage).where(
            WhatsAppMessage.chat_id == chat_id,
            WhatsAppMessage.content_hash == content_hash,
        )
    )
