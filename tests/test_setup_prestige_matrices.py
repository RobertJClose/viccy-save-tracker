"""
Tests for the prestige matrices setup (setup/build_prestige_matrices.py).

Run from the repository root:

    python -m unittest discover -s tests -v
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from setup import build_prestige_matrices
from helpers import CAT_SAVE, make_category_game_dir


class TestPrestigeRows(unittest.TestCase):

    def test_rows_match_agreed_set(self):
        self.assertEqual(
            build_prestige_matrices.ROWS,
            (
                "permanent_prestige",
                "prestige",
                "shared_prestige",
            ),
        )

    def test_filename(self):
        self.assertEqual(
            build_prestige_matrices.FILENAME, "prestige_modifiers.csv"
        )


class TestPrestigeMain(unittest.TestCase):

    def run_main(self, root: Path, *extra: str) -> Path:
        game_dir = make_category_game_dir(root)
        out = root / "out"
        out.mkdir()
        return build_prestige_matrices.main(
            ["--game-dir", str(game_dir), "--output-dir", str(out),
             "--source", "modded", *extra]
        )

    def test_writes_expected_files(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            result = self.run_main(root)
            out = root / "out"
            self.assertEqual(result, out)
            expected = {
                Path("tech_modifiers/army/prestige_modifiers.csv"),
                Path("invention_modifiers/army/prestige_modifiers.csv"),
                Path("westernisation_modifiers/economic/prestige_modifiers.csv"),
                Path("westernisation_modifiers/military/prestige_modifiers.csv"),
            }
            self.assertEqual(
                {p.relative_to(out) for p in out.rglob("*.csv")}, expected
            )
            self.assertEqual(
                (out / "tech_modifiers/army/prestige_modifiers.csv").read_text(
                    encoding="utf-8"
                ),
                "modifier,col_tech,plain_tech\n"
                "permanent_prestige,0,0\n"
                "prestige,0.05,0\n"
                "shared_prestige,0,0\n",
            )
            self.assertEqual(
                (
                    out
                    / "invention_modifiers/army/prestige_modifiers.csv"
                ).read_text(encoding="utf-8"),
                "modifier,col_invention,effectless_invention\n"
                "permanent_prestige,1,0\n"
                "prestige,0,0\n"
                "shared_prestige,0,0\n",
            )

    def test_westernisation_files_hold_only_zeros(self):
        # Fixed rows are always emitted; reforms grant none of these.
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            out = self.run_main(root)
            self.assertEqual(
                (
                    out
                    / "westernisation_modifiers/economic/prestige_modifiers.csv"
                ).read_text(encoding="utf-8"),
                "modifier,no_land_reform,yes_land_reform\n"
                "permanent_prestige,0,0\n"
                "prestige,0,0\n"
                "shared_prestige,0,0\n",
            )
            self.assertEqual(
                (
                    out
                    / "westernisation_modifiers/military/prestige_modifiers.csv"
                ).read_text(encoding="utf-8"),
                "modifier,no_army_schools,yes_army_schools\n"
                "permanent_prestige,0,0\n"
                "prestige,0,0\n"
                "shared_prestige,0,0\n",
            )

    def test_vanilla_anchors_reject_fixture(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            game_dir = make_category_game_dir(root)
            out = root / "out"
            out.mkdir()
            with self.assertRaises(ValueError):
                build_prestige_matrices.main(
                    ["--game-dir", str(game_dir), "--output-dir", str(out)]
                )
            self.assertEqual(list(out.rglob("*.csv")), [])

    def test_check_save_validates(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            save = root / "test.v2"
            save.write_text(CAT_SAVE, encoding="utf-8")
            self.run_main(root, "--check-save", str(save))

    def test_check_save_rejects_unknown_tech(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            save = root / "test.v2"
            save.write_text(
                CAT_SAVE.replace("col_tech", "mystery_tech"), encoding="utf-8"
            )
            with self.assertRaises(ValueError):
                self.run_main(root, "--check-save", str(save))

    def test_missing_output_dir_errors(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            game_dir = make_category_game_dir(root)
            with self.assertRaises(SystemExit):
                build_prestige_matrices.main(
                    [
                        "--game-dir", str(game_dir),
                        "--output-dir", str(root / "nope"),
                        "--source", "modded",
                    ]
                )

    def test_missing_game_dir_raises(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            out = root / "out"
            out.mkdir()
            with self.assertRaises(FileNotFoundError):
                build_prestige_matrices.main(
                    [
                        "--game-dir", str(root / "nope"),
                        "--output-dir", str(out),
                        "--source", "modded",
                    ]
                )


if __name__ == "__main__":
    unittest.main()
