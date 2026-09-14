"""
Tests for goods-price extraction and CSV output (goods.py).

Run from the repository root:

    python -m unittest discover -s tests -v
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import goods
from helpers import MINIMAL_GOODS, MINIMAL_SAVE, read_csv


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


if __name__ == "__main__":
    unittest.main()
