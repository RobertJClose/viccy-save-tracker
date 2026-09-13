"""Player-country invention extraction.

Stub for a future objective: extract the set of active invention IDs
from the player country's ``active_inventions={ ... }`` block.

Save files record inventions as numeric IDs only; human-readable names
come from the ID -> name mapping file produced by
``build_inventions_map.py`` (latest vanilla game).
"""

from __future__ import annotations


def extract_invention_ids(country_block: str) -> set[int]:
    """Return the active invention IDs in a country block.

    Raises:
        NotImplementedError: Invention tracking is not implemented yet.
    """
    raise NotImplementedError("Invention tracking is not implemented yet.")
