from __future__ import annotations

import json
import sys
from pathlib import Path

from core.config import OUTPUT_FILENAME, PROCESSED_FILENAME


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
