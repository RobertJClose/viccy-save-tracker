"""Player-country technology tracking.

Technologies are discrete: a tech is either unlocked or not, and the
set rarely changes. Instead of snapshotting the full set every date,
``technology_changes.csv`` records the full state once (the first date
ever tracked) and only differences afterwards. Replaying the file in
date order reconstructs the state at any time.

In the save, ``name={1 0.000}`` inside the player country's
``technology={ ... }`` block means "unlocked"; the numeric value
carries no meaning, so the tracked state is a plain set of names.
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

from core.parsing import extract_braced_content

CHANGES_FILENAME = "technology_changes.csv"
HEADER = ["date", "technology", "old_value", "new_value"]
ABSENT = "0"
PRESENT = "1"


def extract_technologies(country_block: str) -> set[str]:
    """
    Return the names of technologies unlocked in a country block.

    An empty ``technology={}`` block is valid and yields an empty set
    (e.g. an uncivilised nation at game start).

    The ``research={ technology=... }`` entry records the technology
    currently being researched, not an unlocked one, and is ignored.
    """
    match = re.search(r"(?<![\w])technology\s*=\s*\{", country_block)

    if not match:
        raise ValueError("Could not find technology block.")

    inner = extract_braced_content(
        country_block, match.end() - 1, "technology block"
    )

    return set(re.findall(r"(\w+)=\{[^}]*\}", inner))


def load_technology_state(changes_file: Path) -> set[str]:
    """
    Rebuild the last-known technology set by replaying the changes file.

    A missing file means no date has been tech-tracked yet (empty set).
    A corrupt file warns on stderr and yields an empty set, mirroring
    load_processed_dates.
    """
    if not changes_file.exists():
        return set()

    try:
        with changes_file.open("r", encoding="utf-8", newline="") as f:
            rows = list(csv.reader(f))

        if not rows or rows[0] != HEADER:
            raise ValueError("bad header")

        state: set[str] = set()

        for row in rows[1:]:
            if len(row) != len(HEADER):
                raise ValueError("bad row")

            _, name, _, new_value = row

            if new_value == PRESENT:
                state.add(name)
            elif new_value == ABSENT:
                state.discard(name)
            else:
                raise ValueError("bad value")

        return state

    except (OSError, ValueError, csv.Error):
        print(
            f"Warning: {changes_file} is invalid. "
            "Starting with an empty technology state.",
            file=sys.stderr,
        )
        return set()


def append_technology_changes(
    changes_file: Path,
    game_date: str,
    previous: set[str],
    current: set[str],
) -> tuple[set[str], set[str]]:
    """
    Record technology changes for one in-game date.

    The first date ever tracked (no changes file yet) writes the full
    snapshot: one ``0 -> 1`` row per unlocked technology, or just the
    header when nothing is unlocked. Later dates append one row per
    newly acquired (``0 -> 1``) or lost (``1 -> 0``) technology, sorted
    by name; dates with no changes append nothing.

    Returns:
        (acquired, lost)
    """
    acquired = current - previous
    lost = previous - current

    file_exists = changes_file.exists()

    with changes_file.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow(HEADER)
            for name in sorted(current):
                writer.writerow([game_date, name, ABSENT, PRESENT])
        else:
            for name in sorted(acquired):
                writer.writerow([game_date, name, ABSENT, PRESENT])
            for name in sorted(lost):
                writer.writerow([game_date, name, PRESENT, ABSENT])

    return acquired, lost
