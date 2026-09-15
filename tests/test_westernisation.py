"""
Tests for westernisation extraction and changes CSV (westernisation.py).

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
from domains import westernisation
from helpers import EXAMPLE_SAVE, REPO_ROOT, read_csv

EXAMPLE_1845_SAVE = REPO_ROOT / "example_saves" / "example_japan_1845.v2"
EXAMPLE_1850_SAVE = REPO_ROOT / "example_saves" / "example_japan_1850.v2"


class TestExtractWesternisation(unittest.TestCase):

    def test_extracts_present_levels(self):
        block = (
            "land_reform=no_land_reform\n"
            "army_schools=no_army_schools\n"
        )
        self.assertEqual(
            westernisation.extract_westernisation(block),
            {
                "land_reform": "no_land_reform",
                "army_schools": "no_army_schools",
            },
        )

    def test_missing_keys_are_skipped_not_errors(self):
        # A civilised nation's block has none of the westernisation keys.
        self.assertEqual(
            westernisation.extract_westernisation(
                "wage_reform=no_minimum_wage\nschool_reforms=low_schools\n"
            ),
            {},
        )

    def test_uncivilised_block_returns_levels(self):
        block = (
            "civilized=no\n"
            "land_reform=yes_land_reform\n"
            "army_schools=no_army_schools\n"
        )
        self.assertEqual(
            westernisation.extract_westernisation(block),
            {
                "land_reform": "yes_land_reform",
                "army_schools": "no_army_schools",
            },
        )

    def test_civilised_block_ignores_stale_keys(self):
        # A newly westernised nation keeps its reform lines in the
        # save, but their effects are deactivated.
        block = (
            "civilized=yes\n"
            "land_reform=yes_land_reform\n"
            "army_schools=no_army_schools\n"
        )
        self.assertEqual(westernisation.extract_westernisation(block), {})

    def test_civilised_match_tolerates_spacing(self):
        block = "civilized = yes\nland_reform=yes_land_reform\n"
        self.assertEqual(westernisation.extract_westernisation(block), {})

    def test_empty_block_yields_empty_dict(self):
        self.assertEqual(westernisation.extract_westernisation(""), {})

    def test_key_match_is_exact(self):
        # A longer key name sharing a prefix must not match.
        block = "land_reform_extra=no_land_reform\n"
        self.assertEqual(westernisation.extract_westernisation(block), {})

    def test_real_example_save_jap_block(self):
        text = EXAMPLE_SAVE.read_text(encoding="utf-8", errors="replace")
        block = parsing.extract_country_block(text, "JAP")
        levels = westernisation.extract_westernisation(block)
        self.assertEqual(len(levels), 15)
        self.assertTrue(
            all(value.startswith("no_") for value in levels.values())
        )
        self.assertEqual(levels["land_reform"], "no_land_reform")

    def test_real_example_save_eng_block_is_empty(self):
        text = EXAMPLE_SAVE.read_text(encoding="utf-8", errors="replace")
        block = parsing.extract_country_block(text, "ENG")
        self.assertEqual(westernisation.extract_westernisation(block), {})

    def test_real_example_1845_jap_block_is_still_active(self):
        text = EXAMPLE_1845_SAVE.read_text(encoding="utf-8", errors="replace")
        block = parsing.extract_country_block(text, "JAP")
        levels = westernisation.extract_westernisation(block)
        self.assertEqual(len(levels), 15)
        self.assertEqual(levels["land_reform"], "yes_land_reform")

    def test_real_example_1850_jap_block_is_deactivated(self):
        # Civilised (westernised) Japan keeps stale reform lines in
        # the save; they must not be tracked as active.
        text = EXAMPLE_1850_SAVE.read_text(encoding="utf-8", errors="replace")
        block = parsing.extract_country_block(text, "JAP")
        self.assertIn("civilized=yes", block)
        self.assertIn("land_reform=", block)
        self.assertEqual(westernisation.extract_westernisation(block), {})


class TestWesternisationChanges(unittest.TestCase):

    def test_first_date_writes_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "westernisation_changes.csv"
            changed = westernisation.append_westernisation_changes(
                out,
                "1836-01-02",
                {},
                {
                    "land_reform": "no_land_reform",
                    "army_schools": "no_army_schools",
                },
            )
            self.assertEqual(
                changed,
                {
                    "land_reform": ("", "no_land_reform"),
                    "army_schools": ("", "no_army_schools"),
                },
            )
            self.assertEqual(
                read_csv(out),
                [
                    ["date", "westernisation", "old_value", "new_value"],
                    ["1836-01-02", "army_schools", "", "no_army_schools"],
                    ["1836-01-02", "land_reform", "", "no_land_reform"],
                ],
            )

    def test_first_date_with_no_westernisation_writes_header_only(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "westernisation_changes.csv"
            changed = westernisation.append_westernisation_changes(
                out, "1836-01-02", {}, {}
            )
            self.assertEqual(changed, {})
            self.assertEqual(
                read_csv(out),
                [["date", "westernisation", "old_value", "new_value"]],
            )

    def test_later_date_appends_only_deltas(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "westernisation_changes.csv"
            westernisation.append_westernisation_changes(
                out,
                "1836-01-02",
                {},
                {"land_reform": "no_land_reform"},
            )
            changed = westernisation.append_westernisation_changes(
                out,
                "1836-02-01",
                {"land_reform": "no_land_reform"},
                {
                    "land_reform": "land_reform_enacted",
                    "army_schools": "no_army_schools",
                },
            )
            self.assertEqual(
                changed,
                {
                    "land_reform": ("no_land_reform", "land_reform_enacted"),
                    "army_schools": ("", "no_army_schools"),
                },
            )
            self.assertEqual(
                read_csv(out),
                [
                    ["date", "westernisation", "old_value", "new_value"],
                    ["1836-01-02", "land_reform", "", "no_land_reform"],
                    ["1836-02-01", "army_schools", "", "no_army_schools"],
                    [
                        "1836-02-01",
                        "land_reform",
                        "no_land_reform",
                        "land_reform_enacted",
                    ],
                ],
            )

    def test_disappeared_key_is_recorded(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "westernisation_changes.csv"
            westernisation.append_westernisation_changes(
                out,
                "1836-01-02",
                {},
                {"land_reform": "no_land_reform"},
            )
            changed = westernisation.append_westernisation_changes(
                out, "1836-02-01", {"land_reform": "no_land_reform"}, {}
            )
            self.assertEqual(
                changed, {"land_reform": ("no_land_reform", "")}
            )
            rows = read_csv(out)
            self.assertIn(["1836-02-01", "land_reform", "no_land_reform", ""], rows)
            self.assertEqual(westernisation.load_westernisation_state(out), {})

    def test_westernisation_date_deactivates_full_set(self):
        # Simulates the date the player westernises: the previous
        # state holds enacted levels, the current (civilised) state
        # is empty, so every reform records a disappearance row.
        previous = {
            "land_reform": "yes_land_reform",
            "army_schools": "no_army_schools",
        }
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "westernisation_changes.csv"
            westernisation.append_westernisation_changes(
                out, "1850-02-01", {}, previous
            )
            changed = westernisation.append_westernisation_changes(
                out, "1850-02-24", previous, {}
            )
            self.assertEqual(
                changed,
                {
                    "land_reform": ("yes_land_reform", ""),
                    "army_schools": ("no_army_schools", ""),
                },
            )
            self.assertEqual(
                read_csv(out),
                [
                    ["date", "westernisation", "old_value", "new_value"],
                    ["1850-02-01", "army_schools", "", "no_army_schools"],
                    ["1850-02-01", "land_reform", "", "yes_land_reform"],
                    ["1850-02-24", "army_schools", "no_army_schools", ""],
                    ["1850-02-24", "land_reform", "yes_land_reform", ""],
                ],
            )
            self.assertEqual(westernisation.load_westernisation_state(out), {})

    def test_unchanged_date_appends_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "westernisation_changes.csv"
            westernisation.append_westernisation_changes(
                out,
                "1836-01-02",
                {},
                {"land_reform": "no_land_reform"},
            )
            before = read_csv(out)
            changed = westernisation.append_westernisation_changes(
                out,
                "1836-02-01",
                {"land_reform": "no_land_reform"},
                {"land_reform": "no_land_reform"},
            )
            self.assertEqual(changed, {})
            self.assertEqual(read_csv(out), before)

    def test_replay_reconstructs_state(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "westernisation_changes.csv"
            westernisation.append_westernisation_changes(
                out, "1836-01-02", {}, {}
            )
            westernisation.append_westernisation_changes(
                out,
                "1836-02-01",
                {},
                {"a_reform": "no_a", "b_reform": "no_b"},
            )
            westernisation.append_westernisation_changes(
                out,
                "1836-03-01",
                {"a_reform": "no_a", "b_reform": "no_b"},
                {"b_reform": "yes_b"},
            )
            self.assertEqual(
                westernisation.load_westernisation_state(out),
                {"b_reform": "yes_b"},
            )

    def test_missing_file_replays_to_empty(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(
                westernisation.load_westernisation_state(
                    Path(d) / "westernisation_changes.csv"
                ),
                {},
            )

    def test_corrupt_file_warns_and_replays_to_empty(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "westernisation_changes.csv"
            out.write_text("date,reform\n1836-01-02\n", encoding="utf-8")
            err = io.StringIO()
            with redirect_stderr(err):
                result = westernisation.load_westernisation_state(out)
            self.assertEqual(result, {})
            self.assertIn("Warning", err.getvalue())


if __name__ == "__main__":
    unittest.main()
