"""PDF text extraction via PyMuPDF (fitz)."""

from pathlib import Path

import fitz


class PDFExtractionError(Exception):
    """Raised when a PDF cannot be opened or yields no extractable text."""


def extract_pages(pdf_path: Path) -> list[str]:
    """Return each page's text in order. Raises PDFExtractionError for
    corrupted files, zero-page documents, or image-only PDFs with no text
    layer (OCR is out of scope for V0 per PROJECT_PLAN.md)."""
    try:
        with fitz.open(pdf_path) as doc:
            if doc.page_count == 0:
                raise PDFExtractionError("PDF has no pages")
            pages = [page.get_text() for page in doc]
    except PDFExtractionError:
        raise
    except Exception as exc:  # fitz raises varied error types for malformed files
        raise PDFExtractionError(f"could not read PDF ({exc})") from exc

    if not any(page.strip() for page in pages):
        raise PDFExtractionError("no extractable text (image-only PDFs are unsupported)")

    return pages
