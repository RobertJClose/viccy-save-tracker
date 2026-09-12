# Agent context

## Purpose

A Python script that watches Victoria II autosaves as they roll in and
appends rows to a `.csv` file. The CSV is designed for import into
LibreOffice Calc for visualisation and analysis.

The current implementation tracks coal prices. The design goal is a
general goods-price tracker; each good is simply a column (or, as
currently implemented, a row with a `good` field) of `date,good,price`.

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
    coal_prices.csv        <- output CSV (created at runtime)
    processed_dates.json   <- dedup ledger (created at runtime)
```

The script lives **inside** the save directory, so it can locate the
`.v2` files at `Path(__file__).resolve().parent.parent`.

## How to run

```bash
# One-shot: process every available autosave and exit.
python tracker.py --once history\france

# Watch: poll the save directory; new autosaves are processed as they
# appear. Ctrl+C to stop.
python tracker.py --watch history\france
```

The output directory is **mandatory** and must already exist. It is the
"history" for a specific save game: it holds that world's
`coal_prices.csv` and `processed_dates.json`. The user is responsible
for pointing the script at the directory matching the save they are
about to play; switching to a different save means stopping and
restarting the script with the other directory.

If neither flag is given, `--once` is the default.

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

- **Single extraction helper:** Because there are many goods and each
  extraction is trivial, use one function that accepts a good name and
  returns the price, rather than a separate helper per good.
- **stdlib only:** The script uses no third-party packages.
- **Encoding:** Save files are read as UTF-8 with `errors='replace'`
  (one bad byte must not abort the whole file).
- **Polling, not events:** The watcher checks file modification times
  every ~2 seconds and waits an extra 2 seconds after a change is
  detected before parsing (to let the game finish writing).
