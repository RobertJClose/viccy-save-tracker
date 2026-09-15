# Victoria II Tracker

A small Python program that watches Victoria II autosaves and records
the world-market good prices, the player country's unlocked
technologies, and its westernisation to `.csv` files suitable for
import into LibreOffice Calc.

## Requirements

- Python 3.9+ (uses `pathlib`, builtin generics, and f-strings).
- No third-party packages (stdlib only).
- A working Victoria II installation. Note the save directory is **not**
  under the game install: saves live in your Documents folder at
  `Documents\Paradox Interactive\Victoria II\save games\`
  (e.g. `C:\Users\<you>\Documents\Paradox Interactive\Victoria II\save games\`).

## Setup

1. Clone (or copy) this repository **into** the Victoria II save
   directory:

   ```
   Documents\Paradox Interactive\Victoria II\save games\tracker\
   ```

2. (Optional) create a virtual environment — the script is stdlib-only,
   but a venv keeps your system Python clean:

    ```bash
    cd "Documents\Paradox Interactive\Victoria II\save games\tracker"
    python -m venv .venv
    .venv\Scripts\activate
    ```

3. (One-off) build the reference data from your game
   install (already committed for vanilla; re-run only for modded
   installs):

    ```bash
    # Edit GAME_DIR in core/config.py first, or pass --game-dir explicitly.
     python -m setup.initialise --check-save example_saves/example_japan_1836.v2
    ```

    This builds the invention ID → name mapping
    (`data/vanilla/inventions_map.json`), the exhaustive
    modifier-name list (`data/vanilla/modifiers_from_research_list.txt`, every numeric
    tech/invention/reform effect, e.g. `factory_input`,
    `artillery_defence`, `rgo_goods_output_iron`), the 24
    per-goods modifier matrices (`data/vanilla/{tech,invention,
    westernisation}_modifiers/<group>/{rgo_goods,factory_goods}_modifiers.csv`),
    and one `<category>_modifiers.csv` per group directory for each of the
    colonial, prestige, population, diplomacy, other, research,
    economic and military categories.
    Every matrix holds one value per source, with `0.0` for no effect.

    Reference data lives in one directory per game variant
    (`data/vanilla/`; modded installs generate `data/<mod>/` siblings).
    Like the tracking output directories, the directory must already
    exist — create it first, then point the run at it:

    ```bash
    mkdir data\my_mod
     python -m setup.initialise --game-dir <modded-install> --output-dir data\my_mod --source my_mod
    ```

    `python -m setup.initialise --list` shows the available setup tasks.

## Usage

Both modes require an **output directory** that already exists. This
directory is the "history" for a specific save game: it holds that
world's `goods_prices.csv`, `technology_changes.csv`,
`westernisation_changes.csv`, and
`processed_dates.json`. Point the script
at the directory matching the save you are about to play.

### One-shot

Record the save file(s) you name and exit. You are responsible for
picking the files that belong to the save game being tracked. Each file
must be a `.v2` file name in the save directory (no paths):

```bash
python main.py --once --files autosave.v2 saves\france

# Backfill from the previous two autosaves (only correct if all three
# files are from the save game being tracked).
python main.py --once --files autosave.v2,oldautosave.v2,olderautosave.v2 saves\france

# Record a manual save (stop any watcher first, and point at the output
# directory for that world).
python main.py --once --files mysave.v2 saves\france
```

### Watch mode

Poll the live `autosave.v2` continuously; each new autosave is processed
as soon as it is detected (after a short delay to let the game finish
writing). Press **Ctrl+C** to stop.

```bash
python main.py --watch saves\france
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

The program writes three CSV files (created on first run) inside the
output directory you specify. In all files, `date` is the in-game date
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

`westernisation_changes.csv`: the player country's westernisation
levels as a change log — full levels on the first date tracked, then
only changes (levels recorded raw; a vanished key means an empty new
value):

```csv
date,westernisation,old_value,new_value
1836-01-02,land_reform,,no_land_reform
1836-05-03,land_reform,no_land_reform,land_reform_enacted
```

Replaying it in date order reconstructs the levels at any date; dates
with no changes add no rows. Civilised nations have none of these keys,
so their file holds just the header.

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
mode it reads whatever `.v2` files you name via `--files` (plain file
names in the save directory, no paths):

```
save games\
  autosave.v2
  oldautosave.v2
  olderautosave.v2
  mysave.v2
  tracker\
    main.py
    core\
      config.py
      parsing.py
      ledger.py
    domains\
      goods.py
      technologies.py
      westernisation.py
      inventions.py
    setup\
      initialise.py
      build_inventions_map.py
      research_modifiers\        player bonuses from in-game research:
        build_modifiers_from_research_list.py
        build_per_goods_matrices.py
        build_per_unit_matrices.py
        build_{colonial,prestige,population,diplomacy,other}_matrices.py
        build_{research,economic}_matrices.py
        build_military_matrices.py
    data\
      vanilla\                    <- committed vanilla reference data
        inventions_map.json
        modifiers_from_research_list.txt
        tech_modifiers\<type>\      <- matrices: one dir per tech/invention
        invention_modifiers\<type>\    type (army, commerce, culture,
        westernisation_modifiers\      industry, navy) or reform group
          <group>\                     (economic, military), each holding
            rgo_goods_modifiers.csv    rgo/factory per-goods files, land/naval
            factory_goods_modifiers.csv  per-unit files, plus one
            per_unit_land_modifiers.csv  <category>_modifiers.csv per
            per_unit_naval_modifiers.csv   implemented category (colonial,
            colonial_modifiers.csv       prestige, population, diplomacy,
            prestige_modifiers.csv       other, research, economic)
            population_modifiers.csv
            diplomacy_modifiers.csv
            other_modifiers.csv
            research_modifiers.csv
            economic_modifiers.csv
            military_modifiers.csv
      <mod>\                     <- per-mod reference data (generated, not committed)
    example_saves\
      example_japan_1836.v2
      example_japan_1845.v2
    saves\france\
      goods_prices.csv
      technology_changes.csv
      westernisation_changes.csv
      processed_dates.json
```
