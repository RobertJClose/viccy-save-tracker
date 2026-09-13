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


# ---------------------------------------------------------------------------
# Processed-date tracking
# ---------------------------------------------------------------------------

def load_processed_dates(processed_file: Path) -> set[str]:
    """
    Load dates that have already been exported.

    This is the single source of truth for what has been tracked: every
    module (goods today; technologies, inventions and reforms in future)
    keys off the same in-game-date set.
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
