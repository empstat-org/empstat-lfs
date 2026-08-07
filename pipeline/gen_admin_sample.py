#!/usr/bin/env python3
"""
Sample data for the ADMINISTRATIVE DATA Coverage Index (illustrative, full roster).

Three criteria (coverage + frequency + recency), no pending. Self-contained
scoring that mirrors fetch_and_rank's formulas.

    python gen_admin_sample.py    # writes ../web/admin/data/rankings.(js|json)

Replace with real data via:
    python fetch_and_rank.py --config config_admin --out ../web/admin/data
"""

import os
import random
from datetime import datetime

import config_admin as CA
from fetch_and_rank import write_output
from gen_sample_data import COUNTRIES

random.seed(23)
CURRENT_YEAR = datetime.now().year

ADMIN_SOURCES = [
    "Administrative records", "Social security records",
    "Employment office records", "Labour inspection records",
]


def _clamp(x): return max(0.0, min(100.0, x))


def score(maturity):
    """Return (coverage, frequency, recency, latest_year, best_p, grid, n_cov)."""
    if maturity >= 0.85:
        base_p, reg = ("M" if random.random() < 0.5 else "Q"), 0.95
    elif maturity >= 0.7:
        base_p, reg = "Q", 0.9
    elif maturity >= 0.5:
        base_p, reg = "A", 0.8
    else:
        base_p, reg = "A", 0.5

    lag = (random.choice([0, 1, 1]) if maturity >= 0.85 else
           random.choice([1, 2, 2, 3]) if maturity >= 0.65 else
           random.choice([2, 3, 4, 5]) if maturity >= 0.45 else
           random.choice([4, 6, 8, 10]))

    order = {"M": 3, "Q": 2, "A": 1}
    grid, got, wtot = {}, 0.0, 0.0
    tier1_years, best_p, best_rank = set(), "irregular", -1
    for ind in CA.KEY_INDICATORS:
        wtot += ind["weight"]
        p_cov = maturity - (0.15 if ind["tier"] == 2 else 0.0) + random.uniform(-0.08, 0.08)
        covered = random.random() < p_cov
        if not covered:
            grid[ind["code"]] = {"covered": False, "latest": None, "periodicity": None}
            continue
        allowed = ind["periodicities"]
        per = next((p for p in ["M", "Q", "A"] if p in allowed and order[p] <= order[base_p]), allowed[-1])
        latest = CURRENT_YEAR - lag - (0 if ind["tier"] == 1 else random.choice([0, 1, 2]))
        win = CA.SCORING["coverage"]["coverage_window_years"]
        cov_ok = (CURRENT_YEAR - latest) <= win
        grid[ind["code"]] = {"covered": cov_ok, "latest": latest, "periodicity": per}
        if cov_ok:
            got += ind["weight"]
        if ind["tier"] == 1:
            if order[per] > best_rank:
                best_rank, best_p = order[per], per
            for y in range(CURRENT_YEAR - 10, latest + 1):
                if random.random() < reg:
                    tier1_years.add(y)
            tier1_years.add(latest)

    coverage = round(100.0 * got / wtot, 1) if wtot else 0.0

    pts = CA.SCORING["frequency"]["periodicity_points"]
    reg_win = CA.SCORING["frequency"]["regularity_window_years"]
    reg_from = CURRENT_YEAR - reg_win
    ry = len([y for y in tier1_years if y >= reg_from])
    frequency = round(_clamp((pts.get(best_p, pts["irregular"]) + 100.0 * ry / reg_win) / 2.0), 1)

    latest = max([g["latest"] for g in grid.values() if g["latest"]], default=None)
    rc = CA.SCORING["recency"]
    if latest is None:
        recency = 0.0
    else:
        span = rc["zero_marks_min_age"] - rc["full_marks_max_age"]
        recency = round(_clamp(100.0 * (rc["zero_marks_min_age"] - (CURRENT_YEAR - latest)) / span), 1)

    n_cov = sum(1 for g in grid.values() if g["covered"])
    return coverage, frequency, recency, latest, best_p, grid, n_cov


def main():
    records = []
    for iso, name, region, maturity in COUNTRIES:
        cov, freq, rec, latest, best_p, grid, n_cov = score(maturity)
        if latest:
            k = 1 if maturity >= 0.7 else 2
            src_names = random.sample(ADMIN_SOURCES, k=min(k, len(ADMIN_SOURCES)))
            sources = [{"name": s, "latest": latest} for s in src_names]
        else:
            sources = []
        records.append({
            "iso3": iso, "country": name, "region": region,
            "coverage": cov, "frequency": freq, "recency": rec,
            "latest_year": latest, "best_periodicity": best_p if latest else "irregular",
            "n_covered": n_cov, "n_total": len(CA.KEY_INDICATORS),
            "sources": sources,
            "indicators": {c["code"]: grid[c["code"]] for c in CA.KEY_INDICATORS},
        })

    payload = {
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "current_year": CURRENT_YEAR,
        "index_name": CA.INDEX_NAME,
        "source": "SAMPLE DATA (illustrative) — replace via fetch_and_rank.py --config config_admin",
        "is_sample": True,
        "default_weights": CA.SCORING["weights"],
        "scoring_params": {k: v for k, v in CA.SCORING.items() if k != "weights"},
        "indicators": [
            {"code": i["code"], "label": i["label"], "tier": i["tier"], "weight": i["weight"]}
            for i in CA.KEY_INDICATORS
        ],
        "countries": records,
    }
    out = os.path.join(os.path.dirname(__file__), "..", "web", "admin", "data")
    write_output(payload, os.path.abspath(out))


if __name__ == "__main__":
    main()
