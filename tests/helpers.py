"""Shared fixtures for the tracker test suite.

Extracted verbatim from the former single-file tests/test_tracker.py
(Phase A refactor: file placement only, no logic changes).
"""

import csv
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_SAVE = REPO_ROOT / "example_saves" / "example_japan_1836.v2"


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


# A synthetic game install for the modifier-list setup task: one tech
# exercising scalars, per-good and unit blocks, metadata and ai_chance;
# inventions exercising effect-only scanning (plus an effect-less one and
# the rebel_org_gain oddball); and a minimal issues.txt with one
# economic and one military reform group.
MOD_TECH_FIXTURE = """#tech_group_one
test_tech_alpha = {
\tarea = some_area
\tyear = 1836
\tcost = 3600
\tfactory_input = -0.01
\ttax_eff = 5
\trgo_goods_output = {
\t\tiron = 0.25
\t\tcoal = 0.1
\t}
\tartillery = {
\t\tattack = 0.5
\t\tdefence = 2
\t}
\tactivate_building = lumber_mill
\tai_chance = {
\t\tfactor = 2
\t\tmodifier = {
\t\t\tfactor = 1.5
\t\t\tbig_producer = coal
\t\t}
\t}
}
second_tech = {
\tarea = some_area
\tyear = 1900
\tcost = 7200
}
"""

MOD_INVENTION_FIXTURE = """test_invention = {
\tlimit = { test_tech_alpha = 1 }
\tchance = {
\t\tbase = 2
\t}
\teffect = {
\t\tfactory_throughput = 0.05
\t\tinfantry = {
\t\t\tdefence = 1
\t\t}
\t\tfactory_goods_output = {
\t\t\tfabric = 0.05
\t\t}
\t}
}
effectless_invention = {
\tlimit = { test_tech_alpha = 1 }
}
odd_rebel = {
\tlimit = { test_tech_alpha = 1 }
\teffect = {
\t\trebel_org_gain = {
\t\t\tfaction = all
\t\t\tvalue = -0.25
\t\t}
\t}
}
"""

MOD_ISSUES_FIXTURE = """economic_reforms = {
\tland_reform = {
\t\tno_land_reform = {
\t\t\tglobal_pop_militancy_modifier = -0.005
\t\t}
\t\tyes_land_reform = {
\t\t\tfarm_rgo_eff = 0.25
\t\t\ttechnology_cost = 8000
\t\t\ton_execute = {
\t\t\t\teffect = {
\t\t\t\t\tany_pop = {
\t\t\t\t\t\tmilitancy = 1
\t\t\t\t\t}
\t\t\t\t}
\t\t\t}
\t\t}
\t}
}
military_reforms = {
\tarmy_schools = {
\t\tno_army_schools = {
\t\t\tglobal_pop_militancy_modifier = -0.005
\t\t}
\t}
}
"""

MOD_EXPECTED_NAMES = {
    "factory_input",
    "tax_eff",
    "rgo_goods_output_iron",
    "rgo_goods_output_coal",
    "artillery_attack",
    "artillery_defence",
    "factory_throughput",
    "infantry_defence",
    "factory_goods_output_fabric",
    "rebel_org_gain_all",
    "global_pop_militancy_modifier",
    "farm_rgo_eff",
    "technology_cost",
}

# A synthetic save whose techs and reform levels all exist in the
# MOD_* fixtures above.
MOD_SAVE = """date="1836.1.2"
player="TST"
TST=
{
\ttechnology=
\t{
\t\ttest_tech_alpha={1 0.000}
\t}
\tland_reform=yes_land_reform
\tarmy_schools=no_army_schools
}
"""


def make_modifiers_game_dir(root: Path) -> Path:
    game_dir = root / "game"
    (game_dir / "technologies").mkdir(parents=True)
    (game_dir / "inventions").mkdir(parents=True)
    (game_dir / "common").mkdir(parents=True)
    (game_dir / "technologies" / "t_tech.txt").write_text(
        MOD_TECH_FIXTURE, encoding="utf-8"
    )
    (game_dir / "inventions" / "i_inv.txt").write_text(
        MOD_INVENTION_FIXTURE, encoding="utf-8"
    )
    (game_dir / "common" / "issues.txt").write_text(
        MOD_ISSUES_FIXTURE, encoding="utf-8"
    )
    return game_dir


# A synthetic game install for the per-goods matrices setup task: techs
# and inventions with per-good values alongside scalars, unit blocks and
# trigger vocabulary; reforms with scalar-only levels (as in vanilla,
# where westernisation has no per-good effects).
PGO_TECH_FIXTURE = """#tech_group_one
first_tech = {
\tarea = some_area
\tyear = 1836
\tcost = 3600
\tfactory_input = -0.01
\trgo_goods_output = {
\t\tiron = 0.25
\t}
\trgo_size = {
\t\tcoal = 0.2
\t}
\tartillery = {
\t\tdefence = 1
\t}
\tai_chance = {
\t\tfactor = 2
\t}
}
second_tech = {
\tarea = some_area
\tyear = 1900
\tcost = 7200
\tfactory_goods_output = {
\t\tfabric = 0.05
\t}
}
"""

PGO_INVENTION_FIXTURE = """first_invention = {
\tlimit = { first_tech = 1 }
\tchance = {
\t\tbase = 2
\t}
\teffect = {
\t\tfactory_throughput = 0.05
\t\tfactory_goods_throughput = {
\t\t\tfabric = 0.05
\t\t}
\t\tinfantry = {
\t\t\tdefence = 1
\t\t}
\t}
}
effectless_invention = {
\tlimit = { first_tech = 1 }
}
"""

PGO_ISSUES_FIXTURE = """economic_reforms = {
\tland_reform = {
\t\tno_land_reform = {
\t\t\tglobal_pop_militancy_modifier = -0.005
\t\t}
\t\tyes_land_reform = {
\t\t\tfarm_rgo_eff = 0.25
\t\t\ton_execute = {
\t\t\t\teffect = {
\t\t\t\t\tany_pop = {
\t\t\t\t\t\tmilitancy = 1
\t\t\t\t\t}
\t\t\t\t}
\t\t\t}
\t\t}
\t}
}
military_reforms = {
\tarmy_schools = {
\t\tno_army_schools = {
\t\t\tglobal_pop_militancy_modifier = -0.005
\t\t}
\t\tyes_army_schools = {
\t\t\tland_organisation = 0.1
\t\t}
\t}
}
"""

# A synthetic save whose techs and reform levels all exist in the
# PGO_* fixtures above.
PGO_SAVE = """date="1836.1.2"
player="TST"
TST=
{
\ttechnology=
\t{
\t\tfirst_tech={1 0.000}
\t}
\tland_reform=yes_land_reform
\tarmy_schools=no_army_schools
}
"""


def make_per_goods_game_dir(root: Path) -> Path:
    game_dir = root / "game"
    (game_dir / "technologies").mkdir(parents=True)
    (game_dir / "inventions").mkdir(parents=True)
    (game_dir / "common").mkdir(parents=True)
    (game_dir / "technologies" / "army_tech.txt").write_text(
        PGO_TECH_FIXTURE, encoding="utf-8"
    )
    (game_dir / "inventions" / "army_inventions.txt").write_text(
        PGO_INVENTION_FIXTURE, encoding="utf-8"
    )
    (game_dir / "common" / "issues.txt").write_text(
        PGO_ISSUES_FIXTURE, encoding="utf-8"
    )
    return game_dir


# A synthetic game install for the small-category matrix tasks: one tech
# and one invention granting a colonial, prestige, population, diplomacy
# and other value each, plus effect-less entries and trigger vocabulary
# that must be ignored. Reforms grant none of these (as in vanilla).
CAT_TECH_FIXTURE = """#tech_group_one
col_tech = {
\tarea = some_area
\tyear = 1836
\tcost = 3600
\tcolonial_points = 100
\tprestige = 0.05
\tmax_national_focus = 1
\tinfluence = 0.1
\tunit = 1
\tai_chance = {
\t\tfactor = 2
\t}
}
plain_tech = {
\tarea = some_area
\tyear = 1900
\tcost = 7200
}
"""

CAT_INVENTION_FIXTURE = """col_invention = {
\tlimit = { col_tech = 1 }
\tchance = {
\t\tbase = 2
\t}
\teffect = {
\t\tcolonial_prestige = 0.1
\t\tpermanent_prestige = 1
\t\tpop_growth = 0.0002
\t\tdiplomatic_points = 0.25
\t}
}
effectless_invention = {
\tlimit = { col_tech = 1 }
}
"""

CAT_ISSUES_FIXTURE = """economic_reforms = {
\tland_reform = {
\t\tno_land_reform = {
\t\t\tglobal_pop_militancy_modifier = -0.005
\t\t}
\t\tyes_land_reform = {
\t\t\tfarm_rgo_eff = 0.25
\t\t\ton_execute = {
\t\t\t\teffect = {
\t\t\t\t\tany_pop = {
\t\t\t\t\t\tmilitancy = 1
\t\t\t\t\t}
\t\t\t\t}
\t\t\t}
\t\t}
\t}
}
military_reforms = {
\tarmy_schools = {
\t\tno_army_schools = {
\t\t\tglobal_pop_militancy_modifier = -0.005
\t\t}
\t\tyes_army_schools = {
\t\t\tland_organisation = 0.1
\t\t}
\t}
}
"""

# A synthetic save whose techs and reform levels all exist in the
# CAT_* fixtures above.
CAT_SAVE = """date="1836.1.2"
player="TST"
TST=
{
\ttechnology=
\t{
\t\tcol_tech={1 0.000}
\t}
\tland_reform=yes_land_reform
\tarmy_schools=no_army_schools
}
"""


def make_category_game_dir(root: Path) -> Path:
    game_dir = root / "game"
    (game_dir / "technologies").mkdir(parents=True)
    (game_dir / "inventions").mkdir(parents=True)
    (game_dir / "common").mkdir(parents=True)
    (game_dir / "technologies" / "army_tech.txt").write_text(
        CAT_TECH_FIXTURE, encoding="utf-8"
    )
    (game_dir / "inventions" / "army_inventions.txt").write_text(
        CAT_INVENTION_FIXTURE, encoding="utf-8"
    )
    (game_dir / "common" / "issues.txt").write_text(
        CAT_ISSUES_FIXTURE, encoding="utf-8"
    )
    return game_dir


# A synthetic game install for the research/economic matrix tasks: techs
# and inventions granting research and economic values each, plus
# effect-less entries and trigger vocabulary that must be ignored.
# Reforms grant research values (technology_cost) but no economic ones
# beyond the shared scalar set, mirroring the vanilla split.
RES_TECH_FIXTURE = """#tech_group_one
res_tech = {
\tarea = some_area
\tyear = 1836
\tcost = 3600
\ttax_eff = 3
\tfactory_input = -0.01
\tfarm_rgo_eff = 0.25
\tincrease_research = 0.5
\teducation_efficiency = 0.1
\tai_chance = {
\t\tfactor = 2
\t}
}
plain_tech = {
\tarea = some_area
\tyear = 1900
\tcost = 7200
}
"""

RES_INVENTION_FIXTURE = """res_invention = {
\tlimit = { res_tech = 1 }
\tchance = {
\t\tbase = 2
\t}
\teffect = {
\t\ttax_eff = 1
\t\trgo_output = 0.05
\t\tplurality = 0.1
\t\teducation_efficiency_modifier = 0.15
\t}
}
effectless_invention = {
\tlimit = { res_tech = 1 }
}
"""

RES_ISSUES_FIXTURE = """economic_reforms = {
\tland_reform = {
\t\tno_land_reform = {
\t\t\tglobal_pop_militancy_modifier = -0.005
\t\t}
\t\tyes_land_reform = {
\t\t\ttechnology_cost = 8000
\t\t\tfarm_rgo_eff = 0.25
\t\t\ton_execute = {
\t\t\t\teffect = {
\t\t\t\t\tany_pop = {
\t\t\t\t\t\tmilitancy = 1
\t\t\t\t\t}
\t\t\t\t}
\t\t\t}
\t\t}
\t}
}
military_reforms = {
\tarmy_schools = {
\t\tno_army_schools = {
\t\t\tglobal_pop_militancy_modifier = -0.005
\t\t}
\t\tyes_army_schools = {
\t\t\tland_organisation = 0.1
\t\t}
\t}
}
"""

# A synthetic save whose techs and reform levels all exist in the
# RES_* fixtures above.
RES_SAVE = """date="1836.1.2"
player="TST"
TST=
{
\ttechnology=
\t{
\t\tres_tech={1 0.000}
\t}
\tland_reform=yes_land_reform
\tarmy_schools=no_army_schools
}
"""


def make_research_economic_game_dir(root: Path) -> Path:
    game_dir = root / "game"
    (game_dir / "technologies").mkdir(parents=True)
    (game_dir / "inventions").mkdir(parents=True)
    (game_dir / "common").mkdir(parents=True)
    (game_dir / "technologies" / "army_tech.txt").write_text(
        RES_TECH_FIXTURE, encoding="utf-8"
    )
    (game_dir / "inventions" / "army_inventions.txt").write_text(
        RES_INVENTION_FIXTURE, encoding="utf-8"
    )
    (game_dir / "common" / "issues.txt").write_text(
        RES_ISSUES_FIXTURE, encoding="utf-8"
    )
    return game_dir


# A synthetic game install for the per-unit matrices task: a tech with
# land-unit blocks, an invention with land and naval blocks, and reforms
# with scalar-only levels (as in vanilla, where westernisation grants no
# per-unit bonuses).
PU_TECH_FIXTURE = """#tech_group_one
pu_tech = {
\tarea = some_area
\tyear = 1836
\tcost = 3600
\tinfantry = {
\t\tattack = 0.5
\t\tdefence = 1
\t}
\tplane = {
\t\treconnaissance = 2
\t}
\tmorale = 0.5
\tai_chance = {
\t\tfactor = 2
\t}
}
plain_tech = {
\tarea = some_area
\tyear = 1900
\tcost = 7200
}
"""

PU_INVENTION_FIXTURE = """pu_invention = {
\tlimit = { pu_tech = 1 }
\tchance = {
\t\tbase = 2
\t}
\teffect = {
\t\tinfantry = {
\t\t\tdefence = 2
\t\t}
\t\tcruiser = {
\t\t\ttorpedo_attack = 8
\t\t}
\t}
}
effectless_invention = {
\tlimit = { pu_tech = 1 }
}
"""

PU_ISSUES_FIXTURE = """economic_reforms = {
\tland_reform = {
\t\tno_land_reform = {
\t\t\tglobal_pop_militancy_modifier = -0.005
\t\t}
\t\tyes_land_reform = {
\t\t\tfarm_rgo_eff = 0.25
\t\t\ton_execute = {
\t\t\t\teffect = {
\t\t\t\t\tany_pop = {
\t\t\t\t\t\tmilitancy = 1
\t\t\t\t\t}
\t\t\t\t}
\t\t\t}
\t\t}
\t}
}
military_reforms = {
\tarmy_schools = {
\t\tno_army_schools = {
\t\t\tglobal_pop_militancy_modifier = -0.005
\t\t}
\t\tyes_army_schools = {
\t\t\tland_organisation = 0.1
\t\t}
\t}
}
"""

# A synthetic save whose techs and reform levels all exist in the
# PU_* fixtures above.
PU_SAVE = """date="1836.1.2"
player="TST"
TST=
{
\ttechnology=
\t{
\t\tpu_tech={1 0.000}
\t}
\tland_reform=yes_land_reform
\tarmy_schools=no_army_schools
}
"""


def make_per_unit_game_dir(root: Path) -> Path:
    game_dir = root / "game"
    (game_dir / "technologies").mkdir(parents=True)
    (game_dir / "inventions").mkdir(parents=True)
    (game_dir / "common").mkdir(parents=True)
    (game_dir / "technologies" / "army_tech.txt").write_text(
        PU_TECH_FIXTURE, encoding="utf-8"
    )
    (game_dir / "inventions" / "navy_inventions.txt").write_text(
        PU_INVENTION_FIXTURE, encoding="utf-8"
    )
    (game_dir / "common" / "issues.txt").write_text(
        PU_ISSUES_FIXTURE, encoding="utf-8"
    )
    return game_dir


# A synthetic game install for the military matrices task: a tech and an
# invention granting military scalars and base composites, plus
# effect-less entries and trigger vocabulary that must be ignored.
# Reforms grant military scalars (land_organisation), mirroring vanilla.
MIL_TECH_FIXTURE = """#tech_group_one
mil_tech = {
\tarea = some_area
\tyear = 1836
\tcost = 3600
\tmorale = 0.25
\tmilitary_tactics = 0.25
\tarmy_base = {
\t\tsupply_consumption = 0.05
\t}
\tai_chance = {
\t\tfactor = 2
\t}
}
plain_tech = {
\tarea = some_area
\tyear = 1900
\tcost = 7200
}
"""

MIL_INVENTION_FIXTURE = """mil_invention = {
\tlimit = { mil_tech = 1 }
\tchance = {
\t\tbase = 2
\t}
\teffect = {
\t\tnavy_base = {
\t\t\tmaximum_speed = 1
\t\t}
\t\twar_exhaustion = -0.1
\t}
}
effectless_invention = {
\tlimit = { mil_tech = 1 }
}
"""

MIL_ISSUES_FIXTURE = """economic_reforms = {
\tland_reform = {
\t\tno_land_reform = {
\t\t\tglobal_pop_militancy_modifier = -0.005
\t\t}
\t\tyes_land_reform = {
\t\t\tfarm_rgo_eff = 0.25
\t\t\ton_execute = {
\t\t\t\teffect = {
\t\t\t\t\tany_pop = {
\t\t\t\t\t\tmilitancy = 1
\t\t\t\t\t}
\t\t\t\t}
\t\t\t}
\t\t}
\t}
}
military_reforms = {
\tarmy_schools = {
\t\tno_army_schools = {
\t\t\tglobal_pop_militancy_modifier = -0.005
\t\t}
\t\tyes_army_schools = {
\t\t\tland_organisation = 0.1
\t\t}
\t}
}
"""

# A synthetic save whose techs and reform levels all exist in the
# MIL_* fixtures above.
MIL_SAVE = """date="1836.1.2"
player="TST"
TST=
{
\ttechnology=
\t{
\t\tmil_tech={1 0.000}
\t}
\tland_reform=yes_land_reform
\tarmy_schools=yes_army_schools
}
"""


def make_military_game_dir(root: Path) -> Path:
    game_dir = root / "game"
    (game_dir / "technologies").mkdir(parents=True)
    (game_dir / "inventions").mkdir(parents=True)
    (game_dir / "common").mkdir(parents=True)
    (game_dir / "technologies" / "army_tech.txt").write_text(
        MIL_TECH_FIXTURE, encoding="utf-8"
    )
    (game_dir / "inventions" / "navy_inventions.txt").write_text(
        MIL_INVENTION_FIXTURE, encoding="utf-8"
    )
    (game_dir / "common" / "issues.txt").write_text(
        MIL_ISSUES_FIXTURE, encoding="utf-8"
    )
    return game_dir
