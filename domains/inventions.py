"""Player-country invention tracking.

Inventions are discrete like technologies: an invention is either
active or not, and the set rarely changes. Instead of snapshotting the
full set every date, ``invention_changes.csv`` records the full set
once (the first date ever tracked) and only differences afterwards.
Replaying the file in date order reconstructs the state at any time.

In the save, inventions are numeric IDs inside the player country's
``active_inventions={ ... }`` block (e.g. ``active_inventions={ 1 20
... }``); human-readable names come from the ID -> name mapping file
produced by ``setup/build_inventions_map.py`` (index == ID). A missing
``active_inventions`` block is valid and yields an empty set (e.g. an
uncivilised nation at game start with nothing invented yet).
``illegal_inventions={ ... }`` is a different block and is ignored.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

from core.config import VANILLA_DATA_DIR
from core.parsing import extract_braced_content
from setup.build_inventions_map import OUTPUT_FILENAME as MAP_FILENAME

CHANGES_FILENAME = "invention_changes.csv"
HEADER = ["date", "invention", "old_value", "new_value"]
ABSENT = "0"
PRESENT = "1"


def extract_invention_ids(country_block: str) -> set[int]:
    """Return the active invention IDs in a country block.

    A missing ``active_inventions`` block yields an empty set.
    ``illegal_inventions`` is never collected.
    """
    match = re.search(r"(?<![\w])active_inventions\s*=\s*\{", country_block)

    if not match:
        return set()

    inner = extract_braced_content(
        country_block, match.end() - 1, "active_inventions block"
    )

    ids: set[int] = set()
    for token in inner.split():
        try:
            ids.add(int(token))
        except ValueError:
            raise ValueError(
                f"Bad invention ID {token!r} in active_inventions block."
            ) from None

    return ids


def load_invention_map(map_path: Path | None = None) -> list:
    """Return the ID -> name list where index == save-file ID.

    Index 0 is unused (``None``); IDs are 1-based. Defaults to the
    committed vanilla map.
    """
    path = map_path if map_path is not None else VANILLA_DATA_DIR / MAP_FILENAME

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise FileNotFoundError(
            f"No invention map at {path}. Run "
            "`python -m setup.initialise` first."
        ) from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invention map at {path} is invalid.") from exc

    inventions = data.get("inventions")

    if not isinstance(inventions, list) or not inventions:
        raise ValueError(f"Invention map at {path} is invalid.")

    return inventions


def resolve_invention_names(ids: set[int], inventions: list) -> set[str]:
    """Map save-file IDs to human-readable invention names.

    Raises:
        ValueError: If any ID falls outside the map.
    """
    names: set[str] = set()
    unknown: list[int] = []

    for invention_id in ids:
        if 1 <= invention_id < len(inventions) and inventions[invention_id]:
            names.add(inventions[invention_id])
        else:
            unknown.append(invention_id)

    if unknown:
        raise ValueError(
            f"Unknown invention IDs beyond {len(inventions) - 1} "
            f"inventions: {sorted(unknown)[:10]}..."
        )

    return names


def extract_inventions(country_block: str, inventions: list) -> set[str]:
    """Return the active invention names in a country block."""
    return resolve_invention_names(
        extract_invention_ids(country_block), inventions
    )


def load_invention_state(changes_file: Path) -> set[str]:
    """
    Rebuild the last-known invention set by replaying the changes file.

    A missing file means no date has been invention-tracked yet (empty
    set). A corrupt file warns on stderr and yields an empty set,
    mirroring load_processed_dates.
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
            "Starting with an empty invention state.",
            file=sys.stderr,
        )
        return set()


def append_invention_changes(
    changes_file: Path,
    game_date: str,
    previous: set[str],
    current: set[str],
) -> tuple[set[str], set[str]]:
    """
    Record invention changes for one in-game date.

    The first date ever tracked (no changes file yet) writes the full
    snapshot: one ``0 -> 1`` row per active invention, or just the
    header when nothing is active. Later dates append one row per
    newly activated (``0 -> 1``) or deactivated (``1 -> 0``) invention,
    sorted by name; dates with no changes append nothing.

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
