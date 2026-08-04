"""Deterministic search over already-parsed ContractClause objects
(Sprint 6 Task 04). Sits above ClauseRepository and below any future
planner integration — not retrieval, not semantic search, not AI. Purely
in-memory string matching over whatever a ClauseRepository already holds.

Not integrated anywhere: nothing in the codebase constructs a
ClauseSearchService yet.
"""

from app.contracts.models import ClauseTopic, ContractClause
from app.contracts.repository import ClauseRepository


class ClauseSearchService:
    """Read-only search over a ClauseRepository. Stores the repository as
    given and never mutates it or the ContractClause objects it holds;
    never caches, scores, ranks, or sorts — every method returns results in
    whatever order the repository already holds them."""

    def __init__(self, repository: ClauseRepository) -> None:
        self._repository = repository

    def find_by_number(self, clause_number: str) -> ContractClause | None:
        """Delegate to ClauseRepository.get_by_number()."""
        return self._repository.get_by_number(clause_number)

    def find_by_topic(self, topic: ClauseTopic) -> list[ContractClause]:
        """Delegate to ClauseRepository.get_by_topic()."""
        return self._repository.get_by_topic(topic)

    def find_by_keywords(self, keywords: list[str]) -> list[ContractClause]:
        """Return every clause where at least one of `keywords` appears,
        case-insensitively, as a plain substring of clause_number, title,
        or text — no regex, no scoring, no ranking, no sorting. A clause
        matching more than one keyword still appears only once, and results
        are returned in the repository's original order. Returns [] if
        `keywords` is empty."""
        if not keywords:
            return []

        lowered_keywords = [keyword.lower() for keyword in keywords]

        matches: list[ContractClause] = []
        for clause in self._repository.get_all():
            haystack = f"{clause.clause_number} {clause.title} {clause.text}".lower()
            if any(keyword in haystack for keyword in lowered_keywords):
                matches.append(clause)

        return matches
