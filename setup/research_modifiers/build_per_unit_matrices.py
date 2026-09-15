"""One-shot initialisation: build the per-unit modifier matrices.

For every technology, invention and westernisation reform level, record
the per-unit bonuses it grants (``infantry = { defence = 1 }``,
``cruiser = { torpedo_attack = 8 }``, ...). Output is 24 CSV files:
``<output-dir>/{tech,invention,westernisation}_modifiers/<group>/
per_unit_{land,naval}_modifiers.csv``. Rows are composite modifier
names (``infantry_defence``), columns are sources in declaration order,
cells hold that source's own value (``0.0`` for no effect).

Scopes split land from naval: air units count as land (they are
land-based in-game). Westernisation files are header-only — reform
levels grant no per-unit bonuses.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from core.config import GAME_DIR, VANILLA_DATA_DIR
from setup.research_modifiers.build_per_goods_matrices import (
    check_value_anchors,
    collect_invention_values,
    collect_reform_values,
    collect_technology_values,
    format_number,
    tech_names_only,
    validate_against_save,
)

LAND_SCOPES = (
    "infantry",
    "guard",
    "artillery",
    "engineer",
    "cavalry",
    "cuirassier",
    "dragoon",
    "hussar",
    "irregular",
    "tank",
    "plane",
)

NAVAL_SCOPES = (
    "battleship",
    "cruiser",
    "dreadnought",
    "ironclad",
    "commerce_raider",
    "clipper_transport",
    "steam_transport",
)

LAND_CATEGORY = ("per_unit_land", tuple(scope + "_" for scope in LAND_SCOPES))
NAVAL_CATEGORY = ("per_unit_naval", tuple(scope + "_" for scope in NAVAL_SCOPES))
CATEGORIES = (LAND_CATEGORY, NAVAL_CATEGORY)

LAND_FILENAME = "per_unit_land_modifiers.csv"
NAVAL_FILENAME = "per_unit_naval_modifiers.csv"


def render_matrix(
    columns: list[tuple[str, dict[str, float]]], prefixes: tuple[str, ...]
) -> str:
    """Render one per-unit CSV for the given columns."""
    rows = sorted(
        {
            name
            for _, values in columns
            for name in values
            if name.startswith(prefixes)
        }
    )
    lines = ["modifier," + ",".join(name for name, _ in columns)]

    for row in rows:
        lines.append(
            row
            + ","
            + ",".join(
                format_number(values.get(row, 0.0)) for _, values in columns
            )
        )

    return "\n".join(lines) + "\n"


# Anchor predictions for the vanilla files: (kind, group, source, row)
# must hold the predicted value. Checked only for source == "vanilla".
ANCHORS = (
    ("technology", "army", "iron_muzzle_loaded_artillery", "artillery_attack", 0.25),
    ("invention", "army", "post_napoleonic_army_doctrine", "infantry_defence", 1),
    ("invention", "navy", "torpedo_attacks", "cruiser_torpedo_attack", 8),
    ("invention", "navy", "defensive_attitude", "battleship_hull", 5),
)


def write_matrices(
    output_dir: Path,
    tech_groups: dict[str, list[tuple[str, dict[str, float]]]],
    invention_groups: dict[str, list[tuple[str, dict[str, float]]]],
    reform_groups: dict[str, list[tuple[str, dict[str, float]]]],
) -> list[Path]:
    """Write all 24 per-unit matrices; return the files written."""
    layouts = (
        ("tech_modifiers", tech_groups),
        ("invention_modifiers", invention_groups),
        ("westernisation_modifiers", reform_groups),
    )
    written: list[Path] = []

    for dirname, groups in layouts:
        for group, columns in groups.items():
            group_dir = output_dir / dirname / group
            group_dir.mkdir(parents=True, exist_ok=True)

            for filename, prefixes in (
                (LAND_FILENAME, LAND_CATEGORY[1]),
                (NAVAL_FILENAME, NAVAL_CATEGORY[1]),
            ):
                path = group_dir / filename
                path.write_text(
                    render_matrix(columns, prefixes), encoding="utf-8"
                )
                written.append(path)

    return written


def main(argv: list[str] | None = None) -> Path:
    parser = argparse.ArgumentParser(
        description="Build the per-unit modifier matrices.",
    )

    parser.add_argument(
        "--game-dir",
        type=Path,
        default=GAME_DIR,
        help="Victoria II installation directory (default: GAME_DIR in core/config.py).",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=VANILLA_DATA_DIR,
        help="Directory holding one game variant's reference data "
        "(default: data/vanilla/). Must already exist.",
    )

    parser.add_argument(
        "--check-save",
        type=Path,
        default=None,
        help="Save file to validate the matrices against (e.g. example.v2).",
    )

    parser.add_argument(
        "--source",
        default="vanilla",
        help="Label for anchor checks (anchors run only for vanilla).",
    )

    args = parser.parse_args(argv)

    if args.game_dir is None:
        parser.error("--game-dir is required (GAME_DIR in core/config.py is unset).")

    if not args.output_dir.is_dir():
        parser.error(
            f"Output directory does not exist: {args.output_dir}"
        )

    tech_groups = collect_technology_values(args.game_dir)
    print(f"Found {sum(len(c) for c in tech_groups.values())} technologies.")
    invention_groups = collect_invention_values(args.game_dir)
    print(f"Found {sum(len(c) for c in invention_groups.values())} inventions.")
    reform_groups = collect_reform_values(args.game_dir)
    print(f"Found {sum(len(c) for c in reform_groups.values())} reform levels.")

    if args.source == "vanilla":
        check_value_anchors(tech_groups, invention_groups, ANCHORS)

    if args.check_save is not None:
        save_text = args.check_save.read_text(encoding="utf-8", errors="replace")
        validate_against_save(
            tech_names_only(tech_groups),
            {
                level
                for columns in reform_groups.values()
                for level, _ in columns
            },
            save_text,
            args.check_save.name,
        )
        print(f"Save checks passed for {args.check_save.name}.")

    written = write_matrices(
        args.output_dir, tech_groups, invention_groups, reform_groups
    )
    print(f"Wrote {len(written)} per-unit matrices to {args.output_dir}")

    return args.output_dir


if __name__ == "__main__":
    main()
