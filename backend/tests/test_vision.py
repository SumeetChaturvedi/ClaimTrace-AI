"""Focused tests for Phase W2.3 (Multimodal Image Understanding) --
app/llm/provider.py's image support, app/llm/gemini_provider.py's
multimodal request construction, app/vision/gemini_vision.py,
app/vision/process_pending.py, app/ingestion/image_visual_indexing.py,
and the ImageVisualDescriptionResult model.

Mirrors tests/test_ocr.py's own approach exactly: plain unittest, real
Postgres for anything that touches the database, the Gemini provider
boundary mocked deterministically throughout -- NO live API call is ever
made by this file. Image/eml/zip fixture builders are reused directly
from tests.test_ocr rather than duplicated.

Run with:
    cd backend && source .venv/bin/activate
    PYTHONPATH=. python3 -m unittest tests.test_vision -v
"""

from __future__ import annotations

import io
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import formatdate
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import delete, select, update

from google.genai import errors as genai_errors

from app.config import get_settings
from app.db.models import (
    Document,
    DocumentChunk,
    EmailAttachment,
    EmailMessage,
    EmailThread,
    ImageOcrResult,
    ImageVisualDescriptionResult,
    Project,
    ProjectImageAsset,
    WhatsAppChat,
    WhatsAppMediaAttachment,
    WhatsAppMessage,
)
from app.db.session import get_session_factory
from app.llm.gemini_provider import GeminiProvider
from app.llm.provider import GenerationResult, ImagePart, LLMProviderError, Prompt
from app.main import app
from app.ocr import process_pending as pp
from app.vision import process_pending as vp
from app.vision.gemini_vision import generate_visual_description
from app.vision.pending import ensure_pending_visual_result
from tests.test_ocr import _build_eml, _build_test_image, _build_whatsapp_zip


def _color_of_image_bytes(content: bytes) -> tuple:
    with Image.open(io.BytesIO(content)) as img:
        return img.convert("RGB").getpixel((0, 0))


def _patch_vision_provider(tagged_fn):
    """Patches app.vision.gemini_vision.GeminiProvider (the class name
    that module's own generate_visual_description() constructs when no
    provider is injected -- the production code path) with a fake whose
    .generate(prompt) is `tagged_fn`. Mirrors tests/test_ocr.py's own
    pixel-color-tagging convention exactly, adapted for an image passed
    as Prompt.images[0].data rather than a PIL Image object -- see
    _color_of_image_bytes above."""
    fake_instance = MagicMock()
    fake_instance.generate.side_effect = tagged_fn
    fake_class = MagicMock(return_value=fake_instance)
    return patch("app.vision.gemini_vision.GeminiProvider", fake_class)


class GeminiProviderImageRequestConstructionTests(unittest.TestCase):
    """No database, no app.vision import at all -- purely tests how
    GeminiProvider.generate() constructs its outbound request when
    Prompt.images is set, mirroring tests/test_gemini_provider.py's own
    mocking approach and philosophy exactly (see that file's own
    docstring for why mocking the SDK client at this one, narrow
    boundary is the right tool here)."""

    def _provider_with_fake_client(self, response_text: str = "a description"):
        provider = GeminiProvider()
        fake_client = MagicMock()
        fake_client.models.generate_content.return_value = MagicMock(text=response_text)
        provider._client = fake_client
        return provider, fake_client

    @patch("app.llm.gemini_provider.get_settings")
    def test_prompt_with_images_builds_a_list_of_text_and_image_parts(self, mock_get_settings):
        mock_get_settings.return_value = MagicMock(gemini_api_key="fake-key", gemini_model="fake-model")
        provider, fake_client = self._provider_with_fake_client()

        provider.generate(
            Prompt(system_prompt="sys", user_prompt="describe this", images=(ImagePart(data=b"fake-image-bytes", mime_type="image/png"),))
        )

        _, kwargs = fake_client.models.generate_content.call_args
        contents = kwargs["contents"]
        self.assertIsInstance(contents, list)
        self.assertEqual(len(contents), 2)
        self.assertEqual(contents[0].text, "describe this")
        self.assertEqual(contents[1].inline_data.mime_type, "image/png")
        self.assertEqual(contents[1].inline_data.data, b"fake-image-bytes")

    @patch("app.llm.gemini_provider.get_settings")
    def test_prompt_without_images_keeps_the_existing_bare_string_contents(self, mock_get_settings):
        """Regression: every existing caller (ReasoningEngine, EventExtractor)
        never sets Prompt.images, so their request shape must stay
        byte-for-byte unchanged -- a plain string, never a list."""
        mock_get_settings.return_value = MagicMock(gemini_api_key="fake-key", gemini_model="fake-model")
        provider, fake_client = self._provider_with_fake_client()

        provider.generate(Prompt(system_prompt="sys", user_prompt="describe this"))

        _, kwargs = fake_client.models.generate_content.call_args
        self.assertEqual(kwargs["contents"], "describe this")

    @patch("app.llm.gemini_provider.get_settings")
    def test_multiple_images_each_become_their_own_part(self, mock_get_settings):
        mock_get_settings.return_value = MagicMock(gemini_api_key="fake-key", gemini_model="fake-model")
        provider, fake_client = self._provider_with_fake_client()

        provider.generate(
            Prompt(
                system_prompt="sys",
                user_prompt="describe these",
                images=(ImagePart(data=b"one", mime_type="image/png"), ImagePart(data=b"two", mime_type="image/jpeg")),
            )
        )

        _, kwargs = fake_client.models.generate_content.call_args
        contents = kwargs["contents"]
        self.assertEqual(len(contents), 3)
        self.assertEqual(contents[1].inline_data.data, b"one")
        self.assertEqual(contents[2].inline_data.data, b"two")

    @patch("app.llm.gemini_provider.get_settings")
    def test_api_rejection_of_image_input_is_converted_to_the_provider_error_abstraction(self, mock_get_settings):
        """Pre-commit review follow-up: simulates the realistic shape a
        "this model doesn't support image input" rejection would
        actually take -- a genuine google.genai.errors.ClientError (the
        SDK's own 4xx exception class, a real subclass of the APIError
        already caught at gemini_provider.py's one try/except, verified
        directly against the installed SDK: ClientError -> APIError),
        never a fabricated generic Exception. No live API call: the SDK
        client itself is mocked, only its exception TYPE is real."""
        mock_get_settings.return_value = MagicMock(gemini_api_key="fake-key", gemini_model="fake-model")
        provider, fake_client = self._provider_with_fake_client()
        fake_client.models.generate_content.side_effect = genai_errors.ClientError(
            400,
            {"error": {"code": 400, "message": "Image input is not supported for this model.", "status": "INVALID_ARGUMENT"}},
        )

        with self.assertRaises(LLMProviderError) as ctx:
            provider.generate(
                Prompt(system_prompt="sys", user_prompt="describe this", images=(ImagePart(data=b"fake-image-bytes", mime_type="image/png"),))
            )
        self.assertIn("Image input is not supported for this model", str(ctx.exception))


class GenerateVisualDescriptionTests(unittest.TestCase):
    """app/vision/gemini_vision.py's own run_*()-shaped wrapper, with an
    injected fake LLMProvider -- no real GeminiProvider/SDK involved at
    all, no live call possible."""

    def test_successful_description_returns_a_completed_outcome(self):
        fake_provider = MagicMock()
        fake_provider.generate.return_value = GenerationResult(text="A cracked concrete beam with exposed rebar.")

        result = generate_visual_description(b"fake-image-bytes", mime_type="image/png", provider=fake_provider)

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.text, "A cracked concrete beam with exposed rebar.")
        prompt = fake_provider.generate.call_args[0][0]
        self.assertEqual(len(prompt.images), 1)
        self.assertEqual(prompt.images[0].data, b"fake-image-bytes")
        self.assertEqual(prompt.images[0].mime_type, "image/png")

    def test_provider_error_returns_a_failed_outcome_never_raises(self):
        fake_provider = MagicMock()
        fake_provider.generate.side_effect = LLMProviderError("simulated provider failure")

        result = generate_visual_description(b"fake-image-bytes", mime_type="image/png", provider=fake_provider)

        self.assertEqual(result.status, "failed")
        self.assertIn("simulated provider failure", result.error)


class VisionDocumentIndexingTests(unittest.TestCase):
    """Phase W2.3 end-to-end: real Postgres, the Gemini provider boundary
    mocked deterministically via _patch_vision_provider (pixel-color
    tagging, exactly mirroring tests/test_ocr.py's OcrDocumentIndexingTests).
    Every assertion checks the SPECIFIC row(s) this test itself created by
    id, never a raw aggregate count, since this shares a database with
    unrelated dev data and other tests."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.client.__enter__()
        cls._created_project_ids: list[int] = []

    @classmethod
    def tearDownClass(cls):
        with get_session_factory()() as session:
            for project_id in cls._created_project_ids:
                for document in session.query(Document).filter(Document.project_id == project_id).all():
                    session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
                session.execute(
                    delete(ImageVisualDescriptionResult).where(
                        ImageVisualDescriptionResult.project_image_asset_id.in_(
                            select(ProjectImageAsset.id).where(ProjectImageAsset.project_id == project_id)
                        )
                        | ImageVisualDescriptionResult.email_attachment_id.in_(
                            select(EmailAttachment.id).join(EmailMessage, EmailMessage.document_id == EmailAttachment.message_id).where(
                                EmailMessage.project_id == project_id
                            )
                        )
                        | ImageVisualDescriptionResult.whatsapp_media_attachment_id.in_(
                            select(WhatsAppMediaAttachment.id).join(
                                WhatsAppMessage, WhatsAppMessage.document_id == WhatsAppMediaAttachment.message_id
                            ).where(WhatsAppMessage.project_id == project_id)
                        )
                    )
                )
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
                session.execute(
                    delete(EmailAttachment).where(
                        EmailAttachment.message_id.in_(select(Document.id).where(Document.project_id == project_id))
                    )
                )
                session.execute(delete(EmailMessage).where(EmailMessage.project_id == project_id))
                session.execute(delete(EmailThread).where(EmailThread.project_id == project_id))
                session.execute(
                    delete(WhatsAppMediaAttachment).where(
                        WhatsAppMediaAttachment.message_id.in_(
                            select(WhatsAppMessage.document_id).where(WhatsAppMessage.project_id == project_id)
                        )
                    )
                )
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

    def _upload_image(self, project_id: int, filename: str, *, color=(1, 2, 3)) -> int:
        resp = self.client.post(
            f"/projects/{project_id}/documents",
            files={"files": (filename, io.BytesIO(_build_test_image(color=color, fmt="PNG")), "image/png")},
        )
        return resp.json()["images"][0]["id"]

    def _run_vision(self, **kwargs):
        defaults = {"storage_root": get_settings().storage_root}
        defaults.update(kwargs)
        return vp.process_pending(**defaults)

    def _run_ocr(self, **kwargs):
        defaults = {"language": "eng", "tesseract_cmd": None, "storage_root": get_settings().storage_root}
        defaults.update(kwargs)
        return pp.process_pending(**defaults)

    def _claim_and_process_one_visual(self, result_id: int, *, force: bool = False, retry_failed: bool = False) -> str:
        """Narrow, single-row claim+process -- mirrors
        tests/test_ocr.py's own _claim_and_process_one exactly, never
        touching any row in the shared dev database besides result_id,
        even with force=True/retry_failed=True."""
        with get_session_factory()() as session:
            claimed = vp._claim_specific_rows(session, [result_id], retry_failed=retry_failed, force=force, current_model_version=None, now=datetime.now(timezone.utc))
        self.assertEqual(len(claimed), 1, f"result_id={result_id} was not claimable with force={force}, retry_failed={retry_failed}")
        _claimed_id, token = claimed[0]
        with get_session_factory()() as session:
            return vp._process_claimed_result(session, get_settings().storage_root, result_id, token)

    def test_project_image_visual_description_creates_document_and_sets_visual_document_id(self):
        project_id = self._create_project("Vision Test Project Image")
        color = (210, 30, 30)
        image_id = self._upload_image(project_id, "crack.png", color=color)

        def tagged(prompt):
            if _color_of_image_bytes(prompt.images[0].data) == color:
                return GenerationResult(text="A visible crack runs across a concrete surface.")
            return GenerationResult(text="unrelated")

        with _patch_vision_provider(tagged):
            self._run_vision()

        with get_session_factory()() as session:
            asset = session.get(ProjectImageAsset, image_id)
            self.assertEqual(asset.status, "processed")
            self.assertIsNotNone(asset.visual_document_id)
            self.assertIsNone(asset.document_id, "vision processing alone must never set the OCR document_id")

            document = session.get(Document, asset.visual_document_id)
            self.assertEqual(document.project_id, project_id)
            self.assertEqual(document.derivation_kind, "visual_description")

            chunks = session.scalars(select(DocumentChunk).where(DocumentChunk.document_id == document.id)).all()
            self.assertEqual(len(chunks), 1)
            self.assertIn("crack", chunks[0].chunk_text)

    def test_email_attachment_visual_description_resolves_correct_parent_and_project(self):
        project_id = self._create_project("Vision Test Email")
        color = (211, 31, 31)
        raw = _build_eml(
            headers={"Message-ID": "<vision-email@example.com>", "From": "a@example.com", "Subject": "Site", "Date": formatdate()},
            body="see attached",
            attachments=[{"filename": "site.png", "content": _build_test_image(color=color, fmt="PNG"), "maintype": "image", "subtype": "png"}],
        )
        self.client.post(f"/projects/{project_id}/emails/import", files={"files": ("x.eml", io.BytesIO(raw), "message/rfc822")})

        def tagged(prompt):
            if _color_of_image_bytes(prompt.images[0].data) == color:
                return GenerationResult(text="Scaffolding visible around a partially built structure.")
            return GenerationResult(text="unrelated")

        with _patch_vision_provider(tagged):
            self._run_vision()

        with get_session_factory()() as session:
            attachment = session.scalar(
                select(EmailAttachment).where(
                    EmailAttachment.filename == "site.png",
                    EmailAttachment.message_id.in_(select(EmailMessage.document_id).where(EmailMessage.project_id == project_id)),
                )
            )
            self.assertIsNotNone(attachment.visual_document_id)
            document = session.get(Document, attachment.visual_document_id)
            self.assertEqual(document.project_id, project_id)
            self.assertEqual(attachment.status, "processed")

    def test_whatsapp_attachment_visual_description_resolves_correct_parent_and_project(self):
        project_id = self._create_project("Vision Test WhatsApp")
        color = (212, 32, 32)
        zip_bytes = _build_whatsapp_zip(
            text="[25/03/24, 10:00:00] Alice: <attached: pic.png>\n",
            media={"pic.png": _build_test_image(color=color, fmt="PNG")},
        )
        self.client.post(f"/projects/{project_id}/whatsapp/import", files={"file": ("chat.zip", io.BytesIO(zip_bytes), "application/zip")})

        def tagged(prompt):
            if _color_of_image_bytes(prompt.images[0].data) == color:
                return GenerationResult(text="Steel reinforcement bars stacked on site.")
            return GenerationResult(text="unrelated")

        with _patch_vision_provider(tagged):
            self._run_vision()

        with get_session_factory()() as session:
            attachment = session.scalar(
                select(WhatsAppMediaAttachment).where(
                    WhatsAppMediaAttachment.filename == "pic.png",
                    WhatsAppMediaAttachment.message_id.in_(select(WhatsAppMessage.document_id).where(WhatsAppMessage.project_id == project_id)),
                )
            )
            self.assertIsNotNone(attachment.visual_document_id)
            document = session.get(Document, attachment.visual_document_id)
            self.assertEqual(document.project_id, project_id)
            self.assertEqual(attachment.status, "processed")

    def test_visual_description_is_retrievable_and_passes_citation_verification(self):
        project_id = self._create_project("Vision Test Retrieval Citation")
        color = (213, 33, 33)
        image_id = self._upload_image(project_id, "defect.png", color=color)

        def tagged(prompt):
            if _color_of_image_bytes(prompt.images[0].data) == color:
                return GenerationResult(text="Visible corrosion staining on a metal support bracket.")
            return GenerationResult(text="unrelated")

        with _patch_vision_provider(tagged):
            self._run_vision()

        with get_session_factory()() as session:
            asset = session.get(ProjectImageAsset, image_id)
            document_id = asset.visual_document_id
            chunk = session.scalar(select(DocumentChunk).where(DocumentChunk.document_id == document_id))
            chunk_id = chunk.id
            chunk_text = chunk.chunk_text

        from app.agent.citation_verification import verify_citations
        from app.agent.models import Citation
        from app.retrieval.service import search_chunks

        with get_session_factory()() as session:
            results = search_chunks(session, "corrosion metal bracket", top_k=5, project_id=project_id)
        self.assertTrue(any(r.chunk_id == chunk_id for r in results), "a visual-description chunk must be retrievable through the existing, unmodified retrieval path")

        candidate = Citation(document_id=document_id, chunk_id=chunk_id, page=1, relevance_score=0.9, chunk_text=chunk_text)
        verified = verify_citations([candidate], retrieved_evidence=[candidate])
        self.assertEqual(len(verified), 1, "a visual-description citation must pass the existing, unmodified citation-verification path unchanged")

    def test_image_with_readable_text_produces_independent_ocr_and_visual_description_evidence(self):
        project_id = self._create_project("Vision Test OCR Plus Visual Independent")
        color = (214, 34, 34)
        image_id = self._upload_image(project_id, "notice.png", color=color)

        with pp_patch(color, "SITE NOTICE: stop work order issued") as _:
            self._run_ocr()

        def tagged(prompt):
            if _color_of_image_bytes(prompt.images[0].data) == color:
                return GenerationResult(text="A printed notice posted on a wooden barrier.")
            return GenerationResult(text="unrelated")

        with _patch_vision_provider(tagged):
            self._run_vision()

        with get_session_factory()() as session:
            asset = session.get(ProjectImageAsset, image_id)
            self.assertIsNotNone(asset.document_id, "OCR's own Document must exist")
            self.assertIsNotNone(asset.visual_document_id, "the visual-description Document must ALSO exist")
            self.assertNotEqual(asset.document_id, asset.visual_document_id, "OCR and vision must be two SEPARATE Documents")

            ocr_document = session.get(Document, asset.document_id)
            visual_document = session.get(Document, asset.visual_document_id)
            self.assertEqual(ocr_document.derivation_kind, "ocr_transcription")
            self.assertEqual(visual_document.derivation_kind, "visual_description")

            ocr_chunks = session.scalars(select(DocumentChunk).where(DocumentChunk.document_id == ocr_document.id)).all()
            visual_chunks = session.scalars(select(DocumentChunk).where(DocumentChunk.document_id == visual_document.id)).all()
            self.assertIn("stop work order", ocr_chunks[0].chunk_text)
            self.assertIn("wooden barrier", visual_chunks[0].chunk_text)

    def test_empty_ocr_does_not_block_visual_description_processing(self):
        project_id = self._create_project("Vision Test Empty OCR Does Not Block")
        color = (215, 35, 35)
        image_id = self._upload_image(project_id, "blank_text.png", color=color)

        with pp_patch(color, "   ") as _:
            self._run_ocr()

        with get_session_factory()() as session:
            asset = session.get(ProjectImageAsset, image_id)
            self.assertIsNone(asset.document_id, "empty OCR text must create no Document")

        def tagged(prompt):
            if _color_of_image_bytes(prompt.images[0].data) == color:
                return GenerationResult(text="A close-up of unpainted drywall with no visible text.")
            return GenerationResult(text="unrelated")

        with _patch_vision_provider(tagged):
            self._run_vision()

        with get_session_factory()() as session:
            asset = session.get(ProjectImageAsset, image_id)
            self.assertIsNone(asset.document_id, "OCR's own (empty) outcome must be unaffected by vision running")
            self.assertIsNotNone(asset.visual_document_id, "empty OCR must never block visual-description processing")

    def test_image_byte_size_limit_is_enforced_before_calling_the_provider(self):
        project_id = self._create_project("Vision Test Byte Limit")
        color = (216, 36, 36)
        image_id = self._upload_image(project_id, "oversized.png", color=color)

        never_called = MagicMock(side_effect=AssertionError("the provider must never be called once the byte limit is exceeded"))

        with patch.object(get_settings(), "vision_max_image_bytes", 1):
            with _patch_vision_provider(never_called):
                self._run_vision()

        with get_session_factory()() as session:
            result = session.scalar(select(ImageVisualDescriptionResult).where(ImageVisualDescriptionResult.project_image_asset_id == image_id))
            self.assertEqual(result.status, "failed")
            self.assertIn("byte", result.error)
            asset = session.get(ProjectImageAsset, image_id)
            self.assertIsNone(asset.visual_document_id)

    def test_tampered_storage_key_is_refused_and_marked_failed(self):
        project_id = self._create_project("Vision Test Tampered Path")
        image_id = self._upload_image(project_id, "tampered.png")

        with get_session_factory()() as session:
            asset = session.get(ProjectImageAsset, image_id)
            asset.storage_key = "../../../../etc/passwd_attempt"
            session.commit()

        never_called = MagicMock(side_effect=AssertionError("the provider must never be called for an unresolvable image"))
        with _patch_vision_provider(never_called):
            self._run_vision()

        with get_session_factory()() as session:
            result = session.scalar(select(ImageVisualDescriptionResult).where(ImageVisualDescriptionResult.project_image_asset_id == image_id))
            self.assertEqual(result.status, "failed")

    def test_provider_failure_on_reprocess_preserves_previous_successful_visual_evidence(self):
        project_id = self._create_project("Vision Test Preserve On Failure")
        color = (217, 37, 37)
        image_id = self._upload_image(project_id, "stable.png", color=color)

        def first_pass(prompt):
            if _color_of_image_bytes(prompt.images[0].data) == color:
                return GenerationResult(text="original good description")
            return GenerationResult(text="unrelated")

        with _patch_vision_provider(first_pass):
            self._run_vision()

        with get_session_factory()() as session:
            asset = session.get(ProjectImageAsset, image_id)
            original_document_id = asset.visual_document_id
            original_text_path = session.scalar(
                select(ImageVisualDescriptionResult.description_text_path).where(ImageVisualDescriptionResult.project_image_asset_id == image_id)
            )
            result_id = session.scalar(select(ImageVisualDescriptionResult.id).where(ImageVisualDescriptionResult.project_image_asset_id == image_id))

        def failing_reprocess(prompt):
            raise LLMProviderError("simulated reprocess provider failure")

        with _patch_vision_provider(failing_reprocess):
            outcome = self._claim_and_process_one_visual(result_id, force=True, retry_failed=True)
        self.assertEqual(outcome, "failed")

        with get_session_factory()() as session:
            asset = session.get(ProjectImageAsset, image_id)
            self.assertEqual(asset.visual_document_id, original_document_id, "a failed reprocess must leave the parent's visual_document_id untouched")
            result = session.scalar(select(ImageVisualDescriptionResult).where(ImageVisualDescriptionResult.id == result_id))
            self.assertEqual(result.status, "completed", "the previous completed visual description must be preserved, not marked failed")
            self.assertEqual(result.description_text_path, original_text_path)
            self.assertTrue(Path(original_text_path).exists())
            chunks = session.scalars(select(DocumentChunk).where(DocumentChunk.document_id == original_document_id)).all()
            self.assertIn("original good description", chunks[0].chunk_text)

    def test_genuine_client_error_on_reprocess_is_handled_as_a_failed_attempt_and_preserves_previous_evidence(self):
        """Pre-commit review follow-up: the SAME preserve-on-failure
        guarantee as the test above, but driven by a REAL
        google.genai.errors.ClientError raised from the (mocked) SDK
        client -- through the real, unmocked GeminiProvider.generate()
        and generate_visual_description(), never through a fake
        LLMProviderError injected directly. Confirms the actual
        exception-translation code path (gemini_provider.py's own
        `except APIError` -- ClientError is a real APIError subclass,
        verified against the installed SDK) converts a genuine API
        rejection into the existing LLMProviderError abstraction, and
        that app/vision/process_pending.py then handles it exactly like
        any other provider failure: a clean 'failed' outcome, with the
        previous completed Document/chunks left untouched."""
        project_id = self._create_project("Vision Test Real ClientError Preserve")
        color = (222, 42, 42)
        image_id = self._upload_image(project_id, "clienterror.png", color=color)

        def first_pass(prompt):
            if _color_of_image_bytes(prompt.images[0].data) == color:
                return GenerationResult(text="original good description")
            return GenerationResult(text="unrelated")

        with _patch_vision_provider(first_pass):
            self._run_vision()

        with get_session_factory()() as session:
            asset = session.get(ProjectImageAsset, image_id)
            original_document_id = asset.visual_document_id
            original_text_path = session.scalar(
                select(ImageVisualDescriptionResult.description_text_path).where(ImageVisualDescriptionResult.project_image_asset_id == image_id)
            )
            result_id = session.scalar(select(ImageVisualDescriptionResult.id).where(ImageVisualDescriptionResult.project_image_asset_id == image_id))

        fake_client = MagicMock()
        fake_client.models.generate_content.side_effect = genai_errors.ClientError(
            400,
            {"error": {"code": 400, "message": "Image input is not supported for this model.", "status": "INVALID_ARGUMENT"}},
        )
        # Patches only the SDK client construction, NOT GeminiProvider
        # itself -- the real generate()/generate_visual_description()
        # code runs, exactly as it would against a genuine rejection; no
        # live network call is made since the client is this fake. The
        # api-key check is also forced to pass deterministically here
        # (independent of whatever GEMINI_API_KEY this environment's own
        # .env happens to have), so this test exercises the ClientError
        # conversion itself, not a "no key configured" short-circuit.
        with patch("app.llm.gemini_provider.get_settings", return_value=MagicMock(gemini_api_key="fake-key-for-test", gemini_model="fake-model")):
            with patch.object(GeminiProvider, "_get_client", return_value=fake_client):
                outcome = self._claim_and_process_one_visual(result_id, force=True, retry_failed=True)
        self.assertEqual(outcome, "failed")

        with get_session_factory()() as session:
            asset = session.get(ProjectImageAsset, image_id)
            self.assertEqual(asset.visual_document_id, original_document_id, "a failed reprocess must leave the parent's visual_document_id untouched")
            result = session.scalar(select(ImageVisualDescriptionResult).where(ImageVisualDescriptionResult.id == result_id))
            self.assertEqual(result.status, "completed", "the previous completed visual description must be preserved, not marked failed")
            self.assertEqual(result.description_text_path, original_text_path)
            self.assertTrue(Path(original_text_path).exists())
            document = session.get(Document, original_document_id)
            self.assertEqual(document.derivation_kind, "visual_description", "the preserved Document's own provenance must be untouched")
            chunks = session.scalars(select(DocumentChunk).where(DocumentChunk.document_id == original_document_id)).all()
            self.assertIn("original good description", chunks[0].chunk_text)

    def test_worker_that_loses_its_lease_after_the_provider_call_commits_no_document_or_chunk_changes(self):
        project_id = self._create_project("Vision Test Lease Lost After Provider Call")
        color = (218, 38, 38)
        image_id = self._upload_image(project_id, "race.png", color=color)

        with get_session_factory()() as session:
            ensure_pending_visual_result(session, project_image_asset_id=image_id)
            result_id = session.scalar(select(ImageVisualDescriptionResult.id).where(ImageVisualDescriptionResult.project_image_asset_id == image_id))

        with get_session_factory()() as session:
            claimed = vp._claim_specific_rows(session, [result_id], retry_failed=False, force=False, current_model_version=None, now=datetime.now(timezone.utc))
        self.assertEqual(len(claimed), 1)
        _claimed_id, token_a = claimed[0]

        def steal_lease_during_call(prompt):
            with get_session_factory()() as other_session:
                other_session.execute(
                    update(ImageVisualDescriptionResult)
                    .where(ImageVisualDescriptionResult.id == result_id)
                    .values(lease_token="a-different-workers-token", lease_expires_at=datetime.now(timezone.utc) + timedelta(seconds=60))
                )
                other_session.commit()
            return GenerationResult(text="text a stale worker must never publish")

        with get_session_factory()() as session:
            with _patch_vision_provider(steal_lease_during_call):
                outcome = vp._process_claimed_result(session, get_settings().storage_root, result_id, token_a)

        self.assertEqual(outcome, "skipped")
        with get_session_factory()() as session:
            asset = session.get(ProjectImageAsset, image_id)
            self.assertIsNone(asset.visual_document_id, "a worker that lost its lease must never publish a Document")
            all_documents_for_project = session.scalars(select(Document).where(Document.project_id == project_id)).all()
            self.assertEqual(len(all_documents_for_project), 0, "a worker that lost its lease must commit no Document at all")

    def test_genuine_concurrent_workers_claim_the_same_row_exactly_once(self):
        """Real threads, real Postgres sessions -- mirrors
        tests/test_ocr.py's own genuine-concurrency tests exactly,
        applied to ImageVisualDescriptionResult's own, separate lease."""
        project_id = self._create_project("Vision Test Real Concurrency")
        color = (219, 39, 39)
        image_id = self._upload_image(project_id, "concurrent.png", color=color)

        with get_session_factory()() as session:
            ensure_pending_visual_result(session, project_image_asset_id=image_id)
            result_id = session.scalar(select(ImageVisualDescriptionResult.id).where(ImageVisualDescriptionResult.project_image_asset_id == image_id))

        barrier = threading.Barrier(3)
        outcomes: list[list | None] = [None, None, None]

        def worker(index: int) -> None:
            barrier.wait(timeout=5)
            with get_session_factory()() as session:
                outcomes[index] = vp._claim_specific_rows(session, [result_id], retry_failed=False, force=False, current_model_version=None, now=datetime.now(timezone.utc))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        non_empty = [o for o in outcomes if o]
        self.assertEqual(len(non_empty), 1, "exactly one thread must claim the contested row")

    def test_citation_source_lookup_resolves_to_the_original_image_for_a_visual_description(self):
        project_id = self._create_project("Vision Test Citation Source Lookup")
        color = (220, 40, 40)
        original_bytes = _build_test_image(color=color, fmt="PNG")
        resp_upload = self.client.post(
            f"/projects/{project_id}/documents",
            files={"files": ("lookup.png", io.BytesIO(original_bytes), "image/png")},
        )
        image_id = resp_upload.json()["images"][0]["id"]

        def tagged(prompt):
            if _color_of_image_bytes(prompt.images[0].data) == color:
                return GenerationResult(text="A worker in a high-visibility vest standing near scaffolding.")
            return GenerationResult(text="unrelated")

        with _patch_vision_provider(tagged):
            self._run_vision()

        with get_session_factory()() as session:
            asset = session.get(ProjectImageAsset, image_id)
            document_id = asset.visual_document_id

        resp = self.client.get(f"/projects/{project_id}/documents/{document_id}")
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body["derivation_kind"], "visual_description")
        self.assertIsNotNone(body["image_source"])
        self.assertEqual(body["image_source"]["source_kind"], "project_image")
        self.assertEqual(body["image_source"]["image_id"], image_id)

        image_resp = self.client.get(f"/projects/{project_id}/images/{body['image_source']['image_id']}/file")
        self.assertEqual(image_resp.status_code, 200)
        self.assertEqual(image_resp.content, original_bytes, "the citation must lead back to the exact original image bytes, never the generated description")

        other_project_id = self._create_project("Vision Test Citation Source Lookup -- Other Project")
        cross_project_resp = self.client.get(f"/projects/{other_project_id}/images/{image_id}/file")
        self.assertEqual(cross_project_resp.status_code, 404, "an image must never be reachable from a different project")


class VisionCliGatingTests(unittest.TestCase):
    """Pre-commit review follow-up: app.vision.process_pending.main()'s
    explicit opt-in kill switch (Settings.vision_processing_enabled,
    default False) must refuse to run BEFORE anything else -- no
    Gemini API key check, no database access, no call to
    process_pending() at all. Mirrors tests/test_ocr.py's own
    CliArgumentValidationTests class conventions exactly (patch.object
    on the module's own imported names, assert_not_called on the
    downstream function, no database access in this class)."""

    def test_disabled_switch_exits_without_processing_and_without_needing_an_api_key(self):
        """The disabled path must not even reach the API-key check --
        gemini_api_key is deliberately left unset/None here to prove
        the two gates are independent and ordered correctly (disabled
        switch first)."""
        fake_settings = MagicMock(vision_processing_enabled=False, gemini_api_key=None)
        with patch.object(vp, "get_settings", return_value=fake_settings):
            with patch.object(vp, "process_pending") as mock_process:
                exit_code = vp.main([])
        self.assertEqual(exit_code, 1)
        mock_process.assert_not_called()

    def test_disabled_switch_wins_even_when_an_api_key_is_configured(self):
        """The kill switch is checked first regardless of whether a
        Gemini API key happens to be configured -- an operator with a
        valid key but the switch left at its default (False) must
        still see no processing happen."""
        fake_settings = MagicMock(vision_processing_enabled=False, gemini_api_key="a-real-looking-key")
        with patch.object(vp, "get_settings", return_value=fake_settings):
            with patch.object(vp, "process_pending") as mock_process:
                exit_code = vp.main([])
        self.assertEqual(exit_code, 1)
        mock_process.assert_not_called()

    def test_enabled_switch_with_no_api_key_still_refuses_but_for_the_other_reason(self):
        """Once the switch is enabled, the pre-existing API-key gate
        still applies independently -- enabling vision processing alone
        must never bypass the "no key configured" safeguard."""
        fake_settings = MagicMock(vision_processing_enabled=True, gemini_api_key=None)
        with patch.object(vp, "get_settings", return_value=fake_settings):
            with patch.object(vp, "process_pending") as mock_process:
                exit_code = vp.main([])
        self.assertEqual(exit_code, 1)
        mock_process.assert_not_called()


class _OcrTagContext:
    """Tiny helper so test_vision.py can run OCR with a single tagged
    color/text pair without duplicating tests/test_ocr.py's own full
    BatchProcessingTests machinery -- patches exactly the same
    pytesseract boundary that file's own tests do."""

    def __init__(self, color: tuple, text: str):
        self._color = color
        self._text = text
        self._patches: list = []

    def __enter__(self):
        from app.ocr import tesseract_provider as tp

        def tagged(image, lang=None, timeout=0, **kwargs):
            return self._text if image.convert("RGB").getpixel((0, 0)) == self._color else "unrelated"

        self._patches = [
            patch.object(tp.shutil, "which", return_value="/usr/bin/tesseract"),
            patch.object(tp.pytesseract, "image_to_string", side_effect=tagged),
            patch.object(tp.pytesseract, "get_tesseract_version", return_value="5.3.4"),
        ]
        for p in self._patches:
            p.__enter__()
        return self

    def __exit__(self, *exc_info):
        for p in reversed(self._patches):
            p.__exit__(*exc_info)


def pp_patch(color: tuple, text: str) -> _OcrTagContext:
    return _OcrTagContext(color, text)


if __name__ == "__main__":
    unittest.main()
