"""Orchestrates single-document ingestion: store PDF -> extract text -> store
text -> deterministic metadata -> normalize doc_type -> Document row ->
chunk + embed + index.

AI classification is deliberately out of scope — see PROJECT_PLAN.md Part C
step 4 and app/ingestion/metadata.py.

doc_type normalization: extract_metadata() returns the raw, per-document
slug extract_doc_type() derived from that document's own "DOCUMENT TYPE:"
header text (see app/ingestion/metadata.py). Before persistence, that raw
value is mapped onto the canonical DocumentType taxonomy via
normalize_document_type() (app/domain/document_types.py, Sprint 3 Task 08)
— an explicit lookup only, no fuzzy matching or inference. Values outside
the known mapping still persist as NULL, exactly as an unextracted doc_type
already did; this doesn't add a new failure mode, just changes what a
*successfully classified* doc_type looks like once stored.
"""

from pathlib import Path

from sqlalchemy.orm import Session

from app.db.models import Document
from app.domain.document_types import normalize_document_type
from app.ingestion.extraction import PDFExtractionError, extract_pages
from app.ingestion.indexing import index_document
from app.ingestion.metadata import extract_metadata
from app.ingestion.storage import new_storage_key, save_extracted_text, save_pdf


class IngestionError(Exception):
    """Raised when a single uploaded file cannot be ingested. Callers should
    catch this per-file so one bad upload doesn't fail an entire batch."""


def ingest_document(
    *,
    session: Session,
    storage_root: Path,
    project_id: int,
    filename: str,
    content: bytes,
) -> Document:
    """Store one uploaded PDF, extract its text, derive metadata, persist the
    Document row, and index it (chunk + embed) so it's immediately
    searchable. Raises IngestionError on any failure; the Document row and
    its chunks are committed atomically — a failure at any stage rolls back
    the whole file, leaving no partially-ingested document behind."""
    if not filename.lower().endswith(".pdf"):
        raise IngestionError(f"{filename}: not a PDF file")
    if not content:
        raise IngestionError(f"{filename}: empty upload")

    storage_key = new_storage_key(filename)
    pdf_path = save_pdf(storage_root, project_id, storage_key, content)

    try:
        pages = extract_pages(pdf_path)
    except PDFExtractionError as exc:
        pdf_path.unlink(missing_ok=True)
        raise IngestionError(f"{filename}: {exc}") from exc

    full_text = "\f".join(pages)
    text_path = save_extracted_text(storage_root, project_id, storage_key, full_text)
    metadata = extract_metadata(full_text)
    canonical_doc_type = normalize_document_type(metadata.doc_type)

    document = Document(
        project_id=project_id,
        filename=filename,
        doc_type=canonical_doc_type.value if canonical_doc_type is not None else None,
        doc_date=metadata.doc_date,
        referenced_ids=metadata.referenced_ids,
        raw_text_path=str(text_path),
    )
    session.add(document)
    session.flush()  # assigns document.id for the chunks' foreign key

    try:
        index_document(session, document)
    except Exception as exc:
        session.rollback()
        pdf_path.unlink(missing_ok=True)
        text_path.unlink(missing_ok=True)
        raise IngestionError(f"{filename}: indexing failed ({exc})") from exc

    session.commit()
    session.refresh(document)
    return document
