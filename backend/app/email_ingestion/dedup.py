"""Deterministic deduplication for imported email messages (Phase 8A:
Email Thread Intelligence).

Two independent, layered mechanisms, in priority order:

1. Message-ID (when present) is authoritative. The database itself
   enforces uniqueness per project (see
   EmailMessage.ux_email_messages_project_message_id in app/db/models.py),
   so a re-import of a .eml whose Message-ID already exists for this
   project is detected unambiguously, including under concurrent imports —
   this module's own pre-check (see `find_existing_by_message_id`) exists
   only to produce a clean, reportable "already imported" outcome instead
   of surfacing a raw database IntegrityError to the caller.

2. content_hash (always computed, for every message, Message-ID or not) is
   the fallback identity for a message with no Message-ID header at all —
   real correspondence exports do sometimes lack one (e.g. hand-assembled
   .eml files, some older mail systems). Built from sender + subject + sent
   timestamp + normalized body text: stable across re-import of the exact
   same bytes, but deliberately NOT a hash of the raw .eml bytes themselves
   (which would treat two exports of the identical message with different
   MIME boundary strings or header ordering as different messages).

An import retry is therefore always safe: a Message-ID match or a
content_hash match both stop a duplicate from being persisted a second
time. Neither path silently overwrites the existing message's content —
only the resulting status differs between "imported" and
"already imported"."""

from __future__ import annotations

import hashlib
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import EmailMessage
from app.email_ingestion.parsing import ParsedEmail


def compute_content_hash(parsed: ParsedEmail) -> str:
    """A stable fingerprint of a message's meaningful content, independent
    of incidental re-export differences (MIME boundaries, header order,
    whitespace). Not a security hash — a dedup key only."""
    normalized_body = re.sub(r"\s+", " ", parsed.plain_body or "").strip()
    sent_at_key = parsed.sent_at.isoformat() if parsed.sent_at else ""
    parts = [
        (parsed.sender_email or "").strip().lower(),
        (parsed.subject or "").strip(),
        sent_at_key,
        normalized_body,
    ]
    digest_input = "\x1f".join(parts).encode("utf-8", errors="replace")
    return hashlib.sha256(digest_input).hexdigest()


def find_existing_by_message_id(session: Session, project_id: int, message_id: str) -> EmailMessage | None:
    return session.scalar(
        select(EmailMessage).where(
            EmailMessage.project_id == project_id,
            EmailMessage.message_id == message_id,
        )
    )


def find_existing_by_content_hash(session: Session, project_id: int, content_hash: str) -> EmailMessage | None:
    return session.scalar(
        select(EmailMessage).where(
            EmailMessage.project_id == project_id,
            EmailMessage.content_hash == content_hash,
        )
    )
