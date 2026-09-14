"""Westernisation tracking.

Westernisation is discrete like technology: each of the
military/economic reforms available to an uncivilised nation sits at
some level (e.g. ``land_reform=no_land_reform``) and rarely changes.
Instead of snapshotting all levels every date,
``westernisation_changes.csv`` records the full set once (the first
date ever tracked) and only differences afterwards. Replaying the file
in date order reconstructs the levels at any time.

Only the keys in ``WESTERNISATION_KEYS`` are tracked, read from the
player country's block. Keys absent from the block (e.g. every key for
a civilised nation) are simply not recorded.

Civilised social/political reforms and government tracking are a
separate future category and are deliberately out of scope here.
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

WESTERNISATION_KEYS = (
    "land_reform",
    "admin_reform",
    "finance_reform",
    "education_reform",
    "transport_improv",
    "pre_indust",
    "industrial_construction",
    "foreign_training",
    "foreign_weapons",
    "military_constructions",
    "foreign_officers",
    "army_schools",
    "foreign_naval_officers",
    "naval_schools",
    "foreign_navies",
)

CHANGES_FILENAME = "westernisation_changes.csv"
HEADER = ["date", "westernisation", "old_value", "new_value"]
ABSENT = ""


def extract_westernisation(country_block: str) -> dict[str, str]:
    """
    Return the westernisation levels present in a country block.

    Each key is matched on its own line (``key=value`` with unquoted
    values such as ``no_land_reform``); the ``=`` anchor keeps
    longer key names from colliding. Keys missing from the block are
    skipped, so a civilised nation yields an empty dict. Values are
    recorded raw — progression ladders are discovered from the save,
    never hardcoded.
    """
    westernisation: dict[str, str] = {}

    for key in WESTERNISATION_KEYS:
        match = re.search(
            r"(?m)^[ \t]*" + re.escape(key) + r"[ \t]*=[ \t]*(\w+)",
            country_block,
        )

        if match:
            westernisation[key] = match.group(1)

    return westernisation


def load_westernisation_state(changes_file: Path) -> dict[str, str]:
    """
    Rebuild the last-known westernisation levels by replaying the changes file.

    A missing file means no date has been westernisation-tracked yet
    (empty state). A corrupt file warns on stderr and yields an empty
    state, mirroring load_processed_dates.
    """
    if not changes_file.exists():
        return {}

    try:
        with changes_file.open("r", encoding="utf-8", newline="") as f:
            rows = list(csv.reader(f))

        if not rows or rows[0] != HEADER:
            raise ValueError("bad header")

        state: dict[str, str] = {}

        for row in rows[1:]:
            if len(row) != len(HEADER):
                raise ValueError("bad row")

            _, name, _, new_value = row

            if new_value == ABSENT:
                state.pop(name, None)
            else:
                state[name] = new_value

        return state

    except (OSError, ValueError, csv.Error):
        print(
            f"Warning: {changes_file} is invalid. "
            "Starting with an empty westernisation state.",
            file=sys.stderr,
        )
        return {}


def append_westernisation_changes(
    changes_file: Path,
    game_date: str,
    previous: dict[str, str],
    current: dict[str, str],
) -> dict[str, tuple[str, str]]:
    """
    Record westernisation changes for one in-game date.

    The first date ever tracked (no changes file yet) writes the full
    snapshot: one ``"" -> level`` row per present westernisation, or just
    the header when none is present (e.g. a civilised player). Later dates
    append one row per changed westernisation — new level, newly appeared
    key (``"" -> level``) or disappeared key (``level -> ""``) — sorted by
    westernisation name; dates with no changes append nothing.

    Returns:
        {westernisation: (old_value, new_value)} for every change.
    """
    changed: dict[str, tuple[str, str]] = {}

    for name in previous.keys() | current.keys():
        old_value = previous.get(name, ABSENT)
        new_value = current.get(name, ABSENT)

        if old_value != new_value:
            changed[name] = (old_value, new_value)

    file_exists = changes_file.exists()

    if not file_exists:
        # No history yet: the snapshot is the full current state,
        # reported as baseline ("absent" -> level) rows.
        changed = {name: (ABSENT, current[name]) for name in current}

    with changes_file.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow(HEADER)

        for name in sorted(changed):
            old_value, new_value = changed[name]
            writer.writerow([game_date, name, old_value, new_value])

    return changed
