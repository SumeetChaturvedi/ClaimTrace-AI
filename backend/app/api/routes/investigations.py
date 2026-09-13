"""Persistent, project-scoped investigations (Phase 2: Persistent
Investigations).

This module adds create/list/get/retry persistence AROUND the existing,
completely unmodified investigation engine (InvestigationService ->
InvestigationLoop -> InvestigationAgent -> retrieval/remediation ->
ReasoningEngine -> Gemini -> citation verification) — it never
re-implements, shortcuts, or duplicates any part of that pipeline. The
original POST /investigate (app/api/routes/investigate.py) is left
completely unchanged and still works exactly as before, as a stateless
one-shot call; these routes are the persistent alternative the frontend now
uses. Both share the exact same InvestigationService singleton via
get_investigation_service() (imported from investigate.py, not
re-declared), so there is exactly one investigation engine and exactly one
clause-repository/singleton lifecycle regardless of which route is called.

See app/db/models.py's InvestigationRecord docstring for why this persists
into new tables rather than the pre-existing, never-wired-up
Investigation/InvestigationStep/DossierFinding tables.
"""

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent import InvestigationService
from app.agent.models import DEFAULT_TOP_K, Citation, InvestigationRequest, TimelineEntry
from app.contracts.models import ContractClause
from app.agent.reasoning import ReasoningError
from app.api.routes.investigate import get_investigation_service
from app.db.models import InvestigationRecord, InvestigationRecordCitation, Project
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}/investigations", tags=["investigations"])


class InvestigationCreateRequest(BaseModel):
    """Body for POST .../investigations. project_id comes from the URL path
    (this router's prefix), not the body — unlike the flat, non-project-scoped
    InvestigationRequest (app/agent/models.py) these routes wrap, which still
    takes project_id in its body and is used internally, unchanged, to call
    the engine."""

    query: str = Field(min_length=1, description="Natural-language investigation question")
    top_k: int = Field(default=DEFAULT_TOP_K, gt=0, description="Max supporting chunks to consider")


class InvestigationRecordResponse(BaseModel):
    """The persisted investigation, in the same shape the frontend's
    (pre-Phase-2) session-local record already used — id/project_id/query/
    status/created_at, plus answer/citations/reasoning_steps flattened to
    top level exactly as InvestigationResponse (app/agent/models.py) already
    returns them, so the Workspace's existing rendering code needs no
    reshaping to consume it."""

    id: uuid.UUID
    project_id: int
    query: str
    status: str
    created_at: datetime
    updated_at: datetime
    answer: str | None = None
    citations: list[Citation] = Field(default_factory=list)
    reasoning_steps: list[str] = Field(default_factory=list)
    timeline: list[TimelineEntry] = Field(
        default_factory=list,
        description="Chronology produced by the run that completed this investigation (Phase 4); [] for investigations that predate this field or have none",
    )
    contract_clauses: list[ContractClause] = Field(
        default_factory=list,
        description="Contract clauses retrieved for this investigation (Phase 5); [] for investigations that predate this field or that genuinely retrieved none",
    )
    error: str | None = None


class InvestigationExecutionError(HTTPException):
    """Raised when an investigation record was created/persisted
    successfully but the underlying Gemini/reasoning run then failed. Unlike
    the plain string-detail HTTPException used elsewhere in this app, this
    carries the already-persisted investigation's id in a structured
    `detail` dict — FastAPI/Starlette allow any JSON-serializable value
    there — so the caller can still navigate to (and retry) the failed
    record instead of losing track of it just because the HTTP call
    itself returned an error status."""

    def __init__(self, status_code: int, message: str, investigation_id: uuid.UUID) -> None:
        super().__init__(status_code=status_code, detail={"message": message, "investigation_id": str(investigation_id)})


def _to_response(record: InvestigationRecord) -> InvestigationRecordResponse:
    return InvestigationRecordResponse(
        id=record.id,
        project_id=record.project_id,
        query=record.question,
        status=record.status,
        created_at=record.created_at,
        updated_at=record.updated_at,
        answer=record.answer,
        citations=[
            Citation(
                document_id=c.document_id,
                page=c.page,
                chunk_id=c.chunk_id,
                relevance_score=c.relevance_score,
                chunk_text=c.chunk_text,
            )
            for c in record.citations
        ],
        reasoning_steps=record.reasoning_steps or [],
        timeline=[TimelineEntry.model_validate(entry) for entry in (record.timeline or [])],
        contract_clauses=[ContractClause.model_validate(c) for c in (record.contract_clauses or [])],
        error=record.error,
    )


def _get_project_or_404(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def _get_record_or_404(db: Session, project_id: int, investigation_id: uuid.UUID) -> InvestigationRecord:
    """Look up `investigation_id` and confirm it belongs to `project_id`.
    A mismatch (the investigation is real, but under a different project)
    returns the same plain 404 as a nonexistent id — never a 403 — so a
    request against the wrong project can't even confirm the investigation
    exists elsewhere. Matches the same project-isolation pattern already
    used by app/api/routes/document_file.py."""
    record = db.get(InvestigationRecord, investigation_id)
    if record is None or record.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigation not found")
    return record


async def _run_and_persist(
    db: Session,
    record: InvestigationRecord,
    service: InvestigationService,
    query: str,
    top_k: int,
) -> None:
    """Execute the existing, unmodified investigation engine for `record`
    and persist the outcome onto it — completed with its answer/citations/
    reasoning steps, or failed with its error — so it is never left stuck
    at 'running'. This is the only place allowed to write InvestigationRecord
    fields derived from an engine run; it never re-implements, shortcuts, or
    reinterprets any part of what InvestigationService.investigate() does."""
    try:
        response = await service.investigate(InvestigationRequest(project_id=record.project_id, query=query, top_k=top_k))
    except ValueError as exc:
        record.status = "failed"
        record.error = str(exc)
        db.commit()
        raise InvestigationExecutionError(status.HTTP_400_BAD_REQUEST, str(exc), record.id) from exc
    except ReasoningError as exc:
        record.status = "failed"
        record.error = str(exc)
        db.commit()
        raise InvestigationExecutionError(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc), record.id) from exc
    except Exception as exc:
        logger.exception("Unexpected error during persisted investigation")
        record.status = "failed"
        record.error = "An unexpected error occurred while processing the investigation."
        db.commit()
        raise InvestigationExecutionError(status.HTTP_500_INTERNAL_SERVER_ERROR, record.error, record.id) from exc

    record.status = "completed"
    record.answer = response.answer
    record.reasoning_steps = response.reasoning_steps
    record.timeline = [entry.model_dump(mode="json") for entry in response.timeline]
    record.contract_clauses = [clause.model_dump(mode="json") for clause in response.contract_clauses]
    for ordinal, citation in enumerate(response.citations):
        db.add(
            InvestigationRecordCitation(
                investigation_id=record.id,
                ordinal=ordinal,
                document_id=citation.document_id,
                chunk_id=citation.chunk_id,
                page=citation.page,
                relevance_score=citation.relevance_score,
                chunk_text=citation.chunk_text,
            )
        )
    db.commit()


@router.post("", response_model=InvestigationRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_investigation(
    project_id: int,
    body: InvestigationCreateRequest,
    db: Session = Depends(get_db),
    service: InvestigationService = Depends(get_investigation_service),
) -> InvestigationRecordResponse:
    """Create a persistent investigation for `project_id` and run the
    existing investigation engine for it synchronously, exactly as
    POST /investigate already does — the difference is that the question,
    lifecycle status, and final result are now durably persisted rather
    than only ever returned once. Raises InvestigationExecutionError (still
    after persisting the failed state) if the engine run itself fails."""
    _get_project_or_404(db, project_id)

    record = InvestigationRecord(project_id=project_id, question=body.query, status="running")
    db.add(record)
    db.commit()
    db.refresh(record)

    await _run_and_persist(db, record, service, body.query, body.top_k)
    db.refresh(record)
    return _to_response(record)


@router.get("", response_model=list[InvestigationRecordResponse])
def list_investigations(project_id: int, db: Session = Depends(get_db)) -> list[InvestigationRecordResponse]:
    """List every persisted investigation for `project_id`, most recent
    first. 404s for a nonexistent project rather than silently returning an
    empty list, so a typo'd project id can't be mistaken for a real,
    empty project."""
    _get_project_or_404(db, project_id)
    records = db.scalars(
        select(InvestigationRecord)
        .where(InvestigationRecord.project_id == project_id)
        .order_by(InvestigationRecord.created_at.desc())
    ).all()
    return [_to_response(record) for record in records]


@router.get("/{investigation_id}", response_model=InvestigationRecordResponse)
def get_investigation(
    project_id: int,
    investigation_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> InvestigationRecordResponse:
    """Fetch one persisted investigation. Reopening an investigation from
    the frontend calls only this — never POST — so Gemini is never called
    again for an investigation that already ran."""
    _get_project_or_404(db, project_id)
    record = _get_record_or_404(db, project_id, investigation_id)
    return _to_response(record)


@router.post("/{investigation_id}/retry", response_model=InvestigationRecordResponse)
async def retry_investigation(
    project_id: int,
    investigation_id: uuid.UUID,
    db: Session = Depends(get_db),
    service: InvestigationService = Depends(get_investigation_service),
) -> InvestigationRecordResponse:
    """Re-run the existing, unmodified engine for an investigation that
    previously failed (or is being retried for any other reason), reusing
    its original question and overwriting its prior result in place —
    the persisted equivalent of the pre-Phase-2 frontend's in-session
    Retry button. Clears the previous attempt's citations/error first so a
    successful retry never leaves stale data from the failed one behind."""
    _get_project_or_404(db, project_id)
    record = _get_record_or_404(db, project_id, investigation_id)

    record.status = "running"
    record.answer = None
    record.error = None
    record.reasoning_steps = None
    record.timeline = None
    record.contract_clauses = None
    record.citations = []
    db.commit()

    await _run_and_persist(db, record, service, record.question, DEFAULT_TOP_K)
    db.refresh(record)
    return _to_response(record)
