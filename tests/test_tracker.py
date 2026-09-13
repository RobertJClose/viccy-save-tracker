"""
Unit tests for the tracker package (main.py, common.py, goods.py, ...).

Run from the repository root:

    python -m unittest discover -s tests -v
"""

import csv
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

import init_inventions_map
import initialise

import common
import goods
import inventions
import main
import technologies
import unciv_reforms


REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_SAVE = REPO_ROOT / "example.v2"


# A small realistic save: header date, several price pools (only price_pool
# must be extracted), and a mix of plain / underscored / numeric good names.
MINIMAL_SAVE = """date="1836.1.2"
player="JAP"
worldmarket=
{
\tworldmarket_pool=
\t{
\t\tcoal=999.0
\t\tiron=888.0
\t}
\tprice_pool=
\t{
\t\tcoal=2.33002
\t\tiron=3.53003
\t\ttropical_wood=5.43002
\t\tmachine_parts=36.51001
\t\tclipper_convoy=42.01001
\t}
\tlast_price_history=
\t{
\t\tcoal=2.32001
\t}
\tsupply_pool=
\t{
\t\tcoal=1802.88763
\t}
}
JAP=
{
\ttechnology=
\t{
\t\tflintlock_rifles={1 0.000}
\t}
}
"""

MINIMAL_TECHS = {"flintlock_rifles"}

MINIMAL_GOODS = {
    "coal": 2.33002,
    "iron": 3.53003,
    "tropical_wood": 5.43002,
    "machine_parts": 36.51001,
    "clipper_convoy": 42.01001,
}

# Same in-game date but different prices: dedup must key on the date alone.
OLDER_SAVE = """date="1836.1.2"
player="JAP"
worldmarket=
{
\tprice_pool=
\t{
\t\tcoal=9.99
\t\tiron=8.88
\t\ttropical_wood=7.77
\t\tmachine_parts=6.66
\t\tclipper_convoy=5.55
\t}
}
JAP=
{
\ttechnology=
\t{
\t}
}
"""


def read_csv(path: Path) -> list[list[str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.reader(f))


class TestExtractGameDate(unittest.TestCase):

    def test_single_digit_month_and_day_are_zero_padded(self):
        self.assertEqual(common.extract_game_date(MINIMAL_SAVE), "1836-01-02")

    def test_already_padded_date_round_trips(self):
        text = 'date="1836.04.01"\n'
        self.assertEqual(common.extract_game_date(text), "1836-04-01")

    def test_two_digit_month_and_day(self):
        text = 'date="1836.12.31"\n'
        self.assertEqual(common.extract_game_date(text), "1836-12-31")

    def test_missing_date_raises(self):
        with self.assertRaises(ValueError):
            common.extract_game_date("no date line in here\n")

    def test_indented_date_line_is_not_matched(self):
        # Indented date lines (e.g. building_construction blocks) must not be
        # mistaken for the header. Only a line starting at column 0 is matched.
        text = 'player="JAP"\n\tdate="1836.5.6"\n'
        with self.assertRaises(ValueError):
            common.extract_game_date(text)

    def test_non_header_date_key_is_not_matched(self):
        text = 'price_history_last_update="1836.1.1"\n'
        with self.assertRaises(ValueError):
            common.extract_game_date(text)


class TestExtractGoods(unittest.TestCase):

    def test_extracts_only_price_pool(self):
        expected = MINIMAL_GOODS
        self.assertEqual(goods.extract_goods(MINIMAL_SAVE), expected)

    def test_does_not_match_worldmarket_pool(self):
        # "price_pool=" is a substring risk: worldmarket_pool must not match.
        text = """worldmarket=
{
\tworldmarket_pool=
\t{
\t\tcoal=999.0
\t}
}
"""
        with self.assertRaises(ValueError):
            goods.extract_goods(text)

    def test_missing_price_pool_raises(self):
        with self.assertRaises(ValueError):
            goods.extract_goods("no price pool anywhere\n")

    def test_empty_price_pool_raises(self):
        text = """worldmarket=
{
\tprice_pool=
\t{
\t}
}
"""
        with self.assertRaises(ValueError):
            goods.extract_goods(text)

    def test_values_parsed_as_floats(self):
        text = """worldmarket=
{
\tprice_pool=
\t{
\t\tcoal=2.33002
\t\tfurniture=0.00003
\t}
}
"""
        result = goods.extract_goods(text)
        self.assertEqual(result["coal"], 2.33002)
        self.assertEqual(result["furniture"], 0.00003)

    def test_integer_and_signed_values(self):
        text = """worldmarket=
{
\tprice_pool=
\t{
\t\tcoal=-1.5
\t\tsteel=+2.25
\t\tfish=5
\t}
}
"""
        self.assertEqual(
            goods.extract_goods(text),
            {"coal": -1.5, "steel": 2.25, "fish": 5.0},
        )


class TestReadSave(unittest.TestCase):

    def test_reads_plain_text(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "save.v2"
            p.write_text('date="1836.1.2"\ncoal=1\n', encoding="utf-8")
            self.assertEqual(
                common.read_save(p),
                'date="1836.1.2"\ncoal=1\n',
            )

    def test_invalid_utf8_byte_is_replaced_not_fatal(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "save.v2"
            p.write_bytes(b'date="1836.1.2"\ncoal=1\n\xff\n')
            self.assertEqual(
                common.read_save(p),
                'date="1836.1.2"\ncoal=1\n\ufffd\n',
            )


class TestParseSave(unittest.TestCase):

    def test_parses_synthetic_save(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "autosave.v2"
            p.write_text(MINIMAL_SAVE, encoding="utf-8")
            game_date, result, techs = main.parse_save(p)
            self.assertEqual(game_date, "1836-01-02")
            self.assertEqual(result, MINIMAL_GOODS)
            self.assertEqual(techs, MINIMAL_TECHS)

    def test_parses_the_real_example_save(self):
        game_date, result, techs = main.parse_save(EXAMPLE_SAVE)
        self.assertEqual(game_date, "1836-01-02")
        self.assertEqual(len(result), 48)
        # The good list is discovered from the save: late-game goods appear.
        self.assertEqual(result["coal"], 2.33002)
        self.assertEqual(result["furniture"], 4.93002)
        self.assertEqual(result["aeroplanes"], 110.0)
        self.assertEqual(result["radio"], 16.0)
        # JAP starts with no unlocked technologies.
        self.assertEqual(techs, set())


class TestProcessedDates(unittest.TestCase):

    def test_load_missing_file_returns_empty_without_warning(self):
        with tempfile.TemporaryDirectory() as d:
            err = io.StringIO()
            with redirect_stderr(err):
                result = common.load_processed_dates(Path(d) / "nope.json")
            self.assertEqual(result, set())
            self.assertEqual(err.getvalue(), "")

    def test_load_valid_list(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "processed.json"
            p.write_text('["1836-01-02", "1836-02-01"]', encoding="utf-8")
            self.assertEqual(
                common.load_processed_dates(p),
                {"1836-01-02", "1836-02-01"},
            )

    def test_load_corrupt_json_returns_empty_with_warning(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "processed.json"
            p.write_text("{{not json", encoding="utf-8")
            err = io.StringIO()
            with redirect_stderr(err):
                result = common.load_processed_dates(p)
            self.assertEqual(result, set())
            self.assertIn("Warning", err.getvalue())

    def test_load_valid_json_but_not_a_list_returns_empty_with_warning(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "processed.json"
            p.write_text('{"a": 1}', encoding="utf-8")
            err = io.StringIO()
            with redirect_stderr(err):
                result = common.load_processed_dates(p)
            self.assertEqual(result, set())
            self.assertIn("Warning", err.getvalue())

    def test_save_writes_sorted_json_list(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "processed.json"
            common.save_processed_dates(
                p, {"1836-02-01", "1836-01-02", "1836-03-02"}
            )
            data = json.loads(p.read_text(encoding="utf-8"))
            self.assertEqual(data, ["1836-01-02", "1836-02-01", "1836-03-02"])

    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "processed.json"
            dates = {"1836-01-02", "1836-02-01", "1836-04-03"}
            common.save_processed_dates(p, dates)
            self.assertEqual(common.load_processed_dates(p), dates)


class TestAppendObservations(unittest.TestCase):

    def test_creates_file_with_header_and_sorted_rows(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "goods.csv"
            goods.append_observations(
                out,
                "1836-01-02",
                {
                    "tropical_wood": 5.43,
                    "iron": 3.53003,
                    "furniture": 0.00003,
                    "coal": 2.33002,
                },
            )
            self.assertEqual(
                read_csv(out),
                [
                    ["date", "good", "price"],
                    ["1836-01-02", "coal", "2.33002"],
                    ["1836-01-02", "furniture", "0.00003"],
                    ["1836-01-02", "iron", "3.53003"],
                    ["1836-01-02", "tropical_wood", "5.43000"],
                ],
            )

    def test_appends_without_duplicate_header(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "goods.csv"
            goods.append_observations(out, "1836-01-02", {"coal": 2.33})
            goods.append_observations(out, "1836-02-01", {"iron": 3.53})

            rows = read_csv(out)
            self.assertEqual(rows[0], ["date", "good", "price"])
            self.assertEqual(
                sum(1 for r in rows if r == ["date", "good", "price"]),
                1,
            )
            self.assertIn(["1836-02-01", "iron", "3.53000"], rows)
            self.assertIn(["1836-01-02", "coal", "2.33000"], rows)

    def test_empty_goods_writes_header_only(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "goods.csv"
            goods.append_observations(out, "1836-01-02", {})
            self.assertEqual(read_csv(out), [["date", "good", "price"]])


class TestExtractPlayerTag(unittest.TestCase):

    def test_returns_player_tag(self):
        self.assertEqual(common.extract_player_tag(MINIMAL_SAVE), "JAP")

    def test_missing_player_raises(self):
        with self.assertRaises(ValueError):
            common.extract_player_tag('date="1836.1.2"\n')

    def test_indented_player_line_is_not_matched(self):
        with self.assertRaises(ValueError):
            common.extract_player_tag('\tplayer="JAP"\n')


class TestExtractCountryBlock(unittest.TestCase):

    def test_isolates_tag_block_at_column_zero(self):
        text = (
            'player="JAP"\n'
            'country="JAP"\n'
            "JAP=\n"
            "{\n"
            "\ttechnology=\n"
            "\t{\n"
            "\t}\n"
            "}\n"
        )
        block = common.extract_country_block(text, "JAP")
        self.assertIn("technology=", block)
        self.assertNotIn("player=", block)
        self.assertNotIn("country=", block)

    def test_missing_tag_raises(self):
        with self.assertRaises(ValueError):
            common.extract_country_block('player="JAP"\n', "JAP")

    def test_unbalanced_braces_raise(self):
        with self.assertRaises(ValueError):
            common.extract_country_block("JAP=\n{\n\ttechnology=\n", "JAP")


class TestExtractTechnologies(unittest.TestCase):

    def test_extracts_unlocked_names_ignoring_values(self):
        block = (
            "technology=\n"
            "{\n"
            "\tflintlock_rifles={1 0.000}\n"
            "\tclean_coal={1 0.000}\n"
            "}\n"
        )
        self.assertEqual(
            technologies.extract_technologies(block),
            {"flintlock_rifles", "clean_coal"},
        )

    def test_empty_block_yields_empty_set(self):
        self.assertEqual(
            technologies.extract_technologies("technology=\n{\n}\n"),
            set(),
        )

    def test_research_block_is_ignored(self):
        block = (
            "research=\n"
            "{\n"
            "\ttechnology=romanticism\n"
            "}\n"
            "technology=\n"
            "{\n"
            "\tflintlock_rifles={1 0.000}\n"
            "}\n"
        )
        self.assertEqual(
            technologies.extract_technologies(block),
            {"flintlock_rifles"},
        )

    def test_missing_block_raises(self):
        with self.assertRaises(ValueError):
            technologies.extract_technologies("human=yes\n")

    def test_real_example_save_eng_block(self):
        text = EXAMPLE_SAVE.read_text(encoding="utf-8", errors="replace")
        block = common.extract_country_block(text, "ENG")
        techs = technologies.extract_technologies(block)
        self.assertEqual(len(techs), 35)
        self.assertIn("flintlock_rifles", techs)
        self.assertIn("clean_coal", techs)
        # Currently being researched, not unlocked.
        self.assertNotIn("iron_muzzle_loaded_artillery", techs)


class TestTechnologyChanges(unittest.TestCase):

    def test_first_date_writes_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "technology_changes.csv"
            acquired, lost = technologies.append_technology_changes(
                out, "1836-01-02", set(), {"clean_coal", "flintlock_rifles"}
            )
            self.assertEqual(acquired, {"clean_coal", "flintlock_rifles"})
            self.assertEqual(lost, set())
            self.assertEqual(
                read_csv(out),
                [
                    ["date", "technology", "old_value", "new_value"],
                    ["1836-01-02", "clean_coal", "0", "1"],
                    ["1836-01-02", "flintlock_rifles", "0", "1"],
                ],
            )

    def test_first_date_with_no_techs_writes_header_only(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "technology_changes.csv"
            acquired, lost = technologies.append_technology_changes(
                out, "1836-01-02", set(), set()
            )
            self.assertEqual(acquired, set())
            self.assertEqual(lost, set())
            self.assertEqual(
                read_csv(out),
                [["date", "technology", "old_value", "new_value"]],
            )

    def test_later_date_appends_only_deltas(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "technology_changes.csv"
            technologies.append_technology_changes(
                out, "1836-01-02", set(), {"flintlock_rifles"}
            )
            acquired, lost = technologies.append_technology_changes(
                out,
                "1836-02-01",
                {"flintlock_rifles"},
                {"flintlock_rifles", "clean_coal"},
            )
            self.assertEqual(acquired, {"clean_coal"})
            self.assertEqual(lost, set())
            self.assertEqual(
                read_csv(out),
                [
                    ["date", "technology", "old_value", "new_value"],
                    ["1836-01-02", "flintlock_rifles", "0", "1"],
                    ["1836-02-01", "clean_coal", "0", "1"],
                ],
            )

    def test_lost_technology_is_recorded(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "technology_changes.csv"
            technologies.append_technology_changes(
                out, "1836-01-02", set(), {"a_tech", "b_tech"}
            )
            acquired, lost = technologies.append_technology_changes(
                out, "1836-02-01", {"a_tech", "b_tech"}, {"a_tech"}
            )
            self.assertEqual(acquired, set())
            self.assertEqual(lost, {"b_tech"})
            rows = read_csv(out)
            self.assertIn(["1836-02-01", "b_tech", "1", "0"], rows)
            self.assertEqual(
                technologies.load_technology_state(out), {"a_tech"}
            )

    def test_unchanged_date_appends_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "technology_changes.csv"
            technologies.append_technology_changes(
                out, "1836-01-02", set(), {"flintlock_rifles"}
            )
            before = read_csv(out)
            acquired, lost = technologies.append_technology_changes(
                out,
                "1836-02-01",
                {"flintlock_rifles"},
                {"flintlock_rifles"},
            )
            self.assertEqual(acquired, set())
            self.assertEqual(lost, set())
            self.assertEqual(read_csv(out), before)

    def test_replay_reconstructs_state(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "technology_changes.csv"
            technologies.append_technology_changes(
                out, "1836-01-02", set(), set()
            )
            technologies.append_technology_changes(
                out, "1836-02-01", set(), {"a_tech", "b_tech"}
            )
            technologies.append_technology_changes(
                out, "1836-03-01", {"a_tech", "b_tech"}, {"b_tech", "c_tech"}
            )
            self.assertEqual(
                technologies.load_technology_state(out),
                {"b_tech", "c_tech"},
            )

    def test_missing_file_replays_to_empty(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(
                technologies.load_technology_state(
                    Path(d) / "technology_changes.csv"
                ),
                set(),
            )

    def test_corrupt_file_warns_and_replays_to_empty(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "technology_changes.csv"
            out.write_text("date,technology\n1836-01-02\n", encoding="utf-8")
            err = io.StringIO()
            with redirect_stderr(err):
                result = technologies.load_technology_state(out)
            self.assertEqual(result, set())
            self.assertIn("Warning", err.getvalue())


class TestOutputPaths(unittest.TestCase):

    def test_returns_csv_and_processed_paths(self):
        out = Path("some/output")
        self.assertEqual(
            common.output_paths(out),
            (out / "goods_prices.csv", out / "processed_dates.json"),
        )


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

    def test_new_date_is_recorded(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            save = root / "autosave.v2"
            save.write_text(MINIMAL_SAVE, encoding="utf-8")
            output = root / "goods.csv"
            processed = root / "processed.json"
            tech_changes = root / "technology_changes.csv"
            processed_dates = set()

            out = io.StringIO()
            with redirect_stdout(out):
                result = main.process_save(
                    save, output, processed, processed_dates
                )

            self.assertTrue(result)
            self.assertIn(
                "Recorded 1836-01-02: 5 goods, 1 technologies (1 new)",
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
            processed_dates = set()

            with redirect_stdout(io.StringIO()):
                main.process_save(save, output, processed, processed_dates)

            rows_before = read_csv(output)
            tech_rows_before = read_csv(tech_changes)

            with redirect_stdout(io.StringIO()):
                result = main.process_save(
                    save, output, processed, processed_dates
                )

            self.assertFalse(result)
            self.assertEqual(read_csv(output), rows_before)
            self.assertEqual(read_csv(tech_changes), tech_rows_before)


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
        self.assertEqual(common.WATCH_FILES, ["autosave.v2"])

    def test_save_files_are_the_three_rotated_names(self):
        self.assertEqual(
            common.SAVE_FILES,
            ["autosave.v2", "oldautosave.v2", "olderautosave.v2"],
        )

    def test_output_filenames(self):
        self.assertEqual(common.OUTPUT_FILENAME, "goods_prices.csv")
        self.assertEqual(common.PROCESSED_FILENAME, "processed_dates.json")


class TestStubs(unittest.TestCase):
    """Future tracking modules exist but are not implemented yet."""

    def test_invention_extraction_is_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            inventions.extract_invention_ids("JAP=\n{\n}\n")

    def test_unciv_reform_extraction_is_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            unciv_reforms.extract_unciv_reforms("JAP=\n{\n}\n")


# A synthetic game install: two invention files exercising comments,
# nested blocks, cross-references and unusual-but-valid names.
INIT_FIXTURE_A = """#tech_group_one
first_invention = {
\tlimit = { some_tech = 1 }
\tchance = {
\t\tbase = 2
\t\tmodifier = {
\t\t\tfactor = 2
\t\t\tinvention = other_invention
\t\t}
\t}
\teffect = {
\t\tmorale = 0.15
\t}
}
# A commented-out invention must not take an ID.
#dead_invention = {
#\tlimit = { some_tech = 1 }
#}
genetics:_heredity = {
\tlimit = { medicine = 1 } # inline comment
\tchance = {
\t\tbase = 2
\t}
}
"""

INIT_FIXTURE_B = """populism_vs._establishment = {
\tlimit = { state_n_government = 1 }
}
15_inch_main_armament = {
\tlimit = { modern_naval_design = 1 }
\tchance = {
\t\tbase = 2
\t\tmodifier = {
\t\t\tfactor = 2
\t\t\tinvention = first_invention # cross-file reference
\t\t}
\t}
}
"""


def make_game_dir(root: Path) -> Path:
    game_dir = root / "game"
    inventions = game_dir / "inventions"
    inventions.mkdir(parents=True)
    (inventions / "b_second.txt").write_text(INIT_FIXTURE_B, encoding="utf-8")
    (inventions / "a_first.txt").write_text(INIT_FIXTURE_A, encoding="utf-8")
    return game_dir


class TestStripComments(unittest.TestCase):

    def test_full_line_and_inline_comments_removed(self):
        self.assertEqual(
            init_inventions_map.strip_comments(
                "# header\nfoo = 1 # trailing\nbar = 2\n"
            ),
            "\nfoo = 1 \nbar = 2",
        )

    def test_hash_inside_quotes_preserved(self):
        self.assertEqual(
            init_inventions_map.strip_comments('name = "a#b"\n'),
            'name = "a#b"',
        )


class TestExtractInventionNames(unittest.TestCase):

    def test_collects_only_top_level_blocks_in_order(self):
        self.assertEqual(
            init_inventions_map.extract_invention_names(INIT_FIXTURE_A),
            ["first_invention", "genetics:_heredity"],
        )

    def test_unusual_names_matched(self):
        self.assertEqual(
            init_inventions_map.extract_invention_names(INIT_FIXTURE_B),
            ["populism_vs._establishment", "15_inch_main_armament"],
        )

    def test_empty_file_yields_nothing(self):
        self.assertEqual(init_inventions_map.extract_invention_names("# only\n"), [])


class TestBuildInventionList(unittest.TestCase):

    def test_files_read_in_sorted_order(self):
        with tempfile.TemporaryDirectory() as d:
            names, files = init_inventions_map.build_invention_list(
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
                init_inventions_map.build_invention_list(Path(d) / "nope")

    def test_empty_inventions_dir_raises(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "inventions").mkdir()
            with self.assertRaises(FileNotFoundError):
                init_inventions_map.build_invention_list(Path(d))


class TestValidateAgainstSave(unittest.TestCase):

    NAMES = ["aaa", "b:b", "ccc"]

    def test_ids_within_range_pass(self):
        init_inventions_map.validate_against_save(
            self.NAMES,
            "active_inventions=\n{\n1 3 \t}\n",
            "test.v2",
            check_anchors=False,
        )

    def test_out_of_range_id_raises(self):
        with self.assertRaises(ValueError):
            init_inventions_map.validate_against_save(
                self.NAMES,
                "active_inventions=\n{\n1 4 \t}\n",
                "test.v2",
                check_anchors=False,
            )

    def test_zero_id_raises(self):
        with self.assertRaises(ValueError):
            init_inventions_map.validate_against_save(
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
            result = init_inventions_map.main(
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
                init_inventions_map.main(
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
            init_inventions_map.main(
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
                init_inventions_map.main(
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

    def test_unknown_save_file_name_errors(self):
        argv = ["main.py", "--once", "--files", "bogus.v2", str(self.out)]
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
