"""Deterministic, header-only thread reconstruction (Phase 8A: Email Thread
Intelligence).

Grouping is driven exclusively by Message-ID / In-Reply-To / References —
never by subject matching. This is a deliberate scope decision: the task
brief permits subject normalization only "as a cautious fallback... when
justified by the evidence available," and a same-subject heuristic is easy
to get wrong (two genuinely unrelated messages can share an identical
subject, e.g. a recurring "Weekly Progress Report"). Implementing it would
risk exactly what the brief warns against — "manufacturing thread
relationships" the source headers don't support. A message with no header
linkage to anything else simply becomes a thread of one; this is documented
as a known limitation in the final report, not hidden.

Threads are resolved against BOTH the current import batch and messages
already persisted for this project, and bidirectionally (a new message can
be the parent of an already-imported one, not just a reply to one) — this
is what makes "messages imported out of send order" and "a later import
links back into an earlier thread" both work correctly. When a new message
bridges two previously-separate threads (because neither half's headers
alone connected them), the threads are merged into one, keyed on the
lower/older thread id.
"""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import EmailMessage, EmailThread
from app.email_ingestion.parsing import ParsedEmail


def resolve_thread(session: Session, project_id: int, parsed: ParsedEmail) -> EmailThread:
    """Find (merging if necessary) or create the EmailThread this message
    belongs to. Does not persist the message itself — only ensures a
    correct, already-flushed EmailThread row exists and is returned. Must
    be called within the same transaction as the message's own insert, so
    a merge and the new message land together or not at all."""
    candidate_ids = _candidate_message_ids(parsed)

    matched_thread_ids: set[int] = set()

    if candidate_ids:
        # Direction 1: this message references an already-known message
        # (its own Message-ID, or one of its In-Reply-To/References
        # entries, matches an existing message's Message-ID).
        rows = session.scalars(
            select(EmailMessage.thread_id).where(
                EmailMessage.project_id == project_id,
                EmailMessage.message_id.in_(candidate_ids),
            )
        ).all()
        matched_thread_ids.update(rows)

    if parsed.message_id:
        # Direction 2: an already-imported message references THIS
        # message's Message-ID (this message is a parent/ancestor that
        # arrived after its child) — handles out-of-send-order import.
        #
        # Pre-commit review fix: a plain substring match (`.contains()`,
        # i.e. SQL LIKE '%id%') is NOT safe here, despite Message-IDs
        # looking syntactically distinctive — one Message-ID can be a
        # literal substring of another (e.g. "42@mail.example.com" is a
        # substring of "942@mail.example.com"), which caused a genuinely
        # unrelated message to be merged into an existing thread purely by
        # coincidence, reproduced against the real database during review.
        # in_reply_to/references are stored as space-joined tokens (see
        # EmailMessage.references/in_reply_to docstrings), so matching on a
        # whole token via a word-boundary regex (Postgres's `~` operator
        # with `\m`/`\M` anchors) fixes this without changing the storage
        # shape: a candidate id must appear as a complete whitespace/
        # string-boundary-delimited token, never as part of a longer id.
        token_pattern = r"\m" + re.escape(parsed.message_id) + r"\M"
        rows = session.execute(
            select(EmailMessage.thread_id).where(
                EmailMessage.project_id == project_id,
                EmailMessage.in_reply_to.op("~")(token_pattern)
                | EmailMessage.references.op("~")(token_pattern),
            )
        ).scalars().all()
        matched_thread_ids.update(rows)

    if not matched_thread_ids:
        thread = EmailThread(project_id=project_id, subject=parsed.subject)
        session.add(thread)
        session.flush()
        return thread

    canonical_id = min(matched_thread_ids)
    other_ids = matched_thread_ids - {canonical_id}
    if other_ids:
        _merge_threads(session, canonical_id=canonical_id, other_ids=other_ids)

    canonical_thread = session.get(EmailThread, canonical_id)
    assert canonical_thread is not None  # one of matched_thread_ids, just queried from this same project
    return canonical_thread


def _candidate_message_ids(parsed: ParsedEmail) -> set[str]:
    ids: set[str] = set(parsed.in_reply_to) | set(parsed.references)
    if parsed.message_id:
        ids.add(parsed.message_id)
    return {i for i in ids if i}


def _merge_threads(session: Session, *, canonical_id: int, other_ids: set[int]) -> None:
    """Reassign every message from `other_ids` onto `canonical_id` and
    delete the now-empty thread rows. Only ever called when a new message's
    headers prove two previously-separate threads are actually one
    conversation — never a subject-based guess."""
    session.execute(
        EmailMessage.__table__.update()
        .where(EmailMessage.thread_id.in_(other_ids))
        .values(thread_id=canonical_id)
    )
    session.execute(EmailThread.__table__.delete().where(EmailThread.id.in_(other_ids)))
    session.flush()
