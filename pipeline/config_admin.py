"""
Configuration for the ADMINISTRATIVE DATA Coverage Index.

Same three criteria as the LFS index (coverage + frequency + recency), because
administrative sources can be high-frequency (e.g. monthly registered
unemployment). Pending is disabled.

Run:  python fetch_and_rank.py --config config_admin --out ../web/admin/data

NOTE: the indicator codes below are best-effort — verify them against ILOSTAT's
indicator list (https://rplumber.ilo.org/metadata/toc/indicator/?lang=en) before
a live run, and adjust the source keywords to match how ILOSTAT labels
administrative sources for your priority countries.
"""

from config import ILOSTAT, REGIONS  # reuse the same ILOSTAT endpoints + region map

INDEX_NAME = "Administrative Data Coverage Index"
ENABLE_PENDING = False

# ------------------------------------------------------------------------------
# Administrative-source labour indicators (register / social-security / labour
# inspection / industrial-relations based).
# ------------------------------------------------------------------------------
KEY_INDICATORS = [
    # Tier 1 — core administrative series
    {"code": "UNE_2UNE_SEX_AGE_NB",     "label": "Registered unemployment",                 "tier": 1, "weight": 2.0, "periodicities": ["M", "Q", "A"]},
    {"code": "EMP_TEMP_SEX_ECO_NB",     "label": "Employment by economic activity (register/SSA)", "tier": 1, "weight": 1.5, "periodicities": ["Q", "A"]},
    {"code": "EAR_4MTH_SEX_ECO_CUR_NB", "label": "Average monthly earnings of employees",    "tier": 1, "weight": 1.5, "periodicities": ["M", "Q", "A"]},
    {"code": "INJ_FATL_ECO_RT",         "label": "Occupational injuries, fatal (rate)",      "tier": 1, "weight": 1.5, "periodicities": ["A"]},
    {"code": "INJ_NFTL_ECO_RT",         "label": "Occupational injuries, non-fatal (rate)",  "tier": 1, "weight": 1.5, "periodicities": ["A"]},

    # Tier 2 — extended administrative series
    {"code": "ILR_STRK_ECO_NB",         "label": "Days not worked due to strikes/lockouts",  "tier": 2, "weight": 1.0, "periodicities": ["A"]},
    {"code": "LAI_INSP_NOC_NB",         "label": "Number of labour inspectors",              "tier": 2, "weight": 1.0, "periodicities": ["A"]},
    {"code": "EMP_TEMP_SEX_STE_NB",     "label": "Employees (register/social security)",     "tier": 2, "weight": 1.0, "periodicities": ["Q", "A"]},
    {"code": "HOW_TEMP_SEX_ECO_NB",     "label": "Hours of work (establishment/register)",   "tier": 2, "weight": 1.0, "periodicities": ["Q", "A"]},
]

# ------------------------------------------------------------------------------
# SOURCE FILTER — administrative records (variable names mirror config.py).
# ------------------------------------------------------------------------------
HOUSEHOLD_SURVEY_KEYWORDS = [   # = sources to INCLUDE for this index
    "administrative",
    "administrative records",
    "registered",
    "register",
    "social security",
    "employment office",
    "employment service",
    "labour inspection",
    "insurance records",
]
SOURCE_EXCLUDE_KEYWORDS = [
    "labour force survey",
    "household survey",
    "population census",
]

# ------------------------------------------------------------------------------
# SCORING — three criteria, same shape as the LFS index.
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
