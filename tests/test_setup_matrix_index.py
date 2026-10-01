"""
Tests for the matrix index setup (setup/research_modifiers/build_matrix_index.py).

Run from the repository root:

    python -m unittest discover -s tests -v
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from setup.research_modifiers import build_matrix_index
from helpers import make_category_game_dir


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class TestIndexRows(unittest.TestCase):

    def test_indexes_each_matrix_with_counts(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            write(
                out / "tech_modifiers/army/military_modifiers.csv",
                "modifier,a,b\nmorale,0.25,0\ncombat_width,-5,0\n",
            )
            write(
                out / "tech_modifiers/commerce/military_modifiers.csv",
                "modifier,c\n",
            )
            write(
                out / "invention_modifiers/navy/per_unit_naval_modifiers.csv",
                "modifier,d\necruiser_hull,5,0\n",
            )
            write(
                out / "westernisation_modifiers/economic/colonial_modifiers.csv",
                "modifier,no_x,yes_x\ncolonial_points,0,100\n",
            )
            self.assertEqual(
                build_matrix_index.index_rows(out),
                [
                    [
                        "invention_modifiers/navy/per_unit_naval_modifiers.csv",
                        "per_unit_naval",
                        "1",
                        "1",
                        "1",
                    ],
                    [
                        "tech_modifiers/army/military_modifiers.csv",
                        "military",
                        "2",
                        "2",
                        "2",
                    ],
                    [
                        "tech_modifiers/commerce/military_modifiers.csv",
                        "military",
                        "0",
                        "1",
                        "0",
                    ],
                    [
                        "westernisation_modifiers/economic/colonial_modifiers.csv",
                        "colonial",
                        "1",
                        "2",
                        "1",
                    ],
                ],
            )

    def test_ignores_non_matrix_files(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            write(out / "inventions_map.json", "{}")
            write(out / "modifiers_from_research_list.txt", "# header\nfoo\n")
            write(out / "tech_modifiers/army/notes.csv", "not,a,matrix\n")
            write(
                out / "tech_modifiers/army/rgo_goods_modifiers.csv",
                "modifier,a\n",
            )
            self.assertEqual(
                build_matrix_index.index_rows(out),
                [
                    [
                        "tech_modifiers/army/rgo_goods_modifiers.csv",
                        "rgo_goods",
                        "0",
                        "1",
                        "0",
                    ]
                ],
            )

    def test_missing_trees_are_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(build_matrix_index.index_rows(Path(d)), [])

    def test_empty_matrix_file_raises(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            write(out / "tech_modifiers/army/other_modifiers.csv", "")
            with self.assertRaises(ValueError):
                build_matrix_index.index_rows(out)

    def test_matrix_without_modifier_column_raises(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            write(out / "tech_modifiers/army/other_modifiers.csv", "a,b\n1,2\n")
            with self.assertRaises(ValueError):
                build_matrix_index.index_rows(out)


class TestMatrixIndexMain(unittest.TestCase):

    def test_writes_index_file(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            out = root / "out"
            write(
                out / "tech_modifiers/army/military_modifiers.csv",
                "modifier,a,b\nmorale,0.25,0\n",
            )
            result = build_matrix_index.main(
                ["--output-dir", str(out), "--source", "modded"]
            )
            self.assertEqual(result, out / "matrix_index.csv")
            self.assertEqual(
                result.read_text(encoding="utf-8").splitlines(),
                [
                    "file,kind,rows,columns,nonzero_cells",
                    "tech_modifiers/army/military_modifiers.csv,military,1,2,1",
                ],
            )

    def test_accepts_and_ignores_dispatcher_flags(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            out = root / "out"
            out.mkdir()
            save = root / "test.v2"
            save.write_text("date=\"1836.1.2\"\n", encoding="utf-8")
            # --game-dir/--check-save/--source are forwarded by the
            # dispatcher; the index task accepts and ignores them.
            build_matrix_index.main(
                [
                    "--game-dir", str(root / "no-such-install"),
                    "--output-dir", str(out),
                    "--check-save", str(save),
                    "--source", "mymod",
                ]
            )
            self.assertTrue((out / "matrix_index.csv").exists())

    def test_index_after_matrix_tasks(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            out = root / "out"
            out.mkdir()
            from setup.research_modifiers import build_colonial_matrices

            build_colonial_matrices.main(
                [
                    "--game-dir", str(make_category_game_dir(root)),
                    "--output-dir", str(out),
                    "--source", "modded",
                ]
            )
            rows = build_matrix_index.index_rows(out)
            self.assertEqual(len(rows), 4)
            kinds = {row[1] for row in rows}
            self.assertEqual(kinds, {"colonial"})

    def test_missing_output_dir_errors(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(SystemExit):
                build_matrix_index.main(
                    ["--output-dir", str(Path(d) / "nope")]
                )


if __name__ == "__main__":
    unittest.main()
