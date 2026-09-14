"""Shared fixtures for the tracker test suite.

Extracted verbatim from the former single-file tests/test_tracker.py
(Phase A refactor: file placement only, no logic changes).
"""

import csv
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_SAVE = REPO_ROOT / "example_saves" / "example.v2"


# A small realistic save: header date, several price pools (only price_pool
# must be extracted), and a mix of plain / underscored / numeric good names.
MINIMAL_SAVE = """date="1836.1.2"
player="JAP"
worldmarket=
{
\tworldmarket_pool=
\t{
\t\tcoal=999.0
\t\tiron=888.0
\t}
\tprice_pool=
\t{
\t\tcoal=2.33002
\t\tiron=3.53003
\t\ttropical_wood=5.43002
\t\tmachine_parts=36.51001
\t\tclipper_convoy=42.01001
\t}
\tlast_price_history=
\t{
\t\tcoal=2.32001
\t}
\tsupply_pool=
\t{
\t\tcoal=1802.88763
\t}
}
JAP=
{
\ttechnology=
\t{
\t\tflintlock_rifles={1 0.000}
\t}
\tland_reform=no_land_reform
\tarmy_schools=no_army_schools
}
"""

MINIMAL_TECHS = {"flintlock_rifles"}

MINIMAL_WESTERNISATION = {
    "land_reform": "no_land_reform",
    "army_schools": "no_army_schools",
}

MINIMAL_GOODS = {
    "coal": 2.33002,
    "iron": 3.53003,
    "tropical_wood": 5.43002,
    "machine_parts": 36.51001,
    "clipper_convoy": 42.01001,
}

# Same in-game date but different prices: dedup must key on the date alone.
OLDER_SAVE = """date="1836.1.2"
player="JAP"
worldmarket=
{
\tprice_pool=
\t{
\t\tcoal=9.99
\t\tiron=8.88
\t\ttropical_wood=7.77
\t\tmachine_parts=6.66
\t\tclipper_convoy=5.55
\t}
}
JAP=
{
\ttechnology=
\t{
\t}
\tland_reform=no_land_reform
}
"""


def read_csv(path: Path) -> list[list[str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.reader(f))


# A synthetic game install: two invention files exercising comments,
# nested blocks, cross-references and unusual-but-valid names.
INIT_FIXTURE_A = """#tech_group_one
first_invention = {
\tlimit = { some_tech = 1 }
\tchance = {
\t\tbase = 2
\t\tmodifier = {
\t\t\tfactor = 2
\t\t\tinvention = other_invention
\t\t}
\t}
\teffect = {
\t\tmorale = 0.15
\t}
}
# A commented-out invention must not take an ID.
#dead_invention = {
#\tlimit = { some_tech = 1 }
#}
genetics:_heredity = {
\tlimit = { medicine = 1 } # inline comment
\tchance = {
\t\tbase = 2
\t}
}
"""

INIT_FIXTURE_B = """populism_vs._establishment = {
\tlimit = { state_n_government = 1 }
}
15_inch_main_armament = {
\tlimit = { modern_naval_design = 1 }
\tchance = {
\t\tbase = 2
\t\tmodifier = {
\t\t\tfactor = 2
\t\t\tinvention = first_invention # cross-file reference
\t\t}
\t}
}
"""


def make_game_dir(root: Path) -> Path:
    game_dir = root / "game"
    inventions = game_dir / "inventions"
    inventions.mkdir(parents=True)
    (inventions / "b_second.txt").write_text(INIT_FIXTURE_B, encoding="utf-8")
    (inventions / "a_first.txt").write_text(INIT_FIXTURE_A, encoding="utf-8")
    return game_dir
