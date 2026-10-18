"""Safe extraction of a WhatsApp export ZIP archive (Phase W1: WhatsApp
Export Ingestion) -- the chat .txt file plus zero or more media files.

Reuses app/email_ingestion/zip_import.py's own path-traversal check and
streaming-byte-limited reader DIRECTLY (not reimplemented) -- the task's
own explicit instruction is to "reuse and adapt the existing email ZIP
import protections instead of inventing a separate, weaker approach."
Those two functions are the actual security-critical logic (path-safety,
real-bytes-not-declared-size streaming caps); this module only adapts the
entry-selection policy around them, since a WhatsApp export is
heterogeneous (one .txt plus arbitrary media extensions) rather than
.eml-only.

Security posture (identical primitives to the email importer):
- Path traversal: an entry name containing ".." components, an absolute
  path, or a Windows drive letter is rejected outright.
- Per-entry and total size limits are enforced against the *actual* bytes
  read while streaming, never the archive's own declared/compressed size
  fields -- this is what stops a zip bomb.
- Entry count is capped before any extraction is attempted.
- A corrupt or non-ZIP upload is rejected with a clear, caller-facing
  error, never a raw traceback.

Unlike the email importer (which only ever looks for .eml entries and
silently skips everything else), every non-directory, safely-named entry
within budget is extracted here: a WhatsApp export's media files have
heterogeneous, a-priori-unknown extensions, so filtering by extension at
this layer would risk silently discarding real evidence. Deciding what to
do with each extracted entry (which one is the chat transcript, which are
supported-for-indexing documents, which are media-preserve-only) is the
ingestion pipeline's job (pipeline.py), not this safety layer's.
"""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass

from app.email_ingestion.zip_import import _EntryTooLarge, _is_safe_member_name, _read_bounded

MAX_ENTRY_BYTES = 25 * 1024 * 1024  # mirrors app/email_ingestion/zip_import.py's own per-file cap
MAX_TOTAL_BYTES = 150 * 1024 * 1024  # mirrors app/email_ingestion/zip_import.py's own whole-archive cap
MAX_ENTRIES = 500


class WhatsAppZipImportError(Exception):
    """Raised for an archive that can't be safely processed at all (not a
    ZIP, unreadable, or exceeds MAX_ENTRIES) -- distinct from a single
    rejected entry, which is reported per-entry instead."""


@dataclass(frozen=True)
class ExtractedEntry:
    name: str
    content: bytes


@dataclass(frozen=True)
class RejectedEntry:
    name: str
    error: str


@dataclass(frozen=True)
class WhatsAppZipExtractionResult:
    entries: list[ExtractedEntry]
    rejected: list[RejectedEntry]


def extract_whatsapp_entries(zip_bytes: bytes) -> WhatsAppZipExtractionResult:
    """Return every safely-extractable entry's raw bytes (the chat .txt
    file and any media files, whatever their extension), plus a per-entry
    report of anything rejected. Raises WhatsAppZipImportError only when
    the archive itself can't be processed at all."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile as exc:
        raise WhatsAppZipImportError(f"not a valid ZIP archive: {exc}") from exc

    infos = zf.infolist()
    if len(infos) > MAX_ENTRIES:
        raise WhatsAppZipImportError(f"archive contains {len(infos)} entries, exceeding the {MAX_ENTRIES}-entry limit")

    entries: list[ExtractedEntry] = []
    rejected: list[RejectedEntry] = []
    total_bytes = 0

    for info in infos:
        name = info.filename
        if name.endswith("/") or info.is_dir():
            continue  # directory entry -- not an error, just not a file

        if not _is_safe_member_name(name):
            rejected.append(RejectedEntry(name=name, error="rejected: unsafe path (traversal or absolute path)"))
            continue

        try:
            content = _read_bounded(zf, info, max_bytes=MAX_ENTRY_BYTES)
        except _EntryTooLarge:
            rejected.append(RejectedEntry(name=name, error=f"entry exceeds the {MAX_ENTRY_BYTES // (1024 * 1024)} MB per-file limit"))
            continue
        except (zipfile.BadZipFile, OSError, RuntimeError) as exc:
            rejected.append(RejectedEntry(name=name, error=f"could not extract: {exc}"))
            continue

        total_bytes += len(content)
        if total_bytes > MAX_TOTAL_BYTES:
            rejected.append(RejectedEntry(name=name, error="archive exceeds the total extraction size limit"))
            break  # the archive as a whole is over budget, not just this one entry

        if not content:
            rejected.append(RejectedEntry(name=name, error="empty entry"))
            continue

        entries.append(ExtractedEntry(name=name, content=content))

    return WhatsAppZipExtractionResult(entries=entries, rejected=rejected)
