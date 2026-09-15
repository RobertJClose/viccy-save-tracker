"""One-shot initialisation: build the exhaustive modifier-name list.

Technologies, inventions and westernisation reforms grant the player
country numeric bonuses (``factory_input = -0.01``,
``rgo_goods_output = { iron = 0.25 }``, ...). This task scrapes every
such effect name from the game installation and writes them as a plain
alphabetical list (one name per line) for later per-category work to
build on.

Scope rules (agreed with the user):

- Technologies: everything inside each tech block except the
  ``area``/``year``/``cost`` labels and the ``ai_chance`` block.
- Inventions: only inside ``effect = { ... }`` (``limit``/``chance``
  are trigger vocabulary, not bonuses).
- Westernisation reforms (``common/issues.txt``): only the level blocks
  (e.g. ``yes_land_reform = { ... }``), ignoring
  ``on_execute``/``trigger``.
- Numbers only: a name is listed only if it carries a numeric value,
  so unlocks like ``activate_building = lumber_mill`` and effect-less
  inventions contribute nothing.

Nested ``block = { key = number }`` effects are flattened to composite
names so that every future table cell stays a plain number:
``artillery = { defence = 1 }`` becomes ``artillery_defence`` and
``rgo_goods_output = { iron = 0.25 }`` becomes
``rgo_goods_output_iron``. The single oddball,
``rebel_org_gain = { faction = X value = N }``, becomes
``rebel_org_gain_X``; any other shape fails loudly.
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

TECHNOLOGIES_SUBDIR = "technologies"
INVENTIONS_SUBDIR = "inventions"
ISSUES_PATH = Path("common") / "issues.txt"

# File name this task writes inside the output directory chosen via
# --output (or setup.initialise --output-dir).
OUTPUT_FILENAME = "modifiers_list.txt"

# Numeric labels in tech bodies that are metadata, not bonuses.
TECH_SKIP_SCALARS = {"area", "year", "cost"}
# Blocks whose contents are never bonuses.
TECH_SKIP_BLOCKS = {"ai_chance"}
REFORM_SKIP_BLOCKS = {"on_execute", "trigger"}

REFORM_GROUPS = ("economic_reforms", "military_reforms")

KEY_RE = re.compile(r"([A-Za-z0-9_:.]+)\s*=")
NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")
TOKEN_RE = re.compile(r'"[^"]*"|\S+')


def remove_named_blocks(text: str, names: set[str]) -> str:
    """Cut out every ``name = { ... }`` block for ``names`` in text."""
    pattern = re.compile(r"([A-Za-z0-9_:.]+)\s*=\s*\{")

    while True:
        match = next(
            (m for m in pattern.finditer(text) if m.group(1) in names),
            None,
        )

        if match is None:
            return text

        inner = extract_braced_content(text, match.end() - 1, match.group(1))
        text = text[: match.start()] + " " + text[match.end() - 1 + len(inner) + 2 :]


def iter_top_level_blocks(text: str) -> list[tuple[str, str]]:
    """Return (name, inner) for every depth-0 ``name = { ... }`` block."""
    blocks: list[tuple[str, str]] = []
    depth = 0
    in_quotes = False

    for match in re.finditer(r'"|[{}]|([A-Za-z0-9_:.]+)\s*=\s*\{', text):
        token = match.group(0)

        if token == '"':
            in_quotes = not in_quotes
        elif in_quotes:
            continue
        elif match.group(1) is not None:
            # A keyed block opener counts for depth like a bare brace.
            if depth == 0:
                name = match.group(1)
                inner = extract_braced_content(text, match.end() - 1, name)
                blocks.append((name, inner))
            depth += 1
        elif token == "{":
            depth += 1
        elif token == "}":
            depth -= 1

    return blocks


def collect_modifiers(text: str) -> set[str]:
    """Collect composite modifier names from one effect-context body.

    Depth-0 ``key = number`` entries are recorded as-is; deeper
    ``key = number`` entries are prefixed with their enclosing block
    path (``artillery_defence``). Non-numeric values (tech labels, unit
    names, trigger words) contribute nothing. ``rebel_org_gain`` is the
    one block pairing a text label with its number and is handled
    specially (see module docstring).
    """
    names: set[str] = set()
    stack: list[str | None] = []
    rebel_faction: str | None = None
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
                if rebel_faction is None:
                    raise ValueError(
                        "rebel_org_gain block without a faction label."
                    )
                names.add(f"rebel_org_gain_{rebel_faction}")
                rebel_faction = None
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
            i = j + 1
            continue

        token_match = TOKEN_RE.match(text[j:])

        if token_match:
            token = token_match.group(0)
            is_number = not token.startswith('"') and NUMBER_RE.fullmatch(token)

            if is_number:
                if "rebel_org_gain" in stack:
                    pass  # Recorded with its faction when the block closes.
                elif path():
                    names.add("_".join([*path(), key]))
                elif key not in TECH_SKIP_SCALARS:
                    names.add(key)
            elif "rebel_org_gain" in stack and key == "faction":
                rebel_faction = token

            i = j + token_match.end()
            continue

        i = j if j > i else i + 1

    if "rebel_org_gain" in stack:
        raise ValueError("Unbalanced rebel_org_gain block.")

    return names


def read_game_text(path: Path) -> str:
    """Read a game data file with comments stripped."""
    return strip_comments(path.read_text(encoding="utf-8", errors="replace"))


def collect_technology_modifiers(game_dir: Path) -> tuple[set[str], int]:
    """Return (modifier names, tech count) from technologies/*.txt."""
    tech_dir = game_dir / TECHNOLOGIES_SUBDIR

    if not tech_dir.is_dir():
        raise FileNotFoundError(
            f"No technologies directory at {tech_dir}. "
            "Pass --game-dir pointing at your Victoria II installation "
            "or set GAME_DIR in core/config.py."
        )

    names: set[str] = set()
    count = 0

    for path in sorted(
        p for p in tech_dir.iterdir() if p.is_file() and p.suffix == ".txt"
    ):
        for _, inner in iter_top_level_blocks(read_game_text(path)):
            count += 1
            names.update(
                collect_modifiers(remove_named_blocks(inner, TECH_SKIP_BLOCKS))
            )

    return names, count


def collect_invention_modifiers(game_dir: Path) -> tuple[set[str], int]:
    """Return (modifier names, invention count) from inventions/*.txt.

    Only ``effect = { ... }`` blocks are scanned.
    """
    inventions_dir = game_dir / INVENTIONS_SUBDIR

    if not inventions_dir.is_dir():
        raise FileNotFoundError(
            f"No inventions directory at {inventions_dir}. "
            "Pass --game-dir pointing at your Victoria II installation "
            "or set GAME_DIR in core/config.py."
        )

    names: set[str] = set()
    count = 0

    for path in sorted(
        p for p in inventions_dir.iterdir() if p.is_file() and p.suffix == ".txt"
    ):
        text = read_game_text(path)

        for _, inner in iter_top_level_blocks(text):
            count += 1

            for match in re.finditer(r"effect\s*=\s*\{", inner):
                effect = extract_braced_content(inner, match.end() - 1, "effect")
                names.update(collect_modifiers(effect))

    return names, count


def collect_reform_modifiers(game_dir: Path) -> tuple[set[str], dict[str, list[str]]]:
    """Return (modifier names, {reform: [levels]}) from common/issues.txt."""
    issues = game_dir / ISSUES_PATH

    if not issues.is_file():
        raise FileNotFoundError(
            f"No issues file at {issues}. "
            "Pass --game-dir pointing at your Victoria II installation "
            "or set GAME_DIR in core/config.py."
        )

    text = read_game_text(issues)
    names: set[str] = set()
    levels: dict[str, list[str]] = {}

    for group in REFORM_GROUPS:
        match = re.search(re.escape(group) + r"\s*=\s*\{", text)

        if not match:
            raise ValueError(f"Could not find {group} in {issues}.")

        for reform, reform_inner in iter_top_level_blocks(
            extract_braced_content(text, match.end() - 1, group)
        ):
            for level, level_inner in iter_top_level_blocks(reform_inner):
                levels.setdefault(reform, []).append(level)
                names.update(
                    collect_modifiers(
                        remove_named_blocks(level_inner, REFORM_SKIP_BLOCKS)
                    )
                )

    return names, levels


# Anchor predictions for the vanilla files: one plain scalar, one nested
# unit stat, one per-good composite, one reform scalar and the oddball
# rebel shape. Checked only for source == "vanilla".
ANCHORS = {
    "factory_input",
    "artillery_defence",
    "rgo_goods_output_iron",
    "tax_eff",
    "civilization_progress_modifier",
    "rebel_org_gain_nationalist_rebels",
}


def validate_against_save(
    tech_names: set[str],
    reform_levels: dict[str, list[str]],
    save_text: str,
    save_name: str,
) -> None:
    """Fail if the save uses techs/reforms outside the scraped catalogue."""
    player_tag = extract_player_tag(save_text)
    country_block = extract_country_block(save_text, player_tag)

    unknown_techs = sorted(extract_technologies(country_block) - tech_names)

    if unknown_techs:
        raise ValueError(
            f"{save_name} unlocks technologies outside the catalogue: "
            f"{unknown_techs[:10]}..."
        )

    westernisation = extract_westernisation(country_block)
    unknown_levels = sorted(
        f"{key}={level}"
        for key, level in westernisation.items()
        if key in WESTERNISATION_KEYS
        and level not in reform_levels.get(key, [])
    )

    if unknown_levels:
        raise ValueError(
            f"{save_name} uses westernisation levels outside the catalogue: "
            f"{unknown_levels[:10]}..."
        )


def write_list(
    output: Path,
    names: set[str],
    source: str,
    tech_count: int,
    invention_count: int,
    level_count: int,
) -> None:
    """Write the alphabetical list; `#` lines are provenance, not data."""
    lines = [
        f"# Victoria II modifier list ({source})",
        "# Sources: technologies/*.txt, inventions/*/effect, "
        "common/issues.txt (economic/military reforms)",
        f"# Counts: {tech_count} technologies, "
        f"{invention_count} inventions, {level_count} reform levels",
        f"# Names: {len(names)}",
    ]
    lines.extend(sorted(names))
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> Path:
    parser = argparse.ArgumentParser(
        description="Build the exhaustive Victoria II modifier-name list.",
    )

    parser.add_argument(
        "--game-dir",
        type=Path,
        default=GAME_DIR,
        help="Victoria II installation directory (default: GAME_DIR in core/config.py).",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=VANILLA_DATA_DIR / OUTPUT_FILENAME,
        help="Where to write the list (default: data/vanilla/modifiers_list.txt).",
    )

    parser.add_argument(
        "--check-save",
        type=Path,
        default=None,
        help="Save file to validate the catalogue against (e.g. example.v2).",
    )

    parser.add_argument(
        "--source",
        default="vanilla",
        help="Label recorded in the list (use e.g. a mod name for modded installs).",
    )

    args = parser.parse_args(argv)

    if args.game_dir is None:
        parser.error("--game-dir is required (GAME_DIR in core/config.py is unset).")

    tech_modifiers, tech_count = collect_technology_modifiers(args.game_dir)
    print(f"Found {tech_count} technologies.")
    invention_modifiers, invention_count = collect_invention_modifiers(args.game_dir)
    print(f"Found {invention_count} inventions.")
    reform_modifiers, reform_levels = collect_reform_modifiers(args.game_dir)
    print(f"Found {len(reform_levels)} westernisation reforms.")

    names = tech_modifiers | invention_modifiers | reform_modifiers

    if args.source == "vanilla":
        missing = sorted(ANCHORS - names)

        if missing:
            raise ValueError(
                f"Anchor modifiers missing from the catalogue: {missing}. "
                "The effect parser is wrong; not writing the list."
            )

    if args.check_save is not None:
        save_text = args.check_save.read_text(encoding="utf-8", errors="replace")
        validate_against_save(
            tech_names_only(args.game_dir),
            reform_levels,
            save_text,
            args.check_save.name,
        )
        print(f"Save checks passed for {args.check_save.name}.")

    level_count = sum(len(levels) for levels in reform_levels.values())
    write_list(
        args.output, names, args.source, tech_count, invention_count, level_count
    )
    print(f"Wrote {len(names)} modifiers to {args.output}")

    return args.output


def tech_names_only(game_dir: Path) -> set[str]:
    """Return every technology name declared in technologies/*.txt."""
    tech_dir = game_dir / TECHNOLOGIES_SUBDIR
    tech_names: set[str] = set()

    for path in sorted(
        p for p in tech_dir.iterdir() if p.is_file() and p.suffix == ".txt"
    ):
        tech_names.update(
            name for name, _ in iter_top_level_blocks(read_game_text(path))
        )

    return tech_names


if __name__ == "__main__":
    main()
