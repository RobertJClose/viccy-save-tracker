"""Uncivilised-reform extraction.

Stub for a future objective: extract the military/economic reforms of an
uncivilised nation (e.g. ``land_reform``, ``army_schools``) from the
player country's block.

Civilised social/political reforms and government tracking are a
separate future category and are deliberately out of scope here.
"""

from __future__ import annotations

UNCIV_REFORM_KEYS = (
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


def extract_unciv_reforms(country_block: str) -> dict[str, str]:
    """Return the uncivilised-reform levels in a country block.

    Raises:
        NotImplementedError: Reform tracking is not implemented yet.
    """
    raise NotImplementedError("Uncivilised-reform tracking is not implemented yet.")
