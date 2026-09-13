from __future__ import annotations

import json
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# This package lives in:
#
#   ...\Victoria II\save games\your-repo\main.py
#
# Therefore:
#
#   REPO_DIR = save games\your-repo
#   SAVE_DIR = save games
#
# The output directory (the CSV history and processed-dates ledger) is chosen
# by the user at runtime and must match the save game being tracked.
#
REPO_DIR = Path(__file__).resolve().parent
SAVE_DIR = REPO_DIR.parent

# User setting: edit this to point at your Victoria II installation.
# Used by initialise.py to locate game data (e.g. inventions/*.txt);
# --game-dir on the command line overrides it.
GAME_DIR = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Victoria 2")

# Default vanilla invention ID -> name mapping (committed to the repo).
INVENTIONS_MAP_FILE = REPO_DIR / "inventions_map.json"

OUTPUT_FILENAME = "goods_prices.csv"
PROCESSED_FILENAME = "processed_dates.json"

SAVE_FILES = [
    "autosave.v2",
    "oldautosave.v2",
    "olderautosave.v2",
]

# Watch mode tracks only the live autosave. The rotated files are
# deliberately ignored: after a new save game's first autosave, the game
# cascades the previous session's saves into oldautosave.v2 /
# olderautosave.v2, and recording those would pollute the current watch
# with a different save game's data. Consequence: an autosave missed while
# the watcher is down is not backfilled from the rotated files.
WATCH_FILES = [
    "autosave.v2",
]


# ---------------------------------------------------------------------------
# Save parsing
# ---------------------------------------------------------------------------

def read_save(path: Path) -> str:
    """
    Read a Victoria II save file as text.

    Victoria II saves are text-based. We use errors='replace' so that one
    unusual byte will not prevent the entire save from being read.
    """
    return path.read_text(encoding="utf-8", errors="replace")


def extract_game_date(text: str) -> str:
    """
    Extract the game's current date from the save header.

    Example:
        date="1836.4.1"

    Returns:
        1836-04-01
    """
    match = re.search(r'^date="(\d{4})\.(\d{1,2})\.(\d{1,2})"', text, re.MULTILINE)

    if not match:
        raise ValueError("Could not find the game date in the save.")

    year, month, day = map(int, match.groups())

    return f"{year:04d}-{month:02d}-{day:02d}"


def extract_player_tag(text: str) -> str:
    """
    Extract the player country's tag from the save header.

    Example:
        player="JAP"

    Returns:
        JAP
    """
    match = re.search(r'^player="(\w+)"', text, re.MULTILINE)

    if not match:
        raise ValueError("Could not find the player tag in the save.")

    return match.group(1)


def extract_braced_content(text: str, open_index: int, label: str) -> str:
    """
    Return the text inside the brace opened at open_index.

    Brace counting skips double-quoted strings so that a brace inside a
    quoted value cannot unbalance the scan.

    Raises:
        ValueError: If the braces never balance.
    """
    depth = 0
    in_quotes = False

    for i in range(open_index, len(text)):
        char = text[i]

        if char == '"':
            in_quotes = not in_quotes
        elif not in_quotes:
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[open_index + 1:i]

    raise ValueError(f"Unbalanced braces in {label}.")


def extract_country_block(text: str, tag: str) -> str:
    """
    Isolate a country's top-level block (e.g. ``JAP={ ... }``).

    The tag must start at column 0, so quoted values such as
    ``country="JAP"`` elsewhere in the file cannot match.

    Returns the text inside the country's outer braces.
    """
    match = re.search(
        r"^" + re.escape(tag) + r"=\s*\{",
        text,
        re.MULTILINE,
    )

    if not match:
        raise ValueError(f"Could not find country block for {tag}.")

    return extract_braced_content(text, match.end() - 1, f"country block for {tag}")


# ---------------------------------------------------------------------------
# Processed-date tracking
# ---------------------------------------------------------------------------

def load_processed_dates(processed_file: Path) -> set[str]:
    """
    Load dates that have already been exported.

    This is the single source of truth for what has been tracked: every
    module (goods, technologies and westernisation today; inventions in
    future) keys off the same in-game-date set.
    """
    if not processed_file.exists():
        return set()

    try:
        data = json.loads(processed_file.read_text(encoding="utf-8"))

        if not isinstance(data, list):
            raise ValueError

        return set(data)

    except (json.JSONDecodeError, ValueError):
        print(
            f"Warning: {processed_file} is invalid. "
            "Starting with no processed dates.",
            file=sys.stderr,
        )
        return set()


def save_processed_dates(processed_file: Path, dates: set[str]) -> None:
    """
    Save processed dates in a simple JSON file.
    """
    processed_file.write_text(
        json.dumps(sorted(dates), indent=2),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Output paths
# ---------------------------------------------------------------------------

def output_paths(output_dir: Path) -> tuple[Path, Path]:
    """
    Given an output directory, return (output_file, processed_file).
    """
    return (
        output_dir / OUTPUT_FILENAME,
        output_dir / PROCESSED_FILENAME,
    )
