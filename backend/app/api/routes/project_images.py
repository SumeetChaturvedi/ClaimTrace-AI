"""Project-scoped direct image uploads and inspection (Phase W2.0: Shared
Image Preservation Foundation).

Mirrors app/api/routes/project_whatsapp.py's conventions exactly:
project-scoping enforced on every read, a uniform 404 for "doesn't exist"
and "belongs to a different project" alike, and preserved-original file
serving keyed by the row's own server-generated storage_key — never a
Document, since this phase never creates one.

Upload itself happens through the EXISTING
POST /projects/{project_id}/documents endpoint (app/api/routes/
project_documents.py), which now also accepts recognized images in the
same batch as PDF/DOCX files — this module is only for listing/viewing
the resulting ProjectImageAsset rows, exactly as project_whatsapp.py is a
thin read layer alongside its own import endpoint."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.models import Project, ProjectImageAsset
from app.db.session import get_db
from app.ingestion.image_validation import validate_image
from app.ingestion.storage import image_storage_dir, new_storage_key, save_image
from app.ocr.pending import ensure_pending_ocr_result

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}/images", tags=["images"])


def ingest_project_image(
    *,
    session: Session,
    storage_root: Path,
    project_id: int,
    filename: str,
    content: bytes,
) -> ProjectImageAsset:
    """Preserve one directly-uploaded image as a ProjectImageAsset, called
    from app/api/routes/project_documents.py's upload endpoint for any
    uploaded file that sniffs as a recognized image signature (the caller
    makes that routing decision; this function assumes it's already been
    made and always returns a ProjectImageAsset, never raises for a
    validation failure — only for a genuine, unexpected database error).

    Re-uploading the exact same image bytes to the same project returns
    the EXISTING asset rather than creating a duplicate: an application-
    level pre-check handles the common case, and the real
    ux_project_image_assets_project_content_hash database constraint (see
    ProjectImageAsset's own docstring) is the backstop for a concurrent
    double-upload race — never just a best-effort check, mirroring every
    other dedup path in this codebase (WhatsAppMessage/EmailMessage)."""
    content_hash = hashlib.sha256(content).hexdigest()
    size_bytes = len(content)

    existing = session.scalar(
        select(ProjectImageAsset).where(
            ProjectImageAsset.project_id == project_id,
            ProjectImageAsset.content_hash == content_hash,
        )
    )
    if existing is not None:
        return existing

    result = validate_image(content)
    if not result.valid:
        row = ProjectImageAsset(
            project_id=project_id,
            document_id=None,
            filename=filename,
            content_type=None,
            size_bytes=size_bytes,
            content_hash=content_hash,
            status="rejected",
            processing_error=result.error,
        )
        session.add(row)
        try:
            session.commit()
        except IntegrityError:
            # A concurrent upload of the exact same bytes won the race
            # between our pre-check above and this commit -- discard this
            # attempt and return the winner, never a duplicate row or a
            # 500 (same recovery pattern as every other dedup path here).
            session.rollback()
            winner = session.scalar(
                select(ProjectImageAsset).where(
                    ProjectImageAsset.project_id == project_id,
                    ProjectImageAsset.content_hash == content_hash,
                )
            )
            if winner is not None:
                return winner
            raise
        return row

    storage_key = new_storage_key(filename)
    file_path = save_image(storage_root, project_id, storage_key, content, result.extension)
    row = ProjectImageAsset(
        project_id=project_id,
        document_id=None,
        filename=filename,
        content_type=result.content_type,
        size_bytes=size_bytes,
        content_hash=content_hash,
        status="stored_pending_processing",
        processing_error=None,
        storage_key=storage_key,
        detected_extension=result.extension,
        width_px=result.width,
        height_px=result.height,
    )
    session.add(row)
    try:
        session.commit()
    except IntegrityError:
        # Same concurrent-duplicate race as above, but on the success
        # path: the file we just wrote is exclusively ours (a fresh
        # storage_key), so it's safe to remove now that a concurrent
        # upload of the same bytes already won.
        session.rollback()
        file_path.unlink(missing_ok=True)
        winner = session.scalar(
            select(ProjectImageAsset).where(
                ProjectImageAsset.project_id == project_id,
                ProjectImageAsset.content_hash == content_hash,
            )
        )
        if winner is not None:
            return winner
        raise
    except Exception as exc:  # noqa: BLE001 -- compensating cleanup for the file just written above
        session.rollback()
        file_path.unlink(missing_ok=True)
        logger.warning(
            "Project image asset commit failed after writing %s; removed the now-orphaned file: %s",
            file_path,
            exc,
        )
        return ProjectImageAsset(
            project_id=project_id,
            document_id=None,
            filename=filename,
            content_type=result.content_type,
            size_bytes=size_bytes,
            content_hash=content_hash,
            status="failed",
            processing_error=str(exc),
        )

    # Phase W2.1 (Local OCR Foundation): record this new preservation as
    # OCR work still to be done -- Tesseract is never invoked here (see
    # app/ocr/process_pending.py's own batch command for that). A failure
    # in this step is logged and swallowed (see ensure_pending_ocr_result's
    # own docstring); it never turns an otherwise-successful image upload
    # into a failure, since the row above is already durably committed.
    ensure_pending_ocr_result(
        session,
        project_image_asset_id=row.id,
        default_language=get_settings().ocr_language,
    )
    return row


def _get_project_or_404(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


class ProjectImageAssetSummary(BaseModel):
    """One directly-uploaded project image. `status` is
    'stored_pending_processing' (the original is preserved and viewable,
    not yet OCR'd/described/indexed — W2.1+), 'rejected' (failed
    validation; nothing was stored), or 'failed' (accepted but the
    attachment row's own commit failed — see
    app/api/routes/project_documents.py's image-upload branch; `id` and
    `uploaded_at` are None in this one case specifically, since the
    row was never actually persisted, by design — never a fabricated id
    for something that doesn't durably exist). 'processed'/document_id is
    reserved for a future phase that does not exist yet in this one —
    this phase never sets it."""

    id: int | None
    filename: str
    content_type: str | None
    size_bytes: int
    status: str
    document_id: int | None
    processing_error: str | None
    width_px: int | None
    height_px: int | None
    uploaded_at: datetime | None


def to_project_image_summary(asset: ProjectImageAsset) -> ProjectImageAssetSummary:
    return ProjectImageAssetSummary(
        id=asset.id,
        filename=asset.filename,
        content_type=asset.content_type,
        size_bytes=asset.size_bytes,
        status=asset.status,
        document_id=asset.document_id,
        processing_error=asset.processing_error,
        width_px=asset.width_px,
        height_px=asset.height_px,
        uploaded_at=asset.uploaded_at,
    )


@router.get("", response_model=list[ProjectImageAssetSummary])
def list_project_images(project_id: int, db: Session = Depends(get_db)) -> list[ProjectImageAssetSummary]:
    """List every image directly uploaded to `project_id`, most recently
    uploaded first — including rejected ones, so the real outcome of
    every upload attempt stays visible, never silently dropped."""
    _get_project_or_404(db, project_id)
    assets = list(
        db.scalars(
            select(ProjectImageAsset)
            .where(ProjectImageAsset.project_id == project_id)
            .order_by(ProjectImageAsset.uploaded_at.desc())
        )
    )
    return [to_project_image_summary(a) for a in assets]


@router.get("/{image_id}", response_model=ProjectImageAssetSummary)
def get_project_image(project_id: int, image_id: int, db: Session = Depends(get_db)) -> ProjectImageAssetSummary:
    _get_project_or_404(db, project_id)
    asset = db.get(ProjectImageAsset, image_id)
    if asset is None or asset.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    return to_project_image_summary(asset)


@router.get("/{image_id}/file")
def get_project_image_file(
    project_id: int,
    image_id: int,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    """Serve the preserved original bytes of one directly-uploaded image.
    404s uniformly for "doesn't exist", "belongs to a different project",
    and "no preserved original to serve" (a 'rejected' asset was never
    stored). Content-type is served from the asset's own server-detected
    `content_type` (see app/ingestion/image_validation.py), never guessed
    from the filename at serve time.

    content_disposition_type="inline" (pre-commit review fix): Starlette's
    FileResponse defaults to "attachment" whenever a `filename` is given,
    which forces the browser to download the file instead of displaying
    it -- confirmed directly against the installed Starlette version
    (FileResponse.__init__'s own default `content_disposition_type:
    str = "attachment"`) and by an actual request/response cycle showing
    `content-disposition: attachment; filename="..."` before this fix.
    Every consumer of this route opens it as a plain `<a target="_blank">`
    link expecting to VIEW the original image (ProjectPage.tsx's
    ProjectImageRow, and SourceViewPage/DocumentSourceViewPage's "Open
    original image" action via getOcrSourceImageUrl) -- none of them
    wants a forced download. `filename` is kept so the browser still
    offers the real original filename if the user explicitly saves it
    from the inline view; only the disposition type changes."""
    _get_project_or_404(db, project_id)
    asset = db.get(ProjectImageAsset, image_id)
    if asset is None or asset.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    if not asset.storage_key or not asset.detected_extension:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No preserved original file for this image")

    file_path = image_storage_dir(settings.storage_root, project_id) / f"{asset.storage_key}{asset.detected_extension}"
    if not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preserved original file is missing")

    return FileResponse(
        path=file_path,
        media_type=asset.content_type or "application/octet-stream",
        filename=asset.filename,
        content_disposition_type="inline",
    )
