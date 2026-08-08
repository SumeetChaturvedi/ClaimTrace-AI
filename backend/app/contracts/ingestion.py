"""Automatic contract-package ingestion (Dataset V2 Implementation Task 01;
made project-scoped in Sprint 8 Task 03, Backend Patch v1.0.1).

Scans a storage location for contract source files (PDF or already-
extracted .txt), extracts text — reusing app/ingestion/extraction.py's
extract_pages() for PDFs, no extraction logic duplicated — parses each
file's text with the existing, unmodified ClauseParser, and aggregates
every resulting ContractClause into one ClauseRepository.

Deliberately decoupled from the Document/database ingestion pipeline: no
Document rows are created, no database access happens here. The contract
package is source material for the clause corpus, not investigation
evidence — it doesn't need a chunk/embedding/citation identity the way
evidentiary documents do, only to become ContractClause objects.

Project scoping (Sprint 8 Task 03): each project's contract package lives
in its own subdirectory, storage/contracts/{project_id}/, exactly
mirroring the per-project layout app/ingestion/storage.py already uses for
PDFs and extracted text (storage/pdfs/{project_id}/,
storage/extracted_text/{project_id}/). The mapping from project_id to its
contract package is this directory convention itself -- no hardcoded
project_id -> package-name table exists anywhere, so onboarding a new
project's contract package is purely a data change (create
storage/contracts/{new_project_id}/ and drop its files in), never a code
change. A project with no subdirectory (e.g. project 1, which has never
had a contract package) resolves to an empty ClauseRepository, exactly as
a missing/empty directory always has -- not an error.

get_clause_repository(project_id) is the integration point
InvestigationService uses to resolve a request's own project-scoped
ClauseRepository. It is memoized per project_id (functools.lru_cache) so
each project's contract package is scanned and parsed at most once per
process -- never once per investigation request -- while still allowing
tests (or a future admin action) to force a fresh load via
get_clause_repository.cache_clear().
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
    unparseable/corrupt file, just contributes nothing from that file.
    Unchanged by Sprint 8 Task 03's project scoping -- it still only ever
    loads whatever single directory it is given; project scoping is
    entirely the caller's concern (which directory to pass), not this
    class's."""

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


@lru_cache(maxsize=None)
def get_clause_repository(project_id: int) -> ClauseRepository:
    """The project-scoped ClauseRepository for `project_id`, built from
    storage/contracts/{project_id}/ on disk (Sprint 8 Task 03). Memoized per
    project_id -- each project's contract package is scanned and parsed at
    most once per process, never once per investigation request, exactly
    preserving the "parse once" property the old process-wide
    get_default_clause_repository() had, just keyed per project instead of
    global. A project with no contract package directory (or an empty one)
    resolves to an empty ClauseRepository, not an error -- see
    ContractPackageLoader.load()'s own docstring.

    Call get_clause_repository.cache_clear() to force every project's
    contract package to be freshly reloaded (tests/validation scripts
    only — production code never needs to)."""
    contract_package_dir = get_settings().storage_root / "contracts" / str(project_id)
    return ContractPackageLoader(contract_package_dir=contract_package_dir).load()
