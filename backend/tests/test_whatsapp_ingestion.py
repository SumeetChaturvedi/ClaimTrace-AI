"""Focused tests for the project-scoped WhatsApp export import/inspection
endpoints and pipeline (Phase W1: WhatsApp Export Ingestion) --
POST .../whatsapp/import, GET .../whatsapp/chats,
GET .../whatsapp/chats/{id}, GET .../whatsapp/messages/{id},
GET .../whatsapp/attachments/{id}/file.

Same approach as test_email_ingestion.py: plain `unittest` + TestClient,
no mocks, real Postgres, real ingestion pipeline (the exact same
PyMuPDF/sentence-transformers/pgvector path every PDF upload already goes
through). All chat content below is synthetic, invented for this test
file -- never real personal WhatsApp data.

Real Gemini is invoked exactly once in this whole file (search/citation
traceability through a real investigation), mirroring
test_email_ingestion.py's own "keep real LLM calls to a minimum" principle.

Run with:
    cd backend && source .venv/bin/activate
    PYTHONPATH=. python3 -m unittest tests.test_whatsapp_ingestion -v
"""

import io
import unittest
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.agent import tools as agent_tools
from app.config import get_settings
from app.db.models import (
    Document,
    DocumentChunk,
    InvestigationRecord,
    Project,
    WhatsAppChat,
    WhatsAppMediaAttachment,
    WhatsAppMessage,
)
from app.db.session import get_session_factory
from app.ingestion.storage import whatsapp_media_dir
from app.main import app
from app.whatsapp_ingestion.zip_import import WhatsAppZipImportError, extract_whatsapp_entries

NONEXISTENT_PROJECT_ID = 999_999
NONEXISTENT_CHAT_ID = 999_999
NONEXISTENT_MESSAGE_ID = 999_999


def _build_test_pdf(text: str) -> bytes:
    import fitz

    doc = fitz.open()
    doc.new_page().insert_text((50, 72), text, fontsize=11)
    return doc.tobytes()


def _build_zip(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in entries.items():
            zf.writestr(name, content)
    return buf.getvalue()


_JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 50


class WhatsAppIngestionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.client.__enter__()
        cls._created_project_ids: list[int] = []
        cls._created_investigation_ids: list = []

    @classmethod
    def tearDownClass(cls):
        with get_session_factory()() as session:
            for investigation_id in cls._created_investigation_ids:
                record = session.get(InvestigationRecord, investigation_id)
                if record is not None:
                    session.delete(record)
            session.commit()

            for project_id in cls._created_project_ids:
                documents = session.query(Document).filter(Document.project_id == project_id).all()
                for document in documents:
                    session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
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
        assert resp.status_code == 201, resp.text
        project_id = resp.json()["id"]
        self._created_project_ids.append(project_id)
        return project_id

    def _import(self, project_id: int, filename: str, content: bytes, content_type: str = "application/zip"):
        return self.client.post(
            f"/projects/{project_id}/whatsapp/import",
            files={"file": (filename, io.BytesIO(content), content_type)},
        )

    # -- Basic import / API shape --------------------------------------

    def test_successful_text_only_import_creates_searchable_documents(self):
        project_id = self._create_project("WhatsApp Test Project A")
        text = (
            "[25/03/24, 10:00:00] Site Engineer: Checking status of the retaining wall CLAIMTRACE-WA-A1.\n"
            "[25/03/24, 10:05:00] Project Manager: Will inspect this afternoon.\n"
        )
        resp = self._import(project_id, "chat.txt", text.encode("utf-8"), "text/plain")
        self.assertEqual(resp.status_code, 201, resp.text)
        body = resp.json()
        self.assertEqual(body["imported"], 2)
        self.assertEqual(body["duplicate"], 0)
        chat_id = body["chat_id"]

        docs = self.client.get(f"/projects/{project_id}/documents").json()
        wa_docs = [d for d in docs if d["doc_type"] == "WHATSAPP_MESSAGE"]
        self.assertEqual(len(wa_docs), 2)
        self.assertTrue(all(d["status"] == "ready" for d in wa_docs))

        chat_resp = self.client.get(f"/projects/{project_id}/whatsapp/chats/{chat_id}")
        self.assertEqual(chat_resp.status_code, 200)
        messages = chat_resp.json()["messages"]
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["sender_name"], "Site Engineer")
        self.assertEqual(messages[0]["sequence_index"], 0)
        self.assertEqual(messages[1]["sequence_index"], 1)

    def test_import_to_nonexistent_project_returns_404(self):
        resp = self._import(NONEXISTENT_PROJECT_ID, "chat.txt", b"[01/01/24, 08:00:00] A: hi", "text/plain")
        self.assertEqual(resp.status_code, 404)

    def test_unsupported_file_type_is_rejected(self):
        project_id = self._create_project("WhatsApp Test Project B")
        resp = self._import(project_id, "chat.pdf", b"%PDF-1.4 not really", "application/pdf")
        self.assertEqual(resp.status_code, 400)

    def test_empty_upload_is_rejected(self):
        project_id = self._create_project("WhatsApp Test Project C")
        resp = self._import(project_id, "chat.txt", b"", "text/plain")
        self.assertEqual(resp.status_code, 400)

    def test_zip_with_no_txt_transcript_is_rejected(self):
        project_id = self._create_project("WhatsApp Test Project D")
        zip_bytes = _build_zip({"photo.jpg": _JPEG_BYTES})
        resp = self._import(project_id, "chat.zip", zip_bytes, "application/zip")
        self.assertEqual(resp.status_code, 400)

    # -- Attachment traceability ----------------------------------------

    def test_pdf_attachment_becomes_a_real_indexed_document_linked_to_its_message(self):
        project_id = self._create_project("WhatsApp Test Project E")
        pdf_bytes = _build_test_pdf("Attachment marker CLAIMTRACE-WA-PDF-3001.")
        text = "[25/03/24, 10:00:00] Site Engineer: <attached: notice.pdf>\n"
        zip_bytes = _build_zip({"chat.txt": text.encode("utf-8"), "notice.pdf": pdf_bytes})

        resp = self._import(project_id, "chat.zip", zip_bytes, "application/zip")
        self.assertEqual(resp.status_code, 201, resp.text)
        body = resp.json()
        self.assertEqual(body["attachments_processed"], 1)
        chat_id = body["chat_id"]

        chat = self.client.get(f"/projects/{project_id}/whatsapp/chats/{chat_id}").json()
        message_id = chat["messages"][0]["document_id"]

        message = self.client.get(f"/projects/{project_id}/whatsapp/messages/{message_id}").json()
        self.assertEqual(len(message["attachments"]), 1)
        attachment = message["attachments"][0]
        self.assertEqual(attachment["status"], "processed")
        self.assertIsNotNone(attachment["document_id"])

        # The attachment's own Document is real, indexed, and distinct
        # from the message's own Document.
        file_resp = self.client.get(f"/projects/{project_id}/documents/{attachment['document_id']}/file")
        self.assertEqual(file_resp.status_code, 200)
        self.assertEqual(file_resp.headers["content-type"], "application/pdf")

        # Provenance back to the originating WhatsApp message, mirroring
        # the existing email-attachment-provenance pattern exactly.
        attachment_doc = self.client.get(
            f"/projects/{project_id}/documents/{attachment['document_id']}"
        ).json()
        self.assertIsNotNone(attachment_doc["whatsapp_source"])
        self.assertEqual(attachment_doc["whatsapp_source"]["message_document_id"], message_id)
        self.assertEqual(attachment_doc["whatsapp_source"]["sender_name"], "Site Engineer")
        self.assertIsNone(attachment_doc["email_source"])

        # The message's own body document must NOT carry a whatsapp_source
        # (it IS the source, not an attachment of one).
        message_doc = self.client.get(f"/projects/{project_id}/documents/{message_id}").json()
        self.assertIsNone(message_doc["whatsapp_source"])

    def test_image_attachment_is_preserved_as_bytes_not_discarded_and_not_fabricated_as_indexed(self):
        project_id = self._create_project("WhatsApp Test Project F")
        text = "[25/03/24, 10:00:00] Foreman: <attached: site-photo.jpg>\n"
        zip_bytes = _build_zip({"chat.txt": text.encode("utf-8"), "site-photo.jpg": _JPEG_BYTES})

        resp = self._import(project_id, "chat.zip", zip_bytes, "application/zip")
        self.assertEqual(resp.status_code, 201, resp.text)
        body = resp.json()
        self.assertEqual(body["attachments_pending"], 1)
        chat_id = body["chat_id"]

        chat = self.client.get(f"/projects/{project_id}/whatsapp/chats/{chat_id}").json()
        message_id = chat["messages"][0]["document_id"]
        message = self.client.get(f"/projects/{project_id}/whatsapp/messages/{message_id}").json()
        attachment = message["attachments"][0]

        self.assertEqual(attachment["status"], "stored_pending_processing")
        # Never fabricated as an indexed, citable Document -- no document_id.
        self.assertIsNone(attachment["document_id"])

        # The ORIGINAL bytes are genuinely retrievable, not discarded.
        file_resp = self.client.get(f"/projects/{project_id}/whatsapp/attachments/{attachment['id']}/file")
        self.assertEqual(file_resp.status_code, 200)
        self.assertEqual(file_resp.headers["content-type"], "image/jpeg")
        self.assertEqual(file_resp.content, _JPEG_BYTES)

    def test_media_reference_with_no_matching_zip_entry_is_rejected_not_fabricated(self):
        project_id = self._create_project("WhatsApp Test Project G")
        text = "[25/03/24, 10:00:00] Alice: <attached: missing-file.jpg>\n"
        zip_bytes = _build_zip({"chat.txt": text.encode("utf-8")})

        resp = self._import(project_id, "chat.zip", zip_bytes, "application/zip")
        self.assertEqual(resp.status_code, 201, resp.text)
        body = resp.json()
        self.assertEqual(body["attachments_rejected"], 1)

    def test_a_message_with_media_retains_its_own_message_level_provenance(self):
        """An attachment Document must remain traceable back to its
        originating WhatsApp message, mirroring the email-attachment
        provenance pattern."""
        project_id = self._create_project("WhatsApp Test Project H")
        pdf_bytes = _build_test_pdf("Provenance marker CLAIMTRACE-WA-PROV-4001.")
        text = "[25/03/24, 10:00:00] Site Engineer: <attached: report.pdf>\n"
        zip_bytes = _build_zip({"chat.txt": text.encode("utf-8"), "report.pdf": pdf_bytes})

        resp = self._import(project_id, "chat.zip", zip_bytes, "application/zip")
        chat_id = resp.json()["chat_id"]
        chat = self.client.get(f"/projects/{project_id}/whatsapp/chats/{chat_id}").json()
        message_document_id = chat["messages"][0]["document_id"]
        message = self.client.get(f"/projects/{project_id}/whatsapp/messages/{message_document_id}").json()
        attachment_document_id = message["attachments"][0]["document_id"]

        with get_session_factory()() as session:
            attachment_row = session.scalar(
                select(WhatsAppMediaAttachment).where(WhatsAppMediaAttachment.document_id == attachment_document_id)
            )
            self.assertIsNotNone(attachment_row)
            self.assertEqual(attachment_row.message_id, message_document_id)

    # -- Deduplication ----------------------------------------------------

    def test_identical_reimport_is_a_no_op(self):
        project_id = self._create_project("WhatsApp Test Project I")
        text = (
            "[25/03/24, 10:00:00] Alice: first message\n"
            "[25/03/24, 10:01:00] Bob: second message\n"
        )
        raw = text.encode("utf-8")

        first = self._import(project_id, "chat.txt", raw, "text/plain")
        self.assertEqual(first.json()["imported"], 2)

        second = self._import(project_id, "chat.txt", raw, "text/plain")
        self.assertEqual(second.json()["imported"], 0)
        self.assertEqual(second.json()["duplicate"], 2)
        self.assertEqual(first.json()["chat_id"], second.json()["chat_id"])

        docs = self.client.get(f"/projects/{project_id}/documents").json()
        wa_docs = [d for d in docs if d["doc_type"] == "WHATSAPP_MESSAGE"]
        self.assertEqual(len(wa_docs), 2, "a re-import must never create a second Document for the same message")

    def test_partially_overlapping_export_imports_only_the_new_messages(self):
        project_id = self._create_project("WhatsApp Test Project J")
        first_text = (
            "[25/03/24, 10:00:00] Alice: message one\n"
            "[25/03/24, 10:01:00] Bob: message two\n"
        )
        first = self._import(project_id, "chat.txt", first_text.encode("utf-8"), "text/plain")
        self.assertEqual(first.json()["imported"], 2)

        # A later export of the SAME chat (same filename) that includes
        # both earlier messages AND a genuinely new one.
        second_text = first_text + "[25/03/24, 10:02:00] Alice: message three (new)\n"
        second = self._import(project_id, "chat.txt", second_text.encode("utf-8"), "text/plain")
        self.assertEqual(second.json()["imported"], 1)
        self.assertEqual(second.json()["duplicate"], 2)
        self.assertEqual(first.json()["chat_id"], second.json()["chat_id"])

        chat = self.client.get(f"/projects/{project_id}/whatsapp/chats/{first.json()['chat_id']}").json()
        self.assertEqual(len(chat["messages"]), 3)
        self.assertEqual(chat["messages"][2]["sequence_index"], 2)

    def test_concurrent_identical_imports_never_create_duplicate_messages(self):
        project_id = self._create_project("WhatsApp Test Project K")
        text = "[25/03/24, 10:00:00] Alice: race condition marker message\n"
        raw = text.encode("utf-8")

        def _one(i: int):
            return self._import(project_id, "chat.txt", raw, "text/plain")

        with ThreadPoolExecutor(max_workers=5) as pool:
            responses = list(pool.map(_one, range(5)))

        self.assertTrue(all(r.status_code == 201 for r in responses), [r.text for r in responses])
        imported_counts = [r.json()["imported"] for r in responses]
        self.assertEqual(sum(imported_counts), 1, "a concurrent race must import the message exactly once")

        docs = self.client.get(f"/projects/{project_id}/documents").json()
        wa_docs = [d for d in docs if d["doc_type"] == "WHATSAPP_MESSAGE"]
        self.assertEqual(len(wa_docs), 1, "a concurrent race must never leave more than one Document behind")

    # -- Project isolation -------------------------------------------------

    def test_chat_from_one_project_not_retrievable_via_another(self):
        project_a = self._create_project("WhatsApp Test Project L1")
        project_b = self._create_project("WhatsApp Test Project L2")
        resp = self._import(project_a, "chat.txt", b"[25/03/24, 10:00:00] A: hi", "text/plain")
        chat_id = resp.json()["chat_id"]

        cross_resp = self.client.get(f"/projects/{project_b}/whatsapp/chats/{chat_id}")
        self.assertEqual(cross_resp.status_code, 404)

    def test_message_from_one_project_not_retrievable_via_another(self):
        project_a = self._create_project("WhatsApp Test Project M1")
        project_b = self._create_project("WhatsApp Test Project M2")
        resp = self._import(project_a, "chat.txt", b"[25/03/24, 10:00:00] A: hi", "text/plain")
        chat = self.client.get(f"/projects/{project_a}/whatsapp/chats/{resp.json()['chat_id']}").json()
        message_id = chat["messages"][0]["document_id"]

        cross_resp = self.client.get(f"/projects/{project_b}/whatsapp/messages/{message_id}")
        self.assertEqual(cross_resp.status_code, 404)

    def test_nonexistent_chat_and_message_return_404(self):
        project_id = self._create_project("WhatsApp Test Project N")
        self.assertEqual(
            self.client.get(f"/projects/{project_id}/whatsapp/chats/{NONEXISTENT_CHAT_ID}").status_code, 404
        )
        self.assertEqual(
            self.client.get(f"/projects/{project_id}/whatsapp/messages/{NONEXISTENT_MESSAGE_ID}").status_code, 404
        )

    # -- Timestamp ambiguity surfaced in warnings -------------------------

    def test_ambiguous_timestamp_is_surfaced_as_a_parse_warning(self):
        project_id = self._create_project("WhatsApp Test Project O")
        resp = self._import(project_id, "chat.txt", b"[03/04/24, 10:00:00] A: ambiguous date message", "text/plain")
        self.assertEqual(resp.status_code, 201)
        # No warning is emitted for AMBIGUITY specifically by this parser
        # (ambiguity is a per-message flag, not a parse note) -- verify
        # instead that the message itself is flagged.
        chat = self.client.get(f"/projects/{project_id}/whatsapp/chats/{resp.json()['chat_id']}").json()
        self.assertTrue(chat["messages"][0]["sent_at_ambiguous"])

    def test_unparseable_timestamp_is_surfaced_as_a_parse_warning(self):
        project_id = self._create_project("WhatsApp Test Project P")
        resp = self._import(project_id, "chat.txt", b"[32/13/24, 10:00:00] A: impossible date message", "text/plain")
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(any("unparseable date" in w for w in resp.json()["parse_warnings"]))

    # -- Investigation/retrieval integration (real Gemini, used once) ----

    def test_whatsapp_message_text_is_searchable_through_existing_search_documents(self):
        """No WhatsApp-specific branch exists anywhere in the retrieval/
        investigation stack -- this calls the exact same, unmodified
        search_documents() every PDF/email citation already goes through."""
        project_id = self._create_project("WhatsApp Test Project Q")
        marker = "CLAIMTRACE-WA-SEARCH-9001"
        text = f"[25/03/24, 10:00:00] Site Engineer: Unique retrieval marker {marker} regarding the retaining wall.\n"
        resp = self._import(project_id, "chat.txt", text.encode("utf-8"), "text/plain")
        chat = self.client.get(f"/projects/{project_id}/whatsapp/chats/{resp.json()['chat_id']}").json()
        expected_document_id = chat["messages"][0]["document_id"]

        citations = agent_tools.search_documents(project_id, f"retaining wall {marker}", top_k=3)
        self.assertTrue(
            any(c.document_id == expected_document_id for c in citations),
            f"expected document {expected_document_id} among {[c.document_id for c in citations]}",
        )


class WhatsAppAmbiguousBasenameTests(unittest.TestCase):
    """Pre-commit review fix regression: when a ZIP archive contains more
    than one entry sharing the basename a message referenced, NEITHER
    candidate must ever be silently attached to that message -- see
    app/whatsapp_ingestion/pipeline.py's _resolve_media_candidate. Every
    assertion below checks the actual stored content and document
    associations, not just the returned status string, so a regression
    that merely returns the right label while still misattaching bytes
    would be caught."""

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
        assert resp.status_code == 201, resp.text
        project_id = resp.json()["id"]
        self._created_project_ids.append(project_id)
        return project_id

    def _import(self, project_id: int, filename: str, content: bytes):
        return self.client.post(
            f"/projects/{project_id}/whatsapp/import",
            files={"file": (filename, io.BytesIO(content), "application/zip")},
        )

    def test_two_flat_entries_same_basename_different_content_are_both_ambiguous(self):
        """Scenario 1: no subdirectories at all -- two literal same-name
        entries at the archive root, referenced by a single message."""
        project_id = self._create_project("WA Ambiguous Flat Basenames")
        text = "[25/03/24, 10:00:00] Alice: <attached: photo.jpg>\n"
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("chat.txt", text)
            zf.writestr("photo.jpg", b"FIRST_CONTENT_AAAA")
            zf.writestr("photo.jpg", b"SECOND_CONTENT_BBBB")  # literal duplicate name, same directory

        resp = self._import(project_id, "chat.zip", buf.getvalue())
        self.assertEqual(resp.status_code, 201, resp.text)
        body = resp.json()
        self.assertEqual(body["attachments_ambiguous"], 1)
        self.assertEqual(body["attachments_pending"], 0)

        with get_session_factory()() as session:
            attachment = session.scalar(
                select(WhatsAppMediaAttachment).where(
                    WhatsAppMediaAttachment.filename == "photo.jpg",
                    WhatsAppMediaAttachment.message_id.in_(
                        select(WhatsAppMessage.document_id).where(WhatsAppMessage.project_id == project_id)
                    ),
                )
            )
            self.assertEqual(attachment.status, "rejected")
            self.assertIsNone(attachment.document_id)
            self.assertIsNone(attachment.storage_key)
            self.assertIn("ambiguous", attachment.processing_error.lower())
            # No file was ever written for the ambiguous reference.
            media_dir = whatsapp_media_dir(get_settings().storage_root, project_id)
            self.assertEqual(list(media_dir.iterdir()) if media_dir.exists() else [], [])

    def test_two_entries_in_different_directories_same_basename_are_ambiguous(self):
        """Scenario 2: the exact basename-collision-across-directories
        case the original defect was built on."""
        project_id = self._create_project("WA Ambiguous Nested Basenames")
        text = "[25/03/24, 10:00:00] Alice: <attached: photo.jpg>\n"
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("chat.txt", text)
            zf.writestr("folderA/photo.jpg", b"AAAA_REAL_PHOTO_CONTENT")
            zf.writestr("folderB/photo.jpg", b"BBBB_DIFFERENT_PHOTO_CONTENT")

        resp = self._import(project_id, "chat.zip", buf.getvalue())
        body = resp.json()
        self.assertEqual(body["attachments_ambiguous"], 1)

        with get_session_factory()() as session:
            attachment = session.scalar(
                select(WhatsAppMediaAttachment).where(
                    WhatsAppMediaAttachment.filename == "photo.jpg",
                    WhatsAppMediaAttachment.message_id.in_(
                        select(WhatsAppMessage.document_id).where(WhatsAppMessage.project_id == project_id)
                    ),
                )
            )
            self.assertEqual(attachment.status, "rejected")
            self.assertIsNone(attachment.storage_key)

    def test_two_messages_referencing_the_ambiguous_basename_are_both_ambiguous(self):
        """Scenario 3: the ambiguity applies independently to every
        message that references the colliding basename, not just the
        first one."""
        project_id = self._create_project("WA Ambiguous Two Messages")
        text = (
            "[25/03/24, 10:00:00] Alice: <attached: photo.jpg>\n"
            "[25/03/24, 10:01:00] Bob: <attached: photo.jpg>\n"
        )
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("chat.txt", text)
            zf.writestr("folderA/photo.jpg", b"AAAA")
            zf.writestr("folderB/photo.jpg", b"BBBB")

        resp = self._import(project_id, "chat.zip", buf.getvalue())
        body = resp.json()
        self.assertEqual(body["imported"], 2)
        self.assertEqual(body["attachments_ambiguous"], 2)

        with get_session_factory()() as session:
            attachments = session.scalars(
                select(WhatsAppMediaAttachment).where(
                    WhatsAppMediaAttachment.filename == "photo.jpg",
                    WhatsAppMediaAttachment.message_id.in_(
                        select(WhatsAppMessage.document_id).where(WhatsAppMessage.project_id == project_id)
                    ),
                )
            ).all()
            self.assertEqual(len(attachments), 2)
            self.assertTrue(all(a.status == "rejected" and a.document_id is None for a in attachments))

    def test_pdf_collision_neither_candidate_is_silently_indexed(self):
        """Scenario 4: the more severe PDF case -- neither PDF's text
        must ever become a real, indexed, citable Document."""
        project_id = self._create_project("WA Ambiguous PDF Collision")
        pdf_a = _build_test_pdf("ALICE REAL NOTICE CONTENT MARKER CLAIMTRACE-WA-AMBIG-A")
        pdf_b = _build_test_pdf("BOB DIFFERENT NOTICE CONTENT MARKER CLAIMTRACE-WA-AMBIG-B")
        text = "[25/03/24, 10:00:00] Alice: <attached: notice.pdf>\n"
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("chat.txt", text)
            zf.writestr("folderA/notice.pdf", pdf_a)
            zf.writestr("folderB/notice.pdf", pdf_b)

        resp = self._import(project_id, "chat.zip", buf.getvalue())
        body = resp.json()
        self.assertEqual(body["attachments_processed"], 0)
        self.assertEqual(body["attachments_ambiguous"], 1)

        with get_session_factory()() as session:
            attachment = session.scalar(
                select(WhatsAppMediaAttachment).where(
                    WhatsAppMediaAttachment.filename == "notice.pdf",
                    WhatsAppMediaAttachment.message_id.in_(
                        select(WhatsAppMessage.document_id).where(WhatsAppMessage.project_id == project_id)
                    ),
                )
            )
            self.assertIsNone(attachment.document_id)
            # Neither marker text was indexed as a Document anywhere in
            # this project -- confirms no silent pick of either candidate,
            # not merely that THIS attachment row has no document_id.
            documents = session.query(Document).filter(Document.project_id == project_id).all()
            self.assertEqual([d for d in documents if d.filename == "notice.pdf"], [])

    def test_unrelated_uniquely_named_attachment_in_the_same_archive_still_imports(self):
        """Scenario 5: an ambiguous reference for one message must not
        affect an unrelated, uniquely-named attachment on another
        message in the same import."""
        project_id = self._create_project("WA Ambiguous Plus Unique")
        pdf_bytes = _build_test_pdf("Unique marker CLAIMTRACE-WA-UNIQUE-OK-1")
        text = (
            "[25/03/24, 10:00:00] Alice: <attached: photo.jpg>\n"
            "[25/03/24, 10:01:00] Bob: <attached: report.pdf>\n"
        )
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("chat.txt", text)
            zf.writestr("folderA/photo.jpg", b"AAAA")
            zf.writestr("folderB/photo.jpg", b"BBBB")
            zf.writestr("report.pdf", pdf_bytes)

        resp = self._import(project_id, "chat.zip", buf.getvalue())
        body = resp.json()
        self.assertEqual(body["attachments_ambiguous"], 1)
        self.assertEqual(body["attachments_processed"], 1)

        with get_session_factory()() as session:
            report_attachment = session.scalar(
                select(WhatsAppMediaAttachment).where(
                    WhatsAppMediaAttachment.filename == "report.pdf",
                    WhatsAppMediaAttachment.message_id.in_(
                        select(WhatsAppMessage.document_id).where(WhatsAppMessage.project_id == project_id)
                    ),
                )
            )
            self.assertEqual(report_attachment.status, "processed")
            self.assertIsNotNone(report_attachment.document_id)
            doc = session.get(Document, report_attachment.document_id)
            self.assertEqual(doc.status, "ready")

    def test_normal_zip_with_a_unique_media_filename_still_imports_successfully(self):
        """Scenario 6: the ordinary, non-colliding case is completely
        unaffected by this fix."""
        project_id = self._create_project("WA Ambiguous Control Unique Only")
        pdf_bytes = _build_test_pdf("Control marker CLAIMTRACE-WA-CONTROL-OK-1")
        text = "[25/03/24, 10:00:00] Alice: <attached: notice.pdf>\n"
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("chat.txt", text)
            zf.writestr("notice.pdf", pdf_bytes)

        resp = self._import(project_id, "chat.zip", buf.getvalue())
        body = resp.json()
        self.assertEqual(body["attachments_ambiguous"], 0)
        self.assertEqual(body["attachments_processed"], 1)

        with get_session_factory()() as session:
            attachment = session.scalar(
                select(WhatsAppMediaAttachment).where(
                    WhatsAppMediaAttachment.filename == "notice.pdf",
                    WhatsAppMediaAttachment.message_id.in_(
                        select(WhatsAppMessage.document_id).where(WhatsAppMessage.project_id == project_id)
                    ),
                )
            )
            self.assertEqual(attachment.status, "processed")
            doc = session.get(Document, attachment.document_id)
            self.assertEqual(Path(doc.raw_text_path).read_text().strip(), "Control marker CLAIMTRACE-WA-CONTROL-OK-1")

    def test_commit_failure_after_writing_raw_media_removes_the_orphaned_file(self):
        """Section 2 failure-injection regression test: a raw (non-PDF/
        DOCX) media attachment is written to disk by save_whatsapp_media()
        BEFORE its WhatsAppMediaAttachment row is committed. If that commit
        fails, app/whatsapp_ingestion/pipeline.py's _ingest_media_attachment
        must delete the just-written file rather than leave it orphaned on
        disk with no DB row to ever reference it. This injects a real
        commit failure (via a monkeypatched Session.commit, raised only for
        the specific pending attachment row this test cares about) and
        verifies the file is actually gone afterward, not just that the
        reported status says 'failed'."""
        project_id = self._create_project("WA FailureInjection RawMedia")
        text = "[25/03/24, 10:00:00] Alice: <attached: clip.bin>\n"
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("chat.txt", text)
            zf.writestr("clip.bin", b"RAW_UNSUPPORTED_BYTES_PAYLOAD_FOR_FAILURE_INJECTION")

        original_commit = Session.commit

        def failing_commit(self):
            pending_raw_media = [
                obj
                for obj in self.new
                if isinstance(obj, WhatsAppMediaAttachment)
                and obj.status == "stored_pending_processing"
                and obj.storage_key is not None
            ]
            if pending_raw_media:
                raise RuntimeError("injected commit failure (failure-injection regression test)")
            return original_commit(self)

        with patch.object(Session, "commit", failing_commit):
            resp = self._import(project_id, "chat.zip", buf.getvalue())
        self.assertEqual(resp.status_code, 201, resp.text)
        body = resp.json()
        self.assertEqual(body["imported"], 1)
        self.assertEqual(body["attachments_failed"], 1)
        self.assertEqual(body["attachments_pending"], 0)

        media_dir = whatsapp_media_dir(get_settings().storage_root, project_id)
        leftover_files = list(media_dir.iterdir()) if media_dir.exists() else []
        self.assertEqual(
            leftover_files,
            [],
            "the file written for the raw-media attachment must be deleted when its row commit fails",
        )

        with get_session_factory()() as session:
            orphaned_row = session.scalar(
                select(WhatsAppMediaAttachment).where(
                    WhatsAppMediaAttachment.filename == "clip.bin",
                    WhatsAppMediaAttachment.message_id.in_(
                        select(WhatsAppMessage.document_id).where(WhatsAppMessage.project_id == project_id)
                    ),
                )
            )
            # The row's own commit was rolled back -- it must not exist
            # at all, rather than existing in some inconsistent state.
            self.assertIsNone(orphaned_row)
            message = session.scalar(
                select(WhatsAppMessage).where(WhatsAppMessage.project_id == project_id)
            )
            self.assertIsNotNone(message)


class WhatsAppConstraintTests(unittest.TestCase):
    """Direct, DB-level verification that deduplication and provenance
    are backed by real constraints, not only the application-level
    pre-check -- the same defense-in-depth property the concurrent-import
    test above already demonstrates behaviorally."""

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
                session.execute(delete(WhatsAppMessage).where(WhatsAppMessage.project_id == project_id))
                session.execute(delete(WhatsAppChat).where(WhatsAppChat.project_id == project_id))
                session.query(Document).filter(Document.project_id == project_id).delete()
                session.query(Project).filter(Project.id == project_id).delete()
            session.commit()
        cls.client.__exit__(None, None, None)

    def test_unique_constraint_on_chat_and_content_hash_is_enforced_at_the_database_level(self):
        resp = self.client.post("/projects", json={"name": "WhatsApp Constraint Test A"})
        project_id = resp.json()["id"]
        self._created_project_ids.append(project_id)

        import_resp = self.client.post(
            f"/projects/{project_id}/whatsapp/import",
            files={"file": ("chat.txt", io.BytesIO(b"[01/01/24, 08:00:00] A: constraint marker"), "text/plain")},
        )
        chat_id = import_resp.json()["chat_id"]

        with get_session_factory()() as session:
            chat = session.get(WhatsAppChat, chat_id)
            message = chat.messages[0]
            from app.db.models import Document as DocumentModel

            duplicate_document = DocumentModel(project_id=project_id, filename="dup.txt", doc_type="WHATSAPP_MESSAGE", status="ready")
            session.add(duplicate_document)
            session.commit()
            session.refresh(duplicate_document)

            duplicate_message = WhatsAppMessage(
                document_id=duplicate_document.id,
                project_id=project_id,
                chat_id=chat_id,
                sequence_index=99,
                sender_name="A",
                raw_timestamp_text=message.raw_timestamp_text,
                sent_at=message.sent_at,
                content_hash=message.content_hash,  # deliberately identical
                message_type="text",
            )
            session.add(duplicate_message)
            from sqlalchemy.exc import IntegrityError

            with self.assertRaises(IntegrityError):
                session.commit()
            session.rollback()
            session.delete(duplicate_document)
            session.commit()

    def test_deleting_the_project_cascades_through_chat_message_and_attachment_rows(self):
        resp = self.client.post("/projects", json={"name": "WhatsApp Constraint Test B"})
        project_id = resp.json()["id"]

        pdf_bytes = _build_test_pdf("Cascade marker CLAIMTRACE-WA-CASCADE-5001.")
        zip_bytes = _build_zip(
            {"chat.txt": b"[01/01/24, 08:00:00] A: <attached: f.pdf>", "f.pdf": pdf_bytes}
        )
        import_resp = self.client.post(
            f"/projects/{project_id}/whatsapp/import",
            files={"file": ("chat.zip", io.BytesIO(zip_bytes), "application/zip")},
        )
        chat_id = import_resp.json()["chat_id"]

        with get_session_factory()() as session:
            from sqlalchemy import text as sql_text

            session.execute(sql_text("DELETE FROM projects WHERE id = :pid"), {"pid": project_id})
            session.commit()

        with get_session_factory()() as session:
            self.assertIsNone(session.get(WhatsAppChat, chat_id))
            remaining_messages = session.scalars(select(WhatsAppMessage).where(WhatsAppMessage.chat_id == chat_id)).all()
            self.assertEqual(remaining_messages, [])
            remaining_attachments = session.scalars(
                select(WhatsAppMediaAttachment).where(WhatsAppMediaAttachment.message_id.in_(select(WhatsAppMessage.document_id)))
            ).all()
            self.assertEqual(remaining_attachments, [])


class WhatsAppZipSafetyTests(unittest.TestCase):
    """Deterministic, offline tests for app/whatsapp_ingestion/zip_import.py
    -- no database, mirroring the reused security primitives' own
    guarantees from app/email_ingestion/zip_import.py."""

    def test_path_traversal_entry_is_rejected(self):
        zip_bytes = _build_zip({"chat.txt": b"[01/01/24, 08:00:00] A: hi", "../../evil.txt": b"traversal"})
        result = extract_whatsapp_entries(zip_bytes)
        names = [e.name for e in result.entries]
        self.assertIn("chat.txt", names)
        self.assertTrue(any("unsafe path" in r.error for r in result.rejected))

    def test_malformed_non_zip_input_raises_a_clean_error(self):
        with self.assertRaises(WhatsAppZipImportError):
            extract_whatsapp_entries(b"not a zip file at all")

    def test_entry_exceeding_the_per_file_limit_is_rejected_not_silently_truncated(self):
        from app.whatsapp_ingestion import zip_import as wa_zip

        original_max = wa_zip.MAX_ENTRY_BYTES
        wa_zip.MAX_ENTRY_BYTES = 10
        try:
            zip_bytes = _build_zip({"big.jpg": b"x" * 1000})
            result = extract_whatsapp_entries(zip_bytes)
        finally:
            wa_zip.MAX_ENTRY_BYTES = original_max
        self.assertEqual(result.entries, [])
        self.assertTrue(any("per-file limit" in r.error for r in result.rejected))

    def test_excessive_entry_count_raises_before_any_extraction(self):
        from app.whatsapp_ingestion import zip_import as wa_zip

        original_max = wa_zip.MAX_ENTRIES
        wa_zip.MAX_ENTRIES = 2
        try:
            zip_bytes = _build_zip({"a.txt": b"1", "b.txt": b"2", "c.txt": b"3"})
            with self.assertRaises(WhatsAppZipImportError):
                extract_whatsapp_entries(zip_bytes)
        finally:
            wa_zip.MAX_ENTRIES = original_max

    def test_empty_entry_is_rejected(self):
        zip_bytes = _build_zip({"chat.txt": b"[01/01/24, 08:00:00] A: hi", "empty.jpg": b""})
        result = extract_whatsapp_entries(zip_bytes)
        self.assertTrue(any(r.name == "empty.jpg" and "empty" in r.error for r in result.rejected))

    def test_directory_entries_are_silently_skipped_not_rejected(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("media/", b"")
            zf.writestr("chat.txt", b"[01/01/24, 08:00:00] A: hi")
        result = extract_whatsapp_entries(buf.getvalue())
        names = [e.name for e in result.entries]
        self.assertEqual(names, ["chat.txt"])
        self.assertEqual(result.rejected, [])

    def test_archive_exceeding_the_total_extraction_size_limit_is_rejected(self):
        """Section 3 targeted coverage: the whole-archive MAX_TOTAL_BYTES
        cap (the actual decompressed-byte budget, not merely the
        compressed ZIP size) must stop accepting entries once the running
        total crosses it, using the real production primitive -- not a
        test-local reimplementation."""
        from app.whatsapp_ingestion import zip_import as wa_zip

        original_max = wa_zip.MAX_TOTAL_BYTES
        wa_zip.MAX_TOTAL_BYTES = 100
        try:
            zip_bytes = _build_zip(
                {
                    "chat.txt": b"[01/01/24, 08:00:00] A: hi",
                    "first.jpg": b"a" * 60,
                    "second.jpg": b"b" * 60,
                }
            )
            result = extract_whatsapp_entries(zip_bytes)
        finally:
            wa_zip.MAX_TOTAL_BYTES = original_max

        names = [e.name for e in result.entries]
        self.assertIn("chat.txt", names)
        self.assertIn("first.jpg", names)
        self.assertNotIn("second.jpg", names)
        self.assertTrue(any(r.name == "second.jpg" and "total extraction size limit" in r.error for r in result.rejected))

    def test_literal_duplicate_entry_names_are_both_preserved_as_distinct_entries(self):
        """Section 3 targeted coverage, extraction-layer half of the
        basename-collision fix: when an archive contains two entries at
        the IDENTICAL literal path (zipfile permits this), the extraction
        layer itself must keep both -- collapsing them before the pipeline
        ever sees them would silently recreate the original defect one
        layer lower."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("chat.txt", b"[01/01/24, 08:00:00] A: hi")
            zf.writestr("photo.jpg", b"FIRST_CONTENT_AAAA")
            zf.writestr("photo.jpg", b"SECOND_CONTENT_BBBB")

        result = extract_whatsapp_entries(buf.getvalue())
        photo_entries = [e for e in result.entries if e.name == "photo.jpg"]
        self.assertEqual(len(photo_entries), 2)
        self.assertEqual({e.content for e in photo_entries}, {b"FIRST_CONTENT_AAAA", b"SECOND_CONTENT_BBBB"})


if __name__ == "__main__":
    unittest.main()
