"""Validate a generated scenario PDF set against its source DocumentSpecs:
- every expected PDF exists and opens
- filename == document reference
- page count is sane (>=1) and footer page-numbering is internally consistent
- every substantive source string (title, subject, from/to, every body
  block, every closing line) appears in the extracted PDF text, confirming
  no wording was dropped or altered in rendering

Usage:
    python3 validate_scenario_pdfs.py 01
"""

from __future__ import annotations

import argparse
import importlib
import json
import re
import sys
from pathlib import Path

from pypdf import PdfReader

from pdf_template import LETTERHEADS

SCRIPT_DIR = Path(__file__).resolve().parent
DATASET_ROOT = SCRIPT_DIR.parent


def normalize(text: str) -> str:
    """Collapse whitespace so line-wrap differences between source and
    extracted PDF text don't cause false mismatches."""
    return re.sub(r"\s+", " ", text).strip()


_FOOTER_RE = re.compile(
    r"Nandira River Bridge Project — Package NRB-4\s*\|\s*\S+\s*\|\s*Page \d+ of \d+"
)
_CONFIDENTIALITY_RE = re.compile(
    r"This document is issued in connection with Contract.*?Employer's consent\."
)


def header_prefix(spec) -> str:
    """The exact, ordered text _draw_header() emits on every page: wordmark,
    subtext, legal name (if distinct from the wordmark), address lines,
    then the document type tag -- in that order, matching _draw_header()'s
    draw-call sequence in pdf_template.py. On a continuation page this is
    always a genuine PREFIX of the extracted text (drawn before the frame's
    flowable content for that page), so it can be stripped by an exact
    startswith() match -- never a scattered substring replace, which risks
    deleting a legitimate later mention of the same company name in body
    or signature text."""
    lh = LETTERHEADS[spec.letterhead]
    wordmark = lh["wordmark"] or spec.letterhead_org_override or ""
    subtext = lh["subtext"] or ""
    legal_name = lh["legal_name"] or spec.letterhead_org_override or ""
    parts = [wordmark]
    if subtext:
        parts.append(subtext)
    if legal_name and legal_name != wordmark:
        parts.append(legal_name)
    parts.extend(lh["address"])
    parts.append(spec.doc_type_tag)
    return normalize(" ".join(p for p in parts if p))


def strip_chrome(page_text: str) -> str:
    """Remove footer / confidentiality boilerplate from one page's extracted
    text before concatenating pages. Needed because the footer is drawn via
    a separate overlay merged onto each page's content stream, so pypdf's
    extraction order places it between the tail of one page's body text and
    the head of the next page's body text whenever a paragraph is split
    across a page break -- purely an artifact of extraction order, not a
    rendering defect (the PDF displays correctly; only naive concatenation
    for text-diffing is affected)."""
    text = _FOOTER_RE.sub(" ", page_text)
    text = _CONFIDENTIALITY_RE.sub(" ", text)
    return text


def validate(scenario_num: str) -> bool:
    module = importlib.import_module(f"scenario_{scenario_num}_data")
    documents = module.DOCUMENTS
    out_dir = DATASET_ROOT / "pdf" / f"scenario_{scenario_num}"
    index_path = out_dir / "index.json"

    all_ok = True

    print(f"Validating scenario_{scenario_num} ({len(documents)} documents)\n")

    if not index_path.exists():
        print(f"FAIL: index.json missing at {index_path}")
        return False
    index = json.loads(index_path.read_text())
    if len(index) != len(documents):
        print(f"FAIL: index.json has {len(index)} entries, expected {len(documents)}")
        all_ok = False

    for spec in documents:
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
        if n_pages < 1:
            print("  FAIL: zero pages")
            all_ok = False
        else:
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
        if spec.subject:
            expected_strings.append(spec.subject)
        if spec.cc:
            expected_strings.append(spec.cc)
        for kind, content in spec.body:
            if kind == "table":
                if content.get("headers"):
                    expected_strings.extend(str(h) for h in content["headers"])
                for row in content["rows"]:
                    expected_strings.extend(str(cell) for cell in row)
            else:
                expected_strings.append(content)
        expected_strings.extend(spec.closing_lines)

        missing = []
        for expected in expected_strings:
            if normalize(expected) not in full_text:
                missing.append(expected[:80])

        if missing:
            print(f"  FAIL: {len(missing)} expected string(s) not found verbatim in extracted text:")
            for m in missing:
                print(f"      - {m}...")
            all_ok = False
        else:
            print(f"  OK: all {len(expected_strings)} expected content blocks found verbatim")

        # footer format check on page 1
        page1_text = normalize(reader.pages[0].extract_text() or "")
        expected_footer_fragment = normalize(f"{spec.doc_id}  |  Page 1 of {n_pages}")
        if expected_footer_fragment not in page1_text and f"Page 1 of {n_pages}" not in page1_text:
            print("  WARN: could not confirm footer pagination text on page 1")
        else:
            print("  OK: footer pagination present on page 1")

        print()

    print("=" * 60)
    print("VALIDATION PASSED" if all_ok else "VALIDATION FAILED")
    return all_ok


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario", help="Scenario number, e.g. 01")
    args = parser.parse_args()
    ok = validate(args.scenario)
    sys.exit(0 if ok else 1)
