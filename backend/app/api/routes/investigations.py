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
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.agent import InvestigationService
from app.agent.models import DEFAULT_TOP_K, Citation, ExtractedEvent, InvestigationRequest, TimelineEntry
from app.contracts.models import ContractClause
from app.agent.reasoning import ReasoningError
from app.api.routes.investigate import get_investigation_service
from app.db.models import InvestigationRecord, InvestigationRecordAttempt, InvestigationRecordCitation, Project
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
    events: list[ExtractedEvent] = Field(
        default_factory=list,
        description="Event candidates extracted for this investigation (Phase 8B.2); [] for investigations that predate this field, that genuinely found none, or whose extraction failed (see events_error)",
    )
    events_error: str | None = Field(
        default=None,
        description="Non-None only if event extraction failed for this investigation; events is then also []. None does not imply extraction ran.",
    )
    events_truncated: bool = Field(
        default=False,
        description="True if the extraction response was cut off mid-array and some candidates had to be dropped as incomplete — events still holds every complete, verified candidate found before the cut-off.",
    )
    answer_truncated: bool = Field(
        default=False,
        description=(
            "Phase 1 (Fix Existing Investigation Pipeline Gaps): True if the LLM provider's own "
            "response metadata reported that `answer` was cut off by its output-token budget. "
            "False for every investigation that predates this field — that is the correct, "
            "honest default (see InvestigationRecord.answer_truncated's own docstring), never a "
            "fabricated claim that an old answer was definitely complete."
        ),
    )
    evidence_limitation: str | None = Field(
        default=None,
        description=(
            "Phase 1 (Fix Existing Investigation Pipeline Gaps): a plain-language note when the "
            "Investigation Loop's evidence-gathering stopped for a reason other than finding "
            "sufficient evidence (see _describe_stopping_reason below for the exact mapping) — "
            "None for a cleanly completed investigation, for one that predates this field, and "
            "for a failed investigation (see `error` instead, which is unrelated and untouched "
            "by this field). Never the raw internal stopping-reason value."
        ),
    )
    error: str | None = None
    attempt_number: int = Field(
        default=1,
        description=(
            "Phase 2a (Preserve Investigation Attempt History): 1-based attempt number of the "
            "CURRENT/latest attempt this response represents. 1 for every investigation that "
            "predates this field — correct, not a guess: such a record has only ever had one "
            "known attempt. See GET .../attempts for the full history when this is > 1."
        ),
    )


class InvestigationAttemptSummary(BaseModel):
    """One attempt in an investigation's history (Phase 2a) — either a
    frozen, superseded snapshot or the current/latest attempt (the live
    InvestigationRecord itself, represented accurately whatever its real
    status is: 'running', 'failed', or 'completed' — never implied to have
    completed merely because it's included here). Deliberately omits
    id/project_id/query/created_at: those are investigation-identity-level,
    shared across every attempt of the same investigation, not per-attempt
    — see GET .../investigations/{id} for them."""

    attempt_number: int
    is_current: bool = Field(description="True only for the current/latest attempt (the live record)")
    status: str
    attempted_at: datetime = Field(description="When this specific attempt last changed (completed, failed, or — for the current attempt only — started running)")
    answer: str | None = None
    citations: list[Citation] = Field(default_factory=list)
    reasoning_steps: list[str] = Field(default_factory=list)
    timeline: list[TimelineEntry] = Field(default_factory=list)
    contract_clauses: list[ContractClause] = Field(default_factory=list)
    events: list[ExtractedEvent] = Field(default_factory=list)
    events_error: str | None = None
    events_truncated: bool = False
    answer_truncated: bool = False
    evidence_limitation: str | None = None
    error: str | None = None


# Internal engine stopping-reason values (InvestigationLoop.LoopRunResult.
# stopping_reason / InvestigationResponse.stopping_reason) mapped onto
# plain-language text an investigator can act on — never the raw enum
# name, and never a claim stronger than what the engine actually
# established. 'sufficient' (evidence-gathering completed normally) and
# None (a legacy investigation, or one that failed before a loop result
# was ever produced — see _run_and_persist) both mean "nothing to report"
# and return None here; every other value gets its own or a shared
# generic message, never silently dropped.
_STOPPING_REASON_MESSAGES: dict[str, str] = {
    "unsupported_remediation": (
        "This investigation referenced a specific contract clause that could not be retrieved "
        "from this project's contract data. The finding below reflects only the evidence that "
        "was found; it does not confirm or rule out the referenced clause."
    ),
}
_GENERIC_EVIDENCE_LIMITATION_MESSAGE = (
    "This investigation's evidence search stopped before every available lead was followed. "
    "The finding below reflects the evidence that was gathered, which may be incomplete."
)


def _describe_stopping_reason(stopping_reason: str | None) -> str | None:
    """Map a raw internal stopping_reason onto the plain-language
    `evidence_limitation` text an investigator sees, or None when there is
    nothing to report (stopping_reason is None — a legacy record or a
    failed run — or 'sufficient', meaning the loop's own assessor reported
    the evidence was enough). A recognized non-sufficient reason gets its
    own specific message; any other non-sufficient value (including one
    this mapping doesn't yet know about) gets the shared generic message
    rather than exposing its raw name or being silently dropped."""
    if stopping_reason is None or stopping_reason == "sufficient":
        return None
    return _STOPPING_REASON_MESSAGES.get(stopping_reason, _GENERIC_EVIDENCE_LIMITATION_MESSAGE)


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


def _citations_from_relationship(citations: list[InvestigationRecordCitation]) -> list[Citation]:
    """Convert a live record's real InvestigationRecordCitation rows
    (the relational child table) into plain Citation objects — shared by
    _to_response and _attempt_history's own "current attempt" entry so
    the exact same conversion logic isn't duplicated."""
    return [
        Citation(
            document_id=c.document_id,
            page=c.page,
            chunk_id=c.chunk_id,
            relevance_score=c.relevance_score,
            chunk_text=c.chunk_text,
        )
        for c in citations
    ]


def _to_response(record: InvestigationRecord) -> InvestigationRecordResponse:
    return InvestigationRecordResponse(
        id=record.id,
        project_id=record.project_id,
        query=record.question,
        status=record.status,
        created_at=record.created_at,
        updated_at=record.updated_at,
        answer=record.answer,
        citations=_citations_from_relationship(record.citations),
        reasoning_steps=record.reasoning_steps or [],
        timeline=[TimelineEntry.model_validate(entry) for entry in (record.timeline or [])],
        contract_clauses=[ContractClause.model_validate(c) for c in (record.contract_clauses or [])],
        events=[ExtractedEvent.model_validate(e) for e in (record.events or [])],
        events_error=record.events_error,
        events_truncated=record.events_truncated,
        answer_truncated=record.answer_truncated,
        evidence_limitation=_describe_stopping_reason(record.stopping_reason),
        error=record.error,
        attempt_number=record.attempt_number,
    )


def _snapshot_current_attempt(db: Session, record: InvestigationRecord) -> None:
    """Freeze the CURRENT state of `record` — the attempt about to be
    superseded — into a new InvestigationRecordAttempt row. Must be called
    BEFORE the caller (retry_investigation) clears or mutates any field on
    `record`, including attempt_number itself: this reads record.attempt_
    number, record.updated_at, and every result-bearing field exactly as
    they stand right now, and once this function returns, nothing about
    the previous attempt is recoverable except through the row this just
    added to the session (not yet committed — the caller commits this
    insert and the record's own reset together, atomically).

    Citations are read via the live relationship RIGHT NOW, which forces
    its lazy load before retry_investigation's own `record.citations = []`
    marks the underlying InvestigationRecordCitation rows for deletion —
    reading them any later would risk capturing an already-emptied
    collection instead of the real previous answer's sources. Serialized
    into a plain JSON array (see InvestigationRecordAttempt's own
    docstring for why a snapshot never needs a second child table).

    attempted_at is captured from record.updated_at here, before this same
    call's caller advances it by mutating `record` for the new attempt —
    reading it any later would capture the NEW attempt's start time, not
    this (previous) attempt's real finish time."""
    citations_snapshot = [
        {
            "document_id": c.document_id,
            "chunk_id": c.chunk_id,
            "page": c.page,
            "relevance_score": c.relevance_score,
            "chunk_text": c.chunk_text,
        }
        for c in record.citations
    ]
    db.add(
        InvestigationRecordAttempt(
            investigation_id=record.id,
            attempt_number=record.attempt_number,
            status=record.status,
            answer=record.answer,
            reasoning_steps=record.reasoning_steps,
            citations=citations_snapshot,
            timeline=record.timeline,
            contract_clauses=record.contract_clauses,
            events=record.events,
            events_error=record.events_error,
            events_truncated=record.events_truncated,
            answer_truncated=record.answer_truncated,
            stopping_reason=record.stopping_reason,
            error=record.error,
            attempted_at=record.updated_at,
        )
    )


def _attempt_history(db: Session, record: InvestigationRecord) -> list[InvestigationAttemptSummary]:
    """Full attempt history for `record`: every superseded snapshot,
    oldest first (ascending attempt_number — a stable, documented order),
    followed by the current/latest attempt (the live record itself) last.
    A never-retried investigation has no snapshot rows at all, so this
    returns exactly one entry: attempt 1, is_current=True, with whatever
    its real status genuinely is."""
    snapshots = db.scalars(
        select(InvestigationRecordAttempt)
        .where(InvestigationRecordAttempt.investigation_id == record.id)
        .order_by(InvestigationRecordAttempt.attempt_number.asc())
    ).all()

    history = [
        InvestigationAttemptSummary(
            attempt_number=snapshot.attempt_number,
            is_current=False,
            status=snapshot.status,
            attempted_at=snapshot.attempted_at,
            answer=snapshot.answer,
            citations=[Citation.model_validate(c) for c in (snapshot.citations or [])],
            reasoning_steps=snapshot.reasoning_steps or [],
            timeline=[TimelineEntry.model_validate(entry) for entry in (snapshot.timeline or [])],
            contract_clauses=[ContractClause.model_validate(c) for c in (snapshot.contract_clauses or [])],
            events=[ExtractedEvent.model_validate(e) for e in (snapshot.events or [])],
            events_error=snapshot.events_error,
            events_truncated=snapshot.events_truncated,
            answer_truncated=snapshot.answer_truncated,
            evidence_limitation=_describe_stopping_reason(snapshot.stopping_reason),
            error=snapshot.error,
        )
        for snapshot in snapshots
    ]

    history.append(
        InvestigationAttemptSummary(
            attempt_number=record.attempt_number,
            is_current=True,
            status=record.status,
            attempted_at=record.updated_at,
            answer=record.answer,
            citations=_citations_from_relationship(record.citations),
            reasoning_steps=record.reasoning_steps or [],
            timeline=[TimelineEntry.model_validate(entry) for entry in (record.timeline or [])],
            contract_clauses=[ContractClause.model_validate(c) for c in (record.contract_clauses or [])],
            events=[ExtractedEvent.model_validate(e) for e in (record.events or [])],
            events_error=record.events_error,
            events_truncated=record.events_truncated,
            answer_truncated=record.answer_truncated,
            evidence_limitation=_describe_stopping_reason(record.stopping_reason),
            error=record.error,
        )
    )
    return history


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
    # Phase 8B.2: events=None (not []) specifically when extraction failed
    # this run (events_error set) — distinct from "ran and found none"
    # ([], events_error=None). See InvestigationRecord.events's own
    # docstring for why these are not collapsed into one representation.
    record.events = (
        None if response.events_error is not None else [event.model_dump(mode="json") for event in response.events]
    )
    record.events_error = response.events_error
    record.events_truncated = response.events_truncated
    record.answer_truncated = response.answer_truncated
    record.stopping_reason = response.stopping_reason
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


def _lock_record_for_retry(db: Session, investigation_id: uuid.UUID) -> InvestigationRecord:
    """Row-lock `investigation_id` (SELECT ... FOR UPDATE NOWAIT) for the
    rest of this transaction, so two concurrent retries of the SAME
    investigation can never both snapshot-and-reset it. Called only after
    the caller has already confirmed the record exists and belongs to
    this project via the ordinary, unlocked _get_record_or_404 — this
    function's own job is purely acquiring the lock on an id already
    known to be valid, not re-checking existence/ownership.

    NOWAIT is essential: without it, Postgres would simply BLOCK a second
    concurrent request until the first's transaction ends (which could
    hang that request's whole HTTP call for as long as the first retry's
    real Gemini call takes) instead of failing fast. A lock that's already
    held raises OperationalError immediately, translated here into a
    clean 409 — never left for the caller to misinterpret as some other
    kind of failure.

    Pre-commit review fix: `populate_existing=True` is required here, not
    optional. The caller's own prior, unlocked _get_record_or_404 already
    loaded this same row into this session's identity map; without this
    option, SQLAlchemy returns that ALREADY-CACHED Python object's stale
    attributes rather than refreshing them from this query's own fresh,
    lock-holding read -- even though a real SQL round-trip genuinely ran.
    Reproduced directly against Postgres: a second session's committed
    status change was invisible on the object this function returned
    without this option, and visible with it. Without this fix, the
    'already running' guard in retry_investigation() below could read a
    stale, pre-change status and incorrectly proceed to snapshot/reset an
    attempt that is, in reality, still running elsewhere."""
    try:
        return db.execute(
            select(InvestigationRecord)
            .where(InvestigationRecord.id == investigation_id)
            .with_for_update(nowait=True)
            .execution_options(populate_existing=True)
        ).scalar_one()
    except OperationalError as exc:
        db.rollback()  # the failed locking attempt leaves the transaction unusable otherwise
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Another retry is already in progress for this investigation. Please wait and try again.",
        ) from exc


@router.post("/{investigation_id}/retry", response_model=InvestigationRecordResponse)
async def retry_investigation(
    project_id: int,
    investigation_id: uuid.UUID,
    db: Session = Depends(get_db),
    service: InvestigationService = Depends(get_investigation_service),
) -> InvestigationRecordResponse:
    """Re-run the existing, unmodified engine for an investigation that
    previously failed (or is being retried for any other reason), reusing
    its original question — the persisted equivalent of the pre-Phase-2
    frontend's in-session Retry button.

    Phase 2a (Preserve Investigation Attempt History): the attempt about
    to be overwritten is first frozen into an InvestigationRecordAttempt
    row (_snapshot_current_attempt), in the SAME transaction as the reset
    below, committed together atomically — a crash before that commit
    leaves the previous attempt exactly as it was, never partially
    destroyed; a crash after it has both the snapshot and the reset
    durably applied.

    Two independent concurrency guards, covering two different windows:
    (1) _lock_record_for_retry's row lock covers simultaneous requests
    racing to snapshot-and-reset at the same instant; (2) the explicit
    status == 'running' check below covers the window AFTER that commit
    releases the lock but BEFORE the engine run (_run_and_persist, which
    can take as long as a real Gemini call) finishes — without this
    second guard, a retry request arriving in that window would see an
    unlocked row and incorrectly snapshot/reset an attempt that hasn't
    actually finished running yet."""
    _get_project_or_404(db, project_id)
    _get_record_or_404(db, project_id, investigation_id)  # existence/ownership check, unchanged semantics
    record = _lock_record_for_retry(db, investigation_id)

    if record.status == "running":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This investigation is already running. Wait for it to finish before retrying again.",
        )

    _snapshot_current_attempt(db, record)
    record.attempt_number += 1
    record.status = "running"
    record.answer = None
    record.error = None
    record.reasoning_steps = None
    record.timeline = None
    record.contract_clauses = None
    record.events = None
    record.events_error = None
    record.events_truncated = False
    record.answer_truncated = False
    record.stopping_reason = None
    record.citations = []
    db.commit()

    await _run_and_persist(db, record, service, record.question, DEFAULT_TOP_K)
    db.refresh(record)
    return _to_response(record)


@router.get("/{investigation_id}/attempts", response_model=list[InvestigationAttemptSummary])
def list_investigation_attempts(
    project_id: int,
    investigation_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> list[InvestigationAttemptSummary]:
    """Full attempt history for one investigation (Phase 2a): every
    superseded snapshot, oldest first, followed by the current/latest
    attempt (the live record) last — see _attempt_history for the exact
    composition. Same project-scoping/404 semantics as every other
    investigation endpoint in this router; does not change the meaning or
    response shape of the existing GET/list endpoints at all."""
    _get_project_or_404(db, project_id)
    record = _get_record_or_404(db, project_id, investigation_id)
    return _attempt_history(db, record)
