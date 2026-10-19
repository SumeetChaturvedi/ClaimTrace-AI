import uuid
from datetime import date, datetime
from typing import Any, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Project(Base):
    """A claims-investigation workspace; V0 seeds exactly one default project."""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    documents: Mapped[list["Document"]] = relationship(back_populates="project")
    investigations: Mapped[list["Investigation"]] = relationship(
        back_populates="project"
    )


class Document(Base):
    """An uploaded source document; doc_type/doc_date/referenced_ids are filled in
    deterministically from its own extracted text (see app/ingestion/metadata.py),
    never by AI classification.

    status/processing_error/updated_at (Phase 3: Project + Document Foundation)
    make the ingestion pipeline's real lifecycle observable and persisted,
    rather than only ever succeeding-or-raising within a single request:
        uploaded -> processing -> ready
                                -> failed (processing_error set)
    raw_text_path is nullable because a row now exists (status='uploaded' or
    'processing') before extraction has necessarily produced one; it is set
    once extraction succeeds, alongside status moving to 'ready'.

    These three columns were added to an already-existing, already-populated
    table via a safe, additive, idempotent ALTER (see
    app/db/init_db.py's ensure_document_lifecycle_columns) rather than a
    destructive rebuild — this project has no migration tool, and
    Base.metadata.create_all() only creates missing tables, never alters
    existing ones. Every one of the 130+ real documents ingested before this
    phase is retrofitted to status='ready' (accurate: they are already
    extracted, chunked, and embedded), and updated_at backfilled from their
    existing uploaded_at, ensuring nothing is treated as running while the
    server is checking that everything else stays untouched."""

    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(
            "status IN ('uploaded', 'processing', 'ready', 'failed')",
            name="ck_documents_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    doc_type: Mapped[Optional[str]] = mapped_column(Text)
    doc_date: Mapped[Optional[date]] = mapped_column(Date)
    referenced_ids: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text))
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="ready")
    processing_error: Mapped[Optional[str]] = mapped_column(Text)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    raw_text_path: Mapped[Optional[str]] = mapped_column(Text)

    project: Mapped["Project"] = relationship(back_populates="documents")
    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="document")


class DocumentChunk(Base):
    """A retrieval unit for search_documents(); embedding dim (384) matches
    sentence-transformers/all-MiniLM-L6-v2 per PROJECT_PLAN.md — change both
    if the embedding model changes.

    page_number's meaning depends on the parent Document's own file format
    (Phase 7: Multi-Format Evidence): for a PDF it is a true page number
    (app/ingestion/extraction.py); for a DOCX it is a 1-based paragraph
    ordinal (app/ingestion/docx_extraction.py), since DOCX has no reliable
    native page concept. Both are real, stable, honest positions in the
    source file — never fabricated — but they are not the same kind of
    thing, which is why the frontend labels this "Page N" or "Paragraph N"
    depending on the citing document's filename extension (see
    frontend/src/lib/documentFormat.ts) rather than always saying "Page"."""

    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    page_number: Mapped[Optional[int]] = mapped_column(Integer)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(384))

    document: Mapped["Document"] = relationship(back_populates="chunks")


class Investigation(Base):
    """A single natural-language investigation question and its lifecycle status."""

    __tablename__ = "investigations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default="pending",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    project: Mapped["Project"] = relationship(back_populates="investigations")
    steps: Mapped[list["InvestigationStep"]] = relationship(
        back_populates="investigation"
    )
    findings: Mapped[list["DossierFinding"]] = relationship(
        back_populates="investigation"
    )


class InvestigationStep(Base):
    """One append-only tool call in the agent loop's trail — the investigation's audit log."""

    __tablename__ = "investigation_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    investigation_id: Mapped[int] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
    )
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    tool_called: Mapped[Optional[str]] = mapped_column(Text)
    tool_input: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    tool_output: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    agent_reasoning: Mapped[Optional[str]] = mapped_column(Text)

    investigation: Mapped["Investigation"] = relationship(back_populates="steps")


class DossierFinding(Base):
    """One labeled, cited claim in the final dossier; `verified` reflects the
    deterministic citation check, never the model's own say-so."""

    __tablename__ = "dossier_findings"
    __table_args__ = (
        CheckConstraint(
            "finding_type IN ('FACT', 'INFERENCE', 'CONTRADICTION', 'GAP', 'UNVERIFIED')",
            name="ck_dossier_findings_finding_type",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    investigation_id: Mapped[int] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
    )
    finding_type: Mapped[str] = mapped_column(Text, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    source_document_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("documents.id"),
    )
    source_page: Mapped[Optional[int]] = mapped_column(Integer)
    source_excerpt: Mapped[Optional[str]] = mapped_column(Text)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    investigation: Mapped["Investigation"] = relationship(back_populates="findings")


class InvestigationRecord(Base):
    """A persistent, project-owned investigation (Phase 2: Persistent
    Investigations) — one real POST /investigate run, kept so the
    Investigation Workspace can be reopened after a refresh/restart without
    re-querying Gemini.

    Deliberately a NEW table, not a reuse of `Investigation` above:
    `Investigation`/`InvestigationStep`/`DossierFinding` were never wired
    into any production code path (confirmed by grep — nothing constructs
    or writes to them), and their shape doesn't fit what actually needs
    persisting here. `DossierFinding` in particular models a labeled,
    typed claim (FACT/INFERENCE/CONTRADICTION/GAP/UNVERIFIED) with a single
    source document/page/excerpt — a different, more elaborate concept than
    a plain Citation (document_id, page, chunk_id, relevance_score,
    chunk_text), and forcing Citation's shape into it would mean either
    dropping fields the frontend needs (chunk_id, relevance_score) or
    inventing a finding_type classification with no real backing. Since
    this project has no migration tool (schema is created via
    Base.metadata.create_all(), which only adds missing tables and never
    alters existing ones — see app/db/init_db.py), a new table is also the
    only option that requires no destructive ALTER of already-created
    tables and stays reproducible from a clean database.

    A UUID primary key (rather than autoincrement) matches what the
    frontend already generates client-side for session-local investigation
    ids (crypto.randomUUID(), see the pre-Phase-2 sessionInvestigations.ts)
    and is safe to hand back in a URL without exposing a sequential count.
    """

    __tablename__ = "investigation_records"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'completed', 'failed')",
            name="ck_investigation_records_status",
        ),
        Index("ix_investigation_records_project_id", "project_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="running")
    answer: Mapped[Optional[str]] = mapped_column(Text)
    reasoning_steps: Mapped[Optional[list[str]]] = mapped_column(JSONB)
    # Phase 4 (Timeline Productization): the investigation's own structured
    # TimelineEntry list (app/agent/models.py), persisted as-is so reopening
    # a completed investigation returns the same timeline it produced at run
    # time without re-invoking Gemini or rebuilding it. Added via a safe,
    # additive ALTER (see ensure_investigation_timeline_column in
    # app/db/init_db.py) since this table already has real rows. None (not
    # []) for every investigation that predates this column — the API layer
    # treats that identically to an empty timeline, never as an error.
    timeline: Mapped[Optional[list[dict]]] = mapped_column(JSONB)
    # Phase 5 (Contract Intelligence Productization): the investigation's own
    # retrieved ContractClause list (app/agent/models.py), persisted as-is —
    # same additive-ALTER pattern as `timeline` above (see
    # ensure_investigation_contract_clauses_column in app/db/init_db.py).
    # None (not []) for every investigation that predates this column or
    # genuinely retrieved no clauses; the API layer treats both identically.
    contract_clauses: Mapped[Optional[list[dict]]] = mapped_column(JSONB)
    # Phase 8B.2 (Backend Event Extractor): the investigation's own
    # extracted ExtractedEvent list (app/agent/models.py), persisted as-is —
    # same additive-ALTER pattern as `timeline`/`contract_clauses` above
    # (see ensure_investigation_events_columns in app/db/init_db.py).
    # Unlike those two, None here is NOT interchangeable with []: None means
    # either "predates this column" or "extraction failed for this run"
    # (see `events_error`); [] means extraction genuinely ran and found no
    # events. The API layer (app/api/routes/investigations.py) distinguishes
    # all three cases rather than collapsing them.
    events: Mapped[Optional[list[dict]]] = mapped_column(JSONB)
    # Non-None only when event extraction raised for this run and could not
    # complete — `events` is then also None (there is nothing to show), and
    # this carries a human-readable reason. Never set merely because
    # extraction found zero events (a legitimate outcome, not a failure).
    events_error: Mapped[Optional[str]] = mapped_column(Text)
    # Phase 8B.2 Quality Remediation: True when the extraction response was
    # cut off mid-array and some candidates had to be dropped as incomplete
    # — see InvestigationResponse.events_truncated's own docstring. A plain
    # boolean with a server default (unlike events/events_error, it has no
    # "predates this column" ambiguity to represent: an investigation from
    # before this column existed is correctly described as "not truncated").
    events_truncated: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    # Phase 1 (Fix Existing Investigation Pipeline Gaps): True when the
    # LLM provider's own response metadata reported that `answer` was cut
    # off by its output-token budget (see InvestigationResponse.answer_
    # truncated's own docstring) -- a plain boolean with a real default,
    # same reasoning as events_truncated above: "not truncated" is simply
    # correct for every investigation that predates this column.
    answer_truncated: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    # The raw, internal reason the Investigation Loop's evidence-gathering
    # stopped for this run (InvestigationLoop.LoopRunResult.stopping_reason
    # — e.g. 'sufficient', 'unsupported_remediation', 'max_iterations_
    # reached'). Nullable, with NO default: unlike answer_truncated/events_
    # truncated above, "unknown" (NULL) is the only honest value for a
    # legacy investigation that predates this column, since this phase has
    # no way to know what a pre-existing run's loop actually did. The API
    # layer (app/api/routes/investigations.py) maps a non-NULL value onto a
    # plain-language `evidence_limitation` message for anything an
    # investigator sees, and treats NULL identically to 'sufficient' (no
    # limitation to report) -- never as a failure or a fabricated reason.
    stopping_reason: Mapped[Optional[str]] = mapped_column(Text)
    # Phase 2a (Preserve Investigation Attempt History): 1-based, incremented
    # by retry_investigation() each time this record is retried. A record
    # that predates this column is correctly described as attempt 1 (from
    # this system's own persistence perspective, it has only ever had one
    # known attempt) -- a real default, same reasoning as answer_truncated/
    # events_truncated above, never an "unknown" value is needed here.
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    error: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    project: Mapped["Project"] = relationship()
    citations: Mapped[list["InvestigationRecordCitation"]] = relationship(
        back_populates="investigation",
        order_by="InvestigationRecordCitation.ordinal",
        cascade="all, delete-orphan",
    )


class InvestigationRecordCitation(Base):
    """One persisted Citation belonging to an InvestigationRecord's final
    answer. Stores only stable references (document_id, chunk_id) plus the
    citation's own small fields (page, relevance_score) and the matched
    chunk_text already returned to the frontend at investigation time —
    never a copy of the full document, which stays reachable via
    document_id through the existing Document/DocumentChunk tables and the
    project-scoped PDF endpoint. `ordinal` preserves the exact order
    ReasoningEngine returned the citations in (confidence-ranked), so
    reopening a persisted investigation reproduces the same Sources order
    as the original run."""

    __tablename__ = "investigation_record_citations"
    __table_args__ = (Index("ix_investigation_record_citations_investigation_id", "investigation_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("investigation_records.id", ondelete="CASCADE"),
        nullable=False,
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), nullable=False)
    chunk_id: Mapped[int] = mapped_column(ForeignKey("document_chunks.id"), nullable=False)
    page: Mapped[Optional[int]] = mapped_column(Integer)
    relevance_score: Mapped[float] = mapped_column(Float, nullable=False)
    chunk_text: Mapped[Optional[str]] = mapped_column(Text)

    investigation: Mapped["InvestigationRecord"] = relationship(back_populates="citations")


class InvestigationRecordAttempt(Base):
    """A frozen snapshot of one PREVIOUS, superseded attempt of an
    InvestigationRecord (Phase 2a: Preserve Investigation Attempt History) --
    captured by retry_investigation() (app/api/routes/investigations.py)
    immediately before it clears and reruns the live record, so a retry can
    never destroy what the previous attempt actually produced.

    Deliberately NOT a reuse of the live InvestigationRecord row itself:
    that row always represents the CURRENT/latest attempt, so every
    existing GET/list caller keeps its exact current meaning with zero
    reinterpretation. This table holds only attempts that have since been
    superseded by a later retry -- a never-retried investigation has zero
    rows here; its one and only attempt is simply the live record, numbered
    1 via InvestigationRecord.attempt_number.

    Citations are stored as a plain JSONB array (each element shaped like
    Citation.model_dump()) rather than a child table like
    InvestigationRecordCitation: a snapshot is read-only and append-only
    for its entire life, so it never needs the relational ordinal/
    foreign-key machinery a live, re-populated citation set does -- this
    keeps the feature to one new table, not two.

    New table -- Base.metadata.create_all() (app/db/init_db.py) creates it
    with no ALTER needed, exactly like every other table in this file (see
    InvestigationRecord's own docstring for why a new table is this
    project's migration-free option)."""

    __tablename__ = "investigation_record_attempts"
    __table_args__ = (
        UniqueConstraint(
            "investigation_id", "attempt_number", name="ux_investigation_record_attempts_number"
        ),
        Index("ix_investigation_record_attempts_investigation_id", "investigation_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("investigation_records.id", ondelete="CASCADE"),
        nullable=False,
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[Optional[str]] = mapped_column(Text)
    reasoning_steps: Mapped[Optional[list[str]]] = mapped_column(JSONB)
    # Citation.model_dump() shape per element -- see class docstring for why
    # this is a plain JSONB array rather than a child table.
    citations: Mapped[Optional[list[dict]]] = mapped_column(JSONB)
    timeline: Mapped[Optional[list[dict]]] = mapped_column(JSONB)
    contract_clauses: Mapped[Optional[list[dict]]] = mapped_column(JSONB)
    events: Mapped[Optional[list[dict]]] = mapped_column(JSONB)
    events_error: Mapped[Optional[str]] = mapped_column(Text)
    events_truncated: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    answer_truncated: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    stopping_reason: Mapped[Optional[str]] = mapped_column(Text)
    error: Mapped[Optional[str]] = mapped_column(Text)
    # When this attempt itself last changed (its own completion/failure
    # time) -- captured from the live record's own `updated_at` BEFORE
    # retry processing mutates anything on it. Never re-derived after the
    # fact: by the time the new attempt starts, the live record's
    # updated_at would already reflect the NEW attempt's start, not this
    # (previous) attempt's real finish time.
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    snapshotted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class EmailThread(Base):
    """A project-scoped, conservatively-reconstructed email conversation
    (Phase 8A: Email Thread Intelligence). Built deterministically from
    Message-ID/In-Reply-To/References headers only (see
    app/email_ingestion/threading.py) — never from subject-matching alone,
    so a thread here is never a manufactured relationship the source
    headers don't actually support. A message with no header linkage to any
    other message becomes a thread of exactly one message, not merged into
    anything else.

    New table, not a column added to an existing one — Base.metadata.create_all()
    (app/db/init_db.py) creates it automatically with no ALTER required,
    exactly like every other table in this file."""

    __tablename__ = "email_threads"
    __table_args__ = (Index("ix_email_threads_project_id", "project_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    # The display subject for the thread — the first message's own Subject
    # header, kept exactly as imported (not normalized/cleaned), since this
    # is a label, not a matching key. Threads reconstructed from a message
    # with no Subject header at all fall back to a generic "(no subject)"
    # at the API layer, never a fabricated one persisted here.
    subject: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    project: Mapped["Project"] = relationship()
    messages: Mapped[list["EmailMessage"]] = relationship(
        back_populates="thread",
        order_by="EmailMessage.sent_at",
    )


class EmailMessage(Base):
    """One imported email message (Phase 8A: Email Thread Intelligence).

    Deliberately keyed 1:1 with its own `Document` row via a shared primary
    key (document_id is both this table's PK and its FK to documents.id,
    the same "narrow join table" pattern already used nowhere else in this
    schema but standard SQLAlchemy practice for a strict 1:1) rather than a
    redundant surrogate id. The message's plain-text body is the Document's
    extracted text, chunked/embedded/indexed through the EXISTING,
    completely unmodified app/ingestion/indexing.py pipeline — this is what
    lets an email-body citation be an ordinary Citation(document_id,
    chunk_id, ...) with zero schema change to Citation/TimelineEntry/
    InvestigationResponse (see app/agent/models.py): the frontend already
    resolves document_type/filename for a citation via a separate
    GET /documents lookup rather than embedding them in Citation, exactly
    the seam DOCX reused (Phase 7) and this reuses again.

    Fields that cannot be reliably populated from an arbitrary .eml import
    are left nullable and are never fabricated: provider_message_id/
    provider_thread_id (only ever known if a future live-mailbox connector
    supplies them — plain .eml files have no such concept), html_body (a
    plain-text-only message has none), in_reply_to/references (headers that
    simply may not be present on a given message)."""

    __tablename__ = "email_messages"
    __table_args__ = (
        Index("ix_email_messages_project_id", "project_id"),
        Index("ix_email_messages_thread_id", "thread_id"),
        # A given RFC 822 Message-ID is unique within a project — this is
        # the load-bearing uniqueness constraint dedup relies on (see
        # app/email_ingestion/dedup.py): re-importing a .eml whose
        # Message-ID already exists for this project is caught here, at
        # the database level, not just by an application-side check that
        # could race under concurrent imports. NULL message_ids (an .eml
        # with no Message-ID header) are not constrained by this index —
        # Postgres treats NULLs as distinct for a unique index — so those
        # fall back entirely to the content_hash dedup path instead.
        Index(
            "ux_email_messages_project_message_id",
            "project_id",
            "message_id",
            unique=True,
            postgresql_where=text("message_id IS NOT NULL"),
        ),
        # Pre-commit review fix: the content_hash fallback path (used only
        # when message_id is absent — see dedup.py) had no database-level
        # backstop at all, unlike the message_id path above. Two concurrent
        # imports of the same Message-ID-less message could both pass the
        # application-level dedup pre-check before either commits, each
        # creating its own fully-indexed, searchable "EMAIL" Document — a
        # silent, undetected duplicate in the evidence corpus. This partial
        # unique index closes that race the same way the message_id index
        # already does, scoped to exactly the rows that actually rely on
        # content_hash for identity (message_id IS NULL) so it can never
        # reject two genuinely different messages that merely happen to
        # share content but have distinct real Message-IDs.
        Index(
            "ux_email_messages_project_content_hash_no_message_id",
            "project_id",
            "content_hash",
            unique=True,
            postgresql_where=text("message_id IS NULL"),
        ),
    )

    # Shared primary key with the owning Document row (see class docstring).
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        primary_key=True,
    )
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    thread_id: Mapped[int] = mapped_column(
        ForeignKey("email_threads.id", ondelete="CASCADE"),
        nullable=False,
    )

    import_source: Mapped[str] = mapped_column(Text, nullable=False, server_default="eml_import")

    # Original RFC 822 Message-ID header, angle brackets stripped — the
    # primary deterministic identity for threading and dedup. None for a
    # message whose .eml genuinely has no Message-ID header (dedup then
    # falls back to content_hash — see app/email_ingestion/dedup.py).
    message_id: Mapped[Optional[str]] = mapped_column(Text)
    # Only ever populated by a future live-connector import path — a plain
    # .eml file carries no provider-internal id. Kept now so the schema
    # doesn't need a later migration to add it.
    provider_message_id: Mapped[Optional[str]] = mapped_column(Text)
    provider_thread_id: Mapped[Optional[str]] = mapped_column(Text)

    in_reply_to: Mapped[Optional[str]] = mapped_column(Text)
    # Space-joined References header values, oldest first, exactly as the
    # header itself orders them — kept as one text field (not a separate
    # table) since nothing currently queries into individual reference
    # entries; app/email_ingestion/threading.py splits this at import time
    # when building the thread graph, from the parsed header list, not by
    # re-parsing this stored string.
    references: Mapped[Optional[str]] = mapped_column(Text)

    sender_name: Mapped[Optional[str]] = mapped_column(Text)
    sender_email: Mapped[Optional[str]] = mapped_column(Text)
    # Recipient lists stored as Postgres text[] — each entry a real address
    # (optionally "Name <email>") taken verbatim from the To/Cc header,
    # never deduplicated or reordered.
    to_recipients: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text))
    cc_recipients: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text))

    subject: Mapped[Optional[str]] = mapped_column(Text)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    # True only when the original Date header carried no parseable
    # timezone/offset at all (rare, but real exports vary) — surfaced so
    # the frontend can show "time zone unknown" rather than implying a
    # false precision on sent_at.
    sent_at_timezone_unknown: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    html_body: Mapped[Optional[str]] = mapped_column(Text)

    # Dedup fallback for a message with no Message-ID — see
    # app/email_ingestion/dedup.py for exactly what goes into this hash.
    # Always computed (even when message_id is present) so a later
    # Message-ID-based match and a content-identical duplicate are both
    # detectable through one consistent mechanism.
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)

    raw_eml_path: Mapped[Optional[str]] = mapped_column(Text)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    document: Mapped["Document"] = relationship()
    project: Mapped["Project"] = relationship()
    thread: Mapped["EmailThread"] = relationship(back_populates="messages")
    attachments: Mapped[list["EmailAttachment"]] = relationship(
        back_populates="message",
        order_by="EmailAttachment.id",
        cascade="all, delete-orphan",
    )


class EmailAttachment(Base):
    """One attachment extracted from an EmailMessage (Phase 8A: Email
    Thread Intelligence).

    document_id is populated only for a supported attachment type (PDF or
    DOCX) that was successfully run through the EXISTING, completely
    unmodified app/ingestion/pipeline.py's ingest_document() — at that
    point the attachment IS a normal Document, indexed and citable exactly
    like any other, and this row is purely the provenance link back to the
    email that supplied it. document_id is NULL for an unsupported format
    or one that failed pre-flight validation; status explains why, and no
    second storage/extraction system is built for those — their bytes are
    deliberately not persisted (see app/email_ingestion/pipeline.py), only
    their real, observed metadata (filename/content_type/size/hash).

    Phase W2.0 (Shared Image Preservation Foundation) adds exactly one
    exception to that "bytes not persisted" rule: a recognized image
    attachment (JPEG/PNG/GIF/WEBP, detected by real content signature --
    see app/ingestion/image_validation.py — never by filename or the
    email's own untrusted MIME header) now gets status
    'stored_pending_processing' and its original bytes preserved under
    app/ingestion/storage.py's save_image(), mirroring
    WhatsAppMediaAttachment's own 'stored_pending_processing' contract
    exactly: the original is genuinely available to open/download, but
    this phase makes no claim it has been OCR'd, described, or indexed.
    storage_key/detected_extension/width_px/height_px are populated only
    for that status (and, in a future phase, 'processed' once a real
    Document exists for it); they stay NULL for every other status,
    including the pre-existing 'unsupported_format'/'rejected'/'failed'
    outcomes this phase does not change the meaning of.

    These four columns were added to an already-existing, already-
    populated table via a safe, additive, idempotent ALTER (see
    app/db/init_db.py's ensure_email_attachment_image_columns), the same
    pattern already used for documents.status/processing_error/updated_at
    — Base.metadata.create_all() only creates tables that don't exist yet,
    it never alters one that already does."""

    __tablename__ = "email_attachments"
    __table_args__ = (Index("ix_email_attachments_message_id", "message_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message_id: Mapped[int] = mapped_column(
        ForeignKey("email_messages.document_id", ondelete="CASCADE"),
        nullable=False,
    )
    # Set only when this attachment became a real, indexed Document (see
    # class docstring) — the existing Document row, not a duplicate of its
    # fields.
    document_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"),
    )

    filename: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[Optional[str]] = mapped_column(Text)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(Text, nullable=False)
    processing_error: Mapped[Optional[str]] = mapped_column(Text)

    # Phase W2.0 -- see class docstring. Populated only when a preserved
    # original actually exists on disk (status='stored_pending_processing'
    # today); NULL for every status that predates or doesn't involve it.
    storage_key: Mapped[Optional[str]] = mapped_column(Text)
    detected_extension: Mapped[Optional[str]] = mapped_column(Text)
    width_px: Mapped[Optional[int]] = mapped_column(Integer)
    height_px: Mapped[Optional[int]] = mapped_column(Integer)

    message: Mapped["EmailMessage"] = relationship(back_populates="attachments")
    document: Mapped[Optional["Document"]] = relationship()


class ConnectedMailbox(Base):
    """One external mailbox (Gmail today; Outlook later) connected to a
    single project for automatic import (Phase 1: Gmail Integration).

    Brand-new table — no ALTER needed, created automatically by
    Base.metadata.create_all() exactly like EmailThread/EmailMessage/
    EmailAttachment were when Phase 8A introduced them (see
    EmailThread's own docstring for why this project's migration
    convention treats a new table this way).

    Deliberately scoped to `project_id`, never to a "user" — this
    application has no user/account model at all (confirmed by inspecting
    the full schema and app/main.py before adding this table: no
    authentication middleware, no session mechanism, nothing resembling a
    login). Project scoping is therefore not a deliberately weaker
    substitute for per-user authorization here, it is the SAME boundary
    every other endpoint in this app already relies on exclusively
    (projects.py, project_documents.py, project_emails.py, investigations.py
    all 404 identically for "doesn't exist" and "belongs to another
    project," never anything stronger). Anyone with access to this
    ClaimTrace instance's API can already upload documents, run
    investigations, or import email for any project; this table inherits
    that same structural limitation rather than introducing a new one —
    see the Phase 1 implementation report for the full discussion.

    `provider` is a free-text field, like EmailMessage.import_source,
    deliberately not a CheckConstraint: Outlook is a known near-term
    addition and a value this field doesn't yet accept should never need
    a schema change to permit, only an application-level change.

    `encrypted_refresh_token` is nullable specifically so disconnect can
    set it to NULL (never merely flip a status flag while leaving the
    secret recoverable) — see app/api/routes/project_mailboxes.py's
    disconnect handler. It is never decrypted or returned by any API
    response; see app/email_sync/token_crypto.py for the only two
    functions allowed to touch it.

    `sync_cursor` is Gmail's own historyId (a provider-defined opaque
    string, not a timestamp) once an initial full sync has completed;
    NULL means "no successful sync yet, or the stored cursor expired and a
    fresh full sync is required" (see app/email_sync/orchestrator.py)."""

    __tablename__ = "connected_mailboxes"
    __table_args__ = (
        CheckConstraint(
            "status IN ('connected', 'needs_reauth', 'disconnected')",
            name="ck_connected_mailboxes_status",
        ),
        UniqueConstraint("project_id", "external_email", name="ux_connected_mailboxes_project_email"),
        Index("ix_connected_mailboxes_project_id", "project_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    external_email: Mapped[str] = mapped_column(Text, nullable=False)
    encrypted_refresh_token: Mapped[Optional[str]] = mapped_column(Text)
    granted_scope: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="connected")
    sync_cursor: Mapped[Optional[str]] = mapped_column(Text)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_sync_error: Mapped[Optional[str]] = mapped_column(Text)
    connected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    project: Mapped["Project"] = relationship()


class WhatsAppChat(Base):
    """One imported WhatsApp chat export (Phase W1: WhatsApp Export
    Ingestion) -- the project-scoped conversation/group identity, mirroring
    EmailThread's own role exactly. `title` is derived only from the
    uploaded export's own filename (see app/whatsapp_ingestion/pipeline.py)
    -- a WhatsApp text export carries no analogue of an email Subject
    header naming the conversation, so nothing here is fabricated from
    message content.

    New table -- Base.metadata.create_all() (app/db/init_db.py) creates it
    automatically with no ALTER required, exactly like every other table
    in this file."""

    __tablename__ = "whatsapp_chats"
    __table_args__ = (Index("ix_whatsapp_chats_project_id", "project_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[Optional[str]] = mapped_column(Text)
    source_export_filename: Mapped[str] = mapped_column(Text, nullable=False)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    project: Mapped["Project"] = relationship()
    messages: Mapped[list["WhatsAppMessage"]] = relationship(
        back_populates="chat",
        order_by="WhatsAppMessage.sequence_index",
    )


class WhatsAppMessage(Base):
    """One imported WhatsApp message (Phase W1: WhatsApp Export Ingestion).

    Deliberately keyed 1:1 with its own `Document` row via a shared primary
    key, exactly mirroring EmailMessage's own "narrow join table" pattern
    (see that class's docstring for the full rationale) -- one ordinary
    Document per message, never a multi-message Document whose chunk
    boundaries could span more than one message's text. The message's own
    text is that Document's extracted text, chunked/embedded/indexed
    through the EXISTING, completely unmodified app/ingestion/indexing.py
    pipeline -- this is what lets a WhatsApp-message citation be an
    ordinary Citation(document_id, chunk_id, ...) with zero schema change
    to Citation/TimelineEntry/InvestigationResponse, the same seam
    EMAIL/DOCX already reuse.

    content_hash is the ONLY dedup identity (see
    app/whatsapp_ingestion/dedup.py's own docstring for why -- a WhatsApp
    export has no Message-ID analogue at all, unlike email's two-tier
    scheme). sent_at has NO timezone component (DateTime(timezone=False)):
    a WhatsApp export's timestamp is the device's own local time with no
    recorded offset, and storing it as timezone-aware would silently
    imply a precision that was never actually present in the source."""

    __tablename__ = "whatsapp_messages"
    __table_args__ = (
        CheckConstraint(
            "message_type IN ('text', 'system', 'deleted', 'media')",
            name="ck_whatsapp_messages_message_type",
        ),
        Index("ix_whatsapp_messages_project_id", "project_id"),
        Index("ix_whatsapp_messages_chat_id", "chat_id"),
        # The only dedup backstop available (see dedup.py) -- always
        # enforced, never partial/conditional, since there is no stronger
        # identity tier a WhatsApp export could ever supply for this to
        # defer to. Scoped to chat_id, not project_id, so two different
        # chats sharing an identical (sender, timestamp, text) tuple --
        # an extraordinary coincidence, but not impossible -- are never
        # wrongly rejected as duplicates of each other.
        UniqueConstraint("chat_id", "content_hash", name="ux_whatsapp_messages_chat_content_hash"),
    )

    # Shared primary key with the owning Document row (see class docstring).
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        primary_key=True,
    )
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    chat_id: Mapped[int] = mapped_column(
        ForeignKey("whatsapp_chats.id", ondelete="CASCADE"),
        nullable=False,
    )

    # 0-based position within this export -- the one ordering signal that
    # is always reliable, even when sent_at is ambiguous or entirely
    # unparseable (see app/whatsapp_ingestion/parsing.py).
    sequence_index: Mapped[int] = mapped_column(Integer, nullable=False)

    # None for a system/group-event message -- never a fabricated
    # attribution (see parsing.py's own sender-detection docstring).
    sender_name: Mapped[Optional[str]] = mapped_column(Text)

    # Preserved exactly as exported, even when sent_at below is None --
    # never discarded just because it couldn't be normalized.
    raw_timestamp_text: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False))
    # True when day/month ordering could not be disambiguated from the
    # date alone (see parsing.py's own disambiguation rule) -- surfaced so
    # the frontend can show the uncertainty rather than implying a false
    # precision on sent_at.
    sent_at_ambiguous: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    message_type: Mapped[str] = mapped_column(Text, nullable=False)

    # Dedup identity -- see app/whatsapp_ingestion/dedup.py for exactly
    # what goes into this hash.
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)

    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    document: Mapped["Document"] = relationship()
    project: Mapped["Project"] = relationship()
    chat: Mapped["WhatsAppChat"] = relationship(back_populates="messages")
    media_attachments: Mapped[list["WhatsAppMediaAttachment"]] = relationship(
        back_populates="message",
        order_by="WhatsAppMediaAttachment.id",
        cascade="all, delete-orphan",
    )


class WhatsAppMediaAttachment(Base):
    """One media file referenced by a WhatsAppMessage (Phase W1: WhatsApp
    Export Ingestion).

    document_id is populated only for a supported document type (PDF or
    DOCX) successfully run through the EXISTING, completely unmodified
    app/ingestion/pipeline.py's ingest_document() -- mirrors
    EmailAttachment's own document_id contract exactly.

    Unlike EmailAttachment, an UNSUPPORTED-for-indexing media file's bytes
    are NOT discarded here -- the task's own explicit W1 requirement is to
    preserve original media bytes even when they can't yet be interpreted
    (the email-attachment precedent of dropping unsupported bytes is
    deliberately NOT followed for WhatsApp media). `storage_key`/
    `detected_extension` locate the preserved original on disk (see
    app/ingestion/storage.py's save_whatsapp_media) whenever `status` is
    'processed' or 'stored_pending_processing'; both are None only for
    'rejected' (failed pre-flight validation, e.g. empty/oversized) where
    nothing was ever written to disk at all.

    `status` deliberately keeps "the original is safely stored" and
    "whether it has been interpreted" as separate concerns -- a
    'stored_pending_processing' image is genuinely available to open/
    download, it is simply not yet OCR'd/described/transcribed (W2-W4,
    not this phase); nothing here ever claims understanding that hasn't
    happened."""

    __tablename__ = "whatsapp_media_attachments"
    __table_args__ = (
        CheckConstraint(
            "status IN ('processed', 'stored_pending_processing', 'unsupported_format', 'rejected', 'failed')",
            name="ck_whatsapp_media_attachments_status",
        ),
        Index("ix_whatsapp_media_attachments_message_id", "message_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message_id: Mapped[int] = mapped_column(
        ForeignKey("whatsapp_messages.document_id", ondelete="CASCADE"),
        nullable=False,
    )
    # Set only when this attachment became a real, indexed Document (see
    # class docstring) -- the existing Document row, not a duplicate of
    # its fields.
    document_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"),
    )

    # The filename as referenced in the chat export text -- metadata only,
    # NEVER used to build a filesystem path (see storage.py's
    # save_whatsapp_media, which always uses a fresh, server-generated key).
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[Optional[str]] = mapped_column(Text)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(Text, nullable=False)
    processing_error: Mapped[Optional[str]] = mapped_column(Text)

    # Where the preserved original lives on disk, in storage-key form (not
    # a raw path) -- see app/ingestion/storage.py's whatsapp_media_dir/
    # save_whatsapp_media. None for 'rejected' (nothing was ever stored).
    storage_key: Mapped[Optional[str]] = mapped_column(Text)
    detected_extension: Mapped[Optional[str]] = mapped_column(Text)

    message: Mapped["WhatsAppMessage"] = relationship(back_populates="media_attachments")
    document: Mapped[Optional["Document"]] = relationship()


class ProjectImageAsset(Base):
    """One image uploaded directly to a project as evidence, with no
    covering WhatsApp message or email (Phase W2.0: Shared Image
    Preservation Foundation).

    Unlike EmailAttachment/WhatsAppMediaAttachment, there is no parent
    message row at all here -- project_id is this table's own, direct
    provenance, and content_hash is deduplicated per-project at the
    database level (see the unique constraint below), mirroring how
    WhatsAppMessage/EmailMessage each dedupe within their own scope. This
    deliberately reuses WhatsAppMediaAttachment's column shape and status
    vocabulary ('stored_pending_processing' etc.) rather than inventing a
    third convention for the same kind of fact.

    document_id stays NULL in this phase -- no OCR/vision/Document
    creation happens here at all (W2.1+); it exists now only so a future
    phase can point this row at the real, indexed Document it eventually
    becomes, the same document_id contract WhatsAppMediaAttachment/
    EmailAttachment already use.

    New table -- Base.metadata.create_all() (app/db/init_db.py) creates it
    automatically with no ALTER required, exactly like WhatsAppChat/
    WhatsAppMessage/WhatsAppMediaAttachment were in Phase W1."""

    __tablename__ = "project_image_assets"
    __table_args__ = (
        CheckConstraint(
            "status IN ('stored_pending_processing', 'processed', 'rejected', 'failed')",
            name="ck_project_image_assets_status",
        ),
        # Defense-in-depth backstop (mirrors WhatsAppMessage's own
        # chat_id+content_hash constraint): an application-level dedup
        # pre-check is the first line of defense against re-uploading the
        # exact same image bytes to the same project, but a real DB
        # constraint is what actually prevents it under a concurrent
        # double-upload race, never just a best-effort check.
        UniqueConstraint("project_id", "content_hash", name="ux_project_image_assets_project_content_hash"),
        Index("ix_project_image_assets_project_id", "project_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"),
    )

    # The filename as uploaded -- metadata only, NEVER used to build a
    # filesystem path (see storage.py's save_image, which always uses a
    # fresh, server-generated key).
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[Optional[str]] = mapped_column(Text)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(Text, nullable=False)
    processing_error: Mapped[Optional[str]] = mapped_column(Text)

    storage_key: Mapped[Optional[str]] = mapped_column(Text)
    detected_extension: Mapped[Optional[str]] = mapped_column(Text)
    width_px: Mapped[Optional[int]] = mapped_column(Integer)
    height_px: Mapped[Optional[int]] = mapped_column(Integer)

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    project: Mapped["Project"] = relationship()
    document: Mapped[Optional["Document"]] = relationship()


class ImageOcrResult(Base):
    """Local Tesseract OCR output for one already-preserved image (Phase
    W2.1: Local OCR Foundation) -- DERIVED content, deliberately kept in
    its own table rather than added as columns on ProjectImageAsset/
    EmailAttachment/WhatsAppMediaAttachment, so the original evidence
    row's own fields (filename/content_hash/storage_key/detected_extension)
    are never at risk of being confused with, or overwritten by, this
    phase's output. Exactly one of the three parent FKs is set per row,
    enforced by ck_image_ocr_results_exactly_one_parent below -- never a
    polymorphic (attachment_type, attachment_id) pair with no real
    referential integrity. Each of the three FK columns also carries its
    own UniqueConstraint, so "at most one OCR result per source
    attachment" is a real database guarantee (Postgres treats every NULL
    as distinct, so rows belonging to the other two sources, which leave
    that column NULL, never collide with each other).

    status: 'pending' (row exists, OCR not yet attempted -- created the
    moment the source image is preserved, see
    app/ocr/pending.py's ensure_pending_ocr_result, called from each of
    the three ingestion paths) -> 'processing' (claimed by a batch run,
    see app/ocr/process_pending.py) -> 'completed' (Tesseract ran; text
    saved under ocr_text_path -- EMPTY text is a genuine, honest
    'completed' result, never 'failed') or 'failed' (missing executable,
    unavailable language, timeout, unreadable image, or any other real
    error -- `error` always set).

    ocr_text_path mirrors Document.raw_text_path's own convention: OCR
    text lives in its own server-managed file (app/ingestion/storage.py's
    save_ocr_text), never inline in this row and never logged -- this
    table only ever stores a path to it. (ocr_engine, ocr_engine_version,
    ocr_language) together are this phase's idempotency/provenance key
    (Phase W2.1 Section 7): a completed result is only reprocessed when
    one of these three no longer matches the currently configured
    engine/language, or an explicit --force override is given (see
    app/ocr/process_pending.py) -- never unconditionally re-run.

    W2.1 explicitly does NOT index this text as a Document/DocumentChunk,
    does not touch retrieval/citation verification, and is not read by
    any investigation code path -- that is W2.2's job, not this phase's.

    New table -- Base.metadata.create_all() (app/db/init_db.py) creates it
    automatically with no ALTER required, exactly like every table
    introduced in a prior phase of this project. The lease_token/
    lease_expires_at columns were added after this table was already
    live in some local installations (any database where the app had
    already been run against this phase's earlier, pre-lease code) --
    create_all() never alters a table that already exists, so
    app/db/init_db.py's ensure_image_ocr_result_lease_columns() retrofits
    them via a safe, additive, idempotent ALTER, same convention as every
    other ensure_* function in that module. No-op in effect on a clean
    database, where create_tables() already creates this table with both
    columns from the start."""

    __tablename__ = "image_ocr_results"
    __table_args__ = (
        CheckConstraint(
            "(project_image_asset_id IS NOT NULL)::int "
            "+ (email_attachment_id IS NOT NULL)::int "
            "+ (whatsapp_media_attachment_id IS NOT NULL)::int = 1",
            name="ck_image_ocr_results_exactly_one_parent",
        ),
        CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed')",
            name="ck_image_ocr_results_status",
        ),
        UniqueConstraint("project_image_asset_id", name="ux_image_ocr_results_project_image_asset_id"),
        UniqueConstraint("email_attachment_id", name="ux_image_ocr_results_email_attachment_id"),
        UniqueConstraint("whatsapp_media_attachment_id", name="ux_image_ocr_results_whatsapp_media_attachment_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Exactly one of these three is ever set -- see the CHECK constraint
    # above. ondelete="CASCADE" on all three: once the source evidence row
    # is gone (which itself only ever happens via a project/message
    # cascade -- nothing in this codebase deletes a single attachment in
    # isolation), there is nothing left for this derived-content row to
    # describe; keeping it around would be a dangling, meaningless record,
    # not preserved evidence.
    project_image_asset_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("project_image_assets.id", ondelete="CASCADE"),
    )
    email_attachment_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("email_attachments.id", ondelete="CASCADE"),
    )
    whatsapp_media_attachment_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("whatsapp_media_attachments.id", ondelete="CASCADE"),
    )

    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="pending")
    error: Mapped[Optional[str]] = mapped_column(Text)

    # Where the derived OCR text lives on disk (see app/ingestion/storage.py's
    # save_ocr_text) -- None until a 'completed' result actually writes one.
    ocr_text_path: Mapped[Optional[str]] = mapped_column(Text)

    ocr_engine: Mapped[str] = mapped_column(Text, nullable=False, server_default="tesseract")
    ocr_engine_version: Mapped[Optional[str]] = mapped_column(Text)
    ocr_language: Mapped[str] = mapped_column(Text, nullable=False, server_default="eng")

    processing_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Database-backed lease (W2.1 stale-processing recovery fix): a
    # 'processing' row is only ever reclaimable once lease_expires_at has
    # passed -- NOT based on how long ago processing_started_at was set.
    # lease_token is a fresh, random value assigned every time a row is
    # claimed or reclaimed (app/ocr/process_pending.py's
    # _claim_specific_rows); every later write this module makes to the
    # row (lease renewal, or the final completed/failed status) is a
    # conditional UPDATE keyed on this exact token, so a worker that has
    # lost the race -- another worker's claim already replaced this
    # value -- can never overwrite a newer result. Both columns are
    # cleared back to NULL whenever a row leaves 'processing' for
    # 'completed'/'failed', so they are only ever non-NULL while a row is
    # actively leased. See process_pending.py's own module docstring for
    # the full design.
    lease_token: Mapped[Optional[str]] = mapped_column(Text)
    lease_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    project_image_asset: Mapped[Optional["ProjectImageAsset"]] = relationship()
    email_attachment: Mapped[Optional["EmailAttachment"]] = relationship()
    whatsapp_media_attachment: Mapped[Optional["WhatsAppMediaAttachment"]] = relationship()
