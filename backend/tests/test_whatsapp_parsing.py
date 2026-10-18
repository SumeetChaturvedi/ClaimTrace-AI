"""Deterministic, offline tests for app/whatsapp_ingestion/parsing.py
(Phase W1: WhatsApp Export Ingestion) -- no database, no network, pure
text-in/structured-data-out, mirroring test_email_parsing.py's own style.

All fixtures below are synthetic construction-project conversations
invented for this test file, never real personal WhatsApp data.

Run with:
    cd backend && source .venv/bin/activate
    PYTHONPATH=. python3 -m unittest tests.test_whatsapp_parsing -v
"""

import unittest

from app.whatsapp_ingestion.parsing import WhatsAppParseError, parse_whatsapp_export


class IOSFormatTests(unittest.TestCase):
    def test_bracketed_ios_format_with_seconds_parses_sender_time_and_text(self):
        chat = parse_whatsapp_export(
            "[25/03/24, 10:00:00] Site Engineer: Checking on the delay notice for Block C."
        )
        message = chat.messages[0]
        self.assertEqual(message.sender_name, "Site Engineer")
        self.assertEqual(message.text, "Checking on the delay notice for Block C.")
        self.assertEqual(message.sent_at.isoformat(), "2024-03-25T10:00:00")
        self.assertFalse(message.sent_at_ambiguous)
        self.assertEqual(message.message_type, "text")


class AndroidFormatTests(unittest.TestCase):
    def test_hyphen_android_format_without_seconds_parses_correctly(self):
        chat = parse_whatsapp_export("25/03/24, 9:30 AM - Project Manager: Please send the updated programme.")
        message = chat.messages[0]
        self.assertEqual(message.sender_name, "Project Manager")
        self.assertEqual(message.text, "Please send the updated programme.")
        self.assertEqual(message.sent_at.isoformat(), "2024-03-25T09:30:00")

    def test_12_hour_pm_time_is_converted_to_24_hour(self):
        chat = parse_whatsapp_export("01/02/24, 2:15 PM - Foreman: Concrete pour delayed by rain.")
        self.assertEqual(chat.messages[0].sent_at.hour, 14)


class MultilineMessageTests(unittest.TestCase):
    def test_continuation_lines_are_appended_to_the_previous_message(self):
        text = (
            "[25/03/24, 10:00:00] Site Engineer: Summary of today's site visit:\n"
            "1. Formwork inspected\n"
            "2. Rebar placement delayed\n"
            "[25/03/24, 10:05:00] Project Manager: Thanks, noted."
        )
        chat = parse_whatsapp_export(text)
        self.assertEqual(len(chat.messages), 2)
        self.assertEqual(
            chat.messages[0].text,
            "Summary of today's site visit:\n1. Formwork inspected\n2. Rebar placement delayed",
        )

    def test_leading_continuation_before_any_recognized_message_is_preserved_not_dropped(self):
        text = "stray leading text with no timestamp\n[25/03/24, 10:00:00] A: real message"
        chat = parse_whatsapp_export(text)
        self.assertEqual(len(chat.messages), 2)
        self.assertEqual(chat.messages[0].sender_name, None)
        self.assertIn("stray leading text", chat.messages[0].text)
        self.assertTrue(any("leading content" in note for note in chat.parse_notes))


class UnicodeAndPunctuationSenderTests(unittest.TestCase):
    def test_unicode_name_with_emoji_and_punctuation_is_preserved_verbatim(self):
        chat = parse_whatsapp_export("[01/01/24, 08:00:00] José Müller 🏗️ (Site): Buenos días, revisando el sitio.")
        self.assertEqual(chat.messages[0].sender_name, "José Müller 🏗️ (Site)")
        self.assertEqual(chat.messages[0].text, "Buenos días, revisando el sitio.")

    def test_sender_name_containing_a_colon_in_the_message_text_does_not_confuse_the_split(self):
        """The split is on the FIRST ': ' only -- a message whose own text
        contains a colon must not be mistaken for a second sender."""
        chat = parse_whatsapp_export("[01/01/24, 08:00:00] Alice: Note: see the attached drawing for details")
        self.assertEqual(chat.messages[0].sender_name, "Alice")
        self.assertEqual(chat.messages[0].text, "Note: see the attached drawing for details")


class SystemAndDeletedMessageTests(unittest.TestCase):
    def test_system_message_with_no_sender_shape_is_classified_system_with_no_fabricated_sender(self):
        chat = parse_whatsapp_export("[01/01/24, 08:00:00] Messages and calls are end-to-end encrypted.")
        message = chat.messages[0]
        self.assertIsNone(message.sender_name)
        self.assertEqual(message.message_type, "system")

    def test_group_event_message_is_classified_system(self):
        chat = parse_whatsapp_export("[01/01/24, 08:00:00] Site Engineer added Project Manager")
        self.assertEqual(chat.messages[0].message_type, "system")
        self.assertIsNone(chat.messages[0].sender_name)

    def test_deleted_message_marker_is_classified_deleted_not_text(self):
        chat = parse_whatsapp_export("[01/01/24, 08:00:00] Alice: This message was deleted")
        self.assertEqual(chat.messages[0].message_type, "deleted")
        self.assertEqual(chat.messages[0].sender_name, "Alice")


class MediaPlaceholderTests(unittest.TestCase):
    def test_android_attached_placeholder_extracts_the_referenced_filename(self):
        chat = parse_whatsapp_export("[01/01/24, 08:00:00] Alice: <attached: IMG-20240101-WA0001.jpg>")
        message = chat.messages[0]
        self.assertEqual(message.message_type, "media")
        self.assertEqual(message.media_filename, "IMG-20240101-WA0001.jpg")

    def test_ios_file_attached_placeholder_extracts_the_referenced_filename(self):
        chat = parse_whatsapp_export("[01/01/24, 08:00:00] Bob: site-photo.jpg (file attached)")
        message = chat.messages[0]
        self.assertEqual(message.message_type, "media")
        self.assertEqual(message.media_filename, "site-photo.jpg")

    def test_media_omitted_with_no_filename_is_media_type_with_no_fabricated_filename(self):
        chat = parse_whatsapp_export("[01/01/24, 08:00:00] Alice: image omitted")
        message = chat.messages[0]
        self.assertEqual(message.message_type, "media")
        self.assertIsNone(message.media_filename)


class TimestampAmbiguityTests(unittest.TestCase):
    def test_both_day_and_month_under_13_is_flagged_ambiguous_with_a_default_day_first_reading(self):
        chat = parse_whatsapp_export("[03/04/24, 10:00:00] A: hi")
        message = chat.messages[0]
        self.assertTrue(message.sent_at_ambiguous)
        # Default reading is day-first: day=3, month=4 -> April 3rd.
        self.assertEqual((message.sent_at.month, message.sent_at.day), (4, 3))

    def test_day_over_12_is_unambiguous_regardless_of_which_position_it_is_in(self):
        chat = parse_whatsapp_export("[25/03/24, 10:00:00] A: hi\n[03/25/24, 10:00:00] B: hi")
        first, second = chat.messages
        self.assertFalse(first.sent_at_ambiguous)
        self.assertFalse(second.sent_at_ambiguous)
        self.assertEqual((first.sent_at.month, first.sent_at.day), (3, 25))
        self.assertEqual((second.sent_at.month, second.sent_at.day), (3, 25))

    def test_missing_or_invalid_date_leaves_sent_at_none_and_records_a_note_never_fabricated(self):
        chat = parse_whatsapp_export("[32/13/24, 10:00:00] A: an impossible date")
        message = chat.messages[0]
        self.assertIsNone(message.sent_at)
        self.assertEqual(message.raw_timestamp_text, "32/13/24, 10:00:00")
        self.assertTrue(any("unparseable date" in note for note in chat.parse_notes))

    def test_original_timestamp_text_is_always_preserved_even_when_unparseable(self):
        chat = parse_whatsapp_export("[99/99/24, 25:99:99] A: nonsense timestamp")
        self.assertEqual(chat.messages[0].raw_timestamp_text, "99/99/24, 25:99:99")
        self.assertIsNone(chat.messages[0].sent_at)


class MalformedInputTests(unittest.TestCase):
    def test_empty_input_raises_parse_error(self):
        with self.assertRaises(WhatsAppParseError):
            parse_whatsapp_export("")

    def test_whitespace_only_input_raises_parse_error(self):
        with self.assertRaises(WhatsAppParseError):
            parse_whatsapp_export("   \n\n   ")

    def test_input_with_no_recognizable_message_line_at_all_raises_parse_error(self):
        with self.assertRaises(WhatsAppParseError):
            parse_whatsapp_export("this is just some random text\nwith no timestamps anywhere")

    def test_a_single_malformed_line_among_otherwise_valid_ones_does_not_crash_the_whole_import(self):
        text = (
            "[25/03/24, 10:00:00] Alice: first real message\n"
            "####not a message line at all####\n"
            "[25/03/24, 10:05:00] Bob: second real message"
        )
        chat = parse_whatsapp_export(text)
        # The malformed line is folded into the preceding message as a
        # continuation -- not dropped, not crashing the parse.
        self.assertEqual(len(chat.messages), 2)
        self.assertIn("####not a message line", chat.messages[0].text)


class SequenceOrderingTests(unittest.TestCase):
    def test_sequence_index_is_assigned_in_export_order_starting_at_zero(self):
        text = "\n".join(
            f"[25/03/24, 10:0{i}:00] Alice: message {i}" for i in range(5)
        )
        chat = parse_whatsapp_export(text)
        self.assertEqual([m.sequence_index for m in chat.messages], [0, 1, 2, 3, 4])


if __name__ == "__main__":
    unittest.main()
