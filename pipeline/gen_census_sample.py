#!/usr/bin/env python3
"""
Sample data for the CENSUS Coverage Index (illustrative, full country roster).

Two criteria: coverage + recency. Censuses are ~decennial, so each country gets a
plausible latest-census year and a coverage grid from that census.

    python gen_census_sample.py     # writes ../web/census/data/rankings.(js|json)

Replace with real data via:
    python fetch_and_rank.py --config config_census --out ../web/census/data
"""

import os
import random
from datetime import datetime

import config_census as CC
from fetch_and_rank import write_output
from gen_sample_data import COUNTRIES   # reuse the same country roster + maturity

random.seed(11)
CURRENT_YEAR = datetime.now().year


def census_year(maturity):
    """Plausible most-recent census year given statistical-system maturity."""
    r = random.random()
    if maturity >= 0.8:
        return random.choice([2020, 2021, 2021, 2022, 2022, 2023])
    if maturity >= 0.6:
        return random.choice([2018, 2019, 2020, 2021, 2022])
    if maturity >= 0.45:
        return random.choice([2011, 2013, 2016, 2019, 2021])
    if maturity >= 0.3:
        return random.choice([2009, 2011, 2014, 2016, None])
    return random.choice([2003, 2008, 2010, None, None])


def recency_score(year):
    rc = CC.SCORING["recency"]
    if year is None:
        return 0.0
    age = CURRENT_YEAR - year
    span = rc["zero_marks_min_age"] - rc["full_marks_max_age"]
    v = 100.0 * (rc["zero_marks_min_age"] - age) / span if span > 0 else 100.0
    return round(max(0.0, min(100.0, v)), 1)


def build_country(iso, name, region, maturity):
    yr = census_year(maturity)
    win = CC.SCORING["coverage"]["coverage_window_years"]
    in_window = yr is not None and (CURRENT_YEAR - yr) <= win

    weight_total = sum(i["weight"] for i in CC.KEY_INDICATORS)
    got = 0.0
    grid = {}
    for ind in CC.KEY_INDICATORS:
        # a census that happened produces most structural indicators
        p = 0.55 + maturity * 0.45 - (0.15 if ind["tier"] == 2 else 0.0)
        covered = (yr is not None) and (random.random() < min(0.97, p))
        via = None
        if covered and len(ind.get("codes", [])) > 1:
            labs = list(ind.get("code_labels", {}).values()) or ["citizenship", "place of birth"]
            via = labs[0] if random.random() < 0.7 else labs[1]
        grid[ind["code"]] = {"covered": bool(covered and in_window),
                             "latest": yr if covered else None, "via": via}
        if covered and in_window:
            got += ind["weight"]

    coverage = round(100.0 * got / weight_total, 1) if weight_total else 0.0
    recency = recency_score(yr)  # decays with age
    n_cov = sum(1 for g in grid.values() if g["covered"])
    sources = [{"name": "Population and Housing Census", "latest": yr}] if yr else []

    return {
        "iso3": iso, "country": name, "region": region,
        "coverage": coverage, "recency": recency,
        "latest_year": yr,
        "n_covered": n_cov, "n_total": len(CC.KEY_INDICATORS),
        "sources": sources,
        "indicators": {c["code"]: grid[c["code"]] for c in CC.KEY_INDICATORS},
    }


def main():
    records = [build_country(iso, name, region, mat) for iso, name, region, mat in COUNTRIES]
    payload = {
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "current_year": CURRENT_YEAR,
        "index_name": CC.INDEX_NAME,
        "source": "SAMPLE DATA (illustrative) — replace via fetch_and_rank.py --config config_census",
        "is_sample": True,
        "criteria": ["coverage", "recency"],
        "default_weights": CC.SCORING["weights"],
        "scoring_params": {k: v for k, v in CC.SCORING.items() if k != "weights"},
        "indicators": [
            {"code": i["code"], "label": i["label"], "tier": i["tier"], "weight": i["weight"]}
            for i in CC.KEY_INDICATORS
        ],
        "countries": records,
    }
    out = os.path.join(os.path.dirname(__file__), "..", "web", "census", "data")
    write_output(payload, os.path.abspath(out))


if __name__ == "__main__":
    main()
