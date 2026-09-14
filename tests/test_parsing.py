"""
Tests for save parsing helpers (core.parsing.extract_*).

Run from the repository root:

    python -m unittest discover -s tests -v
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core import parsing
from helpers import MINIMAL_SAVE


class TestExtractGameDate(unittest.TestCase):

    def test_single_digit_month_and_day_are_zero_padded(self):
        self.assertEqual(parsing.extract_game_date(MINIMAL_SAVE), "1836-01-02")

    def test_already_padded_date_round_trips(self):
        text = 'date="1836.04.01"\n'
        self.assertEqual(parsing.extract_game_date(text), "1836-04-01")

    def test_two_digit_month_and_day(self):
        text = 'date="1836.12.31"\n'
        self.assertEqual(parsing.extract_game_date(text), "1836-12-31")

    def test_missing_date_raises(self):
        with self.assertRaises(ValueError):
            parsing.extract_game_date("no date line in here\n")

    def test_indented_date_line_is_not_matched(self):
        # Indented date lines (e.g. building_construction blocks) must not be
        # mistaken for the header. Only a line starting at column 0 is matched.
        text = 'player="JAP"\n\tdate="1836.5.6"\n'
        with self.assertRaises(ValueError):
            parsing.extract_game_date(text)

    def test_non_header_date_key_is_not_matched(self):
        text = 'price_history_last_update="1836.1.1"\n'
        with self.assertRaises(ValueError):
            parsing.extract_game_date(text)


class TestReadSave(unittest.TestCase):

    def test_reads_plain_text(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "save.v2"
            p.write_text('date="1836.1.2"\ncoal=1\n', encoding="utf-8")
            self.assertEqual(
                parsing.read_save(p),
                'date="1836.1.2"\ncoal=1\n',
            )

    def test_invalid_utf8_byte_is_replaced_not_fatal(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "save.v2"
            p.write_bytes(b'date="1836.1.2"\ncoal=1\n\xff\n')
            self.assertEqual(
                parsing.read_save(p),
                'date="1836.1.2"\ncoal=1\n\ufffd\n',
            )


class TestExtractPlayerTag(unittest.TestCase):

    def test_returns_player_tag(self):
        self.assertEqual(parsing.extract_player_tag(MINIMAL_SAVE), "JAP")

    def test_missing_player_raises(self):
        with self.assertRaises(ValueError):
            parsing.extract_player_tag('date="1836.1.2"\n')

    def test_indented_player_line_is_not_matched(self):
        with self.assertRaises(ValueError):
            parsing.extract_player_tag('\tplayer="JAP"\n')


class TestExtractCountryBlock(unittest.TestCase):

    def test_isolates_tag_block_at_column_zero(self):
        text = (
            'player="JAP"\n'
            'country="JAP"\n'
            "JAP=\n"
            "{\n"
            "\ttechnology=\n"
            "\t{\n"
            "\t}\n"
            "}\n"
        )
        block = parsing.extract_country_block(text, "JAP")
        self.assertIn("technology=", block)
        self.assertNotIn("player=", block)
        self.assertNotIn("country=", block)

    def test_missing_tag_raises(self):
        with self.assertRaises(ValueError):
            parsing.extract_country_block('player="JAP"\n', "JAP")

    def test_unbalanced_braces_raise(self):
        with self.assertRaises(ValueError):
            parsing.extract_country_block("JAP=\n{\n\ttechnology=\n", "JAP")


if __name__ == "__main__":
    unittest.main()
