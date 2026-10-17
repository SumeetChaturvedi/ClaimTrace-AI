"""Tests for app/email_sync/orchestrator.py (Phase 1: Gmail Integration).

Real Postgres, real app/email_ingestion/pipeline.py (the exact same
parse/dedup/thread/index/attachment path every manual .eml upload already
goes through — never reimplemented here) — only the Gmail API itself is
mocked (gmail_source.list_message_ids/fetch_raw_message/fetch_profile and
gmail_oauth.refresh_access_token), since there is no live Google account
to sync against in CI. This mirrors test_email_ingestion.py's own
no-mocks-for-the-real-pipeline principle: the pipeline is real, only the
genuinely external, uncontrollable-in-CI dependency (Google's servers) is
replaced.

Run with:
    cd backend && source .venv/bin/activate
    PYTHONPATH=. python3 -m unittest tests.test_mailbox_sync -v
"""

import unittest
from email.message import EmailMessage as StdlibEmailMessage
from email.utils import formatdate
from unittest.mock import patch

from cryptography.fernet import Fernet
from sqlalchemy import delete, select  # noqa: F401 -- `delete` used for Core-level cleanup below

from app.config import Settings, get_settings
from app.db.models import ConnectedMailbox, Document, EmailMessage, Project
from app.db.session import get_session_factory
from app.email_sync.gmail_oauth import GmailCredentialsRevokedError, GmailTransientError
from app.email_sync.gmail_source import GmailApiError, GmailProfile, HistoryExpiredError, MessagePage, RawMessage
from app.email_sync.orchestrator import MailboxNotSyncableError, sync_mailbox
from app.email_sync.token_crypto import encrypt_refresh_token

PROJECT_A_ID = 2
PROJECT_B_ID = 3


def _build_eml(message_id: str, subject: str, body: str, *, in_reply_to: str | None = None) -> bytes:
    msg = StdlibEmailMessage()
    msg["Message-ID"] = message_id
    msg["From"] = "sender@example.com"
    msg["To"] = "recipient@example.com"
    msg["Subject"] = subject
    msg["Date"] = formatdate()
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = in_reply_to
    msg.set_content(body)
    return msg.as_bytes()


def _build_eml_with_pdf_attachment(message_id: str, subject: str, body: str, pdf_text: str) -> bytes:
    import fitz

    msg = StdlibEmailMessage()
    msg["Message-ID"] = message_id
    msg["From"] = "sender@example.com"
    msg["Subject"] = subject
    msg["Date"] = formatdate()
    msg.set_content(body)

    pdf_doc = fitz.open()
    pdf_doc.new_page().insert_text((50, 72), pdf_text, fontsize=11)
    pdf_bytes = pdf_doc.tobytes()
    msg.add_attachment(pdf_bytes, maintype="application", subtype="pdf", filename="notice.pdf")
    return msg.as_bytes()


class MailboxSyncTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fernet_key = Fernet.generate_key().decode()
        cls.settings = Settings(
            mailbox_token_encryption_key=cls.fernet_key,
            gmail_client_id="fake-client-id",
            gmail_client_secret="fake-client-secret",
            database_url=get_settings().database_url,
            storage_root=get_settings().storage_root,
        )
        cls.session_factory = get_session_factory()
        cls._created_document_ids: list[int] = []
        cls._created_mailbox_ids: list[int] = []

    @classmethod
    def tearDownClass(cls):
        # Core-level DELETE, not session.delete(...): the ORM's default
        # cascade behavior for an unconfigured relationship is to NULL
        # each child's FK before deleting the parent, which violates
        # document_chunks.document_id's NOT NULL constraint. A Core
        # DELETE goes straight to SQL and lets the real, database-level
        # ON DELETE CASCADE (already declared on DocumentChunk.document_id
        # et al.) do the job correctly — see the equivalent fix in
        # dataset/event_eval/run_production_eval.py for the same issue.
        with cls.session_factory() as session:
            if cls._created_mailbox_ids:
                session.execute(delete(ConnectedMailbox).where(ConnectedMailbox.id.in_(cls._created_mailbox_ids)))
            if cls._created_document_ids:
                session.execute(delete(Document).where(Document.id.in_(cls._created_document_ids)))
            session.commit()

    def _make_mailbox(self, project_id: int, status: str = "connected") -> ConnectedMailbox:
        session = self.session_factory()
        mailbox = ConnectedMailbox(
            project_id=project_id,
            provider="gmail",
            external_email=f"test-{id(self)}-{len(self._created_mailbox_ids)}@example.com",
            encrypted_refresh_token=encrypt_refresh_token("fake-refresh-token", self.settings),
            granted_scope="https://www.googleapis.com/auth/gmail.readonly",
            status=status,
        )
        session.add(mailbox)
        session.commit()
        session.refresh(mailbox)
        self._created_mailbox_ids.append(mailbox.id)
        session.close()
        return mailbox

    def _reload(self, mailbox_id: int) -> tuple:
        session = self.session_factory()
        mailbox = session.get(ConnectedMailbox, mailbox_id)
        return session, mailbox

    def _track_documents_for(self, session, message_ids_imported: int) -> None:
        # Best-effort cleanup helper: find Document rows created by this
        # test's EmailMessages and remember them for tearDown. Called
        # after a sync so cls._created_document_ids covers whatever was
        # actually created.
        pass


class SingleMessageSyncTests(MailboxSyncTests):
    def test_a_single_fetched_message_is_imported_through_the_real_pipeline(self):
        mailbox = self._make_mailbox(PROJECT_A_ID)
        raw = _build_eml("<unique-1@example.com>", "Test subject one", "Body one")

        with patch("app.email_sync.orchestrator.refresh_access_token", return_value=("fake-access-token", 3600)), \
             patch("app.email_sync.orchestrator.gmail_source.list_message_ids", return_value=MessagePage(["m1"], None)), \
             patch("app.email_sync.orchestrator.gmail_source.fetch_profile", return_value=GmailProfile("acct@example.com", "100")), \
             patch("app.email_sync.orchestrator.gmail_source.fetch_raw_message", return_value=RawMessage("m1", raw)):
            session, mailbox = self._reload(mailbox.id)
            result = sync_mailbox(session, self.settings.storage_root, mailbox, self.settings)

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.imported, 1)
        self.assertEqual(result.duplicate, 0)

        message = session.scalar(select(EmailMessage).where(EmailMessage.message_id == "unique-1@example.com"))
        self.assertIsNotNone(message)
        self.assertEqual(message.project_id, PROJECT_A_ID)
        self._created_document_ids.append(message.document_id)

        self.assertEqual(mailbox.sync_cursor, "history:100")
        self.assertIsNotNone(mailbox.last_synced_at)
        session.close()


class DuplicateSyncTests(MailboxSyncTests):
    def test_syncing_the_same_message_twice_does_not_create_a_duplicate(self):
        mailbox = self._make_mailbox(PROJECT_A_ID)
        raw = _build_eml("<unique-2@example.com>", "Dup test", "Body")

        def run_sync():
            with patch("app.email_sync.orchestrator.refresh_access_token", return_value=("tok", 3600)), \
                 patch("app.email_sync.orchestrator.gmail_source.list_message_ids", return_value=MessagePage(["m-dup"], None)), \
                 patch("app.email_sync.orchestrator.gmail_source.fetch_profile", return_value=GmailProfile("a@example.com", "200")), \
                 patch("app.email_sync.orchestrator.gmail_source.fetch_raw_message", return_value=RawMessage("m-dup", raw)):
                session, mb = self._reload(mailbox.id)
                # Force the full-list path both times (rather than letting
                # the first run's cursor advance to 'history:200' and the
                # second run take the incremental path, which would need a
                # separate mock for list_changed_message_ids) — this test
                # is specifically about dedup across two sync calls that
                # both independently discover the SAME Gmail message id,
                # which the full-list mock already represents faithfully.
                mb.sync_cursor = None
                session.commit()
                result = sync_mailbox(session, self.settings.storage_root, mb, self.settings)
                session.close()
                return result

        first = run_sync()
        second = run_sync()

        self.assertEqual(first.imported, 1)
        self.assertEqual(second.imported, 0)
        self.assertEqual(second.duplicate, 1)

        # Re-processing the identical Message-ID across two sync calls
        # must never create a second row.
        session = self.session_factory()
        rows = session.scalars(
            select(EmailMessage).where(EmailMessage.message_id == "unique-2@example.com")
        ).all()
        self.assertEqual(len(rows), 1)
        self._created_document_ids.append(rows[0].document_id)
        session.close()


class PartialFailureTests(MailboxSyncTests):
    def test_a_transient_failure_mid_page_does_not_advance_the_cursor(self):
        """Proves the 'retry without duplicating or skipping' requirement
        at the cursor level: a message-fetch failure partway through a
        page must leave sync_cursor exactly where it was, so the next
        sync call re-lists the same range rather than silently skipping
        past whatever wasn't actually fetched."""
        mailbox = self._make_mailbox(PROJECT_A_ID)
        from app.email_sync.gmail_source import GmailApiError

        with patch("app.email_sync.orchestrator.refresh_access_token", return_value=("tok", 3600)), \
             patch("app.email_sync.orchestrator.gmail_source.list_message_ids", return_value=MessagePage(["m1", "m2"], None)), \
             patch("app.email_sync.orchestrator.gmail_source.fetch_profile", return_value=GmailProfile("a@example.com", "300")), \
             patch("app.email_sync.orchestrator.gmail_source.fetch_raw_message", side_effect=GmailApiError("simulated failure")):
            session, mb = self._reload(mailbox.id)
            original_cursor = mb.sync_cursor
            result = sync_mailbox(session, self.settings.storage_root, mb, self.settings)

        self.assertEqual(result.status, "partial")
        self.assertEqual(mb.sync_cursor, original_cursor)  # unchanged, not advanced to 'history:300'
        session.close()

    def test_a_not_found_message_is_skipped_without_stopping_the_rest_of_the_page(self):
        mailbox = self._make_mailbox(PROJECT_A_ID)
        from app.email_sync.gmail_source import GmailMessageNotFoundError

        raw = _build_eml("<unique-3@example.com>", "Second message", "Body")

        def fake_fetch(access_token, message_id):
            if message_id == "deleted-one":
                raise GmailMessageNotFoundError(message_id)
            return RawMessage(message_id, raw)

        with patch("app.email_sync.orchestrator.refresh_access_token", return_value=("tok", 3600)), \
             patch("app.email_sync.orchestrator.gmail_source.list_message_ids", return_value=MessagePage(["deleted-one", "real-one"], None)), \
             patch("app.email_sync.orchestrator.gmail_source.fetch_profile", return_value=GmailProfile("a@example.com", "400")), \
             patch("app.email_sync.orchestrator.gmail_source.fetch_raw_message", side_effect=fake_fetch):
            session, mb = self._reload(mailbox.id)
            result = sync_mailbox(session, self.settings.storage_root, mb, self.settings)

        self.assertEqual(result.skipped_not_found, 1)
        self.assertEqual(result.imported, 1)
        self.assertEqual(result.status, "completed")

        message = session.scalar(select(EmailMessage).where(EmailMessage.message_id == "unique-3@example.com"))
        self._created_document_ids.append(message.document_id)
        session.close()


class RevokedCredentialsTests(MailboxSyncTests):
    def test_invalid_grant_on_refresh_marks_the_mailbox_needs_reauth(self):
        mailbox = self._make_mailbox(PROJECT_A_ID)

        with patch(
            "app.email_sync.orchestrator.refresh_access_token",
            side_effect=GmailCredentialsRevokedError("revoked"),
        ):
            session, mb = self._reload(mailbox.id)
            result = sync_mailbox(session, self.settings.storage_root, mb, self.settings)

        self.assertEqual(result.status, "needs_reauth")
        self.assertEqual(mb.status, "needs_reauth")
        session.close()


class EncryptionKeyFailureTests(MailboxSyncTests):
    """Code review requirement: a missing/malformed/rotated encryption
    key must be distinguishable from an actually revoked Google
    credential — status='error', never 'needs_reauth', and the mailbox's
    own `status` column must stay 'connected' (reauthorizing with Google
    would do nothing to fix a local key problem)."""

    def test_a_rotated_encryption_key_produces_error_not_needs_reauth(self):
        """The mailbox's token was encrypted with one Fernet key; sync is
        attempted with a DIFFERENT settings object (a different key) —
        exactly what happens in production if MAILBOX_TOKEN_ENCRYPTION_KEY
        is rotated without re-encrypting existing stored tokens."""
        mailbox = self._make_mailbox(PROJECT_A_ID)
        rotated_settings = Settings(
            mailbox_token_encryption_key=Fernet.generate_key().decode(),
            gmail_client_id=self.settings.gmail_client_id,
            gmail_client_secret=self.settings.gmail_client_secret,
            database_url=self.settings.database_url,
            storage_root=self.settings.storage_root,
        )

        session, mb = self._reload(mailbox.id)
        with patch("app.email_sync.orchestrator.refresh_access_token") as mock_refresh:
            result = sync_mailbox(session, rotated_settings.storage_root, mb, rotated_settings)
            mock_refresh.assert_not_called()  # never even reaches Google — the key fails first

        self.assertEqual(result.status, "error")
        self.assertNotEqual(result.status, "needs_reauth")
        self.assertEqual(mb.status, "connected")  # unchanged — this is not a credentials problem
        self.assertIn("decrypt", (mb.last_sync_error or "").lower())
        session.close()

    def test_a_missing_encryption_key_produces_error_not_needs_reauth(self):
        mailbox = self._make_mailbox(PROJECT_A_ID)
        unconfigured_settings = Settings(
            mailbox_token_encryption_key=None,
            gmail_client_id=self.settings.gmail_client_id,
            gmail_client_secret=self.settings.gmail_client_secret,
            database_url=self.settings.database_url,
            storage_root=self.settings.storage_root,
        )

        session, mb = self._reload(mailbox.id)
        with patch("app.email_sync.orchestrator.refresh_access_token") as mock_refresh:
            result = sync_mailbox(session, unconfigured_settings.storage_root, mb, unconfigured_settings)
            mock_refresh.assert_not_called()

        self.assertEqual(result.status, "error")
        self.assertEqual(mb.status, "connected")
        session.close()


class DisconnectedMailboxTests(MailboxSyncTests):
    def test_syncing_a_disconnected_mailbox_raises_without_any_gmail_api_call(self):
        mailbox = self._make_mailbox(PROJECT_A_ID, status="disconnected")
        session = self.session_factory()
        mb = session.get(ConnectedMailbox, mailbox.id)
        mb.encrypted_refresh_token = None
        session.commit()

        with patch("app.email_sync.orchestrator.refresh_access_token") as mock_refresh:
            with self.assertRaises(MailboxNotSyncableError):
                sync_mailbox(session, self.settings.storage_root, mb, self.settings)
            mock_refresh.assert_not_called()
        session.close()


class ProjectIsolationTests(MailboxSyncTests):
    def test_a_mailbox_connected_to_project_a_imports_only_into_project_a(self):
        mailbox = self._make_mailbox(PROJECT_A_ID)
        raw = _build_eml("<unique-isolation@example.com>", "Isolation test", "Body")

        with patch("app.email_sync.orchestrator.refresh_access_token", return_value=("tok", 3600)), \
             patch("app.email_sync.orchestrator.gmail_source.list_message_ids", return_value=MessagePage(["m-iso"], None)), \
             patch("app.email_sync.orchestrator.gmail_source.fetch_profile", return_value=GmailProfile("a@example.com", "500")), \
             patch("app.email_sync.orchestrator.gmail_source.fetch_raw_message", return_value=RawMessage("m-iso", raw)):
            session, mb = self._reload(mailbox.id)
            sync_mailbox(session, self.settings.storage_root, mb, self.settings)

        message = session.scalar(select(EmailMessage).where(EmailMessage.message_id == "unique-isolation@example.com"))
        self.assertEqual(message.project_id, PROJECT_A_ID)
        self.assertNotEqual(message.project_id, PROJECT_B_ID)
        self._created_document_ids.append(message.document_id)
        session.close()


class AttachmentTraceabilityTests(MailboxSyncTests):
    def test_a_pdf_attachment_on_a_synced_message_becomes_a_real_indexed_document(self):
        mailbox = self._make_mailbox(PROJECT_A_ID)
        raw = _build_eml_with_pdf_attachment(
            "<unique-attach@example.com>", "Notice with attachment", "See attached",
            "CLAIMTRACE-GMAIL-ATTACH-MARKER-9001",
        )

        with patch("app.email_sync.orchestrator.refresh_access_token", return_value=("tok", 3600)), \
             patch("app.email_sync.orchestrator.gmail_source.list_message_ids", return_value=MessagePage(["m-att"], None)), \
             patch("app.email_sync.orchestrator.gmail_source.fetch_profile", return_value=GmailProfile("a@example.com", "600")), \
             patch("app.email_sync.orchestrator.gmail_source.fetch_raw_message", return_value=RawMessage("m-att", raw)):
            session, mb = self._reload(mailbox.id)
            result = sync_mailbox(session, self.settings.storage_root, mb, self.settings)

        self.assertEqual(result.imported, 1)
        message = session.scalar(select(EmailMessage).where(EmailMessage.message_id == "unique-attach@example.com"))
        self._created_document_ids.append(message.document_id)

        from app.db.models import DocumentChunk, EmailAttachment

        attachment = session.scalar(select(EmailAttachment).where(EmailAttachment.message_id == message.document_id))
        self.assertIsNotNone(attachment)
        self.assertEqual(attachment.status, "processed")
        self.assertIsNotNone(attachment.document_id)
        self._created_document_ids.append(attachment.document_id)

        chunks = session.scalars(select(DocumentChunk).where(DocumentChunk.document_id == attachment.document_id)).all()
        self.assertTrue(any("CLAIMTRACE-GMAIL-ATTACH-MARKER-9001" in c.chunk_text for c in chunks))
        session.close()


class HistoryExpiryFallbackTests(MailboxSyncTests):
    def test_an_expired_history_cursor_falls_back_to_a_full_sync_in_the_same_call(self):
        mailbox = self._make_mailbox(PROJECT_A_ID)
        session = self.session_factory()
        mb = session.get(ConnectedMailbox, mailbox.id)
        mb.sync_cursor = "history:old-and-expired"
        session.commit()

        raw = _build_eml("<unique-expiry@example.com>", "After expiry", "Body")

        with patch("app.email_sync.orchestrator.refresh_access_token", return_value=("tok", 3600)), \
             patch("app.email_sync.orchestrator.gmail_source.list_changed_message_ids", side_effect=HistoryExpiredError("expired")), \
             patch("app.email_sync.orchestrator.gmail_source.list_message_ids", return_value=MessagePage(["m-after"], None)), \
             patch("app.email_sync.orchestrator.gmail_source.fetch_profile", return_value=GmailProfile("a@example.com", "700")), \
             patch("app.email_sync.orchestrator.gmail_source.fetch_raw_message", return_value=RawMessage("m-after", raw)):
            result = sync_mailbox(session, self.settings.storage_root, mb, self.settings)

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.imported, 1)
        self.assertEqual(mb.sync_cursor, "history:700")

        message = session.scalar(select(EmailMessage).where(EmailMessage.message_id == "unique-expiry@example.com"))
        self._created_document_ids.append(message.document_id)
        session.close()


class TransientListingErrorTests(MailboxSyncTests):
    """Code review fix: GmailTransientError (429/5xx/network — a separate
    exception hierarchy from GmailApiError/GmailAuthError, see
    gmail_oauth.py vs gmail_source.py) previously escaped sync_mailbox()
    uncaught whenever raised during profile retrieval, full-list
    pagination, or history listing — confirmed by direct, non-destructive
    execution during the code review that found this. These three tests
    pin down the fix for each of those three call sites independently."""

    def test_a_transient_error_during_initial_profile_retrieval_returns_a_controlled_error(self):
        mailbox = self._make_mailbox(PROJECT_A_ID)
        with patch("app.email_sync.orchestrator.refresh_access_token", return_value=("tok", 3600)), \
             patch("app.email_sync.orchestrator.gmail_source.fetch_profile", side_effect=GmailTransientError("503 on profile")):
            session, mb = self._reload(mailbox.id)
            original_cursor = mb.sync_cursor
            result = sync_mailbox(session, self.settings.storage_root, mb, self.settings)

        self.assertEqual(result.status, "error")
        self.assertNotEqual(result.status, "needs_reauth")
        self.assertEqual(mb.status, "connected")
        self.assertEqual(mb.sync_cursor, original_cursor)  # never advanced
        session.close()

    def test_a_transient_error_during_full_list_pagination_returns_a_controlled_error(self):
        mailbox = self._make_mailbox(PROJECT_A_ID)
        with patch("app.email_sync.orchestrator.refresh_access_token", return_value=("tok", 3600)), \
             patch("app.email_sync.orchestrator.gmail_source.fetch_profile", return_value=GmailProfile("a@example.com", "100")), \
             patch("app.email_sync.orchestrator.gmail_source.list_message_ids", side_effect=GmailTransientError("429 on list")):
            session, mb = self._reload(mailbox.id)
            original_cursor = mb.sync_cursor
            result = sync_mailbox(session, self.settings.storage_root, mb, self.settings)

        self.assertEqual(result.status, "error")
        self.assertNotEqual(result.status, "needs_reauth")
        self.assertEqual(mb.status, "connected")
        self.assertEqual(mb.sync_cursor, original_cursor)
        session.close()

    def test_a_transient_error_during_incremental_history_listing_returns_a_controlled_error(self):
        mailbox = self._make_mailbox(PROJECT_A_ID)
        session = self.session_factory()
        mb = session.get(ConnectedMailbox, mailbox.id)
        mb.sync_cursor = "history:500"
        session.commit()

        with patch("app.email_sync.orchestrator.refresh_access_token", return_value=("tok", 3600)), \
             patch("app.email_sync.orchestrator.gmail_source.list_changed_message_ids", side_effect=GmailTransientError("503 on history")):
            result = sync_mailbox(session, self.settings.storage_root, mb, self.settings)

        self.assertEqual(result.status, "error")
        self.assertNotEqual(result.status, "needs_reauth")
        self.assertEqual(mb.status, "connected")
        self.assertEqual(mb.sync_cursor, "history:500")  # unchanged
        session.close()

    def test_a_non_transient_gmail_api_error_during_listing_still_returns_error_not_an_unhandled_exception(self):
        """Regression guard for the existing GmailApiError/GmailAuthError
        handling this fix must not disturb."""
        mailbox = self._make_mailbox(PROJECT_A_ID)
        with patch("app.email_sync.orchestrator.refresh_access_token", return_value=("tok", 3600)), \
             patch("app.email_sync.orchestrator.gmail_source.fetch_profile", side_effect=GmailApiError("malformed response")):
            session, mb = self._reload(mailbox.id)
            result = sync_mailbox(session, self.settings.storage_root, mb, self.settings)

        self.assertEqual(result.status, "error")
        session.close()


class FullSyncHistoryBaselineTests(MailboxSyncTests):
    """Code review fix: the historyId baseline for a full sync must be
    captured BEFORE listing begins, not after — otherwise a message that
    arrives during a multi-page full sync can be silently missed (it may
    never appear in the listing itself, and a baseline captured
    afterward is already past that message's own history entry). These
    tests pin down the corrected behavior directly."""

    def test_the_profile_is_fetched_once_before_the_first_listing_call_not_after(self):
        mailbox = self._make_mailbox(PROJECT_A_ID)
        call_order: list[str] = []

        def fake_list(access_token, *, page_token):
            call_order.append("list")
            return MessagePage([], None)

        def fake_profile(access_token):
            call_order.append("profile")
            return GmailProfile("a@example.com", "800")

        with patch("app.email_sync.orchestrator.refresh_access_token", return_value=("tok", 3600)), \
             patch("app.email_sync.orchestrator.gmail_source.list_message_ids", side_effect=fake_list), \
             patch("app.email_sync.orchestrator.gmail_source.fetch_profile", side_effect=fake_profile):
            session, mb = self._reload(mailbox.id)
            sync_mailbox(session, self.settings.storage_root, mb, self.settings)

        self.assertEqual(call_order, ["profile", "list"])
        session.close()

    def test_a_multi_page_full_sync_carries_the_same_baseline_across_resumed_calls(self):
        """Simulates a full sync too large for one call: the first call
        exhausts its page/message bound mid-listing (next_page_token still
        set), persisting a 'page:<baseline>:<token>' cursor. The second
        call must reuse that SAME baseline — not re-fetch the profile and
        capture a newer one — even though it only resumes listing, never
        calling fetch_profile again until the listing truly finishes."""
        mailbox = self._make_mailbox(PROJECT_A_ID)
        profile_calls = 0

        def fake_profile(access_token):
            nonlocal profile_calls
            profile_calls += 1
            return GmailProfile("a@example.com", "900")

        with patch("app.email_sync.orchestrator.refresh_access_token", return_value=("tok", 3600)), \
             patch("app.email_sync.orchestrator.gmail_source.list_message_ids", return_value=MessagePage(["m1"], "next-page-token")), \
             patch("app.email_sync.orchestrator.gmail_source.fetch_profile", side_effect=fake_profile), \
             patch("app.email_sync.orchestrator.gmail_source.fetch_raw_message", return_value=RawMessage("m1", _build_eml("<unique-baseline-page1@example.com>", "Page one", "Body"))), \
             patch("app.email_sync.orchestrator.MAX_PAGES_PER_CALL", 1):
            session, mb = self._reload(mailbox.id)
            result = sync_mailbox(session, self.settings.storage_root, mb, self.settings)

        self.assertEqual(result.status, "partial")  # listing not finished — a page_token remains
        self.assertEqual(profile_calls, 1)
        self.assertEqual(mb.sync_cursor, "page:900:next-page-token")

        page1_message = session.scalar(
            select(EmailMessage).where(EmailMessage.message_id == "unique-baseline-page1@example.com")
        )
        self._created_document_ids.append(page1_message.document_id)

        # Second call: still mid-listing, must NOT call fetch_profile again
        # (the baseline from the first call is carried forward verbatim).
        with patch("app.email_sync.orchestrator.refresh_access_token", return_value=("tok", 3600)), \
             patch("app.email_sync.orchestrator.gmail_source.list_message_ids", return_value=MessagePage(["m2"], None)), \
             patch("app.email_sync.orchestrator.gmail_source.fetch_profile", side_effect=fake_profile), \
             patch("app.email_sync.orchestrator.gmail_source.fetch_raw_message", return_value=RawMessage("m2", _build_eml("<unique-baseline@example.com>", "Resumed", "Body"))):
            result2 = sync_mailbox(session, self.settings.storage_root, mb, self.settings)

        self.assertEqual(profile_calls, 1)  # still only ever called once for this whole full sync
        self.assertEqual(mb.sync_cursor, "history:900")  # the ORIGINAL baseline, not a freshly re-fetched one
        self.assertEqual(result2.status, "completed")

        message = session.scalar(select(EmailMessage).where(EmailMessage.message_id == "unique-baseline@example.com"))
        self._created_document_ids.append(message.document_id)
        session.close()


class DeferredRecoveryTests(MailboxSyncTests):
    """End-to-end regression test for the documented design decision in
    orchestrator.py's own module docstring: a message absent from the
    initial full-list response (simulating one Gmail's own listing
    happened to miss — e.g. it arrived mid-listing) must still be
    ingested, exactly once, by the NEXT sync call's incremental pass,
    which starts from the baseline the first call captured. This proves
    the self-healing guarantee end-to-end rather than only asserting the
    cursor-mechanics pieces in isolation (see FullSyncHistoryBaselineTests
    above, which this test complements, not replaces)."""

    def test_a_message_missed_by_the_initial_full_list_is_caught_by_the_next_incremental_sync_exactly_once(self):
        mailbox = self._make_mailbox(PROJECT_A_ID)
        present_raw = _build_eml("<unique-present@example.com>", "Seen in initial listing", "Body")
        missed_raw = _build_eml("<unique-missed@example.com>", "Missed by initial listing", "Body")

        # Call 1: the initial full sync. Gmail's own listing (mocked) only
        # returns ONE message — "missed-one" is deliberately absent, as if
        # it arrived after this listing's own page was already generated.
        with patch("app.email_sync.orchestrator.refresh_access_token", return_value=("tok", 3600)), \
             patch("app.email_sync.orchestrator.gmail_source.fetch_profile", return_value=GmailProfile("a@example.com", "2000")), \
             patch("app.email_sync.orchestrator.gmail_source.list_message_ids", return_value=MessagePage(["present-one"], None)), \
             patch("app.email_sync.orchestrator.gmail_source.fetch_raw_message", return_value=RawMessage("present-one", present_raw)):
            session, mb = self._reload(mailbox.id)
            first = sync_mailbox(session, self.settings.storage_root, mb, self.settings)

        self.assertEqual(first.status, "completed")
        self.assertEqual(first.imported, 1)
        self.assertEqual(mb.sync_cursor, "history:2000")  # baseline captured BEFORE the listing, per the fix

        present_message = session.scalar(select(EmailMessage).where(EmailMessage.message_id == "unique-present@example.com"))
        self.assertIsNotNone(present_message)
        self._created_document_ids.append(present_message.document_id)
        session.close()

        # Call 2: the next manual "Sync now". Its incremental pass (mocked
        # history.list, starting from the exact baseline captured above)
        # now reveals the message the first call's listing missed.
        with patch("app.email_sync.orchestrator.refresh_access_token", return_value=("tok", 3600)), \
             patch("app.email_sync.orchestrator.gmail_source.list_changed_message_ids") as mock_history, \
             patch("app.email_sync.orchestrator.gmail_source.fetch_raw_message", return_value=RawMessage("missed-one", missed_raw)):
            from app.email_sync.gmail_source import HistoryPage

            mock_history.return_value = HistoryPage(message_ids=["missed-one"], next_page_token=None, new_history_id="2001")
            session, mb = self._reload(mailbox.id)
            second = sync_mailbox(session, self.settings.storage_root, mb, self.settings)
            # Proves recovery used the SAME baseline the first call captured
            # — never a freshly re-captured one, which would risk reopening
            # the exact gap this whole fix closes.
            mock_history.assert_called_once()
            self.assertEqual(mock_history.call_args.kwargs["start_history_id"], "2000")

        self.assertEqual(second.status, "completed")
        self.assertEqual(second.imported, 1)
        self.assertEqual(second.duplicate, 0)
        self.assertEqual(mb.sync_cursor, "history:2001")  # progressed forward from the recovered point

        missed_message = session.scalar(select(EmailMessage).where(EmailMessage.message_id == "unique-missed@example.com"))
        self.assertIsNotNone(missed_message)
        self._created_document_ids.append(missed_message.document_id)

        # Exactly one row for the recovered message — not duplicated, not
        # silently skipped.
        all_missed_rows = session.scalars(
            select(EmailMessage).where(EmailMessage.message_id == "unique-missed@example.com")
        ).all()
        self.assertEqual(len(all_missed_rows), 1)
        session.close()

    def test_calling_sync_a_third_time_with_the_same_message_still_present_reports_duplicate_not_a_second_import(self):
        """Extends the scenario above: if the message that was recovered
        on call 2 is (for whatever reason — e.g. an overlapping/retried
        history range) surfaced AGAIN on a third call, it must come back
        as 'duplicate', never create a second row — the same dedup
        guarantee this whole module leans on throughout."""
        mailbox = self._make_mailbox(PROJECT_A_ID)
        raw = _build_eml("<unique-repeat-recovery@example.com>", "Recovered then repeated", "Body")

        with patch("app.email_sync.orchestrator.refresh_access_token", return_value=("tok", 3600)), \
             patch("app.email_sync.orchestrator.gmail_source.fetch_profile", return_value=GmailProfile("a@example.com", "3000")), \
             patch("app.email_sync.orchestrator.gmail_source.list_message_ids", return_value=MessagePage([], None)):
            session, mb = self._reload(mailbox.id)
            sync_mailbox(session, self.settings.storage_root, mb, self.settings)

        from app.email_sync.gmail_source import HistoryPage

        def run_incremental():
            with patch("app.email_sync.orchestrator.refresh_access_token", return_value=("tok", 3600)), \
                 patch(
                     "app.email_sync.orchestrator.gmail_source.list_changed_message_ids",
                     return_value=HistoryPage(message_ids=["repeat-one"], next_page_token=None, new_history_id="3001"),
                 ), \
                 patch("app.email_sync.orchestrator.gmail_source.fetch_raw_message", return_value=RawMessage("repeat-one", raw)):
                session2, mb2 = self._reload(mailbox.id)
                result = sync_mailbox(session2, self.settings.storage_root, mb2, self.settings)
                session2.close()
                return result

        second = run_incremental()
        third = run_incremental()

        self.assertEqual(second.imported, 1)
        self.assertEqual(third.imported, 0)
        self.assertEqual(third.duplicate, 1)

        session = self.session_factory()
        rows = session.scalars(
            select(EmailMessage).where(EmailMessage.message_id == "unique-repeat-recovery@example.com")
        ).all()
        self.assertEqual(len(rows), 1)
        self._created_document_ids.append(rows[0].document_id)
        session.close()


if __name__ == "__main__":
    unittest.main()
