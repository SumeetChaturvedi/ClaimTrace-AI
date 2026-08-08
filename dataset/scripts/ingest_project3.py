"""Create Project 3 (Kestrel Flyover Interchange Project — Package KFI-2)
and ingest its complete, independent PDF corpus (4 contract package
documents + 14 Scenario 12 documents) using the existing, unmodified
ingestion pipeline (app.ingestion.pipeline.ingest_document) — mirrors
ingest_dataset_v2.py's own structure (which created project_id=2) exactly,
for a brand new, unrelated project. Refuses to proceed if a project named
PROJECT_NAME already exists, to avoid creating a duplicate on a re-run.

Run from backend/:
    cd backend && PYTHONPATH=. .venv/bin/python3 ../dataset/scripts/ingest_project3.py

Same metadata-enrichment note as ingest_dataset_v2.py/ingest_scenario_10.py:
doc_type/doc_date are filled in afterwards from this dataset's own
DocumentSpec ground truth (contracts_data_kfi2.py + scenario_12_data.py),
not from the unmodified regex extractor (label-casing mismatch, same as
every prior scenario). referenced_ids is left exactly as the existing,
unmodified regex extraction produces it.
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
from sqlalchemy import select

DATASET_ROOT = Path(__file__).resolve().parent.parent
PDF_ROOT = DATASET_ROOT / "pdf"
PROJECT_NAME = "Kestrel Flyover Interchange Project — Package KFI-2"


def load_ground_truth() -> dict[str, dict]:
    truth: dict[str, dict] = {}
    for mod_name in ("contracts_data_kfi2", "scenario_12_data"):
        mod = importlib.import_module(mod_name)
        for spec in mod.DOCUMENTS:
            truth[spec.doc_id] = {"doc_type": spec.doc_type, "date": spec.date}
    return truth


def parse_date(raw: str) -> "datetime.date | None":
    try:
        return datetime.strptime(raw, "%d-%b-%Y").date()
    except ValueError:
        return None


def ordered_pdf_paths() -> list[Path]:
    """Contracts (KFI2's own, independent package) first, then Scenario 12,
    in DOCUMENTS order — same convention as ingest_dataset_v2.py."""
    paths: list[Path] = []
    contracts_index = json.loads((PDF_ROOT / "contracts_kfi2" / "index.json").read_text())
    for entry in contracts_index:
        paths.append(PDF_ROOT / "contracts_kfi2" / entry["filename"])
    scenario_index = json.loads((PDF_ROOT / "scenario_12" / "index.json").read_text())
    for entry in scenario_index:
        paths.append(PDF_ROOT / "scenario_12" / entry["filename"])
    return paths


def main() -> None:
    settings = get_settings()
    init_engine(settings)
    session_factory = get_session_factory()
    db = session_factory()

    existing = db.scalar(select(Project).where(Project.name == PROJECT_NAME))
    if existing is not None:
        raise SystemExit(
            f"Project {PROJECT_NAME!r} already exists as id={existing.id} -- refusing to "
            "create a duplicate. Delete it first if you intend to re-run this script."
        )

    project = Project(name=PROJECT_NAME)
    db.add(project)
    db.commit()
    db.refresh(project)
    print(f"Created project id={project.id} name={project.name!r}")

    ground_truth = load_ground_truth()
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
    project_id, project_name = project.id, project.name
    db.close()

    ok = [r for r in results if r["status"] == "OK"]
    fail = [r for r in results if r["status"] == "FAIL"]
    total_chunks = sum(r["chunk_count"] for r in ok)
    null_type = [r for r in ok if r["doc_type"] is None]
    null_date = [r for r in ok if r["doc_date"] is None]

    summary = {
        "project_id": project_id,
        "project_name": project_name,
        "total_pdfs": len(paths),
        "ingested_ok": len(ok),
        "ingested_fail": len(fail),
        "total_chunks": total_chunks,
        "null_doc_type_after_enrichment": len(null_type),
        "null_doc_date_after_enrichment": len(null_date),
        "elapsed_seconds": round(elapsed, 1),
        "failures": fail,
    }

    out_path = DATASET_ROOT / "scripts" / "ingestion_report_project3.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "documents": results}, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print(json.dumps(summary, indent=2))
    print(f"\nFull per-document report written to {out_path}")


if __name__ == "__main__":
    main()
