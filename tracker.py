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
REPO_DIR = Path(__file__).resolve().parent
SAVE_DIR = REPO_DIR.parent

OUTPUT_FILE = REPO_DIR / "coal_prices.csv"
PROCESSED_FILE = REPO_DIR / "processed_dates.json"

SAVE_FILES = [
    "autosave.v2",
    "oldautosave.v2",
    "olderautosave.v2",
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


def extract_coal_price(text: str) -> float:
    """
    Extract the coal price from worldmarket.price_pool.

    We first isolate the price_pool block, then look specifically for coal.

    Example:
        coal=2.77045
    """

    price_pool_match = re.search(
        r'price_pool=\s*\{(.*?)\n\s*\}',
        text,
        re.DOTALL,
    )

    if not price_pool_match:
        raise ValueError("Could not find worldmarket.price_pool.")

    price_pool = price_pool_match.group(1)

    coal_match = re.search(
        r'\bcoal=([-+]?(?:\d+(?:\.\d*)?|\.\d+))',
        price_pool,
    )

    if not coal_match:
        raise ValueError("Could not find coal price in price_pool.")

    return float(coal_match.group(1))


def parse_save(path: Path) -> tuple[str, float]:
    """
    Parse a Victoria II save and return:

        (game_date, coal_price)
    """
    text = read_save(path)

    game_date = extract_game_date(text)
    coal_price = extract_coal_price(text)

    return game_date, coal_price


# ---------------------------------------------------------------------------
# Processed-date tracking
# ---------------------------------------------------------------------------

def load_processed_dates() -> set[str]:
    """
    Load dates that have already been exported.
    """
    if not PROCESSED_FILE.exists():
        return set()

    try:
        data = json.loads(PROCESSED_FILE.read_text(encoding="utf-8"))

        if not isinstance(data, list):
            raise ValueError

        return set(data)

    except (json.JSONDecodeError, ValueError):
        print(
            f"Warning: {PROCESSED_FILE} is invalid. "
            "Starting with no processed dates.",
            file=sys.stderr,
        )
        return set()


def save_processed_dates(dates: set[str]) -> None:
    """
    Save processed dates in a simple JSON file.
    """
    PROCESSED_FILE.write_text(
        json.dumps(sorted(dates), indent=2),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# CSV handling
# ---------------------------------------------------------------------------

def append_observation(game_date: str, coal_price: float) -> None:
    """
    Append one observation to coal_prices.csv.

    CSV format:

        date,good,price
        1836-01-02,coal,2.33002
    """

    file_exists = OUTPUT_FILE.exists()

    with OUTPUT_FILE.open(
        "a",
        newline="",
        encoding="utf-8",
    ) as csv_file:

        writer = csv.writer(csv_file)

        if not file_exists:
            writer.writerow(["date", "good", "price"])

        writer.writerow([
            game_date,
            "coal",
            f"{coal_price:.5f}",
        ])


# ---------------------------------------------------------------------------
# Save processing
# ---------------------------------------------------------------------------

def process_save(path: Path, processed_dates: set[str]) -> bool:
    """
    Process one save.

    Returns True if a new observation was recorded.
    """

    if not path.exists():
        return False

    try:
        game_date, coal_price = parse_save(path)

    except (OSError, ValueError) as exc:
        print(f"Could not process {path.name}: {exc}")
        return False

    # The in-game date is our unique identifier.
    if game_date in processed_dates:
        return False

    append_observation(game_date, coal_price)

    processed_dates.add(game_date)
    save_processed_dates(processed_dates)

    print(
        f"Recorded {game_date}: "
        f"coal = {coal_price:.5f}"
    )

    return True


def process_existing_saves() -> None:
    """
    Process all currently available autosaves.
    """

    processed_dates = load_processed_dates()

    print(f"Save directory: {SAVE_DIR}")
    print(f"Repository:     {REPO_DIR}")
    print()

    for filename in SAVE_FILES:
        path = SAVE_DIR / filename

        if path.exists():
            process_save(path, processed_dates)
        else:
            print(f"Not found: {filename}")


# ---------------------------------------------------------------------------
# Watch mode
# ---------------------------------------------------------------------------

def watch() -> None:
    """
    Continuously monitor the autosave files.

    When Victoria II modifies an autosave, we wait briefly for the file to
    finish being written before attempting to parse it.
    """

    processed_dates = load_processed_dates()

    print(f"Watching: {SAVE_DIR}")
    print("Press Ctrl+C to stop.")
    print()

    # Store the last filesystem modification time we've seen for each file.
    modification_times: dict[Path, float] = {}

    for filename in SAVE_FILES:
        path = SAVE_DIR / filename

        if path.exists():
            modification_times[path] = path.stat().st_mtime

    while True:
        try:
            for filename in SAVE_FILES:
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

                    process_save(path, processed_dates)

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
        description="Track Victoria II coal prices."
    )

    parser.add_argument(
        "--once",
        action="store_true",
        help="Process currently available saves and exit.",
    )

    parser.add_argument(
        "--watch",
        action="store_true",
        help="Watch the save directory for new autosaves.",
    )

    args = parser.parse_args()

    if args.once and args.watch:
        parser.error("Use either --once or --watch, not both.")

    # Default to --once if no mode was specified.
    if not args.once and not args.watch:
        args.once = True

    if args.once:
        process_existing_saves()

    elif args.watch:
        watch()


if __name__ == "__main__":
    main()