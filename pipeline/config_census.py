"""
Configuration for the CENSUS Coverage Index.

Same shape as config.py, but tuned for population censuses:
  - source filter targets population (and housing) censuses, not surveys
  - a census-appropriate indicator subset (structural stocks a census produces)
  - TWO criteria only: coverage + recency (no frequency — censuses are ~decennial)
  - a longer, decennial recency window
  - pending disabled (there's no per-country NSO census-release registry)

Run:  python fetch_and_rank.py --config config_census --out ../web/census/data
"""

from config import ILOSTAT, REGIONS  # reuse the same ILOSTAT endpoints + region map

INDEX_NAME = "Population Census"
ENABLE_PENDING = False

# ------------------------------------------------------------------------------
# Census-appropriate indicators (structural stocks a population census produces).
# Uses the same indicator set as the LFS index (so the two are directly
# comparable). Note some of these (hours, earnings, informality, LU4) are rarely
# produced from a census, so those will simply show low coverage here.
# ------------------------------------------------------------------------------
KEY_INDICATORS = [
    # Tier 1 — headline
    {"code": "POP_XWAP_SEX_AGE_NB",     "label": "Working-age population",          "tier": 1, "weight": 2.0, "periodicities": ["A"]},
    {"code": "EAP_TEAP_SEX_AGE_NB",     "label": "Labour force",                    "tier": 1, "weight": 2.0, "periodicities": ["A"]},
    {"code": "EAP_DWAP_SEX_AGE_RT",     "label": "Labour force participation rate", "tier": 1, "weight": 2.0, "periodicities": ["A"]},
    {"code": "EMP_TEMP_SEX_AGE_NB",     "label": "Employment by sex and age",       "tier": 1, "weight": 2.0, "periodicities": ["A"]},
    {"code": "EMP_DWAP_SEX_AGE_RT",     "label": "Employment-to-population ratio",  "tier": 1, "weight": 2.0, "periodicities": ["A"]},
    {"code": "UNE_TUNE_SEX_AGE_NB",     "label": "Unemployment",                    "tier": 1, "weight": 2.0, "periodicities": ["A"]},
    {"code": "UNE_DEAP_SEX_AGE_RT",     "label": "Unemployment rate",               "tier": 1, "weight": 2.0, "periodicities": ["A"]},
    {"code": "LUU_XLU4_SEX_AGE_RT",     "label": "Composite measure of labour underutilization (LU4)", "tier": 1, "weight": 1.5, "periodicities": ["A"]},
    {"code": "EMP_TEMP_SEX_STE_NB",     "label": "Employment by status in employment", "tier": 1, "weight": 1.5, "periodicities": ["A"]},
    {"code": "EMP_TEMP_SEX_OCU_NB",     "label": "Employment by occupation",        "tier": 1, "weight": 1.5, "periodicities": ["A"]},
    {"code": "EMP_TEMP_SEX_ECO_NB",     "label": "Employment by economic activity", "tier": 1, "weight": 1.5, "periodicities": ["A"]},
    {"code": "EMP_NIFL_SEX_RT",         "label": "Informal employment rate",        "tier": 1, "weight": 1.5, "periodicities": ["A"]},
    {"code": "HOW_TEMP_SEX_ECO_NB",     "label": "Mean weekly hours actually worked", "tier": 1, "weight": 1.5, "periodicities": ["A"]},
    {"code": "EAR_EMTA_SEX_ECO_CUR_NB", "label": "Average monthly earnings of employees", "tier": 1, "weight": 1.5, "periodicities": ["A"]},

    # Tier 2 — extended / disaggregated
    {"code": "UNE_TUNE_SEX_AGE_DUR_NB",   "label": "Unemployment by duration",                 "tier": 2, "weight": 1.0, "periodicities": ["A"]},
    # Fallback indicator: use citizenship if available, otherwise place of birth.
    {"code": "EMP_TEMP_SEX_AGE_CCT_NB",
     "codes": ["EMP_TEMP_SEX_AGE_CCT_NB", "EMP_TEMP_SEX_AGE_CBR_NB"],
     "code_labels": {"EMP_TEMP_SEX_AGE_CCT_NB": "citizenship", "EMP_TEMP_SEX_AGE_CBR_NB": "place of birth"},
     "label": "Employment by citizenship or place of birth", "tier": 2, "weight": 1.0, "periodicities": ["A"]},
    {"code": "EMP_TEMP_SEX_GEO_NB",       "label": "Employment by urban / rural",              "tier": 2, "weight": 1.0, "periodicities": ["A"]},
    {"code": "EMP_TEMP_SEX_AGE_DSB_NB",   "label": "Employment by disability",                 "tier": 2, "weight": 1.0, "periodicities": ["A"]},
    {"code": "EMP_TEMP_SEX_EDU_NB",       "label": "Employment by education level",            "tier": 2, "weight": 1.0, "periodicities": ["A"]},
]

# ------------------------------------------------------------------------------
# SOURCE FILTER — population censuses only.
# (Variable names mirror config.py so the pipeline needs no special-casing;
#  here they mean "sources to INCLUDE / EXCLUDE" for the census index.)
# ------------------------------------------------------------------------------
HOUSEHOLD_SURVEY_KEYWORDS = [   # = sources to INCLUDE for this index
    "population census",
    "population and housing census",
    "housing census",
    "census",
]
SOURCE_EXCLUDE_KEYWORDS = [
    "agricultural census",
    "agriculture census",
    "economic census",
    "establishment census",
    "modelled",              # exclude ILO modelled estimates — national sources only
    "modeled",
    "official estimate",
]

# ------------------------------------------------------------------------------
# SCORING — coverage + recency only (no frequency).
# ------------------------------------------------------------------------------
SCORING = {
    "weights": {
        "coverage": 1.0,   # share of census indicators with data
        "recency":  1.0,   # how recent the latest census is
    },
    "coverage": {
        # a census within this many years counts the indicator as "covered"
        "coverage_window_years": 15,
    },
    # decennial decay: a census <=3 years old is current; ~20+ years old scores 0
    "recency": {
        "full_marks_max_age": 3,
        "zero_marks_min_age": 20,
    },
}
