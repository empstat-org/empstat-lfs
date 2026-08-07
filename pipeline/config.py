"""
Configuration for the ILOSTAT Labour Market Information (LMI) Ranking platform.

Everything you are likely to want to *refine later* lives in this one file:
  - which indicators count as "key indicators"        -> KEY_INDICATORS
  - what counts as a "household survey" source         -> HOUSEHOLD_SURVEY_KEYWORDS
  - how the score is computed and weighted             -> SCORING
  - which time window is considered "recent"           -> SCORING["recency"]

The pipeline (fetch_and_rank.py) reads this file, pulls the matching data from
ILOSTAT, scores every country, and writes ../web/data/rankings.js (+ rankings.json).
The website reads that file. Change anything here, re-run the pipeline, refresh
the site.

--------------------------------------------------------------------------------
ILOSTAT indicator codes
--------------------------------------------------------------------------------
ILOSTAT identifies each series by an indicator code, e.g.

    UNE_DEAP_SEX_AGE_RT   = Unemployment rate, by sex and age
    EMP_TEMP_SEX_OCU_NB   = Employment by sex and occupation (ISCO)

The last token encodes periodicity in the *bulk download* file id:
    ..._A  = annual        ..._Q = quarterly       ..._M = monthly

For coverage we don't care about the periodicity suffix (we want "does the
country measure this at all, from a household survey"), so each entry below lists
the base code and the periodicities ILOSTAT publishes it in. The pipeline checks
all listed periodicities and keeps the best (most frequent) one it finds.

Full, searchable list of codes:
    https://rplumber.ilo.org/metadata/toc/indicator/?lang=en
"""

# ------------------------------------------------------------------------------
# KEY INDICATORS  (the "extended" set)
# ------------------------------------------------------------------------------
# tier 1 = headline indicators every mature LFS should produce
# tier 2 = extended / disaggregated indicators that mark a more advanced system
#
# `weight` lets you make some indicators count more toward the coverage score.
# Tier-1 default weight 2.0, tier-2 default weight 1.0. Adjust freely.
#
# `periodicities` = the bulk-download suffixes to look for, best (most frequent)
# first. The pipeline records the most frequent one actually found per country.

KEY_INDICATORS = [
    # ---- Tier 1 : headline labour force indicators --------------------------
    {"code": "POP_XWAP_SEX_AGE_NB",     "label": "Working-age population",          "tier": 1, "weight": 2.0, "periodicities": ["Q", "A"]},
    {"code": "EAP_TEAP_SEX_AGE_NB",     "label": "Labour force",                    "tier": 1, "weight": 2.0, "periodicities": ["M", "Q", "A"]},
    {"code": "EAP_DWAP_SEX_AGE_RT",     "label": "Labour force participation rate", "tier": 1, "weight": 2.0, "periodicities": ["M", "Q", "A"]},
    {"code": "EMP_TEMP_SEX_AGE_NB",     "label": "Employment by sex and age",       "tier": 1, "weight": 2.0, "periodicities": ["M", "Q", "A"]},
    {"code": "EMP_DWAP_SEX_AGE_RT",     "label": "Employment-to-population ratio",  "tier": 1, "weight": 2.0, "periodicities": ["M", "Q", "A"]},
    {"code": "UNE_TUNE_SEX_AGE_NB",     "label": "Unemployment",                    "tier": 1, "weight": 2.0, "periodicities": ["M", "Q", "A"]},
    {"code": "UNE_DEAP_SEX_AGE_RT",     "label": "Unemployment rate",               "tier": 1, "weight": 2.0, "periodicities": ["M", "Q", "A"]},
    {"code": "LUU_DLU4_SEX_AGE_RT",     "label": "Composite measure of labour underutilization (LU4)", "tier": 1, "weight": 1.5, "periodicities": ["Q", "A"]},
    {"code": "EMP_TEMP_SEX_STE_NB",     "label": "Employment by status in employment", "tier": 1, "weight": 1.5, "periodicities": ["Q", "A"]},
    {"code": "EMP_TEMP_SEX_OCU_NB",     "label": "Employment by occupation",        "tier": 1, "weight": 1.5, "periodicities": ["Q", "A"]},
    {"code": "EMP_TEMP_SEX_ECO_NB",     "label": "Employment by economic activity", "tier": 1, "weight": 1.5, "periodicities": ["Q", "A"]},
    {"code": "EMP_NIFL_SEX_RT",         "label": "Informal employment rate",        "tier": 1, "weight": 1.5, "periodicities": ["A"]},
    {"code": "HOW_TEMP_SEX_ECO_NB",     "label": "Mean weekly hours actually worked", "tier": 1, "weight": 1.5, "periodicities": ["Q", "A"]},
    {"code": "EAR_4MTH_SEX_ECO_CUR_NB", "label": "Average monthly earnings of employees", "tier": 1, "weight": 1.5, "periodicities": ["Q", "A"]},

    # ---- Tier 2 : extended / disaggregated indicators -----------------------
    {"code": "UNE_TUNE_SEX_AGE_DUR_NB",   "label": "Unemployment by duration",                 "tier": 2, "weight": 1.0, "periodicities": ["A"]},
    # Fallback indicator: use citizenship if available, otherwise place of birth.
    # `codes` are tried in order per country; the first with data wins.
    {"code": "EMP_TEMP_SEX_CTZ_NB",
     "codes": ["EMP_TEMP_SEX_CTZ_NB", "EMP_TEMP_SEX_POB_NB"],
     "code_labels": {"EMP_TEMP_SEX_CTZ_NB": "citizenship", "EMP_TEMP_SEX_POB_NB": "place of birth"},
     "label": "Employment by citizenship or place of birth", "tier": 2, "weight": 1.0, "periodicities": ["A"]},
    {"code": "EMP_TEMP_SEX_GEO_NB",       "label": "Employment by urban / rural",              "tier": 2, "weight": 1.0, "periodicities": ["A"]},
    {"code": "EMP_TEMP_SEX_AGE_DSB_NB",   "label": "Employment by disability",                 "tier": 2, "weight": 1.0, "periodicities": ["A"]},
    {"code": "EMP_TEMP_SEX_EDU_NB",       "label": "Employment by education level",            "tier": 2, "weight": 1.0, "periodicities": ["A"]},
]

# ------------------------------------------------------------------------------
# HOUSEHOLD-SURVEY SOURCE FILTER
# ------------------------------------------------------------------------------
# ILOSTAT tags every observation with a data source. We only want observations
# that come from a household survey (labour force survey or another household
# survey with a labour module), NOT from administrative records, establishment
# surveys, or official estimates.
#
# The pipeline matches the source label (from ILOSTAT's source code list,
# CL_SURVEY) against these keywords, case-insensitively. Add/remove to taste.
HOUSEHOLD_SURVEY_KEYWORDS = [
    "labour force survey",
    "household survey",
    "household income",
    "living standards",
    "living conditions",
    "socio-economic",
    "socioeconomic",
    "integrated household",
    "continuous household",
    "multipurpose household",
]

# Sources to explicitly exclude even if a keyword matched (defensive).
SOURCE_EXCLUDE_KEYWORDS = [
    "establishment survey",
    "administrative",
    "population census",   # census is a household enumeration but not a *survey*; exclude by default
    "insurance records",
    "official estimate",
]

# ------------------------------------------------------------------------------
# SCORING
# ------------------------------------------------------------------------------
# Overall score (0-100) = weighted average of three sub-scores, each 0-100.
# The website lets the user move these weights with sliders; the values here are
# the defaults shown on first load.
SCORING = {
    # relative importance of the three criteria (need not sum to 1; normalised)
    "weights": {
        "coverage":  1.0,   # breadth: share of key indicators with HH-survey data
        "frequency": 1.0,   # how often / how regularly data is produced
        "recency":   1.0,   # how up to date the most recent data is
    },

    # ---- coverage sub-score -------------------------------------------------
    # Share of KEY_INDICATORS (weighted by indicator `weight`) for which the
    # country has at least one qualifying household-survey observation inside
    # `coverage_window_years`. Set window to None to count data of any age.
    "coverage": {
        "coverage_window_years": 15,
    },

    # ---- frequency / regularity sub-score -----------------------------------
    # Two parts, averaged:
    #   periodicity_score : based on the most frequent periodicity the country
    #                       produces its headline indicators in.
    #   regularity_score  : share of the last `regularity_window_years` in which
    #                       at least one headline indicator was produced (are
    #                       there gaps, or is it a steady annual/quarterly cadence?)
    "frequency": {
        "periodicity_points": {"M": 100, "Q": 85, "A": 60, "irregular": 30},
        "regularity_window_years": 10,
    },

    # ---- recency sub-score --------------------------------------------------
    # Based on the age (in years) of the most recent qualifying datapoint across
    # the key indicators. Linear decay from full marks to zero.
    "recency": {
        "full_marks_max_age": 1,   # <=1 year old  -> 100
        "zero_marks_min_age": 12,  # >=12 years old -> 0
    },
}

# ------------------------------------------------------------------------------
# ILOSTAT endpoints
# ------------------------------------------------------------------------------
ILOSTAT = {
    # Bulk CSV download facility (one gzip CSV per indicator+periodicity).
    # ILO reorganised their site: the bulk files now live under webapps.ilo.org.
    # The pipeline probes these bases in order and uses the first that responds.
    "bulk_bases": [
        "https://webapps.ilo.org/ilostat-files/WEB_bulk_download/indicator",
        "https://www.ilo.org/ilostat-files/WEB_bulk_download/indicator",
    ],
    "bulk_base": "https://webapps.ilo.org/ilostat-files/WEB_bulk_download/indicator",
    # Dictionary (code list) CSVs from the same bulk facility (fallbacks for labels).
    "dic_bases": [
        "https://webapps.ilo.org/ilostat-files/WEB_bulk_download/dic",
        "https://www.ilo.org/ilostat-files/WEB_bulk_download/dic",
    ],
    # rplumber REST API (used for the table of contents / code lists).
    "toc_indicator": "https://rplumber.ilo.org/metadata/toc/indicator/?lang=en",
    "toc_ref_area":  "https://rplumber.ilo.org/metadata/toc/ref_area/?lang=en",
    "codelist_survey": "https://rplumber.ilo.org/metadata/dic/CL_SURVEY/?lang=en",
    "codelist_area": "https://rplumber.ilo.org/metadata/dic/CL_AREA/?lang=en",
    # Don't overwrite the published site unless at least this many countries were
    # scored (protects the live site if ILOSTAT is unreachable or a URL changes).
    "min_countries": 30,
}

# Regions we display in the UI filter. ISO3 -> region.  (M49-based grouping;
# the pipeline falls back to "Other" for anything not listed.)
# Kept short here; the pipeline can also pull regions from ILOSTAT's ref_area toc.
