"""Deterministic parser converting raw contract text into ContractClause
objects (Sprint 6 Task 02). No AI, no database access, no inference beyond
literal numbered-heading detection — a clause is whatever text sits between
one numbered heading and the next, nothing more.

Not integrated anywhere: nothing in the codebase constructs a ClauseParser
yet, the same "canonical shape/logic only" discipline Sprint 6 Task 01
established for the domain model itself.
"""

import re

from app.contracts.models import ClauseTopic, ContractClause

# A heading line is a line containing nothing but a clause number — a bare
# integer ("1", "20") or a dotted sub-clause number ("1.1", "8.4", "13.1",
# "20.1"). Generalizes to any number of dot-separated segments rather than
# hardcoding "at most one dot", though the task's own examples only go one
# level deep.
_HEADING_RE = re.compile(r"^\s*(\d+(?:\.\d+)*)\s*$")

# Deterministic clause-number-prefix -> ClauseTopic mapping (Sprint 6
# Task 02's explicit examples), covering the minimum clause set Sprint 6
# Research Task 01 recommended. Deliberately small, not every FIDIC clause —
# just the prefixes this project's clause set actually uses. Any prefix not
# listed here falls back to ClauseTopic.GENERAL.
_TOPIC_BY_CLAUSE_PREFIX: dict[str, ClauseTopic] = {
    "1": ClauseTopic.GENERAL,
    "3": ClauseTopic.ENGINEER,
    "4": ClauseTopic.CONTRACTOR,
    "8": ClauseTopic.DELAY,
    "13": ClauseTopic.VARIATION,
    "14": ClauseTopic.PAYMENT,
    "20": ClauseTopic.CLAIMS,
}


def _topic_for(clause_number: str) -> ClauseTopic:
    """Look up the topic for `clause_number`'s leading whole-number prefix
    (e.g. "8" for "8.4"). Falls back to ClauseTopic.GENERAL for any prefix
    not in _TOPIC_BY_CLAUSE_PREFIX — never raises."""
    prefix = clause_number.split(".", 1)[0]
    return _TOPIC_BY_CLAUSE_PREFIX.get(prefix, ClauseTopic.GENERAL)


def _split_title_and_text(body_lines: list[str]) -> tuple[str, str]:
    """The first non-blank line in `body_lines` is the title; everything
    after it (rejoined, leading/trailing whitespace stripped) is the text.
    Returns ("", "") if `body_lines` has no non-blank content."""
    for index, line in enumerate(body_lines):
        if line.strip():
            title = line.strip()
            remaining = "\n".join(body_lines[index + 1 :]).strip()
            return title, remaining
    return "", ""


class ClauseParser:
    """Splits raw contract text into ContractClause objects on numbered
    heading lines. Pure text processing: no AI, no database access, no
    clause-hierarchy inference — a clause is exactly the text between one
    numbered heading and the next (or end of text), nothing more."""

    def parse(self, text: str) -> list[ContractClause]:
        """Return one ContractClause per numbered heading found in `text`,
        in the order they appear. A heading with no body before the next
        heading (or end of text) still produces a ContractClause, with an
        empty title and/or text rather than being skipped or raising."""
        lines = text.splitlines()

        heading_indices: list[tuple[int, str]] = []
        for index, line in enumerate(lines):
            match = _HEADING_RE.match(line)
            if match:
                heading_indices.append((index, match.group(1)))

        clauses: list[ContractClause] = []
        for position, (start_index, clause_number) in enumerate(heading_indices):
            end_index = (
                heading_indices[position + 1][0] if position + 1 < len(heading_indices) else len(lines)
            )
            body_lines = lines[start_index + 1 : end_index]
            title, clause_text = _split_title_and_text(body_lines)

            clauses.append(
                ContractClause(
                    clause_number=clause_number,
                    title=title,
                    topic=_topic_for(clause_number),
                    text=clause_text,
                )
            )

        return clauses
