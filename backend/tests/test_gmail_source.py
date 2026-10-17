"""Tests for app/email_sync/gmail_source.py (Phase 1: Gmail Integration) —
mocked Gmail API responses via a patched httpx.get, no real network call
and no live Google credentials anywhere in this file. This is exactly the
kind of external-HTTP boundary this project's own "no mocks" principle
(see test_investigations.py's docstring) doesn't apply to: there is no
real Gmail account to test against in CI, so a mock at the HTTP boundary
is the correct tool, not a shortcut around a real dependency this project
could otherwise exercise directly.

Run with:
    cd backend && source .venv/bin/activate
    PYTHONPATH=. python3 -m unittest tests.test_gmail_source -v
"""

import base64
import json
import unittest
from unittest.mock import patch

import httpx

from app.email_sync.gmail_source import (
    GmailApiError,
    GmailAuthError,
    GmailMessageNotFoundError,
    HistoryExpiredError,
    fetch_profile,
    fetch_raw_message,
    list_changed_message_ids,
    list_message_ids,
)
from app.email_sync.gmail_oauth import GmailTransientError


def _response(status_code: int, body: dict) -> httpx.Response:
    return httpx.Response(status_code=status_code, content=json.dumps(body).encode("utf-8"))


class ListMessageIdsPaginationTests(unittest.TestCase):
    def test_a_single_page_with_no_next_page_token_returns_its_ids_and_none(self):
        with patch("app.email_sync.gmail_source.httpx.get") as mock_get:
            mock_get.return_value = _response(200, {"messages": [{"id": "a"}, {"id": "b"}]})
            page = list_message_ids("fake-access-token", page_token=None)
        self.assertEqual(page.message_ids, ["a", "b"])
        self.assertIsNone(page.next_page_token)

    def test_a_page_with_a_next_page_token_is_returned_for_the_caller_to_continue(self):
        with patch("app.email_sync.gmail_source.httpx.get") as mock_get:
            mock_get.return_value = _response(200, {"messages": [{"id": "a"}], "nextPageToken": "page-2"})
            page = list_message_ids("fake-access-token", page_token=None)
        self.assertEqual(page.next_page_token, "page-2")

    def test_the_page_token_is_actually_forwarded_to_the_next_request(self):
        seen_params = []

        def fake_get(url, headers=None, params=None, timeout=None):
            seen_params.append(params)
            return _response(200, {"messages": []})

        with patch("app.email_sync.gmail_source.httpx.get", side_effect=fake_get):
            list_message_ids("fake-access-token", page_token="resume-here")
        self.assertEqual(seen_params[0]["pageToken"], "resume-here")

    def test_an_empty_mailbox_returns_an_empty_list_not_an_error(self):
        with patch("app.email_sync.gmail_source.httpx.get") as mock_get:
            mock_get.return_value = _response(200, {})
            page = list_message_ids("fake-access-token", page_token=None)
        self.assertEqual(page.message_ids, [])


class ErrorHandlingTests(unittest.TestCase):
    def test_a_401_response_raises_gmail_auth_error(self):
        with patch("app.email_sync.gmail_source.httpx.get") as mock_get:
            mock_get.return_value = httpx.Response(status_code=401, content=b"{}")
            with self.assertRaises(GmailAuthError):
                list_message_ids("fake-access-token", page_token=None)

    def test_a_429_response_raises_a_transient_error_not_a_hard_failure(self):
        with patch("app.email_sync.gmail_source.httpx.get") as mock_get:
            mock_get.return_value = httpx.Response(status_code=429, content=b"{}")
            with self.assertRaises(GmailTransientError):
                list_message_ids("fake-access-token", page_token=None)

    def test_a_500_response_raises_a_transient_error(self):
        with patch("app.email_sync.gmail_source.httpx.get") as mock_get:
            mock_get.return_value = httpx.Response(status_code=503, content=b"{}")
            with self.assertRaises(GmailTransientError):
                list_message_ids("fake-access-token", page_token=None)

    def test_a_network_error_raises_a_transient_error(self):
        with patch("app.email_sync.gmail_source.httpx.get", side_effect=httpx.ConnectError("boom")):
            with self.assertRaises(GmailTransientError):
                list_message_ids("fake-access-token", page_token=None)


class HistoryListTests(unittest.TestCase):
    def test_extracts_only_added_message_ids_from_a_history_response(self):
        body = {
            "history": [
                {"messagesAdded": [{"message": {"id": "new-1"}}]},
                {"messagesAdded": [{"message": {"id": "new-2"}}, {"message": {"id": "new-3"}}]},
            ],
            "historyId": "12345",
        }
        with patch("app.email_sync.gmail_source.httpx.get") as mock_get:
            mock_get.return_value = _response(200, body)
            page = list_changed_message_ids("fake-access-token", start_history_id="100")
        self.assertEqual(page.message_ids, ["new-1", "new-2", "new-3"])
        self.assertEqual(page.new_history_id, "12345")

    def test_a_404_response_raises_history_expired_error(self):
        with patch("app.email_sync.gmail_source.httpx.get") as mock_get:
            mock_get.return_value = httpx.Response(status_code=404, content=b"{}")
            with self.assertRaises(HistoryExpiredError):
                list_changed_message_ids("fake-access-token", start_history_id="too-old")

    def test_no_history_entries_returns_an_empty_list(self):
        with patch("app.email_sync.gmail_source.httpx.get") as mock_get:
            mock_get.return_value = _response(200, {"historyId": "999"})
            page = list_changed_message_ids("fake-access-token", start_history_id="100")
        self.assertEqual(page.message_ids, [])


class FetchRawMessageTests(unittest.TestCase):
    def test_decodes_base64url_raw_payload_into_real_bytes(self):
        original_bytes = b"From: a@example.com\r\nSubject: Test\r\n\r\nBody text"
        encoded = base64.urlsafe_b64encode(original_bytes).rstrip(b"=").decode("ascii")
        with patch("app.email_sync.gmail_source.httpx.get") as mock_get:
            mock_get.return_value = _response(200, {"raw": encoded})
            result = fetch_raw_message("fake-access-token", "msg-1")
        self.assertEqual(result.raw_bytes, original_bytes)
        self.assertEqual(result.message_id, "msg-1")

    def test_a_404_raises_gmail_message_not_found_error_not_a_hard_failure(self):
        with patch("app.email_sync.gmail_source.httpx.get") as mock_get:
            mock_get.return_value = httpx.Response(status_code=404, content=b"{}")
            with self.assertRaises(GmailMessageNotFoundError):
                fetch_raw_message("fake-access-token", "deleted-message")

    def test_a_response_with_no_raw_field_raises_gmail_api_error(self):
        with patch("app.email_sync.gmail_source.httpx.get") as mock_get:
            mock_get.return_value = _response(200, {})
            with self.assertRaises(GmailApiError):
                fetch_raw_message("fake-access-token", "msg-1")


class FetchProfileTests(unittest.TestCase):
    def test_returns_email_and_history_id(self):
        with patch("app.email_sync.gmail_source.httpx.get") as mock_get:
            mock_get.return_value = _response(200, {"emailAddress": "person@example.com", "historyId": "42"})
            profile = fetch_profile("fake-access-token")
        self.assertEqual(profile.email_address, "person@example.com")
        self.assertEqual(profile.history_id, "42")

    def test_a_response_missing_history_id_raises(self):
        with patch("app.email_sync.gmail_source.httpx.get") as mock_get:
            mock_get.return_value = _response(200, {"emailAddress": "person@example.com"})
            with self.assertRaises(GmailApiError):
                fetch_profile("fake-access-token")


if __name__ == "__main__":
    unittest.main()
