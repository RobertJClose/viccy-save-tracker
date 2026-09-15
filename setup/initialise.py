"""One-shot setup tasks (run manually, not part of tracking).

Today this builds the invention ID -> name mapping, the exhaustive
research-modifier list, and the per-category modifier matrices; future
initialisation work registers in TASKS below.

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
from setup.research_modifiers.build_modifiers_from_research_list import (
    OUTPUT_FILENAME as MODIFIERS_OUTPUT_FILENAME,
)
from setup.research_modifiers.build_modifiers_from_research_list import (
    main as build_modifiers_from_research_main,
)
from setup.research_modifiers.build_per_goods_matrices import (
    main as build_per_goods_matrices_main,
)
from setup.research_modifiers.build_colonial_matrices import (
    main as build_colonial_matrices_main,
)
from setup.research_modifiers.build_prestige_matrices import (
    main as build_prestige_matrices_main,
)
from setup.research_modifiers.build_population_matrices import (
    main as build_population_matrices_main,
)
from setup.research_modifiers.build_diplomacy_matrices import (
    main as build_diplomacy_matrices_main,
)
from setup.research_modifiers.build_other_matrices import (
    main as build_other_matrices_main,
)
from setup.research_modifiers.build_research_matrices import (
    main as build_research_matrices_main,
)
from setup.research_modifiers.build_economic_matrices import (
    main as build_economic_matrices_main,
)
from setup.research_modifiers.build_per_unit_matrices import (
    main as build_per_unit_matrices_main,
)
from setup.research_modifiers.build_military_matrices import (
    main as build_military_matrices_main,
)

TASKS = {
    "inventions-map": (
        "Build inventions_map.json (ID -> name) from the game install.",
        build_inventions_map_main,
        INVENTIONS_OUTPUT_FILENAME,
    ),
    "modifiers-from-research-list": (
        "Build modifiers_from_research_list.txt (exhaustive research "
        "modifier names) from the game install.",
        build_modifiers_from_research_main,
        MODIFIERS_OUTPUT_FILENAME,
    ),
    "per-goods-matrices": (
        "Build the 24 per-goods modifier matrices from the game install.",
        build_per_goods_matrices_main,
        None,
    ),
    "colonial-matrices": (
        "Build the colonial modifier matrices from the game install.",
        build_colonial_matrices_main,
        None,
    ),
    "prestige-matrices": (
        "Build the prestige modifier matrices from the game install.",
        build_prestige_matrices_main,
        None,
    ),
    "population-matrices": (
        "Build the population modifier matrices from the game install.",
        build_population_matrices_main,
        None,
    ),
    "diplomacy-matrices": (
        "Build the diplomacy modifier matrices from the game install.",
        build_diplomacy_matrices_main,
        None,
    ),
    "other-matrices": (
        "Build the other-modifier matrices from the game install.",
        build_other_matrices_main,
        None,
    ),
    "research-matrices": (
        "Build the research modifier matrices from the game install.",
        build_research_matrices_main,
        None,
    ),
    "economic-matrices": (
        "Build the economic modifier matrices from the game install.",
        build_economic_matrices_main,
        None,
    ),
    "per-unit-matrices": (
        "Build the 24 per-unit modifier matrices from the game install.",
        build_per_unit_matrices_main,
        None,
    ),
    "military-matrices": (
        "Build the military modifier matrices from the game install.",
        build_military_matrices_main,
        None,
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
        # output directory (forwarded as --output), or None for tasks that
        # write a whole tree and take --output-dir instead.
        print(f"=== {name} ===")
        forwarded: list[str] = []

        if args.game_dir is not None:
            forwarded += ["--game-dir", str(args.game_dir)]
        if args.check_save is not None:
            forwarded += ["--check-save", str(args.check_save)]
        if args.source is not None:
            forwarded += ["--source", str(args.source)]
        if len(entry) > 2:
            if entry[2] is not None:
                forwarded += ["--output", str(args.output_dir / entry[2])]
            else:
                forwarded += ["--output-dir", str(args.output_dir)]

        task(forwarded)


if __name__ == "__main__":
    main()
