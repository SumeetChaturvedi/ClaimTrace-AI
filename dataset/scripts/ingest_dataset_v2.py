"""Ingest the complete Dataset V2 PDF corpus (dataset/pdf/**) into ClaimTrace
using the existing, unmodified ingestion pipeline
(app.ingestion.pipeline.ingest_document).

Run from backend/ so .env / relative storage_root resolve correctly:
    cd backend && ../.venv-or-system-python -m ... (see README note printed
    at the bottom of this file) — in practice invoked as:
    cd backend && PYTHONPATH=. .venv/bin/python3 ../dataset/scripts/ingest_dataset_v2.py

Metadata enrichment note (read before assuming a bug): ingest_document()
derives doc_type/doc_date via deterministic regex extraction
(app/ingestion/metadata.py) against literal "DOCUMENT TYPE:" / "DATE:"
header text, a stand-in the pipeline's own docstring calls "not a
replacement" for a real classification step and explicitly says these
fields "stay overwritable ... later". Two real incompatibilities exist
between that V1-dataset-shaped extractor and the V2 PDF template's
metadata-box layout:
  1. doc_date: the metadata box renders the label "Date:" (mixed case);
     the extractor's regex requires literal upper-case "DATE:". Purely a
     label-casing mismatch, not a classification problem.
  2. doc_type: normalize_document_type() (app/domain/document_types.py) is
     an explicit, exhaustive lookup keyed on the *exact* raw slugs observed
     in the V1 corpus (e.g. "daily_progress_report") -- it has no entries
     for any V2 document type, and extending it is a backend code change,
     out of scope for this task ("Do NOT modify ClaimTrace backend").
This script does not patch either regex or the backend lookup. Instead,
after calling the unmodified ingest_document(), it fills doc_type/doc_date
from this dataset's own ground truth (the same DocumentSpec data the PDFs
were rendered from) -- exactly the kind of post-hoc enrichment the
pipeline's docstring anticipates a "later" classification step performing.
referenced_ids is left exactly as the existing regex extraction produces
it; that extraction has no such label dependency and works against the
V2 corpus's ID-shaped inline references unchanged.
"""

from __future__ import annotations

import importlib
import io
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # for pdf_template etc.

from app.config import get_settings
from app.db.models import Document, Project
from app.db.session import get_session_factory, init_engine
from app.ingestion.pipeline import IngestionError, ingest_document

DATASET_ROOT = Path(__file__).resolve().parent.parent
PDF_ROOT = DATASET_ROOT / "pdf"
PROJECT_NAME = "Dataset V2 — Nandira River Bridge Project, Package NRB-4"

SCENARIO_MODULES = [f"scenario_{i:02d}_data" for i in range(1, 10)]


def load_ground_truth() -> dict[str, dict]:
    """doc_id -> {doc_type, doc_date} from this dataset's own DocumentSpec
    data (the same source the PDFs were rendered from), plus the 4 contract
    package documents."""
    truth: dict[str, dict] = {}
    for mod_name in SCENARIO_MODULES:
        mod = importlib.import_module(mod_name)
        for spec in mod.DOCUMENTS:
            truth[spec.doc_id] = {"doc_type": spec.doc_type, "date": spec.date}
    contracts_mod = importlib.import_module("contracts_data")
    for spec in contracts_mod.DOCUMENTS:
        truth[spec.doc_id] = {"doc_type": spec.doc_type, "date": spec.date}
    return truth


def parse_date(raw: str) -> "datetime.date | None":
    for fmt in ("%d-%b-%Y",):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def ordered_pdf_paths() -> list[Path]:
    """Contracts first, then each scenario folder in its own documented
    ingestion order (== the order DOCUMENTS is listed in each *_data.py,
    which generate_scenario_pdfs.py already renders in, and index.json
    already reflects)."""
    paths: list[Path] = []
    contracts_index = json.loads((PDF_ROOT / "contracts" / "index.json").read_text())
    for entry in contracts_index:
        paths.append(PDF_ROOT / "contracts" / entry["filename"])
    for i in range(1, 10):
        scenario_dir = PDF_ROOT / f"scenario_{i:02d}"
        index = json.loads((scenario_dir / "index.json").read_text())
        for entry in index:
            paths.append(scenario_dir / entry["filename"])
    return paths


def main() -> None:
    settings = get_settings()
    init_engine(settings)
    session_factory = get_session_factory()
    db = session_factory()

    ground_truth = load_ground_truth()

    project = Project(name=PROJECT_NAME)
    db.add(project)
    db.commit()
    db.refresh(project)
    print(f"Created project id={project.id} name={project.name!r}")

    paths = ordered_pdf_paths()
    print(f"Found {len(paths)} PDFs to ingest\n")

    results = []
    t0 = time.time()
    for path in paths:
        doc_id = path.stem
        content = path.read_bytes()
        try:
            document = ingest_document(
                session=db,
                storage_root=settings.storage_root,
                project_id=project.id,
                filename=path.name,
                content=content,
            )
        except IngestionError as exc:
            print(f"  FAIL {doc_id}: {exc}")
            results.append({"doc_id": doc_id, "status": "FAIL", "error": str(exc)})
            continue

        truth = ground_truth.get(doc_id)
        enriched = False
        if truth is not None:
            canonical_type = truth["doc_type"]
            canonical_date = parse_date(truth["date"])
            if document.doc_type != canonical_type or document.doc_date != canonical_date:
                document.doc_type = canonical_type
                document.doc_date = canonical_date
                db.commit()
                db.refresh(document)
                enriched = True

        chunk_count = len(document.chunks)
        results.append(
            {
                "doc_id": doc_id,
                "status": "OK",
                "document_pk": document.id,
                "doc_type": document.doc_type,
                "doc_date": str(document.doc_date) if document.doc_date else None,
                "referenced_ids": document.referenced_ids,
                "chunk_count": chunk_count,
                "metadata_enriched": enriched,
            }
        )
        print(
            f"  OK   {doc_id:24s} pk={document.id:3d} type={document.doc_type!s:16s} "
            f"date={document.doc_date} chunks={chunk_count}"
        )

    elapsed = time.time() - t0
    db.close()

    ok = [r for r in results if r["status"] == "OK"]
    fail = [r for r in results if r["status"] == "FAIL"]
    total_chunks = sum(r["chunk_count"] for r in ok)
    null_type = [r for r in ok if r["doc_type"] is None]
    null_date = [r for r in ok if r["doc_date"] is None]

    summary = {
        "project_id": project.id,
        "project_name": project.name,
        "total_pdfs": len(paths),
        "ingested_ok": len(ok),
        "ingested_fail": len(fail),
        "total_chunks": total_chunks,
        "null_doc_type_after_enrichment": len(null_type),
        "null_doc_date_after_enrichment": len(null_date),
        "elapsed_seconds": round(elapsed, 1),
        "failures": fail,
    }

    out_path = DATASET_ROOT / "scripts" / "ingestion_report.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "documents": results}, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print(json.dumps(summary, indent=2))
    print(f"\nFull per-document report written to {out_path}")


if __name__ == "__main__":
    main()
