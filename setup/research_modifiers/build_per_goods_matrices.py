"""One-shot initialisation: build the per-goods modifier matrices.

For every technology, invention and westernisation reform level, record
the per-good bonuses it grants (``rgo_goods_output = { iron = 0.25 }``,
``factory_goods_output = { fabric = 0.05 }``, ...). Output is 24 CSV
files: ``<output-dir>/{tech,invention,westernisation}_modifiers/<group>/
{rgo_goods,factory_goods}_modifiers.csv``. Rows are composite modifier
names (``rgo_goods_output_iron``), columns are sources, cells are plain
numbers with ``0.0`` for no effect.

Scope rules mirror the exhaustive list (see
``setup/research_modifiers/build_modifiers_from_research_list.py``): technologies minus
``area``/``year``/``cost``/``ai_chance``, inventions' ``effect`` only,
reform levels minus ``on_execute``/``trigger``. Only the four per-good
block families are collected here; every other modifier is out of scope
for now. A composite appearing twice within one source fails loudly.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from core.config import GAME_DIR, VANILLA_DATA_DIR
from core.parsing import extract_braced_content, extract_country_block, extract_player_tag
from domains.technologies import extract_technologies
from domains.westernisation import WESTERNISATION_KEYS, extract_westernisation
from setup.build_inventions_map import strip_comments
from setup.research_modifiers.build_modifiers_from_research_list import (
    INVENTIONS_SUBDIR,
    ISSUES_PATH,
    REFORM_GROUPS,
    REFORM_SKIP_BLOCKS,
    TECH_SKIP_BLOCKS,
    TECH_SKIP_SCALARS,
    TECHNOLOGIES_SUBDIR,
    iter_top_level_blocks,
    remove_named_blocks,
)

# (directory prefix, file stem, row-name prefixes).
RGO_CATEGORY = ("rgo_goods", ("rgo_goods_output_", "rgo_size_"))
FACTORY_CATEGORY = ("factory_goods", ("factory_goods_output_", "factory_goods_throughput_"))
CATEGORIES = (RGO_CATEGORY, FACTORY_CATEGORY)

RGO_FILENAME = "rgo_goods_modifiers.csv"
FACTORY_FILENAME = "factory_goods_modifiers.csv"

KEY_RE = re.compile(r"([A-Za-z0-9_:.]+)\s*=")
NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")
TOKEN_RE = re.compile(r'"[^"]*"|\S+')


def _record(store: dict[str, float], name: str, value: float, where: str) -> None:
    """Store one value, failing loudly on a within-source duplicate."""
    if name in store:
        raise ValueError(f"Duplicate modifier {name} in {where}.")
    store[name] = value


def collect_modifier_values(text: str, where: str) -> dict[str, float]:
    """Collect {composite name: value} from one effect-context body.

    Same traversal rules as the exhaustive list's ``collect_modifiers``,
    but keeps the numbers. Depth-0 ``key = number`` entries are recorded
    as-is; deeper entries are prefixed with their enclosing block path.
    """
    values: dict[str, float] = {}
    stack: list[str | None] = []
    rebel_faction: str | None = None
    rebel_value: float | None = None
    i = 0
    n = len(text)
    in_quotes = False

    def path() -> list[str]:
        return [entry for entry in stack if entry]

    while i < n:
        char = text[i]

        if char == '"':
            in_quotes = not in_quotes
            i += 1
            continue

        if in_quotes:
            i += 1
            continue

        if char == "{":
            stack.append(None)
            i += 1
            continue

        if char == "}":
            if stack and stack[-1] == "rebel_org_gain":
                if rebel_faction is None or rebel_value is None:
                    raise ValueError(
                        f"Unexpected rebel_org_gain shape in {where}."
                    )
                _record(
                    values,
                    f"rebel_org_gain_{rebel_faction}",
                    rebel_value,
                    where,
                )
                rebel_faction = None
                rebel_value = None
            if stack:
                stack.pop()
            i += 1
            continue

        key_match = KEY_RE.match(text, i)

        if not key_match:
            i += 1
            continue

        key = key_match.group(1)
        j = key_match.end()

        while j < n and text[j] in " \t\r\n":
            j += 1

        if j < n and text[j] == "{":
            stack.append(key)
            if key == "rebel_org_gain":
                rebel_faction = None
                rebel_value = None
            i = j + 1
            continue

        token_match = TOKEN_RE.match(text[j:])

        if token_match:
            token = token_match.group(0)
            is_number = not token.startswith('"') and NUMBER_RE.fullmatch(token)

            if is_number:
                number = float(token)
                if stack and stack[-1] == "rebel_org_gain":
                    if key == "value":
                        rebel_value = number
                elif path():
                    _record(values, "_".join([*path(), key]), number, where)
                elif key not in TECH_SKIP_SCALARS:
                    _record(values, key, number, where)
            elif "rebel_org_gain" in stack and key == "faction":
                rebel_faction = token

            i = j + token_match.end()
            continue

        i = j if j > i else i + 1

    if "rebel_org_gain" in stack:
        raise ValueError(f"Unbalanced rebel_org_gain block in {where}.")

    return values


def read_game_text(path: Path) -> str:
    """Read a game data file with comments stripped."""
    return strip_comments(path.read_text(encoding="utf-8", errors="replace"))


def group_name(filename: str, suffix: str) -> str:
    """Map a game data file to its matrix group (e.g. army_tech.txt -> army)."""
    stem = Path(filename).stem
    return stem[: -len(suffix)] if stem.endswith(suffix) else stem


def collect_technology_values(
    game_dir: Path,
) -> dict[str, list[tuple[str, dict[str, float]]]]:
    """Return {group: [(tech, values)]} in declaration order."""
    tech_dir = game_dir / TECHNOLOGIES_SUBDIR

    if not tech_dir.is_dir():
        raise FileNotFoundError(
            f"No technologies directory at {tech_dir}. "
            "Pass --game-dir pointing at your Victoria II installation "
            "or set GAME_DIR in core/config.py."
        )

    groups: dict[str, list[tuple[str, dict[str, float]]]] = {}

    for path in sorted(
        p for p in tech_dir.iterdir() if p.is_file() and p.suffix == ".txt"
    ):
        group = group_name(path.name, "_tech")
        columns = groups.setdefault(group, [])

        for name, inner in iter_top_level_blocks(read_game_text(path)):
            columns.append(
                (
                    name,
                    collect_modifier_values(
                        remove_named_blocks(inner, TECH_SKIP_BLOCKS),
                        f"technology {name}",
                    ),
                )
            )

    return groups


def collect_invention_values(
    game_dir: Path,
) -> dict[str, list[tuple[str, dict[str, float]]]]:
    """Return {group: [(invention, values)]} in declaration order.

    Only ``effect = { ... }`` blocks are scanned.
    """
    inventions_dir = game_dir / INVENTIONS_SUBDIR

    if not inventions_dir.is_dir():
        raise FileNotFoundError(
            f"No inventions directory at {inventions_dir}. "
            "Pass --game-dir pointing at your Victoria II installation "
            "or set GAME_DIR in core/config.py."
        )

    groups: dict[str, list[tuple[str, dict[str, float]]]] = {}

    for path in sorted(
        p for p in inventions_dir.iterdir() if p.is_file() and p.suffix == ".txt"
    ):
        group = group_name(path.name, "_inventions")
        columns = groups.setdefault(group, [])

        for name, inner in iter_top_level_blocks(read_game_text(path)):
            values: dict[str, float] = {}
            where = f"invention {name}"

            for match in re.finditer(r"effect\s*=\s*\{", inner):
                effect = extract_braced_content(inner, match.end() - 1, "effect")

                for composite, value in collect_modifier_values(
                    effect, where
                ).items():
                    _record(values, composite, value, where)

            columns.append((name, values))

    return groups


def collect_reform_values(
    game_dir: Path,
) -> dict[str, list[tuple[str, dict[str, float]]]]:
    """Return {group: [(level, values)]} in issues.txt order.

    Groups are ``economic`` and ``military`` (the ``_reforms`` suffix of
    the issues.txt group names).
    """
    issues = game_dir / ISSUES_PATH

    if not issues.is_file():
        raise FileNotFoundError(
            f"No issues file at {issues}. "
            "Pass --game-dir pointing at your Victoria II installation "
            "or set GAME_DIR in core/config.py."
        )

    text = read_game_text(issues)
    groups: dict[str, list[tuple[str, dict[str, float]]]] = {}

    for group_block in REFORM_GROUPS:
        match = re.search(re.escape(group_block) + r"\s*=\s*\{", text)

        if not match:
            raise ValueError(f"Could not find {group_block} in {issues}.")

        group = group_name(group_block, "_reforms")
        columns = groups.setdefault(group, [])

        for _, reform_inner in iter_top_level_blocks(
            extract_braced_content(text, match.end() - 1, group_block)
        ):
            for level, level_inner in iter_top_level_blocks(reform_inner):
                columns.append(
                    (
                        level,
                        collect_modifier_values(
                            remove_named_blocks(level_inner, REFORM_SKIP_BLOCKS),
                            f"reform level {level}",
                        ),
                    )
                )

    return groups


def format_number(value: float) -> str:
    """Format a cell value plainly (``0.25``, ``1``, ``-0.25``)."""
    return "%g" % value


def render_matrix(
    columns: list[tuple[str, dict[str, float]]], prefixes: tuple[str, ...]
) -> str:
    """Render one category CSV for the given columns."""
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
    ("technology", "industry", "mechanized_mining", "rgo_goods_output_iron", 0.25),
    ("technology", "industry", "clean_coal", "rgo_size_coal", 0.2),
    (
        "invention",
        "industry",
        "daimlers_automobile",
        "factory_goods_output_machine_parts",
        0.01,
    ),
    (
        "invention",
        "industry",
        "northrop_power_loom",
        "factory_goods_throughput_fabric",
        0.05,
    ),
)


def check_value_anchors(
    tech_groups: dict[str, list[tuple[str, dict[str, float]]]],
    invention_groups: dict[str, list[tuple[str, dict[str, float]]]],
    anchors: tuple[tuple[str, str, str, str, float], ...],
) -> None:
    """Fail if a vanilla anchor cell does not hold its predicted value.

    Each anchor is (kind, group, source, row, expected) with kind one of
    "technology"/"invention". Shared by the per-category matrix tasks.
    """
    lookups = {"technology": tech_groups, "invention": invention_groups}
    missing: list[str] = []

    for kind, group, source, row, expected in anchors:
        columns = dict(lookups[kind].get(group, []))
        actual = columns.get(source, {}).get(row)

        if actual != expected:
            missing.append(f"{source}/{row} (expected {expected}, got {actual})")

    if missing:
        raise ValueError(
            "Anchor cells do not hold their predicted values: "
            + "; ".join(missing)
            + ". The effect parser is wrong; not writing the matrices."
        )


def check_anchors(
    tech_groups: dict[str, list[tuple[str, dict[str, float]]]],
    invention_groups: dict[str, list[tuple[str, dict[str, float]]]],
) -> None:
    """Fail if a vanilla anchor cell does not hold its predicted value."""
    check_value_anchors(tech_groups, invention_groups, ANCHORS)


def check_rows_covered(
    rows: tuple[str, ...],
    tech_groups: dict[str, list[tuple[str, dict[str, float]]]],
    invention_groups: dict[str, list[tuple[str, dict[str, float]]]],
    reform_groups: dict[str, list[tuple[str, dict[str, float]]]],
) -> None:
    """Fail if a category row never occurs in any column (vanilla only).

    Catches typos in a task's row set: every agreed name must be granted
    by at least one source.
    """
    seen = {
        name
        for groups in (tech_groups, invention_groups, reform_groups)
        for columns in groups.values()
        for _, values in columns
        for name in values
    }
    missing = sorted(set(rows) - seen)

    if missing:
        raise ValueError(
            f"Category rows never granted by any source: {missing}. "
            "The row set is wrong; not writing the matrices."
        )


def render_exact_matrix(
    columns: list[tuple[str, dict[str, float]]], rows: tuple[str, ...]
) -> str:
    """Render one category CSV: fixed rows, ``0.0`` for no effect."""
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


def write_category_tree(
    output_dir: Path,
    filename: str,
    rows: tuple[str, ...],
    tech_groups: dict[str, list[tuple[str, dict[str, float]]]],
    invention_groups: dict[str, list[tuple[str, dict[str, float]]]],
    reform_groups: dict[str, list[tuple[str, dict[str, float]]]],
) -> list[Path]:
    """Write one category file per existing group dir; return files written.

    Files land alongside the per-goods matrices
    (``tech_modifiers/<type>/``, ``invention_modifiers/<type>/``,
    ``westernisation_modifiers/<group>/``), so group directories are
    shared, never duplicated.
    """
    written: list[Path] = []

    for dirname, groups in (
        ("tech_modifiers", tech_groups),
        ("invention_modifiers", invention_groups),
        ("westernisation_modifiers", reform_groups),
    ):
        for group, columns in groups.items():
            group_dir = output_dir / dirname / group
            group_dir.mkdir(parents=True, exist_ok=True)
            path = group_dir / filename
            path.write_text(render_exact_matrix(columns, rows), encoding="utf-8")
            written.append(path)

    return written


def tech_names_only(
    tech_groups: dict[str, list[tuple[str, dict[str, float]]]],
) -> set[str]:
    """Return every technology name found across all tech groups."""
    return {
        name for columns in tech_groups.values() for name, _ in columns
    }


def validate_against_save(
    tech_names: set[str],
    reform_levels: set[str],
    save_text: str,
    save_name: str,
) -> None:
    """Fail if the save's techs/reform levels are not matrix columns.

    (Invention IDs are validated by the inventions-map task, which owns
    the ID -> name mapping.)
    """
    player_tag = extract_player_tag(save_text)
    country_block = extract_country_block(save_text, player_tag)

    unknown_techs = sorted(extract_technologies(country_block) - tech_names)

    if unknown_techs:
        raise ValueError(
            f"{save_name} unlocks technologies outside the matrices: "
            f"{unknown_techs[:10]}..."
        )

    westernisation = extract_westernisation(country_block)
    unknown_levels = sorted(
        f"{key}={level}"
        for key, level in westernisation.items()
        if key in WESTERNISATION_KEYS and level not in reform_levels
    )

    if unknown_levels:
        raise ValueError(
            f"{save_name} uses westernisation levels outside the matrices: "
            f"{unknown_levels[:10]}..."
        )


def write_matrices(
    output_dir: Path,
    tech_groups: dict[str, list[tuple[str, dict[str, float]]]],
    invention_groups: dict[str, list[tuple[str, dict[str, float]]]],
    reform_groups: dict[str, list[tuple[str, dict[str, float]]]],
) -> list[Path]:
    """Write all 24 per-goods matrices; return the files written."""
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
                (RGO_FILENAME, RGO_CATEGORY[1]),
                (FACTORY_FILENAME, FACTORY_CATEGORY[1]),
            ):
                path = group_dir / filename
                path.write_text(
                    render_matrix(columns, prefixes), encoding="utf-8"
                )
                written.append(path)

    return written


def main(argv: list[str] | None = None) -> Path:
    parser = argparse.ArgumentParser(
        description="Build the per-goods modifier matrices.",
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
        check_anchors(tech_groups, invention_groups)

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
    print(f"Wrote {len(written)} matrices to {args.output_dir}")

    return args.output_dir


if __name__ == "__main__":
    main()
