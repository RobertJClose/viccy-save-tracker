"""
Tests for one-shot invention-map setup (setup/build_inventions_map.py, setup/initialise.py).

Run from the repository root:

    python -m unittest discover -s tests -v
"""

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from setup import build_inventions_map
from setup import initialise
from helpers import INIT_FIXTURE_A, INIT_FIXTURE_B, make_game_dir


class TestStripComments(unittest.TestCase):

    def test_full_line_and_inline_comments_removed(self):
        self.assertEqual(
            build_inventions_map.strip_comments(
                "# header\nfoo = 1 # trailing\nbar = 2\n"
            ),
            "\nfoo = 1 \nbar = 2",
        )

    def test_hash_inside_quotes_preserved(self):
        self.assertEqual(
            build_inventions_map.strip_comments('name = "a#b"\n'),
            'name = "a#b"',
        )


class TestExtractInventionNames(unittest.TestCase):

    def test_collects_only_top_level_blocks_in_order(self):
        self.assertEqual(
            build_inventions_map.extract_invention_names(INIT_FIXTURE_A),
            ["first_invention", "genetics:_heredity"],
        )

    def test_unusual_names_matched(self):
        self.assertEqual(
            build_inventions_map.extract_invention_names(INIT_FIXTURE_B),
            ["populism_vs._establishment", "15_inch_main_armament"],
        )

    def test_empty_file_yields_nothing(self):
        self.assertEqual(build_inventions_map.extract_invention_names("# only\n"), [])


class TestBuildInventionList(unittest.TestCase):

    def test_files_read_in_sorted_order(self):
        with tempfile.TemporaryDirectory() as d:
            names, files = build_inventions_map.build_invention_list(
                make_game_dir(Path(d))
            )
            self.assertEqual(files, ["a_first.txt", "b_second.txt"])
            self.assertEqual(
                names,
                [
                    "first_invention",
                    "genetics:_heredity",
                    "populism_vs._establishment",
                    "15_inch_main_armament",
                ],
            )

    def test_missing_inventions_dir_raises(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileNotFoundError):
                build_inventions_map.build_invention_list(Path(d) / "nope")

    def test_empty_inventions_dir_raises(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "inventions").mkdir()
            with self.assertRaises(FileNotFoundError):
                build_inventions_map.build_invention_list(Path(d))


class TestValidateAgainstSave(unittest.TestCase):

    NAMES = ["aaa", "b:b", "ccc"]

    def test_ids_within_range_pass(self):
        build_inventions_map.validate_against_save(
            self.NAMES,
            "active_inventions=\n{\n1 3 \t}\n",
            "test.v2",
            check_anchors=False,
        )

    def test_out_of_range_id_raises(self):
        with self.assertRaises(ValueError):
            build_inventions_map.validate_against_save(
                self.NAMES,
                "active_inventions=\n{\n1 4 \t}\n",
                "test.v2",
                check_anchors=False,
            )

    def test_zero_id_raises(self):
        with self.assertRaises(ValueError):
            build_inventions_map.validate_against_save(
                self.NAMES,
                "active_inventions=\n{\n0 \t}\n",
                "test.v2",
                check_anchors=False,
            )


class TestInitInventionsMapMain(unittest.TestCase):

    def test_writes_index_aligned_map(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            game_dir = make_game_dir(root)
            out = root / "map.json"
            result = build_inventions_map.main(
                ["--game-dir", str(game_dir), "--output", str(out)]
            )
            self.assertEqual(result, out)
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload["source"], "vanilla")
            self.assertEqual(payload["files"], ["a_first.txt", "b_second.txt"])
            self.assertEqual(payload["count"], 4)
            # Index == save ID; index 0 unused.
            self.assertEqual(payload["inventions"][0], None)
            self.assertEqual(payload["inventions"][1], "first_invention")
            self.assertEqual(payload["inventions"][4], "15_inch_main_armament")

    def test_missing_game_dir_raises(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileNotFoundError):
                build_inventions_map.main(
                    [
                        "--game-dir", str(Path(d) / "nope"),
                        "--output", str(Path(d) / "map.json"),
                    ]
                )

    def test_check_save_validates_ids(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            game_dir = make_game_dir(root)
            save = root / "test.v2"
            save.write_text(
                "active_inventions=\n{\n1 2 3 4 \t}\n", encoding="utf-8"
            )
            build_inventions_map.main(
                [
                    "--game-dir", str(game_dir),
                    "--output", str(root / "map.json"),
                    "--check-save", str(save),
                    "--source", "modded",
                ]
            )

    def test_check_save_rejects_unknown_id(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            game_dir = make_game_dir(root)
            save = root / "test.v2"
            save.write_text(
                "active_inventions=\n{\n1 99 \t}\n", encoding="utf-8"
            )
            with self.assertRaises(ValueError):
                build_inventions_map.main(
                    [
                        "--game-dir", str(game_dir),
                        "--output", str(root / "map.json"),
                        "--check-save", str(save),
                        "--source", "modded",
                    ]
                )
            self.assertFalse((root / "map.json").exists())


class TestInitialise(unittest.TestCase):

    def test_list_shows_tasks(self):
        out = io.StringIO()
        with redirect_stdout(out):
            initialise.main(["--list"])
        self.assertIn("inventions-map", out.getvalue())

    def test_runs_registered_tasks(self):
        seen = []

        def fake_task(argv):
            seen.append(argv)

        with mock.patch.dict(
            initialise.TASKS,
            {"fake": ("Fake task.", fake_task)},
            clear=True,
        ):
            initialise.main(["--game-dir", "gamedir"])

        self.assertEqual(seen, [["--game-dir", "gamedir"]])


if __name__ == "__main__":
    unittest.main()
