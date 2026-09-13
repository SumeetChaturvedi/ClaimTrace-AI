"""DOCX text extraction via python-docx (Phase 7: Multi-Format Evidence).

Mirrors extraction.py's PDF contract exactly: returns one string per unit,
in true document order, so the rest of the pipeline (chunking.py's
"\\f"-per-unit convention, embeddings.py, indexing.py) needs zero changes to
treat a DOCX exactly like a PDF. For a PDF, that unit is a page; for a
DOCX, it is a paragraph — DOCX has no reliable native "page" concept (a
page break is a rendering-time layout decision made by whatever program
later opens the file, not a stable property stored per-paragraph in the
underlying document.xml), so this deliberately does not invent one.

Every paragraph in the source document is included, in order, even blank
ones — chunk_document() already produces zero chunks for a blank "page"
(see chunking.py's own docstring), so this costs nothing, and it means a
paragraph's 1-based position in the returned list is always genuinely its
real position in the source .docx, exactly what a reviewer would count by
opening the original file — a stable, honest location, never fabricated.

See DocumentChunk.page_number / Citation.page's docstrings (app/db/models.py,
app/agent/models.py) for how a DOCX citation's "page" is actually a
paragraph ordinal, and the frontend's lib/documentFormat.ts for how that is
labeled "Paragraph N" rather than "Page N" for this format.
"""

from pathlib import Path

import docx


class DocxExtractionError(Exception):
    """Raised when a .docx file can't be opened or yields no extractable
    text — mirrors PDFExtractionError's role for the PDF path exactly, so
    app/ingestion/pipeline.py's existing catch-all failure handling needs
    no format-specific branching to persist a 'failed' Document."""


def extract_paragraphs(docx_path: Path) -> list[str]:
    """Return each paragraph's text in order. Raises DocxExtractionError for
    a file that isn't a valid .docx (corrupt zip, not OOXML at all) or one
    with no extractable text at all."""
    try:
        document = docx.Document(docx_path)
    except Exception as exc:  # python-docx/lxml raise varied error types for malformed input
        raise DocxExtractionError(f"could not read DOCX ({exc})") from exc

    paragraphs = [paragraph.text for paragraph in document.paragraphs]

    if not paragraphs:
        raise DocxExtractionError("DOCX has no paragraphs")
    if not any(paragraph.strip() for paragraph in paragraphs):
        raise DocxExtractionError("no extractable text (the document contains no text)")

    return paragraphs
