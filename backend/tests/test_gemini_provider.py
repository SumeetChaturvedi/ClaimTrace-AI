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

from app.llm.gemini_provider import MAX_OUTPUT_TOKENS, GeminiProvider
from app.llm.provider import Prompt


def _provider_with_fake_client(response_text: str = "ok"):
    provider = GeminiProvider()
    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = MagicMock(text=response_text)
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


if __name__ == "__main__":
    unittest.main()
