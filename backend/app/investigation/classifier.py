"""Deterministic keyword-based classification of investigation questions.

Isolated from InvestigationPlanner (service.py) specifically so it can be
swapped for a smarter classifier later (e.g. LLM-backed) without touching
create_plan()'s public signature — only this module would need to change.

V1.1: whole-word/whole-phrase keyword matching (Sprint 4 Task 02), checked in
a fixed priority order (the order SUPPORTED_TYPES lists them). No LLM, no
embeddings. Each keyword is matched via a `\\b...\\b`-bounded regex rather
than plain substring containment, so a keyword only fires when it appears as
a complete word or complete phrase — "late" matches "running late" but not
"relate"; "instruction" matches "the instruction" but not, say, a made-up
word like "reinstruction". This replaces Sprint 3.5's discovered substring-
collision bugs (e.g. "relate" being misclassified as "delay" via "late") with
whole-word matching; it does not change the keyword lists, the priority
order, or the public API — only how each keyword is tested against the
question text. Ambiguous or oddly-phrased questions may still be
misclassified, and questions matching multiple categories still resolve to
whichever category is checked first — this is still a known, accepted
limitation for a "lightweight planning task," not an oversight.

Sprint 7 Task 5: five categories added — quality, programme, practical
completion, defects, taking over — covering investigation types the
original seven (built against Dataset V1's delay/variation/payment/approval-
centric vocabulary) had no coverage for, so a question like "was the
concrete quality non-conformance legitimate?" or "does the punch list
prevent Practical Completion?" no longer falls through to "unknown". Added
strictly after the original seven in _KEYWORDS_BY_TYPE, so priority order
for every pre-existing category is unchanged and no previously-classified
question can be reclassified — this is purely additive.
"""

import re

UNKNOWN_TYPE = "unknown"

# Order doubles as classification priority: for a question matching more
# than one category's keywords, the first (in this order) wins.
_KEYWORDS_BY_TYPE: dict[str, list[str]] = {
    "approval": [
        "approve", "approved", "approval", "authorised", "authorized",
        "sign-off", "signed off",
    ],
    "delay": [
        "delay", "delayed", "late", "behind schedule", "extension of time",
    ],
    "variation": [
        "variation", "instructed", "instruction", "change order",
    ],
    "entitlement": [
        "entitle", "entitled", "entitlement", "claim", "eligible",
    ],
    "payment": [
        "payment", "paid", "invoice", "valuation", "amount due", "cost buildup",
    ],
    "evidence": [
        "evidence", "which documents", "what documents", "proof",
        "supporting documents",
    ],
    "compliance": [
        "compliance", "comply", "compliant", "breach", "violation",
        "notice period", "contractual obligation",
    ],
    # -- Sprint 7 Task 5: added after the original seven; see module
    # docstring. Priority order among these five is arbitrary (no benchmark
    # question matched more than one), listed in the order Task 5 itself
    # lists the categories.
    "quality": [
        "quality", "non-conformance", "nonconformance", "ncr",
        "concrete strength", "cube test", "workmanship",
    ],
    "programme": [
        "recovery programme", "recovery program", "critical path",
        "programme update", "program update", "resource loading",
    ],
    "practical_completion": [
        "practical completion", "beneficial use",
    ],
    "defects": [
        "defect", "defects", "defects notification period",
        "remedy the defect", "remedy defects",
    ],
    "taking_over": [
        "taking-over", "taking over", "punch list", "punch-list",
        "outstanding items",
    ],
}

SUPPORTED_TYPES = [*_KEYWORDS_BY_TYPE.keys(), UNKNOWN_TYPE]

# Each keyword/phrase compiled once at import time into a \b-bounded regex,
# so matching tests for a complete word or complete phrase rather than mere
# substring containment (Sprint 4 Task 02) — same keyword lists, same
# priority order, only the test itself changed.
_KEYWORD_PATTERNS_BY_TYPE: dict[str, list[re.Pattern[str]]] = {
    investigation_type: [re.compile(rf"\b{re.escape(keyword)}\b") for keyword in keywords]
    for investigation_type, keywords in _KEYWORDS_BY_TYPE.items()
}


def classify_investigation_type(question: str) -> str:
    """Classify `question` into one of SUPPORTED_TYPES by whole-word/
    whole-phrase keyword match. Returns "unknown" if no keyword matches."""
    lowered = question.lower()
    for investigation_type, patterns in _KEYWORD_PATTERNS_BY_TYPE.items():
        if any(pattern.search(lowered) for pattern in patterns):
            return investigation_type
    return UNKNOWN_TYPE
