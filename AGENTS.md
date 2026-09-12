# Agent context

## Purpose

A Python script that watches Victoria II autosaves as they roll in and
appends rows to a `.csv` file. The CSV is designed for import into
LibreOffice Calc for visualisation and analysis.

The tracker records **every** good's price found in
`worldmarket.price_pool`. Each good is a row of `date,good,price`.

## Directory layout

```
save games\                <- Victoria II's save directory (parent of the repo)
  autosave.v2              <- live autosave (rotated by the game each month)
  oldautosave.v2           <- previous autosave
  olderautosave.v2         <- two autosaves ago
  tracker\                 <- THIS REPO (the script lives here)
    tracker.py
    example.v2             <- example save for agents to inspect
  history\<output-dir>      <- user-chosen per-world output (see below)
    goods_prices.csv       <- output CSV (created at runtime)
    processed_dates.json   <- dedup ledger (created at runtime)
```

The script lives **inside** the save directory, so it can locate the
`.v2` files at `Path(__file__).resolve().parent.parent`.

## How to run

```bash
# One-shot: record the file(s) you name and exit. It is your
# responsibility to pick the files that belong to this save game.
python tracker.py --once --files autosave.v2 history\france

# The same, but also backfill from the previous two autosaves (only
# correct if all three files are from the save game being tracked).
python tracker.py --once --files autosave.v2,oldautosave.v2,olderautosave.v2 history\france

# Watch: poll the live autosave; new autosaves are processed as they
# appear. Ctrl+C to stop.
python tracker.py --watch history\france
```

The output directory is **mandatory** and must already exist. It is the
"history" for a specific save game: it holds that world's
`goods_prices.csv` and `processed_dates.json`. The user is responsible
for pointing the script at the directory matching the save they are
about to play; switching to a different save means stopping and
restarting the script with the other directory.

If neither flag is given, `--once` is the default (and still requires
`--files`).

## Save-file format (for reference)

Victoria II saves are plain text. The first line is the game date:

```
date="1836.1.2"
```

Prices live inside `worldmarket.price_pool`:

```
worldmarket=
{
    ...
    price_pool=
    {
        coal=2.33002
        iron=3.53003
        ...
    }
}
```

Each line inside the block is `good_name=decimal_price`.

See `example.v2` for a full sample (start-of-game date, so no late-game
goods or events).

## CSV schema

```
date,good,price
1836-01-02,coal,2.33002
```

`date` is the in-game date (YYYY-MM-DD), not the real-world date. It is
the unique key — the script will never append a row for a date already
recorded.

## Dedup / processed dates

`processed_dates.json` holds a sorted JSON array of in-game dates that
have already been exported:

```json
["1836-01-02", "1836-02-01"]
```

If the file is missing or corrupt, the script starts with an empty set
(warning printed to stderr).

## Design notes for future agents

- **Single extraction helper:** There is exactly one parsing function,
  `extract_goods`, which isolates the `price_pool` block and returns a
  `{good: price}` dict. Good names are discovered dynamically from the
  save rather than hardcoded, so late-game goods and modded goods are
  tracked without code changes. Do not reintroduce per-good helpers.
- **Stdlib only:** The script uses no third-party packages.
- **Encoding:** Save files are read as UTF-8 with `errors='replace'`
  (one bad byte must not abort the whole file).
- **Polling, not events:** The watcher checks the live autosave's
  modification time every ~2 seconds and waits an extra 2 seconds after
  a change is detected before parsing (to let the game finish writing).
- **Watch mode tracks only `autosave.v2`:** `oldautosave.v2` and
  `olderautosave.v2` are deliberately not watched. When a new save game
  autosaves for the first time, the game cascades the previous session's
  autosaves into those rotated files; watching them would pollute the
  current watch with a different save game's data. Tradeoff: an autosave
  missed while the watcher is down is not backfilled automatically (see
  `--once --files` for manual recovery). Do not reintroduce them into
  the watch loop without solving the cross-world contamination.
- **`--once` is a manual operation:** it requires `--files` naming the
  specific save file(s) to record. Correctness is the user's
  responsibility; the script intentionally does not guess.
