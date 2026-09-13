"""Focused tests for DOCX ingestion (Phase 7: Multi-Format Evidence) —
proves the real .docx extraction/storage/serving path added in
app/ingestion/docx_extraction.py, app/ingestion/pipeline.py, and
app/api/routes/document_file.py, reusing the exact same
project-scoped upload/list/file endpoints test_project_documents.py
already exercises for PDF.

Same approach as the rest of this test suite: plain `unittest` +
TestClient, no mocks, real Postgres, real ingestion pipeline (python-docx
extraction, deterministic chunking, local sentence-transformers
embeddings, pgvector storage) — a real .docx is built with python-docx
itself, the same library the pipeline uses, not a hand-rolled fixture
string masquerading as one.

Run with:
    cd backend && source .venv/bin/activate
    PYTHONPATH=. python3 -m unittest tests.test_docx_ingestion -v
"""

import io
import unittest

import docx
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.models import Document, DocumentChunk, Project
from app.db.session import get_session_factory
from app.main import app

NONEXISTENT_PROJECT_ID = 999_999


def _build_test_docx(paragraphs: list[str]) -> bytes:
    """A minimal, real, valid multi-paragraph .docx — built via python-docx
    itself, so this exercises the real extract -> chunk -> embed -> index
    path exactly as a genuine upload would."""
    document = docx.Document()
    for text in paragraphs:
        document.add_paragraph(text)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


class DocxIngestionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.client.__enter__()  # runs the app's real lifespan (DB init)
        cls._created_project_ids: list[int] = []

    @classmethod
    def tearDownClass(cls):
        with get_session_factory()() as session:
            for project_id in cls._created_project_ids:
                documents = session.query(Document).filter(Document.project_id == project_id).all()
                for document in documents:
                    session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
                session.query(Document).filter(Document.project_id == project_id).delete()
                session.query(Project).filter(Project.id == project_id).delete()
            session.commit()
        cls.client.__exit__(None, None, None)

    def _create_project(self, name: str) -> int:
        resp = self.client.post("/projects", json={"name": name})
        assert resp.status_code == 201, resp.text
        project_id = resp.json()["id"]
        self._created_project_ids.append(project_id)
        return project_id

    def test_upload_real_docx_becomes_ready_with_paragraph_located_chunks(self):
        project_id = self._create_project("Test Suite DOCX Project A")
        # A blank paragraph before the target one, so the resulting chunk's
        # page_number (really a paragraph ordinal for DOCX — see
        # docx_extraction.py) must be > 1 if paragraph position is genuinely
        # tracked, not just defaulted to 1.
        content = _build_test_docx(
            [
                "Site Correspondence",
                "",
                "This paragraph contains the unique marker CLAIMTRACE-DOCX-TEST-77213 for retrieval verification.",
                "A closing paragraph with no special content.",
            ]
        )
        resp = self.client.post(
            f"/projects/{project_id}/documents",
            files={"files": ("site-letter.docx", io.BytesIO(content), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
        self.assertEqual(resp.status_code, 201, resp.text)
        body = resp.json()
        self.assertEqual(body["rejected"], [])
        self.assertEqual(len(body["documents"]), 1)
        document = body["documents"][0]
        self.assertEqual(document["status"], "ready")
        self.assertIsNone(document["processing_error"])

        with get_session_factory()() as session:
            chunks = session.query(DocumentChunk).filter(DocumentChunk.document_id == document["id"]).all()
            self.assertGreater(len(chunks), 0, "no chunks were created for the uploaded DOCX")
            self.assertTrue(all(c.embedding is not None for c in chunks), "a chunk was persisted without an embedding")

            marker_chunks = [c for c in chunks if "CLAIMTRACE-DOCX-TEST-77213" in c.chunk_text]
            self.assertEqual(len(marker_chunks), 1, "expected exactly one chunk to contain the unique marker")
            # Paragraphs are 1-based and every paragraph (including the
            # blank one) is counted, so the marker's own paragraph is the
            # 3rd paragraph in the source .docx.
            self.assertEqual(marker_chunks[0].page_number, 3)

    def test_docx_file_is_served_with_the_correct_media_type(self):
        project_id = self._create_project("Test Suite DOCX Project B")
        content = _build_test_docx(["A short real paragraph."])
        upload_resp = self.client.post(
            f"/projects/{project_id}/documents",
            files={"files": ("memo.docx", io.BytesIO(content), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
        document_id = upload_resp.json()["documents"][0]["id"]

        file_resp = self.client.get(f"/projects/{project_id}/documents/{document_id}/file")
        self.assertEqual(file_resp.status_code, 200)
        self.assertEqual(
            file_resp.headers["content-type"],
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        # The real DOCX bytes round-trip: a genuine .docx is itself a zip,
        # which always starts with the "PK" local-file-header signature.
        self.assertTrue(file_resp.content.startswith(b"PK"))

    def test_docx_document_from_one_project_not_retrievable_via_another(self):
        project_a = self._create_project("Test Suite DOCX Project C")
        project_b = self._create_project("Test Suite DOCX Project D")
        content = _build_test_docx(["Cross-project isolation check paragraph."])
        upload_resp = self.client.post(
            f"/projects/{project_a}/documents",
            files={"files": ("isolation-check.docx", io.BytesIO(content), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
        document_id = upload_resp.json()["documents"][0]["id"]

        cross_meta_resp = self.client.get(f"/projects/{project_b}/documents/{document_id}")
        self.assertEqual(cross_meta_resp.status_code, 404)
        cross_file_resp = self.client.get(f"/projects/{project_b}/documents/{document_id}/file")
        self.assertEqual(cross_file_resp.status_code, 404)

        own_file_resp = self.client.get(f"/projects/{project_a}/documents/{document_id}/file")
        self.assertEqual(own_file_resp.status_code, 200)

    def test_malformed_docx_is_persisted_as_failed_not_dropped_or_crashed(self):
        # A file with a .docx extension whose content isn't a real zip/OOXML
        # archive at all -- must not be pre-flight-rejected (the extension
        # is valid), must not crash the request, and must not silently
        # disappear: it becomes a real, visible, failed Document row, same
        # as a corrupt PDF already does.
        project_id = self._create_project("Test Suite DOCX Project E")
        resp = self.client.post(
            f"/projects/{project_id}/documents",
            files={"files": ("corrupt.docx", io.BytesIO(b"this is not a real docx file at all"), "application/octet-stream")},
        )
        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        self.assertEqual(body["rejected"], [])
        self.assertEqual(len(body["documents"]), 1)
        document = body["documents"][0]
        self.assertEqual(document["status"], "failed")
        self.assertIsNotNone(document["processing_error"])
        # The persisted error is a short, sanitized message, not a raw
        # Python traceback dumped to the user.
        self.assertNotIn("Traceback", document["processing_error"])
        self.assertLess(len(document["processing_error"]), 500)

        list_resp = self.client.get(f"/projects/{project_id}/documents")
        filenames = [d["filename"] for d in list_resp.json()]
        self.assertIn("corrupt.docx", filenames, "a failed document must still be visible, never silently dropped")

    def test_empty_docx_upload_is_rejected_before_creating_a_document(self):
        project_id = self._create_project("Test Suite DOCX Project F")
        resp = self.client.post(
            f"/projects/{project_id}/documents",
            files={"files": ("empty.docx", io.BytesIO(b""), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
        body = resp.json()
        self.assertEqual(body["documents"], [])
        self.assertEqual(len(body["rejected"]), 1)
        self.assertIn("empty", body["rejected"][0]["error"])

    def test_pdf_and_docx_can_both_be_uploaded_to_the_same_project(self):
        # Confirms the two formats coexist without interference in the
        # same project register -- neither pipeline branch clobbers the
        # other's storage directory or document rows.
        import fitz

        project_id = self._create_project("Test Suite DOCX Project G")
        pdf_doc = fitz.open()
        pdf_doc.new_page().insert_text((50, 72), "A real test PDF page.", fontsize=11)
        pdf_bytes = pdf_doc.tobytes()
        docx_bytes = _build_test_docx(["A real test DOCX paragraph."])

        pdf_resp = self.client.post(
            f"/projects/{project_id}/documents",
            files={"files": ("mixed-test.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )
        docx_resp = self.client.post(
            f"/projects/{project_id}/documents",
            files={"files": ("mixed-test.docx", io.BytesIO(docx_bytes), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
        self.assertEqual(pdf_resp.json()["documents"][0]["status"], "ready")
        self.assertEqual(docx_resp.json()["documents"][0]["status"], "ready")

        list_resp = self.client.get(f"/projects/{project_id}/documents")
        filenames = {d["filename"] for d in list_resp.json()}
        self.assertIn("mixed-test.pdf", filenames)
        self.assertIn("mixed-test.docx", filenames)


if __name__ == "__main__":
    unittest.main()
