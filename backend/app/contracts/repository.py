"""Read-only, in-memory repository over an already-parsed collection of
ContractClause objects (Sprint 6 Task 03). No database, no file loading, no
parsing (ClauseParser is a separate, upstream concern), no AI, no
retrieval — purely a lookup layer over data supplied to the constructor.

Not integrated anywhere: nothing in the codebase constructs a
ClauseRepository yet.
"""

from app.contracts.models import ClauseTopic, ContractClause


class ClauseRepository:
    """Wraps a fixed collection of ContractClause objects and answers
    lookups against it. Read-only: nothing on this class mutates the
    clauses it was constructed with, and nothing it returns exposes
    internal state a caller could mutate to corrupt it."""

    def __init__(self, clauses: list[ContractClause]) -> None:
        """Store `clauses` independent of the list object passed in — later
        mutating the caller's own list has no effect on this repository.
        Order is preserved as given."""
        self._clauses: tuple[ContractClause, ...] = tuple(clauses)
        self._by_number: dict[str, ContractClause] = {}
        for clause in self._clauses:
            self._by_number.setdefault(clause.clause_number, clause)

    def get_all(self) -> list[ContractClause]:
        """Return every clause, in construction order. A fresh list each
        call — mutating the returned list never affects this repository."""
        return list(self._clauses)

    def get_by_number(self, clause_number: str) -> ContractClause | None:
        """Return the clause whose clause_number exactly matches, or None
        if none does. If more than one clause shares a clause_number
        (unvalidated here — that's ClauseParser/upstream data quality, not
        this repository's concern), the first one encountered at
        construction time wins."""
        return self._by_number.get(clause_number)

    def get_by_topic(self, topic: ClauseTopic) -> list[ContractClause]:
        """Return every clause whose topic matches `topic`, in construction
        order. Empty list if none match."""
        return [clause for clause in self._clauses if clause.topic == topic]
