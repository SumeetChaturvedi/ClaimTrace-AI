"""Focused tests for the project register and project-scoped document
endpoints (Phase 3: Project + Document Foundation) — GET/POST /projects,
GET /projects/{id}, and GET/POST /projects/{project_id}/documents,
GET /projects/{project_id}/documents/{document_id}.

Same approach as test_document_file.py and test_investigations.py: plain
`unittest` + TestClient, no new dependency, real Postgres, real ingestion
pipeline (PyMuPDF extraction, deterministic chunking, local
sentence-transformers embeddings, pgvector storage) — no mocks. Unlike
test_investigations.py, none of this needs a real Gemini call (uploading
and listing documents never invokes the LLM), so this file stays fast.

Projects and documents created here are deleted in tearDownClass.

Run with:
    cd backend && source .venv/bin/activate
    PYTHONPATH=. python3 -m unittest tests.test_project_documents -v
"""

import io
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.models import Document, DocumentChunk, Project
from app.db.session import get_session_factory
from app.main import app

NONEXISTENT_PROJECT_ID = 999_999
NONEXISTENT_DOCUMENT_ID = 999_999

# A minimal, real, valid one-page PDF (not a fixture string masquerading as
# one) -- built once via PyMuPDF, the same library the real extraction
# pipeline uses, so this exercises the real extract -> chunk -> embed ->
# index path exactly as a genuine upload would.
def _build_test_pdf(text: str) -> bytes:
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), text, fontsize=11)
    return doc.tobytes()


class ProjectAndDocumentEndpointsTests(unittest.TestCase):
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

    # -- Projects ---------------------------------------------------------

    def test_list_projects_includes_the_real_seeded_projects(self):
        resp = self.client.get("/projects")
        self.assertEqual(resp.status_code, 200)
        ids = [p["id"] for p in resp.json()]
        self.assertIn(1, ids)
        self.assertIn(2, ids)
        self.assertIn(3, ids)

    def test_create_project_persists_and_is_listed(self):
        project_id = self._create_project("Test Suite Project A")
        resp = self.client.get(f"/projects/{project_id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["name"], "Test Suite Project A")

        list_resp = self.client.get("/projects")
        self.assertIn(project_id, [p["id"] for p in list_resp.json()])

    def test_get_nonexistent_project_returns_404(self):
        resp = self.client.get(f"/projects/{NONEXISTENT_PROJECT_ID}")
        self.assertEqual(resp.status_code, 404)

    # -- Document upload + processing lifecycle --------------------------

    def test_upload_real_pdf_becomes_ready_and_searchable(self):
        project_id = self._create_project("Test Suite Project B")
        pdf_bytes = _build_test_pdf("UNIQUE-TEST-MARKER-ALPHA-9001. This is a real test document.")

        resp = self.client.post(
            f"/projects/{project_id}/documents",
            files={"files": ("marker_alpha.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )
        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        self.assertEqual(len(body["documents"]), 1)
        self.assertEqual(body["rejected"], [])

        document = body["documents"][0]
        self.assertEqual(document["status"], "ready")
        self.assertIsNone(document["processing_error"])

        with get_session_factory()() as session:
            chunks = session.query(DocumentChunk).filter(DocumentChunk.document_id == document["id"]).all()
            self.assertGreater(len(chunks), 0, "no chunks were created for the uploaded document")
            self.assertTrue(all(c.embedding is not None for c in chunks), "a chunk was persisted without an embedding")

    def test_uploaded_document_appears_in_project_document_list(self):
        project_id = self._create_project("Test Suite Project C")
        pdf_bytes = _build_test_pdf("UNIQUE-TEST-MARKER-BETA-9002.")
        self.client.post(
            f"/projects/{project_id}/documents",
            files={"files": ("marker_beta.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )
        resp = self.client.get(f"/projects/{project_id}/documents")
        self.assertEqual(resp.status_code, 200)
        filenames = [d["filename"] for d in resp.json()]
        self.assertIn("marker_beta.pdf", filenames)

    def test_duplicate_upload_creates_two_independent_documents(self):
        project_id = self._create_project("Test Suite Project D")
        pdf_bytes = _build_test_pdf("UNIQUE-TEST-MARKER-GAMMA-9003.")
        for _ in range(2):
            resp = self.client.post(
                f"/projects/{project_id}/documents",
                files={"files": ("marker_gamma.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            )
            self.assertEqual(resp.status_code, 201)

        list_resp = self.client.get(f"/projects/{project_id}/documents")
        matching = [d for d in list_resp.json() if d["filename"] == "marker_gamma.pdf"]
        self.assertEqual(len(matching), 2, "uploading the same file twice should create two independent documents")
        self.assertNotEqual(matching[0]["id"], matching[1]["id"])

    # -- Validation -------------------------------------------------------

    def test_unsupported_file_type_is_rejected_without_creating_a_document(self):
        # Phase 7 (Multi-Format Evidence): PDF and DOCX are both accepted
        # now, so the honest rejection message is format-generic rather
        # than "not a PDF" specifically — this test asserts that updated,
        # still-accurate message.
        project_id = self._create_project("Test Suite Project E")
        resp = self.client.post(
            f"/projects/{project_id}/documents",
            files={"files": ("notes.txt", io.BytesIO(b"just text"), "text/plain")},
        )
        self.assertEqual(resp.status_code, 201)  # the batch endpoint itself succeeds
        body = resp.json()
        self.assertEqual(body["documents"], [])
        self.assertEqual(len(body["rejected"]), 1)
        self.assertIn("not a supported file type", body["rejected"][0]["error"])

    def test_empty_file_upload_is_rejected(self):
        project_id = self._create_project("Test Suite Project F")
        resp = self.client.post(
            f"/projects/{project_id}/documents",
            files={"files": ("empty.pdf", io.BytesIO(b""), "application/pdf")},
        )
        body = resp.json()
        self.assertEqual(body["documents"], [])
        self.assertIn("empty", body["rejected"][0]["error"])

    def test_upload_to_nonexistent_project_returns_404(self):
        pdf_bytes = _build_test_pdf("irrelevant")
        resp = self.client.post(
            f"/projects/{NONEXISTENT_PROJECT_ID}/documents",
            files={"files": ("x.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )
        self.assertEqual(resp.status_code, 404)

    def test_list_documents_for_nonexistent_project_returns_404(self):
        resp = self.client.get(f"/projects/{NONEXISTENT_PROJECT_ID}/documents")
        self.assertEqual(resp.status_code, 404)

    # -- Project isolation (critical) ---------------------------------------

    def test_document_from_one_project_not_retrievable_via_another(self):
        project_a = self._create_project("Test Suite Project G")
        project_b = self._create_project("Test Suite Project H")
        pdf_bytes = _build_test_pdf("UNIQUE-TEST-MARKER-DELTA-9004.")
        upload_resp = self.client.post(
            f"/projects/{project_a}/documents",
            files={"files": ("marker_delta.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )
        document_id = upload_resp.json()["documents"][0]["id"]

        # Metadata endpoint: wrong project -> 404.
        cross_resp = self.client.get(f"/projects/{project_b}/documents/{document_id}")
        self.assertEqual(cross_resp.status_code, 404)

        # File endpoint: wrong project -> 404.
        cross_file_resp = self.client.get(f"/projects/{project_b}/documents/{document_id}/file")
        self.assertEqual(cross_file_resp.status_code, 404)

        # Correct project -> 200 for both.
        own_resp = self.client.get(f"/projects/{project_a}/documents/{document_id}")
        self.assertEqual(own_resp.status_code, 200)
        own_file_resp = self.client.get(f"/projects/{project_a}/documents/{document_id}/file")
        self.assertEqual(own_file_resp.status_code, 200)
        self.assertEqual(own_file_resp.headers["content-type"], "application/pdf")

        # Cross-project document list must never include the other project's document.
        list_b_resp = self.client.get(f"/projects/{project_b}/documents")
        self.assertNotIn(document_id, [d["id"] for d in list_b_resp.json()])

    def test_get_nonexistent_document_returns_404(self):
        project_id = self._create_project("Test Suite Project I")
        resp = self.client.get(f"/projects/{project_id}/documents/{NONEXISTENT_DOCUMENT_ID}")
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
