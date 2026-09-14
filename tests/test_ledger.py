"""
Tests for the processed-dates ledger and output paths (common.py).

Run from the repository root:

    python -m unittest discover -s tests -v
"""

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import common


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


class TestOutputPaths(unittest.TestCase):

    def test_returns_csv_and_processed_paths(self):
        out = Path("some/output")
        self.assertEqual(
            common.output_paths(out),
            (out / "goods_prices.csv", out / "processed_dates.json"),
        )


if __name__ == "__main__":
    unittest.main()
