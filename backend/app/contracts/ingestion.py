"""Automatic contract-package ingestion (Dataset V2 Implementation Task 01).

Scans a fixed storage location for contract source files (PDF or already-
extracted .txt), extracts text — reusing app/ingestion/extraction.py's
extract_pages() for PDFs, no extraction logic duplicated — parses each
file's text with the existing, unmodified ClauseParser, and aggregates
every resulting ContractClause into one ClauseRepository.

Deliberately decoupled from the Document/database ingestion pipeline: no
Document rows are created, no database access happens here. The contract
package is source material for the clause corpus, not investigation
evidence — it doesn't need a chunk/embedding/citation identity the way
evidentiary documents do, only to become ContractClause objects.

get_default_clause_repository() is the integration point InvestigationService
uses when no ClauseRepository is explicitly injected. It is memoized
(functools.lru_cache) so the contract package is scanned and parsed at most
once per process — never once per investigation request — while still
allowing tests (or a future admin action) to force a fresh load via
get_default_clause_repository.cache_clear().
"""

from functools import lru_cache
from pathlib import Path

from app.config import get_settings
from app.contracts.models import ContractClause
from app.contracts.parser import ClauseParser
from app.contracts.repository import ClauseRepository
from app.ingestion.extraction import PDFExtractionError, extract_pages

_SUPPORTED_SUFFIXES = (".pdf", ".txt")


class ContractPackageLoader:
    """Loads every contract source file in a directory into a single
    ClauseRepository. Read-only with respect to its inputs — never writes
    anything, never raises for a missing/empty directory or an
    unparseable/corrupt file, just contributes nothing from that file."""

    def __init__(self, contract_package_dir: Path | None = None, parser: ClauseParser | None = None) -> None:
        self._contract_package_dir = contract_package_dir or (get_settings().storage_root / "contracts")
        self._parser = parser or ClauseParser()

    def load(self) -> ClauseRepository:
        """Return a ClauseRepository built from every clause parsed out of
        every contract source file found in the configured directory, in
        deterministic (sorted-filename) order. Returns an empty
        ClauseRepository — never raises — if the directory doesn't exist,
        is empty, or contains no parseable files (e.g. this project's own
        Particular Conditions/Contract Data/Employer's Requirements, which
        use lettered Parts and plain sections rather than FIDIC's numbered
        clause/sub-clause headings ClauseParser looks for — contributing 0
        clauses from a file is not an error)."""
        clauses: list[ContractClause] = []
        for path in self._source_files():
            text = self._extract_text(path)
            if text:
                clauses.extend(self._parser.parse(text))
        return ClauseRepository(clauses)

    def _source_files(self) -> list[Path]:
        if not self._contract_package_dir.is_dir():
            return []
        return sorted(
            path
            for path in self._contract_package_dir.iterdir()
            if path.is_file() and path.suffix.lower() in _SUPPORTED_SUFFIXES
        )

    def _extract_text(self, path: Path) -> str:
        if path.suffix.lower() == ".txt":
            try:
                return path.read_text(encoding="utf-8")
            except OSError:
                return ""
        try:
            pages = extract_pages(path)
        except PDFExtractionError:
            return ""
        return "\f".join(pages)


@lru_cache(maxsize=1)
def get_default_clause_repository() -> ClauseRepository:
    """The process-wide default ClauseRepository, built from the contract
    package on disk. Constructed at most once per process — the contract
    package is not re-scanned or re-parsed on every call, so repeated use
    (e.g. one call per investigation request) is free after the first.
    Call get_default_clause_repository.cache_clear() to force a fresh load
    (tests only — production code never needs to)."""
    return ContractPackageLoader().load()
