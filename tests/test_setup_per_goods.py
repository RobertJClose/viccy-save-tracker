"""
Tests for the per-goods matrices setup (setup/research_modifiers/build_per_goods_matrices.py).

Run from the repository root:

    python -m unittest discover -s tests -v
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from setup.research_modifiers import build_per_goods_matrices
from helpers import PGO_SAVE, make_per_goods_game_dir


class TestCollectModifierValues(unittest.TestCase):

    def test_scalars_and_composites_keep_values(self):
        values = build_per_goods_matrices.collect_modifier_values(
            "factory_input = -0.01\n"
            "rgo_goods_output = { iron = 0.25 }\n"
            "artillery = { defence = 1 }\n",
            "test",
        )
        self.assertEqual(
            values,
            {
                "factory_input": -0.01,
                "rgo_goods_output_iron": 0.25,
                "artillery_defence": 1.0,
            },
        )

    def test_non_numeric_values_ignored(self):
        values = build_per_goods_matrices.collect_modifier_values(
            "area = some_area\n"
            "activate_building = lumber_mill\n"
            "limit = { first_tech = 1 }\n",
            "test",
        )
        self.assertEqual(values, {"limit_first_tech": 1.0})

    def test_rebel_org_gain_uses_faction(self):
        values = build_per_goods_matrices.collect_modifier_values(
            "rebel_org_gain = { faction = all value = -0.25 }\n",
            "test",
        )
        self.assertEqual(values, {"rebel_org_gain_all": -0.25})

    def test_rebel_org_gain_without_value_raises(self):
        with self.assertRaises(ValueError):
            build_per_goods_matrices.collect_modifier_values(
                "rebel_org_gain = { faction = all }\n",
                "test",
            )

    def test_duplicate_scalar_raises(self):
        with self.assertRaises(ValueError):
            build_per_goods_matrices.collect_modifier_values(
                "tax_eff = 5\ntax_eff = 6\n",
                "test",
            )

    def test_duplicate_composite_raises(self):
        with self.assertRaises(ValueError):
            build_per_goods_matrices.collect_modifier_values(
                "rgo_goods_output = { iron = 0.25 }\n"
                "rgo_goods_output = { iron = 0.1 }\n",
                "test",
            )

    def test_deeper_nesting_joins_full_path(self):
        values = build_per_goods_matrices.collect_modifier_values(
            "outer = { inner = { deep_stat = 2 } }\n",
            "test",
        )
        self.assertEqual(values, {"outer_inner_deep_stat": 2.0})


class TestGroupName(unittest.TestCase):

    def test_suffix_stripped(self):
        self.assertEqual(
            build_per_goods_matrices.group_name("army_tech.txt", "_tech"), "army"
        )
        self.assertEqual(
            build_per_goods_matrices.group_name(
                "army_inventions.txt", "_inventions"
            ),
            "army",
        )
        self.assertEqual(
            build_per_goods_matrices.group_name("economic_reforms", "_reforms"),
            "economic",
        )

    def test_missing_suffix_falls_back_to_stem(self):
        self.assertEqual(
            build_per_goods_matrices.group_name("weird.txt", "_tech"), "weird"
        )


class TestCollectGroups(unittest.TestCase):

    def test_technology_groups_in_declaration_order(self):
        with tempfile.TemporaryDirectory() as d:
            groups = build_per_goods_matrices.collect_technology_values(
                make_per_goods_game_dir(Path(d))
            )
            self.assertEqual(list(groups), ["army"])
            self.assertEqual(
                [name for name, _ in groups["army"]],
                ["first_tech", "second_tech"],
            )
            self.assertEqual(
                groups["army"][0][1]["rgo_goods_output_iron"], 0.25
            )
            # Trigger vocabulary and metadata contribute nothing.
            for _, values in groups["army"]:
                for excluded in ("area", "year", "cost", "factor"):
                    self.assertNotIn(excluded, values)

    def test_invention_groups_scan_effect_only(self):
        with tempfile.TemporaryDirectory() as d:
            groups = build_per_goods_matrices.collect_invention_values(
                make_per_goods_game_dir(Path(d))
            )
            self.assertEqual(
                [name for name, _ in groups["army"]],
                ["first_invention", "effectless_invention"],
            )
            first, effectless = groups["army"][0][1], groups["army"][1][1]
            self.assertEqual(
                first["factory_goods_throughput_fabric"], 0.05
            )
            self.assertNotIn("base", first)
            self.assertEqual(effectless, {})

    def test_reform_groups_in_file_order(self):
        with tempfile.TemporaryDirectory() as d:
            groups = build_per_goods_matrices.collect_reform_values(
                make_per_goods_game_dir(Path(d))
            )
            self.assertEqual(
                [name for name, _ in groups["economic"]],
                ["no_land_reform", "yes_land_reform"],
            )
            self.assertEqual(
                [name for name, _ in groups["military"]],
                ["no_army_schools", "yes_army_schools"],
            )
            self.assertEqual(
                groups["economic"][1][1]["farm_rgo_eff"], 0.25
            )
            # The on_execute militancy never leaks in.
            for _, values in groups["economic"]:
                self.assertNotIn("militancy", values)

    def test_missing_dirs_raise(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            with self.assertRaises(FileNotFoundError):
                build_per_goods_matrices.collect_technology_values(root)
            with self.assertRaises(FileNotFoundError):
                build_per_goods_matrices.collect_invention_values(root)
            with self.assertRaises(FileNotFoundError):
                build_per_goods_matrices.collect_reform_values(root)


class TestRenderMatrix(unittest.TestCase):

    def test_exact_csv_text(self):
        columns = [
            ("first_tech", {"rgo_goods_output_iron": 0.25, "tax_eff": 5.0}),
            ("second_tech", {"rgo_size_coal": 0.2}),
        ]
        self.assertEqual(
            build_per_goods_matrices.render_matrix(
                columns, ("rgo_goods_output_", "rgo_size_")
            ),
            "modifier,first_tech,second_tech\n"
            "rgo_goods_output_iron,0.25,0\n"
            "rgo_size_coal,0,0.2\n",
        )

    def test_header_only_when_no_rows(self):
        self.assertEqual(
            build_per_goods_matrices.render_matrix(
                [("no_x", {"tax_eff": 1.0})], ("rgo_goods_output_",)
            ),
            "modifier,no_x\n",
        )

    def test_format_number(self):
        fmt = build_per_goods_matrices.format_number
        self.assertEqual(fmt(0.25), "0.25")
        self.assertEqual(fmt(-0.25), "-0.25")
        self.assertEqual(fmt(1.0), "1")
        self.assertEqual(fmt(0.0), "0")


class TestCheckAnchors(unittest.TestCase):

    def test_matching_anchors_pass(self):
        build_per_goods_matrices.check_anchors(
            {
                "industry": [
                    (
                        "mechanized_mining",
                        {"rgo_goods_output_iron": 0.25},
                    ),
                    ("clean_coal", {"rgo_size_coal": 0.2}),
                ]
            },
            {
                "industry": [
                    (
                        "daimlers_automobile",
                        {"factory_goods_output_machine_parts": 0.01},
                    ),
                    (
                        "northrop_power_loom",
                        {"factory_goods_throughput_fabric": 0.05},
                    ),
                ]
            },
        )

    def test_wrong_value_raises(self):
        with self.assertRaises(ValueError):
            build_per_goods_matrices.check_anchors(
                {
                    "industry": [
                        (
                            "mechanized_mining",
                            {"rgo_goods_output_iron": 0.5},
                        ),
                        ("clean_coal", {"rgo_size_coal": 0.2}),
                    ]
                },
                {},
            )


class TestValidateAgainstSave(unittest.TestCase):

    def test_matching_save_passes(self):
        build_per_goods_matrices.validate_against_save(
            {"first_tech", "second_tech"},
            {
                "no_land_reform",
                "yes_land_reform",
                "no_army_schools",
                "yes_army_schools",
            },
            PGO_SAVE,
            "test.v2",
        )

    def test_unknown_tech_raises(self):
        with self.assertRaises(ValueError):
            build_per_goods_matrices.validate_against_save(
                {"first_tech"},
                {"yes_land_reform", "no_army_schools"},
                PGO_SAVE.replace("first_tech", "mystery_tech"),
                "test.v2",
            )

    def test_unknown_level_raises(self):
        with self.assertRaises(ValueError):
            build_per_goods_matrices.validate_against_save(
                {"first_tech"},
                {"no_land_reform", "no_army_schools"},
                PGO_SAVE,
                "test.v2",
            )


class TestPerGoodsMain(unittest.TestCase):

    def run_main(self, root: Path, *extra: str) -> Path:
        game_dir = make_per_goods_game_dir(root)
        out = root / "out"
        out.mkdir()
        return build_per_goods_matrices.main(
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
                Path("tech_modifiers/army/rgo_goods_modifiers.csv"),
                Path("tech_modifiers/army/factory_goods_modifiers.csv"),
                Path("invention_modifiers/army/rgo_goods_modifiers.csv"),
                Path("invention_modifiers/army/factory_goods_modifiers.csv"),
                Path("westernisation_modifiers/economic/rgo_goods_modifiers.csv"),
                Path("westernisation_modifiers/economic/factory_goods_modifiers.csv"),
                Path("westernisation_modifiers/military/rgo_goods_modifiers.csv"),
                Path("westernisation_modifiers/military/factory_goods_modifiers.csv"),
            }
            self.assertEqual(
                {p.relative_to(out) for p in out.rglob("*.csv")}, expected
            )
            self.assertEqual(
                (out / "tech_modifiers/army/rgo_goods_modifiers.csv").read_text(
                    encoding="utf-8"
                ),
                "modifier,first_tech,second_tech\n"
                "rgo_goods_output_iron,0.25,0\n"
                "rgo_size_coal,0.2,0\n",
            )
            self.assertEqual(
                (out / "invention_modifiers/army/factory_goods_modifiers.csv").read_text(
                    encoding="utf-8"
                ),
                "modifier,first_invention,effectless_invention\n"
                "factory_goods_throughput_fabric,0.05,0\n",
            )

    def test_westernisation_files_are_header_only(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            out = self.run_main(root)
            self.assertEqual(
                (
                    out
                    / "westernisation_modifiers/economic/rgo_goods_modifiers.csv"
                ).read_text(encoding="utf-8"),
                "modifier,no_land_reform,yes_land_reform\n",
            )
            self.assertEqual(
                (
                    out
                    / "westernisation_modifiers/military/factory_goods_modifiers.csv"
                ).read_text(encoding="utf-8"),
                "modifier,no_army_schools,yes_army_schools\n",
            )

    def test_vanilla_anchors_reject_fixture(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            game_dir = make_per_goods_game_dir(root)
            out = root / "out"
            out.mkdir()
            with self.assertRaises(ValueError):
                build_per_goods_matrices.main(
                    ["--game-dir", str(game_dir), "--output-dir", str(out)]
                )
            self.assertEqual(list(out.rglob("*.csv")), [])

    def test_check_save_validates(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            save = root / "test.v2"
            save.write_text(PGO_SAVE, encoding="utf-8")
            self.run_main(root, "--check-save", str(save))

    def test_check_save_rejects_unknown_tech(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            save = root / "test.v2"
            save.write_text(
                PGO_SAVE.replace("first_tech", "mystery_tech"), encoding="utf-8"
            )
            with self.assertRaises(ValueError):
                self.run_main(root, "--check-save", str(save))

    def test_missing_output_dir_errors(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            game_dir = make_per_goods_game_dir(root)
            with self.assertRaises(SystemExit):
                build_per_goods_matrices.main(
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
                build_per_goods_matrices.main(
                    [
                        "--game-dir", str(root / "nope"),
                        "--output-dir", str(out),
                        "--source", "modded",
                    ]
                )


if __name__ == "__main__":
    unittest.main()
