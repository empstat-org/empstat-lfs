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
    {"code": "LUU_XLU4_SEX_AGE_RT",     "label": "Composite measure of labour underutilization (LU4)", "tier": 1, "weight": 1.5, "periodicities": ["Q", "A"]},
    {"code": "EMP_TEMP_SEX_STE_NB",     "label": "Employment by status in employment", "tier": 1, "weight": 1.5, "periodicities": ["Q", "A"]},
    {"code": "EMP_TEMP_SEX_OCU_NB",     "label": "Employment by occupation",        "tier": 1, "weight": 1.5, "periodicities": ["Q", "A"]},
    {"code": "EMP_TEMP_SEX_ECO_NB",     "label": "Employment by economic activity", "tier": 1, "weight": 1.5, "periodicities": ["Q", "A"]},
    {"code": "EMP_NIFL_SEX_RT",         "label": "Informal employment rate",        "tier": 1, "weight": 1.5, "periodicities": ["A"]},
    {"code": "HOW_TEMP_SEX_ECO_NB",     "label": "Mean weekly hours actually worked", "tier": 1, "weight": 1.5, "periodicities": ["Q", "A"]},
    {"code": "EAR_EMTA_SEX_ECO_CUR_NB", "label": "Average monthly earnings of employees", "tier": 1, "weight": 1.5, "periodicities": ["Q", "A"]},

    # ---- Tier 2 : extended / disaggregated indicators -----------------------
    {"code": "UNE_TUNE_SEX_AGE_DUR_NB",   "label": "Unemployment by duration",                 "tier": 2, "weight": 1.0, "periodicities": ["A"]},
    # Fallback indicator: use citizenship if available, otherwise place of birth.
    # `codes` are tried in order per country; the first with data wins.
    {"code": "EMP_TEMP_SEX_AGE_CCT_NB",
     "codes": ["EMP_TEMP_SEX_AGE_CCT_NB", "EMP_TEMP_SEX_AGE_CBR_NB"],
     "code_labels": {"EMP_TEMP_SEX_AGE_CCT_NB": "citizenship", "EMP_TEMP_SEX_AGE_CBR_NB": "place of birth"},
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
    "modelled",              # exclude ILO modelled estimates — national sources only
    "modeled",
    "estimate",
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
    # ILOSTAT is served by the rplumber API. The data endpoint returns CSV
    # directly, and with type=both it includes source LABELS (so we can identify
    # household surveys without a separate dictionary):
    #   https://rplumber.ilo.org/data/indicator?id={id}&type=both&format=.csv
    "data_api": "https://rplumber.ilo.org/data/indicator",
    "toc_indicator": "https://rplumber.ilo.org/metadata/toc/indicator/?lang=en",
    "toc_ref_area":  "https://rplumber.ilo.org/metadata/toc/ref_area/?lang=en",
    # Only request data from this many years back (keeps downloads small).
    "years_back": 25,
    # Don't overwrite the published site unless at least this many countries were
    # scored (protects the live site if ILOSTAT is unreachable or a URL changes).
    "min_countries": 30,
}

# Regions we display in the UI filter. ISO3 -> region.  (M49-based grouping;
# the pipeline falls back to "Other" for anything not listed.)
# Kept short here; the pipeline can also pull regions from ILOSTAT's ref_area toc.


# ISO3 -> ILO region (baked in, since the live ref_area API has no region column).
REGIONS = {
    "AFG": "Asia and the Pacific", "AGO": "Africa", "ALB": "Europe and Central Asia",
    "AND": "Europe and Central Asia", "ARE": "Arab States", "ARG": "Americas",
    "ARM": "Europe and Central Asia", "ATG": "Americas", "AUS": "Asia and the Pacific",
    "AUT": "Europe and Central Asia", "AZE": "Europe and Central Asia", "BDI": "Africa",
    "BEL": "Europe and Central Asia", "BEN": "Africa", "BFA": "Africa",
    "BGD": "Asia and the Pacific", "BGR": "Europe and Central Asia", "BHR": "Arab States",
    "BHS": "Americas", "BIH": "Europe and Central Asia", "BLR": "Europe and Central Asia",
    "BLZ": "Americas", "BOL": "Americas", "BRA": "Americas", "BRB": "Americas",
    "BRN": "Asia and the Pacific", "BTN": "Asia and the Pacific", "BWA": "Africa",
    "CAF": "Africa", "CAN": "Americas", "CHE": "Europe and Central Asia", "CHL": "Americas",
    "CHN": "Asia and the Pacific", "CIV": "Africa", "CMR": "Africa", "COD": "Africa",
    "COG": "Africa", "COL": "Americas", "COM": "Africa", "CPV": "Africa", "CRI": "Americas",
    "CUB": "Americas", "CYP": "Europe and Central Asia", "CZE": "Europe and Central Asia",
    "DEU": "Europe and Central Asia", "DJI": "Africa", "DMA": "Americas",
    "DNK": "Europe and Central Asia", "DOM": "Americas", "DZA": "Africa", "ECU": "Americas",
    "EGY": "Africa", "ERI": "Africa", "ESP": "Europe and Central Asia",
    "EST": "Europe and Central Asia", "ETH": "Africa", "FIN": "Europe and Central Asia",
    "FJI": "Asia and the Pacific", "FRA": "Europe and Central Asia",
    "FSM": "Asia and the Pacific", "GAB": "Africa", "GBR": "Europe and Central Asia",
    "GEO": "Europe and Central Asia", "GHA": "Africa", "GIN": "Africa", "GMB": "Africa",
    "GNB": "Africa", "GNQ": "Africa", "GRC": "Europe and Central Asia", "GRD": "Americas",
    "GTM": "Americas", "GUY": "Americas", "HND": "Americas", "HRV": "Europe and Central Asia",
    "HTI": "Americas", "HUN": "Europe and Central Asia", "IDN": "Asia and the Pacific",
    "IND": "Asia and the Pacific", "IRL": "Europe and Central Asia",
    "IRN": "Asia and the Pacific", "IRQ": "Arab States", "ISL": "Europe and Central Asia",
    "ISR": "Europe and Central Asia", "ITA": "Europe and Central Asia", "JAM": "Americas",
    "JOR": "Arab States", "JPN": "Asia and the Pacific", "KAZ": "Europe and Central Asia",
    "KEN": "Africa", "KGZ": "Europe and Central Asia", "KHM": "Asia and the Pacific",
    "KIR": "Asia and the Pacific", "KNA": "Americas", "KOR": "Asia and the Pacific",
    "KWT": "Arab States", "LAO": "Asia and the Pacific", "LBN": "Arab States", "LBR": "Africa",
    "LBY": "Africa", "LCA": "Americas", "LIE": "Europe and Central Asia",
    "LKA": "Asia and the Pacific", "LSO": "Africa", "LTU": "Europe and Central Asia",
    "LUX": "Europe and Central Asia", "LVA": "Europe and Central Asia", "MAR": "Africa",
    "MCO": "Europe and Central Asia", "MDA": "Europe and Central Asia", "MDG": "Africa",
    "MDV": "Asia and the Pacific", "MEX": "Americas", "MHL": "Asia and the Pacific",
    "MKD": "Europe and Central Asia", "MLI": "Africa", "MLT": "Europe and Central Asia",
    "MMR": "Asia and the Pacific", "MNE": "Europe and Central Asia",
    "MNG": "Asia and the Pacific", "MOZ": "Africa", "MRT": "Africa", "MUS": "Africa",
    "MWI": "Africa", "MYS": "Asia and the Pacific", "NAM": "Africa", "NER": "Africa",
    "NGA": "Africa", "NIC": "Americas", "NLD": "Europe and Central Asia",
    "NOR": "Europe and Central Asia", "NPL": "Asia and the Pacific",
    "NZL": "Asia and the Pacific", "OMN": "Arab States", "PAK": "Asia and the Pacific",
    "PAN": "Americas", "PER": "Americas", "PHL": "Asia and the Pacific",
    "PLW": "Asia and the Pacific", "PNG": "Asia and the Pacific",
    "POL": "Europe and Central Asia", "PRK": "Asia and the Pacific",
    "PRT": "Europe and Central Asia", "PRY": "Americas", "PSE": "Arab States",
    "QAT": "Arab States", "ROU": "Europe and Central Asia", "RUS": "Europe and Central Asia",
    "RWA": "Africa", "SAU": "Arab States", "SDN": "Africa", "SEN": "Africa",
    "SGP": "Asia and the Pacific", "SLB": "Asia and the Pacific", "SLE": "Africa",
    "SLV": "Americas", "SMR": "Europe and Central Asia", "SOM": "Africa",
    "SRB": "Europe and Central Asia", "SSD": "Africa", "STP": "Africa", "SUR": "Americas",
    "SVK": "Europe and Central Asia", "SVN": "Europe and Central Asia",
    "SWE": "Europe and Central Asia", "SWZ": "Africa", "SYC": "Africa", "SYR": "Arab States",
    "TCD": "Africa", "TGO": "Africa", "THA": "Asia and the Pacific",
    "TJK": "Europe and Central Asia", "TKM": "Europe and Central Asia",
    "TLS": "Asia and the Pacific", "TON": "Asia and the Pacific", "TTO": "Americas",
    "TUN": "Africa", "TUR": "Europe and Central Asia", "TUV": "Asia and the Pacific",
    "TZA": "Africa", "UGA": "Africa", "UKR": "Europe and Central Asia", "URY": "Americas",
    "USA": "Americas", "UZB": "Europe and Central Asia", "VCT": "Americas", "VEN": "Americas",
    "VNM": "Asia and the Pacific", "VUT": "Asia and the Pacific",
    "WSM": "Asia and the Pacific", "YEM": "Arab States", "ZAF": "Africa", "ZMB": "Africa",
    "ZWE": "Africa",
}
