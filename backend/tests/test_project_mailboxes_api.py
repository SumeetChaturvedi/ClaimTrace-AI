"""API-level tests for app/api/routes/project_mailboxes.py (Phase 1: Gmail
Integration) — real Postgres, real TestClient, no real Google calls (the
OAuth connect/callback endpoints are exercised only up to the point where
they'd need to reach Google, which is covered by mocks in
test_gmail_oauth.py/test_gmail_source.py instead). This file is about the
HTTP layer: project scoping, response shapes, and that no secret ever
appears in a response.

Run with:
    cd backend && source .venv/bin/activate
    PYTHONPATH=. python3 -m unittest tests.test_project_mailboxes_api -v
"""

import unittest
from unittest.mock import patch

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.config import Settings, get_settings
from app.db.models import ConnectedMailbox
from app.db.session import get_session_factory
from app.email_sync.token_crypto import encrypt_refresh_token
from app.main import app

PROJECT_ID = 2
OTHER_PROJECT_ID = 3
NONEXISTENT_PROJECT_ID = 999_999


class ProjectMailboxApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.client.__enter__()
        cls.fernet_key = Fernet.generate_key().decode()
        cls.settings = Settings(
            mailbox_token_encryption_key=cls.fernet_key,
            gmail_client_id="fake-client-id",
            gmail_client_secret="fake-client-secret",
            database_url=get_settings().database_url,
            storage_root=get_settings().storage_root,
        )
        cls._created_mailbox_ids: list[int] = []

    @classmethod
    def tearDownClass(cls):
        with get_session_factory()() as session:
            if cls._created_mailbox_ids:
                session.execute(delete(ConnectedMailbox).where(ConnectedMailbox.id.in_(cls._created_mailbox_ids)))
                session.commit()
        cls.client.__exit__(None, None, None)

    def _make_mailbox(self, project_id: int, status: str = "connected") -> int:
        with get_session_factory()() as session:
            mailbox = ConnectedMailbox(
                project_id=project_id,
                provider="gmail",
                external_email=f"api-test-{len(self._created_mailbox_ids)}@example.com",
                encrypted_refresh_token=encrypt_refresh_token("fake-token", self.settings),
                granted_scope="https://www.googleapis.com/auth/gmail.readonly",
                status=status,
            )
            session.add(mailbox)
            session.commit()
            session.refresh(mailbox)
            self._created_mailbox_ids.append(mailbox.id)
            return mailbox.id

    def _override_settings(self):
        app.dependency_overrides[get_settings] = lambda: self.settings

    def tearDown(self):
        app.dependency_overrides.pop(get_settings, None)

    def test_connect_under_nonexistent_project_returns_404(self):
        self._override_settings()
        resp = self.client.post(f"/projects/{NONEXISTENT_PROJECT_ID}/mailboxes/gmail/connect")
        self.assertEqual(resp.status_code, 404)

    def test_connect_returns_an_authorization_url_containing_a_state_parameter(self):
        self._override_settings()
        resp = self.client.post(f"/projects/{PROJECT_ID}/mailboxes/gmail/connect")
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertIn("authorization_url", body)
        self.assertIn("state=", body["authorization_url"])
        self.assertIn("gmail.readonly", body["authorization_url"])

    def test_connect_without_gmail_configured_returns_503_not_a_500(self):
        app.dependency_overrides[get_settings] = lambda: Settings(gmail_client_id=None, gmail_client_secret=None)
        resp = self.client.post(f"/projects/{PROJECT_ID}/mailboxes/gmail/connect")
        self.assertEqual(resp.status_code, 503)

    def test_list_mailboxes_under_nonexistent_project_returns_404(self):
        resp = self.client.get(f"/projects/{NONEXISTENT_PROJECT_ID}/mailboxes")
        self.assertEqual(resp.status_code, 404)

    def test_list_mailboxes_never_includes_the_encrypted_refresh_token(self):
        self._make_mailbox(PROJECT_ID)
        resp = self.client.get(f"/projects/{PROJECT_ID}/mailboxes")
        self.assertEqual(resp.status_code, 200)
        body_text = resp.text
        self.assertNotIn("encrypted_refresh_token", body_text)
        self.assertNotIn("refresh_token", body_text)
        self.assertNotIn("access_token", body_text)

    def test_a_mailbox_from_another_project_is_not_visible_or_syncable_under_this_project(self):
        mailbox_id = self._make_mailbox(OTHER_PROJECT_ID)

        list_resp = self.client.get(f"/projects/{PROJECT_ID}/mailboxes")
        self.assertEqual(list_resp.status_code, 200)
        self.assertNotIn(mailbox_id, [m["id"] for m in list_resp.json()])

        sync_resp = self.client.post(f"/projects/{PROJECT_ID}/mailboxes/{mailbox_id}/sync")
        self.assertEqual(sync_resp.status_code, 404)

        disconnect_resp = self.client.post(f"/projects/{PROJECT_ID}/mailboxes/{mailbox_id}/disconnect")
        self.assertEqual(disconnect_resp.status_code, 404)

    def test_disconnect_nulls_the_token_and_a_subsequent_sync_is_rejected(self):
        """Code review fix: this test previously made a real outbound HTTPS
        call to Google's revoke endpoint (via the unmocked revoke_token()) —
        confirmed by its log line appearing in real test output. Mocked
        here like every other Gmail HTTP call in this file's siblings."""
        self._override_settings()
        mailbox_id = self._make_mailbox(PROJECT_ID)

        with patch("app.api.routes.project_mailboxes.revoke_token", return_value=True) as mock_revoke:
            disconnect_resp = self.client.post(f"/projects/{PROJECT_ID}/mailboxes/{mailbox_id}/disconnect")
            mock_revoke.assert_called_once()
        self.assertEqual(disconnect_resp.status_code, 200, disconnect_resp.text)
        self.assertEqual(disconnect_resp.json()["status"], "disconnected")

        with get_session_factory()() as session:
            from app.db.models import ConnectedMailbox as CM

            mailbox = session.get(CM, mailbox_id)
            self.assertIsNone(mailbox.encrypted_refresh_token)

        sync_resp = self.client.post(f"/projects/{PROJECT_ID}/mailboxes/{mailbox_id}/sync")
        self.assertEqual(sync_resp.status_code, 409)

    def test_callback_with_an_invalid_state_redirects_rather_than_500ing(self):
        self._override_settings()
        resp = self.client.get(
            "/mailboxes/gmail/callback",
            params={"code": "fake-code", "state": "tampered-or-garbage-state"},
            follow_redirects=False,
        )
        self.assertIn(resp.status_code, (302, 307))
        self.assertIn("gmail_connect=error", resp.headers["location"])

    def test_callback_with_a_denial_error_redirects_without_attempting_a_token_exchange(self):
        resp = self.client.get(
            "/mailboxes/gmail/callback",
            params={"error": "access_denied"},
            follow_redirects=False,
        )
        self.assertIn(resp.status_code, (302, 307))
        self.assertIn("gmail_connect=denied", resp.headers["location"])

    def test_callback_missing_code_or_state_redirects_with_error(self):
        resp = self.client.get("/mailboxes/gmail/callback", follow_redirects=False)
        self.assertIn(resp.status_code, (302, 307))
        self.assertIn("gmail_connect=error", resp.headers["location"])

    def test_callback_for_a_project_deleted_before_the_redirect_completes_fails_gracefully(self):
        """Code review fix: previously, a valid, correctly-signed state for
        a project_id that no longer exists would reach the ConnectedMailbox
        insert and raise an unhandled IntegrityError (foreign key
        violation) -- a raw 500 instead of the same graceful redirect every
        other failure in this handler produces. Exercised with a real,
        validly-signed state (built the same way the connect endpoint
        builds one) so this test proves the NEW project-existence check,
        not just state validation (already covered above)."""
        self._override_settings()
        from app.email_sync.gmail_oauth import build_oauth_state

        state = build_oauth_state(self.settings, project_id=NONEXISTENT_PROJECT_ID)

        resp = self.client.get(
            "/mailboxes/gmail/callback",
            params={"code": "fake-code", "state": state},
            follow_redirects=False,
        )
        self.assertIn(resp.status_code, (302, 307))
        self.assertIn("gmail_connect=error", resp.headers["location"])


if __name__ == "__main__":
    unittest.main()
