"""
Tests for the rebels matrices setup (setup/research_modifiers/build_rebels_matrices.py).

Run from the repository root:

    python -m unittest discover -s tests -v
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from setup.research_modifiers import build_rebels_matrices
from helpers import REB_SAVE, make_rebels_game_dir

ZERO_ROWS = (
    "global_pop_militancy_modifier,0,0\n"
    "rebel_org_gain_all,0,0\n"
    "rebel_org_gain_communist_rebels,0,0\n"
    "rebel_org_gain_fascist_rebels,0,0\n"
    "rebel_org_gain_nationalist_rebels,0,0\n"
    "rebel_org_gain_reactionary_rebels,0,0\n"
    "seperatism,0,0\n"
    "suppression_points_modifier,0,0\n"
)


class TestRebelsRows(unittest.TestCase):

    def test_rows_match_agreed_set(self):
        self.assertEqual(
            build_rebels_matrices.ROWS,
            (
                "global_pop_militancy_modifier",
                "rebel_org_gain_all",
                "rebel_org_gain_communist_rebels",
                "rebel_org_gain_fascist_rebels",
                "rebel_org_gain_nationalist_rebels",
                "rebel_org_gain_reactionary_rebels",
                "seperatism",
                "suppression_points_modifier",
            ),
        )

    def test_filename(self):
        self.assertEqual(
            build_rebels_matrices.FILENAME, "rebels_modifiers.csv"
        )


class TestRebelsMain(unittest.TestCase):

    def run_main(self, root: Path, *extra: str) -> Path:
        game_dir = make_rebels_game_dir(root)
        out = root / "out"
        out.mkdir()
        return build_rebels_matrices.main(
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
                Path("tech_modifiers/army/rebels_modifiers.csv"),
                Path("invention_modifiers/culture/rebels_modifiers.csv"),
                Path("westernisation_modifiers/economic/rebels_modifiers.csv"),
                Path("westernisation_modifiers/military/rebels_modifiers.csv"),
            }
            self.assertEqual(
                {p.relative_to(out) for p in out.rglob("*.csv")}, expected
            )
            self.assertEqual(
                (out / "tech_modifiers/army/rebels_modifiers.csv").read_text(
                    encoding="utf-8"
                ),
                "modifier,reb_tech,plain_tech\n"
                + ZERO_ROWS.replace("seperatism,0,0\n", "seperatism,0.5,0\n"),
            )
            self.assertEqual(
                (
                    out
                    / "invention_modifiers/culture/rebels_modifiers.csv"
                ).read_text(encoding="utf-8"),
                "modifier,reb_invention,effectless_invention\n"
                + ZERO_ROWS.replace(
                    "rebel_org_gain_all,0,0\n", "rebel_org_gain_all,-0.25,0\n"
                ).replace(
                    "suppression_points_modifier,0,0\n",
                    "suppression_points_modifier,0.25,0\n",
                ),
            )

    def test_westernisation_reform_values_recorded(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            out = self.run_main(root)
            self.assertEqual(
                (
                    out
                    / "westernisation_modifiers/economic/rebels_modifiers.csv"
                ).read_text(encoding="utf-8"),
                "modifier,no_land_reform,yes_land_reform\n"
                + ZERO_ROWS.replace(
                    "global_pop_militancy_modifier,0,0\n",
                    "global_pop_militancy_modifier,-0.005,0\n",
                ),
            )
            self.assertEqual(
                (
                    out
                    / "westernisation_modifiers/military/rebels_modifiers.csv"
                ).read_text(encoding="utf-8"),
                "modifier,no_army_schools,yes_army_schools\n"
                + ZERO_ROWS.replace(
                    "global_pop_militancy_modifier,0,0\n",
                    "global_pop_militancy_modifier,-0.005,0\n",
                ),
            )

    def test_vanilla_anchors_reject_fixture(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            game_dir = make_rebels_game_dir(root)
            out = root / "out"
            out.mkdir()
            with self.assertRaises(ValueError):
                build_rebels_matrices.main(
                    ["--game-dir", str(game_dir), "--output-dir", str(out)]
                )
            self.assertEqual(list(out.rglob("*.csv")), [])

    def test_check_save_validates(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            save = root / "test.v2"
            save.write_text(REB_SAVE, encoding="utf-8")
            self.run_main(root, "--check-save", str(save))

    def test_check_save_rejects_unknown_tech(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            save = root / "test.v2"
            save.write_text(
                REB_SAVE.replace("reb_tech", "mystery_tech"), encoding="utf-8"
            )
            with self.assertRaises(ValueError):
                self.run_main(root, "--check-save", str(save))

    def test_missing_output_dir_errors(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            game_dir = make_rebels_game_dir(root)
            with self.assertRaises(SystemExit):
                build_rebels_matrices.main(
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
                build_rebels_matrices.main(
                    [
                        "--game-dir", str(root / "nope"),
                        "--output-dir", str(out),
                        "--source", "modded",
                    ]
                )


if __name__ == "__main__":
    unittest.main()
