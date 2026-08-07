#!/usr/bin/env python3
"""
Generate a realistic SAMPLE dataset so the website works before you have run the
real pipeline (fetch_and_rank.py can't reach ILOSTAT from every environment).

This version covers ILOSTAT's FULL roster — ~190 countries and territories across
the five ILO regions (Africa, Americas, Arab States, Asia and the Pacific,
Europe and Central Asia).

The sample is internally consistent: each country gets a plausible per-indicator
availability grid, and the coverage/frequency/recency scores are computed from
that grid using the *exact same* scoring functions the real pipeline uses
(imported from fetch_and_rank).

    python gen_sample_data.py

Writes ../web/data/rankings.js and rankings.json (same format as the real run).
Replace it any time by running fetch_and_rank.py.

NOTE: the `maturity` value per country is a rough illustrative estimate of
statistical-system development used only to shape the sample. It is NOT a real
ILOSTAT figure. Real numbers require fetch_and_rank.py.
"""

import os
import random
from datetime import datetime

import config as C
from fetch_and_rank import (score_country, write_output, next_period,
                            enumerate_pending, period_sort_key, load_nso_registry)

random.seed(42)
_NOW = datetime.now()
CURRENT_YEAR = _NOW.year
CUR_Q = (_NOW.month - 1) // 3 + 1
CUR_M = _NOW.month

AF = "Africa"
AM = "Americas"
AR = "Arab States"
AP = "Asia and the Pacific"
EU = "Europe and Central Asia"

# (iso3, name, region, maturity 0-1)  maturity shapes coverage/frequency/recency
COUNTRIES = [
    # ------------------------- Africa -------------------------
    ("DZA", "Algeria", AF, 0.55), ("AGO", "Angola", AF, 0.30), ("BEN", "Benin", AF, 0.42),
    ("BWA", "Botswana", AF, 0.58), ("BFA", "Burkina Faso", AF, 0.35), ("BDI", "Burundi", AF, 0.22),
    ("CPV", "Cabo Verde", AF, 0.55), ("CMR", "Cameroon", AF, 0.36), ("CAF", "Central African Republic", AF, 0.15),
    ("TCD", "Chad", AF, 0.20), ("COM", "Comoros", AF, 0.28), ("COG", "Congo", AF, 0.30),
    ("COD", "Congo, Democratic Republic of the", AF, 0.26), ("CIV", "Côte d'Ivoire", AF, 0.47),
    ("DJI", "Djibouti", AF, 0.30), ("EGY", "Egypt", AF, 0.68), ("GNQ", "Equatorial Guinea", AF, 0.20),
    ("ERI", "Eritrea", AF, 0.12), ("SWZ", "Eswatini", AF, 0.45), ("ETH", "Ethiopia", AF, 0.40),
    ("GAB", "Gabon", AF, 0.38), ("GMB", "Gambia", AF, 0.36), ("GHA", "Ghana", AF, 0.54),
    ("GIN", "Guinea", AF, 0.30), ("GNB", "Guinea-Bissau", AF, 0.22), ("KEN", "Kenya", AF, 0.56),
    ("LSO", "Lesotho", AF, 0.44), ("LBR", "Liberia", AF, 0.30), ("LBY", "Libya", AF, 0.28),
    ("MDG", "Madagascar", AF, 0.34), ("MWI", "Malawi", AF, 0.38), ("MLI", "Mali", AF, 0.33),
    ("MRT", "Mauritania", AF, 0.38), ("MUS", "Mauritius", AF, 0.74), ("MAR", "Morocco", AF, 0.70),
    ("MOZ", "Mozambique", AF, 0.34), ("NAM", "Namibia", AF, 0.58), ("NER", "Niger", AF, 0.30),
    ("NGA", "Nigeria", AF, 0.46), ("RWA", "Rwanda", AF, 0.58), ("STP", "Sao Tome and Principe", AF, 0.32),
    ("SEN", "Senegal", AF, 0.49), ("SYC", "Seychelles", AF, 0.55), ("SLE", "Sierra Leone", AF, 0.32),
    ("SOM", "Somalia", AF, 0.12), ("ZAF", "South Africa", AF, 0.82), ("SSD", "South Sudan", AF, 0.14),
    ("SDN", "Sudan", AF, 0.24), ("TZA", "Tanzania, United Republic of", AF, 0.48), ("TGO", "Togo", AF, 0.38),
    ("TUN", "Tunisia", AF, 0.66), ("UGA", "Uganda", AF, 0.50), ("ZMB", "Zambia", AF, 0.44),
    ("ZWE", "Zimbabwe", AF, 0.42),

    # ------------------------- Arab States -------------------------
    ("BHR", "Bahrain", AR, 0.55), ("IRQ", "Iraq", AR, 0.40), ("JOR", "Jordan", AR, 0.64),
    ("KWT", "Kuwait", AR, 0.58), ("LBN", "Lebanon", AR, 0.42), ("OMN", "Oman", AR, 0.58),
    ("PSE", "Occupied Palestinian Territory", AR, 0.48), ("QAT", "Qatar", AR, 0.66),
    ("SAU", "Saudi Arabia", AR, 0.72), ("SYR", "Syrian Arab Republic", AR, 0.20),
    ("ARE", "United Arab Emirates", AR, 0.68), ("YEM", "Yemen", AR, 0.16),

    # ------------------------- Asia and the Pacific -------------------------
    ("AFG", "Afghanistan", AP, 0.20), ("AUS", "Australia", AP, 0.96), ("BGD", "Bangladesh", AP, 0.55),
    ("BTN", "Bhutan", AP, 0.45), ("BRN", "Brunei Darussalam", AP, 0.55), ("KHM", "Cambodia", AP, 0.44),
    ("CHN", "China", AP, 0.70), ("FJI", "Fiji", AP, 0.42), ("IND", "India", AP, 0.66),
    ("IDN", "Indonesia", AP, 0.76), ("IRN", "Iran, Islamic Republic of", AP, 0.55), ("JPN", "Japan", AP, 0.93),
    ("KIR", "Kiribati", AP, 0.25), ("PRK", "Korea, Democratic People's Republic of", AP, 0.10),
    ("KOR", "Korea, Republic of", AP, 0.93), ("LAO", "Lao People's Democratic Republic", AP, 0.40),
    ("MYS", "Malaysia", AP, 0.83), ("MDV", "Maldives", AP, 0.50), ("MHL", "Marshall Islands", AP, 0.22),
    ("FSM", "Micronesia, Federated States of", AP, 0.22), ("MNG", "Mongolia", AP, 0.63),
    ("MMR", "Myanmar", AP, 0.35), ("NPL", "Nepal", AP, 0.45), ("NZL", "New Zealand", AP, 0.94),
    ("PAK", "Pakistan", AP, 0.50), ("PLW", "Palau", AP, 0.25), ("PNG", "Papua New Guinea", AP, 0.28),
    ("PHL", "Philippines", AP, 0.80), ("WSM", "Samoa", AP, 0.35), ("SGP", "Singapore", AP, 0.88),
    ("SLB", "Solomon Islands", AP, 0.26), ("LKA", "Sri Lanka", AP, 0.68), ("THA", "Thailand", AP, 0.82),
    ("TLS", "Timor-Leste", AP, 0.35), ("TON", "Tonga", AP, 0.32), ("TUV", "Tuvalu", AP, 0.20),
    ("VUT", "Vanuatu", AP, 0.28), ("VNM", "Viet Nam", AP, 0.72),

    # ------------------------- Europe and Central Asia -------------------------
    ("ALB", "Albania", EU, 0.68), ("AND", "Andorra", EU, 0.52), ("ARM", "Armenia", EU, 0.70),
    ("AUT", "Austria", EU, 0.93), ("AZE", "Azerbaijan", EU, 0.62), ("BLR", "Belarus", EU, 0.66),
    ("BEL", "Belgium", EU, 0.94), ("BIH", "Bosnia and Herzegovina", EU, 0.66), ("BGR", "Bulgaria", EU, 0.85),
    ("HRV", "Croatia", EU, 0.87), ("CYP", "Cyprus", EU, 0.88), ("CZE", "Czechia", EU, 0.90),
    ("DNK", "Denmark", EU, 0.95), ("EST", "Estonia", EU, 0.90), ("FIN", "Finland", EU, 0.96),
    ("FRA", "France", EU, 0.95), ("GEO", "Georgia", EU, 0.74), ("DEU", "Germany", EU, 0.96),
    ("GRC", "Greece", EU, 0.89), ("HUN", "Hungary", EU, 0.87), ("ISL", "Iceland", EU, 0.92),
    ("IRL", "Ireland", EU, 0.90), ("ISR", "Israel", EU, 0.90), ("ITA", "Italy", EU, 0.93),
    ("KAZ", "Kazakhstan", EU, 0.72), ("KGZ", "Kyrgyzstan", EU, 0.55), ("LVA", "Latvia", EU, 0.89),
    ("LIE", "Liechtenstein", EU, 0.52), ("LTU", "Lithuania", EU, 0.89), ("LUX", "Luxembourg", EU, 0.92),
    ("MLT", "Malta", EU, 0.86), ("MDA", "Moldova, Republic of", EU, 0.62), ("MCO", "Monaco", EU, 0.50),
    ("MNE", "Montenegro", EU, 0.64), ("NLD", "Netherlands", EU, 0.97), ("MKD", "North Macedonia", EU, 0.66),
    ("NOR", "Norway", EU, 0.95), ("POL", "Poland", EU, 0.90), ("PRT", "Portugal", EU, 0.91),
    ("ROU", "Romania", EU, 0.86), ("RUS", "Russian Federation", EU, 0.78), ("SMR", "San Marino", EU, 0.50),
    ("SRB", "Serbia", EU, 0.80), ("SVK", "Slovakia", EU, 0.89), ("SVN", "Slovenia", EU, 0.90),
    ("ESP", "Spain", EU, 0.94), ("SWE", "Sweden", EU, 0.98), ("CHE", "Switzerland", EU, 0.94),
    ("TJK", "Tajikistan", EU, 0.45), ("TUR", "Türkiye", EU, 0.85), ("TKM", "Turkmenistan", EU, 0.30),
    ("UKR", "Ukraine", EU, 0.62), ("GBR", "United Kingdom", EU, 0.94), ("UZB", "Uzbekistan", EU, 0.55),

    # ------------------------- Americas -------------------------
    ("ATG", "Antigua and Barbuda", AM, 0.45), ("ARG", "Argentina", AM, 0.82), ("BHS", "Bahamas", AM, 0.55),
    ("BRB", "Barbados", AM, 0.60), ("BLZ", "Belize", AM, 0.48), ("BOL", "Bolivia", AM, 0.66),
    ("BRA", "Brazil", AM, 0.86), ("CAN", "Canada", AM, 0.95), ("CHL", "Chile", AM, 0.85),
    ("COL", "Colombia", AM, 0.83), ("CRI", "Costa Rica", AM, 0.82), ("CUB", "Cuba", AM, 0.45),
    ("DMA", "Dominica", AM, 0.40), ("DOM", "Dominican Republic", AM, 0.74), ("ECU", "Ecuador", AM, 0.77),
    ("SLV", "El Salvador", AM, 0.68), ("GRD", "Grenada", AM, 0.42), ("GTM", "Guatemala", AM, 0.58),
    ("GUY", "Guyana", AM, 0.48), ("HTI", "Haiti", AM, 0.24), ("HND", "Honduras", AM, 0.55),
    ("JAM", "Jamaica", AM, 0.60), ("MEX", "Mexico", AM, 0.85), ("NIC", "Nicaragua", AM, 0.55),
    ("PAN", "Panama", AM, 0.72), ("PRY", "Paraguay", AM, 0.70), ("PER", "Peru", AM, 0.79),
    ("KNA", "Saint Kitts and Nevis", AM, 0.40), ("LCA", "Saint Lucia", AM, 0.45),
    ("VCT", "Saint Vincent and the Grenadines", AM, 0.42), ("SUR", "Suriname", AM, 0.45),
    ("TTO", "Trinidad and Tobago", AM, 0.62), ("USA", "United States", AM, 0.95),
    ("URY", "Uruguay", AM, 0.84), ("VEN", "Venezuela, Bolivarian Republic of", AM, 0.40),
]


def make_indicator_grid(maturity):
    """Return {code: availability record} consistent with the maturity level."""
    # periodicity the country is capable of, by maturity
    if maturity >= 0.9:
        base_period, regularity = "Q", 0.98
        if random.random() < 0.35:
            base_period = "M"
    elif maturity >= 0.78:
        base_period, regularity = "Q", 0.9
    elif maturity >= 0.6:
        base_period, regularity = "A", 0.85
    elif maturity >= 0.4:
        base_period, regularity = "A", 0.6
    else:
        base_period, regularity = "A", 0.35

    # recency: how old is the most recent data, by maturity
    if maturity >= 0.9:
        latest_lag = random.choice([0, 0, 1])
    elif maturity >= 0.75:
        latest_lag = random.choice([0, 1, 1, 2])
    elif maturity >= 0.55:
        latest_lag = random.choice([1, 2, 2, 3])
    elif maturity >= 0.4:
        latest_lag = random.choice([2, 3, 4, 5])
    else:
        latest_lag = random.choice([4, 6, 8, 10, 12])

    grid = {}
    order_rank = {"M": 3, "Q": 2, "A": 1}
    for ind in C.KEY_INDICATORS:
        code = ind["code"]
        # probability this indicator is covered: higher maturity + tier-1 first
        p_cov = maturity - (0.18 if ind["tier"] == 2 else 0.0)
        p_cov += random.uniform(-0.08, 0.08)
        covered = random.random() < p_cov

        if not covered:
            grid[code] = {"covered": False, "latest": None, "latest_period": None,
                          "periodicity": None, "recent_years": set()}
            continue

        allowed = ind["periodicities"]
        period = None
        for p in ["M", "Q", "A"]:
            if p in allowed and order_rank[p] <= order_rank[base_period]:
                period = p
                break
        if period is None:
            period = allowed[-1]

        latest = CURRENT_YEAR - latest_lag - (0 if ind["tier"] == 1 else random.choice([0, 0, 1, 2]))

        years = set()
        for y in range(CURRENT_YEAR - 10, latest + 1):
            if y <= latest and random.random() < regularity:
                years.add(y)
        years.add(latest)

        # build a realistic latest *period* string for this indicator
        if period == "Q":
            q = max(1, CUR_Q - 1) if latest == CURRENT_YEAR else random.randint(1, 4)
            lp = f"{latest}Q{q}"
        elif period == "M":
            m = max(1, CUR_M - 1) if latest == CURRENT_YEAR else random.randint(1, 12)
            lp = f"{latest}M{m:02d}"
        else:
            lp = f"{latest}"

        via = None
        if len(ind.get("codes", [])) > 1:
            labs = list(ind.get("code_labels", {}).values()) or ["citizenship", "place of birth"]
            via = labs[0] if random.random() < 0.7 else labs[1]
        grid[code] = {"covered": True, "latest": latest, "latest_period": lp,
                      "periodicity": period, "recent_years": years, "via": via}

    win = C.SCORING["coverage"]["coverage_window_years"]
    cutoff = CURRENT_YEAR - win if win else None
    for rec in grid.values():
        rec["covered"] = rec["latest"] is not None and (cutoff is None or rec["latest"] >= cutoff)
    return grid


_OTHER_HH_SURVEYS = [
    "Integrated Household Survey", "Living Standards Measurement Survey",
    "Household Budget Survey", "Socio-Economic Survey",
    "Continuous Household Survey", "Household Income and Expenditure Survey",
]


def build_sources(iso, maturity, latest_year, registry):
    """Illustrative survey source name(s) for the sample (real pipeline reads the
    actual ILOSTAT source labels)."""
    if latest_year is None:
        return []
    entry = registry.get(iso)
    if entry:
        name = entry.get("note") or "Labour Force Survey"
        return [{"name": name, "latest": latest_year}]
    out = [{"name": "Labour Force Survey", "latest": latest_year}]
    if maturity < 0.55 and random.random() < 0.6:
        # lower-capacity systems often rely on a broader household survey instead
        out = [{"name": random.choice(_OTHER_HH_SURVEYS), "latest": latest_year}]
    elif 0.55 <= maturity < 0.8 and random.random() < 0.3:
        out.append({"name": random.choice(_OTHER_HH_SURVEYS),
                    "latest": latest_year - random.choice([1, 2, 3])})
    return out


def prev_period(s, per):
    """The period immediately before s, at periodicity per (sample-only helper)."""
    from fetch_and_rank import coerce_period, parse_period
    s = coerce_period(s, per)
    y, k, sub = parse_period(s)
    if per == "A":
        return f"{y - 1}"
    if per == "Q":
        q = sub - 1
        return f"{y - 1}Q4" if q < 1 else f"{y}Q{q}"
    if per == "M":
        mo = sub - 1
        return f"{y - 1}M12" if mo < 1 else f"{y}M{mo:02d}"
    return s


def recency_from_year(yr):
    rc = C.SCORING["recency"]
    if yr is None:
        return 0.0
    age = CURRENT_YEAR - yr
    span = rc["zero_marks_min_age"] - rc["full_marks_max_age"]
    v = 100.0 * (rc["zero_marks_min_age"] - age) / span if span > 0 else 100.0
    return round(max(0.0, min(100.0, v)), 1)


def main():
    registry = load_nso_registry()
    records = []
    for iso, name, region, maturity in COUNTRIES:
        grid = make_indicator_grid(maturity)
        cov, freq, rec, meta = score_country(grid)

        # headline latest period from the grid
        ilo_period = None
        for ind in C.KEY_INDICATORS:
            if ind["tier"] != 1:
                continue
            lp = grid[ind["code"]].get("latest_period")
            if lp and (ilo_period is None or period_sort_key(lp) > period_sort_key(ilo_period)):
                ilo_period = lp

        latest_year = meta["latest_year"]
        best_per = meta["best_periodicity"]
        recency = rec
        pending = None

        # Pending only for countries in the NSO registry (matches the real pipeline).
        # For the sample we place ILOSTAT a few periods BEHIND the NSO's real latest,
        # which is the true lag scenario (e.g. Jamaica: ILOSTAT behind STATIN).
        entry = registry.get(iso)
        if entry and meta["latest_year"] is not None:
            per = entry.get("periodicity") or "A"
            nso_latest = entry.get("nso_latest")
            lag = random.choice([3, 4, 5, 6, 7, 8])
            ilo = nso_latest
            for _ in range(lag):
                ilo = prev_period(ilo, per)
            ilo_period = ilo
            best_per = per
            latest_year = int(ilo_period[:4])
            recency = recency_from_year(latest_year)
            periods = enumerate_pending(ilo_period, nso_latest, per)
            if periods:
                pending = {
                    "nso": entry.get("nso", "National statistics office"),
                    "nso_latest": nso_latest,
                    "periodicity": per,
                    "periods": periods,
                    "count": len(periods),
                    "source": entry.get("source", ""),
                    "checked": entry.get("checked", _NOW.strftime("%Y-%m-%d")),
                    "note": entry.get("note", ""),
                }

        records.append({
            "iso3": iso, "country": name, "region": region,
            "coverage": cov, "frequency": freq, "recency": recency,
            "latest_year": latest_year,
            "latest_period": ilo_period,
            "best_periodicity": best_per,
            "n_covered": meta["n_covered"], "n_total": meta["n_total"],
            "pending": pending,
            "sources": build_sources(iso, maturity, latest_year, registry),
            "indicators": {
                code: {"covered": grid[code]["covered"],
                       "latest": grid[code]["latest"],
                       "periodicity": grid[code]["periodicity"],
                       "via": grid[code].get("via")}
                for code in [i["code"] for i in C.KEY_INDICATORS]
            },
        })

    payload = {
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "current_year": CURRENT_YEAR,
        "source": "SAMPLE DATA (illustrative, full country roster) — replace by running fetch_and_rank.py",
        "is_sample": True,
        "default_weights": C.SCORING["weights"],
        "scoring_params": {
            "coverage": C.SCORING["coverage"],
            "frequency": C.SCORING["frequency"],
            "recency": C.SCORING["recency"],
        },
        "indicators": [
            {"code": i["code"], "label": i["label"], "tier": i["tier"], "weight": i["weight"]}
            for i in C.KEY_INDICATORS
        ],
        "countries": records,
    }
    out = os.path.join(os.path.dirname(__file__), "..", "web", "data")
    write_output(payload, os.path.abspath(out))


if __name__ == "__main__":
    main()
