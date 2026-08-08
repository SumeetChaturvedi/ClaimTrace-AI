"""Validate the generated Contract Package PDF set, using the same checks
as validate_scenario_pdfs.py (existence, filenames, page open, chrome-aware
text-fidelity diff, index.json completeness)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from pypdf import PdfReader

from pdf_template import LETTERHEADS
from contracts_data import DOCUMENTS
from validate_scenario_pdfs import normalize, strip_chrome, header_prefix

SCRIPT_DIR = Path(__file__).resolve().parent
DATASET_ROOT = SCRIPT_DIR.parent


def validate() -> bool:
    out_dir = DATASET_ROOT / "pdf" / "contracts"
    index_path = out_dir / "index.json"
    all_ok = True

    print(f"Validating contracts ({len(DOCUMENTS)} documents)\n")

    if not index_path.exists():
        print(f"FAIL: index.json missing at {index_path}")
        return False
    index = json.loads(index_path.read_text())
    if len(index) != len(DOCUMENTS):
        print(f"FAIL: index.json has {len(index)} entries, expected {len(DOCUMENTS)}")
        all_ok = False

    for spec in DOCUMENTS:
        pdf_path = out_dir / f"{spec.doc_id}.pdf"
        print(f"-- {spec.doc_id} --")

        if not pdf_path.exists():
            print("  FAIL: PDF file does not exist")
            all_ok = False
            continue
        if pdf_path.name != f"{spec.doc_id}.pdf":
            print(f"  FAIL: filename {pdf_path.name} does not match document reference")
            all_ok = False

        try:
            reader = PdfReader(str(pdf_path))
        except Exception as exc:
            print(f"  FAIL: could not open PDF ({exc})")
            all_ok = False
            continue

        n_pages = len(reader.pages)
        print(f"  OK: opens successfully, {n_pages} page(s)")

        prefix = header_prefix(spec)

        def _clean_page(raw: str, is_continuation: bool) -> str:
            cleaned = normalize(strip_chrome(raw))
            if is_continuation and cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
            return cleaned

        full_text = normalize(
            " ".join(
                _clean_page(page.extract_text() or "", is_continuation=(i > 0))
                for i, page in enumerate(reader.pages)
            )
        )

        expected_strings = [spec.title, spec.doc_id, spec.date, spec.from_, spec.to]
        for kind, content in spec.body:
            if kind == "table":
                if content.get("headers"):
                    expected_strings.extend(str(h) for h in content["headers"])
                for row in content["rows"]:
                    expected_strings.extend(str(c) for c in row)
            else:
                expected_strings.append(content)

        missing = [e[:80] for e in expected_strings if normalize(e) not in full_text]
        if missing:
            print(f"  FAIL: {len(missing)} expected string(s) not found verbatim:")
            for m in missing:
                print(f"      - {m}...")
            all_ok = False
        else:
            print(f"  OK: all {len(expected_strings)} expected content blocks found verbatim")
        print()

    print("=" * 60)
    print("VALIDATION PASSED" if all_ok else "VALIDATION FAILED")
    return all_ok


if __name__ == "__main__":
    ok = validate()
    sys.exit(0 if ok else 1)
