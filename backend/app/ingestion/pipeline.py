"""Orchestrates single-document ingestion: store source file -> Document row
(status tracked) -> extract text -> store text -> deterministic metadata ->
normalize doc_type -> chunk + embed + index -> ready (or failed).

Format support (Phase 7: Multi-Format Evidence): PDF (via
app/ingestion/extraction.py, PyMuPDF) and DOCX (via
app/ingestion/docx_extraction.py, python-docx) are both accepted. The
format only matters for two things: which extractor produces the
"\\f"-joined text, and which storage directory holds the raw file
(save_pdf/pdf_storage_dir vs save_docx/docx_storage_dir, see storage.py).
Everything downstream of extraction — save_extracted_text, extract_metadata,
normalize_document_type, index_document (chunking, embedding, pgvector
indexing) — is completely format-independent and untouched by this phase:
it only ever sees a plain "\\f"-joined string, exactly as before. A PDF's
extracted units are pages; a DOCX's are paragraphs (DOCX has no reliable
native page concept — see docx_extraction.py). Both are stored in the same
DocumentChunk.page_number column and the same Citation.page field — no
schema change was needed for this — but the two formats mean different
things by that field, so the frontend labels it "Page N" or "Paragraph N"
depending on the citing document's own filename extension (see
frontend/src/lib/documentFormat.ts). Nothing here fabricates a page number
for a DOCX citation.

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

Processing lifecycle (Phase 3: Project + Document Foundation): a Document
row is created and committed as 'processing' BEFORE extraction/chunking/
embedding run, then updated in place to 'ready' (with its real metadata and
chunks) or 'failed' (with processing_error set) once the outcome is known —
never left at 'processing' by the time this function returns, and never
silently discarded. This is a genuine behavior change from the prior
version, which raised IngestionError and persisted nothing at all on an
extraction/indexing failure; that made a failed document invisible (no row,
nothing to show as failed, nothing to retry) rather than truthfully
recorded, which this phase's processing-lifecycle requirement needs.
IngestionError is now raised only for pre-flight validation (unsupported
file type, empty upload, oversized) that means no row should exist at all
— an input-rejection, not a processing outcome.

Timing (Phase 3 §17): each stage's wall-clock duration is logged, not
persisted, as a baseline for future async-processing decisions — this
phase's own instruction is "do not optimize prematurely," so it stays a log
line, not a new column or metrics system.
"""

import logging
import time
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.models import Document
from app.domain.document_types import normalize_document_type
from app.ingestion.docx_extraction import extract_paragraphs
from app.ingestion.extraction import extract_pages
from app.ingestion.indexing import index_document
from app.ingestion.metadata import extract_metadata
from app.ingestion.storage import new_storage_key, save_docx, save_extracted_text, save_pdf

logger = logging.getLogger(__name__)

# Generous for the scanned/printed construction-claims correspondence and
# reports this pipeline actually handles (a few hundred KB to a few MB
# typically); high enough to not be a nuisance, low enough to keep
# synchronous, in-request processing (this phase's explicit approach)
# bounded rather than accepting an arbitrarily large file.
MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB


class IngestionError(Exception):
    """Raised only for pre-flight validation failures (unsupported file
    type, empty upload, oversized) where no Document row should be created
    at all. Callers should catch this per-file so one bad upload doesn't
    reject an entire batch. A failure *after* a file passes these checks —
    a corrupt PDF or DOCX, an indexing exception — is no longer raised as
    this; it is persisted as a 'failed' Document instead (see
    ingest_document)."""


# Phase 7 (Multi-Format Evidence): the only two formats accepted. Adding a
# format means adding one more entry here plus one branch each in the
# storage/extraction blocks below — never a second pipeline.
_SUPPORTED_EXTENSIONS = (".pdf", ".docx")


def ingest_document(
    *,
    session: Session,
    storage_root: Path,
    project_id: int,
    filename: str,
    content: bytes,
) -> Document:
    """Store one uploaded PDF or DOCX and persist its full processing
    lifecycle.

    Raises IngestionError only for pre-flight validation (unsupported file
    type, empty, oversized) — no Document row is created for these. Once
    past that check, always returns a Document: status='ready' with real
    doc_type/doc_date/referenced_ids/chunks on success, or status='failed'
    with processing_error set if extraction or indexing raises. Either way
    the row is durably persisted and visible to a subsequent list/get call
    — never silently dropped, never left at 'processing'.
    """
    extension = Path(filename).suffix.lower()
    if extension not in _SUPPORTED_EXTENSIONS:
        raise IngestionError(f"{filename}: not a supported file type (PDF or DOCX only)")
    if not content:
        raise IngestionError(f"{filename}: empty upload")
    if len(content) > MAX_UPLOAD_BYTES:
        raise IngestionError(f"{filename}: file exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB upload limit")

    t_start = time.monotonic()
    storage_key = new_storage_key(filename)
    source_path = save_docx(storage_root, project_id, storage_key, content) if extension == ".docx" else save_pdf(storage_root, project_id, storage_key, content)
    t_stored = time.monotonic()

    document = Document(project_id=project_id, filename=filename, status="processing")
    session.add(document)
    session.commit()
    session.refresh(document)

    try:
        units = extract_paragraphs(source_path) if extension == ".docx" else extract_pages(source_path)
        full_text = "\f".join(units)
        text_path = save_extracted_text(storage_root, project_id, storage_key, full_text)
        t_extracted = time.monotonic()

        metadata = extract_metadata(full_text)
        canonical_doc_type = normalize_document_type(metadata.doc_type)

        document.doc_type = canonical_doc_type.value if canonical_doc_type is not None else None
        document.doc_date = metadata.doc_date
        document.referenced_ids = metadata.referenced_ids
        document.raw_text_path = str(text_path)

        index_document(session, document)
        t_indexed = time.monotonic()

        document.status = "ready"
        document.processing_error = None
        session.commit()
        session.refresh(document)

        logger.info(
            "Ingested %s (document_id=%s, project_id=%s): store=%.2fs extract=%.2fs index=%.2fs total=%.2fs",
            filename,
            document.id,
            project_id,
            t_stored - t_start,
            t_extracted - t_stored,
            t_indexed - t_extracted,
            t_indexed - t_start,
        )
        return document

    except Exception as exc:  # noqa: BLE001 -- any failure here must end in 'failed', never propagate and lose the row
        session.rollback()  # discard any partial metadata/chunk writes from this attempt
        session.refresh(document)  # reload the last committed state ('processing', no metadata yet)
        document.status = "failed"
        document.processing_error = str(exc)
        session.add(document)
        session.commit()
        session.refresh(document)
        logger.warning("Ingestion failed for %s (document_id=%s, project_id=%s): %s", filename, document.id, project_id, exc)
        return document
