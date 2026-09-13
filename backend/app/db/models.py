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
    func,
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
