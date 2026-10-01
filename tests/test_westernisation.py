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


class TestLevelValue(unittest.TestCase):

    def test_no_prefix_is_zero(self):
        self.assertEqual(westernisation.level_value("no_land_reform"), "0")
        self.assertEqual(westernisation.level_value("no_army_schools"), "0")

    def test_yes_prefix_is_one(self):
        self.assertEqual(westernisation.level_value("yes_land_reform"), "1")
        self.assertEqual(westernisation.level_value("land_reform_enacted"), "1")

    def test_two_suffix_is_two(self):
        self.assertEqual(westernisation.level_value("finance_reform_two"), "2")


class TestExtractWesternisation(unittest.TestCase):

    def test_enacted_levels_are_kept_as_numbers(self):
        block = (
            "land_reform=yes_land_reform\n"
            "army_schools=yes_army_schools\n"
        )
        self.assertEqual(
            westernisation.extract_westernisation(block),
            {
                "land_reform": "1",
                "army_schools": "1",
            },
        )

    def test_zero_levels_are_omitted(self):
        # A nation still at no_* has nothing enacted: empty state.
        block = (
            "land_reform=no_land_reform\n"
            "army_schools=no_army_schools\n"
        )
        self.assertEqual(westernisation.extract_westernisation(block), {})

    def test_second_level_is_two(self):
        block = "finance_reform=finance_reform_two\n"
        self.assertEqual(
            westernisation.extract_westernisation(block),
            {"finance_reform": "2"},
        )

    def test_missing_keys_are_skipped_not_errors(self):
        # A civilised nation's block has none of the westernisation keys.
        self.assertEqual(
            westernisation.extract_westernisation(
                "wage_reform=no_minimum_wage\nschool_reforms=low_schools\n"
            ),
            {},
        )

    def test_uncivilised_block_returns_only_enacted(self):
        block = (
            "civilized=no\n"
            "land_reform=yes_land_reform\n"
            "army_schools=no_army_schools\n"
        )
        self.assertEqual(
            westernisation.extract_westernisation(block),
            {"land_reform": "1"},
        )

    def test_first_save_with_active_reforms_is_preserved(self):
        # A late-started history must not drop reforms already enacted.
        block = (
            "land_reform=yes_land_reform\n"
            "finance_reform=finance_reform_two\n"
            "army_schools=no_army_schools\n"
        )
        self.assertEqual(
            westernisation.extract_westernisation(block),
            {"land_reform": "1", "finance_reform": "2"},
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

    def test_raw_helper_keeps_level_names(self):
        block = (
            "land_reform=no_land_reform\n"
            "army_schools=yes_army_schools\n"
        )
        self.assertEqual(
            westernisation.extract_raw_westernisation(block),
            {
                "land_reform": "no_land_reform",
                "army_schools": "yes_army_schools",
            },
        )

    def test_real_example_save_jap_block_is_all_zero(self):
        # 1836 Japan sits at no_* everywhere: numeric state is empty,
        # while the raw helper still sees all 15 levels.
        text = EXAMPLE_SAVE.read_text(encoding="utf-8", errors="replace")
        block = parsing.extract_country_block(text, "JAP")
        self.assertEqual(westernisation.extract_westernisation(block), {})
        raw = westernisation.extract_raw_westernisation(block)
        self.assertEqual(len(raw), 15)
        self.assertTrue(
            all(value.startswith("no_") for value in raw.values())
        )
        self.assertEqual(raw["land_reform"], "no_land_reform")

    def test_real_example_save_eng_block_is_empty(self):
        text = EXAMPLE_SAVE.read_text(encoding="utf-8", errors="replace")
        block = parsing.extract_country_block(text, "ENG")
        self.assertEqual(westernisation.extract_westernisation(block), {})

    def test_real_example_1845_jap_block_has_enacted_reforms(self):
        text = EXAMPLE_1845_SAVE.read_text(encoding="utf-8", errors="replace")
        block = parsing.extract_country_block(text, "JAP")
        levels = westernisation.extract_westernisation(block)
        self.assertEqual(levels["land_reform"], "1")
        self.assertIn("education_reform", levels)
        # Zero-level reforms are omitted, not stored as "0".
        self.assertNotIn("army_schools", levels)

    def test_real_example_1850_jap_block_is_deactivated(self):
        # Civilised (westernised) Japan keeps stale reform lines in
        # the save; they must not be tracked as active.
        text = EXAMPLE_1850_SAVE.read_text(encoding="utf-8", errors="replace")
        block = parsing.extract_country_block(text, "JAP")
        self.assertIn("civilized=yes", block)
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
                    "land_reform": "1",
                    "army_schools": "1",
                },
            )
            self.assertEqual(
                changed,
                {
                    "land_reform": ("0", "1"),
                    "army_schools": ("0", "1"),
                },
            )
            self.assertEqual(
                read_csv(out),
                [
                    ["date", "westernisation", "old_value", "new_value"],
                    ["1836-01-02", "army_schools", "0", "1"],
                    ["1836-01-02", "land_reform", "0", "1"],
                ],
            )

    def test_first_date_preserves_second_level(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "westernisation_changes.csv"
            changed = westernisation.append_westernisation_changes(
                out,
                "1845-01-01",
                {},
                {"finance_reform": "2", "land_reform": "1"},
            )
            self.assertEqual(
                changed,
                {
                    "finance_reform": ("0", "2"),
                    "land_reform": ("0", "1"),
                },
            )
            self.assertEqual(
                read_csv(out),
                [
                    ["date", "westernisation", "old_value", "new_value"],
                    ["1845-01-01", "finance_reform", "0", "2"],
                    ["1845-01-01", "land_reform", "0", "1"],
                ],
            )
            self.assertEqual(
                westernisation.load_westernisation_state(out),
                {"finance_reform": "2", "land_reform": "1"},
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
                {"land_reform": "1"},
            )
            changed = westernisation.append_westernisation_changes(
                out,
                "1836-02-01",
                {"land_reform": "1"},
                {
                    "land_reform": "2",
                    "army_schools": "1",
                },
            )
            self.assertEqual(
                changed,
                {
                    "land_reform": ("1", "2"),
                    "army_schools": ("0", "1"),
                },
            )
            self.assertEqual(
                read_csv(out),
                [
                    ["date", "westernisation", "old_value", "new_value"],
                    ["1836-01-02", "land_reform", "0", "1"],
                    ["1836-02-01", "army_schools", "0", "1"],
                    [
                        "1836-02-01",
                        "land_reform",
                        "1",
                        "2",
                    ],
                ],
            )

    def test_disappeared_key_is_recorded_as_zero(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "westernisation_changes.csv"
            westernisation.append_westernisation_changes(
                out,
                "1836-01-02",
                {},
                {"land_reform": "1"},
            )
            changed = westernisation.append_westernisation_changes(
                out, "1836-02-01", {"land_reform": "1"}, {}
            )
            self.assertEqual(changed, {"land_reform": ("1", "0")})
            rows = read_csv(out)
            self.assertIn(["1836-02-01", "land_reform", "1", "0"], rows)
            self.assertEqual(westernisation.load_westernisation_state(out), {})

    def test_westernisation_date_deactivates_full_set(self):
        # Simulates the date the player westernises: the previous
        # state holds enacted levels, the current (civilised) state
        # is empty, so every reform records a -> 0 row.
        previous = {
            "land_reform": "1",
            "army_schools": "1",
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
                    "land_reform": ("1", "0"),
                    "army_schools": ("1", "0"),
                },
            )
            self.assertEqual(
                read_csv(out),
                [
                    ["date", "westernisation", "old_value", "new_value"],
                    ["1850-02-01", "army_schools", "0", "1"],
                    ["1850-02-01", "land_reform", "0", "1"],
                    ["1850-02-24", "army_schools", "1", "0"],
                    ["1850-02-24", "land_reform", "1", "0"],
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
                {"land_reform": "1"},
            )
            before = read_csv(out)
            changed = westernisation.append_westernisation_changes(
                out,
                "1836-02-01",
                {"land_reform": "1"},
                {"land_reform": "1"},
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
                {"a_reform": "1", "b_reform": "1"},
            )
            westernisation.append_westernisation_changes(
                out,
                "1836-03-01",
                {"a_reform": "1", "b_reform": "1"},
                {"b_reform": "2"},
            )
            self.assertEqual(
                westernisation.load_westernisation_state(out),
                {"b_reform": "2"},
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

    def test_old_raw_format_warns_and_replays_to_empty(self):
        # Files written before the numeric scheme hold raw level names
        # and empty-string absence: they must not mix with the new
        # history, so they replay to empty with a warning (fresh
        # history required).
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "westernisation_changes.csv"
            out.write_text(
                "date,westernisation,old_value,new_value\n"
                "1836-01-02,land_reform,,no_land_reform\n",
                encoding="utf-8",
            )
            err = io.StringIO()
            with redirect_stderr(err):
                result = westernisation.load_westernisation_state(out)
            self.assertEqual(result, {})
            self.assertIn("Warning", err.getvalue())


if __name__ == "__main__":
    unittest.main()
