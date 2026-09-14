"""
Tests for player technology extraction and changes CSV (technologies.py).

Run from the repository root:

    python -m unittest discover -s tests -v
"""

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core import parsing
from domains import technologies
from helpers import EXAMPLE_SAVE, read_csv


class TestExtractTechnologies(unittest.TestCase):

    def test_extracts_unlocked_names_ignoring_values(self):
        block = (
            "technology=\n"
            "{\n"
            "\tflintlock_rifles={1 0.000}\n"
            "\tclean_coal={1 0.000}\n"
            "}\n"
        )
        self.assertEqual(
            technologies.extract_technologies(block),
            {"flintlock_rifles", "clean_coal"},
        )

    def test_empty_block_yields_empty_set(self):
        self.assertEqual(
            technologies.extract_technologies("technology=\n{\n}\n"),
            set(),
        )

    def test_research_block_is_ignored(self):
        block = (
            "research=\n"
            "{\n"
            "\ttechnology=romanticism\n"
            "}\n"
            "technology=\n"
            "{\n"
            "\tflintlock_rifles={1 0.000}\n"
            "}\n"
        )
        self.assertEqual(
            technologies.extract_technologies(block),
            {"flintlock_rifles"},
        )

    def test_missing_block_raises(self):
        with self.assertRaises(ValueError):
            technologies.extract_technologies("human=yes\n")

    def test_real_example_save_eng_block(self):
        text = EXAMPLE_SAVE.read_text(encoding="utf-8", errors="replace")
        block = parsing.extract_country_block(text, "ENG")
        techs = technologies.extract_technologies(block)
        self.assertEqual(len(techs), 35)
        self.assertIn("flintlock_rifles", techs)
        self.assertIn("clean_coal", techs)
        # Currently being researched, not unlocked.
        self.assertNotIn("iron_muzzle_loaded_artillery", techs)


class TestTechnologyChanges(unittest.TestCase):

    def test_first_date_writes_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "technology_changes.csv"
            acquired, lost = technologies.append_technology_changes(
                out, "1836-01-02", set(), {"clean_coal", "flintlock_rifles"}
            )
            self.assertEqual(acquired, {"clean_coal", "flintlock_rifles"})
            self.assertEqual(lost, set())
            self.assertEqual(
                read_csv(out),
                [
                    ["date", "technology", "old_value", "new_value"],
                    ["1836-01-02", "clean_coal", "0", "1"],
                    ["1836-01-02", "flintlock_rifles", "0", "1"],
                ],
            )

    def test_first_date_with_no_techs_writes_header_only(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "technology_changes.csv"
            acquired, lost = technologies.append_technology_changes(
                out, "1836-01-02", set(), set()
            )
            self.assertEqual(acquired, set())
            self.assertEqual(lost, set())
            self.assertEqual(
                read_csv(out),
                [["date", "technology", "old_value", "new_value"]],
            )

    def test_later_date_appends_only_deltas(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "technology_changes.csv"
            technologies.append_technology_changes(
                out, "1836-01-02", set(), {"flintlock_rifles"}
            )
            acquired, lost = technologies.append_technology_changes(
                out,
                "1836-02-01",
                {"flintlock_rifles"},
                {"flintlock_rifles", "clean_coal"},
            )
            self.assertEqual(acquired, {"clean_coal"})
            self.assertEqual(lost, set())
            self.assertEqual(
                read_csv(out),
                [
                    ["date", "technology", "old_value", "new_value"],
                    ["1836-01-02", "flintlock_rifles", "0", "1"],
                    ["1836-02-01", "clean_coal", "0", "1"],
                ],
            )

    def test_lost_technology_is_recorded(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "technology_changes.csv"
            technologies.append_technology_changes(
                out, "1836-01-02", set(), {"a_tech", "b_tech"}
            )
            acquired, lost = technologies.append_technology_changes(
                out, "1836-02-01", {"a_tech", "b_tech"}, {"a_tech"}
            )
            self.assertEqual(acquired, set())
            self.assertEqual(lost, {"b_tech"})
            rows = read_csv(out)
            self.assertIn(["1836-02-01", "b_tech", "1", "0"], rows)
            self.assertEqual(
                technologies.load_technology_state(out), {"a_tech"}
            )

    def test_unchanged_date_appends_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "technology_changes.csv"
            technologies.append_technology_changes(
                out, "1836-01-02", set(), {"flintlock_rifles"}
            )
            before = read_csv(out)
            acquired, lost = technologies.append_technology_changes(
                out,
                "1836-02-01",
                {"flintlock_rifles"},
                {"flintlock_rifles"},
            )
            self.assertEqual(acquired, set())
            self.assertEqual(lost, set())
            self.assertEqual(read_csv(out), before)

    def test_replay_reconstructs_state(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "technology_changes.csv"
            technologies.append_technology_changes(
                out, "1836-01-02", set(), set()
            )
            technologies.append_technology_changes(
                out, "1836-02-01", set(), {"a_tech", "b_tech"}
            )
            technologies.append_technology_changes(
                out, "1836-03-01", {"a_tech", "b_tech"}, {"b_tech", "c_tech"}
            )
            self.assertEqual(
                technologies.load_technology_state(out),
                {"b_tech", "c_tech"},
            )

    def test_missing_file_replays_to_empty(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(
                technologies.load_technology_state(
                    Path(d) / "technology_changes.csv"
                ),
                set(),
            )

    def test_corrupt_file_warns_and_replays_to_empty(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "technology_changes.csv"
            out.write_text("date,technology\n1836-01-02\n", encoding="utf-8")
            err = io.StringIO()
            with redirect_stderr(err):
                result = technologies.load_technology_state(out)
            self.assertEqual(result, set())
            self.assertIn("Warning", err.getvalue())


if __name__ == "__main__":
    unittest.main()
