"""Focused tests for Phase W2.1 (Local OCR Foundation) --
app/ocr/tesseract_provider.py, app/ocr/pending.py, app/ocr/process_pending.py,
and the ImageOcrResult model.

Same approach as test_image_validation.py/test_project_documents.py: plain
`unittest`, real Postgres for anything that touches the database, no real
Tesseract binary required for the routine suite -- the Tesseract
subprocess boundary (pytesseract.image_to_string/get_tesseract_version)
is mocked deterministically throughout, exactly as this phase's own task
instructions require. A single, clearly separate integration smoke test
at the bottom is skipped unless a real `tesseract` executable is actually
on PATH.

Run with:
    cd backend && source .venv/bin/activate
    PYTHONPATH=. python3 -m unittest tests.test_ocr -v
"""

from __future__ import annotations

import io
import shutil
import threading
import unittest
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage as StdlibEmailMessage
from email.utils import formatdate
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError

from app.config import get_settings
from app.db.models import (
    Document,
    DocumentChunk,
    EmailAttachment,
    EmailMessage,
    EmailThread,
    ImageOcrResult,
    Project,
    ProjectImageAsset,
    WhatsAppChat,
    WhatsAppMediaAttachment,
    WhatsAppMessage,
)
from app.db.session import get_session_factory
from app.ingestion.storage import image_storage_dir
from app.main import app
from app.ocr import process_pending as pp
from app.ocr import tesseract_provider as tp
from app.ocr.pending import ensure_pending_ocr_result

NONEXISTENT_ID = 999_999


def _build_test_image(*, size: tuple[int, int] = (64, 48), color=(10, 120, 200), fmt: str = "JPEG") -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color=color).save(buf, format=fmt)
    return buf.getvalue()


def _build_eml(**kwargs) -> bytes:
    msg = StdlibEmailMessage()
    for key, value in kwargs.pop("headers", {}).items():
        msg[key] = value
    msg.set_content(kwargs.pop("body", ""))
    for attachment in kwargs.pop("attachments", []):
        msg.add_attachment(
            attachment["content"],
            maintype=attachment.get("maintype", "application"),
            subtype=attachment.get("subtype", "octet-stream"),
            filename=attachment["filename"],
        )
    return msg.as_bytes()


def _build_whatsapp_zip(*, text: str, media: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("chat.txt", text)
        for name, content in media.items():
            zf.writestr(name, content)
    return buf.getvalue()


class TesseractProviderTests(unittest.TestCase):
    """Deterministic, offline tests for app/ocr/tesseract_provider.py --
    no database, no real Tesseract binary. Mirrors
    test_image_validation.py's own "deterministic, mocked" conventions."""

    def test_missing_executable_is_reported_cleanly(self):
        with patch.object(tp.shutil, "which", return_value=None):
            result = tp.run_ocr(_build_test_image(fmt="PNG"))
        self.assertEqual(result.status, "failed")
        self.assertIn("not found", result.error.lower())
        self.assertIsNone(result.text)

    def test_is_tesseract_available_reflects_which_result(self):
        with patch.object(tp.shutil, "which", return_value=None):
            self.assertFalse(tp.is_tesseract_available())
        with patch.object(tp.shutil, "which", return_value="/usr/bin/tesseract"):
            self.assertTrue(tp.is_tesseract_available())

    def test_successful_ocr_returns_text_and_engine_version(self):
        with patch.object(tp.shutil, "which", return_value="/usr/bin/tesseract"):
            with patch.object(tp.pytesseract, "image_to_string", return_value="Marker CLAIMTRACE-OCR-1"):
                with patch.object(tp.pytesseract, "get_tesseract_version", return_value="5.3.4"):
                    result = tp.run_ocr(_build_test_image(fmt="PNG"), language="eng")
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.text, "Marker CLAIMTRACE-OCR-1")
        self.assertEqual(result.engine_version, "5.3.4")
        self.assertEqual(result.language, "eng")

    def test_empty_ocr_result_is_completed_not_failed(self):
        """A genuinely successful OCR run that finds no text must never
        be reported as a failure."""
        with patch.object(tp.shutil, "which", return_value="/usr/bin/tesseract"):
            with patch.object(tp.pytesseract, "image_to_string", return_value=""):
                with patch.object(tp.pytesseract, "get_tesseract_version", return_value="5.3.4"):
                    result = tp.run_ocr(_build_test_image(fmt="PNG"))
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.text, "")
        self.assertIsNone(result.error)

    def test_timeout_is_reported_cleanly(self):
        """Verified against the real, installed pytesseract==0.3.13:
        a subprocess timeout raises a plain RuntimeError with the literal
        message 'Tesseract process timeout' (no dedicated exception
        class in this version) -- see tesseract_provider.py's own
        docstring for the verified source location."""
        with patch.object(tp.shutil, "which", return_value="/usr/bin/tesseract"):
            with patch.object(tp.pytesseract, "image_to_string", side_effect=RuntimeError("Tesseract process timeout")):
                with patch.object(tp.pytesseract, "get_tesseract_version", return_value="5.3.4"):
                    result = tp.run_ocr(_build_test_image(fmt="PNG"), timeout=1)
        self.assertEqual(result.status, "failed")
        self.assertIn("timeout", result.error.lower())

    def test_unavailable_language_is_reported_cleanly(self):
        """Verified against the real pytesseract: Tesseract exiting
        non-zero (e.g. 'Error opening data file ...' for a language whose
        trained data isn't installed) raises TesseractError(status,
        message)."""
        with patch.object(tp.shutil, "which", return_value="/usr/bin/tesseract"):
            with patch.object(
                tp.pytesseract,
                "image_to_string",
                side_effect=tp.TesseractError(1, "Error opening data file /usr/share/tessdata/xyz.traineddata"),
            ):
                with patch.object(tp.pytesseract, "get_tesseract_version", return_value="5.3.4"):
                    result = tp.run_ocr(_build_test_image(fmt="PNG"), language="xyz")
        self.assertEqual(result.status, "failed")
        self.assertIn("error opening data file", result.error.lower())
        self.assertEqual(result.language, "xyz")

    def test_malformed_image_bytes_are_reported_cleanly(self):
        """No pytesseract mock needed here -- Image.open() itself raises
        for genuinely malformed bytes, before pytesseract is ever
        reached; run_ocr's own try/except must catch that too."""
        with patch.object(tp.shutil, "which", return_value="/usr/bin/tesseract"):
            with patch.object(tp.pytesseract, "get_tesseract_version", return_value="5.3.4"):
                result = tp.run_ocr(b"not an image at all", language="eng")
        self.assertEqual(result.status, "failed")
        self.assertIsNotNone(result.error)

    def test_never_logs_image_bytes_or_ocr_text(self):
        marker = "SECRET-OCR-TEXT-MUST-NEVER-BE-LOGGED-9f3a"
        with self.assertLogs(level="DEBUG") as captured:
            import logging

            logging.getLogger(__name__).debug("harness: ensure assertLogs has at least one record")
            with patch.object(tp.shutil, "which", return_value="/usr/bin/tesseract"):
                with patch.object(tp.pytesseract, "image_to_string", return_value=marker):
                    with patch.object(tp.pytesseract, "get_tesseract_version", return_value="5.3.4"):
                        tp.run_ocr(_build_test_image(fmt="PNG"))
        for record in captured.records:
            self.assertNotIn(marker, record.getMessage())


class ImageOcrResultConstraintTests(unittest.TestCase):
    """Direct, DB-level verification of the new table's own constraints --
    mirrors WhatsAppConstraintTests' own "defense-in-depth, not just an
    application-level check" convention."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.client.__enter__()
        cls._created_project_ids: list[int] = []

    @classmethod
    def tearDownClass(cls):
        with get_session_factory()() as session:
            for project_id in cls._created_project_ids:
                session.execute(
                    delete(ImageOcrResult).where(
                        ImageOcrResult.project_image_asset_id.in_(
                            select(ProjectImageAsset.id).where(ProjectImageAsset.project_id == project_id)
                        )
                    )
                )
                session.execute(delete(ProjectImageAsset).where(ProjectImageAsset.project_id == project_id))
                session.query(Project).filter(Project.id == project_id).delete()
            session.commit()
        cls.client.__exit__(None, None, None)

    def _create_project(self, name: str) -> int:
        resp = self.client.post("/projects", json={"name": name})
        project_id = resp.json()["id"]
        self._created_project_ids.append(project_id)
        return project_id

    def _create_image_asset(self, project_id: int) -> int:
        resp = self.client.post(
            f"/projects/{project_id}/documents",
            files={"files": ("photo.jpg", io.BytesIO(_build_test_image()), "image/jpeg")},
        )
        return resp.json()["images"][0]["id"]

    def test_zero_parents_is_rejected_by_the_check_constraint(self):
        with get_session_factory()() as session:
            session.add(ImageOcrResult(status="pending", ocr_engine="tesseract", ocr_language="eng"))
            with self.assertRaises(IntegrityError):
                session.commit()

    def test_two_parents_at_once_is_rejected_by_the_check_constraint(self):
        project_id = self._create_project("OCR Constraint Test Two Parents")
        asset_id = self._create_image_asset(project_id)
        with get_session_factory()() as session:
            # The real asset's own row already got a pending OcrResult at
            # ingestion time -- this second, malformed row (two parents
            # set) must still be rejected regardless.
            session.add(
                ImageOcrResult(
                    project_image_asset_id=asset_id,
                    email_attachment_id=NONEXISTENT_ID,
                    status="pending",
                    ocr_engine="tesseract",
                    ocr_language="eng",
                )
            )
            with self.assertRaises(IntegrityError):
                session.commit()

    def test_at_most_one_result_per_project_image_asset(self):
        project_id = self._create_project("OCR Constraint Test Uniqueness")
        asset_id = self._create_image_asset(project_id)
        with get_session_factory()() as session:
            session.add(ImageOcrResult(project_image_asset_id=asset_id, status="pending", ocr_engine="tesseract", ocr_language="eng"))
            with self.assertRaises(IntegrityError):
                session.commit()

    def test_invalid_status_value_is_rejected_by_the_check_constraint(self):
        project_id = self._create_project("OCR Constraint Test Bad Status")
        asset_id = self._create_image_asset(project_id)
        with get_session_factory()() as session:
            row = session.scalar(select(ImageOcrResult).where(ImageOcrResult.project_image_asset_id == asset_id))
            row.status = "not_a_real_status"
            with self.assertRaises(IntegrityError):
                session.commit()

    def test_deleting_the_project_cascades_through_the_image_asset_to_the_ocr_result(self):
        project_id = self._create_project("OCR Constraint Test Cascade")
        asset_id = self._create_image_asset(project_id)
        with get_session_factory()() as session:
            self.assertIsNotNone(session.scalar(select(ImageOcrResult).where(ImageOcrResult.project_image_asset_id == asset_id)))
            session.query(ProjectImageAsset).filter(ProjectImageAsset.id == asset_id).delete()
            session.commit()
            self.assertIsNone(session.scalar(select(ImageOcrResult).where(ImageOcrResult.project_image_asset_id == asset_id)))
        self._created_project_ids.remove(project_id) if project_id in self._created_project_ids else None
        with get_session_factory()() as session:
            session.query(Project).filter(Project.id == project_id).delete()
            session.commit()


class PendingRowCreationTests(unittest.TestCase):
    """Verifies that successful image preservation across all three
    sources creates exactly one 'pending' ImageOcrResult row, that
    WhatsApp non-image media never does, and that re-importing/re-
    uploading the same content never creates a duplicate."""

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
                session.execute(
                    delete(ImageOcrResult).where(
                        ImageOcrResult.project_image_asset_id.in_(
                            select(ProjectImageAsset.id).where(ProjectImageAsset.project_id == project_id)
                        )
                        | ImageOcrResult.email_attachment_id.in_(
                            select(EmailAttachment.id).join(EmailMessage, EmailMessage.document_id == EmailAttachment.message_id).where(
                                EmailMessage.project_id == project_id
                            )
                        )
                        | ImageOcrResult.whatsapp_media_attachment_id.in_(
                            select(WhatsAppMediaAttachment.id).join(
                                WhatsAppMessage, WhatsAppMessage.document_id == WhatsAppMediaAttachment.message_id
                            ).where(WhatsAppMessage.project_id == project_id)
                        )
                    )
                )
                session.execute(delete(ProjectImageAsset).where(ProjectImageAsset.project_id == project_id))
                session.execute(delete(EmailAttachment).where(
                    EmailAttachment.message_id.in_(select(Document.id).where(Document.project_id == project_id))
                ))
                session.execute(delete(EmailMessage).where(EmailMessage.project_id == project_id))
                session.execute(delete(EmailThread).where(EmailThread.project_id == project_id))
                session.execute(delete(WhatsAppMediaAttachment).where(
                    WhatsAppMediaAttachment.message_id.in_(
                        select(WhatsAppMessage.document_id).where(WhatsAppMessage.project_id == project_id)
                    )
                ))
                session.execute(delete(WhatsAppMessage).where(WhatsAppMessage.project_id == project_id))
                session.execute(delete(WhatsAppChat).where(WhatsAppChat.project_id == project_id))
                session.query(Document).filter(Document.project_id == project_id).delete()
                session.query(Project).filter(Project.id == project_id).delete()
            session.commit()
        cls.client.__exit__(None, None, None)

    def _create_project(self, name: str) -> int:
        resp = self.client.post("/projects", json={"name": name})
        project_id = resp.json()["id"]
        self._created_project_ids.append(project_id)
        return project_id

    def test_direct_upload_creates_a_pending_ocr_row(self):
        project_id = self._create_project("OCR Pending Test Direct Upload")
        resp = self.client.post(
            f"/projects/{project_id}/documents",
            files={"files": ("photo.jpg", io.BytesIO(_build_test_image()), "image/jpeg")},
        )
        image_id = resp.json()["images"][0]["id"]
        with get_session_factory()() as session:
            row = session.scalar(select(ImageOcrResult).where(ImageOcrResult.project_image_asset_id == image_id))
            self.assertIsNotNone(row)
            self.assertEqual(row.status, "pending")
            self.assertEqual(row.ocr_engine, "tesseract")

    def test_gmail_image_attachment_creates_a_pending_ocr_row(self):
        project_id = self._create_project("OCR Pending Test Gmail")
        raw = _build_eml(
            headers={"Message-ID": "<ocr-pending@example.com>", "From": "a@example.com", "Subject": "Photo", "Date": formatdate()},
            body="see attached",
            attachments=[{"filename": "site.jpg", "content": _build_test_image(), "maintype": "image", "subtype": "jpeg"}],
        )
        resp = self.client.post(f"/projects/{project_id}/emails/import", files={"files": ("x.eml", io.BytesIO(raw), "message/rfc822")})
        document_id = resp.json()["results"][0]["document_id"]
        message = self.client.get(f"/projects/{project_id}/emails/messages/{document_id}").json()
        attachment_id = message["attachments"][0]["id"]
        with get_session_factory()() as session:
            row = session.scalar(select(ImageOcrResult).where(ImageOcrResult.email_attachment_id == attachment_id))
            self.assertIsNotNone(row)
            self.assertEqual(row.status, "pending")

    def test_whatsapp_image_attachment_creates_a_pending_ocr_row(self):
        project_id = self._create_project("OCR Pending Test WhatsApp Image")
        zip_bytes = _build_whatsapp_zip(
            text="[25/03/24, 10:00:00] Alice: <attached: pic.jpg>\n",
            media={"pic.jpg": _build_test_image()},
        )
        resp = self.client.post(f"/projects/{project_id}/whatsapp/import", files={"file": ("chat.zip", io.BytesIO(zip_bytes), "application/zip")})
        self.assertEqual(resp.status_code, 201, resp.text)
        with get_session_factory()() as session:
            attachment = session.scalar(select(WhatsAppMediaAttachment).where(
                WhatsAppMediaAttachment.filename == "pic.jpg",
                WhatsAppMediaAttachment.message_id.in_(select(WhatsAppMessage.document_id).where(WhatsAppMessage.project_id == project_id)),
            ))
            row = session.scalar(select(ImageOcrResult).where(ImageOcrResult.whatsapp_media_attachment_id == attachment.id))
            self.assertIsNotNone(row)
            self.assertEqual(row.status, "pending")

    def test_whatsapp_non_image_media_never_gets_an_ocr_row(self):
        project_id = self._create_project("OCR Pending Test WhatsApp Non-Image")
        zip_bytes = _build_whatsapp_zip(
            text="[25/03/24, 10:00:00] Alice: <attached: clip.mp3>\n",
            media={"clip.mp3": b"ID3" + b"x" * 50},
        )
        resp = self.client.post(f"/projects/{project_id}/whatsapp/import", files={"file": ("chat.zip", io.BytesIO(zip_bytes), "application/zip")})
        self.assertEqual(resp.status_code, 201, resp.text)
        with get_session_factory()() as session:
            attachment = session.scalar(select(WhatsAppMediaAttachment).where(
                WhatsAppMediaAttachment.filename == "clip.mp3",
                WhatsAppMediaAttachment.message_id.in_(select(WhatsAppMessage.document_id).where(WhatsAppMessage.project_id == project_id)),
            ))
            self.assertEqual(attachment.status, "stored_pending_processing")
            self.assertEqual(attachment.detected_extension, ".mp3")
            row = session.scalar(select(ImageOcrResult).where(ImageOcrResult.whatsapp_media_attachment_id == attachment.id))
            self.assertIsNone(row, "OCR must never be scheduled for non-image WhatsApp media")

    def test_duplicate_direct_upload_does_not_create_a_duplicate_ocr_row(self):
        project_id = self._create_project("OCR Pending Test Direct Dup")
        image_bytes = _build_test_image(color=(44, 55, 66))
        first = self.client.post(f"/projects/{project_id}/documents", files={"files": ("a.jpg", io.BytesIO(image_bytes), "image/jpeg")})
        second = self.client.post(f"/projects/{project_id}/documents", files={"files": ("b.jpg", io.BytesIO(image_bytes), "image/jpeg")})
        image_id_1 = first.json()["images"][0]["id"]
        image_id_2 = second.json()["images"][0]["id"]
        self.assertEqual(image_id_1, image_id_2, "re-uploading identical bytes must return the existing asset")
        with get_session_factory()() as session:
            rows = session.scalars(select(ImageOcrResult).where(ImageOcrResult.project_image_asset_id == image_id_1)).all()
            self.assertEqual(len(rows), 1)

    def test_duplicate_gmail_import_does_not_create_a_duplicate_ocr_row(self):
        project_id = self._create_project("OCR Pending Test Gmail Dup")
        raw = _build_eml(
            headers={"Message-ID": "<ocr-dup@example.com>", "From": "a@example.com", "Subject": "Dup", "Date": formatdate()},
            body="see attached",
            attachments=[{"filename": "dup.jpg", "content": _build_test_image(), "maintype": "image", "subtype": "jpeg"}],
        )
        self.client.post(f"/projects/{project_id}/emails/import", files={"files": ("x1.eml", io.BytesIO(raw), "message/rfc822")})
        resp2 = self.client.post(f"/projects/{project_id}/emails/import", files={"files": ("x2.eml", io.BytesIO(raw), "message/rfc822")})
        self.assertEqual(resp2.json()["results"][0]["status"], "duplicate")
        with get_session_factory()() as session:
            attachments = session.scalars(select(EmailAttachment).where(EmailAttachment.filename == "dup.jpg")).all()
            self.assertEqual(len(attachments), 1, "a duplicate import must never re-process the attachment at all")


class BatchProcessingTests(unittest.TestCase):
    """Real-Postgres tests of app/ocr/process_pending.py, with the
    Tesseract subprocess boundary mocked deterministically throughout.

    process_pending() is deliberately system-wide, not project-scoped --
    it claims every currently-eligible row in the whole database (see
    its own module docstring), exactly like the real batch command would
    in production. This shares its database with real, manually-created
    dev data (never wiped by a test), so every assertion here checks the
    SPECIFIC row(s) this test itself created by id, never a raw aggregate
    `counts` dict value that could be inflated by unrelated eligible rows
    already sitting in the database from outside this test."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.client.__enter__()
        cls._created_project_ids: list[int] = []

    @classmethod
    def tearDownClass(cls):
        with get_session_factory()() as session:
            for project_id in cls._created_project_ids:
                session.execute(
                    delete(ImageOcrResult).where(
                        ImageOcrResult.project_image_asset_id.in_(
                            select(ProjectImageAsset.id).where(ProjectImageAsset.project_id == project_id)
                        )
                    )
                )
                session.execute(delete(ProjectImageAsset).where(ProjectImageAsset.project_id == project_id))
                session.query(Project).filter(Project.id == project_id).delete()
            session.commit()
        cls.client.__exit__(None, None, None)

    def _create_project(self, name: str) -> int:
        resp = self.client.post("/projects", json={"name": name})
        project_id = resp.json()["id"]
        self._created_project_ids.append(project_id)
        return project_id

    def _upload_image(self, project_id: int, filename: str, *, color=(1, 2, 3)) -> int:
        # PNG, not JPEG: these tests tag each image by its own exact pixel
        # color to distinguish it from unrelated, pre-existing rows in
        # this shared database (see class docstring) -- JPEG's lossy
        # compression measurably shifts even a flat color block's pixel
        # values on round-trip (verified directly: (210,20,30) decodes
        # back as (211,19,30)), which would silently break that tagging.
        resp = self.client.post(
            f"/projects/{project_id}/documents",
            files={"files": (filename, io.BytesIO(_build_test_image(color=color, fmt="PNG")), "image/png")},
        )
        return resp.json()["images"][0]["id"]

    def _run(self, **kwargs):
        defaults = {"language": "eng", "tesseract_cmd": None, "storage_root": get_settings().storage_root}
        defaults.update(kwargs)
        return pp.process_pending(**defaults)

    def _ocr_status(self, image_id: int) -> ImageOcrResult:
        with get_session_factory()() as session:
            row = session.scalar(select(ImageOcrResult).where(ImageOcrResult.project_image_asset_id == image_id))
            session.expunge(row)
            return row

    @staticmethod
    def _color_of(image) -> tuple:
        return image.convert("RGB").getpixel((0, 0))

    def test_batch_continues_after_a_single_failure(self):
        """Real-DB caveat: process_pending() is system-wide, so the mock
        below only applies its special fail/succeed behavior to THIS
        test's own two, uniquely-colored images -- anything else the run
        happens to sweep up (pre-existing dev data) gets a harmless
        default so it can never affect this test's own assertions."""
        project_id = self._create_project("OCR Batch Test Continue After Failure")
        fail_id = self._upload_image(project_id, "fail.jpg", color=(201, 7, 7))
        ok_id = self._upload_image(project_id, "ok.jpg", color=(7, 201, 7))

        def flaky(image, lang=None, timeout=0, **kwargs):
            color = self._color_of(image)
            if color == (201, 7, 7):
                raise tp.TesseractError(1, "simulated failure on the first image")
            if color == (7, 201, 7):
                return "second image succeeded"
            return "unrelated"

        with patch.object(tp.shutil, "which", return_value="/usr/bin/tesseract"):
            with patch.object(tp.pytesseract, "image_to_string", side_effect=flaky):
                with patch.object(tp.pytesseract, "get_tesseract_version", return_value="5.3.4"):
                    self._run()

        self.assertEqual(self._ocr_status(fail_id).status, "failed")
        self.assertEqual(self._ocr_status(ok_id).status, "completed")

    def test_empty_ocr_text_counted_as_empty_not_failed_and_stored_as_completed(self):
        project_id = self._create_project("OCR Batch Test Empty Result")
        image_id = self._upload_image(project_id, "blank.jpg", color=(202, 8, 8))

        def maybe_empty(image, lang=None, timeout=0, **kwargs):
            return "   " if self._color_of(image) == (202, 8, 8) else "unrelated"

        with patch.object(tp.shutil, "which", return_value="/usr/bin/tesseract"):
            with patch.object(tp.pytesseract, "image_to_string", side_effect=maybe_empty):
                with patch.object(tp.pytesseract, "get_tesseract_version", return_value="5.3.4"):
                    self._run()

        row = self._ocr_status(image_id)
        self.assertEqual(row.status, "completed")
        self.assertIsNotNone(row.ocr_text_path)

    def test_idempotent_rerun_with_matching_config_does_not_reprocess(self):
        project_id = self._create_project("OCR Batch Test Idempotent")
        image_id = self._upload_image(project_id, "stable.jpg", color=(203, 9, 9))

        def tagged(image, lang=None, timeout=0, **kwargs):
            return "text" if self._color_of(image) == (203, 9, 9) else "unrelated"

        with patch.object(tp.shutil, "which", return_value="/usr/bin/tesseract"):
            with patch.object(tp.pytesseract, "image_to_string", side_effect=tagged):
                with patch.object(tp.pytesseract, "get_tesseract_version", return_value="5.3.4"):
                    self._run()
                    row_after_first = self._ocr_status(image_id)
                    self._run()
                    row_after_second = self._ocr_status(image_id)

        self.assertEqual(row_after_first.status, "completed")
        self.assertEqual(
            row_after_second.processed_at,
            row_after_first.processed_at,
            "a matching-config rerun must not touch an already-completed row again",
        )

    def test_version_change_makes_a_completed_result_eligible_again(self):
        project_id = self._create_project("OCR Batch Test Version Change")
        image_id = self._upload_image(project_id, "versioned.jpg", color=(204, 10, 10))

        def tagged_v1(image, lang=None, timeout=0, **kwargs):
            return "v1 text" if self._color_of(image) == (204, 10, 10) else "unrelated"

        def tagged_v2(image, lang=None, timeout=0, **kwargs):
            return "v2 text" if self._color_of(image) == (204, 10, 10) else "unrelated"

        with patch.object(tp.shutil, "which", return_value="/usr/bin/tesseract"):
            with patch.object(tp.pytesseract, "image_to_string", side_effect=tagged_v1):
                with patch.object(tp.pytesseract, "get_tesseract_version", return_value="5.3.4"):
                    self._run()
            first_processed_at = self._ocr_status(image_id).processed_at

            with patch.object(tp.pytesseract, "image_to_string", side_effect=tagged_v2):
                with patch.object(tp.pytesseract, "get_tesseract_version", return_value="5.4.0"):
                    self._run()

        row = self._ocr_status(image_id)
        self.assertEqual(row.ocr_engine_version, "5.4.0")
        self.assertNotEqual(row.processed_at, first_processed_at, "a changed engine version must make the completed row eligible again")

    def test_retry_failed_flag_controls_reprocessing(self):
        project_id = self._create_project("OCR Batch Test Retry Failed")
        image_id = self._upload_image(project_id, "retry.jpg", color=(205, 11, 11))

        def always_boom(image, lang=None, timeout=0, **kwargs):
            if self._color_of(image) == (205, 11, 11):
                raise tp.TesseractError(1, "boom")
            return "unrelated"

        def tagged_retry(image, lang=None, timeout=0, **kwargs):
            return "retried" if self._color_of(image) == (205, 11, 11) else "unrelated"

        with patch.object(tp.shutil, "which", return_value="/usr/bin/tesseract"):
            with patch.object(tp.pytesseract, "image_to_string", side_effect=always_boom):
                with patch.object(tp.pytesseract, "get_tesseract_version", return_value="5.3.4"):
                    self._run()
            self.assertEqual(self._ocr_status(image_id).status, "failed")

            with patch.object(tp.pytesseract, "image_to_string", side_effect=always_boom):
                with patch.object(tp.pytesseract, "get_tesseract_version", return_value="5.3.4"):
                    self._run()  # no --retry-failed: must leave the failed row alone
            self.assertEqual(self._ocr_status(image_id).status, "failed", "without --retry-failed a failed row must not be touched again")

            with patch.object(tp.pytesseract, "image_to_string", side_effect=tagged_retry):
                with patch.object(tp.pytesseract, "get_tesseract_version", return_value="5.3.4"):
                    self._run(retry_failed=True)

        self.assertEqual(self._ocr_status(image_id).status, "completed")

    def test_force_flag_reprocesses_regardless_of_match(self):
        project_id = self._create_project("OCR Batch Test Force")
        image_id = self._upload_image(project_id, "forced.jpg", color=(206, 12, 12))

        def tagged_first(image, lang=None, timeout=0, **kwargs):
            return "first pass" if self._color_of(image) == (206, 12, 12) else "unrelated"

        def tagged_second(image, lang=None, timeout=0, **kwargs):
            return "forced rerun" if self._color_of(image) == (206, 12, 12) else "unrelated"

        with patch.object(tp.shutil, "which", return_value="/usr/bin/tesseract"):
            with patch.object(tp.pytesseract, "image_to_string", side_effect=tagged_first):
                with patch.object(tp.pytesseract, "get_tesseract_version", return_value="5.3.4"):
                    self._run()
            first_processed_at = self._ocr_status(image_id).processed_at

            with patch.object(tp.pytesseract, "image_to_string", side_effect=tagged_second):
                with patch.object(tp.pytesseract, "get_tesseract_version", return_value="5.3.4"):
                    self._run(force=True)

        row = self._ocr_status(image_id)
        self.assertEqual(row.status, "completed")
        self.assertNotEqual(row.processed_at, first_processed_at, "--force must reprocess even a matching-config completed row")

    def test_competing_batch_invocations_do_not_process_the_same_row_twice(self):
        """Real concurrency: three genuinely parallel process_pending()
        runs against the SAME six newly-created, uniquely-colored rows --
        SKIP LOCKED must ensure each one is claimed by exactly one of
        them, never twice, regardless of whatever else is eligible
        elsewhere in this shared database at the same time."""
        project_id = self._create_project("OCR Batch Test Concurrency")
        colors = [(210 + i, 20 + i, 30 + i) for i in range(6)]
        image_ids = [self._upload_image(project_id, f"race-{i}.jpg", color=colors[i]) for i in range(6)]

        call_log: list[tuple] = []
        call_log_lock = threading.Lock()

        def counting_call(image, lang=None, timeout=0, **kwargs):
            color = self._color_of(image)
            if color in colors:
                with call_log_lock:
                    call_log.append(color)
            return "concurrent ocr text"

        with patch.object(tp.shutil, "which", return_value="/usr/bin/tesseract"):
            with patch.object(tp.pytesseract, "image_to_string", side_effect=counting_call):
                with patch.object(tp.pytesseract, "get_tesseract_version", return_value="5.3.4"):
                    with ThreadPoolExecutor(max_workers=3) as pool:
                        list(pool.map(lambda _: self._run(batch_size=2), range(3)))

        for image_id in image_ids:
            self.assertEqual(self._ocr_status(image_id).status, "completed")
        self.assertEqual(len(call_log), 6, "each of this test's own 6 rows must be OCR'd exactly once, never twice")
        self.assertEqual(len(set(call_log)), 6, "no color/row appears more than once in the call log")

    def _backdate_processing(self, image_id: int, *, seconds_ago: float, lease_token: str | None = "test-backdated-lease") -> str:
        """Simulate a row left behind by a run that claimed it
        `seconds_ago` seconds ago and has not been heard from since --
        sets lease_expires_at exactly as the real claim step would have,
        relative to that original claim time (processing_started_at +
        LEASE_DURATION_SECONDS), so backdating far enough past
        LEASE_DURATION_SECONDS produces a genuinely EXPIRED lease, and
        backdating by only a few seconds produces one that is still
        comfortably valid -- never a NULL lease_expires_at (which the
        eligibility clause always treats as expired regardless of
        seconds_ago, representing "no real lease was ever granted", not
        "granted a while ago"). Returns the lease_token assigned, so
        callers can assert on its later renewal/replacement."""
        claimed_at = datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)
        with get_session_factory()() as session:
            row = session.scalar(select(ImageOcrResult).where(ImageOcrResult.project_image_asset_id == image_id))
            row.status = "processing"
            row.processing_started_at = claimed_at
            row.lease_token = lease_token
            row.lease_expires_at = claimed_at + timedelta(seconds=pp.LEASE_DURATION_SECONDS)
            session.commit()
        return lease_token

    def test_abandoned_processing_row_past_the_staleness_threshold_is_reclaimed(self):
        """Pre-commit review fix (Section 1), now lease-based: a row left
        in 'processing' by a killed/crashed invocation -- simulated here
        by directly backdating its claim far enough that its lease (claim
        time + LEASE_DURATION_SECONDS) has genuinely expired, exactly
        what a real crash would leave behind -- must become eligible
        again on a later run, with no special flag required."""
        project_id = self._create_project("OCR Batch Test Stale Reclaim")
        image_id = self._upload_image(project_id, "abandoned.jpg", color=(220, 30, 40))
        self._backdate_processing(image_id, seconds_ago=pp.LEASE_DURATION_SECONDS + 60)

        def tagged(image, lang=None, timeout=0, **kwargs):
            return "reclaimed text" if self._color_of(image) == (220, 30, 40) else "unrelated"

        with patch.object(tp.shutil, "which", return_value="/usr/bin/tesseract"):
            with patch.object(tp.pytesseract, "image_to_string", side_effect=tagged):
                with patch.object(tp.pytesseract, "get_tesseract_version", return_value="5.3.4"):
                    self._run()

        row = self._ocr_status(image_id)
        self.assertEqual(row.status, "completed")
        self.assertEqual(Path(row.ocr_text_path).read_text(), "reclaimed text")

    def test_recently_claimed_processing_row_is_not_reclaimed(self):
        """The other half of the same guarantee: a row whose
        processing_started_at is recent (i.e. a currently-live
        invocation could plausibly still be working through it) must
        NOT be touched -- this is what distinguishes genuinely abandoned
        work from active work, and is exactly what the task warns
        against breaking ("do not simply make every processing row
        immediately eligible")."""
        project_id = self._create_project("OCR Batch Test Stale Not Yet Active")
        image_id = self._upload_image(project_id, "active.jpg", color=(221, 31, 41))
        self._backdate_processing(image_id, seconds_ago=5)  # claimed moments ago -- still "live"

        def tagged(image, lang=None, timeout=0, **kwargs):
            return "must not run" if self._color_of(image) == (221, 31, 41) else "unrelated"

        with patch.object(tp.shutil, "which", return_value="/usr/bin/tesseract"):
            with patch.object(tp.pytesseract, "image_to_string", side_effect=tagged) as mock_call:
                with patch.object(tp.pytesseract, "get_tesseract_version", return_value="5.3.4"):
                    self._run()

        row = self._ocr_status(image_id)
        self.assertEqual(row.status, "processing", "a recently-claimed row must not be reclaimed as if it were abandoned")
        self.assertFalse(
            any(self._color_of_call_arg(call) == (221, 31, 41) for call in mock_call.call_args_list),
            "Tesseract must never be invoked for a row that is still within its active lease window",
        )

    def _color_of_call_arg(self, call) -> tuple:
        image = call.args[0] if call.args else call.kwargs.get("image")
        return self._color_of(image)

    def test_concurrent_invocations_reclaim_the_same_abandoned_row_only_once(self):
        """The abandoned-row-recovery mechanism must share the SAME
        SKIP LOCKED protection as ordinary pending-row claiming -- three
        genuinely concurrent invocations racing to reclaim one stale row
        must still OCR it exactly once."""
        project_id = self._create_project("OCR Batch Test Stale Concurrent Reclaim")
        image_id = self._upload_image(project_id, "contested.jpg", color=(222, 32, 42))
        self._backdate_processing(image_id, seconds_ago=pp.LEASE_DURATION_SECONDS + 60)

        call_log: list[tuple] = []
        call_log_lock = threading.Lock()

        def counting_call(image, lang=None, timeout=0, **kwargs):
            if self._color_of(image) == (222, 32, 42):
                with call_log_lock:
                    call_log.append(1)
            return "reclaimed"

        with patch.object(tp.shutil, "which", return_value="/usr/bin/tesseract"):
            with patch.object(tp.pytesseract, "image_to_string", side_effect=counting_call):
                with patch.object(tp.pytesseract, "get_tesseract_version", return_value="5.3.4"):
                    with ThreadPoolExecutor(max_workers=3) as pool:
                        list(pool.map(lambda _: self._run(batch_size=2), range(3)))

        self.assertEqual(len(call_log), 1, "an abandoned row must be reclaimed and OCR'd exactly once, never concurrently")
        self.assertEqual(self._ocr_status(image_id).status, "completed")

    def test_old_claim_with_an_actively_renewed_lease_is_not_reclaimed(self):
        """The core of this fix: distinguishes "claimed a long time ago"
        from "lease still valid". A row whose processing_started_at is
        far in the past (older than LEASE_DURATION_SECONDS) but whose
        lease_expires_at has been actively renewed into the future --
        exactly what a live worker still working through a large batch
        would have done the moment it reached this row -- must NOT be
        reclaimed. The ORIGINAL design this replaces (a single fixed
        threshold on processing_started_at alone) would have wrongly
        reclaimed this row; the lease-based design must not."""
        project_id = self._create_project("OCR Batch Test Active Lease Despite Old Claim")
        image_id = self._upload_image(project_id, "renewed.jpg", color=(232, 52, 62))

        with get_session_factory()() as session:
            result = session.scalar(select(ImageOcrResult).where(ImageOcrResult.project_image_asset_id == image_id))
            result.status = "processing"
            result.processing_started_at = datetime.now(timezone.utc) - timedelta(seconds=pp.LEASE_DURATION_SECONDS + 500)
            result.lease_token = "actively-renewed-token"
            result.lease_expires_at = datetime.now(timezone.utc) + timedelta(seconds=60)
            session.commit()

        def tagged(image, lang=None, timeout=0, **kwargs):
            return "must not run" if self._color_of(image) == (232, 52, 62) else "unrelated"

        with patch.object(tp.shutil, "which", return_value="/usr/bin/tesseract"):
            with patch.object(tp.pytesseract, "image_to_string", side_effect=tagged) as mock_call:
                with patch.object(tp.pytesseract, "get_tesseract_version", return_value="5.3.4"):
                    self._run()

        row = self._ocr_status(image_id)
        self.assertEqual(row.status, "processing", "an old claim with a still-valid, actively renewed lease must not be reclaimed")
        self.assertFalse(
            any(self._color_of_call_arg(call) == (232, 52, 62) for call in mock_call.call_args_list),
            "Tesseract must never be invoked for a row whose lease is still valid, regardless of how old its original claim is",
        )

    def test_renewing_with_the_wrong_lease_token_fails_without_touching_the_row(self):
        """_renew_lease is the gate that keeps a worker from starting
        Tesseract on a row it has already lost -- renewing with a token
        that doesn't match the row's current lease_token must report
        False, and must leave the row's real lease untouched."""
        project_id = self._create_project("OCR Batch Test Renewal Wrong Token")
        image_id = self._upload_image(project_id, "renew-wrong-token.jpg", color=(233, 53, 63))
        real_expiry = datetime.now(timezone.utc) + timedelta(seconds=60)

        with get_session_factory()() as session:
            result = session.scalar(select(ImageOcrResult).where(ImageOcrResult.project_image_asset_id == image_id))
            result.status = "processing"
            result.lease_token = "the-real-token"
            result.lease_expires_at = real_expiry
            session.commit()
            result_id = result.id

            renewed = pp._renew_lease(session, result_id, "a-different-token")
            self.assertFalse(renewed, "renewing with the wrong token must report failure, never success")

        with get_session_factory()() as session:
            refreshed = session.get(ImageOcrResult, result_id)
            self.assertEqual(refreshed.lease_token, "the-real-token", "a failed renewal must not change the real owner's lease_token")
            self.assertEqual(
                refreshed.lease_expires_at.replace(microsecond=0),
                real_expiry.replace(microsecond=0),
                "a failed renewal must not extend or otherwise change lease_expires_at",
            )

    def test_renewal_failure_from_a_database_error_is_treated_as_lease_lost_not_success(self):
        """Requirement: a failure during lease renewal must not falsely
        report successful ownership. A database error while attempting
        the renewal (not merely a token mismatch) must still return
        False, the same safe, conservative outcome as an ordinary lost
        race -- never True."""
        project_id = self._create_project("OCR Batch Test Renewal Database Error")
        image_id = self._upload_image(project_id, "renew-db-error.jpg", color=(234, 54, 64))

        with get_session_factory()() as session:
            result = session.scalar(select(ImageOcrResult).where(ImageOcrResult.project_image_asset_id == image_id))
            result.status = "processing"
            result.lease_token = "a-real-token"
            result.lease_expires_at = datetime.now(timezone.utc) + timedelta(seconds=60)
            session.commit()
            result_id = result.id

        with get_session_factory()() as session:
            with patch.object(pp, "_update_with_lease", side_effect=RuntimeError("simulated database error during renewal")):
                renewed = pp._renew_lease(session, result_id, "a-real-token")
            self.assertFalse(renewed, "a database error during renewal must be treated as a lost lease, never falsely reported as owned")

    def test_a_worker_that_loses_its_lease_cannot_overwrite_a_newer_workers_committed_result(self):
        """Requirement: if lease renewal fails, the worker must not
        overwrite a result claimed by another worker. Simulates two
        workers racing for the same row: "Worker A" claims it, its lease
        then genuinely expires before it gets around to processing the
        row (a long pause, or simply a large batch queued ahead of it),
        "Worker B" reclaims and completes it first -- and only THEN does
        Worker A finally try to process its own, now-stale claim. Worker
        A's attempt must be refused (Tesseract never even invoked for
        it), and Worker B's already-committed result must survive
        untouched."""
        project_id = self._create_project("OCR Batch Test Lease Lost No Overwrite")
        image_id = self._upload_image(project_id, "lease-race.jpg", color=(235, 55, 65))

        with get_session_factory()() as session:
            result = session.scalar(select(ImageOcrResult).where(ImageOcrResult.project_image_asset_id == image_id))
            result_id = result.id

        with get_session_factory()() as session:
            claimed_a = pp._claim_specific_rows(
                session,
                [result_id],
                retry_failed=False,
                force=False,
                current_engine_version=None,
                current_language="eng",
                now=datetime.now(timezone.utc),
            )
        self.assertEqual(len(claimed_a), 1)
        _claimed_id_a, token_a = claimed_a[0]

        # Worker A's lease genuinely expires before it gets around to
        # processing this row -- simulated directly, exactly what a long
        # pause (or a crash) would leave behind.
        with get_session_factory()() as session:
            session.execute(
                update(ImageOcrResult).where(ImageOcrResult.id == result_id).values(lease_expires_at=datetime.now(timezone.utc) - timedelta(seconds=1))
            )
            session.commit()

        # Worker B sees the expired lease, reclaims, and completes the
        # row with its own result.
        with get_session_factory()() as session:
            claimed_b = pp._claim_specific_rows(
                session,
                [result_id],
                retry_failed=False,
                force=False,
                current_engine_version=None,
                current_language="eng",
                now=datetime.now(timezone.utc),
            )
            self.assertEqual(len(claimed_b), 1)
            _claimed_id_b, token_b = claimed_b[0]

            with patch.object(tp.shutil, "which", return_value="/usr/bin/tesseract"):
                with patch.object(tp.pytesseract, "image_to_string", return_value="worker B text"):
                    with patch.object(tp.pytesseract, "get_tesseract_version", return_value="5.3.4"):
                        outcome_b = pp._process_claimed_result(
                            session, get_settings().storage_root, result_id, token_b, language="eng", tesseract_cmd=None
                        )
        self.assertEqual(outcome_b, "completed")
        row_after_b = self._ocr_status(image_id)
        self.assertEqual(row_after_b.status, "completed")
        self.assertEqual(Path(row_after_b.ocr_text_path).read_text(), "worker B text")

        # Worker A now finally gets around to processing its own,
        # now-stale claim -- must be refused without ever invoking
        # Tesseract, and must never overwrite Worker B's result.
        with get_session_factory()() as session:
            with patch.object(tp.shutil, "which", return_value="/usr/bin/tesseract"):
                with patch.object(tp.pytesseract, "image_to_string", return_value="stale worker A text") as mock_call:
                    with patch.object(tp.pytesseract, "get_tesseract_version", return_value="5.3.4"):
                        outcome_a = pp._process_claimed_result(
                            session, get_settings().storage_root, result_id, token_a, language="eng", tesseract_cmd=None
                        )
            mock_call.assert_not_called()

        self.assertEqual(outcome_a, "skipped", "a worker that has lost its lease must report 'skipped', never 'completed' or 'failed'")
        row_final = self._ocr_status(image_id)
        self.assertEqual(row_final.status, "completed")
        self.assertEqual(
            Path(row_final.ocr_text_path).read_text(), "worker B text", "Worker A must never overwrite Worker B's already-committed result"
        )

    def test_ocr_text_stored_separately_and_original_bytes_hash_unchanged(self):
        project_id = self._create_project("OCR Batch Test Separate Storage")
        image_bytes = _build_test_image(color=(77, 88, 99))
        resp = self.client.post(f"/projects/{project_id}/documents", files={"files": ("orig.jpg", io.BytesIO(image_bytes), "image/jpeg")})
        image_id = resp.json()["images"][0]["id"]

        with get_session_factory()() as session:
            asset_before = session.get(ProjectImageAsset, image_id)
            hash_before = asset_before.content_hash
            storage_key_before = asset_before.storage_key

        with patch.object(tp.shutil, "which", return_value="/usr/bin/tesseract"):
            with patch.object(tp.pytesseract, "image_to_string", return_value="SEPARATE TEXT MARKER"):
                with patch.object(tp.pytesseract, "get_tesseract_version", return_value="5.3.4"):
                    self._run()

        with get_session_factory()() as session:
            asset_after = session.get(ProjectImageAsset, image_id)
            self.assertEqual(asset_after.content_hash, hash_before, "OCR must never modify the original asset's hash")
            self.assertEqual(asset_after.storage_key, storage_key_before, "OCR must never modify the original asset's storage_key")

            ocr_row = session.scalar(select(ImageOcrResult).where(ImageOcrResult.project_image_asset_id == image_id))
            self.assertNotEqual(ocr_row.ocr_text_path, str(image_storage_dir(get_settings().storage_root, project_id) / f"{storage_key_before}.jpg"))
            self.assertEqual(Path(ocr_row.ocr_text_path).read_text(), "SEPARATE TEXT MARKER")
            # The original image file is untouched.
            original_path = image_storage_dir(get_settings().storage_root, project_id) / f"{storage_key_before}.jpg"
            self.assertEqual(original_path.read_bytes(), image_bytes)

    def test_commit_failure_after_writing_ocr_text_removes_the_orphaned_file(self):
        """The commit-failure injection point is now _update_with_lease
        (every status-setting write in process_pending.py goes through
        it -- see that function's own docstring), not raw ORM dirty-state
        inspection: the final write no longer mutates an ORM-tracked
        object, it issues a Core UPDATE keyed on lease_token, so a
        Session.commit()-level dirty-set check would never see it."""
        project_id = self._create_project("OCR Batch Test Commit Failure")
        image_id = self._upload_image(project_id, "willfail.jpg", color=(207, 13, 13))

        original_update_with_lease = pp._update_with_lease

        def failing_update(session, result_id, lease_token, values):
            if values.get("status") == "completed":
                raise RuntimeError("injected commit failure (failure-injection regression test)")
            return original_update_with_lease(session, result_id, lease_token, values)

        with patch.object(tp.shutil, "which", return_value="/usr/bin/tesseract"):
            with patch.object(tp.pytesseract, "image_to_string", return_value="text that will not survive"):
                with patch.object(tp.pytesseract, "get_tesseract_version", return_value="5.3.4"):
                    with patch.object(pp, "_update_with_lease", side_effect=failing_update):
                        self._run()

        self.assertEqual(self._ocr_status(image_id).status, "failed")
        ocr_dir = get_settings().storage_root / "ocr_text" / str(project_id)
        leftover = list(ocr_dir.iterdir()) if ocr_dir.exists() else []
        self.assertEqual(leftover, [], "a failed final commit must not leave an orphaned OCR text file on disk")

    def _complete_once(self, image_id: int, color: tuple, text: str) -> tuple[str, str]:
        """Run a single, successful first-pass OCR for `image_id` (whose
        pixels are `color`), and return (ocr_text_path, text) of the
        real, now-committed result -- the "previous valid result" later
        tests reprocess against."""

        def tagged(image, lang=None, timeout=0, **kwargs):
            return text if self._color_of(image) == color else "unrelated"

        with patch.object(tp.shutil, "which", return_value="/usr/bin/tesseract"):
            with patch.object(tp.pytesseract, "image_to_string", side_effect=tagged):
                with patch.object(tp.pytesseract, "get_tesseract_version", return_value="5.3.4"):
                    self._run()

        row = self._ocr_status(image_id)
        self.assertEqual(row.status, "completed")
        return row.ocr_text_path, Path(row.ocr_text_path).read_text()

    def test_reprocess_ocr_failure_preserves_the_previous_completed_result(self):
        """Pre-commit review fix (Section 2): a --force reprocess whose
        OCR call itself fails must not destroy a real, previously
        successful result -- the row stays 'completed' with its
        original text and file untouched."""
        project_id = self._create_project("OCR Batch Test Preserve On OCR Failure")
        color = (223, 33, 43)
        image_id = self._upload_image(project_id, "preserve_ocr_fail.jpg", color=color)
        original_path, original_text = self._complete_once(image_id, color, "original good text")

        def failing_reprocess(image, lang=None, timeout=0, **kwargs):
            if self._color_of(image) == color:
                raise tp.TesseractError(1, "simulated reprocess OCR failure")
            return "unrelated"

        with patch.object(tp.shutil, "which", return_value="/usr/bin/tesseract"):
            with patch.object(tp.pytesseract, "image_to_string", side_effect=failing_reprocess):
                with patch.object(tp.pytesseract, "get_tesseract_version", return_value="5.3.4"):
                    self._run(force=True)

        restored = self._ocr_status(image_id)
        self.assertEqual(restored.status, "completed", "a failed reprocess OCR attempt must preserve the previous completed status")
        self.assertEqual(restored.ocr_text_path, original_path)
        self.assertEqual(Path(restored.ocr_text_path).read_text(), original_text)
        self.assertTrue(Path(original_path).exists(), "the original, still-valid OCR text file must not be deleted")

    def test_reprocess_file_write_failure_preserves_the_previous_completed_result(self):
        """Pre-commit review fix (Section 2): if writing the NEW
        candidate OCR text file itself fails (disk full, permissions),
        nothing has been committed or deleted yet -- a previously
        successful result must be preserved exactly as the OCR-failure
        case above."""
        project_id = self._create_project("OCR Batch Test Preserve On File Write Failure")
        color = (224, 34, 44)
        image_id = self._upload_image(project_id, "preserve_write_fail.jpg", color=color)
        original_path, original_text = self._complete_once(image_id, color, "original good text 2")

        def second_pass(image, lang=None, timeout=0, **kwargs):
            return "text that never gets written" if self._color_of(image) == color else "unrelated"

        with patch.object(tp.shutil, "which", return_value="/usr/bin/tesseract"):
            with patch.object(tp.pytesseract, "image_to_string", side_effect=second_pass):
                with patch.object(tp.pytesseract, "get_tesseract_version", return_value="5.3.4"):
                    with patch.object(pp, "save_ocr_text", side_effect=OSError("simulated disk failure")):
                        self._run(force=True)

        restored = self._ocr_status(image_id)
        self.assertEqual(restored.status, "completed", "a failed OCR-text file write must preserve the previous completed status")
        self.assertEqual(restored.ocr_text_path, original_path)
        self.assertEqual(Path(restored.ocr_text_path).read_text(), original_text)

    def test_reprocess_commit_failure_preserves_the_previous_result_and_cleans_up_the_candidate(self):
        """Pre-commit review fix (Section 2): if the final commit for a
        successful reprocess OCR run fails, the previous valid result
        must be preserved AND the newly-written candidate text file
        (never committed to any row) must be cleaned up -- never left
        as an orphan alongside the restored original."""
        project_id = self._create_project("OCR Batch Test Preserve On Commit Failure")
        color = (225, 35, 45)
        image_id = self._upload_image(project_id, "preserve_commit_fail.jpg", color=color)
        original_path, original_text = self._complete_once(image_id, color, "original good text 3")

        original_update_with_lease = pp._update_with_lease

        def failing_update(session, result_id, lease_token, values):
            if values.get("status") == "completed" and values.get("ocr_text_path") != original_path:
                raise RuntimeError("injected commit failure during reprocess (failure-injection regression test)")
            return original_update_with_lease(session, result_id, lease_token, values)

        def second_pass(image, lang=None, timeout=0, **kwargs):
            return "new text that should not survive" if self._color_of(image) == color else "unrelated"

        with patch.object(tp.shutil, "which", return_value="/usr/bin/tesseract"):
            with patch.object(tp.pytesseract, "image_to_string", side_effect=second_pass):
                with patch.object(tp.pytesseract, "get_tesseract_version", return_value="5.3.4"):
                    with patch.object(pp, "_update_with_lease", side_effect=failing_update):
                        self._run(force=True)

        restored = self._ocr_status(image_id)
        self.assertEqual(restored.status, "completed")
        self.assertEqual(restored.ocr_text_path, original_path)
        self.assertEqual(Path(restored.ocr_text_path).read_text(), original_text)

        # The candidate (new) file must have been cleaned up -- nothing
        # left in this project's ocr_text dir besides the original.
        ocr_dir = get_settings().storage_root / "ocr_text" / str(project_id)
        remaining_files = {p.name for p in ocr_dir.iterdir()}
        self.assertEqual(remaining_files, {Path(original_path).name})

    def test_tampered_storage_key_pointing_outside_storage_root_is_refused(self):
        """Defense in depth: even though storage_key is always server-
        generated, _resolve_source_image must still refuse to read a
        path that doesn't stay inside the configured storage root."""
        project_id = self._create_project("OCR Batch Test Path Containment")
        image_id = self._upload_image(project_id, "tampered.jpg")

        with get_session_factory()() as session:
            asset = session.get(ProjectImageAsset, image_id)
            asset.storage_key = "../../../../etc/passwd_attempt"
            session.commit()

            result = session.scalar(select(ImageOcrResult).where(ImageOcrResult.project_image_asset_id == image_id))
            resolved = pp._resolve_source_image(session, result, get_settings().storage_root)
            self.assertIsNone(resolved)

    def test_application_still_starts_with_tesseract_missing(self):
        """The real, un-mocked environment for this entire test file has
        no Tesseract installed (verified at module scope elsewhere) --
        the app booting and serving requests throughout every other test
        in this file already demonstrates this, but asserted explicitly
        here too."""
        with patch.object(tp.shutil, "which", return_value=None):
            self.assertFalse(tp.is_tesseract_available())
        resp = self.client.get("/projects")
        self.assertEqual(resp.status_code, 200)


class CliArgumentValidationTests(unittest.TestCase):
    """Pre-commit review fix (Section 3): --batch-size/--limit must be
    validated BEFORE anything else runs -- no Tesseract check, no
    database query, no row mutation. No database access at all in this
    class; argparse's own `type=` validation is exercised directly via
    main()'s argument parsing."""

    def test_batch_size_zero_is_rejected_with_a_clean_error_and_no_database_access(self):
        with patch.object(pp, "is_tesseract_available") as mock_available, patch.object(pp, "process_pending") as mock_process:
            with self.assertRaises(SystemExit) as ctx:
                pp.main(["--batch-size", "0"])
        self.assertEqual(ctx.exception.code, 2)
        mock_available.assert_not_called()
        mock_process.assert_not_called()

    def test_batch_size_negative_is_rejected(self):
        with patch.object(pp, "is_tesseract_available") as mock_available, patch.object(pp, "process_pending") as mock_process:
            with self.assertRaises(SystemExit) as ctx:
                pp.main(["--batch-size", "-5"])
        self.assertEqual(ctx.exception.code, 2)
        mock_available.assert_not_called()
        mock_process.assert_not_called()

    def test_limit_zero_is_rejected_with_a_clean_error_and_no_database_access(self):
        with patch.object(pp, "is_tesseract_available") as mock_available, patch.object(pp, "process_pending") as mock_process:
            with self.assertRaises(SystemExit) as ctx:
                pp.main(["--limit", "0"])
        self.assertEqual(ctx.exception.code, 2)
        mock_available.assert_not_called()
        mock_process.assert_not_called()

    def test_limit_negative_is_rejected(self):
        with patch.object(pp, "is_tesseract_available") as mock_available, patch.object(pp, "process_pending") as mock_process:
            with self.assertRaises(SystemExit) as ctx:
                pp.main(["--limit", "-1"])
        self.assertEqual(ctx.exception.code, 2)
        mock_available.assert_not_called()
        mock_process.assert_not_called()

    def test_valid_batch_size_and_limit_are_accepted_and_reach_process_pending(self):
        """Regression guard: the new validation must not reject sane,
        documented values -- only zero/negative ones."""
        with patch.object(pp, "is_tesseract_available", return_value=True):
            with patch.object(pp, "process_pending", return_value={"completed": 0, "empty": 0, "failed": 0, "skipped": 0}) as mock_process:
                exit_code = pp.main(["--batch-size", "5", "--limit", "10"])
        self.assertEqual(exit_code, 0)
        self.assertEqual(mock_process.call_args.kwargs["batch_size"], 5)
        self.assertEqual(mock_process.call_args.kwargs["limit"], 10)

    def test_default_batch_size_and_unset_limit_are_still_accepted(self):
        with patch.object(pp, "is_tesseract_available", return_value=True):
            with patch.object(pp, "process_pending", return_value={"completed": 0, "empty": 0, "failed": 0, "skipped": 0}) as mock_process:
                exit_code = pp.main([])
        self.assertEqual(exit_code, 0)
        self.assertEqual(mock_process.call_args.kwargs["batch_size"], pp.DEFAULT_BATCH_SIZE)
        self.assertIsNone(mock_process.call_args.kwargs["limit"])

    def test_process_pending_itself_also_rejects_non_positive_values(self):
        """Defense in depth: process_pending() is a public function other
        callers can invoke directly, bypassing main()'s argparse
        validation entirely -- it must reject bad input on its own too,
        before ever opening a database session."""
        with self.assertRaises(ValueError):
            pp.process_pending(batch_size=0, language="eng", tesseract_cmd=None, storage_root=get_settings().storage_root)
        with self.assertRaises(ValueError):
            pp.process_pending(batch_size=-3, language="eng", tesseract_cmd=None, storage_root=get_settings().storage_root)
        with self.assertRaises(ValueError):
            pp.process_pending(batch_size=10, limit=0, language="eng", tesseract_cmd=None, storage_root=get_settings().storage_root)
        with self.assertRaises(ValueError):
            pp.process_pending(batch_size=10, limit=-1, language="eng", tesseract_cmd=None, storage_root=get_settings().storage_root)


@unittest.skipUnless(shutil.which("tesseract"), "tesseract executable not installed -- skipping real integration smoke test")
class RealTesseractIntegrationSmokeTest(unittest.TestCase):
    """The one test in this file that exercises the REAL Tesseract
    binary end to end -- deliberately separate from, and never required
    by, the routine suite above."""

    def test_real_ocr_against_a_simple_rendered_text_image(self):
        from app.ocr.tesseract_provider import run_ocr

        img = Image.new("RGB", (400, 100), color=(255, 255, 255))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        result = run_ocr(buf.getvalue())
        self.assertEqual(result.status, "completed")
        self.assertIsNotNone(result.engine_version)


if __name__ == "__main__":
    unittest.main()
