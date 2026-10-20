"""Serves the stored original file for a single document, scoped to its
project.

Project-scoping is this endpoint's entire reason for existing: `Document.id`
is a globally unique primary key, so a document could technically be
resolved regardless of which project_id the URL names. This endpoint must
never do that — it must confirm `document.project_id == project_id` before
returning any file, exactly like the existing investigation engine already
scopes retrieval by project_id (app/agent/tools.py) even though the
document ids themselves aren't project-namespaced.

Storage layout is not reinvented here: app/ingestion/storage.py already
documents and implements it (`pdfs/{project_id}/{storage_key}.pdf`,
`docx/{project_id}/{storage_key}.docx` — Phase 7: Multi-Format Evidence —
`extracted_text/{project_id}/{storage_key}.txt`, the same storage_key
shared across all of a document's files — see
app/ingestion/pipeline.py's ingest_document()). The Document row only
persists `raw_text_path` (the extracted-text path), so the original file's
path is derived from that path's filename stem (the shared storage_key) —
which directory and extension depend on the document's own filename
extension, exactly which format ingest_document() branched on at upload
time.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.models import Document
from app.db.session import get_db
from app.ingestion.storage import docx_storage_dir, email_storage_dir, pdf_storage_dir

router = APIRouter(prefix="/projects", tags=["documents"])

# Phase 7 (Multi-Format Evidence) / Phase 8A (Email Thread Intelligence):
# storage directory + media type per supported extension. Adding a format
# means adding one entry here (plus the corresponding entry in
# pipeline.py's _SUPPORTED_EXTENSIONS for PDF/DOCX, or
# app/email_ingestion/pipeline.py for .eml) — never a second file-serving
# code path. .eml documents are never created via pipeline.py's
# _SUPPORTED_EXTENSIONS (they're created by app/email_ingestion/pipeline.py
# instead), but downloading the original message reuses this exact same
# endpoint for free once the extension is registered here.
_STORAGE_BY_EXTENSION = {
    ".pdf": (pdf_storage_dir, "application/pdf"),
    ".docx": (docx_storage_dir, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    ".eml": (email_storage_dir, "message/rfc822"),
}


@router.get("/{project_id}/documents/{document_id}/file")
def get_document_file(
    project_id: int,
    document_id: int,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    """Return the original stored file (PDF or DOCX) for one document —
    only if it belongs to the requested project.

    Returns 404 uniformly for "document doesn't exist", "document belongs
    to a different project", and "stored file is missing from disk".
    Using the same response for "wrong project" as for "doesn't exist" is
    deliberate: confirming a document id exists under some *other* project
    would itself be a cross-project information leak.
    """
    document = db.scalar(select(Document).where(Document.id == document_id))
    if document is None or document.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    # Phase 3: raw_text_path is null until a document actually finishes
    # processing (status='ready') — a document still uploading/processing,
    # or one that failed, has no extracted text and therefore no derivable
    # original-file path either; treat that the same as "file not found"
    # rather than raising on Path(None).
    if document.raw_text_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document file not found")

    extension = Path(document.filename).suffix.lower()
    storage_dir_fn, media_type = _STORAGE_BY_EXTENSION.get(extension, (None, None))
    if storage_dir_fn is None:
        # Reachable by design, not just defensively, for a Document whose
        # text came from locally-OCR'd image evidence (Phase W2.2: OCR
        # Evidence Integration -- see app/ingestion/image_ocr_indexing.py):
        # its filename is the preserved image's own original name (e.g.
        # "notice.png"), never a PDF/DOCX extension pipeline.py's own
        # upload-time check would have required. There is no original
        # PDF/DOCX/.eml binary to serve for such a document -- its real
        # preserved original is the image itself, served by the existing,
        # separate image/attachment file routes (see
        # ProjectDocumentSummary.image_source) -- so returning the same
        # "file not found" 404 here is correct, not a bug, for that case.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document file not found")

    # raw_text_path looks like ".../extracted_text/{project_id}/{storage_key}.txt";
    # storage_key (the filename stem) is shared with the sibling original file.
    storage_key = Path(document.raw_text_path).stem
    expected_dir = storage_dir_fn(settings.storage_root, project_id).resolve()
    file_path = (expected_dir / f"{storage_key}{extension}").resolve()

    # Defense in depth: even though storage_key can never contain a path
    # separator (it's a single filename stem, never user-supplied), confirm
    # the resolved file is still actually inside the project's own
    # format-specific directory before opening it.
    if expected_dir not in file_path.parents or not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document file not found")

    return FileResponse(file_path, media_type=media_type, filename=document.filename)
