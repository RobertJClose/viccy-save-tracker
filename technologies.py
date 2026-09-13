"""Player-country technology extraction.

Stub for a future objective: extract the set of unlocked technologies
from the player country's ``technology={ ... }`` block.

In the save, ``name={1 0.000}`` means "unlocked"; the numeric value
carries no meaning, so the result will be a plain set of names.
"""

from __future__ import annotations


def extract_technologies(country_block: str) -> set[str]:
    """Return the names of technologies unlocked in a country block.

    Raises:
        NotImplementedError: Technology tracking is not implemented yet.
    """
    raise NotImplementedError("Technology tracking is not implemented yet.")
