"""ClauseRetriever — the deterministic orchestration this task adds on top
of ClauseSearchService (Sprint 6 Task 07): unions the results of clause
retrieval by number, topic, and keyword into a single, deduplicated,
repository-ordered list.

This is genuinely new logic, not duplicated from ClauseSearchService: that
service deliberately returns each of its three lookups independently, each
already in repository order on its own, but never combines them. Naively
concatenating those three already-ordered lists would NOT preserve true
repository order across the union (e.g. a clause found only via topic could
sort ahead of one found only via keyword, in an order that has nothing to
do with where either sits in the repository) — so this module collects the
matched clause_numbers into a set first, then filters
ClauseRepository.get_all() by that set. Filtering the repository's own
already-ordered output is what guarantees true repository order and
automatic deduplication (a clause_number can only appear once in a set,
and get_all() lists each clause exactly once already).

No AI, no database, no semantic search, no embeddings — pure set/list
operations over ClauseSearchService's existing, unmodified public methods.
"""

from app.contracts.context import ContractContext
from app.contracts.models import ContractClause
from app.contracts.repository import ClauseRepository
from app.contracts.search import ClauseSearchService


class ClauseRetriever:
    """Retrieves ContractClause objects matching a ContractContext, via
    ClauseSearchService, in the order: by number (only if clause_numbers is
    non-empty), by topic, by keywords — unioned, deduplicated, and returned
    in the underlying ClauseRepository's own order."""

    def __init__(self, repository: ClauseRepository, search_service: ClauseSearchService) -> None:
        self._repository = repository
        self._search_service = search_service

    def retrieve(self, context: ContractContext) -> list[ContractClause]:
        """Return every clause matched by `context`, via clause number (if
        any are given), topic, or keyword, unioned with no duplicates, in
        the repository's own order. Returns [] if `context` matches
        nothing (including a fully empty ContractContext)."""
        matched_numbers: set[str] = set()

        if context.clause_numbers:
            for clause_number in context.clause_numbers:
                clause = self._search_service.find_by_number(clause_number)
                if clause is not None:
                    matched_numbers.add(clause.clause_number)

        for topic in context.clause_topics:
            for clause in self._search_service.find_by_topic(topic):
                matched_numbers.add(clause.clause_number)

        for clause in self._search_service.find_by_keywords(context.keywords):
            matched_numbers.add(clause.clause_number)

        return [clause for clause in self._repository.get_all() if clause.clause_number in matched_numbers]
