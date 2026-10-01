"""One-shot initialisation: build the matrix index for a game variant.

The per-category matrix tasks write one CSV per group directory
(``<output-dir>/{tech,invention,westernisation}_modifiers/<group>/``),
and most groups have no effect at all in most categories — so those
files are header-only. This task reads the generated matrices back and
writes a single index, so the spreadsheet (or a human) can find the
populated files without scanning 156 of them::

    file,kind,rows,columns,nonzero_cells
    tech_modifiers/army/military_modifiers.csv,military,32,30,55
    tech_modifiers/commerce/military_modifiers.csv,military,0,30,0

Indexing the written files (rather than sharing in-memory state) keeps
the result correct regardless of which tasks ran, and in what order.
The task takes the same ``--game-dir``/``--check-save``/``--source``
flags as every other task so the dispatcher can forward them
uniformly; it ignores them, as it reads generated output, not the game
install.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from core.config import GAME_DIR, VANILLA_DATA_DIR

OUTPUT_FILENAME = "matrix_index.csv"

# The three matrix trees and the glob matching the matrices inside them.
MATRIX_TREES = (
    "tech_modifiers",
    "invention_modifiers",
    "westernisation_modifiers",
)
MATRIX_SUFFIX = "_modifiers.csv"

HEADER = ["file", "kind", "rows", "columns", "nonzero_cells"]


def index_rows(output_dir: Path) -> list[list[str]]:
    """Return one index row per generated matrix, sorted by file path."""
    rows: list[list[str]] = []

    for tree in MATRIX_TREES:
        tree_dir = output_dir / tree

        if not tree_dir.is_dir():
            continue

        for path in sorted(tree_dir.rglob(f"*{MATRIX_SUFFIX}")):
            if not path.is_file():
                continue

            with path.open("r", encoding="utf-8", newline="") as f:
                matrix = list(csv.reader(f))

            if not matrix:
                raise ValueError(f"Matrix file is empty: {path}")

            header_row, body = matrix[0], matrix[1:]

            if header_row[0] != "modifier":
                raise ValueError(
                    f"Matrix file has no modifier column: {path}"
                )

            columns = len(header_row) - 1
            nonzero = sum(
                1
                for row in body
                for cell in row[1:]
                if float(cell) != 0
            )
            relative = path.relative_to(output_dir).as_posix()
            rows.append(
                [
                    relative,
                    path.stem[: -len("_modifiers")],
                    str(len(body)),
                    str(columns),
                    str(nonzero),
                ]
            )

    return sorted(rows)


def write_index(output_dir: Path) -> Path:
    """Write the index for one game variant; return the file written."""
    output = output_dir / OUTPUT_FILENAME

    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(HEADER)
        writer.writerows(index_rows(output_dir))

    return output


def main(argv: list[str] | None = None) -> Path:
    parser = argparse.ArgumentParser(
        description="Index the generated modifier matrices.",
    )

    parser.add_argument(
        "--game-dir",
        type=Path,
        default=GAME_DIR,
        help="Ignored (this task reads generated output, not the install).",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=VANILLA_DATA_DIR,
        help="Directory holding one game variant's reference data "
        "(default: data/vanilla/). Must already exist.",
    )

    parser.add_argument(
        "--check-save",
        type=Path,
        default=None,
        help="Ignored (see --game-dir).",
    )

    parser.add_argument(
        "--source",
        default=None,
        help="Ignored (see --game-dir).",
    )

    args = parser.parse_args(argv)

    if not args.output_dir.is_dir():
        parser.error(
            f"Output directory does not exist: {args.output_dir}"
        )

    rows = index_rows(args.output_dir)
    output = write_index(args.output_dir)
    print(f"Indexed {len(rows)} matrices into {output}")

    return output


if __name__ == "__main__":
    main()
