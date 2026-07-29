"""Filesystem storage for uploaded PDFs and their extracted text.

Layout under settings.storage_root:
    pdfs/{project_id}/{storage_key}.pdf
    extracted_text/{project_id}/{storage_key}.txt
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


def save_extracted_text(storage_root: Path, project_id: int, storage_key: str, full_text: str) -> Path:
    """Persist a document's extracted text (pages joined with form-feed
    separators so a later chunking step can recover page boundaries)."""
    destination = text_storage_dir(storage_root, project_id) / f"{storage_key}.txt"
    destination.write_text(full_text, encoding="utf-8")
    return destination
