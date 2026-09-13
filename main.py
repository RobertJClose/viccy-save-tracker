from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from common import (
    OUTPUT_FILENAME,
    PROCESSED_FILENAME,
    REPO_DIR,
    SAVE_DIR,
    SAVE_FILES,
    WATCH_FILES,
    extract_country_block,
    extract_game_date,
    extract_player_tag,
    load_processed_dates,
    output_paths,
    read_save,
    save_processed_dates,
)
from goods import append_observations, extract_goods
from technologies import (
    CHANGES_FILENAME as TECHNOLOGY_CHANGES_FILENAME,
    append_technology_changes,
    extract_technologies,
    load_technology_state,
)
from unciv_reforms import (
    CHANGES_FILENAME as WESTERNISATION_CHANGES_FILENAME,
    append_westernisation_changes,
    extract_unciv_reforms,
    load_unciv_reform_state,
)


# ---------------------------------------------------------------------------
# Save processing
# ---------------------------------------------------------------------------

def parse_save(path: Path) -> tuple[str, dict[str, float], set[str], dict[str, str]]:
    """
    Parse a Victoria II save and return:

        (game_date, {good: price, ...}, {unlocked technology, ...},
         {uncivilised reform: level, ...})

    Technologies and reforms belong to the player country (see the
    ``player=`` header); ``name={1 0.000}`` means unlocked, and reform
    levels (e.g. ``land_reform=no_land_reform``) are recorded raw.
    """
    text = read_save(path)

    game_date = extract_game_date(text)
    goods = extract_goods(text)
    player_tag = extract_player_tag(text)
    country_block = extract_country_block(text, player_tag)
    technologies = extract_technologies(country_block)
    reforms = extract_unciv_reforms(country_block)

    return game_date, goods, technologies, reforms


def process_save(
    path: Path,
    output_file: Path,
    processed_file: Path,
    processed_dates: set[str],
) -> bool:
    """
    Process one save.

    Returns True if a new observation was recorded.
    """

    if not path.exists():
        return False

    try:
        game_date, goods, techs, reforms = parse_save(path)

    except (OSError, ValueError) as exc:
        print(f"Could not process {path.name}: {exc}")
        return False

    # The in-game date is our unique identifier.
    if game_date in processed_dates:
        return False

    append_observations(output_file, game_date, goods)

    # Discrete state is derived by replaying the changes files, so no
    # extra cursors are needed: processed_dates.json stays the single
    # source of truth for what has been tracked.
    tech_file = processed_file.parent / TECHNOLOGY_CHANGES_FILENAME
    previous_techs = load_technology_state(tech_file)
    acquired, _ = append_technology_changes(
        tech_file, game_date, previous_techs, techs
    )

    reform_file = processed_file.parent / WESTERNISATION_CHANGES_FILENAME
    previous_reforms = load_unciv_reform_state(reform_file)
    changed_reforms = append_westernisation_changes(
        reform_file, game_date, previous_reforms, reforms
    )

    processed_dates.add(game_date)
    save_processed_dates(processed_file, processed_dates)

    print(
        f"Recorded {game_date}: "
        f"{len(goods)} goods, "
        f"{len(techs)} technologies ({len(acquired)} new), "
        f"{len(reforms)} unciv reforms ({len(changed_reforms)} changed)"
    )

    return True


def process_existing_saves(output_dir: Path, files: list[str]) -> None:
    """
    Process the user-chosen autosave files (see --files).
    """

    output_file, processed_file = output_paths(output_dir)
    processed_dates = load_processed_dates(processed_file)

    print(f"Output directory: {output_dir}")
    print(f"Save directory:   {SAVE_DIR}")
    print(f"Repository:       {REPO_DIR}")
    print()

    for filename in files:
        path = SAVE_DIR / filename

        if path.exists():
            process_save(path, output_file, processed_file, processed_dates)
        else:
            print(f"Not found: {filename}")


# ---------------------------------------------------------------------------
# Watch mode
# ---------------------------------------------------------------------------

def watch(output_dir: Path) -> None:
    """
    Continuously monitor the live autosave file.

    When Victoria II overwrites autosave.v2, we wait briefly for the file
    to finish being written before attempting to parse it. Rotated files
    (oldautosave.v2 / olderautosave.v2) are not watched.
    """

    output_file, processed_file = output_paths(output_dir)
    processed_dates = load_processed_dates(processed_file)

    print(f"Watching:         {SAVE_DIR}")
    print(f"Output directory: {output_dir}")
    print("Press Ctrl+C to stop.")
    print()

    # Store the last filesystem modification time we've seen for each file.
    modification_times: dict[Path, float] = {}

    for filename in WATCH_FILES:
        path = SAVE_DIR / filename

        if path.exists():
            modification_times[path] = path.stat().st_mtime

    while True:
        try:
            for filename in WATCH_FILES:
                path = SAVE_DIR / filename

                if not path.exists():
                    continue

                current_mtime = path.stat().st_mtime
                previous_mtime = modification_times.get(path)

                if previous_mtime is None:
                    modification_times[path] = current_mtime
                    continue

                if current_mtime != previous_mtime:
                    modification_times[path] = current_mtime

                    print(
                        f"Change detected: {filename}"
                    )

                    # Victoria II may still be writing the save.
                    time.sleep(2)

                    process_save(path, output_file, processed_file, processed_dates)

            # We don't need to poll particularly frequently.
            time.sleep(2)

        except KeyboardInterrupt:
            print("\nStopped.")
            return


# ---------------------------------------------------------------------------
# Main program
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Track Victoria II good prices, player technology "
            "and uncivilised reforms."
        ),
    )

    parser.add_argument(
        "output_dir",
        type=Path,
        help=(
            "Directory holding the CSV history and processed-dates ledger "
            "for the save game being tracked."
        ),
    )

    parser.add_argument(
        "--once",
        action="store_true",
        help=(
            "Record the autosave file(s) named by --files, then exit. "
            "Requires --files."
        ),
    )

    parser.add_argument(
        "--watch",
        action="store_true",
        help="Watch the live autosave and record new prices as they appear.",
    )

    parser.add_argument(
        "--files",
        metavar="FILE[,FILE...]",
        help=(
            "Comma-separated save file(s) to record with --once, e.g. "
            "autosave.v2 or autosave.v2,oldautosave.v2,olderautosave.v2. "
            "You are responsible for choosing the files that belong to the "
            "save game being tracked."
        ),
    )

    args = parser.parse_args()

    if args.once and args.watch:
        parser.error("Use either --once or --watch, not both.")

    files: list[str] | None = None

    if args.files is not None:
        if not args.once:
            parser.error("--files may only be used with --once.")

        files = [name.strip() for name in args.files.split(",")]

        for filename in files:
            if not filename:
                parser.error("Empty save file name in --files.")
            if filename not in SAVE_FILES:
                parser.error(
                    f"Unknown save file: {filename}. "
                    f"Expected one of: {', '.join(SAVE_FILES)}"
                )

    # The output directory must already exist. It is how the user tells us
    # which save game's history we are tracking.
    if not args.output_dir.is_dir():
        parser.error(
            f"Output directory does not exist: {args.output_dir}"
        )

    # Default to --once if no mode was specified.
    if not args.once and not args.watch:
        args.once = True

    if args.once:
        if files is None:
            parser.error(
                "--once requires --files so you can choose which save "
                "file(s) to record."
            )

        process_existing_saves(args.output_dir, files)

    elif args.watch:
        watch(args.output_dir)


if __name__ == "__main__":
    main()
