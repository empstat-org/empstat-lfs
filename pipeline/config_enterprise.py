"""
Configuration for the ENTERPRISE / ESTABLISHMENT DATA Coverage Index.

Same shape as config.py / config_admin.py, but tuned for company-level labour
statistics — the series that come from establishment / enterprise surveys,
economic & establishment censuses, and register / social-security sources
(everything that is collected from the *employer/business* rather than from
households).

Three criteria (coverage + frequency + recency), because establishment sources
are often high-frequency (monthly / quarterly earnings and employees). Pending
is disabled (no per-country NSO release registry for this index).

Run:  python fetch_and_rank.py --config config_enterprise --out ../web/data

SOURCE FILTER — "all establishment / enterprise / register sources"
-------------------------------------------------------------------
Per the design decision, this index counts *every* source EXCEPT household /
labour-force surveys, population censuses and modelled / official estimates.
That is expressed by leaving HOUSEHOLD_SURVEY_KEYWORDS **empty** — the pipeline
(fetch_and_rank.is_household_source) then includes any source that is not in
SOURCE_EXCLUDE_KEYWORDS. Note that ECONOMIC and ESTABLISHMENT censuses are kept
(they are business-level); only POPULATION censuses are excluded.
"""

from config import ILOSTAT, REGIONS  # reuse the same ILOSTAT endpoints + region map

INDEX_NAME = "Enterprise / Establishment Data Coverage Index"
ENABLE_PENDING = False

# ------------------------------------------------------------------------------
# Company-level / establishment indicator set.
# Tier 1 = headline establishment statistics; Tier 2 = extended.
# The same indicator can be collected from several source types — the SOURCE
# FILTER below is what restricts each observation to a business-level source.
# ------------------------------------------------------------------------------
KEY_INDICATORS = [
    # ---- Tier 1 : headline establishment / enterprise statistics ------------
    {"code": "EES_TEES_SEX_AGE_NB",     "label": "Employees",                              "tier": 1, "weight": 2.0, "periodicities": ["M", "Q", "A"]},
    {"code": "EMP_TEMP_SEX_ECO_NB",     "label": "Employment by economic activity",        "tier": 1, "weight": 2.0, "periodicities": ["M", "Q", "A"]},
    {"code": "EAR_EMTA_SEX_ECO_CUR_NB", "label": "Average monthly earnings of employees",   "tier": 1, "weight": 1.5, "periodicities": ["Q", "A"]},
    {"code": "EAR_EHRA_SEX_ECO_CUR_NB", "label": "Average hourly earnings of employees",    "tier": 1, "weight": 1.5, "periodicities": ["Q", "A"]},
    {"code": "HOW_TEMP_SEX_ECO_NB",     "label": "Mean weekly hours actually worked",       "tier": 1, "weight": 1.5, "periodicities": ["M", "Q", "A"]},

    # ---- Tier 2 : extended -------------------------------------------------
    {"code": "EES_TEES_SEX_AGE_ECO_NB", "label": "Employees by economic activity",          "tier": 2, "weight": 1.0, "periodicities": ["Q", "A"]},
    {"code": "EES_TEES_SEX_AGE_INS_NB", "label": "Employees by public / private sector",     "tier": 2, "weight": 1.0, "periodicities": ["Q", "A"]},
    {"code": "LAC_XEES_ECO_CUR_NB",     "label": "Average hourly labour cost per employee",  "tier": 2, "weight": 1.0, "periodicities": ["A"]},
    {"code": "EMP_TEMP_SEX_STE_NB",     "label": "Employment by status in employment",       "tier": 2, "weight": 1.0, "periodicities": ["Q", "A"]},
]

# ------------------------------------------------------------------------------
# SOURCE FILTER — all business-level sources (see module docstring).
# HOUSEHOLD_SURVEY_KEYWORDS is intentionally EMPTY: the pipeline then includes
# every source not matched by SOURCE_EXCLUDE_KEYWORDS.
# ------------------------------------------------------------------------------
HOUSEHOLD_SURVEY_KEYWORDS = []   # empty => include ALL non-excluded sources

SOURCE_EXCLUDE_KEYWORDS = [
    # household / labour-force surveys (belong to the LFS index)
    "labour force survey",
    "household survey",
    "household income",
    "living conditions",
    "living standards",
    "socio-economic",
    "socioeconomic",
    "integrated household",
    "continuous household",
    "multipurpose household",
    # population censuses (belong to the Census index) — but NOT economic /
    # establishment censuses, which are business-level and kept.
    "population census",
    "population and housing census",
    "housing census",
    # never count modelled / official estimates — national sources only
    "modelled",
    "modeled",
    "official estimate",
]

# ------------------------------------------------------------------------------
# SCORING — three criteria, same shape as the LFS and Admin indices.
# ------------------------------------------------------------------------------
SCORING = {
    "weights": {"coverage": 1.0, "frequency": 1.0, "recency": 1.0},
    "coverage": {"coverage_window_years": 15},
    "frequency": {
        "periodicity_points": {"M": 100, "Q": 85, "A": 60, "irregular": 30},
        "regularity_window_years": 10,
    },
    "recency": {"full_marks_max_age": 1, "zero_marks_min_age": 12},
}
