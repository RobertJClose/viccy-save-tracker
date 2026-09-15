"""
Tests for the economic matrices setup (setup/research_modifiers/build_economic_matrices.py).

Run from the repository root:

    python -m unittest discover -s tests -v
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from setup.research_modifiers import build_economic_matrices
from helpers import RES_SAVE, make_research_economic_game_dir


class TestEconomicRows(unittest.TestCase):

    def test_rows_match_agreed_set(self):
        self.assertEqual(
            build_economic_matrices.ROWS,
            (
                "administrative_efficiency",
                "administrative_efficiency_modifier",
                "factory_cost",
                "factory_input",
                "factory_output",
                "factory_throughput",
                "farm_RGO_eff",
                "farm_rgo_eff",
                "farm_rgo_size",
                "loan_interest",
                "max_loan_modifier",
                "max_railroad",
                "mine_RGO_eff",
                "mine_rgo_eff",
                "mine_rgo_size",
                "rgo_output",
                "tariff_efficiency_modifier",
                "tax_eff",
                "tax_efficiency",
            ),
        )

    def test_filename(self):
        self.assertEqual(
            build_economic_matrices.FILENAME, "economic_modifiers.csv"
        )


class TestEconomicMain(unittest.TestCase):

    def run_main(self, root: Path, *extra: str) -> Path:
        game_dir = make_research_economic_game_dir(root)
        out = root / "out"
        out.mkdir()
        return build_economic_matrices.main(
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
                Path("tech_modifiers/army/economic_modifiers.csv"),
                Path("invention_modifiers/army/economic_modifiers.csv"),
                Path("westernisation_modifiers/economic/economic_modifiers.csv"),
                Path("westernisation_modifiers/military/economic_modifiers.csv"),
            }
            self.assertEqual(
                {p.relative_to(out) for p in out.rglob("*.csv")}, expected
            )
            text = (
                out / "tech_modifiers/army/economic_modifiers.csv"
            ).read_text(encoding="utf-8")
            lines = text.splitlines()
            self.assertEqual(lines[0], "modifier,res_tech,plain_tech")
            self.assertEqual(len(lines), 20)
            body = dict(
                (row.split(",")[0], row.split(",")[1:]) for row in lines[1:]
            )
            self.assertEqual(body["tax_eff"], ["3", "0"])
            self.assertEqual(body["factory_input"], ["-0.01", "0"])
            self.assertEqual(body["farm_rgo_eff"], ["0.25", "0"])
            self.assertEqual(body["farm_RGO_eff"], ["0", "0"])
            text = (
                out / "invention_modifiers/army/economic_modifiers.csv"
            ).read_text(encoding="utf-8")
            lines = text.splitlines()
            self.assertEqual(
                lines[0], "modifier,res_invention,effectless_invention"
            )
            body = dict(
                (row.split(",")[0], row.split(",")[1:]) for row in lines[1:]
            )
            self.assertEqual(body["tax_eff"], ["1", "0"])
            self.assertEqual(body["rgo_output"], ["0.05", "0"])

    def test_westernisation_reform_values_recorded(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            out = self.run_main(root)
            text = (
                out
                / "westernisation_modifiers/economic/economic_modifiers.csv"
            ).read_text(encoding="utf-8")
            lines = text.splitlines()
            self.assertEqual(
                lines[0], "modifier,no_land_reform,yes_land_reform"
            )
            body = dict(
                (row.split(",")[0], row.split(",")[1:]) for row in lines[1:]
            )
            self.assertEqual(body["farm_rgo_eff"], ["0", "0.25"])
            self.assertEqual(body["tax_eff"], ["0", "0"])
            text = (
                out
                / "westernisation_modifiers/military/economic_modifiers.csv"
            ).read_text(encoding="utf-8")
            lines = text.splitlines()
            self.assertEqual(
                lines[0], "modifier,no_army_schools,yes_army_schools"
            )
            self.assertTrue(
                all(row.endswith(",0,0") for row in lines[1:])
            )

    def test_vanilla_anchors_reject_fixture(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            game_dir = make_research_economic_game_dir(root)
            out = root / "out"
            out.mkdir()
            with self.assertRaises(ValueError):
                build_economic_matrices.main(
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
                build_economic_matrices.main(
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
                build_economic_matrices.main(
                    [
                        "--game-dir", str(root / "nope"),
                        "--output-dir", str(out),
                        "--source", "modded",
                    ]
                )


if __name__ == "__main__":
    unittest.main()
