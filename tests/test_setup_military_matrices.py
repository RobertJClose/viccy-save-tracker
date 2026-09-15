"""
Tests for the military matrices setup (setup/research_modifiers/build_military_matrices.py).

Run from the repository root:

    python -m unittest discover -s tests -v
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from setup.research_modifiers import build_military_matrices
from helpers import MIL_SAVE, make_military_game_dir


class TestMilitaryRows(unittest.TestCase):

    def test_rows_match_agreed_set(self):
        self.assertEqual(
            build_military_matrices.ROWS,
            (
                "army_base_default_organisation",
                "army_base_maximum_speed",
                "army_base_supply_consumption",
                "combat_width",
                "dig_in_cap",
                "land_attrition",
                "land_defense_modifier",
                "land_organisation",
                "land_unit_start_experience",
                "leadership_modifier",
                "max_fort",
                "max_naval_base",
                "military_tactics",
                "mobilisation_economy_impact",
                "mobilisation_size",
                "morale",
                "naval_attack_modifier",
                "naval_attrition",
                "naval_defense_modifier",
                "naval_unit_start_experience",
                "navy_base_build_time",
                "navy_base_default_organisation",
                "navy_base_gun_power",
                "navy_base_hull",
                "navy_base_maximum_speed",
                "regular_experience_level",
                "reinforce_rate",
                "research_points_on_conquer",
                "soldier_to_pop_loss",
                "supply_limit",
                "supply_range",
                "war_exhaustion",
            ),
        )

    def test_filename(self):
        self.assertEqual(
            build_military_matrices.FILENAME, "military_modifiers.csv"
        )


class TestMilitaryMain(unittest.TestCase):

    def run_main(self, root: Path, *extra: str) -> Path:
        game_dir = make_military_game_dir(root)
        out = root / "out"
        out.mkdir()
        return build_military_matrices.main(
            ["--game-dir", str(game_dir), "--output-dir", str(out),
             "--source", "modded", *extra]
        )

    def read_body(self, path: Path) -> dict[str, list[str]]:
        lines = path.read_text(encoding="utf-8").splitlines()
        return dict(
            (row.split(",")[0], row.split(",")[1:]) for row in lines[1:]
        )

    def test_writes_expected_files(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            result = self.run_main(root)
            out = root / "out"
            self.assertEqual(result, out)
            expected = {
                Path("tech_modifiers/army/military_modifiers.csv"),
                Path("invention_modifiers/navy/military_modifiers.csv"),
                Path("westernisation_modifiers/economic/military_modifiers.csv"),
                Path("westernisation_modifiers/military/military_modifiers.csv"),
            }
            self.assertEqual(
                {p.relative_to(out) for p in out.rglob("*.csv")}, expected
            )
            tech_text = (
                out / "tech_modifiers/army/military_modifiers.csv"
            ).read_text(encoding="utf-8")
            tech_lines = tech_text.splitlines()
            self.assertEqual(tech_lines[0], "modifier,mil_tech,plain_tech")
            self.assertEqual(len(tech_lines), 33)
            body = self.read_body(out / "tech_modifiers/army/military_modifiers.csv")
            self.assertEqual(body["morale"], ["0.25", "0"])
            self.assertEqual(body["military_tactics"], ["0.25", "0"])
            self.assertEqual(
                body["army_base_supply_consumption"], ["0.05", "0"]
            )
            self.assertEqual(body["war_exhaustion"], ["0", "0"])
            inv_body = self.read_body(
                out / "invention_modifiers/navy/military_modifiers.csv"
            )
            self.assertEqual(
                inv_body["navy_base_maximum_speed"], ["1", "0"]
            )
            self.assertEqual(inv_body["war_exhaustion"], ["-0.1", "0"])
            self.assertEqual(inv_body["morale"], ["0", "0"])

    def test_westernisation_reform_values_recorded(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            out = self.run_main(root)
            eco_body = self.read_body(
                out
                / "westernisation_modifiers/economic/military_modifiers.csv"
            )
            self.assertEqual(len(eco_body), 32)
            self.assertEqual(eco_body["land_organisation"], ["0", "0"])
            self.assertEqual(eco_body["morale"], ["0", "0"])
            mil_body = self.read_body(
                out
                / "westernisation_modifiers/military/military_modifiers.csv"
            )
            self.assertEqual(mil_body["land_organisation"], ["0", "0.1"])
            self.assertEqual(mil_body["morale"], ["0", "0"])

    def test_vanilla_anchors_reject_fixture(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            game_dir = make_military_game_dir(root)
            out = root / "out"
            out.mkdir()
            with self.assertRaises(ValueError):
                build_military_matrices.main(
                    ["--game-dir", str(game_dir), "--output-dir", str(out)]
                )
            self.assertEqual(list(out.rglob("*.csv")), [])

    def test_check_save_validates(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            save = root / "test.v2"
            save.write_text(MIL_SAVE, encoding="utf-8")
            self.run_main(root, "--check-save", str(save))

    def test_check_save_rejects_unknown_tech(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            save = root / "test.v2"
            save.write_text(
                MIL_SAVE.replace("mil_tech", "mystery_tech"), encoding="utf-8"
            )
            with self.assertRaises(ValueError):
                self.run_main(root, "--check-save", str(save))

    def test_missing_output_dir_errors(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            game_dir = make_military_game_dir(root)
            with self.assertRaises(SystemExit):
                build_military_matrices.main(
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
                build_military_matrices.main(
                    [
                        "--game-dir", str(root / "nope"),
                        "--output-dir", str(out),
                        "--source", "modded",
                    ]
                )


if __name__ == "__main__":
    unittest.main()
