"""Safe extraction of .eml entries from an uploaded ZIP archive (Phase 8A:
Email Thread Intelligence).

Uses only the standard library `zipfile` module — no new dependency.
Security posture, matching the task brief's explicit requirements:

- Path traversal: an entry name containing ".." components, an absolute
  path, or a Windows drive letter is rejected outright, never written
  anywhere and never passed to the .eml parser.
- Per-entry and total size limits are enforced against the *actual* bytes
  read while streaming, not against the (attacker-controlled) size fields
  recorded in the archive's central directory — this is what stops a
  zip-bomb (a tiny archive whose declared or compressed size looks small
  but decompresses to gigabytes).
- Only `.eml`-suffixed entries are considered; directories and anything
  else inside the archive are silently skipped (not an error — a ZIP of
  mixed content choosing to include other files is not misuse).
- A corrupt or non-ZIP upload is rejected with a clear, caller-facing
  error, never a raw traceback.
"""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from pathlib import PurePosixPath

MAX_ENTRY_BYTES = 25 * 1024 * 1024  # mirrors app/ingestion/pipeline.py's MAX_UPLOAD_BYTES for one document
MAX_TOTAL_BYTES = 150 * 1024 * 1024  # across every .eml entry in one archive
MAX_ENTRIES = 500
_READ_CHUNK = 1024 * 1024


class ZipImportError(Exception):
    """Raised for an archive that can't be safely processed at all (not a
    ZIP, unreadable, or exceeds MAX_ENTRIES) — distinct from a single
    rejected entry, which is reported per-entry instead (see
    extract_eml_entries' return shape)."""


@dataclass(frozen=True)
class ExtractedEntry:
    name: str
    content: bytes


@dataclass(frozen=True)
class RejectedEntry:
    name: str
    error: str


@dataclass(frozen=True)
class ZipExtractionResult:
    entries: list[ExtractedEntry]
    rejected: list[RejectedEntry]


def _is_safe_member_name(name: str) -> bool:
    """Reject path traversal and absolute paths. ZIP entry names are always
    "/"-separated regardless of platform (APPNOTE.TXT), so PurePosixPath is
    the correct parser here even when this runs on Windows."""
    if not name or name.endswith("/"):
        return False  # directory entry, not a traversal attempt, but not a file either
    path = PurePosixPath(name)
    if path.is_absolute():
        return False
    if ".." in path.parts:
        return False
    # A bare Windows drive letter ("C:...") isn't flagged by is_absolute()
    # under PurePosixPath — reject it explicitly too.
    if len(name) >= 2 and name[1] == ":":
        return False
    return True


def extract_eml_entries(zip_bytes: bytes) -> ZipExtractionResult:
    """Return every safely-extractable .eml entry's raw bytes, plus a
    per-entry report of anything rejected. Raises ZipImportError only when
    the archive itself can't be processed at all."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile as exc:
        raise ZipImportError(f"not a valid ZIP archive: {exc}") from exc

    infos = zf.infolist()
    if len(infos) > MAX_ENTRIES:
        raise ZipImportError(f"archive contains {len(infos)} entries, exceeding the {MAX_ENTRIES}-entry limit")

    entries: list[ExtractedEntry] = []
    rejected: list[RejectedEntry] = []
    total_bytes = 0

    for info in infos:
        name = info.filename
        if name.endswith("/") or info.is_dir():
            continue  # directory entry — not an error, just not a file
        if not name.lower().endswith(".eml"):
            continue  # not an .eml entry — silently skipped, not rejected

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
            # Stop entirely rather than keep extracting — the archive as a
            # whole is over budget, not just this one entry.
            break

        if not content:
            rejected.append(RejectedEntry(name=name, error="empty entry"))
            continue

        entries.append(ExtractedEntry(name=name, content=content))

    return ZipExtractionResult(entries=entries, rejected=rejected)


class _EntryTooLarge(Exception):
    pass


def _read_bounded(zf: zipfile.ZipFile, info: zipfile.ZipInfo, *, max_bytes: int) -> bytes:
    """Stream-read one entry's *decompressed* bytes with a hard cap on the
    actual bytes produced — never trusts `info.file_size` (which is just a
    value recorded in the archive and can be forged/understated by a
    crafted zip bomb). Aborts as soon as the running total would exceed
    max_bytes, without ever buffering more than that in memory."""
    chunks: list[bytes] = []
    total = 0
    with zf.open(info) as handle:
        while True:
            chunk = handle.read(_READ_CHUNK)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise _EntryTooLarge()
            chunks.append(chunk)
    return b"".join(chunks)
