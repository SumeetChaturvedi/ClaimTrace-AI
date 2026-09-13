"""Focused tests for GET /projects/{project_id}/documents/{document_id}/file.

No test framework existed in this repository before this file (confirmed:
no tests/ directory, no pytest in requirements.txt, no conftest.py
anywhere) — and per this task's explicit "do not introduce a new
dependency" instruction, this does not add pytest either. It uses only
the standard library's `unittest` plus `fastapi.testclient.TestClient`
(already available: TestClient requires httpx, which is already installed
as a transitive dependency of fastapi in this project's venv).

These tests run against the REAL app, the REAL Postgres/pgvector database,
and the REAL files under backend/storage/ — the same ingested Project
1/2/3 dataset the rest of this codebase's validate_*.py scripts use. No
mocks. Requires the same local setup as running the app itself: the
`claimtrace-db` Postgres container up (`docker compose up -d`).

Run with:
    cd backend && source .venv/bin/activate
    python3 -m unittest tests.test_document_file -v
"""

import os
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

# Real, stable documents from the real dataset (verified present at the
# time this test was written): project 2's contract package and project
# 3's contract package are both ingested once, early, and never modified
# by later scenario work, so their ids are stable anchors for these tests.
PROJECT_2_ID = 2
PROJECT_2_DOCUMENT_ID = 19  # NRB4-GC-2020.pdf

PROJECT_3_ID = 3
PROJECT_3_DOCUMENT_ID = 118  # KFI2-GC-2019.pdf

NONEXISTENT_DOCUMENT_ID = 999_999  # well beyond the real max document id


class DocumentFileEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.client.__enter__()  # runs the app's real lifespan (DB init)

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)

    def _pdf_path_for(self, project_id: int, document_id: int) -> Path:
        """Independently resolves a document's real stored PDF path, using
        the same DB row the endpoint itself reads, to set up/verify tests
        without duplicating the endpoint's own logic as the assertion."""
        from sqlalchemy import select

        from app.db.models import Document
        from app.db.session import get_session_factory
        from app.ingestion.storage import pdf_storage_dir

        with get_session_factory()() as session:
            document = session.scalar(select(Document).where(Document.id == document_id))
        assert document is not None and document.project_id == project_id
        storage_key = Path(document.raw_text_path).stem
        return pdf_storage_dir(get_settings().storage_root, project_id) / f"{storage_key}.pdf"

    # 1. Valid Project 2 + Project 2 document -> PDF returned.
    def test_valid_project_2_document_returns_pdf(self):
        resp = self.client.get(f"/projects/{PROJECT_2_ID}/documents/{PROJECT_2_DOCUMENT_ID}/file")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers["content-type"], "application/pdf")
        self.assertTrue(resp.content.startswith(b"%PDF-"), "response body is not a real PDF")
        self.assertGreater(len(resp.content), 1000)

    # 2. Valid Project 3 + Project 3 document -> PDF returned.
    def test_valid_project_3_document_returns_pdf(self):
        resp = self.client.get(f"/projects/{PROJECT_3_ID}/documents/{PROJECT_3_DOCUMENT_ID}/file")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers["content-type"], "application/pdf")
        self.assertTrue(resp.content.startswith(b"%PDF-"), "response body is not a real PDF")

    # 3. Non-existent document -> safe 404.
    def test_nonexistent_document_returns_404(self):
        resp = self.client.get(f"/projects/{PROJECT_2_ID}/documents/{NONEXISTENT_DOCUMENT_ID}/file")
        self.assertEqual(resp.status_code, 404)
        self.assertNotIn(b"%PDF-", resp.content)

    # 4. Existing Project 2 document requested under Project 3 -> safe failure.
    def test_project_2_document_requested_under_project_3_fails(self):
        resp = self.client.get(f"/projects/{PROJECT_3_ID}/documents/{PROJECT_2_DOCUMENT_ID}/file")
        self.assertEqual(resp.status_code, 404)
        self.assertNotIn(b"%PDF-", resp.content)

    # 5. Existing Project 3 document requested under Project 2 -> safe failure.
    def test_project_3_document_requested_under_project_2_fails(self):
        resp = self.client.get(f"/projects/{PROJECT_2_ID}/documents/{PROJECT_3_DOCUMENT_ID}/file")
        self.assertEqual(resp.status_code, 404)
        self.assertNotIn(b"%PDF-", resp.content)

    # 6. Stored/missing file case -> safe failure. Exercises the real
    # missing-file branch against a real Document row by temporarily
    # renaming its real PDF aside and restoring it no matter what happens.
    def test_missing_stored_file_returns_safe_404(self):
        pdf_path = self._pdf_path_for(PROJECT_2_ID, PROJECT_2_DOCUMENT_ID)
        self.assertTrue(pdf_path.is_file(), "precondition failed: expected real PDF file is missing")
        moved_aside = pdf_path.with_suffix(".pdf.test_moved_aside")
        os.rename(pdf_path, moved_aside)
        try:
            resp = self.client.get(f"/projects/{PROJECT_2_ID}/documents/{PROJECT_2_DOCUMENT_ID}/file")
            self.assertEqual(resp.status_code, 404)
        finally:
            os.rename(moved_aside, pdf_path)
        self.assertTrue(pdf_path.is_file(), "failed to restore the real PDF file after the test")

    # 7. Content type is application/pdf -- covered by tests 1/2 above;
    # asserted again explicitly here for a document with no page metadata
    # quirks, as a standalone check independent of the "happy path" tests.
    def test_content_type_is_application_pdf(self):
        resp = self.client.get(f"/projects/{PROJECT_2_ID}/documents/{PROJECT_2_DOCUMENT_ID}/file")
        self.assertEqual(resp.headers["content-type"], "application/pdf")

    # 8. No path traversal is possible through the endpoint.
    def test_path_traversal_attempts_are_rejected(self):
        traversal_attempts = [
            f"/projects/{PROJECT_2_ID}/documents/../../../../etc/passwd/file",
            f"/projects/{PROJECT_2_ID}/documents/..%2f..%2f..%2fetc%2fpasswd/file",
            f"/projects/../../etc/documents/{PROJECT_2_DOCUMENT_ID}/file",
            f"/projects/{PROJECT_2_ID}/documents/{PROJECT_2_DOCUMENT_ID}%2f..%2f..%2fetc%2fpasswd/file",
        ]
        for path in traversal_attempts:
            resp = self.client.get(path)
            self.assertNotEqual(resp.status_code, 200, f"traversal attempt unexpectedly succeeded: {path}")
            self.assertNotIn(b"root:", resp.content, f"traversal attempt may have leaked a system file: {path}")

    # Sanity check on the ownership-check code path itself: the derived
    # PDF path must always stay inside the project's own storage
    # directory, never a sibling project's, even for two real, valid,
    # differently-scoped documents.
    def test_derived_paths_stay_within_their_own_project_directory(self):
        from app.ingestion.storage import pdf_storage_dir

        p2_dir = pdf_storage_dir(get_settings().storage_root, PROJECT_2_ID).resolve()
        p3_dir = pdf_storage_dir(get_settings().storage_root, PROJECT_3_ID).resolve()
        p2_pdf = self._pdf_path_for(PROJECT_2_ID, PROJECT_2_DOCUMENT_ID).resolve()
        p3_pdf = self._pdf_path_for(PROJECT_3_ID, PROJECT_3_DOCUMENT_ID).resolve()

        self.assertIn(p2_dir, p2_pdf.parents)
        self.assertIn(p3_dir, p3_pdf.parents)
        self.assertNotIn(p3_dir, p2_pdf.parents)
        self.assertNotIn(p2_dir, p3_pdf.parents)


if __name__ == "__main__":
    unittest.main()
