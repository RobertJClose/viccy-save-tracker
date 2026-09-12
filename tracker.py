from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from pathlib import Path


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# This script lives in:
#
#   ...\Victoria II\save games\your-repo\tracker.py
#
# Therefore:
#
#   REPO_DIR = save games\your-repo
#   SAVE_DIR = save games
#
# The output directory (the CSV history and processed-dates ledger) is chosen
# by the user at runtime and must match the save game being tracked.
#
REPO_DIR = Path(__file__).resolve().parent
SAVE_DIR = REPO_DIR.parent

OUTPUT_FILENAME = "goods_prices.csv"
PROCESSED_FILENAME = "processed_dates.json"

SAVE_FILES = [
    "autosave.v2",
    "oldautosave.v2",
    "olderautosave.v2",
]

# Watch mode tracks only the live autosave. The rotated files are
# deliberately ignored: after a new save game's first autosave, the game
# cascades the previous session's saves into oldautosave.v2 /
# olderautosave.v2, and recording those would pollute the current watch
# with a different save game's data. Consequence: an autosave missed while
# the watcher is down is not backfilled from the rotated files.
WATCH_FILES = [
    "autosave.v2",
]


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


def extract_goods(text: str) -> dict[str, float]:
    """
    Extract every good price from worldmarket.price_pool.

    We first isolate the price_pool block, then capture every pair
    of good_name=price within it.

    Example:
        coal=2.33002
        iron=3.53003

    Returns:
        {"coal": 2.33002, "iron": 3.53003, ...}
    """

    price_pool_match = re.search(
        r'price_pool=\s*\{(.*?)\n\s*\}',
        text,
        re.DOTALL,
    )

    if not price_pool_match:
        raise ValueError("Could not find worldmarket.price_pool.")

    price_pool = price_pool_match.group(1)

    goods: dict[str, float] = {}

    for good, price in re.findall(
        r'(\w+)=([-+]?(?:\d+(?:\.\d*)?|\.\d+))',
        price_pool,
    ):
        goods[good] = float(price)

    if not goods:
        raise ValueError("No goods found in price_pool.")

    return goods


def parse_save(path: Path) -> tuple[str, dict[str, float]]:
    """
    Parse a Victoria II save and return:

        (game_date, {good: price, ...})
    """
    text = read_save(path)

    game_date = extract_game_date(text)
    goods = extract_goods(text)

    return game_date, goods


# ---------------------------------------------------------------------------
# Processed-date tracking
# ---------------------------------------------------------------------------

def load_processed_dates(processed_file: Path) -> set[str]:
    """
    Load dates that have already been exported.
    """
    if not processed_file.exists():
        return set()

    try:
        data = json.loads(processed_file.read_text(encoding="utf-8"))

        if not isinstance(data, list):
            raise ValueError

        return set(data)

    except (json.JSONDecodeError, ValueError):
        print(
            f"Warning: {processed_file} is invalid. "
            "Starting with no processed dates.",
            file=sys.stderr,
        )
        return set()


def save_processed_dates(processed_file: Path, dates: set[str]) -> None:
    """
    Save processed dates in a simple JSON file.
    """
    processed_file.write_text(
        json.dumps(sorted(dates), indent=2),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# CSV handling
# ---------------------------------------------------------------------------

def append_observations(
    output_file: Path,
    game_date: str,
    goods: dict[str, float],
) -> None:
    """
    Append one row per good to goods_prices.csv.

    CSV format:

        date,good,price
        1836-01-02,coal,2.33002
        1836-01-02,iron,3.53003
    """

    file_exists = output_file.exists()

    with output_file.open(
        "a",
        newline="",
        encoding="utf-8",
    ) as csv_file:

        writer = csv.writer(csv_file)

        if not file_exists:
            writer.writerow(["date", "good", "price"])

        for good in sorted(goods):
            writer.writerow([
                game_date,
                good,
                f"{goods[good]:.5f}",
            ])


# ---------------------------------------------------------------------------
# Output paths
# ---------------------------------------------------------------------------

def output_paths(output_dir: Path) -> tuple[Path, Path]:
    """
    Given an output directory, return (output_file, processed_file).
    """
    return (
        output_dir / OUTPUT_FILENAME,
        output_dir / PROCESSED_FILENAME,
    )


# ---------------------------------------------------------------------------
# Save processing
# ---------------------------------------------------------------------------

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
        game_date, goods = parse_save(path)

    except (OSError, ValueError) as exc:
        print(f"Could not process {path.name}: {exc}")
        return False

    # The in-game date is our unique identifier.
    if game_date in processed_dates:
        return False

    append_observations(output_file, game_date, goods)

    processed_dates.add(game_date)
    save_processed_dates(processed_file, processed_dates)

    print(
        f"Recorded {game_date}: "
        f"{len(goods)} goods"
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
        description="Track Victoria II good prices."
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