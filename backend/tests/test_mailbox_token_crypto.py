"""Tests for app/email_sync/token_crypto.py (Phase 1: Gmail Integration).
Pure, offline, deterministic — no network, no database, no real Google
credentials. Mirrors this project's established principle (real behavior,
no mocks) where the behavior under test genuinely has no external
dependency to mock: encryption here is a pure function of (plaintext,
key).

Run with:
    cd backend && source .venv/bin/activate
    PYTHONPATH=. python3 -m unittest tests.test_mailbox_token_crypto -v
"""

import unittest

from cryptography.fernet import Fernet

from app.config import Settings
from app.email_sync.token_crypto import (
    TokenDecryptionError,
    TokenEncryptionNotConfigured,
    decrypt_refresh_token,
    encrypt_refresh_token,
)


def _settings(key: str | None) -> Settings:
    return Settings(mailbox_token_encryption_key=key)


class EncryptDecryptRoundTripTests(unittest.TestCase):
    def test_round_trip_recovers_the_original_token(self):
        key = Fernet.generate_key().decode()
        settings = _settings(key)
        ciphertext = encrypt_refresh_token("1//my-real-refresh-token", settings)
        self.assertEqual(decrypt_refresh_token(ciphertext, settings), "1//my-real-refresh-token")

    def test_ciphertext_does_not_contain_the_plaintext(self):
        key = Fernet.generate_key().decode()
        settings = _settings(key)
        ciphertext = encrypt_refresh_token("super-secret-token-value", settings)
        self.assertNotIn("super-secret-token-value", ciphertext)

    def test_empty_plaintext_is_rejected(self):
        settings = _settings(Fernet.generate_key().decode())
        with self.assertRaises(ValueError):
            encrypt_refresh_token("", settings)


class FailsClosedWithoutConfigurationTests(unittest.TestCase):
    def test_encrypt_raises_when_key_is_not_configured(self):
        settings = _settings(None)
        with self.assertRaises(TokenEncryptionNotConfigured):
            encrypt_refresh_token("a-token", settings)

    def test_encrypt_raises_when_key_is_blank(self):
        settings = _settings("   ")
        with self.assertRaises(TokenEncryptionNotConfigured):
            encrypt_refresh_token("a-token", settings)

    def test_decrypt_raises_when_key_is_not_configured(self):
        settings = _settings(None)
        with self.assertRaises(TokenEncryptionNotConfigured):
            decrypt_refresh_token("anything", settings)

    def test_malformed_key_is_rejected_not_silently_accepted(self):
        settings = _settings("not-a-real-fernet-key")
        with self.assertRaises(TokenEncryptionNotConfigured):
            encrypt_refresh_token("a-token", settings)


class WrongOrRotatedKeyTests(unittest.TestCase):
    def test_decrypting_with_a_different_key_raises_rather_than_returning_garbage(self):
        settings_a = _settings(Fernet.generate_key().decode())
        settings_b = _settings(Fernet.generate_key().decode())
        ciphertext = encrypt_refresh_token("a-real-token", settings_a)
        with self.assertRaises(TokenDecryptionError):
            decrypt_refresh_token(ciphertext, settings_b)

    def test_corrupted_ciphertext_raises_rather_than_returning_garbage(self):
        settings = _settings(Fernet.generate_key().decode())
        ciphertext = encrypt_refresh_token("a-real-token", settings)
        corrupted = ciphertext[:-4] + "abcd"
        with self.assertRaises(TokenDecryptionError):
            decrypt_refresh_token(corrupted, settings)


if __name__ == "__main__":
    unittest.main()
