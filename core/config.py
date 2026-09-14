from __future__ import annotations

from pathlib import Path


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# This package lives in:
#
#   ...\Victoria II\save games\your-repo\core\config.py
#
# Therefore:
#
#   REPO_DIR = save games\your-repo
#   SAVE_DIR = save games
#
# The output directory (the CSV history and processed-dates ledger) is chosen
# by the user at runtime and must match the save game being tracked.
#
REPO_DIR = Path(__file__).resolve().parent.parent
SAVE_DIR = REPO_DIR.parent

# User setting: edit this to point at your Victoria II installation.
# Used by setup.initialise to locate game data (e.g. inventions/*.txt);
# --game-dir on the command line overrides it.
GAME_DIR = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Victoria 2")

# Default vanilla invention ID -> name mapping (committed to the repo).
INVENTIONS_MAP_FILE = REPO_DIR / "data" / "inventions_map.json"

OUTPUT_FILENAME = "goods_prices.csv"
PROCESSED_FILENAME = "processed_dates.json"

# Watch mode tracks only the live autosave. The rotated files are
# deliberately ignored: after a new save game's first autosave, the game
# cascades the previous session's saves into oldautosave.v2 /
# olderautosave.v2, and recording those would pollute the current watch
# with a different save game's data. Consequence: an autosave missed while
# the watcher is down is not backfilled from the rotated files.
WATCH_FILES = [
    "autosave.v2",
]
