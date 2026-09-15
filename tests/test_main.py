"""
Tests for save orchestration, CLI validation and watch mode (main.py).

Run from the repository root:

    python -m unittest discover -s tests -v
"""

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core import config
import main
from helpers import (
    EXAMPLE_SAVE,
    MINIMAL_GOODS,
    MINIMAL_SAVE,
    MINIMAL_TECHS,
    MINIMAL_WESTERNISATION,
    OLDER_SAVE,
    REPO_ROOT,
    read_csv,
)

EXAMPLE_1850_SAVE = REPO_ROOT / "example_saves" / "example_japan_1850.v2"

# Same goods/techs/reforms as MINIMAL_SAVE, but the player has just
# westernised: civilized=yes with stale reform lines still present.
# Extraction must deactivate them (empty westernisation).
CIVILISED_SAVE = """date="1850.2.24"
player="JAP"
worldmarket=
{
\tprice_pool=
\t{
\t\tcoal=2.33002
\t\tiron=3.53003
\t\ttropical_wood=5.43002
\t\tmachine_parts=36.51001
\t\tclipper_convoy=42.01001
\t}
}
JAP=
{
\tcivilized=yes
\ttechnology=
\t{
\t\tflintlock_rifles={1 0.000}
\t}
\tland_reform=yes_land_reform
\tarmy_schools=no_army_schools
}
"""


class TestParseSave(unittest.TestCase):

    def test_parses_synthetic_save(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "autosave.v2"
            p.write_text(MINIMAL_SAVE, encoding="utf-8")
            game_date, result, techs, westernisation = main.parse_save(p)
            self.assertEqual(game_date, "1836-01-02")
            self.assertEqual(result, MINIMAL_GOODS)
            self.assertEqual(techs, MINIMAL_TECHS)
            self.assertEqual(westernisation, MINIMAL_WESTERNISATION)

    def test_parses_the_real_example_save(self):
        game_date, result, techs, westernisation = main.parse_save(EXAMPLE_SAVE)
        self.assertEqual(game_date, "1836-01-02")
        self.assertEqual(len(result), 48)
        # The good list is discovered from the save: late-game goods appear.
        self.assertEqual(result["coal"], 2.33002)
        self.assertEqual(result["furniture"], 4.93002)
        self.assertEqual(result["aeroplanes"], 110.0)
        self.assertEqual(result["radio"], 16.0)
        # JAP starts with no unlocked technologies.
        self.assertEqual(techs, set())
        # ...but with all 15 westernisation levels at their base.
        self.assertEqual(len(westernisation), 15)
        self.assertEqual(westernisation["land_reform"], "no_land_reform")
        self.assertEqual(westernisation["foreign_navies"], "no_foreign_navies")

    def test_parses_civilised_save_ignores_stale_reforms(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "civilised.v2"
            p.write_text(CIVILISED_SAVE, encoding="utf-8")
            game_date, _, techs, westernisation = main.parse_save(p)
            self.assertEqual(game_date, "1850-02-24")
            self.assertEqual(techs, MINIMAL_TECHS)
            self.assertEqual(westernisation, {})

    def test_parses_real_1850_example_as_deactivated(self):
        _, _, _, westernisation = main.parse_save(EXAMPLE_1850_SAVE)
        self.assertEqual(westernisation, {})


class TestProcessSave(unittest.TestCase):

    def test_missing_file_returns_false(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            output = root / "goods.csv"
            processed = root / "processed.json"
            with redirect_stdout(io.StringIO()):
                result = main.process_save(
                    root / "missing.v2", output, processed, set()
                )
            self.assertFalse(result)
            self.assertFalse(output.exists())
            self.assertFalse(processed.exists())

    def test_unparseable_save_returns_false_and_prints_error(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            save = root / "bad.v2"
            save.write_text("no date or price pool here\n", encoding="utf-8")
            output = root / "goods.csv"
            processed = root / "processed.json"
            tech_changes = root / "technology_changes.csv"
            westernisation_changes = root / "westernisation_changes.csv"
            out = io.StringIO()
            with redirect_stdout(out):
                result = main.process_save(
                    save, output, processed, set()
                )
            self.assertFalse(result)
            self.assertIn("Could not process bad.v2", out.getvalue())
            self.assertFalse(output.exists())
            self.assertFalse(processed.exists())
            self.assertFalse(tech_changes.exists())
            self.assertFalse(westernisation_changes.exists())

    def test_new_date_is_recorded(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            save = root / "autosave.v2"
            save.write_text(MINIMAL_SAVE, encoding="utf-8")
            output = root / "goods.csv"
            processed = root / "processed.json"
            tech_changes = root / "technology_changes.csv"
            westernisation_changes = root / "westernisation_changes.csv"
            processed_dates = set()

            out = io.StringIO()
            with redirect_stdout(out):
                result = main.process_save(
                    save, output, processed, processed_dates
                )

            self.assertTrue(result)
            self.assertIn(
                "Recorded 1836-01-02: 5 goods, "
                "1 technologies (1 new), "
                "2 westernisation (2 changed)",
                out.getvalue(),
            )
            self.assertEqual(len(read_csv(output)), len(MINIMAL_GOODS) + 1)
            # First tech-tracked date writes the full snapshot.
            self.assertEqual(
                read_csv(tech_changes),
                [
                    ["date", "technology", "old_value", "new_value"],
                    ["1836-01-02", "flintlock_rifles", "0", "1"],
                ],
            )
            # First westernisation-tracked date writes the full snapshot.
            self.assertEqual(
                read_csv(westernisation_changes),
                [
                    ["date", "westernisation", "old_value", "new_value"],
                    ["1836-01-02", "army_schools", "", "no_army_schools"],
                    ["1836-01-02", "land_reform", "", "no_land_reform"],
                ],
            )
            self.assertIn("1836-01-02", processed_dates)
            self.assertEqual(
                json.loads(processed.read_text(encoding="utf-8")),
                ["1836-01-02"],
            )

    def test_already_processed_date_is_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            save = root / "autosave.v2"
            save.write_text(MINIMAL_SAVE, encoding="utf-8")
            output = root / "goods.csv"
            processed = root / "processed.json"
            tech_changes = root / "technology_changes.csv"
            westernisation_changes = root / "westernisation_changes.csv"
            processed_dates = set()

            with redirect_stdout(io.StringIO()):
                main.process_save(save, output, processed, processed_dates)

            rows_before = read_csv(output)
            tech_rows_before = read_csv(tech_changes)
            westernisation_rows_before = read_csv(westernisation_changes)

            with redirect_stdout(io.StringIO()):
                result = main.process_save(
                    save, output, processed, processed_dates
                )

            self.assertFalse(result)
            self.assertEqual(read_csv(output), rows_before)
            self.assertEqual(read_csv(tech_changes), tech_rows_before)
            self.assertEqual(read_csv(westernisation_changes), westernisation_rows_before)

    def test_fresh_civilised_date_writes_header_only(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            save = root / "civilised.v2"
            save.write_text(CIVILISED_SAVE, encoding="utf-8")
            output = root / "goods.csv"
            processed = root / "processed.json"
            westernisation_changes = root / "westernisation_changes.csv"
            out = io.StringIO()
            with redirect_stdout(out):
                result = main.process_save(
                    save, output, processed, set()
                )
            self.assertTrue(result)
            self.assertIn("0 westernisation (0 changed)", out.getvalue())
            self.assertEqual(
                read_csv(westernisation_changes),
                [["date", "westernisation", "old_value", "new_value"]],
            )

    def test_westernisation_date_deactivates_tracked_reforms(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            uncivilised = root / "autosave.v2"
            uncivilised.write_text(MINIMAL_SAVE, encoding="utf-8")
            civilised = root / "civilised.v2"
            civilised.write_text(CIVILISED_SAVE, encoding="utf-8")
            output = root / "goods.csv"
            processed = root / "processed.json"
            westernisation_changes = root / "westernisation_changes.csv"
            processed_dates = set()

            with redirect_stdout(io.StringIO()):
                main.process_save(uncivilised, output, processed, processed_dates)

            out = io.StringIO()
            with redirect_stdout(out):
                result = main.process_save(
                    civilised, output, processed, processed_dates
                )

            self.assertTrue(result)
            self.assertIn("0 westernisation (2 changed)", out.getvalue())
            self.assertEqual(
                read_csv(westernisation_changes),
                [
                    ["date", "westernisation", "old_value", "new_value"],
                    ["1836-01-02", "army_schools", "", "no_army_schools"],
                    ["1836-01-02", "land_reform", "", "no_land_reform"],
                    ["1850-02-24", "army_schools", "no_army_schools", ""],
                    ["1850-02-24", "land_reform", "no_land_reform", ""],
                ],
            )


class TestProcessExistingSaves(unittest.TestCase):

    def test_processes_named_files(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            save_dir = root / "save"
            save_dir.mkdir()
            (save_dir / "autosave.v2").write_text(
                MINIMAL_SAVE, encoding="utf-8"
            )
            out = root / "out"
            out.mkdir()

            with mock.patch.object(main, "SAVE_DIR", save_dir):
                with redirect_stdout(io.StringIO()):
                    main.process_existing_saves(out, ["autosave.v2"])

            rows = read_csv(out / "goods_prices.csv")
            self.assertEqual(rows[0], ["date", "good", "price"])
            self.assertEqual(len(rows), len(MINIMAL_GOODS) + 1)
            self.assertEqual(
                json.loads((out / "processed_dates.json").read_text(encoding="utf-8")),
                ["1836-01-02"],
            )
            self.assertEqual(
                read_csv(out / "technology_changes.csv"),
                [
                    ["date", "technology", "old_value", "new_value"],
                    ["1836-01-02", "flintlock_rifles", "0", "1"],
                ],
            )
            self.assertEqual(
                read_csv(out / "westernisation_changes.csv"),
                [
                    ["date", "westernisation", "old_value", "new_value"],
                    ["1836-01-02", "army_schools", "", "no_army_schools"],
                    ["1836-01-02", "land_reform", "", "no_land_reform"],
                ],
            )

    def test_processes_custom_named_manual_save(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            save_dir = root / "save"
            save_dir.mkdir()
            (save_dir / "France_1840.v2").write_text(
                MINIMAL_SAVE, encoding="utf-8"
            )
            out = root / "out"
            out.mkdir()

            with mock.patch.object(main, "SAVE_DIR", save_dir):
                with redirect_stdout(io.StringIO()):
                    main.process_existing_saves(out, ["France_1840.v2"])

            rows = read_csv(out / "goods_prices.csv")
            self.assertEqual(rows[0], ["date", "good", "price"])
            self.assertEqual(len(rows), len(MINIMAL_GOODS) + 1)
            self.assertEqual(
                json.loads((out / "processed_dates.json").read_text(encoding="utf-8")),
                ["1836-01-02"],
            )

    def test_missing_file_prints_not_found(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            save_dir = root / "save"
            save_dir.mkdir()
            out = root / "out"
            out.mkdir()

            stdout = io.StringIO()
            with mock.patch.object(main, "SAVE_DIR", save_dir):
                with redirect_stdout(stdout):
                    main.process_existing_saves(out, ["autosave.v2"])

            self.assertIn("Not found: autosave.v2", stdout.getvalue())
            self.assertFalse((out / "goods_prices.csv").exists())

    def test_dedup_across_runs_and_across_files(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            save_dir = root / "save"
            save_dir.mkdir()
            (save_dir / "autosave.v2").write_text(
                MINIMAL_SAVE, encoding="utf-8"
            )
            (save_dir / "oldautosave.v2").write_text(
                OLDER_SAVE, encoding="utf-8"
            )
            out = root / "out"
            out.mkdir()

            with mock.patch.object(main, "SAVE_DIR", save_dir):
                with redirect_stdout(io.StringIO()):
                    main.process_existing_saves(
                        out, ["autosave.v2", "oldautosave.v2"]
                    )

            rows = read_csv(out / "goods_prices.csv")
            # The second file has the same in-game date: no duplicate rows.
            self.assertEqual(len(rows), len(MINIMAL_GOODS) + 1)
            self.assertEqual(
                json.loads((out / "processed_dates.json").read_text(encoding="utf-8")),
                ["1836-01-02"],
            )


class TestWatch(unittest.TestCase):

    def _make_watch_env(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        save_dir = root / "save"
        save_dir.mkdir()
        out = root / "out"
        out.mkdir()
        return save_dir, out

    def test_no_change_no_processing(self):
        save_dir, out = self._make_watch_env()
        autosave = save_dir / "autosave.v2"
        autosave.write_text(MINIMAL_SAVE, encoding="utf-8")

        with mock.patch.object(main, "SAVE_DIR", save_dir), \
                mock.patch("main.time.sleep", side_effect=KeyboardInterrupt), \
                mock.patch("main.process_save") as mock_process:
            with redirect_stdout(io.StringIO()):
                main.watch(out)

        mock_process.assert_not_called()

    def test_mtime_change_triggers_single_processing(self):
        save_dir, out = self._make_watch_env()
        autosave = save_dir / "autosave.v2"
        autosave.write_text(MINIMAL_SAVE, encoding="utf-8")
        os.utime(autosave, (0, 0))

        calls = {"n": 0}

        def sleep_hook(seconds):
            calls["n"] += 1
            if calls["n"] == 1:
                os.utime(autosave, (5, 5))
                return
            if calls["n"] == 2:
                return
            raise KeyboardInterrupt

        with mock.patch.object(main, "SAVE_DIR", save_dir), \
                mock.patch("main.time.sleep", side_effect=sleep_hook), \
                mock.patch("main.process_save", return_value=True) as mock_process:
            with redirect_stdout(io.StringIO()):
                main.watch(out)

        self.assertEqual(mock_process.call_count, 1)
        self.assertEqual(mock_process.call_args.args[0], autosave)

    def test_rotated_files_are_never_processed(self):
        save_dir, out = self._make_watch_env()
        for name in ("autosave.v2", "oldautosave.v2", "olderautosave.v2"):
            p = save_dir / name
            p.write_text(MINIMAL_SAVE, encoding="utf-8")
            os.utime(p, (0, 0))

        calls = {"n": 0}

        def sleep_hook(seconds):
            calls["n"] += 1
            if calls["n"] == 1:
                # Only the rotated files change; the live autosave does not.
                os.utime(save_dir / "oldautosave.v2", (5, 5))
                os.utime(save_dir / "olderautosave.v2", (5, 5))
                return
            raise KeyboardInterrupt

        with mock.patch.object(main, "SAVE_DIR", save_dir), \
                mock.patch("main.time.sleep", side_effect=sleep_hook), \
                mock.patch("main.process_save") as mock_process:
            with redirect_stdout(io.StringIO()):
                main.watch(out)

        mock_process.assert_not_called()


class TestConstants(unittest.TestCase):

    def test_watch_mode_tracks_only_the_live_autosave(self):
        self.assertEqual(config.WATCH_FILES, ["autosave.v2"])

    def test_output_filenames(self):
        self.assertEqual(config.OUTPUT_FILENAME, "goods_prices.csv")
        self.assertEqual(config.PROCESSED_FILENAME, "processed_dates.json")


class TestMain(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.out = self.root / "out"
        self.out.mkdir()

    def run_main(self, argv):
        with mock.patch.object(sys, "argv", argv):
            with redirect_stderr(io.StringIO()):
                main.main()

    def test_valid_once_calls_process_existing_saves(self):
        argv = ["main.py", "--once", "--files", "autosave.v2", str(self.out)]
        with mock.patch("main.process_existing_saves") as mock_process:
            self.run_main(argv)
        mock_process.assert_called_once_with(self.out, ["autosave.v2"])

    def test_valid_watch_calls_watch(self):
        argv = ["main.py", "--watch", str(self.out)]
        with mock.patch("main.watch") as mock_watch:
            self.run_main(argv)
        mock_watch.assert_called_once_with(self.out)

    def test_once_without_files_errors(self):
        argv = ["main.py", "--once", str(self.out)]
        with self.assertRaises(SystemExit):
            self.run_main(argv)

    def test_files_without_once_errors(self):
        argv = ["main.py", "--files", "autosave.v2", str(self.out)]
        with self.assertRaises(SystemExit):
            self.run_main(argv)

    def test_once_and_watch_together_error(self):
        argv = ["main.py", "--once", "--watch", str(self.out)]
        with self.assertRaises(SystemExit):
            self.run_main(argv)

    def test_valid_once_with_custom_save_name_calls_process_existing_saves(self):
        argv = ["main.py", "--once", "--files", "mysave.v2", str(self.out)]
        with mock.patch("main.process_existing_saves") as mock_process:
            self.run_main(argv)
        mock_process.assert_called_once_with(self.out, ["mysave.v2"])

    def test_non_v2_extension_errors(self):
        argv = ["main.py", "--once", "--files", "notes.txt", str(self.out)]
        with self.assertRaises(SystemExit):
            self.run_main(argv)

    def test_save_file_with_path_errors(self):
        for bad in (
            "subdir/mysave.v2",
            "subdir\\mysave.v2",
            "../mysave.v2",
        ):
            with self.subTest(bad=bad):
                argv = [
                    "main.py",
                    "--once",
                    "--files",
                    bad,
                    str(self.out),
                ]
                with self.assertRaises(SystemExit):
                    self.run_main(argv)

    def test_empty_save_file_name_errors(self):
        argv = ["main.py", "--once", "--files", "autosave.v2,", str(self.out)]
        with self.assertRaises(SystemExit):
            self.run_main(argv)

    def test_non_existent_output_directory_errors(self):
        argv = [
            "main.py",
            "--once",
            "--files",
            "autosave.v2",
            str(self.root / "nope"),
        ]
        with self.assertRaises(SystemExit):
            self.run_main(argv)

    def test_no_mode_defaults_to_once_and_requires_files(self):
        argv = ["main.py", str(self.out)]
        with self.assertRaises(SystemExit):
            self.run_main(argv)


if __name__ == "__main__":
    unittest.main()
