# Victoria II Price Tracker

A small Python script that watches Victoria II autosaves and appends
commodity prices to a `.csv` file suitable for import into LibreOffice
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
world's `coal_prices.csv` and `processed_dates.json`. Point the script at
the directory matching the save you are about to play.

### One-shot

Process every available autosave and exit:

```bash
python tracker.py --once history\france
```

### Watch mode

Poll the save directory continuously; new autosaves are processed as
soon as they are detected (after a short delay to let the game finish
writing). Press **Ctrl+C** to stop.

```bash
python tracker.py --watch history\france
```

If you load a different save game, stop the watcher and restart it with
the output directory for that world.

## Output

The script writes `coal_prices.csv` (created on first run) inside the
output directory you specify:

```csv
date,good,price
1836-01-02,coal,2.33002
1836-02-01,coal,2.60028
```

`date` is the in-game date (YYYY-MM-DD), not the real-world date.

### Importing into LibreOffice Calc

1. Open LibreOffice Calc.
2. **File → Open** and select `coal_prices.csv`.
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

The script expects the three Victoria II autosave files to be in the
**parent** directory of the repository:

```
save games\
  autosave.v2
  oldautosave.v2
  olderautosave.v2
  tracker\
    tracker.py
    history\france\
      coal_prices.csv
      processed_dates.json
```

If the game is configured with more or fewer autosave slots, edit the
`SAVE_FILES` list in `tracker.py`.
