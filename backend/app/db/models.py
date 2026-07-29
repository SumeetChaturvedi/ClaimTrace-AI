from datetime import date, datetime
from typing import Any, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
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
    """An uploaded source document; doc_type/doc_date/referenced_ids are filled in by
    the (not-yet-built) classification step of the ingestion pipeline."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    doc_type: Mapped[Optional[str]] = mapped_column(Text)
    doc_date: Mapped[Optional[date]] = mapped_column(Date)
    referenced_ids: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text))
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    raw_text_path: Mapped[str] = mapped_column(Text, nullable=False)

    project: Mapped["Project"] = relationship(back_populates="documents")
    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="document")


class DocumentChunk(Base):
    """A retrieval unit for search_documents(); embedding dim (384) matches
    sentence-transformers/all-MiniLM-L6-v2 per PROJECT_PLAN.md — change both
    if the embedding model changes."""

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
