"""Tests for app/email_sync/gmail_oauth.py (Phase 1: Gmail Integration).

State signing/verification is pure and offline — tested directly.
exchange_code_for_tokens/refresh_access_token/revoke_token/
fetch_account_email all make real HTTP calls to Google; those are tested
in test_gmail_source.py's style via a mocked httpx transport rather than
here, to keep this file focused on the CSRF-protection logic, which is
the part with no external dependency to mock.

No live Google credentials are used or required anywhere in this file.

Run with:
    cd backend && source .venv/bin/activate
    PYTHONPATH=. python3 -m unittest tests.test_gmail_oauth -v
"""

import time
import unittest
from unittest.mock import patch

from app.config import Settings
from app.email_sync.gmail_oauth import (
    GmailOAuthError,
    build_authorization_url,
    build_oauth_state,
    verify_oauth_state,
)


def _settings(**overrides) -> Settings:
    defaults = dict(
        gmail_client_id="fake-client-id.apps.googleusercontent.com",
        gmail_client_secret="fake-client-secret",
        gmail_oauth_redirect_uri="http://127.0.0.1:8000/mailboxes/gmail/callback",
    )
    defaults.update(overrides)
    return Settings(**defaults)


class StateRoundTripTests(unittest.TestCase):
    def test_a_freshly_built_state_verifies_to_the_same_project_id(self):
        settings = _settings()
        state = build_oauth_state(settings, project_id=42)
        self.assertEqual(verify_oauth_state(settings, state), 42)

    def test_two_states_for_the_same_project_are_not_identical(self):
        """Each state carries a fresh random nonce — this is what keeps a
        captured state from being a long-lived, reusable token even
        within its validity window, beyond the HMAC's own tamper-
        detection."""
        settings = _settings()
        state1 = build_oauth_state(settings, project_id=1)
        state2 = build_oauth_state(settings, project_id=1)
        self.assertNotEqual(state1, state2)


class TamperingIsRejectedTests(unittest.TestCase):
    def test_changing_the_signed_project_id_is_rejected(self):
        """Directly exercises the CSRF protection: an attacker who
        intercepts a state for project 1 and tries to redirect it onto
        project 2 must fail signature verification."""
        settings = _settings()
        state = build_oauth_state(settings, project_id=1)
        payload_b64, signature_b64 = state.split(".", 1)

        import base64

        def _decode(s):
            return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))

        def _encode(b):
            return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")

        payload = _decode(payload_b64).decode("utf-8")
        _, issued_at, nonce = payload.split(":", 2)
        tampered_payload = f"2:{issued_at}:{nonce}"  # project_id changed from 1 to 2
        tampered_state = f"{_encode(tampered_payload.encode())}.{signature_b64}"

        with self.assertRaises(GmailOAuthError):
            verify_oauth_state(settings, tampered_state)

    def test_a_state_signed_with_a_different_client_secret_is_rejected(self):
        settings_a = _settings(gmail_client_secret="secret-a")
        settings_b = _settings(gmail_client_secret="secret-b")
        state = build_oauth_state(settings_a, project_id=1)
        with self.assertRaises(GmailOAuthError):
            verify_oauth_state(settings_b, state)

    def test_garbage_input_is_rejected_not_crashed_on(self):
        settings = _settings()
        with self.assertRaises(GmailOAuthError):
            verify_oauth_state(settings, "not-a-real-state-token")

    def test_empty_state_is_rejected(self):
        settings = _settings()
        with self.assertRaises(GmailOAuthError):
            verify_oauth_state(settings, "")


class ExpiryTests(unittest.TestCase):
    def test_an_expired_state_is_rejected(self):
        settings = _settings()
        with patch("app.email_sync.gmail_oauth.time.time", return_value=1_000_000.0):
            state = build_oauth_state(settings, project_id=7)
        with patch("app.email_sync.gmail_oauth.time.time", return_value=1_000_000.0 + 601):
            with self.assertRaises(GmailOAuthError):
                verify_oauth_state(settings, state)

    def test_a_state_just_under_the_expiry_window_still_verifies(self):
        settings = _settings()
        with patch("app.email_sync.gmail_oauth.time.time", return_value=1_000_000.0):
            state = build_oauth_state(settings, project_id=7)
        with patch("app.email_sync.gmail_oauth.time.time", return_value=1_000_000.0 + 599):
            self.assertEqual(verify_oauth_state(settings, state), 7)


class ConfigurationRequiredTests(unittest.TestCase):
    def test_building_an_authorization_url_without_gmail_configured_raises(self):
        settings = _settings(gmail_client_id=None, gmail_client_secret=None)
        with self.assertRaises(GmailOAuthError):
            build_authorization_url(settings, project_id=1)

    def test_authorization_url_requests_only_the_readonly_scope(self):
        settings = _settings()
        url = build_authorization_url(settings, project_id=1)
        self.assertIn("gmail.readonly", url)
        self.assertNotIn("gmail.modify", url)
        self.assertNotIn("gmail.send", url)

    def test_authorization_url_requests_offline_access_and_forces_consent(self):
        """access_type=offline + prompt=consent together are what
        guarantee a refresh_token comes back even for a returning user —
        see build_authorization_url's own docstring."""
        settings = _settings()
        url = build_authorization_url(settings, project_id=1)
        self.assertIn("access_type=offline", url)
        self.assertIn("prompt=consent", url)

    def test_authorization_url_includes_a_state_parameter(self):
        settings = _settings()
        url = build_authorization_url(settings, project_id=1)
        self.assertIn("state=", url)


if __name__ == "__main__":
    unittest.main()
