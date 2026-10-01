"""Westernisation tracking.

Westernisation is discrete like technology: each of the
military/economic reforms available to an uncivilised nation sits at
some level (e.g. ``land_reform=no_land_reform``) and rarely changes.
Instead of snapshotting all levels every date,
``westernisation_changes.csv`` records the full set once (the first
date ever tracked) and only differences afterwards. Replaying the file
in date order reconstructs the levels at any time.

Levels are recorded as numbers, matching the technology ``0``/``1``
shape: ``0`` means no reform, missing key, or a civilised
(deactivated) nation; ``1`` means the first enacted step (usually
``yes_*``); ``2`` means the second enacted step (today only
``finance_reform_two``). Only enacted reforms (``1``/``2``) are kept in
the state — zeros are implied by absence, so a fresh uncivilised
nation still at ``no_*`` and a fresh civilised nation both start as an
empty state with a header-only file.

Only the keys in ``WESTERNISATION_KEYS`` are tracked, read from the
player country's block. A newly westernised nation keeps stale reform
lines in its block, but the game deactivates their effects once
``civilized=yes`` — so a civilised block always yields an empty dict,
even when stale keys are still present.

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
ABSENT = "0"
LEVEL_1 = "1"
LEVEL_2 = "2"


def level_value(raw: str) -> str:
    """Map a raw save-file reform level to ``0``/``1``/``2``.

    ``no_*`` means no reform (``0``); a ``*_two`` suffix means the
    second enacted step (``2``, today only ``finance_reform_two``);
    anything else enacted (usually ``yes_*``) means ``1``.
    """
    if raw.startswith("no_"):
        return ABSENT
    if raw.endswith("_two"):
        return LEVEL_2
    return LEVEL_1


def extract_raw_westernisation(country_block: str) -> dict[str, str]:
    """Return the raw reform levels present in a country block.

    This is the pre-numeric helper kept for one-shot setup validation
    (``setup`` compares raw ``no_*``/``yes_*`` names against
    ``common/issues.txt``). Tracking itself uses
    :func:`extract_westernisation`, which maps through
    :func:`level_value` and omits zeros.
    """
    civilized = re.search(
        r"(?m)^[ \t]*civilized[ \t]*=[ \t]*(\w+)",
        country_block,
    )

    if civilized is not None and civilized.group(1) == "yes":
        return {}

    westernisation: dict[str, str] = {}

    for key in WESTERNISATION_KEYS:
        match = re.search(
            r"(?m)^[ \t]*" + re.escape(key) + r"[ \t]*=[ \t]*(\w+)",
            country_block,
        )

        if match:
            westernisation[key] = match.group(1)

    return westernisation


def extract_westernisation(country_block: str) -> dict[str, str]:
    """
    Return the enacted westernisation levels in a country block.

    Each key is matched on its own line (``key=value`` with unquoted
    values such as ``no_land_reform``); the ``=`` anchor keeps
    longer key names from colliding. Raw levels are mapped through
    :func:`level_value`, and zeros are omitted — so a nation still at
    ``no_*``, a civilised nation, and a block missing keys alike yield
    no entry for that reform. A first save with enacted reforms (``1``
    or ``2``) is therefore preserved as a ``0 -> 1``/``0 -> 2``
    snapshot, never silently dropped.

    A newly westernised nation keeps its reform lines in the save, but
    their effects are deactivated once ``civilized=yes``. Such stale
    keys are therefore ignored: any civilised block yields an empty
    dict. A block without a ``civilized=`` line falls back to the key
    scan.
    """
    return {
        key: value
        for key, raw in extract_raw_westernisation(country_block).items()
        for value in (level_value(raw),)
        if value != ABSENT
    }


def load_westernisation_state(changes_file: Path) -> dict[str, str]:
    """
    Rebuild the last-known westernisation levels by replaying the changes file.

    A missing file means no date has been westernisation-tracked yet
    (empty state). A corrupt file warns on stderr and yields an empty
    state, mirroring load_processed_dates. Files written before the
    numeric ``0``/``1``/``2`` scheme (raw level names, empty-string
    absence) are treated as corrupt: start a fresh history rather than
    mixing schemes.
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
            elif new_value in (LEVEL_1, LEVEL_2):
                state[name] = new_value
            else:
                raise ValueError("bad value")

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
    snapshot: one ``0 -> 1``/``0 -> 2`` row per enacted westernisation,
    or just the header when none is enacted (e.g. a nation still at
    ``no_*`` or a civilised player). A first save that already has
    reforms active is therefore preserved, never dropped. Later dates
    append one row per changed level — ``0 -> 1``, ``1 -> 2``,
    ``1 -> 0``, ``2 -> 0`` and so on — sorted by westernisation name;
    dates with no changes append nothing.

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
