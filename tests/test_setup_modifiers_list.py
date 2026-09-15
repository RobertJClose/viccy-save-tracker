"""
Tests for the exhaustive modifier-list setup (setup/build_modifiers_list.py).

Run from the repository root:

    python -m unittest discover -s tests -v
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from setup import build_modifiers_list
from setup import initialise
from helpers import (
    MOD_EXPECTED_NAMES,
    MOD_SAVE,
    make_modifiers_game_dir,
)


class TestCollectModifiers(unittest.TestCase):

    def test_scalars_recorded_metadata_ignored(self):
        names = build_modifiers_list.collect_modifiers(
            "area = some_area\nyear = 1836\ncost = 3600\nfactory_input = -0.01\n"
        )
        self.assertEqual(names, {"factory_input"})

    def test_nested_blocks_become_composites(self):
        names = build_modifiers_list.collect_modifiers(
            "artillery = { attack = 0.5 defence = 2 }\n"
            "rgo_goods_output = { iron = 0.25 }\n"
        )
        self.assertEqual(
            names,
            {"artillery_attack", "artillery_defence", "rgo_goods_output_iron"},
        )

    def test_bare_words_and_strings_ignored(self):
        names = build_modifiers_list.collect_modifiers(
            "activate_building = lumber_mill\n"
            'name = "a { brace"\n'
            "limit = { test_tech = 1 }\n"
        )
        # `limit` is a block (its inner `test_tech` is a trigger word with a
        # number, recorded as a composite, never as a bare modifier).
        self.assertEqual(names, {"limit_test_tech"})

    def test_quoted_braces_do_not_unbalance(self):
        names = build_modifiers_list.collect_modifiers(
            'label = "weird { value"\ntax_eff = 5\n'
        )
        self.assertEqual(names, {"tax_eff"})

    def test_deeper_nesting_joins_full_path(self):
        names = build_modifiers_list.collect_modifiers(
            "outer = { inner = { deep_stat = 1 } }\n"
        )
        self.assertEqual(names, {"outer_inner_deep_stat"})

    def test_rebel_org_gain_uses_faction(self):
        names = build_modifiers_list.collect_modifiers(
            "rebel_org_gain = { faction = all value = -0.25 }\n"
        )
        self.assertEqual(names, {"rebel_org_gain_all"})

    def test_rebel_org_gain_without_faction_raises(self):
        with self.assertRaises(ValueError):
            build_modifiers_list.collect_modifiers(
                "rebel_org_gain = { value = 0.33 }\n"
            )


class TestBlockHelpers(unittest.TestCase):

    def test_top_level_blocks_skip_nested(self):
        blocks = build_modifiers_list.iter_top_level_blocks(
            "aaa = {\n"
            "\tx = 1\n"
            "\tnested = {\n"
            "\t\ty = 2\n"
            "\t}\n"
            "}\n"
            "bbb = {\n"
            "\tz = 3\n"
            "}\n"
        )
        self.assertEqual([name for name, _ in blocks], ["aaa", "bbb"])
        self.assertIn("nested", blocks[0][1])

    def test_remove_named_blocks_keeps_rest(self):
        text = build_modifiers_list.remove_named_blocks(
            "keep = 1\nai_chance = {\n\tfactor = 2\n}\n"
            "also_keep = 2\nai_chance = {\n\tfactor = 3\n}\n",
            {"ai_chance"},
        )
        self.assertNotIn("ai_chance", text)
        self.assertNotIn("factor", text)
        self.assertIn("keep = 1", text)
        self.assertIn("also_keep = 2", text)


class TestCollectFromGameDir(unittest.TestCase):

    def test_full_fixture_yields_expected_names(self):
        with tempfile.TemporaryDirectory() as d:
            game_dir = make_modifiers_game_dir(Path(d))
            techs, tech_count = build_modifiers_list.collect_technology_modifiers(
                game_dir
            )
            inventions, invention_count = (
                build_modifiers_list.collect_invention_modifiers(game_dir)
            )
            reforms, levels = build_modifiers_list.collect_reform_modifiers(
                game_dir
            )
            self.assertEqual(tech_count, 2)
            self.assertEqual(invention_count, 3)
            self.assertEqual(
                levels,
                {
                    "land_reform": ["no_land_reform", "yes_land_reform"],
                    "army_schools": ["no_army_schools"],
                },
            )
            self.assertEqual(techs | inventions | reforms, MOD_EXPECTED_NAMES)

    def test_effect_less_invention_contributes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            game_dir = make_modifiers_game_dir(Path(d))
            inventions, _ = build_modifiers_list.collect_invention_modifiers(
                game_dir
            )
            self.assertEqual(
                inventions,
                {
                    "factory_throughput",
                    "infantry_defence",
                    "factory_goods_output_fabric",
                    "rebel_org_gain_all",
                },
            )

    def test_trigger_vocabulary_excluded(self):
        with tempfile.TemporaryDirectory() as d:
            game_dir = make_modifiers_game_dir(Path(d))
            techs, _ = build_modifiers_list.collect_technology_modifiers(game_dir)
            for excluded in (
                "area",
                "year",
                "cost",
                "factor",
                "big_producer",
                "activate_building",
            ):
                self.assertNotIn(excluded, techs)

    def test_missing_dirs_raise(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            with self.assertRaises(FileNotFoundError):
                build_modifiers_list.collect_technology_modifiers(root)
            with self.assertRaises(FileNotFoundError):
                build_modifiers_list.collect_invention_modifiers(root)
            with self.assertRaises(FileNotFoundError):
                build_modifiers_list.collect_reform_modifiers(root)


class TestValidateAgainstSave(unittest.TestCase):

    def test_matching_save_passes(self):
        with tempfile.TemporaryDirectory() as d:
            game_dir = make_modifiers_game_dir(Path(d))
            _, reforms = build_modifiers_list.collect_reform_modifiers(game_dir)
            build_modifiers_list.validate_against_save(
                build_modifiers_list.tech_names_only(game_dir),
                reforms,
                MOD_SAVE,
                "test.v2",
            )

    def test_unknown_tech_raises(self):
        with tempfile.TemporaryDirectory() as d:
            game_dir = make_modifiers_game_dir(Path(d))
            _, reforms = build_modifiers_list.collect_reform_modifiers(game_dir)
            bad = MOD_SAVE.replace("test_tech_alpha", "mystery_tech")
            with self.assertRaises(ValueError):
                build_modifiers_list.validate_against_save(
                    build_modifiers_list.tech_names_only(game_dir),
                    reforms,
                    bad,
                    "test.v2",
                )

    def test_unknown_reform_level_raises(self):
        with tempfile.TemporaryDirectory() as d:
            game_dir = make_modifiers_game_dir(Path(d))
            _, reforms = build_modifiers_list.collect_reform_modifiers(game_dir)
            bad = MOD_SAVE.replace("yes_land_reform", "super_land_reform")
            with self.assertRaises(ValueError):
                build_modifiers_list.validate_against_save(
                    build_modifiers_list.tech_names_only(game_dir),
                    reforms,
                    bad,
                    "test.v2",
                )


class TestModifiersListMain(unittest.TestCase):

    def test_writes_sorted_list_with_header(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            game_dir = make_modifiers_game_dir(root)
            out = root / "modifiers.txt"
            result = build_modifiers_list.main(
                [
                    "--game-dir", str(game_dir),
                    "--output", str(out),
                    "--source", "modded",
                ]
            )
            self.assertEqual(result, out)
            lines = out.read_text(encoding="utf-8").splitlines()
            header, names = lines[:4], lines[4:]
            self.assertTrue(all(line.startswith("#") for line in header))
            self.assertIn("modded", header[0])
            self.assertEqual(names, sorted(names))
            self.assertEqual(set(names), MOD_EXPECTED_NAMES)

    def test_vanilla_anchors_reject_broken_parse(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            game_dir = make_modifiers_game_dir(root)
            # The fixture has none of the vanilla anchors.
            with self.assertRaises(ValueError):
                build_modifiers_list.main(
                    [
                        "--game-dir", str(game_dir),
                        "--output", str(root / "modifiers.txt"),
                    ]
                )
            self.assertFalse((root / "modifiers.txt").exists())

    def test_modded_source_skips_anchors(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            game_dir = make_modifiers_game_dir(root)
            out = root / "modifiers.txt"
            build_modifiers_list.main(
                [
                    "--game-dir", str(game_dir),
                    "--output", str(out),
                    "--source", "modded",
                ]
            )
            self.assertTrue(out.exists())

    def test_check_save_validates(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            game_dir = make_modifiers_game_dir(root)
            save = root / "test.v2"
            save.write_text(MOD_SAVE, encoding="utf-8")
            build_modifiers_list.main(
                [
                    "--game-dir", str(game_dir),
                    "--output", str(root / "modifiers.txt"),
                    "--check-save", str(save),
                    "--source", "modded",
                ]
            )

    def test_check_save_rejects_unknown_tech(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            game_dir = make_modifiers_game_dir(root)
            save = root / "test.v2"
            save.write_text(
                MOD_SAVE.replace("test_tech_alpha", "mystery_tech"),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                build_modifiers_list.main(
                    [
                        "--game-dir", str(game_dir),
                        "--output", str(root / "modifiers.txt"),
                        "--check-save", str(save),
                        "--source", "modded",
                    ]
                )
            self.assertFalse((root / "modifiers.txt").exists())

    def test_missing_game_dir_raises(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileNotFoundError):
                build_modifiers_list.main(
                    [
                        "--game-dir", str(Path(d) / "nope"),
                        "--output", str(Path(d) / "modifiers.txt"),
                        "--source", "modded",
                    ]
                )


class TestInitialiseRouting(unittest.TestCase):

    def test_list_shows_modifiers_task(self):
        from io import StringIO
        from contextlib import redirect_stdout

        out = StringIO()
        with redirect_stdout(out):
            initialise.main(["--list"])
        self.assertIn("modifiers-list", out.getvalue())
        self.assertIn("inventions-map", out.getvalue())

    def test_output_dir_routed_per_task(self):
        seen: dict[str, list[str]] = {}

        with mock.patch.dict(
            initialise.TASKS,
            {
                "inventions-map": (
                    "Maps.",
                    lambda argv: seen.setdefault("inventions", argv),
                    "inventions_map.json",
                ),
                "modifiers-list": (
                    "Lists.",
                    lambda argv: seen.setdefault("modifiers", argv),
                    "modifiers_list.txt",
                ),
            },
            clear=True,
        ):
            with tempfile.TemporaryDirectory() as d:
                initialise.main(
                    [
                        "--game-dir", "g",
                        "--output-dir", d,
                        "--source", "mymod",
                        "--check-save", "s",
                    ]
                )

                self.assertEqual(
                    seen["inventions"],
                    [
                        "--game-dir", "g",
                        "--check-save", "s",
                        "--source", "mymod",
                        "--output", str(Path(d) / "inventions_map.json"),
                    ],
                )
                self.assertEqual(
                    seen["modifiers"],
                    [
                        "--game-dir", "g",
                        "--check-save", "s",
                        "--source", "mymod",
                        "--output", str(Path(d) / "modifiers_list.txt"),
                    ],
                )

    def test_source_omitted_when_unset(self):
        seen: dict[str, list[str]] = {}

        with mock.patch.dict(
            initialise.TASKS,
            {
                "only": (
                    "Only.",
                    lambda argv: seen.setdefault("only", argv),
                    "only.txt",
                ),
            },
            clear=True,
        ):
            with tempfile.TemporaryDirectory() as d:
                initialise.main(["--output-dir", d])

        self.assertEqual(
            seen["only"], ["--output", str(Path(d) / "only.txt")]
        )

    def test_missing_output_dir_errors(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(SystemExit):
                initialise.main(
                    ["--output-dir", str(Path(d) / "nope")]
                )


if __name__ == "__main__":
    unittest.main()
