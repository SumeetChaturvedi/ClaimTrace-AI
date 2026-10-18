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


def email_storage_dir(storage_root: Path, project_id: int) -> Path:
    path = storage_root / "emails" / str(project_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_eml(storage_root: Path, project_id: int, storage_key: str, content: bytes) -> Path:
    """Persist raw .eml bytes (Phase 8A: Email Thread Intelligence). Mirrors
    save_pdf()/save_docx() exactly, in its own emails/ tree, so the
    existing generic file-serving endpoint (app/api/routes/document_file.py)
    can serve the original message with one added dict entry, no new
    file-serving code path."""
    destination = email_storage_dir(storage_root, project_id) / f"{storage_key}.eml"
    destination.write_bytes(content)
    return destination


def image_storage_dir(storage_root: Path, project_id: int) -> Path:
    path = storage_root / "images" / str(project_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_image(storage_root: Path, project_id: int, storage_key: str, content: bytes, extension: str) -> Path:
    """Persist raw image bytes (Phase W2.0: Shared Image Preservation
    Foundation), source-neutral: used by Gmail image attachments
    (app/email_ingestion/pipeline.py) and direct project image uploads
    (app/api/routes/project_images.py) alike, in its own images/ tree --
    mirrors save_eml()/save_pdf()/save_whatsapp_media()'s own pattern
    exactly. Deliberately NOT used by app/whatsapp_ingestion/pipeline.py,
    which already has its own, already-reviewed save_whatsapp_media() and
    whatsapp_media/ tree from Phase W1; this function exists for the two
    sources that had no such preservation path before this phase, not to
    replace one that already works.

    `extension` is the SERVER-DETECTED file type (see
    app/ingestion/image_validation.py's validate_image), never the
    original filename's own extension taken on faith -- the original
    filename is preserved only as metadata on the owning row, never used
    to build a filesystem path. `storage_key` is always a fresh,
    server-generated value (new_storage_key()), never derived from
    untrusted input."""
    destination = image_storage_dir(storage_root, project_id) / f"{storage_key}{extension}"
    destination.write_bytes(content)
    return destination


def save_extracted_text(storage_root: Path, project_id: int, storage_key: str, full_text: str) -> Path:
    """Persist a document's extracted text (pages joined with form-feed
    separators so a later chunking step can recover page boundaries)."""
    destination = text_storage_dir(storage_root, project_id) / f"{storage_key}.txt"
    destination.write_text(full_text, encoding="utf-8")
    return destination


def whatsapp_media_dir(storage_root: Path, project_id: int) -> Path:
    path = storage_root / "whatsapp_media" / str(project_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_whatsapp_media(storage_root: Path, project_id: int, storage_key: str, content: bytes, extension: str) -> Path:
    """Persist raw WhatsApp media bytes (Phase W1: WhatsApp Export
    Ingestion) under its own tree, mirroring save_eml()/save_pdf()'s own
    pattern exactly. `extension` is the SERVER-DETECTED file type (see
    app/whatsapp_ingestion/pipeline.py's content-sniffing), never the
    original filename's own extension taken on faith -- the original
    filename is preserved only as metadata (WhatsAppMediaAttachment.
    filename), never used to build a filesystem path."""
    destination = whatsapp_media_dir(storage_root, project_id) / f"{storage_key}{extension}"
    destination.write_bytes(content)
    return destination
