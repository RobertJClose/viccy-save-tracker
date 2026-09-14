"""One-shot setup tasks (run manually, not part of tracking).

Today this only builds the invention ID -> name mapping; future
initialisation work registers in TASKS below.

Usage:
    python -m setup.initialise [--game-dir ...] [--output ...] [--check-save ...]
    python -m setup.initialise --list
"""

from __future__ import annotations

import argparse
from pathlib import Path

from setup.build_inventions_map import main as build_inventions_map_main

TASKS = {
    "inventions-map": (
        "Build inventions_map.json (ID -> name) from the game install.",
        build_inventions_map_main,
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
        "--output",
        type=Path,
        default=None,
        help="Forwarded to tasks (overrides the default output file).",
    )

    parser.add_argument(
        "--check-save",
        type=Path,
        default=None,
        help="Forwarded to tasks (save file to validate against).",
    )

    args = parser.parse_args(argv)

    if args.list:
        for name, (description, _) in TASKS.items():
            print(f"{name}: {description}")
        return

    forwarded: list[str] = []

    if args.game_dir is not None:
        forwarded += ["--game-dir", str(args.game_dir)]
    if args.output is not None:
        forwarded += ["--output", str(args.output)]
    if args.check_save is not None:
        forwarded += ["--check-save", str(args.check_save)]

    for name, (_, task) in TASKS.items():
        print(f"=== {name} ===")
        task(forwarded)


if __name__ == "__main__":
    main()
