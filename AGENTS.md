# Agent context

## Purpose

A Python script that watches Victoria II autosaves as they roll in and
appends rows to `.csv` files. The CSVs are designed for import into
LibreOffice Calc for visualisation and analysis.

The tracker records **every** good's price found in
`worldmarket.price_pool`. Each good is a row of `date,good,price`.

It also records the **player's** unlocked technologies (player tag from
the `player=` header; `technology={ ... }` inside that country's block,
where `name={1 0.000}` means unlocked). Techs are discrete, so
`technology_changes.csv` stores the full set once and only differences
afterwards — replaying it in date order reconstructs the state at any
time.

It likewise records the player's **westernisation** (the military /
economic reform set: `land_reform`, `army_schools`, ... as flat
`key=level` lines in the same country block; absent keys, e.g. every
key for a civilised nation, are simply skipped). Levels are recorded
raw in `westernisation_changes.csv` with the same snapshot-then-deltas
shape as technologies.

## Directory layout

```
Documents\Paradox Interactive\Victoria II\
  save games\                <- Victoria II's save directory (parent of the repo)
    autosave.v2              <- live autosave (rotated by the game each month)
    oldautosave.v2           <- previous autosave
    olderautosave.v2         <- two autosaves ago
    tracker\                 <- THIS REPO (the script lives here)
      main.py                  <- entrypoint (CLI, watch loop, orchestration)
      core\                    <- shared infra: config (paths,
                                  GAME_DIR setting), parsing (dates, player
                                  tag, country-block isolation), ledger
                                  (processed-dates, output paths)
      domains\                 <- one module per tracked thing:
        goods.py                 goods-price extraction + CSV output
        technologies.py          player tech extraction + changes CSV
                                 (snapshot first, deltas after)
        westernisation.py        player westernisation extraction + changes CSV
                                 (snapshot first, deltas after)
        inventions.py            STUB: player invention extraction
                                 (NotImplementedError)
      setup\                   <- one-shot setup (run manually, not tracking):
        initialise.py            setup dispatcher (`python -m setup.initialise`)
        build_inventions_map.py  invention ID -> name mapping builder
      data\
        inventions_map.json      committed vanilla mapping (generated, index == ID)
      example_saves\
        example_japan_1836.v2  <- example save for agents to inspect
        example_japan_1845.v2
      tests\                   <- per-module tests + helpers.py (shared fixtures)
      saves\<output-dir>        <- user-chosen per-world output (see below)
        goods_prices.csv       <- output CSV (created at runtime)
        technology_changes.csv <- tech change log (created at runtime)
        westernisation_changes.csv <- westernisation change log (created at runtime)
        processed_dates.json   <- dedup ledger (created at runtime)
```

The script lives **inside** the save directory, so `core/config.py`
can locate the `.v2` files at `Path(__file__).resolve().parent.parent`.

## How to run

```bash
# One-shot: record the file(s) you name and exit. It is your
# responsibility to pick the files that belong to this save game.
# Each --files entry must be a .v2 file name in the save directory
# (no paths).
python main.py --once --files autosave.v2 saves\france

# The same, but also backfill from the previous two autosaves (only
# correct if all three files are from the save game being tracked).
python main.py --once --files autosave.v2,oldautosave.v2,olderautosave.v2 saves\france

# Manual save: stop any watcher first, then record that file into the
# output directory for its world.
python main.py --once --files mysave.v2 saves\france

# Watch: poll the live autosave; new autosaves are processed as they
# appear. Ctrl+C to stop.
python main.py --watch saves\france
```

The output directory is **mandatory** and must already exist. It is the
"history" for a specific save game: it holds that world's
`goods_prices.csv` and `processed_dates.json`. The user is responsible
for pointing the script at the directory matching the save they are
about to play; switching to a different save means stopping and
restarting the script with the other directory.

If neither flag is given, `--once` is the default (and still requires
`--files`).

## Running tests

Before and after any change to the Python sources (`main.py`,
`core/`, `domains/`, `setup/`, ...), run the unit test suite from
the repository root:

```bash
python -m unittest discover -s tests -v
```

The tests document the script's current behaviour end-to-end, including
the parsing helpers, the dedup ledger, the CSV output format, CLI
validation, and watch mode. The real fixture `example_saves/example_japan_1836.v2` is parsed as an
integration test, so good-discovery (including late-game goods like
`automobiles` and `radio`) is verified.

Agents are responsible for writing tests for the code they develop: any
new behaviour must ship with its test, and any behaviour change must be
made together with its updated test. Leave the suite green before
finishing a task.

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

See `example_saves/example_japan_1836.v2` for a full sample (start-of-game date, so no late-game
goods or events).

## CSV schemas

Goods (`goods_prices.csv`):

```
date,good,price
1836-01-02,coal,2.33002
```

`date` is the in-game date (YYYY-MM-DD), not the real-world date. It is
the unique key — the script will never append a row for a date already
recorded.

Technologies (`technology_changes.csv`): one row per acquisition or
loss, with `0` = absent and `1` = present:

```
date,technology,old_value,new_value
1836-01-02,flintlock_rifles,0,1
```

The first date ever tracked writes the full snapshot (one `0 -> 1` row
per unlocked tech, or just the header when none is unlocked); later
dates append only changed techs, and unchanged dates append nothing.

Reforms (`westernisation_changes.csv`): one row per level change, with
levels recorded raw and disappearance as an empty new value:

```
date,westernisation,old_value,new_value
1836-01-02,land_reform,,no_land_reform
```

Same snapshot-then-deltas shape: full levels once, then only changes;
unchanged dates append nothing.

## Dedup / processed dates

`processed_dates.json` holds a sorted JSON array of in-game dates that
have already been exported:

```json
["1836-01-02", "1836-02-01"]
```

If the file is missing or corrupt, the script starts with an empty set
(warning printed to stderr).

## Design notes for future agents

- **Single extraction helper per domain:** each extractable thing owns
  exactly one parsing function in its module — `extract_goods` in
  `domains/goods.py` (isolates the `price_pool` block, returns `{good: price}`),
  `extract_technologies` in `domains/technologies.py` (isolates the player
  country's `technology` block via `core.parsing.extract_country_block`,
  returns `{tech, ...}`; `name={1 0.000}` means unlocked, the value is
  ignored), `extract_westernisation` in `domains/westernisation.py` (flat
  `key=level` lines for the fixed `WESTERNISATION_KEYS` set, returns
  `{westernisation: level}` of keys present; levels recorded raw, absent keys
  skipped), and later `extract_invention_ids` in its module. Good names are discovered
  dynamically from the save rather than hardcoded, so late-game goods
  and modded goods are tracked without code changes. Do not reintroduce
  per-good helpers.
- **One processed-dates ledger:** `processed_dates.json` is the single
  source of truth for what has been tracked. Every module (goods,
  technologies and westernisation today; inventions in future) keys off
  the same in-game-date set — do not add per-module cursors. Discrete
  state is derived by replaying the changes CSVs
  (`load_technology_state`, `load_westernisation_state`), not from
  separate state files.
- **Country blocks need brace matching:** nested `{...}` blocks cannot
  be isolated with a single regex — use
  `core.parsing.extract_braced_content`, which counts braces while skipping
  quoted strings. Tags are anchored at column 0 so values like
  `country="JAP"` never match.
- **Invention IDs are 1-based declaration order:** save-file invention
  IDs index the game install's `inventions/*.txt` files read in sorted
  filename order, top-level `name = {` blocks in file order. The parser
  (`setup/build_inventions_map.py`) strips `#` comments first (commented-out
  inventions take no ID) and skips nested blocks, so nested
  `invention = <name>` cross-references are never collected. Names may
  contain `:`, `.` and leading digits (`genetics:_heredity`,
  `15_inch_main_armament`). `data/inventions_map.json` is generated once via
  `python -m setup.initialise --check-save example_saves/example_japan_1836.v2` (validates count ==
  max save ID plus anchor IDs) and committed as the vanilla default; a
  modded install re-runs with `--game-dir`/`--output`. `GAME_DIR` in
  `core/config.py` is the user-edited install root.
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
  specific `.v2` save file(s) to record (plain file names in the save
  directory, no paths). Correctness is the user's
  responsibility; the script intentionally does not guess.
