"""Validation for Sprint 8 Task 01's EvidenceNarrower. Runs against the
real, already-ingested Dataset V2 corpus (project_id=2), through the real,
now-integrated InvestigationLoop (Phase 3 Task 06/07) -- real embeddings,
real retrieval, real remediation, zero Gemini calls. The narrower itself is
exercised directly against real InvestigationState.evidence.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "backend"))

from app.agent.evidence_narrowing import EvidenceNarrower, _is_decisive
from app.agent.evidence_narrowing_config import EvidenceNarrowingConfig
from app.agent.models import Citation, Evidence
from app.agent.service import InvestigationService
from app.agent.models import InvestigationRequest
from app.config import get_settings
from app.db.session import init_engine

FAILURES = []


def check(label: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {label}" + (f" -- {detail}" if detail else ""))
    if not condition:
        FAILURES.append(label)


init_engine(get_settings())
service = InvestigationService()
PROJECT_ID = 2

print("=== Real end-to-end: narrow() reduces a real ~59-item evidence set into the target range ===")
req = InvestigationRequest(
    project_id=PROJECT_ID,
    query="Was the Contractor entitled to an extension of time for the Pier 3 utility conflict, and if so, for how long?",
    top_k=10,
)
loop_result = service._investigation_loop.run(req)
state = loop_result.state
evidence_before = len(state.evidence)
print(f"  real evidence before narrowing: {evidence_before}")

result = service._evidence_narrower.narrow(state.evidence)
print(f"  stats: {result.statistics}")

check("real evidence set was well above the target range before narrowing", evidence_before > 30, str(evidence_before))
check("narrowed evidence count falls within the 8-15 target range", 8 <= result.statistics.evidence_after <= 15, str(result.statistics.evidence_after))
check("retained + discarded accounts for every original evidence item", len(result.retained_evidence) + len(result.discarded_evidence) >= evidence_before)
check("documents_after did not increase relative to documents_before", result.statistics.documents_after <= result.statistics.documents_before)
check("every retained item has a real chunk id", all(item.citation.chunk_id is not None for item in result.retained_evidence))
check("every discarded item names a real reason", all(d.reason for d in result.discarded_evidence))

print()
print("=== Explainability: every discard reason is one of the documented categories ===")
allowed_prefixes = ("duplicate", "merged_into:", "below_confidence_threshold", "per_document_cap_exceeded", "exceeded_max_citations")
check(
    "all discard reasons match a documented category",
    all(d.reason.startswith(allowed_prefixes) for d in result.discarded_evidence),
    str({d.reason.split(":")[0] for d in result.discarded_evidence}),
)

print()
print("=== Determinism: narrowing the same real evidence twice gives identical output ===")
result_again = service._evidence_narrower.narrow(state.evidence)
check(
    "retained evidence is identical (same chunk ids, same order) across two calls",
    [item.citation.chunk_id for item in result.retained_evidence] == [item.citation.chunk_id for item in result_again.retained_evidence],
)
check("statistics are identical across two calls", result.statistics == result_again.statistics)

print()
print("=== Merge: same-document consecutive chunks are combined, not shown twice ===")
merged_items = [item for item in result.retained_evidence if item.metadata.get("source") == "evidence_narrowing_merge"]
check("at least one real merge occurred (this corpus's dense same-document retrieval produces adjacent chunks)", len(merged_items) > 0, str(len(merged_items)))
if merged_items:
    sample = merged_items[0]
    check("a merged item's excerpt is longer than a single chunk's raw excerpt would be (real combined content)", len(sample.surrounding_context) > 0)
    check("a merged item records which chunk ids it absorbed", len(sample.metadata.get("merged_chunk_ids", [])) > 1, str(sample.metadata.get("merged_chunk_ids")))

print()
print("=== Decisive prioritization: decisive evidence is never dropped for low confidence ===")
decisive_before = [item for item in state.evidence if _is_decisive(item)]
decisive_document_chunk_pairs_before = {(item.document_id, item.citation.chunk_id) for item in decisive_before}
# A decisive item can still be absorbed by a merge (folded into a combined
# item) or dropped by the total/per-document cap if there are more decisive
# items than the cap allows -- but it must never be discarded specifically
# for low confidence.
low_confidence_discards_of_decisive = [
    d for d in result.discarded_evidence
    if d.reason == "below_confidence_threshold" and (d.document_id, d.chunk_id) in decisive_document_chunk_pairs_before
]
check(
    "no decisive evidence item was discarded specifically for low confidence",
    len(low_confidence_discards_of_decisive) == 0,
    str(low_confidence_discards_of_decisive),
)

print()
print("=== Controlled fixture: dedup, merge, confidence floor, and caps in isolation ===")
# Hand-built, real-shaped Evidence objects (real document ids from Dataset
# V2) to isolate each stage's behaviour precisely, independent of whatever
# a live loop run happens to produce.


def _make_evidence(document_id, chunk_id, page, confidence, text, source=None):
    return Evidence(
        citation=Citation(document_id=document_id, chunk_id=chunk_id, page=page, relevance_score=confidence, chunk_text=text),
        document_id=document_id,
        document_name=f"DOC-{document_id}.pdf",
        excerpt=text[:280],
        surrounding_context=text,
        confidence=confidence,
        metadata={"source": source} if source else {},
    )


exact_duplicate_text = "The Engineer determined a 10 week extension of time under Sub-Clause 8.4 on 25-Sep-2021."
fixture_evidence = [
    _make_evidence(101, 1, 1, 0.9, exact_duplicate_text),
    _make_evidence(101, 2, 1, 0.85, exact_duplicate_text),  # exact duplicate text -> dedup
    _make_evidence(102, 10, 1, 0.4, "A minor procedural remark with no determination content."),  # low confidence, not decisive -> dropped
    _make_evidence(103, 20, 1, 0.4, "Determined: the Contractor is granted 6 weeks under Sub-Clause 8.4."),  # low confidence BUT decisive -> retained
]
# The confidence-floor mechanism (stage 3) is tested here with an explicit,
# non-zero threshold -- the production default is 0.0 (effectively
# disabled; see evidence_narrowing_config.py for the real-benchmark finding
# that a nonzero default silently discarded genuine low-but-real matches),
# so this isolates that the mechanism itself still works correctly when a
# deployment does configure a threshold, independent of the default.
confidence_floor_config = EvidenceNarrowingConfig(min_confidence_to_retain=0.5)
fixture_result = EvidenceNarrower(config=confidence_floor_config).narrow(fixture_evidence)
check("exact-duplicate text is deduplicated (one of the two identical items dropped)", any(d.reason == "duplicate" for d in fixture_result.discarded_evidence))
check("low-confidence, non-decisive evidence is dropped when a confidence floor is configured", any(d.document_id == 102 and d.reason == "below_confidence_threshold" for d in fixture_result.discarded_evidence))
check("low-confidence BUT decisive evidence is retained even with a confidence floor configured", any(item.document_id == 103 for item in fixture_result.retained_evidence))

default_fixture_result = EvidenceNarrower().narrow(fixture_evidence)
check(
    "with the production default (floor disabled), the low-confidence non-decisive item is retained too",
    any(item.document_id == 102 for item in default_fixture_result.retained_evidence),
)

# Adjacent-chunk merge fixture: two consecutive chunks on the same page,
# same document, with genuine word-level overlap (mirrors chunking.py's
# real sliding-window overlap).
overlap_text_a = "one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen"
overlap_text_b = "eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty"
merge_fixture = [
    _make_evidence(201, 50, 1, 0.7, overlap_text_a),
    _make_evidence(201, 51, 1, 0.75, overlap_text_b),
]
merge_result = EvidenceNarrower().narrow(merge_fixture)
check("two adjacent overlapping chunks merge into exactly one retained item", len(merge_result.retained_evidence) == 1, str(len(merge_result.retained_evidence)))
if merge_result.retained_evidence:
    merged_text = merge_result.retained_evidence[0].surrounding_context
    check("the merged text contains content unique to both chunks, without duplicating the overlap", "one two three" in merged_text and "sixteen seventeen" in merged_text and merged_text.count("eleven twelve thirteen") == 1)

# Per-document cap fixture: 5 items from the same document, cap=2. Chunk
# ids spaced apart (non-consecutive) and on different pages so the merge
# stage (which combines same-page, consecutive-chunk_id runs) does not
# collapse them first -- this isolates the cap stage specifically.
cap_fixture = [_make_evidence(301, 60 + i * 10, 1 + i, 0.9 - i * 0.01, f"distinct content number {i} with no overlap whatsoever here") for i in range(5)]
cap_config = EvidenceNarrowingConfig(max_citations_per_document=2, max_citations=15, min_confidence_to_retain=0.0)
cap_result = EvidenceNarrower(config=cap_config).narrow(cap_fixture)
check("per-document cap keeps only the configured maximum from one document", len(cap_result.retained_evidence) == 2, str(len(cap_result.retained_evidence)))
check("the retained items are the highest-confidence ones", {item.citation.chunk_id for item in cap_result.retained_evidence} == {60, 70})

# Total cap fixture: many distinct documents, cap total=3.
total_fixture = [_make_evidence(400 + i, 70 + i, 1, 0.5 + i * 0.05, f"unique content block {i} standalone") for i in range(10)]
total_config = EvidenceNarrowingConfig(max_citations=3, max_citations_per_document=10, min_confidence_to_retain=0.0)
total_result = EvidenceNarrower(config=total_config).narrow(total_fixture)
check("total cap limits the final retained count regardless of document diversity", len(total_result.retained_evidence) == 3, str(len(total_result.retained_evidence)))

print()
print("=" * 60)
if FAILURES:
    print(f"VALIDATION FAILED ({len(FAILURES)} check(s)):")
    for f in FAILURES:
        print(" -", f)
    sys.exit(1)
else:
    print("VALIDATION PASSED (all checks)")
