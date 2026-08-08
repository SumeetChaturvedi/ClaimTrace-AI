"""Generate the production PDF dataset for a given scenario, per Dataset V2
Phase 2A Task 02. Renders each approved document (verbatim content, defined
in scenario_XX_data.py) through the template engine (pdf_template.py) into
dataset/pdf/scenario_XX/, and writes an index.json describing the set.

Usage:
    python3 generate_scenario_pdfs.py 01
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

from pdf_template import render_document, DocumentSpec

SCRIPT_DIR = Path(__file__).resolve().parent
DATASET_ROOT = SCRIPT_DIR.parent


def load_documents(scenario_num: str) -> list[DocumentSpec]:
    module_name = f"scenario_{scenario_num}_data"
    module = importlib.import_module(module_name)
    return module.DOCUMENTS


def generate(scenario_num: str) -> tuple[list[dict], Path]:
    out_dir = DATASET_ROOT / "pdf" / f"scenario_{scenario_num}"
    out_dir.mkdir(parents=True, exist_ok=True)

    documents = load_documents(scenario_num)
    index_entries = []

    for spec in documents:
        filename = f"{spec.doc_id}.pdf"
        out_path = out_dir / filename
        render_document(spec, str(out_path))
        index_entries.append(
            {
                "document_id": spec.doc_id,
                "filename": filename,
                "document_type": spec.doc_type,
                "title": spec.title,
                "scenario": spec.scenario,
            }
        )
        print(f"  rendered {filename}")

    index_path = out_dir / "index.json"
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index_entries, f, indent=2, ensure_ascii=False)
    print(f"  wrote {index_path}")

    return index_entries, out_dir


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario", help="Scenario number, e.g. 01")
    args = parser.parse_args()
    entries, out_dir = generate(args.scenario)
    print(f"\nGenerated {len(entries)} PDFs in {out_dir}")
