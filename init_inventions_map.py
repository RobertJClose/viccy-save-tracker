"""One-shot initialisation: build the invention ID -> name mapping file.

Save files record inventions as numeric IDs
(``active_inventions={ 332 1 20 ... }``); the names live in the game
installation's ``inventions/*.txt`` files. IDs are 1-based positions in
declaration order across those files in sorted filename order (army,
commerce, culture, industry, navy in vanilla).

Run once via ``initialise.py``; the resulting ``inventions_map.json``
is committed as the vanilla default. A modded install just means
re-running with a different ``--game-dir``/``--output``.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from common import GAME_DIR, INVENTIONS_MAP_FILE

INVENTIONS_SUBDIR = "inventions"

# Invention names are word characters plus extras seen in vanilla:
# genetics:_heredity, populism_vs._establishment, 15_inch_main_armament.
NAME_PATTERN = re.compile(r"([A-Za-z0-9_:.]+)\s*=\s*\{")
TOKEN_PATTERN = re.compile(r'"|[{}]|([A-Za-z0-9_:.]+)\s*=\s*\{')


def strip_comments(text: str) -> str:
    """Remove ``#``-to-end-of-line comments, respecting double quotes."""
    stripped = []

    for line in text.splitlines():
        in_quotes = False

        for i, char in enumerate(line):
            if char == '"':
                in_quotes = not in_quotes
            elif char == "#" and not in_quotes:
                line = line[:i]
                break

        stripped.append(line)

    return "\n".join(stripped)


def extract_invention_names(text: str) -> list[str]:
    """
    Return top-level ``name = {`` block names in file order.

    Brace depth skips nested blocks (``limit``/``chance``/``effect``)
    and nested ``invention = <name>`` cross-references, so only real
    invention definitions are collected.
    """
    names: list[str] = []
    depth = 0
    in_quotes = False

    for match in TOKEN_PATTERN.finditer(strip_comments(text)):
        token = match.group(0)

        if token == '"':
            in_quotes = not in_quotes
        elif in_quotes:
            continue
        elif token == "{":
            depth += 1
        elif token == "}":
            depth -= 1
        elif depth == 0:
            names.append(match.group(1))
            depth += 1
        else:
            depth += 1

    return names


def build_invention_list(game_dir: Path) -> tuple[list[str], list[str]]:
    """
    Return (names, filenames) from ``game_dir/inventions/*.txt``.

    Files are read in sorted filename order; names are concatenated in
    file order, so a name's 1-based position is its save-file ID.
    """
    inventions_dir = game_dir / INVENTIONS_SUBDIR

    if not inventions_dir.is_dir():
        raise FileNotFoundError(
            f"No inventions directory at {inventions_dir}. "
            "Pass --game-dir pointing at your Victoria II installation "
            "or set GAME_DIR in common.py."
        )

    files = sorted(
        p for p in inventions_dir.iterdir()
        if p.is_file() and p.suffix == ".txt"
    )

    if not files:
        raise FileNotFoundError(f"No .txt files in {inventions_dir}.")

    names: list[str] = []

    for path in files:
        names.extend(
            extract_invention_names(
                path.read_text(encoding="utf-8", errors="replace")
            )
        )

    return names, [p.name for p in files]


def save_invention_ids(save_text: str) -> set[int]:
    """Collect every invention ID referenced by a save file."""
    ids: set[int] = set()

    for match in re.finditer(
        r"(?:active|illegal)_inventions=\s*\{([^}]*)\}", save_text
    ):
        ids.update(int(token) for token in match.group(1).split())

    return ids


# Anchor predictions for the vanilla files: ID 1 is the first block of
# the first file; IDs 37-39 are the three consecutive unit-activation
# inventions. Checked only for source == "vanilla".
ANCHORS = {
    1: "post_napoleonic_army_doctrine",
    37: "cuirassier_activation",
    38: "dragoon_activation",
    39: "hussar_activation",
}


def validate_against_save(
    names: list[str],
    save_text: str,
    save_name: str,
    check_anchors: bool,
) -> None:
    """
    Fail if any save-file ID falls outside the catalogue, or (vanilla
    only) if an anchor ID does not map to its predicted name.
    """
    unknown = sorted(i for i in save_invention_ids(save_text) if not 1 <= i <= len(names))

    if unknown:
        raise ValueError(
            f"{save_name} references IDs beyond {len(names)} inventions: "
            f"{unknown[:10]}..."
        )

    if check_anchors:
        for anchor_id, expected in ANCHORS.items():
            actual = names[anchor_id - 1]

            if actual != expected:
                raise ValueError(
                    f"Anchor ID {anchor_id}: expected {expected}, "
                    f"got {actual}. The file-order assumption is wrong; "
                    "not writing the map."
                )


def write_map(output: Path, names: list[str], files: list[str], source: str) -> None:
    """Write the mapping; index == save ID (index 0 unused)."""
    output.write_text(
        json.dumps(
            {
                "source": source,
                "files": files,
                "count": len(names),
                "inventions": [None, *names],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> Path:
    parser = argparse.ArgumentParser(
        description="Build the Victoria II invention ID -> name mapping file.",
    )

    parser.add_argument(
        "--game-dir",
        type=Path,
        default=GAME_DIR,
        help="Victoria II installation directory (default: GAME_DIR in common.py).",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=INVENTIONS_MAP_FILE,
        help="Where to write the mapping (default: inventions_map.json).",
    )

    parser.add_argument(
        "--check-save",
        type=Path,
        default=None,
        help="Save file to validate the map against (e.g. example.v2).",
    )

    parser.add_argument(
        "--source",
        default="vanilla",
        help="Label recorded in the map (use e.g. a mod name for modded installs).",
    )

    args = parser.parse_args(argv)

    if args.game_dir is None:
        parser.error("--game-dir is required (GAME_DIR in common.py is unset).")

    names, files = build_invention_list(args.game_dir)
    print(f"Found {len(names)} inventions in {len(files)} files: {', '.join(files)}")

    if args.check_save is not None:
        save_text = args.check_save.read_text(encoding="utf-8", errors="replace")
        validate_against_save(
            names, save_text, args.check_save.name,
            check_anchors=args.source == "vanilla",
        )
        print(f"Save-ID and anchor checks passed for {args.check_save.name}.")

    write_map(args.output, names, files, source=args.source)
    print(f"Wrote {args.output}")

    return args.output


if __name__ == "__main__":
    main()
