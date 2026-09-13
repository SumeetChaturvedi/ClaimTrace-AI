"""Filesystem storage for uploaded source documents and their extracted text.

Layout under settings.storage_root:
    pdfs/{project_id}/{storage_key}.pdf
    docx/{project_id}/{storage_key}.docx    (Phase 7: Multi-Format Evidence)
    extracted_text/{project_id}/{storage_key}.txt

docx_storage_dir()/save_docx() are new, additive siblings of
pdf_storage_dir()/save_pdf() — a separate directory per format, not a
generalized "originals" directory — specifically so adding DOCX support
touches zero bytes of the existing, already-populated pdfs/ tree or the
code path that resolves it. extracted_text/ is shared by both formats
unchanged: it always holds plain "\\f"-joined text regardless of which
extractor produced it.
"""

import re
import uuid
from pathlib import Path

_UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


def new_storage_key(original_filename: str) -> str:
    """Build a collision-safe, path-traversal-safe stem shared by a document's
    stored PDF and extracted-text file."""
    base = Path(original_filename).name  # strip any directory components
    stem = Path(_UNSAFE_CHARS.sub("_", base) or "document").stem or "document"
    return f"{uuid.uuid4().hex[:8]}_{stem}"


def pdf_storage_dir(storage_root: Path, project_id: int) -> Path:
    path = storage_root / "pdfs" / str(project_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def text_storage_dir(storage_root: Path, project_id: int) -> Path:
    path = storage_root / "extracted_text" / str(project_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_pdf(storage_root: Path, project_id: int, storage_key: str, content: bytes) -> Path:
    """Persist raw PDF bytes under the project's storage directory."""
    destination = pdf_storage_dir(storage_root, project_id) / f"{storage_key}.pdf"
    destination.write_bytes(content)
    return destination


def docx_storage_dir(storage_root: Path, project_id: int) -> Path:
    path = storage_root / "docx" / str(project_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_docx(storage_root: Path, project_id: int, storage_key: str, content: bytes) -> Path:
    """Persist raw DOCX bytes under the project's storage directory. Mirrors
    save_pdf() exactly, in its own docx/ tree (see module docstring)."""
    destination = docx_storage_dir(storage_root, project_id) / f"{storage_key}.docx"
    destination.write_bytes(content)
    return destination


def save_extracted_text(storage_root: Path, project_id: int, storage_key: str, full_text: str) -> Path:
    """Persist a document's extracted text (pages joined with form-feed
    separators so a later chunking step can recover page boundaries)."""
    destination = text_storage_dir(storage_root, project_id) / f"{storage_key}.txt"
    destination.write_text(full_text, encoding="utf-8")
    return destination
