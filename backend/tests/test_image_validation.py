"""Focused, deterministic, offline tests for app/ingestion/image_validation.py
-- no database, no TestClient, mirroring test_whatsapp_ingestion.py's own
WhatsAppZipSafetyTests class ("deterministic, offline tests... no database").

Pre-commit review regression (W2.0 fix pass): validate_image() previously
let PIL's own Image.DecompressionBombError/-Warning propagate uncaught out
of Image.open() -- a declared-pixel-count check Pillow performs BEFORE
this module's own signature/dimension checks ever run, and which a small,
highly-compressible file (e.g. a solid-color PNG) can trigger while still
passing the byte-size limit. Mocked here for determinism (no huge image
allocation in the routine tests), plus one real, non-mocked regression
test reproducing the exact reported failure.

Run with:
    cd backend && source .venv/bin/activate
    PYTHONPATH=. python3 -m unittest tests.test_image_validation -v
"""

import io
import unittest
import warnings
from unittest.mock import patch

from PIL import Image

from app.ingestion import image_validation as iv
from app.ingestion.image_validation import sniff_image_signature, validate_image


def _build_test_image(*, size: tuple[int, int] = (64, 48), color=(10, 120, 200), fmt: str = "PNG") -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color=color).save(buf, format=fmt)
    return buf.getvalue()


class DecompressionBombHandlingTests(unittest.TestCase):
    """Deterministic (mocked) coverage of both of Pillow's own
    decompression-bomb outcomes -- never allocating an actual huge image
    buffer here, per this phase's own "don't depend on huge images in
    routine tests" requirement."""

    def test_decompression_bomb_error_during_open_becomes_a_clean_invalid_result(self):
        valid_png_bytes = _build_test_image()

        with patch.object(iv.Image, "open", side_effect=iv.Image.DecompressionBombError("mocked bomb error")):
            result = validate_image(valid_png_bytes)

        self.assertFalse(result.valid)
        self.assertIsNotNone(result.error)
        self.assertIn("mocked bomb error", result.error)
        # Never partially populated on a rejection.
        self.assertIsNone(result.extension)
        self.assertIsNone(result.width)

    def test_decompression_bomb_warning_during_open_is_treated_as_a_rejection(self):
        valid_png_bytes = _build_test_image()

        def _warn_then_raise_via_filter(*args, **kwargs):
            # Mirrors what Pillow itself does: emit the warning through the
            # real warnings machinery so validate_image()'s own
            # warnings.simplefilter("error", ...) scoping is what actually
            # converts it, not a shortcut that bypasses that mechanism.
            warnings.warn("mocked bomb warning", iv.Image.DecompressionBombWarning)
            raise AssertionError("unreachable: the warning above must have been escalated to an exception first")

        with patch.object(iv.Image, "open", side_effect=_warn_then_raise_via_filter):
            result = validate_image(valid_png_bytes)

        self.assertFalse(result.valid)
        self.assertIsNotNone(result.error)
        self.assertIn("mocked bomb warning", result.error)

    def test_decompression_bomb_warning_conversion_does_not_leak_globally(self):
        """The warnings.catch_warnings()/simplefilter scoping must be local
        to this one call -- it must not change how DecompressionBombWarning
        (or anything else) behaves for unrelated code after validate_image()
        returns."""
        original_filters = list(warnings.filters)
        valid_png_bytes = _build_test_image()

        with patch.object(iv.Image, "open", side_effect=iv.Image.DecompressionBombError("mocked")):
            validate_image(valid_png_bytes)

        self.assertEqual(warnings.filters, original_filters)

    def test_a_realistic_oversized_image_within_pillows_warning_tier_is_rejected_cleanly(self):
        """Non-mocked regression test reproducing the exact confirmed
        failure at a scale cheap enough for a routine test: Pillow's own
        MAX_IMAGE_PIXELS default is 89,478,485 -- a 10000x10000 image
        (100,000,000 pixels) is just over that WARNING tier, compresses to
        well under this module's own MAX_IMAGE_BYTES limit (it's a solid
        color), and builds in well under a second -- no huge allocation."""
        image_bytes = _build_test_image(size=(10_000, 10_000), color=(5, 5, 5))
        self.assertLess(len(image_bytes), iv.MAX_IMAGE_BYTES, "must pass the byte-size check to reach Pillow's own guard")

        result = validate_image(image_bytes)

        self.assertFalse(result.valid)
        self.assertIsNotNone(result.error)
        self.assertIn("decompression bomb", result.error.lower())

    def test_ordinary_valid_image_is_unaffected_by_the_bomb_handling_change(self):
        """Regression guard: the fix must not change the outcome for a
        perfectly normal image."""
        image_bytes = _build_test_image(size=(64, 48))
        result = validate_image(image_bytes)
        self.assertTrue(result.valid)
        self.assertEqual((result.width, result.height), (64, 48))

    def test_existing_rejection_paths_are_unaffected_by_the_bomb_handling_change(self):
        # Empty file.
        self.assertFalse(validate_image(b"").valid)
        # Not a recognized image signature at all.
        self.assertFalse(validate_image(b"plain text, not an image").valid)
        # A real JPEG signature with undecodable bytes behind it.
        fake_jpeg = b"\xff\xd8\xff\xe0" + b"not a real jpeg body" * 5
        corrupt_result = validate_image(fake_jpeg)
        self.assertFalse(corrupt_result.valid)
        self.assertIn("could not read image", corrupt_result.error)
        # A real, truncated JPEG.
        full = _build_test_image(size=(100, 100), fmt="JPEG")
        truncated_result = validate_image(full[: len(full) // 2])
        self.assertFalse(truncated_result.valid)

    def test_sniff_image_signature_is_unaffected_by_the_bomb_handling_change(self):
        jpeg_bytes = _build_test_image(fmt="JPEG")
        self.assertEqual(sniff_image_signature(jpeg_bytes), (".jpg", "image/jpeg"))
        self.assertIsNone(sniff_image_signature(b"not an image"))


if __name__ == "__main__":
    unittest.main()
