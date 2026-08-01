"""Deterministic keyword-based classification of investigation questions.

Isolated from InvestigationPlanner (service.py) specifically so it can be
swapped for a smarter classifier later (e.g. LLM-backed) without touching
create_plan()'s public signature — only this module would need to change.

V1: simple lowercase substring keyword matching, checked in a fixed
priority order (the order SUPPORTED_TYPES lists them). No LLM, no
embeddings, no regex. This is a known, accepted limitation for a
"lightweight planning task," not an oversight — ambiguous or oddly-phrased
questions may be misclassified, and questions matching multiple categories
resolve to whichever category is checked first.
"""

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
}

SUPPORTED_TYPES = [*_KEYWORDS_BY_TYPE.keys(), UNKNOWN_TYPE]


def classify_investigation_type(question: str) -> str:
    """Classify `question` into one of SUPPORTED_TYPES by keyword match.
    Returns "unknown" if no keyword matches."""
    lowered = question.lower()
    for investigation_type, keywords in _KEYWORDS_BY_TYPE.items():
        if any(keyword in lowered for keyword in keywords):
            return investigation_type
    return UNKNOWN_TYPE
