# Victoria II Tracker

A small Python program that watches Victoria II autosaves and records
the world-market good prices plus the player country's unlocked
technologies to `.csv` files suitable for import into LibreOffice
Calc.

## Requirements

- Python 3.9+ (uses `pathlib`, builtin generics, and f-strings).
- No third-party packages (stdlib only).
- A working Victoria II installation whose save directory is
  `<game>\save games\`.

## Setup

1. Clone (or copy) this repository **into** the Victoria II save
   directory:

   ```
   <game>\save games\tracker\
   ```

2. (Optional) create a virtual environment — the script is stdlib-only,
   but a venv keeps your system Python clean:

   ```bash
   cd "<game>\save games\tracker"
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. (One-off) build the invention ID → name mapping from your game
   install (already committed for vanilla; re-run only for modded
   installs):

   ```bash
   # Edit GAME_DIR in common.py first, or pass --game-dir explicitly.
   python initialise.py --check-save example.v2
   ```

   `python initialise.py --list` shows the available setup tasks.

## Usage

Both modes require an **output directory** that already exists. This
directory is the "history" for a specific save game: it holds that
world's `goods_prices.csv`, `technology_changes.csv`, and
`processed_dates.json`. Point the script
at the directory matching the save you are about to play.

### One-shot

Record the autosave file(s) you name and exit. You are responsible for
picking the files that belong to the save game being tracked:

```bash
python main.py --once --files autosave.v2 history\france

# Backfill from the previous two autosaves (only correct if all three
# files are from the save game being tracked).
python main.py --once --files autosave.v2,oldautosave.v2,olderautosave.v2 history\france
```

### Watch mode

Poll the live `autosave.v2` continuously; each new autosave is processed
as soon as it is detected (after a short delay to let the game finish
writing). Press **Ctrl+C** to stop.

```bash
python main.py --watch history\france
```

Only `autosave.v2` is watched. The rotated files (`oldautosave.v2`,
`olderautosave.v2`) are deliberately ignored: when a new save game
autosaves for the first time, the game cascades the previous session's
autosaves into those slots, and recording them would pollute the watch
with a different world's data. Since every date first appears in
`autosave.v2`, no current-world observation is missed. Tradeoff: an
autosave missed while the watcher is down is not backfilled automatically
— recover it manually with `--once --files` (see above).

If you load a different save game, stop the watcher and restart it with
the output directory for that world.

## Output

The program writes two CSV files (created on first run) inside the
output directory you specify. In both files, `date` is the in-game date
(YYYY-MM-DD), not the real-world date.

`goods_prices.csv`: for each in-game date, a row for **every** good
found in `worldmarket.price_pool`:

```csv
date,good,price
1836-01-02,coal,2.33002
1836-01-02,iron,3.53003
1836-02-01,coal,2.60028
1836-02-01,iron,3.61029
```

`technology_changes.csv`: the player country's unlocked technologies
as a change log — the full set on the first date tracked, then only
acquisitions and losses (`0` = absent, `1` = present):

```csv
date,technology,old_value,new_value
1836-01-02,flintlock_rifles,0,1
1836-05-03,clean_coal,0,1
```

Replaying `technology_changes.csv` in date order reconstructs the
unlocked set at any date; dates with no changes add no rows.

The good list is taken straight from the save, so late-game goods (for
example `automobiles`, `aeroplanes`, `radio`) appear automatically as
they are unlocked.

### Importing into LibreOffice Calc

This section is planned and not yet ready.

## Dedup

A `processed_dates.json` file is maintained automatically in the output
directory. It stores in-game dates that have already been exported so
that repeated polls never produce duplicate rows. A date is recorded
for all categories together or not at all — `processed_dates.json` is
the single source of truth for what has been tracked.

If this file becomes corrupt, simply delete it — the script will
recreate it on the next run (with a warning on stderr).

## Save file location

The script looks for `autosave.v2` in the **parent** directory of the
repository. In watch mode that is the only file it reads; in one-shot
mode it reads whatever files you name via `--files` (which must be one
of the file names listed in the `SAVE_FILES` constant):

```
save games\
  autosave.v2
  oldautosave.v2
  olderautosave.v2
  tracker\
    main.py
    common.py
    goods.py
    technologies.py
    inventions.py
    unciv_reforms.py
    initialise.py
    init_inventions_map.py
    inventions_map.json
    history\france\
      goods_prices.csv
      technology_changes.csv
      processed_dates.json
```
