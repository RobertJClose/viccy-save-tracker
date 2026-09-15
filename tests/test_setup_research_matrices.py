"""
Tests for the research matrices setup (setup/research_modifiers/build_research_matrices.py).

Run from the repository root:

    python -m unittest discover -s tests -v
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from setup.research_modifiers import build_research_matrices
from helpers import RES_SAVE, make_research_economic_game_dir


class TestResearchRows(unittest.TestCase):

    def test_rows_match_agreed_set(self):
        self.assertEqual(
            build_research_matrices.ROWS,
            (
                "civilization_progress_modifier",
                "education_efficiency",
                "education_efficiency_modifier",
                "increase_research",
                "plurality",
                "technology_cost",
            ),
        )

    def test_filename(self):
        self.assertEqual(
            build_research_matrices.FILENAME, "research_modifiers.csv"
        )


class TestResearchMain(unittest.TestCase):

    def run_main(self, root: Path, *extra: str) -> Path:
        game_dir = make_research_economic_game_dir(root)
        out = root / "out"
        out.mkdir()
        return build_research_matrices.main(
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
                Path("tech_modifiers/army/research_modifiers.csv"),
                Path("invention_modifiers/army/research_modifiers.csv"),
                Path("westernisation_modifiers/economic/research_modifiers.csv"),
                Path("westernisation_modifiers/military/research_modifiers.csv"),
            }
            self.assertEqual(
                {p.relative_to(out) for p in out.rglob("*.csv")}, expected
            )
            self.assertEqual(
                (out / "tech_modifiers/army/research_modifiers.csv").read_text(
                    encoding="utf-8"
                ),
                "modifier,res_tech,plain_tech\n"
                "civilization_progress_modifier,0,0\n"
                "education_efficiency,0.1,0\n"
                "education_efficiency_modifier,0,0\n"
                "increase_research,0.5,0\n"
                "plurality,0,0\n"
                "technology_cost,0,0\n",
            )
            self.assertEqual(
                (
                    out
                    / "invention_modifiers/army/research_modifiers.csv"
                ).read_text(encoding="utf-8"),
                "modifier,res_invention,effectless_invention\n"
                "civilization_progress_modifier,0,0\n"
                "education_efficiency,0,0\n"
                "education_efficiency_modifier,0.15,0\n"
                "increase_research,0,0\n"
                "plurality,0.1,0\n"
                "technology_cost,0,0\n",
            )

    def test_westernisation_reform_values_recorded(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            out = self.run_main(root)
            self.assertEqual(
                (
                    out
                    / "westernisation_modifiers/economic/research_modifiers.csv"
                ).read_text(encoding="utf-8"),
                "modifier,no_land_reform,yes_land_reform\n"
                "civilization_progress_modifier,0,0\n"
                "education_efficiency,0,0\n"
                "education_efficiency_modifier,0,0\n"
                "increase_research,0,0\n"
                "plurality,0,0\n"
                "technology_cost,0,8000\n",
            )
            self.assertEqual(
                (
                    out
                    / "westernisation_modifiers/military/research_modifiers.csv"
                ).read_text(encoding="utf-8"),
                "modifier,no_army_schools,yes_army_schools\n"
                "civilization_progress_modifier,0,0\n"
                "education_efficiency,0,0\n"
                "education_efficiency_modifier,0,0\n"
                "increase_research,0,0\n"
                "plurality,0,0\n"
                "technology_cost,0,0\n",
            )

    def test_vanilla_anchors_reject_fixture(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            game_dir = make_research_economic_game_dir(root)
            out = root / "out"
            out.mkdir()
            with self.assertRaises(ValueError):
                build_research_matrices.main(
                    ["--game-dir", str(game_dir), "--output-dir", str(out)]
                )
            self.assertEqual(list(out.rglob("*.csv")), [])

    def test_check_save_validates(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            save = root / "test.v2"
            save.write_text(RES_SAVE, encoding="utf-8")
            self.run_main(root, "--check-save", str(save))

    def test_check_save_rejects_unknown_tech(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            save = root / "test.v2"
            save.write_text(
                RES_SAVE.replace("res_tech", "mystery_tech"), encoding="utf-8"
            )
            with self.assertRaises(ValueError):
                self.run_main(root, "--check-save", str(save))

    def test_missing_output_dir_errors(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            game_dir = make_research_economic_game_dir(root)
            with self.assertRaises(SystemExit):
                build_research_matrices.main(
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
                build_research_matrices.main(
                    [
                        "--game-dir", str(root / "nope"),
                        "--output-dir", str(out),
                        "--source", "modded",
                    ]
                )


if __name__ == "__main__":
    unittest.main()
