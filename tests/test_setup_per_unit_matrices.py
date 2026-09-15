"""
Tests for the per-unit matrices setup (setup/build_per_unit_matrices.py).

Run from the repository root:

    python -m unittest discover -s tests -v
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from setup import build_per_unit_matrices
from helpers import PU_SAVE, make_per_unit_game_dir


class TestPerUnitScopes(unittest.TestCase):

    def test_scopes_match_agreed_split(self):
        self.assertEqual(
            set(build_per_unit_matrices.LAND_SCOPES),
            {
                "infantry",
                "guard",
                "artillery",
                "engineer",
                "cavalry",
                "cuirassier",
                "dragoon",
                "hussar",
                "irregular",
                "tank",
                "plane",
            },
        )
        self.assertEqual(
            set(build_per_unit_matrices.NAVAL_SCOPES),
            {
                "battleship",
                "cruiser",
                "dreadnought",
                "ironclad",
                "commerce_raider",
                "clipper_transport",
                "steam_transport",
            },
        )
        self.assertFalse(
            set(build_per_unit_matrices.LAND_SCOPES)
            & set(build_per_unit_matrices.NAVAL_SCOPES)
        )

    def test_filenames(self):
        self.assertEqual(
            build_per_unit_matrices.LAND_FILENAME, "per_unit_land_modifiers.csv"
        )
        self.assertEqual(
            build_per_unit_matrices.NAVAL_FILENAME,
            "per_unit_naval_modifiers.csv",
        )


class TestPerUnitRender(unittest.TestCase):

    def test_land_naval_split(self):
        columns = [
            (
                "pu_tech",
                {"infantry_defence": 1.0, "cruiser_hull": 5.0, "morale": 0.5},
            ),
            ("plain_tech", {}),
        ]
        self.assertEqual(
            build_per_unit_matrices.render_matrix(
                columns, build_per_unit_matrices.LAND_CATEGORY[1]
            ),
            "modifier,pu_tech,plain_tech\ninfantry_defence,1,0\n",
        )
        self.assertEqual(
            build_per_unit_matrices.render_matrix(
                columns, build_per_unit_matrices.NAVAL_CATEGORY[1]
            ),
            "modifier,pu_tech,plain_tech\ncruiser_hull,5,0\n",
        )

    def test_header_only_when_no_rows(self):
        self.assertEqual(
            build_per_unit_matrices.render_matrix(
                [("plain_tech", {})],
                build_per_unit_matrices.LAND_CATEGORY[1],
            ),
            "modifier,plain_tech\n",
        )


class TestPerUnitMain(unittest.TestCase):

    def run_main(self, root: Path, *extra: str) -> Path:
        game_dir = make_per_unit_game_dir(root)
        out = root / "out"
        out.mkdir()
        return build_per_unit_matrices.main(
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
                Path("tech_modifiers/army/per_unit_land_modifiers.csv"),
                Path("tech_modifiers/army/per_unit_naval_modifiers.csv"),
                Path("invention_modifiers/navy/per_unit_land_modifiers.csv"),
                Path("invention_modifiers/navy/per_unit_naval_modifiers.csv"),
                Path("westernisation_modifiers/economic/per_unit_land_modifiers.csv"),
                Path("westernisation_modifiers/economic/per_unit_naval_modifiers.csv"),
                Path("westernisation_modifiers/military/per_unit_land_modifiers.csv"),
                Path("westernisation_modifiers/military/per_unit_naval_modifiers.csv"),
            }
            self.assertEqual(
                {p.relative_to(out) for p in out.rglob("*.csv")}, expected
            )
            self.assertEqual(
                (out / "tech_modifiers/army/per_unit_land_modifiers.csv").read_text(
                    encoding="utf-8"
                ),
                "modifier,pu_tech,plain_tech\n"
                "infantry_attack,0.5,0\n"
                "infantry_defence,1,0\n"
                "plane_reconnaissance,2,0\n",
            )
            self.assertEqual(
                (out / "tech_modifiers/army/per_unit_naval_modifiers.csv").read_text(
                    encoding="utf-8"
                ),
                "modifier,pu_tech,plain_tech\n",
            )
            self.assertEqual(
                (
                    out
                    / "invention_modifiers/navy/per_unit_land_modifiers.csv"
                ).read_text(encoding="utf-8"),
                "modifier,pu_invention,effectless_invention\n"
                "infantry_defence,2,0\n",
            )
            self.assertEqual(
                (
                    out
                    / "invention_modifiers/navy/per_unit_naval_modifiers.csv"
                ).read_text(encoding="utf-8"),
                "modifier,pu_invention,effectless_invention\n"
                "cruiser_torpedo_attack,8,0\n",
            )

    def test_westernisation_files_are_header_only(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            out = self.run_main(root)
            self.assertEqual(
                (
                    out
                    / "westernisation_modifiers/economic/per_unit_land_modifiers.csv"
                ).read_text(encoding="utf-8"),
                "modifier,no_land_reform,yes_land_reform\n",
            )
            self.assertEqual(
                (
                    out
                    / "westernisation_modifiers/military/per_unit_naval_modifiers.csv"
                ).read_text(encoding="utf-8"),
                "modifier,no_army_schools,yes_army_schools\n",
            )

    def test_vanilla_anchors_reject_fixture(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            game_dir = make_per_unit_game_dir(root)
            out = root / "out"
            out.mkdir()
            with self.assertRaises(ValueError):
                build_per_unit_matrices.main(
                    ["--game-dir", str(game_dir), "--output-dir", str(out)]
                )
            self.assertEqual(list(out.rglob("*.csv")), [])

    def test_check_save_validates(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            save = root / "test.v2"
            save.write_text(PU_SAVE, encoding="utf-8")
            self.run_main(root, "--check-save", str(save))

    def test_check_save_rejects_unknown_tech(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            save = root / "test.v2"
            save.write_text(
                PU_SAVE.replace("pu_tech", "mystery_tech"), encoding="utf-8"
            )
            with self.assertRaises(ValueError):
                self.run_main(root, "--check-save", str(save))

    def test_missing_output_dir_errors(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            game_dir = make_per_unit_game_dir(root)
            with self.assertRaises(SystemExit):
                build_per_unit_matrices.main(
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
                build_per_unit_matrices.main(
                    [
                        "--game-dir", str(root / "nope"),
                        "--output-dir", str(out),
                        "--source", "modded",
                    ]
                )


if __name__ == "__main__":
    unittest.main()
