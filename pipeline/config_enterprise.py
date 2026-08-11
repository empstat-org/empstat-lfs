"""
Configuration for the ENTERPRISE / ESTABLISHMENT DATA Coverage Index.

Same shape as config.py / config_admin.py, but tuned for company-level labour
statistics — the series that come from establishment / enterprise surveys,
economic & establishment censuses, and establishment / business registers
(everything that is collected from the *employer/business* rather than from
households). Social-security / social-insurance records are treated as an
administrative source and excluded (they belong to the Admin index).

Three criteria (coverage + frequency + recency), because establishment sources
are often high-frequency (monthly / quarterly earnings and employees). Pending
is disabled (no per-country NSO release registry for this index).

Run:  python fetch_and_rank.py --config config_enterprise --out ../web/data

SOURCE FILTER — business-level sources only, by ILOSTAT source-type CODE
------------------------------------------------------------------------
ILOSTAT labels every source as "CODE - Description" (e.g. "ES - Labour Cost
Survey", "EC - Economic or Establishment Census", "ADM-EBR - Businesses
register", "LFS - ...", "HIES - ...", "ADM - ...", "PC - ..."). This index keeps
ONLY the business-level codes via SOURCE_INCLUDE_PREFIXES:
    ES      = establishment / enterprise surveys
    EC      = economic / establishment censuses
    ADM-EBR = establishment / business registers
Everything else is excluded — household & labour-force surveys (LFS, HIES, HS),
general administrative & insurance records (ADM, ADM-IR, ADM-EOR), population
censuses (PC), national accounts (SNA) and official estimates (OE). Filtering on
the code is language-independent and far more reliable than free-text keywords.
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
# SOURCE FILTER — business-level sources only, selected by ILOSTAT CODE prefix.
# SOURCE_INCLUDE_PREFIXES (below) is the authoritative filter: a source is kept
# iff its "CODE - ..." prefix is in that list. The keyword lists here only apply
# to any (rare) source label that has no recognised code prefix.
# ------------------------------------------------------------------------------
HOUSEHOLD_SURVEY_KEYWORDS = []   # empty => include un-prefixed non-excluded sources

# Keep ONLY these ILOSTAT source-type codes: establishment surveys (ES),
# economic / establishment censuses (EC), and establishment / business registers
# (ADM-EBR). This drops LFS/HIES/HS household & labour-force surveys, ADM/ADM-IR
# general administrative & insurance records, ADM-EOR, PC population censuses,
# SNA national accounts and OE official estimates.
SOURCE_INCLUDE_PREFIXES = ["ES", "EC", "ADM-EBR"]

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
    # social-security / social-insurance registers (belong to the Admin index).
    # Establishment / business registers and economic censuses are still kept;
    # only social-security-based records are excluded here.
    "social security",
    "social-security",
    "social insurance",
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
