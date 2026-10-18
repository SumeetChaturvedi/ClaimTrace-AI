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
import struct
import unittest
import zlib
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import delete, select
from sqlalchemy.orm import Session as SqlAlchemySession

from app.db.models import Document, DocumentChunk, Project, ProjectImageAsset
from app.db.session import get_session_factory
from app.ingestion.storage import image_storage_dir
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


def _build_test_image(*, size: tuple[int, int] = (64, 48), color=(10, 120, 200), fmt: str = "JPEG") -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color=color).save(buf, format=fmt)
    return buf.getvalue()


def _build_png_with_forged_dimensions(width: int, height: int, *, real_size: tuple[int, int] = (4, 4)) -> bytes:
    """A real, tiny, genuinely-decodable PNG (default 4x4) whose IHDR
    chunk is rewritten (with a correctly recomputed CRC) to CLAIM the
    given, much larger, width/height. Exercises Pillow's real
    decompression-bomb check -- which fires purely from the declared
    header dimensions inside Image.open(), before any pixel data is
    decoded -- without this test ever allocating an actual huge pixel
    buffer. Builds in milliseconds, unlike constructing a genuinely
    width x height image via Image.new()."""
    buf = io.BytesIO()
    Image.new("RGB", real_size, color=(5, 5, 5)).save(buf, format="PNG")
    data = bytearray(buf.getvalue())
    assert data[12:16] == b"IHDR", "PNG structure assumption (IHDR immediately follows the signature) broke"
    bit_depth, color_type, compression, filter_method, interlace = data[24:29]
    new_ihdr_data = struct.pack(">IIBBBBB", width, height, bit_depth, color_type, compression, filter_method, interlace)
    crc = zlib.crc32(b"IHDR" + new_ihdr_data) & 0xFFFFFFFF
    data[16 : 16 + 13] = new_ihdr_data
    data[29:33] = struct.pack(">I", crc)
    return bytes(data)


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


class DirectImageUploadTests(unittest.TestCase):
    """Phase W2.0 (Shared Image Preservation Foundation): a recognized
    image uploaded directly to a project (the same
    POST /projects/{project_id}/documents endpoint PDF/DOCX already use)
    is preserved as a ProjectImageAsset rather than rejected outright or
    run through ingest_document() -- never claimed as OCR'd/indexed, and
    never confused with a real Document."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.client.__enter__()
        cls._created_project_ids: list[int] = []

    @classmethod
    def tearDownClass(cls):
        with get_session_factory()() as session:
            for project_id in cls._created_project_ids:
                documents = session.query(Document).filter(Document.project_id == project_id).all()
                for document in documents:
                    session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
                session.execute(delete(ProjectImageAsset).where(ProjectImageAsset.project_id == project_id))
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

    def _upload(self, project_id: int, filename: str, content: bytes, content_type: str = "image/jpeg"):
        return self.client.post(
            f"/projects/{project_id}/documents",
            files={"files": (filename, io.BytesIO(content), content_type)},
        )

    def test_valid_image_is_preserved_not_indexed_and_byte_exact_on_retrieval(self):
        project_id = self._create_project("Image Upload Test Valid")
        image_bytes = _build_test_image(color=(5, 6, 7))
        resp = self._upload(project_id, "site.jpg", image_bytes)
        self.assertEqual(resp.status_code, 201, resp.text)
        body = resp.json()
        self.assertEqual(body["documents"], [])
        self.assertEqual(body["rejected"], [])
        self.assertEqual(len(body["images"]), 1)
        image = body["images"][0]
        self.assertEqual(image["status"], "stored_pending_processing")
        self.assertIsNone(image["document_id"])
        self.assertEqual(image["width_px"], 64)
        self.assertEqual(image["height_px"], 48)

        listed = self.client.get(f"/projects/{project_id}/images").json()
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]["id"], image["id"])

        file_resp = self.client.get(f"/projects/{project_id}/images/{image['id']}/file")
        self.assertEqual(file_resp.status_code, 200)
        self.assertEqual(file_resp.content, image_bytes)
        self.assertEqual(file_resp.headers["content-type"], "image/jpeg")

        # Never listed among this project's real Documents.
        docs = self.client.get(f"/projects/{project_id}/documents").json()
        self.assertEqual([d for d in docs if d["filename"] == "site.jpg"], [])

    def test_pdf_upload_in_the_same_batch_is_unaffected_by_image_handling(self):
        """The existing PDF/DOCX path through this exact endpoint must be
        completely unchanged by this phase -- uploaded in the same batch
        as an image, to directly exercise that they don't interfere."""
        project_id = self._create_project("Image Upload Test Mixed Batch")
        pdf_bytes = _build_test_pdf("Marker CLAIMTRACE-W2-MIXED-BATCH-1.")
        image_bytes = _build_test_image()
        resp = self.client.post(
            f"/projects/{project_id}/documents",
            files=[
                ("files", ("notice.pdf", io.BytesIO(pdf_bytes), "application/pdf")),
                ("files", ("photo.jpg", io.BytesIO(image_bytes), "image/jpeg")),
            ],
        )
        self.assertEqual(resp.status_code, 201, resp.text)
        body = resp.json()
        self.assertEqual(len(body["documents"]), 1)
        self.assertEqual(body["documents"][0]["status"], "ready")
        self.assertEqual(body["documents"][0]["filename"], "notice.pdf")
        self.assertEqual(len(body["images"]), 1)
        self.assertEqual(body["images"][0]["filename"], "photo.jpg")

    def test_decompression_bomb_image_is_rejected_without_aborting_the_rest_of_the_batch(self):
        """Pre-commit review fix regression: a declared-oversized image
        must be cleanly rejected, not crash the whole upload request, and
        the other, ordinary files in the same batch must still be
        processed normally.

        Independent-review follow-up: this specifically exercises
        Pillow's DecompressionBombERROR tier (> 2 x Image.MAX_IMAGE_PIXELS,
        i.e. > 178,956,970 pixels in this installed version) -- the actual
        originally-confirmed defect, which raises unconditionally inside
        Image.open() regardless of any warnings filter. An earlier version
        of this test used a 10000x10000 (~100M pixel) image, which only
        reaches Pillow's WARNING tier; that image was already caught by
        this module's own pre-existing, pre-fix MAX_IMAGE_TOTAL_PIXELS
        check even before the decompression-bomb fix existed, so it
        passed regardless of whether the fix was present -- verified by
        reconstructing the pre-fix validate_image() during review and
        confirming that version of this test still passed against it. The
        real, confirmed-dangerous size (20000x20000, 400,000,000 pixels)
        is reproduced here via a forged PNG header (see
        _build_png_with_forged_dimensions) rather than by actually
        allocating a 20000x20000 pixel buffer, so this stays a fast,
        routine test."""
        project_id = self._create_project("Image Upload Test Decompression Bomb")
        bomb_bytes = _build_png_with_forged_dimensions(20_000, 20_000)
        self.assertGreater(20_000 * 20_000, 2 * 89_478_485, "must exceed Pillow's own ERROR tier, not just its warning tier")
        pdf_bytes = _build_test_pdf("Marker CLAIMTRACE-W2-BOMB-BATCH-1.")
        normal_image_bytes = _build_test_image()

        resp = self.client.post(
            f"/projects/{project_id}/documents",
            files=[
                ("files", ("bomb.png", io.BytesIO(bomb_bytes), "image/png")),
                ("files", ("notice.pdf", io.BytesIO(pdf_bytes), "application/pdf")),
                ("files", ("photo.jpg", io.BytesIO(normal_image_bytes), "image/jpeg")),
            ],
        )
        self.assertEqual(
            resp.status_code, 201, f"a decompression-bomb-sized image must never crash the request: {resp.text}"
        )
        body = resp.json()

        bomb_result = next(img for img in body["images"] if img["filename"] == "bomb.png")
        self.assertEqual(bomb_result["status"], "rejected")
        self.assertIsNotNone(bomb_result["processing_error"])
        self.assertIn("decompression bomb", bomb_result["processing_error"].lower())

        # The rest of the batch was still processed normally.
        self.assertEqual(len(body["documents"]), 1)
        self.assertEqual(body["documents"][0]["status"], "ready")
        normal_image_result = next(img for img in body["images"] if img["filename"] == "photo.jpg")
        self.assertEqual(normal_image_result["status"], "stored_pending_processing")

    def test_corrupt_image_with_a_real_signature_is_rejected_with_a_reason(self):
        project_id = self._create_project("Image Upload Test Corrupt")
        fake_jpeg = b"\xff\xd8\xff\xe0" + b"garbage, not a decodable jpeg" * 5
        resp = self._upload(project_id, "broken.jpg", fake_jpeg)
        self.assertEqual(resp.status_code, 201, resp.text)
        body = resp.json()
        self.assertEqual(len(body["images"]), 1)
        self.assertEqual(body["images"][0]["status"], "rejected")
        self.assertIsNotNone(body["images"][0]["processing_error"])

        from app.config import get_settings

        media_dir = image_storage_dir(get_settings().storage_root, project_id)
        self.assertEqual(list(media_dir.iterdir()) if media_dir.exists() else [], [])

    def test_oversized_image_is_rejected_with_a_clear_reason(self):
        from app.ingestion import image_validation as iv

        original_max_bytes = iv.MAX_IMAGE_BYTES
        iv.MAX_IMAGE_BYTES = 100
        try:
            project_id = self._create_project("Image Upload Test Oversized")
            image_bytes = _build_test_image(size=(200, 200))
            self.assertGreater(len(image_bytes), 100)
            resp = self._upload(project_id, "big.jpg", image_bytes)
        finally:
            iv.MAX_IMAGE_BYTES = original_max_bytes

        body = resp.json()
        self.assertEqual(body["images"][0]["status"], "rejected")
        self.assertIn("MB size limit", body["images"][0]["processing_error"])

    def test_reuploading_the_same_image_to_the_same_project_does_not_duplicate_it(self):
        project_id = self._create_project("Image Upload Test Duplicate")
        image_bytes = _build_test_image(color=(9, 9, 9))
        first = self._upload(project_id, "dup.jpg", image_bytes).json()
        second = self._upload(project_id, "dup-again.jpg", image_bytes).json()

        self.assertEqual(first["images"][0]["id"], second["images"][0]["id"])
        listed = self.client.get(f"/projects/{project_id}/images").json()
        self.assertEqual(len(listed), 1, "re-uploading the exact same image bytes must not create a duplicate asset")

    def test_commit_failure_after_writing_the_image_removes_the_orphaned_file(self):
        project_id = self._create_project("Image Upload Test Commit Failure")
        image_bytes = _build_test_image()

        original_commit = SqlAlchemySession.commit

        def failing_commit(self):
            pending_image_rows = [
                obj for obj in self.new
                if isinstance(obj, ProjectImageAsset) and obj.status == "stored_pending_processing"
            ]
            if pending_image_rows:
                raise RuntimeError("injected commit failure (failure-injection regression test)")
            return original_commit(self)

        with patch.object(SqlAlchemySession, "commit", failing_commit):
            resp = self._upload(project_id, "willfail.jpg", image_bytes)
        self.assertEqual(resp.status_code, 201, resp.text)
        self.assertEqual(resp.json()["images"][0]["status"], "failed")

        from app.config import get_settings

        media_dir = image_storage_dir(get_settings().storage_root, project_id)
        leftover_files = list(media_dir.iterdir()) if media_dir.exists() else []
        self.assertEqual(leftover_files, [], "the file written for the image must be removed when its row commit fails")

        with get_session_factory()() as session:
            orphaned_row = session.scalar(select(ProjectImageAsset).where(ProjectImageAsset.project_id == project_id))
            self.assertIsNone(orphaned_row, "a failed commit must not leave a persisted row behind")

    def test_image_from_one_project_not_retrievable_via_another(self):
        project_a = self._create_project("Image Upload Test Isolation A")
        project_b = self._create_project("Image Upload Test Isolation B")
        image_bytes = _build_test_image()
        image_id = self._upload(project_a, "iso.jpg", image_bytes).json()["images"][0]["id"]

        cross_project_resp = self.client.get(f"/projects/{project_b}/images/{image_id}")
        self.assertEqual(cross_project_resp.status_code, 404)
        cross_project_file_resp = self.client.get(f"/projects/{project_b}/images/{image_id}/file")
        self.assertEqual(cross_project_file_resp.status_code, 404)

        own_resp = self.client.get(f"/projects/{project_a}/images/{image_id}")
        self.assertEqual(own_resp.status_code, 200)

        list_b = self.client.get(f"/projects/{project_b}/images").json()
        self.assertEqual(list_b, [])


if __name__ == "__main__":
    unittest.main()
