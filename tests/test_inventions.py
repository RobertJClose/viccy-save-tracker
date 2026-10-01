"""
Tests for player invention extraction and changes CSV (inventions.py).

Run from the repository root:

    python -m unittest discover -s tests -v
"""

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core import parsing
from domains import inventions
from helpers import EXAMPLE_SAVE, REPO_ROOT, read_csv


class TestExtractInventionIds(unittest.TestCase):

    def test_extracts_ids(self):
        block = (
            "active_inventions=\n"
            "{\n"
            "\t1 20 37\n"
            "}\n"
        )
        self.assertEqual(
            inventions.extract_invention_ids(block), {1, 20, 37}
        )

    def test_empty_block_yields_empty_set(self):
        self.assertEqual(
            inventions.extract_invention_ids("active_inventions=\n{\n}\n"),
            set(),
        )

    def test_missing_block_yields_empty_set(self):
        # An uncivilised nation at game start has nothing invented yet.
        self.assertEqual(
            inventions.extract_invention_ids("human=yes\n"), set()
        )
        self.assertEqual(inventions.extract_invention_ids(""), set())

    def test_illegal_block_is_ignored(self):
        block = (
            "illegal_inventions=\n"
            "{\n"
            "\t1 2 3\n"
            "}\n"
            "active_inventions=\n"
            "{\n"
            "\t20\n"
            "}\n"
        )
        self.assertEqual(inventions.extract_invention_ids(block), {20})

    def test_bad_token_raises(self):
        with self.assertRaises(ValueError):
            inventions.extract_invention_ids(
                "active_inventions=\n{\n\t1 abc\n}\n"
            )

    def test_real_example_save_jap_block_is_empty(self):
        text = EXAMPLE_SAVE.read_text(encoding="utf-8", errors="replace")
        block = parsing.extract_country_block(text, "JAP")
        self.assertEqual(inventions.extract_invention_ids(block), set())

    def test_real_example_save_eng_block(self):
        text = EXAMPLE_SAVE.read_text(encoding="utf-8", errors="replace")
        block = parsing.extract_country_block(text, "ENG")
        ids = inventions.extract_invention_ids(block)
        self.assertIn(1, ids)
        self.assertIn(20, ids)
        self.assertIn(37, ids)
        self.assertGreater(len(ids), 30)


class TestInventionMap(unittest.TestCase):

    def test_loads_vanilla_map(self):
        found = inventions.load_invention_map()
        # Index == ID, index 0 unused.
        self.assertEqual(len(found) - 1, 387)
        self.assertEqual(found[1], "post_napoleonic_army_doctrine")
        self.assertEqual(found[37], "cuirassier_activation")
        self.assertEqual(found[38], "dragoon_activation")
        self.assertEqual(found[39], "hussar_activation")

    def test_resolves_names(self):
        found = inventions.load_invention_map()
        self.assertEqual(
            inventions.resolve_invention_names({1, 37}, found),
            {"post_napoleonic_army_doctrine", "cuirassier_activation"},
        )

    def test_unknown_id_raises(self):
        found = inventions.load_invention_map()
        with self.assertRaises(ValueError):
            inventions.resolve_invention_names({len(found) + 5}, found)
        with self.assertRaises(ValueError):
            inventions.resolve_invention_names({0}, found)

    def test_missing_map_file_raises(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileNotFoundError):
                inventions.load_invention_map(Path(d) / "missing.json")

    def test_corrupt_map_file_raises(self):
        with tempfile.TemporaryDirectory() as d:
            bad = Path(d) / "bad.json"
            bad.write_text("{not json", encoding="utf-8")
            with self.assertRaises(ValueError):
                inventions.load_invention_map(bad)

    def test_extract_inventions_combines_ids_and_map(self):
        found = inventions.load_invention_map()
        block = "active_inventions=\n{\n\t1 37\n}\n"
        self.assertEqual(
            inventions.extract_inventions(block, found),
            {"post_napoleonic_army_doctrine", "cuirassier_activation"},
        )


class TestInventionChanges(unittest.TestCase):

    def test_first_date_writes_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "invention_changes.csv"
            acquired, lost = inventions.append_invention_changes(
                out, "1836-01-02", set(), {"b_inv", "a_inv"}
            )
            self.assertEqual(acquired, {"a_inv", "b_inv"})
            self.assertEqual(lost, set())
            self.assertEqual(
                read_csv(out),
                [
                    ["date", "invention", "old_value", "new_value"],
                    ["1836-01-02", "a_inv", "0", "1"],
                    ["1836-01-02", "b_inv", "0", "1"],
                ],
            )

    def test_first_date_with_no_inventions_writes_header_only(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "invention_changes.csv"
            acquired, lost = inventions.append_invention_changes(
                out, "1836-01-02", set(), set()
            )
            self.assertEqual(acquired, set())
            self.assertEqual(lost, set())
            self.assertEqual(
                read_csv(out),
                [["date", "invention", "old_value", "new_value"]],
            )

    def test_later_date_appends_only_deltas(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "invention_changes.csv"
            inventions.append_invention_changes(
                out, "1836-01-02", set(), {"a_inv"}
            )
            acquired, lost = inventions.append_invention_changes(
                out, "1836-02-01", {"a_inv"}, {"a_inv", "b_inv"}
            )
            self.assertEqual(acquired, {"b_inv"})
            self.assertEqual(lost, set())
            self.assertEqual(
                read_csv(out),
                [
                    ["date", "invention", "old_value", "new_value"],
                    ["1836-01-02", "a_inv", "0", "1"],
                    ["1836-02-01", "b_inv", "0", "1"],
                ],
            )

    def test_lost_invention_is_recorded(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "invention_changes.csv"
            inventions.append_invention_changes(
                out, "1836-01-02", set(), {"a_inv", "b_inv"}
            )
            acquired, lost = inventions.append_invention_changes(
                out, "1836-02-01", {"a_inv", "b_inv"}, {"a_inv"}
            )
            self.assertEqual(acquired, set())
            self.assertEqual(lost, {"b_inv"})
            rows = read_csv(out)
            self.assertIn(["1836-02-01", "b_inv", "1", "0"], rows)
            self.assertEqual(
                inventions.load_invention_state(out), {"a_inv"}
            )

    def test_unchanged_date_appends_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "invention_changes.csv"
            inventions.append_invention_changes(
                out, "1836-01-02", set(), {"a_inv"}
            )
            before = read_csv(out)
            acquired, lost = inventions.append_invention_changes(
                out, "1836-02-01", {"a_inv"}, {"a_inv"}
            )
            self.assertEqual(acquired, set())
            self.assertEqual(lost, set())
            self.assertEqual(read_csv(out), before)

    def test_replay_reconstructs_state(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "invention_changes.csv"
            inventions.append_invention_changes(
                out, "1836-01-02", set(), set()
            )
            inventions.append_invention_changes(
                out, "1836-02-01", set(), {"a_inv", "b_inv"}
            )
            inventions.append_invention_changes(
                out, "1836-03-01", {"a_inv", "b_inv"}, {"b_inv", "c_inv"}
            )
            self.assertEqual(
                inventions.load_invention_state(out), {"b_inv", "c_inv"}
            )

    def test_missing_file_replays_to_empty(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(
                inventions.load_invention_state(
                    Path(d) / "invention_changes.csv"
                ),
                set(),
            )

    def test_corrupt_file_warns_and_replays_to_empty(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "invention_changes.csv"
            out.write_text("date,invention\n1836-01-02\n", encoding="utf-8")
            err = io.StringIO()
            with redirect_stderr(err):
                result = inventions.load_invention_state(out)
            self.assertEqual(result, set())
            self.assertIn("Warning", err.getvalue())


if __name__ == "__main__":
    unittest.main()
