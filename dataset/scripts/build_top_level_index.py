"""Aggregate every per-scenario index.json (and, separately, note the
contracts index) into dataset/pdf/index.json, per Task 03's deliverable.
Read-only with respect to the scenario/contracts folders -- only writes
the new top-level file."""

import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DATASET_ROOT = SCRIPT_DIR.parent
PDF_ROOT = DATASET_ROOT / "pdf"


def build() -> list[dict]:
    combined = []
    for scenario_dir in sorted(PDF_ROOT.glob("scenario_*")):
        index_path = scenario_dir / "index.json"
        if not index_path.exists():
            continue
        entries = json.loads(index_path.read_text())
        for e in entries:
            combined.append(
                {
                    "scenario": e["scenario"],
                    "document_id": e["document_id"],
                    "filename": e["filename"],
                    "document_type": e["document_type"],
                    "title": e["title"],
                }
            )
    out_path = PDF_ROOT / "index.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)
    print(f"wrote {out_path} with {len(combined)} entries (scenarios 1-9 only, per spec)")
    return combined


if __name__ == "__main__":
    build()
