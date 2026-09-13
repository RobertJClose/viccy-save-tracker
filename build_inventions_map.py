"""One-shot initialisation: build the invention ID -> name mapping file.

Skeleton for a future objective. Save files record inventions as numeric
IDs (``active_inventions={ 332 1 20 ... }``); the names live in the game
installation's ``inventions/*.txt`` files, where each ID is the
invention's load-order index (latest vanilla game, no mods).

Running this script will write e.g. ``inventions_map.json`` mapping each
numeric ID to its invention name.
"""

from __future__ import annotations

import argparse
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT = REPO_DIR / "inventions_map.json"


def build_map(game_dir: Path) -> dict[int, str]:
    """Build the invention ID -> name mapping from the game install.

    Raises:
        NotImplementedError: Mapping generation is not implemented yet.
    """
    raise NotImplementedError("Invention-map generation is not implemented yet.")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Build the Victoria II invention ID -> name mapping file.",
    )

    parser.add_argument(
        "--game-dir",
        type=Path,
        required=True,
        help="Victoria II installation directory holding inventions/*.txt.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Where to write the mapping (default: {DEFAULT_OUTPUT.name}).",
    )

    parser.parse_args(argv)

    raise NotImplementedError("Invention-map generation is not implemented yet.")


if __name__ == "__main__":
    main()
