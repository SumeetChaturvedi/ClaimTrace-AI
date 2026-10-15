"""Phase 8B.2 — production evaluation adapter.

Bridges the real, committed `EventExtractor` (backend/app/agent/event_extraction.py)
to the already-committed Phase 8B.1 gold dataset/scorer (dataset/event_eval/).
This is the ONE file in this package allowed to import backend/app/ — every
other module here (gold_schema.py, dataset.py, scorer.py, ...) stays
independent of the production application, per gold_schema.py's own module
docstring; this script's entire purpose is being the seam between the two,
so it is exempt from that independence by design, not by accident.

What this does, concretely, per scenario:
  1. Creates one throwaway Project in the REAL database.
  2. Imports that scenario's MESSAGES into it via the REAL, unmodified
     email ingestion pipeline (app.email_ingestion.pipeline.ingest_email_bytes)
     — real Document/EmailMessage/DocumentChunk rows, real embeddings.
     For S06 specifically, synthesizes a real one-page PDF (via PyMuPDF,
     the same library the production PDF pipeline itself uses) containing
     the scenario's ATTACHMENT_TEXT and attaches it to the covering email,
     so the attachment path is genuinely exercised end-to-end rather than
     assumed from the fixture's plain-text stand-in.
  3. Reads back every real DocumentChunk belonging to that project and
     wraps each as an Evidence object (document_id/chunk_id/chunk_text) —
     the exact shape EventExtractor.extract() consumes in production,
     fed directly rather than through a full InvestigationService run, to
     keep the Gemini call budget at exactly one extraction call per
     scenario (12 calls total) instead of however many an investigation
     loop's own remediation iterations would add.
  4. Calls the real EventExtractor.extract() once for that project's full
     evidence set.
  5. Converts each returned ExtractedEvent back into a CandidateEvent
     (dataset/event_eval/gold_schema.py) via a document_id -> message_key
     map recorded during step 2 (the only information CandidateEvent needs
     that ExtractedEvent itself doesn't carry).

All 12 scenarios' candidates are then scored in one call against the full
DATASET.gold_events, exactly mirroring run_event_eval.py's own pattern (see
that script; this one reuses score()/DEFAULT_THRESHOLDS unchanged, no new
scoring logic). Each throwaway project is deleted at the end regardless of
outcome.

Run with (from the repository root, backend's venv active, GEMINI_API_KEY set):
    cd backend && source .venv/bin/activate
    PYTHONPATH=".:..:../dataset/scripts" python3 -m dataset.event_eval.run_production_eval
"""

from __future__ import annotations

import json
import sys
import time
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dataset.event_eval.dataset import DATASET
from dataset.event_eval.gold_schema import CandidateEvent
from dataset.event_eval.scorer import DEFAULT_THRESHOLDS, attribution_accuracy_normalized, passes_thresholds, score
from dataset.event_eval.scenarios import (
    scenario_01_clarification_delay as s01,
    scenario_02_instruction_revised_drawing as s02,
    scenario_03_contractor_notice as s03,
    scenario_04_commitment_follow_up as s04,
    scenario_05_conflicting_accounts as s05,
    scenario_06_attachment_evidence as s06,
    scenario_07_late_received_email as s07,
    scenario_08_ambiguous_date as s08,
    scenario_09_broken_threading as s09,
    scenario_10_similar_subjects as s10,
    scenario_11_unsupported_assertion as s11,
    scenario_12_irrelevant_noise as s12,
)

_SCENARIO_MODULES = [s01, s02, s03, s04, s05, s06, s07, s08, s09, s10, s11, s12]

RESULTS_PATH = Path(__file__).resolve().parent / "production_eval_results.json"


def _generic_question(scenario_id: str) -> str:
    return (
        f"[{scenario_id}] Summarize what happened in this correspondence: what was requested, "
        "instructed, committed to, reported, or claimed, and by whom."
    )


def main() -> int:
    from app.agent.event_extraction import EventExtractionError, EventExtractor
    from app.agent.models import Evidence, Citation
    from app.db.init_db import initialize_database
    from app.db.models import Document, DocumentChunk, EmailAttachment, EmailMessage, Project
    from app.db.session import get_session_factory
    from app.config import get_settings
    from app.email_ingestion.pipeline import ingest_email_bytes
    from sqlalchemy import create_engine, select

    settings = get_settings()
    engine = create_engine(settings.database_url)
    initialize_database(engine, settings)

    extractor = EventExtractor()
    session_factory = get_session_factory()

    all_candidates: list[CandidateEvent] = []
    gemini_calls = 0
    gemini_errors = 0
    scenario_reports: dict[str, dict] = {}
    created_project_ids: list[int] = []
    started = time.monotonic()

    try:
        for module in _SCENARIO_MODULES:
            scenario_id = module.SCENARIO_ID
            with session_factory() as session:
                project = Project(name=f"Phase 8B.2 eval — {scenario_id}")
                session.add(project)
                session.commit()
                project_id = project.id
                created_project_ids.append(project_id)

                message_key_by_document_id: dict[int, str] = {}

                for message_key, raw_eml in module.MESSAGES.items():
                    raw_eml_for_ingest = raw_eml
                    if scenario_id == "S06" and message_key == "S06-M01":
                        raw_eml_for_ingest = _attach_pdf_to_eml(raw_eml, module.ATTACHMENT_TEXTS["S06-ATT01"])

                    outcome = ingest_email_bytes(
                        session=session,
                        storage_root=Path(settings.storage_root),
                        project_id=project_id,
                        source_name=f"{message_key}.eml",
                        raw_bytes=raw_eml_for_ingest,
                    )
                    if outcome.status != "imported" or outcome.document_id is None:
                        scenario_reports.setdefault(scenario_id, {}).setdefault("ingest_warnings", []).append(
                            f"{message_key}: {outcome.status} ({outcome.error})"
                        )
                        continue
                    message_key_by_document_id[outcome.document_id] = message_key

                    if scenario_id == "S06" and message_key == "S06-M01":
                        attachment = session.scalars(
                            select(EmailAttachment).where(EmailAttachment.message_id == outcome.document_id)
                        ).first()
                        if attachment is not None and attachment.document_id is not None:
                            message_key_by_document_id[attachment.document_id] = "S06-ATT01"

                document_ids = list(message_key_by_document_id.keys())
                chunks = session.scalars(
                    select(DocumentChunk).where(DocumentChunk.document_id.in_(document_ids))
                ).all() if document_ids else []

                evidence = [
                    Evidence(
                        citation=Citation(
                            document_id=chunk.document_id,
                            chunk_id=chunk.id,
                            relevance_score=1.0,
                            chunk_text=chunk.chunk_text,
                        ),
                        document_id=chunk.document_id,
                        document_name=message_key_by_document_id.get(chunk.document_id, "unknown"),
                        excerpt=chunk.chunk_text[:280],
                        surrounding_context=chunk.chunk_text,
                        confidence=1.0,
                        metadata={},
                    )
                    for chunk in chunks
                ]

            scenario_started = time.monotonic()
            truncated = False
            try:
                extraction_result = extractor.extract(_generic_question(scenario_id), evidence)
                extracted = extraction_result.events
                truncated = extraction_result.truncated
                gemini_calls += 1
            except EventExtractionError as exc:
                gemini_calls += 1
                gemini_errors += 1
                scenario_reports.setdefault(scenario_id, {})["error"] = str(exc)
                extracted = []
            scenario_elapsed = time.monotonic() - scenario_started

            scenario_candidates = []
            for event in extracted:
                source_message_key = message_key_by_document_id.get(event.document_id)
                if source_message_key is None:
                    continue  # cannot map back to a fixture key; excluded rather than guessed
                scenario_candidates.append(
                    CandidateEvent(
                        source_message_key=source_message_key,
                        excerpt=event.excerpt,
                        event_type=event.event_type,
                        assertion_type=event.assertion_type,
                        event_date=event.event_date.isoformat() if isinstance(event.event_date, date) else None,
                        event_date_basis=event.event_date_basis,
                        attributed_party=event.attributed_party,
                    )
                )

            all_candidates.extend(scenario_candidates)
            scenario_reports.setdefault(scenario_id, {}).update({
                "evidence_chunks": len(evidence),
                "raw_extracted_count": len(extracted),
                "candidates_mapped": len(scenario_candidates),
                "truncated": truncated,
                "elapsed_seconds": round(scenario_elapsed, 2),
            })
            print(f"[{scenario_id}] evidence={len(evidence)} extracted={len(extracted)} "
                  f"mapped={len(scenario_candidates)} truncated={truncated} elapsed={scenario_elapsed:.1f}s")

        report = score(DATASET, list(DATASET.gold_events), all_candidates)
        threshold_results = passes_thresholds(report, DEFAULT_THRESHOLDS)
        normalized_attribution = attribution_accuracy_normalized(report)

        # Candidate-level detail (Quality Remediation task): not part of
        # score()'s own aggregate metrics, purely for human error analysis
        # — every candidate, whether matched or not, with its own fields
        # and (if matched) the gold fields it was scored against.
        candidate_detail = []
        matched_by_identity = {id(pair.candidate): pair for pair in report.matched_pairs}
        for candidate in all_candidates:
            pair = matched_by_identity.get(id(candidate))
            entry = {
                "source_message_key": candidate.source_message_key,
                "excerpt": candidate.excerpt,
                "event_type": candidate.event_type,
                "assertion_type": candidate.assertion_type,
                "event_date": candidate.event_date,
                "event_date_basis": candidate.event_date_basis,
                "attributed_party": candidate.attributed_party,
                "matched_gold_id": pair.gold.event_id if pair else None,
            }
            if pair is not None:
                entry["gold"] = {
                    "event_type": pair.gold.event_type,
                    "assertion_type": pair.gold.assertion_type,
                    "event_date": pair.gold.event_date,
                    "event_date_basis": pair.gold.event_date_basis,
                    "attributed_party": pair.gold.attributed_party,
                    "sources": [s.message_key for s in pair.gold.sources],
                }
                entry["matched_source_message_key"] = pair.matched_source_message_key
            candidate_detail.append(entry)

        result = {
            "total_elapsed_seconds": round(time.monotonic() - started, 2),
            "gemini_calls": gemini_calls,
            "gemini_errors": gemini_errors,
            "any_scenario_truncated": any(r.get("truncated") for r in scenario_reports.values()),
            "total_candidates": report.total_candidates,
            "total_gold_events": report.total_gold_events,
            "matched_count": len(report.matched_pairs),
            "metrics": {
                "recall": report.recall,
                "precision": report.precision,
                "event_type_accuracy": report.event_type_accuracy,
                "date_accuracy": report.date_accuracy,
                "date_basis_accuracy": report.date_basis_accuracy,
                "attribution_accuracy": report.attribution_accuracy,
                "attribution_accuracy_normalized": normalized_attribution,
                "source_link_accuracy": report.source_link_accuracy,
                "duplicate_event_rate": report.duplicate_event_rate,
                "unsupported_event_rate": report.unsupported_event_rate,
                "conflict_preservation_rate": report.conflict_preservation_rate,
                "abstention_rate": report.abstention_rate,
            },
            "threshold_results": threshold_results,
            "unmatched_gold_ids": [g.event_id for g in report.unmatched_gold],
            "unmatched_candidate_sources": [c.source_message_key for c in report.unmatched_candidates],
            "unsupported_candidate_indices": report.unsupported_candidate_indices,
            "wrong_source_link_pairs": [
                {"gold_id": p.gold.event_id, "candidate_source": p.candidate.source_message_key, "matched_source": p.matched_source_message_key}
                for p in report.wrong_source_link_pairs
            ],
            "scenario_reports": scenario_reports,
            "candidate_detail": candidate_detail,
        }

        print("\n=== Phase 8B.2 production evaluation ===")
        print(f"Gemini calls: {gemini_calls}  errors: {gemini_errors}  elapsed: {result['total_elapsed_seconds']}s")
        for metric, value in result["metrics"].items():
            print(f"  {metric}: {value}")
        print("\nThreshold results (official — exact-string attribution_accuracy, unchanged thresholds):")
        for metric, passed in threshold_results.items():
            print(f"  {'PASS' if passed else 'FAIL'}  {metric}")
        print(
            f"\n  (informational only, not an official threshold) attribution_accuracy_normalized: "
            f"{normalized_attribution} -- {'PASS' if (normalized_attribution is None or normalized_attribution >= DEFAULT_THRESHOLDS.min_attribution_accuracy) else 'FAIL'} "
            f"against the SAME unchanged 0.90 threshold"
        )

        RESULTS_PATH.write_text(json.dumps(result, indent=2))
        print(f"\nWrote {RESULTS_PATH}")

        return 0 if all(threshold_results.values()) else 1
    finally:
        from sqlalchemy import delete

        # Core-level delete (not session.delete(project)): the ORM's default
        # cascade behavior for an unconfigured relationship is to NULL each
        # child's FK before deleting the parent, which violates documents.
        # project_id's NOT NULL constraint. A Core DELETE goes straight to
        # SQL and lets the real, database-level ON DELETE CASCADE (already
        # declared on Document.project_id et al.) do the job correctly.
        with session_factory() as session:
            for project_id in created_project_ids:
                session.execute(delete(Project).where(Project.id == project_id))
            session.commit()
        print(f"\nCleaned up {len(created_project_ids)} throwaway project(s).")


def _attach_pdf_to_eml(raw_eml: bytes, attachment_text: str) -> bytes:
    """Rebuild `raw_eml` (an S06-M01-shaped message with no attachment)
    with a real one-page PDF attachment containing `attachment_text`,
    using the exact PyMuPDF technique backend/tests/test_email_ingestion.py's
    own `_build_test_pdf` helper uses — not reusing that test module
    directly (this script must not import backend/tests/), just its
    already-proven technique."""
    import email as email_lib
    import email.policy
    import fitz

    original = email_lib.message_from_bytes(raw_eml, policy=email.policy.default)

    # insert_text() draws one line verbatim with no wrapping — the
    # attachment's own long, unbroken paragraph (no internal '\n') would
    # extend far past the page's right edge and get silently clipped from
    # the page's extractable text (discovered via this task's own
    # candidate-level error analysis: the real indexed chunk_text for this
    # attachment was truncated mid-sentence). insert_textbox() wraps text
    # to fit a given rectangle, so the full paragraph is actually rendered
    # — and therefore actually extractable — on the page.
    pdf_doc = fitz.open()
    page = pdf_doc.new_page()
    page.insert_textbox(fitz.Rect(50, 50, 545, 792), attachment_text, fontsize=10)
    pdf_bytes = pdf_doc.tobytes()

    rebuilt = email_lib.message.EmailMessage(policy=email.policy.default)
    for header in ("Message-ID", "In-Reply-To", "References", "From", "To", "Cc", "Subject", "Date"):
        if header in original:
            rebuilt[header] = original[header]
    body_part = original.get_body(preferencelist=("plain",))
    rebuilt.set_content(body_part.get_content() if body_part else "")
    rebuilt.add_attachment(pdf_bytes, maintype="application", subtype="pdf", filename="inspection_report.pdf")
    return rebuilt.as_bytes()


if __name__ == "__main__":
    raise SystemExit(main())
