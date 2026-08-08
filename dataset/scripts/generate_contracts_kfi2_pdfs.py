"""Generate PDFs for Project 3's 4 Contract Package documents into
dataset/pdf/contracts_kfi2/, mirroring generate_contracts_pdfs.py exactly
(same template engine, same DocumentSpec shape, same index.json format).
Kept as a separate output folder from dataset/pdf/contracts/ (NRB4's own
contract package) since these belong to a different, independent project
and must not be conflated with it."""

from __future__ import annotations

import json
from pathlib import Path

from pdf_template import render_document
from contracts_data_kfi2 import DOCUMENTS

SCRIPT_DIR = Path(__file__).resolve().parent
DATASET_ROOT = SCRIPT_DIR.parent


def generate() -> tuple[list[dict], Path]:
    out_dir = DATASET_ROOT / "pdf" / "contracts_kfi2"
    out_dir.mkdir(parents=True, exist_ok=True)

    index_entries = []
    for spec in DOCUMENTS:
        filename = f"{spec.doc_id}.pdf"
        out_path = out_dir / filename
        render_document(spec, str(out_path))
        index_entries.append(
            {
                "document_id": spec.doc_id,
                "filename": filename,
                "document_type": spec.doc_type,
                "title": spec.title,
            }
        )
        print(f"  rendered {filename}")

    index_path = out_dir / "index.json"
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index_entries, f, indent=2, ensure_ascii=False)
    print(f"  wrote {index_path}")

    return index_entries, out_dir


if __name__ == "__main__":
    entries, out_dir = generate()
    print(f"\nGenerated {len(entries)} PDFs in {out_dir}")
