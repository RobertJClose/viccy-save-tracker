from __future__ import annotations

import re
from pathlib import Path


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
