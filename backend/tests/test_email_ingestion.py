"""Focused tests for the project-scoped email import/inspection endpoints
and pipeline (Phase 8A: Email Thread Intelligence) — POST .../emails/import,
GET .../emails/threads, GET .../emails/threads/{id}, GET .../emails/messages/{id}.

Same approach as test_docx_ingestion.py: plain `unittest` + TestClient, no
mocks, real Postgres, real ingestion pipeline (the exact same PyMuPDF/
python-docx/sentence-transformers/pgvector path every PDF/DOCX upload
already goes through) — real .eml bytes are built via Python's own stdlib
`email` package, the same library app/email_ingestion/parsing.py itself
uses to read them back, not a hand-written fixture string.

Real Gemini is invoked exactly once in this whole file (citation
traceability through a real investigation), mirroring
test_investigations.py's own "keep real LLM calls to a minimum, share
across tests" principle.

Run with:
    cd backend && source .venv/bin/activate
    PYTHONPATH=. python3 -m unittest tests.test_email_ingestion -v
"""

import io
import unittest
import zipfile
from concurrent.futures import ThreadPoolExecutor
from email.message import EmailMessage as StdlibEmailMessage
from email.utils import formatdate

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.config import get_settings
from app.db.models import (
    Document,
    DocumentChunk,
    EmailAttachment,
    EmailMessage,
    EmailThread,
    InvestigationRecord,
    Project,
)
from app.db.session import get_session_factory
from app.ingestion.storage import email_storage_dir, text_storage_dir
from app.main import app

NONEXISTENT_PROJECT_ID = 999_999


def _build_eml(**kwargs) -> bytes:
    msg = StdlibEmailMessage()
    for key, value in kwargs.pop("headers", {}).items():
        msg[key] = value
    body = kwargs.pop("body", "")
    msg.set_content(body)
    for attachment in kwargs.pop("attachments", []):
        msg.add_attachment(
            attachment["content"],
            maintype=attachment.get("maintype", "application"),
            subtype=attachment.get("subtype", "octet-stream"),
            filename=attachment["filename"],
        )
    return msg.as_bytes()


def _build_test_pdf(text: str) -> bytes:
    import fitz

    doc = fitz.open()
    doc.new_page().insert_text((50, 72), text, fontsize=11)
    return doc.tobytes()


def _build_test_docx(paragraphs: list[str]) -> bytes:
    import docx

    document = docx.Document()
    for text in paragraphs:
        document.add_paragraph(text)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _zip_of(entries: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        for name, content in entries.items():
            zf.writestr(name, content)
    return buffer.getvalue()


class EmailIngestionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.client.__enter__()  # runs the app's real lifespan (DB init)
        cls._created_project_ids: list[int] = []
        cls._created_investigation_ids: list = []

    @classmethod
    def tearDownClass(cls):
        with get_session_factory()() as session:
            # Investigation citations hold a plain (non-cascading) FK to
            # document_chunks/documents — delete any investigations we
            # created first so that constraint never blocks the cascade
            # below, exactly like the project/investigation cleanup this
            # phase's own manual validation needed (see citation
            # traceability test).
            for investigation_id in cls._created_investigation_ids:
                record = session.get(InvestigationRecord, investigation_id)
                if record is not None:
                    session.delete(record)
            session.commit()

            for project_id in cls._created_project_ids:
                documents = session.query(Document).filter(Document.project_id == project_id).all()
                for document in documents:
                    session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
                # EmailAttachment/EmailMessage/EmailThread all cascade from
                # Document/Project via ON DELETE CASCADE (see
                # app/db/models.py) — explicit here anyway, for the same
                # belt-and-suspenders clarity test_docx_ingestion.py uses
                # for DocumentChunk, not because cascade wouldn't do it.
                session.execute(delete(EmailAttachment).where(EmailAttachment.message_id.in_(select(Document.id).where(Document.project_id == project_id))))
                session.execute(delete(EmailMessage).where(EmailMessage.project_id == project_id))
                session.execute(delete(EmailThread).where(EmailThread.project_id == project_id))
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

    def _import(self, project_id: int, filename: str, content: bytes, content_type: str = "message/rfc822"):
        return self.client.post(
            f"/projects/{project_id}/emails/import",
            files={"files": (filename, io.BytesIO(content), content_type)},
        )

    # -- Parsing-through-the-API / application basics ----------------------

    def test_successful_project_scoped_import_creates_a_searchable_document(self):
        project_id = self._create_project("Email Test Project A")
        raw = _build_eml(
            headers={
                "Message-ID": "<app-a@example.com>",
                "From": "Jane <jane@example.com>",
                "Subject": "Application test",
                "Date": formatdate(),
            },
            body="Marker CLAIMTRACE-EMAIL-APP-TEST-1001 in the body.",
        )
        resp = self._import(project_id, "a.eml", raw)
        self.assertEqual(resp.status_code, 201, resp.text)
        body = resp.json()
        self.assertEqual(len(body["results"]), 1)
        result = body["results"][0]
        self.assertEqual(result["status"], "imported")
        self.assertIsNotNone(result["document_id"])

        with get_session_factory()() as session:
            document = session.get(Document, result["document_id"])
            self.assertEqual(document.status, "ready")
            self.assertEqual(document.doc_type, "EMAIL")
            chunks = session.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).all()
            marker_chunks = [c for c in chunks if "CLAIMTRACE-EMAIL-APP-TEST-1001" in c.chunk_text]
            self.assertEqual(len(marker_chunks), 1, "message body should be retrievable by its distinctive phrase")

    def test_import_to_nonexistent_project_returns_404(self):
        raw = _build_eml(headers={"Subject": "x", "From": "a@example.com", "Date": formatdate()}, body="x")
        resp = self._import(NONEXISTENT_PROJECT_ID, "x.eml", raw)
        self.assertEqual(resp.status_code, 404)

    def test_unsupported_extension_is_rejected_without_crashing_the_batch(self):
        project_id = self._create_project("Email Test Project B")
        resp = self.client.post(
            f"/projects/{project_id}/emails/import",
            files={"files": ("notes.txt", io.BytesIO(b"just text"), "text/plain")},
        )
        self.assertEqual(resp.status_code, 201)
        result = resp.json()["results"][0]
        self.assertEqual(result["status"], "rejected")
        self.assertIn("not a supported file type", result["error"])

    def test_malformed_eml_is_still_imported_with_whatever_signal_it_has(self):
        # Python's email parser is lenient by design (see
        # app/email_ingestion/parsing.py) — garbage .eml content with no
        # headers at all still becomes a persisted, honest record (empty
        # subject/sender, whatever text was found as the body), never a
        # crash and never silently dropped.
        project_id = self._create_project("Email Test Project C")
        resp = self._import(project_id, "garbage.eml", b"not a real email, just some bytes with CLAIMTRACE-GARBAGE-1 inside")
        self.assertEqual(resp.status_code, 201)
        result = resp.json()["results"][0]
        self.assertEqual(result["status"], "imported")

    def test_empty_eml_is_rejected_before_creating_a_document(self):
        project_id = self._create_project("Email Test Project D")
        resp = self._import(project_id, "empty.eml", b"")
        result = resp.json()["results"][0]
        self.assertEqual(result["status"], "rejected")
        self.assertIn("empty", result["error"])

    # -- Threading -----------------------------------------------------------

    def test_reply_chain_with_valid_headers_joins_one_thread(self):
        project_id = self._create_project("Email Test Project E")
        root = _build_eml(
            headers={"Message-ID": "<root-e@example.com>", "From": "a@example.com", "Subject": "Thread E", "Date": formatdate()},
            body="root",
        )
        reply = _build_eml(
            headers={
                "Message-ID": "<reply-e@example.com>",
                "In-Reply-To": "<root-e@example.com>",
                "References": "<root-e@example.com>",
                "From": "b@example.com",
                "Subject": "Re: Thread E",
                "Date": formatdate(),
            },
            body="reply",
        )
        r1 = self._import(project_id, "root.eml", root).json()["results"][0]
        r2 = self._import(project_id, "reply.eml", reply).json()["results"][0]
        self.assertEqual(r1["thread_id"], r2["thread_id"])

        threads = self.client.get(f"/projects/{project_id}/emails/threads").json()
        self.assertEqual(len(threads), 1)
        self.assertEqual(threads[0]["message_count"], 2)

    def test_messages_with_no_threading_headers_become_separate_threads(self):
        project_id = self._create_project("Email Test Project F")
        msg_a = _build_eml(headers={"Message-ID": "<f-a@example.com>", "From": "a@example.com", "Subject": "A", "Date": formatdate()}, body="a")
        msg_b = _build_eml(headers={"Message-ID": "<f-b@example.com>", "From": "a@example.com", "Subject": "B", "Date": formatdate()}, body="b")
        r1 = self._import(project_id, "a.eml", msg_a).json()["results"][0]
        r2 = self._import(project_id, "b.eml", msg_b).json()["results"][0]
        self.assertNotEqual(r1["thread_id"], r2["thread_id"])

    def test_same_subject_alone_does_not_merge_unrelated_messages(self):
        # Deliberate scope decision (see app/email_ingestion/threading.py):
        # subject matching alone must never create a thread relationship
        # the headers don't support.
        project_id = self._create_project("Email Test Project G")
        msg_a = _build_eml(
            headers={"Message-ID": "<g-a@example.com>", "From": "a@example.com", "Subject": "Weekly Progress Report", "Date": formatdate()},
            body="week 1",
        )
        msg_b = _build_eml(
            headers={"Message-ID": "<g-b@example.com>", "From": "b@example.com", "Subject": "Weekly Progress Report", "Date": formatdate()},
            body="week 2, unrelated sender, no threading headers",
        )
        r1 = self._import(project_id, "a.eml", msg_a).json()["results"][0]
        r2 = self._import(project_id, "b.eml", msg_b).json()["results"][0]
        self.assertNotEqual(r1["thread_id"], r2["thread_id"], "identical subject alone must not merge threads")

    def test_out_of_send_order_import_still_joins_the_correct_thread(self):
        # The reply is imported BEFORE its parent — threading must still
        # recognize the relationship once the parent arrives (see
        # app/email_ingestion/threading.py's bidirectional match).
        project_id = self._create_project("Email Test Project H")
        parent = _build_eml(
            headers={"Message-ID": "<h-parent@example.com>", "From": "a@example.com", "Subject": "H", "Date": formatdate()},
            body="parent",
        )
        child = _build_eml(
            headers={
                "Message-ID": "<h-child@example.com>",
                "In-Reply-To": "<h-parent@example.com>",
                "From": "b@example.com",
                "Subject": "Re: H",
                "Date": formatdate(),
            },
            body="child",
        )
        r_child = self._import(project_id, "child.eml", child).json()["results"][0]
        r_parent = self._import(project_id, "parent.eml", parent).json()["results"][0]
        self.assertEqual(r_child["thread_id"], r_parent["thread_id"])

        threads = self.client.get(f"/projects/{project_id}/emails/threads").json()
        self.assertEqual(len(threads), 1)
        self.assertEqual(threads[0]["message_count"], 2)

    # -- Deduplication / import retry -----------------------------------

    def test_duplicate_import_by_message_id_is_not_silently_duplicated(self):
        project_id = self._create_project("Email Test Project I")
        raw = _build_eml(headers={"Message-ID": "<dup-i@example.com>", "From": "a@example.com", "Subject": "Dup", "Date": formatdate()}, body="x")
        r1 = self._import(project_id, "a.eml", raw).json()["results"][0]
        r2 = self._import(project_id, "a.eml", raw).json()["results"][0]
        self.assertEqual(r1["status"], "imported")
        self.assertEqual(r2["status"], "duplicate")
        self.assertEqual(r1["document_id"], r2["document_id"])

        threads = self.client.get(f"/projects/{project_id}/emails/threads").json()
        self.assertEqual(threads[0]["message_count"], 1, "a duplicate import must not create a second message")

    def test_duplicate_import_without_message_id_falls_back_to_content_hash(self):
        project_id = self._create_project("Email Test Project J")
        raw = _build_eml(headers={"From": "a@example.com", "Subject": "No id", "Date": "Tue, 03 Feb 2026 09:15:00 +0000"}, body="identical content")
        r1 = self._import(project_id, "a.eml", raw).json()["results"][0]
        r2 = self._import(project_id, "a.eml", raw).json()["results"][0]
        self.assertEqual(r1["status"], "imported")
        self.assertEqual(r2["status"], "duplicate")

    def test_overlapping_eml_files_in_one_batch_do_not_double_import(self):
        project_id = self._create_project("Email Test Project K")
        raw = _build_eml(headers={"Message-ID": "<overlap-k@example.com>", "From": "a@example.com", "Subject": "K", "Date": formatdate()}, body="x")
        resp = self.client.post(
            f"/projects/{project_id}/emails/import",
            files=[
                ("files", ("copy1.eml", io.BytesIO(raw), "message/rfc822")),
                ("files", ("copy2.eml", io.BytesIO(raw), "message/rfc822")),
            ],
        )
        results = resp.json()["results"]
        statuses = sorted(r["status"] for r in results)
        self.assertEqual(statuses, ["duplicate", "imported"])

    # -- Attachments -------------------------------------------------------

    def test_pdf_attachment_becomes_a_real_indexed_document(self):
        project_id = self._create_project("Email Test Project L")
        pdf_bytes = _build_test_pdf("Attachment marker CLAIMTRACE-EMAIL-PDF-ATTACH-2001.")
        raw = _build_eml(
            headers={"Message-ID": "<l-msg@example.com>", "From": "a@example.com", "Subject": "PDF attach", "Date": formatdate()},
            body="see attached",
            attachments=[{"filename": "notice.pdf", "content": pdf_bytes, "maintype": "application", "subtype": "pdf"}],
        )
        result = self._import(project_id, "l.eml", raw).json()["results"][0]
        message = self.client.get(f"/projects/{project_id}/emails/messages/{result['document_id']}").json()
        self.assertEqual(len(message["attachments"]), 1)
        attachment = message["attachments"][0]
        self.assertEqual(attachment["status"], "processed")
        self.assertIsNotNone(attachment["document_id"])

        with get_session_factory()() as session:
            doc = session.get(Document, attachment["document_id"])
            self.assertEqual(doc.status, "ready")
            chunks = session.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).all()
            self.assertTrue(any("CLAIMTRACE-EMAIL-PDF-ATTACH-2001" in c.chunk_text for c in chunks))

        # The attachment is viewable through the EXISTING, unmodified file
        # endpoint — no special-casing needed for an email-sourced PDF.
        file_resp = self.client.get(f"/projects/{project_id}/documents/{attachment['document_id']}/file")
        self.assertEqual(file_resp.status_code, 200)
        self.assertEqual(file_resp.headers["content-type"], "application/pdf")

    def test_an_attachment_document_carries_its_covering_email_as_email_source(self):
        """GET /projects/{id}/documents (and the single-document lookup)
        enrich an attachment's own Document row with which email it came
        from — reusing the existing EmailAttachment.message_id link, never
        a new relationship. The covering email's own Document (doc_type
        'EMAIL') and any ordinary, non-email document must NOT carry this
        field, so the frontend can reliably distinguish 'this document IS
        an attachment' from 'this document is something else'."""
        project_id = self._create_project("Email Test Project M")
        pdf_bytes = _build_test_pdf("Attachment marker CLAIMTRACE-EMAIL-SOURCE-3001.")
        raw = _build_eml(
            headers={"Message-ID": "<m-msg@example.com>", "From": "a@example.com", "Subject": "Email source test", "Date": formatdate()},
            body="see attached",
            attachments=[{"filename": "notice.pdf", "content": pdf_bytes, "maintype": "application", "subtype": "pdf"}],
        )
        result = self._import(project_id, "m.eml", raw).json()["results"][0]
        message = self.client.get(f"/projects/{project_id}/emails/messages/{result['document_id']}").json()
        attachment_document_id = message["attachments"][0]["document_id"]

        docs = {d["id"]: d for d in self.client.get(f"/projects/{project_id}/documents").json()}

        attachment_doc = docs[attachment_document_id]
        self.assertIsNotNone(attachment_doc["email_source"])
        self.assertEqual(attachment_doc["email_source"]["subject"], "Email source test")
        self.assertEqual(attachment_doc["email_source"]["message_document_id"], result["document_id"])

        email_body_doc = docs[result["document_id"]]
        self.assertIsNone(email_body_doc["email_source"])

        single_resp = self.client.get(f"/projects/{project_id}/documents/{attachment_document_id}").json()
        self.assertEqual(single_resp["email_source"]["subject"], "Email source test")

    def test_docx_attachment_becomes_a_real_indexed_document(self):
        project_id = self._create_project("Email Test Project M")
        docx_bytes = _build_test_docx(["Attachment marker CLAIMTRACE-EMAIL-DOCX-ATTACH-2002."])
        raw = _build_eml(
            headers={"Message-ID": "<m-msg@example.com>", "From": "a@example.com", "Subject": "DOCX attach", "Date": formatdate()},
            body="see attached",
            attachments=[{
                "filename": "memo.docx",
                "content": docx_bytes,
                "maintype": "application",
                "subtype": "vnd.openxmlformats-officedocument.wordprocessingml.document",
            }],
        )
        result = self._import(project_id, "m.eml", raw).json()["results"][0]
        message = self.client.get(f"/projects/{project_id}/emails/messages/{result['document_id']}").json()
        attachment = message["attachments"][0]
        self.assertEqual(attachment["status"], "processed")
        with get_session_factory()() as session:
            doc = session.get(Document, attachment["document_id"])
            self.assertEqual(doc.status, "ready")

    def test_unsupported_attachment_format_is_marked_not_pretended_processed(self):
        project_id = self._create_project("Email Test Project N")
        raw = _build_eml(
            headers={"Message-ID": "<n-msg@example.com>", "From": "a@example.com", "Subject": "Image attach", "Date": formatdate()},
            body="see attached",
            attachments=[{"filename": "site-photo.jpg", "content": b"\xff\xd8\xff fake jpeg bytes", "maintype": "image", "subtype": "jpeg"}],
        )
        result = self._import(project_id, "n.eml", raw).json()["results"][0]
        message = self.client.get(f"/projects/{project_id}/emails/messages/{result['document_id']}").json()
        attachment = message["attachments"][0]
        self.assertEqual(attachment["status"], "unsupported_format")
        self.assertIsNone(attachment["document_id"])
        self.assertEqual(attachment["filename"], "site-photo.jpg")

    def test_empty_attachment_is_rejected_not_silently_dropped(self):
        project_id = self._create_project("Email Test Project O")
        raw = _build_eml(
            headers={"Message-ID": "<o-msg@example.com>", "From": "a@example.com", "Subject": "Empty attach", "Date": formatdate()},
            body="see attached",
            attachments=[{"filename": "empty.pdf", "content": b"", "maintype": "application", "subtype": "pdf"}],
        )
        result = self._import(project_id, "o.eml", raw).json()["results"][0]
        message = self.client.get(f"/projects/{project_id}/emails/messages/{result['document_id']}").json()
        attachment = message["attachments"][0]
        self.assertEqual(attachment["status"], "rejected")
        self.assertIsNone(attachment["document_id"])

    def test_malformed_pdf_attachment_is_persisted_as_failed_not_dropped(self):
        project_id = self._create_project("Email Test Project P")
        raw = _build_eml(
            headers={"Message-ID": "<p-msg@example.com>", "From": "a@example.com", "Subject": "Corrupt attach", "Date": formatdate()},
            body="see attached",
            attachments=[{"filename": "corrupt.pdf", "content": b"this is not a real pdf", "maintype": "application", "subtype": "pdf"}],
        )
        result = self._import(project_id, "p.eml", raw).json()["results"][0]
        message = self.client.get(f"/projects/{project_id}/emails/messages/{result['document_id']}").json()
        attachment = message["attachments"][0]
        self.assertEqual(attachment["status"], "failed")
        self.assertIsNotNone(attachment["document_id"])  # a real, visible, failed Document — not dropped

    def test_attachment_parent_message_linkage_is_correct(self):
        project_id = self._create_project("Email Test Project Q")
        pdf_bytes = _build_test_pdf("linkage check")
        raw = _build_eml(
            headers={"Message-ID": "<q-msg@example.com>", "From": "a@example.com", "Subject": "Linkage", "Date": formatdate()},
            body="see attached",
            attachments=[{"filename": "x.pdf", "content": pdf_bytes, "maintype": "application", "subtype": "pdf"}],
        )
        result = self._import(project_id, "q.eml", raw).json()["results"][0]
        with get_session_factory()() as session:
            attachments = session.query(EmailAttachment).filter(EmailAttachment.message_id == result["document_id"]).all()
            self.assertEqual(len(attachments), 1)
            self.assertEqual(attachments[0].message_id, result["document_id"])

    # -- ZIP import ----------------------------------------------------------

    def test_zip_of_eml_files_imports_each_message(self):
        project_id = self._create_project("Email Test Project R")
        msg1 = _build_eml(headers={"Message-ID": "<r1@example.com>", "From": "a@example.com", "Subject": "R1", "Date": formatdate()}, body="one")
        msg2 = _build_eml(headers={"Message-ID": "<r2@example.com>", "From": "a@example.com", "Subject": "R2", "Date": formatdate()}, body="two")
        archive = _zip_of({"thread/msg1.eml": msg1, "thread/msg2.eml": msg2, "readme.txt": b"not an eml, should be skipped silently"})
        resp = self.client.post(
            f"/projects/{project_id}/emails/import",
            files={"files": ("batch.zip", io.BytesIO(archive), "application/zip")},
        )
        self.assertEqual(resp.status_code, 201)
        results = resp.json()["results"]
        imported = [r for r in results if r["status"] == "imported"]
        self.assertEqual(len(imported), 2)

    def test_zip_path_traversal_entry_is_rejected(self):
        project_id = self._create_project("Email Test Project S")
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as zf:
            zf.writestr("../../etc/evil.eml", b"Subject: evil\r\n\r\nbody")
        resp = self.client.post(
            f"/projects/{project_id}/emails/import",
            files={"files": ("evil.zip", io.BytesIO(buffer.getvalue()), "application/zip")},
        )
        self.assertEqual(resp.status_code, 201)
        results = resp.json()["results"]
        self.assertTrue(all(r["status"] == "rejected" for r in results))
        self.assertIn("unsafe path", results[0]["error"])

    def test_invalid_zip_archive_is_rejected_with_a_clean_error(self):
        project_id = self._create_project("Email Test Project T")
        resp = self.client.post(
            f"/projects/{project_id}/emails/import",
            files={"files": ("notazip.zip", io.BytesIO(b"this is not a zip file at all"), "application/zip")},
        )
        self.assertEqual(resp.status_code, 201)
        result = resp.json()["results"][0]
        self.assertEqual(result["status"], "rejected")
        self.assertNotIn("Traceback", result["error"])

    # -- Project isolation (critical) ---------------------------------------

    def test_email_message_from_one_project_not_retrievable_via_another(self):
        project_a = self._create_project("Email Test Project U")
        project_b = self._create_project("Email Test Project V")
        raw = _build_eml(headers={"Message-ID": "<u-msg@example.com>", "From": "a@example.com", "Subject": "Isolation", "Date": formatdate()}, body="x")
        result = self._import(project_a, "u.eml", raw).json()["results"][0]

        cross_resp = self.client.get(f"/projects/{project_b}/emails/messages/{result['document_id']}")
        self.assertEqual(cross_resp.status_code, 404)

        own_resp = self.client.get(f"/projects/{project_a}/emails/messages/{result['document_id']}")
        self.assertEqual(own_resp.status_code, 200)

        threads_b = self.client.get(f"/projects/{project_b}/emails/threads").json()
        self.assertEqual(threads_b, [])

    def test_thread_from_one_project_not_retrievable_via_another(self):
        project_a = self._create_project("Email Test Project W")
        project_b = self._create_project("Email Test Project X")
        raw = _build_eml(headers={"Message-ID": "<w-msg@example.com>", "From": "a@example.com", "Subject": "Thread isolation", "Date": formatdate()}, body="x")
        result = self._import(project_a, "w.eml", raw).json()["results"][0]

        cross_resp = self.client.get(f"/projects/{project_b}/emails/threads/{result['thread_id']}")
        self.assertEqual(cross_resp.status_code, 404)

    # -- Citation traceability (the one real-Gemini test in this file) ------

    def test_citation_traces_back_to_the_exact_email_message(self):
        project_id = self._create_project("Email Test Project Y")
        raw = _build_eml(
            headers={"Message-ID": "<y-msg@example.com>", "From": "Jane <jane@example.com>", "Subject": "Citation trace", "Date": formatdate()},
            body="The unique verification phrase is CLAIMTRACE-EMAIL-CITATION-TRACE-3003.",
        )
        import_result = self._import(project_id, "y.eml", raw).json()["results"][0]
        self.assertEqual(import_result["status"], "imported")

        inv_resp = self.client.post(
            f"/projects/{project_id}/investigations",
            json={"query": "What is the unique verification phrase CLAIMTRACE-EMAIL-CITATION-TRACE-3003?"},
        )
        self.assertEqual(inv_resp.status_code, 201, inv_resp.text)
        record = inv_resp.json()
        self.__class__._created_investigation_ids.append(record["id"])
        self.assertEqual(record["status"], "completed")

        email_citations = [c for c in record["citations"] if c["document_id"] == import_result["document_id"]]
        self.assertTrue(
            len(email_citations) > 0,
            "the investigation's citations should include the email message that contains the exact phrase asked about",
        )

        # Trace the citation back to its message via the SAME document_id —
        # no second lookup table needed (see app/api/routes/project_emails.py).
        message = self.client.get(f"/projects/{project_id}/emails/messages/{email_citations[0]['document_id']}")
        self.assertEqual(message.status_code, 200)
        self.assertEqual(message.json()["subject"], "Citation trace")
        self.assertEqual(message.json()["sender_email"], "jane@example.com")

        # And the document register / existing Document endpoints agree
        # it's the same, real, email-typed document.
        doc_resp = self.client.get(f"/projects/{project_id}/documents/{email_citations[0]['document_id']}")
        self.assertEqual(doc_resp.json()["doc_type"], "EMAIL")

    # -- Pre-commit review regression: threading substring collision ------

    def test_threading_does_not_merge_via_message_id_substring_collision(self):
        # Reproduces a confirmed bug: a plain substring match (not a
        # word-boundary match) against the stored in_reply_to/references
        # text let one message's Message-ID, which happened to be a
        # literal substring of an unrelated message's Message-ID, merge
        # two unrelated conversations into one thread. See
        # app/email_ingestion/threading.py's Direction 2 comment.
        project_id = self._create_project("Email Test Project Z1")
        m1 = _build_eml(
            headers={"Message-ID": "<942@mail.example.com>", "From": "a@example.com", "Subject": "Unrelated topic A", "Date": formatdate()},
            body="unrelated content",
        )
        m2 = _build_eml(
            headers={
                "Message-ID": "<reply-to-942@mail.example.com>",
                "In-Reply-To": "<942@mail.example.com>",
                "From": "a@example.com",
                "Subject": "Re: Unrelated topic A",
                "Date": formatdate(),
            },
            body="real reply",
        )
        # m3's own Message-ID ("42@mail.example.com") is a literal substring
        # of m1's ("942@mail.example.com") and, transitively, of m2's stored
        # in_reply_to — but m3 has no threading headers at all and must not
        # join m1/m2's thread.
        m3 = _build_eml(
            headers={"Message-ID": "<42@mail.example.com>", "From": "a@example.com", "Subject": "Completely different topic B", "Date": formatdate()},
            body="totally unrelated content",
        )
        self._import(project_id, "m1.eml", m1)
        self._import(project_id, "m2.eml", m2)
        r3 = self._import(project_id, "m3.eml", m3).json()["results"][0]

        threads = self.client.get(f"/projects/{project_id}/emails/threads").json()
        self.assertEqual(len(threads), 2, "the unrelated message must not be merged via substring collision")
        thread_with_m3 = next(t for t in threads if t["id"] == r3["thread_id"])
        self.assertEqual(thread_with_m3["message_count"], 1)


class EmailConcurrentImportTests(unittest.TestCase):
    """Pre-commit review regression: concurrent imports of the exact same
    message (racing past the application-level dedup pre-check) must never
    leave more than one real Document/EmailMessage behind.

    Drives this through real concurrent HTTP requests (ThreadPoolExecutor +
    TestClient), the same shape as the live reproduction run against the
    actual dev server during review — each request gets its own DB session
    via the app's normal Depends(get_db), exercising the real database-level
    race. (An earlier version of this test called ingest_email_bytes()
    directly from raw Python threads sharing one in-process embedding model
    instance; that triggered unrelated contention in the underlying
    ML-inference library's own thread handling, not anything in the code
    under test, so it was replaced with this HTTP-level form.)"""

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
                session.execute(delete(EmailMessage).where(EmailMessage.project_id == project_id))
                session.execute(delete(EmailThread).where(EmailThread.project_id == project_id))
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

    def _concurrent_import(self, project_id: int, raw: bytes, workers: int = 5) -> list:
        def _one(i: int):
            resp = self.client.post(
                f"/projects/{project_id}/emails/import",
                files={"files": (f"race-{i}.eml", io.BytesIO(raw), "message/rfc822")},
            )
            if resp.status_code != 201:
                return f"HTTP_{resp.status_code}"
            return resp.json()["results"][0]["status"]

        with ThreadPoolExecutor(max_workers=workers) as pool:
            return list(pool.map(_one, range(workers)))

    def test_concurrent_import_with_message_id_never_orphans_a_document(self):
        project_id = self._create_project("Email Concurrency Test A")
        raw = _build_eml(
            headers={"Message-ID": "<concurrent-a@example.com>", "From": "a@example.com", "Subject": "Race A", "Date": formatdate()},
            body="race marker A",
        )
        statuses = self._concurrent_import(project_id, raw)
        self.assertEqual(statuses.count("imported"), 1, statuses)
        self.assertEqual(statuses.count("duplicate"), len(statuses) - 1, statuses)

        docs = self.client.get(f"/projects/{project_id}/documents").json()
        email_docs = [d for d in docs if d["doc_type"] == "EMAIL"]
        self.assertEqual(len(email_docs), 1, "a concurrent race must never leave more than one Document behind")

    def test_concurrent_import_without_message_id_never_orphans_a_document(self):
        project_id = self._create_project("Email Concurrency Test B")
        raw = _build_eml(
            headers={"From": "a@example.com", "Subject": "Race B (no message id)", "Date": "Tue, 03 Feb 2026 09:15:00 +0000"},
            body="race marker B, identical content every time",
        )
        statuses = self._concurrent_import(project_id, raw)
        self.assertEqual(statuses.count("imported"), 1, statuses)
        self.assertEqual(statuses.count("duplicate"), len(statuses) - 1, statuses)

        docs = self.client.get(f"/projects/{project_id}/documents").json()
        email_docs = [d for d in docs if d["doc_type"] == "EMAIL"]
        self.assertEqual(len(email_docs), 1, "a concurrent race must never leave more than one Document behind")

    def test_concurrent_import_race_cleans_up_the_discarded_duplicates_files(self):
        """Code review fix regression: the IntegrityError recovery path in
        ingest_email_bytes() deletes the losing duplicate's Document row,
        but previously left its on-disk .eml and extracted-text files
        behind. Drives the same real concurrent race as the tests above,
        then checks the filesystem directly: exactly one .eml and one
        extracted-text file must remain for this project -- never one per
        losing thread, and never zero (the winner's own files must still
        be intact)."""
        project_id = self._create_project("Email Concurrency Test C (file cleanup)")
        raw = _build_eml(
            headers={"From": "a@example.com", "Subject": "Race C (file cleanup)", "Date": "Tue, 03 Feb 2026 09:15:00 +0000"},
            body="race marker C, identical content every time, checked against disk",
        )
        statuses = self._concurrent_import(project_id, raw, workers=5)
        self.assertEqual(statuses.count("imported"), 1, statuses)

        settings = get_settings()
        eml_files = list(email_storage_dir(settings.storage_root, project_id).iterdir())
        text_files = list(text_storage_dir(settings.storage_root, project_id).iterdir())
        self.assertEqual(len(eml_files), 1, f"expected exactly one surviving .eml file, found {eml_files}")
        self.assertEqual(len(text_files), 1, f"expected exactly one surviving extracted-text file, found {text_files}")


if __name__ == "__main__":
    unittest.main()
