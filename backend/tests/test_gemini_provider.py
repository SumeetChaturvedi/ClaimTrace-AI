"""Focused provider-level test for GeminiProvider's request construction
(Phase 8B.2 Quality Remediation §3) — specifically, that
Prompt.max_output_tokens actually reaches the outbound
types.GenerateContentConfig, without making a real Gemini call.

Every other test in this project deliberately avoids mocks (see
test_investigations.py's own docstring on this) because it's testing
business/retrieval logic, where a mock would hide exactly the kind of bug
that principle exists to catch. This file is different in kind: it tests
how one specific SDK call is CONSTRUCTED (which keyword argument gets
which value), not whether Gemini produces a good answer — mocking the SDK
client at that single, narrow boundary is the right tool for that
question, and real-Gemini coverage of this same code path already exists
via test_event_extraction.py's OutputBudgetTests (checked at the Prompt
level) and the Phase 8B.2 production evaluation (checked end-to-end against
real responses).

Run with:
    cd backend && source .venv/bin/activate
    PYTHONPATH=. python3 -m unittest tests.test_gemini_provider -v
"""

import unittest
from unittest.mock import MagicMock, patch

from google.genai import types

from app.llm.gemini_provider import MAX_OUTPUT_TOKENS, GeminiProvider
from app.llm.provider import Prompt


def _provider_with_fake_client(response_text: str = "ok", finish_reason=None):
    """finish_reason=None simulates a response with no candidate metadata
    at all (the exact shape the three existing request-construction tests
    below already rely on) -- a real types.FinishReason value simulates a
    real Gemini response that actually reports one."""
    provider = GeminiProvider()
    fake_client = MagicMock()
    if finish_reason is None:
        fake_response = MagicMock(text=response_text)
    else:
        fake_response = MagicMock(text=response_text, candidates=[MagicMock(finish_reason=finish_reason)])
    fake_client.models.generate_content.return_value = fake_response
    provider._client = fake_client  # bypass the lazy genai.Client() construction
    return provider, fake_client


class OutputBudgetReachesRequestConfigTests(unittest.TestCase):
    @patch("app.llm.gemini_provider.get_settings")
    def test_default_prompt_uses_the_shared_max_output_tokens_constant(self, mock_get_settings):
        mock_get_settings.return_value = MagicMock(gemini_api_key="fake-key", gemini_model="fake-model")
        provider, fake_client = _provider_with_fake_client()

        provider.generate(Prompt(system_prompt="sys", user_prompt="user"))

        _, kwargs = fake_client.models.generate_content.call_args
        self.assertEqual(kwargs["config"].max_output_tokens, MAX_OUTPUT_TOKENS)

    @patch("app.llm.gemini_provider.get_settings")
    def test_prompt_level_override_reaches_the_request_config(self, mock_get_settings):
        mock_get_settings.return_value = MagicMock(gemini_api_key="fake-key", gemini_model="fake-model")
        provider, fake_client = _provider_with_fake_client()

        provider.generate(Prompt(system_prompt="sys", user_prompt="user", max_output_tokens=4096))

        _, kwargs = fake_client.models.generate_content.call_args
        self.assertEqual(kwargs["config"].max_output_tokens, 4096)
        self.assertNotEqual(4096, MAX_OUTPUT_TOKENS)  # the override is genuinely different from the default

    @patch("app.llm.gemini_provider.get_settings")
    def test_override_does_not_change_system_or_user_prompt_forwarding(self, mock_get_settings):
        """The override must be additive — it should not disturb any other
        part of the request construction."""
        mock_get_settings.return_value = MagicMock(gemini_api_key="fake-key", gemini_model="fake-model")
        provider, fake_client = _provider_with_fake_client()

        provider.generate(Prompt(system_prompt="sys-text", user_prompt="user-text", max_output_tokens=4096))

        args, kwargs = fake_client.models.generate_content.call_args
        self.assertEqual(kwargs["contents"], "user-text")
        self.assertEqual(kwargs["config"].system_instruction, "sys-text")


class AnswerTruncationDetectionTests(unittest.TestCase):
    """Phase 1 fix: GenerationResult.truncated must reflect Gemini's own
    reported finish_reason, never a guess based on the text itself."""

    @patch("app.llm.gemini_provider.get_settings")
    def test_max_tokens_finish_reason_sets_truncated_true(self, mock_get_settings):
        mock_get_settings.return_value = MagicMock(gemini_api_key="fake-key", gemini_model="fake-model")
        provider, _ = _provider_with_fake_client(finish_reason=types.FinishReason.MAX_TOKENS)

        result = provider.generate(Prompt(system_prompt="sys", user_prompt="user"))

        self.assertTrue(result.truncated)
        self.assertEqual(result.text, "ok")

    @patch("app.llm.gemini_provider.get_settings")
    def test_normal_stop_finish_reason_does_not_set_truncated(self, mock_get_settings):
        mock_get_settings.return_value = MagicMock(gemini_api_key="fake-key", gemini_model="fake-model")
        provider, _ = _provider_with_fake_client(finish_reason=types.FinishReason.STOP)

        result = provider.generate(Prompt(system_prompt="sys", user_prompt="user"))

        self.assertFalse(result.truncated)

    @patch("app.llm.gemini_provider.get_settings")
    def test_response_with_no_candidate_metadata_defaults_to_not_truncated(self, mock_get_settings):
        """A response shape this code can't read finish_reason from at all
        (no `candidates`) must never be treated as proof of truncation --
        only STOP/MAX_TOKENS from a real response indicate anything."""
        mock_get_settings.return_value = MagicMock(gemini_api_key="fake-key", gemini_model="fake-model")
        provider, _ = _provider_with_fake_client()  # finish_reason=None -> no `candidates` attribute set

        result = provider.generate(Prompt(system_prompt="sys", user_prompt="user"))

        self.assertFalse(result.truncated)


if __name__ == "__main__":
    unittest.main()
