"""Incrementally ingest Scenario 11's 14 PDFs (dataset/pdf/scenario_11/)
into the EXISTING Dataset V2 project (project_id=2), using the same
unmodified ingestion pipeline (app.ingestion.pipeline.ingest_document)
ingest_dataset_v2.py and ingest_scenario_10.py already used. Does not create
a new project and does not touch any existing Document row.

Run from backend/:
    cd backend && PYTHONPATH=. .venv/bin/python3 ../dataset/scripts/ingest_scenario_11.py

Same metadata-enrichment note as ingest_scenario_10.py: doc_type/doc_date
are filled in afterwards from scenario_11_data.py's own DocumentSpec ground
truth (not from the unmodified regex extractor, which doesn't recognise
this dataset's metadata-box casing/labels), exactly as prior scenarios were
enriched. referenced_ids is left exactly as the existing, unmodified regex
extraction produces it.
"""

from __future__ import annotations

import importlib
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
EXISTING_PROJECT_ID = 2
SCENARIO_MODULE = "scenario_11_data"


def load_ground_truth() -> dict[str, dict]:
    mod = importlib.import_module(SCENARIO_MODULE)
    return {spec.doc_id: {"doc_type": spec.doc_type, "date": spec.date} for spec in mod.DOCUMENTS}


def parse_date(raw: str) -> "datetime.date | None":
    try:
        return datetime.strptime(raw, "%d-%b-%Y").date()
    except ValueError:
        return None


def main() -> None:
    settings = get_settings()
    init_engine(settings)
    session_factory = get_session_factory()
    db = session_factory()

    project = db.get(Project, EXISTING_PROJECT_ID)
    if project is None:
        raise SystemExit(f"Project id={EXISTING_PROJECT_ID} does not exist -- refusing to create a new one.")
    print(f"Ingesting into existing project id={project.id} name={project.name!r}")

    existing_count_before = db.query(Document).filter(Document.project_id == project.id).count()
    print(f"Documents already in this project before this run: {existing_count_before}")

    ground_truth = load_ground_truth()

    scenario_dir = PDF_ROOT / "scenario_11"
    index = json.loads((scenario_dir / "index.json").read_text())
    paths = [scenario_dir / entry["filename"] for entry in index]
    print(f"Found {len(paths)} PDFs to ingest for Scenario 11\n")

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

    existing_count_after = db.query(Document).filter(Document.project_id == project.id).count()
    db.close()

    ok = [r for r in results if r["status"] == "OK"]
    fail = [r for r in results if r["status"] == "FAIL"]
    total_chunks = sum(r["chunk_count"] for r in ok)
    null_type = [r for r in ok if r["doc_type"] is None]
    null_date = [r for r in ok if r["doc_date"] is None]

    summary = {
        "project_id": project.id,
        "project_name": project.name,
        "scenario": 11,
        "documents_before": existing_count_before,
        "documents_after": existing_count_after,
        "total_pdfs_this_run": len(paths),
        "ingested_ok": len(ok),
        "ingested_fail": len(fail),
        "total_chunks_this_run": total_chunks,
        "null_doc_type_after_enrichment": len(null_type),
        "null_doc_date_after_enrichment": len(null_date),
        "elapsed_seconds": round(elapsed, 1),
        "failures": fail,
    }

    out_path = DATASET_ROOT / "scripts" / "ingestion_report_scenario_11.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "documents": results}, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print(json.dumps(summary, indent=2))
    print(f"\nFull per-document report written to {out_path}")


if __name__ == "__main__":
    main()
