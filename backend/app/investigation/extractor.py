"""Deterministic entity extraction from investigation questions.

V1: no LLM, no embeddings, no external NLP libraries — simple pattern and
keyword matching, one heuristic per supported entity type. Isolated in its
own class so it can grow more heuristics, or be replaced by an LLM-backed
extractor later, without changing extract()'s public signature.
"""

import re

from app.investigation.entities import ConstructionEntity, EntityExtractionResult, EntityType

# "Pier P-42"-style structure references: a label word followed by a short
# alphanumeric identifier.
_STRUCTURE_PATTERN = re.compile(r"\bPier\s+[A-Za-z]-?\d+\b", re.IGNORECASE)

# Checked in order — most specific phrase first, so "additional reinforcement
# work" isn't also double-counted as a separate "reinforcement work" match.
_WORK_ACTIVITY_PHRASES = [
    "additional reinforcement work",
    "reinforcement work",
]

_ORGANIZATION_KEYWORDS = ["contractor", "employer", "engineer"]

STRUCTURE_CONFIDENCE = 0.9
WORK_ACTIVITY_CONFIDENCE = 0.9
ORGANIZATION_CONFIDENCE = 0.7


class ConstructionEntityExtractor:
    """Extracts ConstructionEntity objects from a question via simple,
    deterministic heuristics — not yet backed by an LLM or NLP library.
    `investigation_type` is accepted for interface stability (future
    heuristics may specialize by type) but unused today."""

    def extract(self, question: str, investigation_type: str) -> EntityExtractionResult:
        """Return every entity found in `question` across all supported
        heuristics. Returns an empty EntityExtractionResult if none match."""
        entities: list[ConstructionEntity] = []
        entities.extend(self._extract_structures(question))
        entities.extend(self._extract_work_activities(question))
        entities.extend(self._extract_organizations(question))
        return EntityExtractionResult(entities=entities)

    def _extract_structures(self, question: str) -> list[ConstructionEntity]:
        return [
            ConstructionEntity(
                name=match.group(0),
                entity_type=EntityType.STRUCTURE,
                confidence=STRUCTURE_CONFIDENCE,
            )
            for match in _STRUCTURE_PATTERN.finditer(question)
        ]

    def _extract_work_activities(self, question: str) -> list[ConstructionEntity]:
        lowered = question.lower()
        for phrase in _WORK_ACTIVITY_PHRASES:
            index = lowered.find(phrase)
            if index != -1:
                matched_text = question[index : index + len(phrase)]
                return [
                    ConstructionEntity(
                        name=matched_text.capitalize(),
                        entity_type=EntityType.WORK_ACTIVITY,
                        confidence=WORK_ACTIVITY_CONFIDENCE,
                    )
                ]
        return []

    def _extract_organizations(self, question: str) -> list[ConstructionEntity]:
        lowered = question.lower()
        return [
            ConstructionEntity(
                name=keyword.capitalize(),
                entity_type=EntityType.ORGANIZATION,
                confidence=ORGANIZATION_CONFIDENCE,
            )
            for keyword in _ORGANIZATION_KEYWORDS
            if keyword in lowered
        ]
