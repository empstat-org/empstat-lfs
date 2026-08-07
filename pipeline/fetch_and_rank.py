#!/usr/bin/env python3
"""
ILOSTAT Labour Market Information (LMI) Ranking — data pipeline.

What it does
------------
1. Reads the indicator set, household-survey filter and scoring rules from config.py
2. Downloads the ILOSTAT source code list (to tell household surveys apart from
   administrative / establishment / census sources)
3. For every key indicator, downloads the relevant bulk-download CSV(s)
4. Keeps only observations that come from a household survey
5. For each country builds a per-indicator availability record
   (covered?, latest year, best periodicity, number of recent years)
6. Turns that into three 0-100 sub-scores — coverage, frequency, recency
7. Writes ../web/data/rankings.json and ../web/data/rankings.js

The website reads rankings.js. Re-run this whenever you change config.py.

Usage
-----
    pip install -r requirements.txt
    python fetch_and_rank.py                 # full run, all key indicators
    python fetch_and_rank.py --limit 3       # quick test: first 3 indicators only
    python fetch_and_rank.py --out ../web/data

Notes
-----
* ILOSTAT bulk files can be large; the script streams and gzip-decodes them.
* If a single indicator file 404s or times out it is skipped with a warning,
  so one missing series never aborts the whole run.
* Country names/regions come from ILOSTAT's own reference-area table of contents.
"""

import argparse
import csv
import gzip
import importlib
import io
import json
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime

import requests

import config as C

HTTP_TIMEOUT = 120
CURRENT_YEAR = datetime.now().year


# --------------------------------------------------------------------------- #
# Time-period helpers  (annual "2024", quarterly "2024Q4", monthly "2024M07")
# Used for the "pending in ILOSTAT" feature: comparing ILOSTAT's latest period
# against what an NSO has already released.
# --------------------------------------------------------------------------- #
def parse_period(s):
    """'2024', '2024Q4', '2024M07' -> (year, kind, sub) or None."""
    if not s:
        return None
    m = re.match(r"^(\d{4})(?:Q([1-4])|M(\d{1,2}))?$", str(s).strip().upper())
    if not m:
        return None
    y = int(m.group(1))
    if m.group(2):
        return (y, "Q", int(m.group(2)))
    if m.group(3):
        return (y, "M", int(m.group(3)))
    return (y, "A", 0)


def coerce_period(s, per):
    """Express a period at the target periodicity ('A'|'Q'|'M')."""
    p = parse_period(s)
    if not p:
        return None
    y, k, sub = p
    if per == "A":
        return f"{y}"
    if per == "Q":
        q = sub if k == "Q" else (min(4, (sub - 1) // 3 + 1) if k == "M" else 4)
        return f"{y}Q{q}"
    if per == "M":
        mo = sub if k == "M" else (sub * 3 if k == "Q" else 12)
        return f"{y}M{mo:02d}"
    return s


def period_sort_key(s):
    """Monotonic ordering key that works across periodicities."""
    p = parse_period(s)
    if not p:
        return (-1, 0.0)
    y, k, sub = p
    scale = {"A": 1, "Q": 4, "M": 12}[k]
    return (y, sub / scale)


def next_period(s, per):
    """The period immediately after s, at periodicity per."""
    s = coerce_period(s, per)
    y, k, sub = parse_period(s)
    if per == "A":
        return f"{y + 1}"
    if per == "Q":
        q = sub + 1
        return f"{y + 1}Q1" if q > 4 else f"{y}Q{q}"
    if per == "M":
        mo = sub + 1
        return f"{y + 1}M01" if mo > 12 else f"{y}M{mo:02d}"
    return s


def enumerate_pending(ilostat_latest, nso_latest, per, cap=48):
    """Periods released by the NSO but newer than ILOSTAT's latest."""
    if not ilostat_latest or not nso_latest:
        return []
    cur = coerce_period(ilostat_latest, per)
    target = coerce_period(nso_latest, per)
    out, guard = [], 0
    while period_sort_key(cur) < period_sort_key(target) and guard < cap:
        cur = next_period(cur, per)
        out.append(cur)
        guard += 1
    return out


def load_nso_registry():
    """Load the curated NSO-latest-release registry (optional)."""
    path = os.path.join(os.path.dirname(__file__), "nso_releases.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return {k: v for k, v in data.items() if not k.startswith("_")}
    except Exception as e:  # noqa: BLE001
        print(f"  ! could not read nso_releases.json ({e})", file=sys.stderr)
        return {}


def compute_pending(iso, ilostat_latest_period, best_periodicity, registry):
    """Return a pending dict for a country, or None if nothing pending/tracked."""
    entry = registry.get(iso)
    if not entry:
        return None
    nso_latest = entry.get("nso_latest")
    per = entry.get("periodicity") or best_periodicity or "A"
    if per == "irregular":
        per = "A"
    periods = enumerate_pending(ilostat_latest_period, nso_latest, per)
    if not periods:
        return None
    return {
        "nso": entry.get("nso", ""),
        "nso_latest": nso_latest,
        "periodicity": per,
        "periods": periods,
        "count": len(periods),
        "source": entry.get("source", ""),
        "checked": entry.get("checked", ""),
        "note": entry.get("note", ""),
    }


# --------------------------------------------------------------------------- #
# HTTP helpers
# --------------------------------------------------------------------------- #
def _get(url, as_text=True):
    r = requests.get(url, timeout=HTTP_TIMEOUT, headers={"User-Agent": "lmi-ranking/1.0"})
    r.raise_for_status()
    return r.text if as_text else r.content


def load_indicator_toc():
    """Return the set of valid dataset ids from the rplumber indicator toc."""
    try:
        rows = list(_get_csv_rows(C.ILOSTAT["toc_indicator"]))
        ids = set()
        for r in rows:
            i = (r.get("id") or r.get("ID") or r.get("indicator") or "").strip()
            if i:
                ids.add(i)
        if ids:
            print(f"  indicator table of contents loaded ({len(ids)} datasets)")
            return ids
    except Exception as e:  # noqa: BLE001
        print(f"  ! could not load indicator toc ({e}); will attempt downloads directly")
    return None


def dataset_url(dataset_id):
    """rplumber data endpoint returning CSV with codes + labels (type=both)."""
    frm = CURRENT_YEAR - C.ILOSTAT.get("years_back", 25)
    return (f"{C.ILOSTAT['data_api']}?id={dataset_id}"
            f"&type=both&timefrom={frm}&format=.csv")


def _get_csv_rows(url):
    """Download a (possibly gzipped) CSV and yield dict rows."""
    content = _get(url, as_text=False)
    if url.endswith(".gz"):
        content = gzip.decompress(content)
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        yield row


# --------------------------------------------------------------------------- #
# Reference data: source labels, country names/regions
# --------------------------------------------------------------------------- #
def is_household_source(label):
    """True if a source LABEL (e.g. 'Labour force survey') is an included source
    for this index, per the config keywords."""
    l = (label or "").lower()
    if any(x in l for x in C.SOURCE_EXCLUDE_KEYWORDS):
        return False
    return any(x in l for x in C.HOUSEHOLD_SURVEY_KEYWORDS)


def load_countries():
    """Return {iso3: {'name':..., 'region':...}} from ILOSTAT ref_area toc."""
    out = {}
    try:
        rows = list(_get_csv_rows(C.ILOSTAT["toc_ref_area"]))
        for row in rows:
            iso = (row.get("ref_area") or row.get("id") or row.get("code") or "").strip()
            name = (row.get("ref_area.label") or row.get("label") or row.get("name") or "").strip()
            # the live ref_area API has no region column, so use our baked-in map
            region = getattr(C, "REGIONS", {}).get(iso, "Other")
            # ILOSTAT ref_area includes regional aggregates (X..) — keep 3-letter ISO only
            if iso and len(iso) == 3 and iso.isalpha():
                out[iso] = {"name": name or iso, "region": region}
    except Exception as e:  # noqa: BLE001
        print(f"  ! could not load country list ({e})", file=sys.stderr)
    return out


# --------------------------------------------------------------------------- #
# Core: gather per-country / per-indicator availability
# --------------------------------------------------------------------------- #
def year_of(time_str):
    """'2023', '2023Q3', '2023M07' -> 2023 (int) or None."""
    if not time_str:
        return None
    try:
        return int(str(time_str)[:4])
    except ValueError:
        return None


def gather(limit=None):
    """
    Returns:
      avail[iso][code] = {
          'covered': bool,          # any qualifying obs in coverage window
          'latest': int|None,       # latest year of qualifying obs
          'periodicity': 'M'|'Q'|'A'|None,   # best periodicity found
          'recent_years': set(int), # years with a qualifying obs (last decade+)
      }
    """
    toc_ids = load_indicator_toc()
    print(f"  using data API: {C.ILOSTAT['data_api']}")

    indicators = C.KEY_INDICATORS[:limit] if limit else C.KEY_INDICATORS
    avail = defaultdict(dict)
    sources = defaultdict(dict)  # iso -> {survey label: latest year seen}
    diagnosed = False

    for ind in indicators:
        key = ind["code"]                                   # stable key for this indicator
        fetch_codes = ind.get("codes", [ind["code"]])       # 1+ ILOSTAT codes, priority order
        code_labels = ind.get("code_labels", {})
        for ci, base in enumerate(fetch_codes):
          for period in ind["periodicities"]:
            dataset_id = f"{base}_{period}"
            if toc_ids is not None and dataset_id not in toc_ids:
                continue  # not a real ILOSTAT dataset (e.g. this indicator has no such periodicity)
            url = dataset_url(dataset_id)
            print(f"  fetching {dataset_id} ...", flush=True)
            try:
                rows = list(_get_csv_rows(url))
                # One-time diagnostic: show real columns + example source labels.
                if not diagnosed and rows:
                    cols = list(rows[0].keys())
                    seen = []
                    for rr in rows:
                        sv = (rr.get("source.label") or rr.get("source_label")
                              or rr.get("source") or "").strip()
                        if sv and sv not in seen:
                            seen.append(sv)
                        if len(seen) >= 12:
                            break
                    print(f"    [diag] columns: {cols}")
                    print(f"    [diag] sample source labels: {seen}")
                    diagnosed = True
                n = 0
                for row in rows:
                    iso = ("" if row.get("ref_area") is None else str(row.get("ref_area"))).strip()
                    if len(iso) != 3 or not iso.isalpha() or not iso.isupper():
                        continue
                    # fallback preference: if a higher-priority code already
                    # populated this indicator for the country, ignore later codes
                    if ci > 0 and key in avail[iso]:
                        continue
                    src_label = (row.get("source.label") or row.get("source_label") or "").strip()
                    if not src_label:
                        src_label = ("" if row.get("source") is None else str(row.get("source"))).strip()
                    if src_label.lower() == "nan":
                        src_label = ""
                    if not is_household_source(src_label):
                        continue
                    yr = year_of(row.get("time"))
                    if yr is None:
                        continue
                    lbl = src_label
                    if lbl and (lbl not in sources[iso] or yr > sources[iso][lbl]):
                        sources[iso][lbl] = yr
                    rec = avail[iso].get(key)
                    if rec is None:
                        rec = {"covered": False, "latest": None, "latest_period": None,
                               "periodicity": None, "recent_years": set(), "via": None}
                        avail[iso][key] = rec
                    if len(fetch_codes) > 1:
                        rec["via"] = code_labels.get(base, base)
                    rec["recent_years"].add(yr)
                    if rec["latest"] is None or yr > rec["latest"]:
                        rec["latest"] = yr
                    tstr = str(row.get("time") or "").strip()
                    if rec["latest_period"] is None or \
                            period_sort_key(tstr) > period_sort_key(rec["latest_period"]):
                        rec["latest_period"] = tstr
                    # keep the most frequent periodicity seen (M>Q>A)
                    order = {"M": 3, "Q": 2, "A": 1, None: 0}
                    if order[period] > order[rec["periodicity"]]:
                        rec["periodicity"] = period
                    n += 1
                print(f"      kept {n} household-survey observations")
            except requests.HTTPError as e:
                print(f"      skip ({e.response.status_code})")
            except Exception as e:  # noqa: BLE001
                print(f"      skip ({e})")
            time.sleep(0.3)  # be polite to the server

    # finalise 'covered' using the coverage window
    win = C.SCORING["coverage"]["coverage_window_years"]
    cutoff = CURRENT_YEAR - win if win else None
    for iso, inds in avail.items():
        for base, rec in inds.items():
            rec["covered"] = rec["latest"] is not None and (cutoff is None or rec["latest"] >= cutoff)
    return avail, sources


# --------------------------------------------------------------------------- #
# Scoring  (identical formulas are documented in README.md)
# --------------------------------------------------------------------------- #
def _clamp(x, lo=0.0, hi=100.0):
    return max(lo, min(hi, x))


def score_country(inds):
    """inds = {code: availability record}. Returns (coverage, frequency, recency, meta)."""
    weight_by_code = {i["code"]: i["weight"] for i in C.KEY_INDICATORS}
    tier1 = [i["code"] for i in C.KEY_INDICATORS if i["tier"] == 1]

    # ---- coverage ---------------------------------------------------------
    total_w = sum(weight_by_code.values())
    got_w = sum(weight_by_code[c] for c in weight_by_code
                if inds.get(c, {}).get("covered"))
    coverage = 100.0 * got_w / total_w if total_w else 0.0

    # ---- frequency / regularity (optional: some indices omit this) --------
    order = {"M": 3, "Q": 2, "A": 1}
    best_p, best_rank = "irregular", -1
    for c in tier1:
        p = inds.get(c, {}).get("periodicity")
        if p and order.get(p, 0) > best_rank:
            best_rank, best_p = order[p], p
    if "frequency" in C.SCORING:
        pts = C.SCORING["frequency"]["periodicity_points"]
        periodicity_score = pts.get(best_p, pts["irregular"])
        reg_win = C.SCORING["frequency"]["regularity_window_years"]
        reg_from = CURRENT_YEAR - reg_win
        years_covered = set()
        for c in tier1:
            years_covered |= {y for y in inds.get(c, {}).get("recent_years", set()) if y >= reg_from}
        regularity_score = 100.0 * len(years_covered) / reg_win if reg_win else 0.0
        frequency = round(_clamp((periodicity_score + regularity_score) / 2.0), 1)
    else:
        frequency = None

    # ---- recency ----------------------------------------------------------
    latest = max([rec["latest"] for rec in inds.values() if rec.get("latest")], default=None)
    rc = C.SCORING["recency"]
    if latest is None:
        recency = 0.0
    else:
        age = CURRENT_YEAR - latest
        span = rc["zero_marks_min_age"] - rc["full_marks_max_age"]
        recency = _clamp(100.0 * (rc["zero_marks_min_age"] - age) / span) if span > 0 else 100.0

    # most recent ILOSTAT *period* (for the pending-data comparison), from headline
    latest_period = None
    for c in tier1:
        lp = inds.get(c, {}).get("latest_period")
        if lp and (latest_period is None or period_sort_key(lp) > period_sort_key(latest_period)):
            latest_period = lp

    meta = {
        "latest_year": latest,
        "latest_period": latest_period,
        "best_periodicity": best_p,
        "n_covered": sum(1 for c in weight_by_code if inds.get(c, {}).get("covered")),
        "n_total": len(weight_by_code),
    }
    return round(coverage, 1), frequency, round(recency, 1), meta


# --------------------------------------------------------------------------- #
# Assemble output
# --------------------------------------------------------------------------- #
def build(limit=None):
    print("Loading reference data ...")
    countries = load_countries()
    print(f"  {len(countries)} countries in ILOSTAT ref_area list")

    print("Gathering indicator availability ...")
    avail, sources = gather(limit=limit)

    print("Scoring ...")
    pending_on = getattr(C, "ENABLE_PENDING", True)
    registry = load_nso_registry() if pending_on else {}
    if pending_on:
        print(f"  NSO release registry entries: {len(registry)}")
    records = []
    for iso, inds in avail.items():
        cov, freq, rec, meta = score_country(inds)
        info = countries.get(iso, {"name": iso, "region": "Other"})
        pending = compute_pending(iso, meta["latest_period"], meta["best_periodicity"], registry) if pending_on else None
        records.append({
            "iso3": iso,
            "country": info["name"],
            "region": info["region"],
            "coverage": cov,
            "frequency": freq,
            "recency": rec,
            "latest_year": meta["latest_year"],
            "latest_period": meta["latest_period"],
            "best_periodicity": meta["best_periodicity"],
            "n_covered": meta["n_covered"],
            "n_total": meta["n_total"],
            "pending": pending,
            "sources": [
                {"name": name, "latest": yr}
                for name, yr in sorted(sources.get(iso, {}).items(),
                                       key=lambda kv: (-kv[1], kv[0]))
            ],
            "indicators": {
                code: {
                    "covered": inds.get(code, {}).get("covered", False),
                    "latest": inds.get(code, {}).get("latest"),
                    "periodicity": inds.get(code, {}).get("periodicity"),
                    "via": inds.get(code, {}).get("via"),
                }
                for code in [i["code"] for i in C.KEY_INDICATORS]
            },
        })

    payload = {
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "current_year": CURRENT_YEAR,
        "index_name": getattr(C, "INDEX_NAME", "LFS Coverage Index"),
        "source": "ILOSTAT (ilostat.ilo.org)",
        "default_weights": C.SCORING["weights"],
        "scoring_params": {k: v for k, v in C.SCORING.items() if k != "weights"},
        "indicators": [
            {"code": i["code"], "label": i["label"], "tier": i["tier"], "weight": i["weight"]}
            for i in C.KEY_INDICATORS
        ],
        "countries": records,
    }
    return payload


def write_output(payload, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, "rankings.json")
    js_path = os.path.join(out_dir, "rankings.js")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    with open(js_path, "w", encoding="utf-8") as f:
        f.write("// Auto-generated by fetch_and_rank.py — do not edit by hand.\n")
        f.write("window.RANKINGS = ")
        json.dump(payload, f, ensure_ascii=False)
        f.write(";\n")
    print(f"Wrote {json_path}")
    print(f"Wrote {js_path}")
    print(f"Countries scored: {len(payload['countries'])}")


def main():
    ap = argparse.ArgumentParser(description="Build ILOSTAT coverage rankings")
    ap.add_argument("--limit", type=int, default=None,
                    help="only process the first N key indicators (quick test)")
    ap.add_argument("--config", default="config",
                    help="config module to use: 'config' (LFS), 'config_census', 'config_admin'")
    ap.add_argument("--out", default=None,
                    help="output directory for rankings.js/json")
    args = ap.parse_args()

    # swap in the chosen config for all functions that reference the module global C
    global C
    C = importlib.import_module(args.config)

    out = args.out or os.path.join(os.path.dirname(__file__), "..", "web", "data")
    print(f"Config: {args.config}  ({getattr(C, 'INDEX_NAME', 'LFS Coverage Index')})")
    payload = build(limit=args.limit)

    # Safety net: never overwrite the published site with an empty/short result
    # (e.g. if ILOSTAT is unreachable or a URL changed). Leave existing data in
    # place and exit cleanly so the site still deploys with its last-good data.
    n = len(payload["countries"])
    min_n = C.ILOSTAT.get("min_countries", 0)
    if n < min_n:
        print(f"Only {n} countries scored (minimum {min_n}). "
              f"Keeping existing data; not overwriting. This usually means the "
              f"ILOSTAT download URL needs updating — check the log above.")
        return
    write_output(payload, os.path.abspath(out))


if __name__ == "__main__":
    main()
