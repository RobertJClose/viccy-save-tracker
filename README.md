# Victoria II Price Tracker

A small Python script that watches Victoria II autosaves and appends
every good's price to a `.csv` file suitable for import into LibreOffice
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

## Usage

Both modes require an **output directory** that already exists. This
directory is the "history" for a specific save game: it holds that
world's `goods_prices.csv` and `processed_dates.json`. Point the script
at the directory matching the save you are about to play.

### One-shot

Record the autosave file(s) you name and exit. You are responsible for
picking the files that belong to the save game being tracked:

```bash
python tracker.py --once --files autosave.v2 history\france

# Backfill from the previous two autosaves (only correct if all three
# files are from the save game being tracked).
python tracker.py --once --files autosave.v2,oldautosave.v2,olderautosave.v2 history\france
```

### Watch mode

Poll the live `autosave.v2` continuously; each new autosave is processed
as soon as it is detected (after a short delay to let the game finish
writing). Press **Ctrl+C** to stop.

```bash
python tracker.py --watch history\france
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

The script writes `goods_prices.csv` (created on first run) inside the
output directory you specify. For each in-game date it records a row for
**every** good found in `worldmarket.price_pool`:

```csv
date,good,price
1836-01-02,coal,2.33002
1836-01-02,iron,3.53003
1836-02-01,coal,2.60028
1836-02-01,iron,3.61029
```

`date` is the in-game date (YYYY-MM-DD), not the real-world date. The
good list is taken straight from the save, so late-game goods (for
example `automobiles`, `aeroplanes`, `radio`) appear automatically as
they are unlocked.

### Importing into LibreOffice Calc

1. Open LibreOffice Calc.
2. **File → Open** and select `goods_prices.csv`.
3. In the Text Import dialog:
   - Character set: Unicode (UTF-8)
   - Separator: Comma
4. Click **OK**.

The data can now be plotted or analysed like any other spreadsheet.

## Dedup

A `processed_dates.json` file is maintained automatically in the output
directory. It stores in-game dates that have already been exported so
that repeated polls never produce duplicate rows.

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
    tracker.py
    history\france\
      goods_prices.csv
      processed_dates.json
```
