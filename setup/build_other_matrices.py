"""One-shot initialisation: build the other-modifier matrices.

One ``other_modifiers.csv`` per group directory (alongside the
per-goods matrices): rows are the leftover names that fit no agreed
category (today just ``unit``, a cosmetic map-sprite flag kept
verbatim). Columns are sources in declaration order, cells hold that
source's own value (``0.0`` for no effect).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from core.config import GAME_DIR, VANILLA_DATA_DIR
from setup.build_per_goods_matrices import (
    check_rows_covered,
    check_value_anchors,
    collect_invention_values,
    collect_reform_values,
    collect_technology_values,
    tech_names_only,
    validate_against_save,
    write_category_tree,
)

FILENAME = "other_modifiers.csv"

ROWS = (
    "unit",
)

# Anchor predictions for the vanilla files: (kind, group, source, row)
# must hold the predicted value. Checked only for source == "vanilla".
ANCHORS = (
    ("technology", "army", "bolt_action_rifles", "unit", 1),
)


def main(argv: list[str] | None = None) -> Path:
    parser = argparse.ArgumentParser(
        description="Build the other-modifier matrices.",
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
        check_rows_covered(ROWS, tech_groups, invention_groups, reform_groups)

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

    written = write_category_tree(
        args.output_dir,
        FILENAME,
        ROWS,
        tech_groups,
        invention_groups,
        reform_groups,
    )
    print(f"Wrote {len(written)} other matrices to {args.output_dir}")

    return args.output_dir


if __name__ == "__main__":
    main()
