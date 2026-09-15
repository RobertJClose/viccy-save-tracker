"""One-shot setup tasks (run manually, not part of tracking).

Today this builds the invention ID -> name mapping and the exhaustive
modifier-name list; future initialisation work registers in TASKS below.

Reference data lives in one directory per game variant: data/vanilla/
is the committed vanilla default, and modded installs generate sibling
directories (data/<mod>/).

Usage:
    python -m setup.initialise [--game-dir ...] [--output-dir ...]
        [--source ...] [--check-save ...]
    python -m setup.initialise --list
"""

from __future__ import annotations

import argparse
from pathlib import Path

from core.config import VANILLA_DATA_DIR
from setup.build_inventions_map import (
    OUTPUT_FILENAME as INVENTIONS_OUTPUT_FILENAME,
)
from setup.build_inventions_map import main as build_inventions_map_main
from setup.build_modifiers_list import (
    OUTPUT_FILENAME as MODIFIERS_OUTPUT_FILENAME,
)
from setup.build_modifiers_list import main as build_modifiers_list_main

TASKS = {
    "inventions-map": (
        "Build inventions_map.json (ID -> name) from the game install.",
        build_inventions_map_main,
        INVENTIONS_OUTPUT_FILENAME,
    ),
    "modifiers-list": (
        "Build modifiers_list.txt (exhaustive modifier names) from the game install.",
        build_modifiers_list_main,
        MODIFIERS_OUTPUT_FILENAME,
    ),
}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Run one-shot tracker setup tasks.",
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List tasks and exit.",
    )

    parser.add_argument(
        "--game-dir",
        type=Path,
        default=None,
        help="Forwarded to tasks (overrides GAME_DIR in core/config.py).",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=VANILLA_DATA_DIR,
        help=(
            "Directory holding one game variant's reference data "
            "(default: data/vanilla/). Must already exist."
        ),
    )

    parser.add_argument(
        "--source",
        default=None,
        help=(
            "Forwarded to tasks as their source label "
            "(e.g. a mod name for modded installs)."
        ),
    )

    parser.add_argument(
        "--check-save",
        type=Path,
        default=None,
        help="Forwarded to tasks (save file to validate against).",
    )

    args = parser.parse_args(argv)

    if args.list:
        for name, entry in TASKS.items():
            print(f"{name}: {entry[0]}")
        return

    # The output directory must already exist. It is how the user tells us
    # which game variant (vanilla or a mod) we are building data for.
    if not args.output_dir.is_dir():
        parser.error(
            f"Output directory does not exist: {args.output_dir}"
        )

    for name, entry in TASKS.items():
        task = entry[1]
        # Optional third element: the file name this task writes inside the
        # output directory.
        output_filename = entry[2] if len(entry) > 2 else None
        print(f"=== {name} ===")
        forwarded: list[str] = []

        if args.game_dir is not None:
            forwarded += ["--game-dir", str(args.game_dir)]
        if args.check_save is not None:
            forwarded += ["--check-save", str(args.check_save)]
        if args.source is not None:
            forwarded += ["--source", str(args.source)]
        if output_filename is not None:
            forwarded += ["--output", str(args.output_dir / output_filename)]

        task(forwarded)


if __name__ == "__main__":
    main()
