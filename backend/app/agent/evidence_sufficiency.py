"""EvidenceSufficiencyAssessor — the deterministic decision model from the
approved Investigation Agent architecture (Phase 3 Task 01 foundation; the
loop that would act on its decisions is not built yet, and nothing here is
wired into InvestigationService or any production path).

Evaluates an InvestigationState (investigation_state.py) against four
assessment stages, in priority order, and returns a single
SufficiencyDecision: either "sufficient, stop" or "not sufficient, here is
the ONE highest-priority remediation needed" — never more than one
remediation at a time, so a future orchestrator's iterations stay targeted
and explainable (see the architecture spec's Decision Model, §5).

Deliberately stateless and DB-free: assess() takes only an InvestigationState
and returns a value, touching no database, no retrieval, no LLM. This is
what makes it independently testable with hand-built state fixtures and
keeps "deciding" cleanly separated from "doing" — remediation (running a
search, expanding a reference, reading a document) is the orchestrator's
job, never this module's.

Reference resolution contract: stage 1 flags a document-reference-shaped
string as unresolved whenever it is NOT already in
state.followed_reference_ids. Whether a reference actually turns out to
name a new document, an already-visited one, or nothing in the corpus can
only be known by querying the database — deliberately out of scope here.
The contract is: whoever processes a reference (the future orchestrator)
must call state.mark_reference_followed() for every reference it looks at,
regardless of outcome, or this assessor will keep re-flagging it.
"""

import re

from pydantic import BaseModel, Field

from app.agent.investigation_state import InvestigationState, RemediationType
from app.ingestion.metadata import extract_document_references

# Stage 3 thresholds.
ENTITY_COVERAGE_THRESHOLD = 0.7
MIN_CONFIDENT_EVIDENCE_COUNT = 2
CONFIDENCE_THRESHOLD = 0.6

# Stage 4 thresholds. A document is "dominant" once it supplies at least
# this share of current evidence; it is also required to have at least
# MIN_EVIDENCE_FOR_DOMINANCE items, so a single-item evidence set (100%
# from one document, trivially) doesn't get flagged as under-informative
# before there was ever a chance to diversify it.
DOMINANT_DOCUMENT_SHARE = 0.5
MIN_EVIDENCE_FOR_DOMINANCE = 2

# Sub-Clause 8.4 / Clause 13 style references. Deliberately generic (not
# tied to the 10 sub-clauses in any one contract package) since this
# assessor must not assume which dataset it's running against.
_CLAUSE_REFERENCE_RE = re.compile(r"\b(?:Sub-Clause|Clause)\s+(\d+(?:\.\d+)*)\b", re.IGNORECASE)

# Words indicating a sentence states a determination/outcome rather than
# just describing an event — used only alongside a digit (see
# _has_determination_content below), not on their own, to stay a coarse,
# dataset-agnostic heuristic rather than a claim of real understanding.
_DETERMINATION_WORDS = (
    "granted", "rejected", "determined", "determination", "approved",
    "denied", "entitled", "entitlement", "certified", "confirmed",
)
_DETERMINATION_PATTERNS = [re.compile(rf"\b{word}\b", re.IGNORECASE) for word in _DETERMINATION_WORDS]
_DIGIT_RE = re.compile(r"\d")


class SufficiencyDecision(BaseModel):
    """The assessor's output: either sufficient (remediation is None) or a
    single remediation to perform next, plus enough structured detail for
    the caller to act on it without re-deriving anything, and a
    human-readable reason for the explainability trail."""

    sufficient: bool
    remediation: RemediationType | None = Field(
        default=None, description="The single highest-priority remediation needed, or None if sufficient"
    )
    reason: str = Field(description="Human-readable explanation, suitable for a search_history entry")
    details: dict = Field(
        default_factory=dict,
        description="Remediation-specific structured payload (see EvidenceSufficiencyAssessor docstring)",
    )


def _combined_evidence_text(state: InvestigationState) -> str:
    """All current evidence excerpts, concatenated, as the text every
    text-scanning stage below searches against. Uses `excerpt` (the
    specific supporting text) rather than `surrounding_context`, matching
    what a reader would actually be shown."""
    return " ".join(item.excerpt for item in state.evidence)


def _whole_word_present(term: str, text: str) -> bool:
    """Whole-word/whole-phrase containment check, the same `\\b`-bounded
    approach already used by app/investigation/classifier.py and
    app/domain/document_types.py, for the same reason: a plain substring
    check would let e.g. "contract" match inside "contractor"."""
    if not term:
        return False
    return re.search(rf"\b{re.escape(term)}\b", text, re.IGNORECASE) is not None


def _has_determination_content(text: str) -> bool:
    """Coarse heuristic for "this text states an outcome, not just a fact":
    at least one digit (a number, date, or amount) together with at least
    one determination-indicating word. Deliberately approximate — a stand-in
    for genuine understanding, in the same spirit as the classifier's
    keyword matching elsewhere in this codebase."""
    if not _DIGIT_RE.search(text):
        return False
    return any(pattern.search(text) for pattern in _DETERMINATION_PATTERNS)


class EvidenceSufficiencyAssessor:
    """Runs the four assessment stages, in priority order, against an
    InvestigationState and returns the first (highest-priority) unmet one,
    or a "sufficient" decision if none fire. Holds no state of its own —
    safe to share a single instance across investigations, or construct a
    fresh one per call; both are equivalent."""

    def assess(self, state: InvestigationState) -> SufficiencyDecision:
        """Evaluate `state` and return a SufficiencyDecision. Never
        mutates `state`; never performs retrieval, DB access, or an LLM
        call."""
        for stage in (
            self._check_unresolved_references,
            self._check_missing_clauses,
            self._check_coverage_and_confidence,
            self._check_dominant_document,
        ):
            decision = stage(state)
            if decision is not None:
                return decision

        return SufficiencyDecision(
            sufficient=True,
            remediation=None,
            reason="All sufficiency checks passed: no unresolved references, no missing named clauses, "
            "adequate entity coverage and confident evidence, and no under-informative dominant document.",
        )

    # -- Stage 1: unresolved document references -----------------------

    def _check_unresolved_references(self, state: InvestigationState) -> SufficiencyDecision | None:
        references = extract_document_references(_combined_evidence_text(state))
        unresolved = [ref for ref in references if ref not in state.followed_reference_ids]
        if not unresolved:
            return None

        return SufficiencyDecision(
            sufficient=False,
            remediation=RemediationType.REFERENCE_EXPANSION,
            reason=(
                f"Evidence text mentions {len(unresolved)} document reference(s) not yet followed: "
                f"{', '.join(unresolved)}."
            ),
            details={"unresolved_references": unresolved},
        )

    # -- Stage 2: named clauses not retrieved ----------------------------

    def _check_missing_clauses(self, state: InvestigationState) -> SufficiencyDecision | None:
        mentioned = {m.group(1) for m in _CLAUSE_REFERENCE_RE.finditer(_combined_evidence_text(state))}
        missing = sorted(mentioned - state.retrieved_clause_numbers)
        if not missing:
            return None

        return SufficiencyDecision(
            sufficient=False,
            remediation=RemediationType.CLAUSE_TOP_UP,
            reason=(
                f"Evidence text names {len(missing)} contract clause(s) not among the retrieved "
                f"clauses: {', '.join(missing)}."
            ),
            details={"missing_clause_numbers": missing},
        )

    # -- Stage 3: low entity coverage / confidence -----------------------

    def _check_coverage_and_confidence(self, state: InvestigationState) -> SufficiencyDecision | None:
        text = _combined_evidence_text(state)
        entities = state.plan.primary_entities

        if entities:
            covered = [entity for entity in entities if _whole_word_present(entity, text)]
            coverage = len(covered) / len(entities)
        else:
            coverage = 1.0

        confident_count = sum(1 for item in state.evidence if item.confidence >= CONFIDENCE_THRESHOLD)

        coverage_ok = coverage >= ENTITY_COVERAGE_THRESHOLD
        confidence_ok = confident_count >= MIN_CONFIDENT_EVIDENCE_COUNT

        if coverage_ok and confidence_ok:
            return None

        return SufficiencyDecision(
            sufficient=False,
            remediation=RemediationType.FOCUSED_RETRIEVAL,
            reason=(
                f"Entity coverage {coverage:.0%} (threshold {ENTITY_COVERAGE_THRESHOLD:.0%}) or "
                f"confident evidence count {confident_count} (threshold {MIN_CONFIDENT_EVIDENCE_COUNT}) "
                "not yet met."
            ),
            details={
                "entity_coverage": coverage,
                "uncovered_entities": [e for e in entities if not _whole_word_present(e, text)],
                "confident_evidence_count": confident_count,
            },
        )

    # -- Stage 4: dominant document with insufficient information --------

    def _check_dominant_document(self, state: InvestigationState) -> SufficiencyDecision | None:
        if len(state.evidence) < MIN_EVIDENCE_FOR_DOMINANCE:
            return None

        counts: dict[int, int] = {}
        for item in state.evidence:
            counts[item.document_id] = counts.get(item.document_id, 0) + 1

        dominant_document_id, dominant_count = max(counts.items(), key=lambda pair: pair[1])
        share = dominant_count / len(state.evidence)
        if share < DOMINANT_DOCUMENT_SHARE:
            return None

        dominant_text = " ".join(
            item.excerpt for item in state.evidence if item.document_id == dominant_document_id
        )
        if _has_determination_content(dominant_text):
            return None

        if dominant_document_id in state.fully_read_document_ids:
            # Already read in full once — reading it again would not add
            # information. Not this assessor's job to pick a different
            # remediation; it simply has nothing further to recommend for
            # this document.
            return None

        return SufficiencyDecision(
            sufficient=False,
            remediation=RemediationType.FULL_DOCUMENT_READ,
            reason=(
                f"Document {dominant_document_id} supplies {share:.0%} of current evidence but its "
                "retrieved excerpts contain no clear determination/outcome content."
            ),
            details={"document_id": dominant_document_id},
        )
