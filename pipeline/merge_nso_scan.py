#!/usr/bin/env python3
"""
merge_nso_scan.py — merge a monthly NSO scan into the pending-data registry.

The scan (see SCAN_PROCEDURE.md) produces a *candidate* file: for each country,
the latest labour-force period that country's NSO appears to have published.
This script merges those candidates into `nso_releases.json` under strict
guardrails, and writes a human-readable report of everything that changed.

Guardrails (deliberately conservative — the registry drives a public site):
  * NEVER REGRESS. A candidate older than the stored value is refused and
    flagged. A bad parse can therefore never shrink a country's pending count.
  * FAILED SCANS ARE INERT. A country the scan could not resolve keeps its
    existing entry untouched, including its old `checked` date, so a stale
    entry is visibly stale rather than silently "re-confirmed".
  * LOW CONFIDENCE IS QUARANTINED. Candidates below --min-confidence are
    reported but not written.
  * FUTURE PERIODS ARE REFUSED. An NSO cannot have published a period that
    has not ended yet; such candidates indicate a misparse.

Usage
-----
  python merge_nso_scan.py --candidates scan_candidates.json \
                           --registry nso_releases.json \
                           --report scan_report.md
  python merge_nso_scan.py --candidates scan_candidates.json --dry-run

Candidate file schema
---------------------
{
  "_scan_date": "2026-09-01",
  "JAM": {
    "nso": "STATIN",
    "nso_latest": "2026Q2",
    "periodicity": "Q",
    "source": "https://statinja.gov.jm/LabourForce/NewLFS.aspx",
    "confidence": "high",          # high | medium | low | failed
    "method": "web",               # eurostat | api | web
    "note": "Quarterly Labour Force Survey",
    "evidence": "Release page headline: 'Labour Force Survey April 2026'"
  },
  ...
}
"""

import argparse
import json
import os
import re
import sys
from datetime import date, datetime

CONFIDENCE_ORDER = {"failed": 0, "low": 1, "medium": 2, "high": 3}

# Keys we preserve from the existing registry when a scan fails or is refused.
PRESERVED_KEYS = ("nso", "nso_latest", "periodicity", "source", "checked", "note")


# --------------------------------------------------------------------------- #
# Period helpers — MUST stay behaviourally identical to fetch_and_rank.py
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
        mo = int(m.group(3))
        if not 1 <= mo <= 12:
            return None
        return (y, "M", mo)
    return (y, "A", 0)


def period_sort_key(s):
    """Monotonic ordering key that works across periodicities."""
    p = parse_period(s)
    if not p:
        return (-1, 0.0)
    y, k, sub = p
    scale = {"A": 1, "Q": 4, "M": 12}[k]
    return (y, sub / scale)


MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun",
     "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}


def coerce_loose(s):
    """Accept common human/scraped spellings and return canonical form.

    Handles '2026-Q2', 'Q2 2026', 'Q2-2026', '2026-06', '2026M6',
    'June 2026', 'Jun-2026', '2026 Q2'. Returns None if it cannot tell.
    Deliberately refuses ambiguous all-numeric pairs like '06/2026'
    rather than guessing month vs quarter.
    """
    if s is None:
        return None
    t = str(s).strip().upper().replace("_", " ")
    if not t:
        return None

    # Already canonical
    if re.match(r"^\d{4}(Q[1-4]|M\d{1,2})?$", t):
        return t

    # 2026-Q2 / 2026 Q2
    m = re.match(r"^(\d{4})[\s\-/]*Q([1-4])$", t)
    if m:
        return f"{m.group(1)}Q{m.group(2)}"

    # Q2 2026 / Q2-2026
    m = re.match(r"^Q([1-4])[\s\-/]*(\d{4})$", t)
    if m:
        return f"{m.group(2)}Q{m.group(1)}"

    # 2026-06 / 2026M6 / 2026 06  (2-digit tail <= 12 -> month)
    m = re.match(r"^(\d{4})[\s\-/M]+(\d{1,2})$", t)
    if m and 1 <= int(m.group(2)) <= 12:
        return f"{m.group(1)}M{int(m.group(2)):02d}"

    # June 2026 / Jun-2026
    m = re.match(r"^([A-Z]{3,9})[\s\-/,]+(\d{4})$", t)
    if m:
        mo = MONTHS.get(m.group(1)[:3].lower())
        if mo:
            return f"{m.group(2)}M{mo:02d}"

    # 2026 June
    m = re.match(r"^(\d{4})[\s\-/,]+([A-Z]{3,9})$", t)
    if m:
        mo = MONTHS.get(m.group(2)[:3].lower())
        if mo:
            return f"{m.group(1)}M{mo:02d}"

    return None


def normalise_period(s):
    """Canonical form: 2026Q2, 2026M06, 2026. Returns None if unparseable."""
    s = coerce_loose(s) or s
    p = parse_period(s)
    if not p:
        return None
    y, k, sub = p
    if k == "Q":
        return f"{y}Q{sub}"
    if k == "M":
        return f"{y}M{sub:02d}"
    return f"{y}"


def period_end_date(s):
    """Last calendar day covered by a period — used for the future check."""
    p = parse_period(s)
    if not p:
        return None
    y, k, sub = p
    if k == "A":
        return date(y, 12, 31)
    m = sub * 3 if k == "Q" else sub
    if m == 12:
        return date(y, 12, 31)
    return date.fromordinal(date(y, m + 1, 1).toordinal() - 1)


# --------------------------------------------------------------------------- #
# Merge
# --------------------------------------------------------------------------- #
def load_json(path, what):
    if not os.path.exists(path):
        sys.exit(f"error: {what} not found at {path}")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        sys.exit(f"error: {what} is not valid JSON ({e})")


def merge(registry, candidates, scan_date, min_confidence, allow_future_days=0):
    """Return (new_registry, events). Does not mutate inputs."""
    out = {k: v for k, v in registry.items()}
    events = []
    threshold = CONFIDENCE_ORDER.get(min_confidence, 2)
    today = date.today()

    for iso, cand in sorted(candidates.items()):
        if iso.startswith("_"):
            continue
        if not isinstance(cand, dict):
            events.append((iso, "malformed", "candidate entry is not an object", None, None))
            continue

        existing = registry.get(iso)
        old_period = (existing or {}).get("nso_latest")
        conf = str(cand.get("confidence", "low")).lower()
        raw = cand.get("nso_latest")
        new_period = normalise_period(raw)

        # --- failed / unresolvable -------------------------------------- #
        if conf == "failed" or not raw:
            events.append((iso, "failed", cand.get("evidence") or "scan could not resolve a period",
                           old_period, None))
            continue

        if new_period is None:
            events.append((iso, "unparseable", f"could not parse period {raw!r}", old_period, None))
            continue

        # --- future period ----------------------------------------------- #
        pend = period_end_date(new_period)
        if pend and (pend - today).days > allow_future_days:
            events.append((iso, "future", f"{new_period} has not finished yet (ends {pend})",
                           old_period, new_period))
            continue

        # --- confidence --------------------------------------------------- #
        if CONFIDENCE_ORDER.get(conf, 0) < threshold:
            events.append((iso, "low_confidence", f"confidence={conf}", old_period, new_period))
            continue

        # --- regression ---------------------------------------------------- #
        if old_period:
            old_norm = normalise_period(old_period)
            if old_norm and period_sort_key(new_period) < period_sort_key(old_norm):
                # A verified correction may move a date BACKWARDS. This exists
                # because the seeded registry contained illustrative dates that
                # were simply wrong (e.g. KEN claimed 2025Q4 for a series that
                # was discontinued after 2022Q4). Requires an explicit flag plus
                # evidence, and is always reported loudly.
                if cand.get("regression_verified") and conf == "high":
                    entry = dict(existing)
                    entry["nso"] = cand.get("nso") or entry.get("nso", "")
                    entry["nso_latest"] = new_period
                    entry["periodicity"] = cand.get("periodicity") or entry.get("periodicity") or "Q"
                    entry["source"] = cand.get("source") or entry.get("source", "")
                    entry["checked"] = scan_date
                    if cand.get("note"):
                        entry["note"] = cand["note"]
                    out[iso] = entry
                    events.append((iso, "corrected",
                                   f"VERIFIED correction {old_norm} -> {new_period}: "
                                   f"{cand.get('evidence', 'no evidence given')}",
                                   old_period, new_period))
                    continue
                events.append((iso, "regression",
                               f"scan found {new_period}, older than stored {old_norm}",
                               old_period, new_period))
                continue
            if old_norm and period_sort_key(new_period) == period_sort_key(old_norm):
                # Same period re-confirmed: refresh `checked` only.
                entry = dict(existing)
                entry["checked"] = scan_date
                for k in ("nso", "source", "note"):
                    if cand.get(k):
                        entry[k] = cand[k]
                out[iso] = entry
                events.append((iso, "confirmed", "unchanged, checked date refreshed",
                               old_period, new_period))
                continue

        # --- accepted -------------------------------------------------------- #
        entry = dict(existing) if existing else {}
        entry["nso"] = cand.get("nso") or entry.get("nso", "")
        entry["nso_latest"] = new_period
        entry["periodicity"] = cand.get("periodicity") or entry.get("periodicity") or "Q"
        entry["source"] = cand.get("source") or entry.get("source", "")
        entry["checked"] = scan_date
        note = cand.get("note") or entry.get("note", "")
        if cand.get("method") == "eurostat":
            marker = "via Eurostat (lower bound — national release may be newer)"
            note = f"{note}; {marker}" if note and marker not in note else (note or marker)
        entry["note"] = note
        out[iso] = entry
        events.append((iso, "new" if not existing else "advanced",
                       "first time tracked" if not existing else f"{old_period} -> {new_period}",
                       old_period, new_period))

    return out, events


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #
CATEGORY_TITLES = [
    ("advanced", "Advanced — new periods published", True),
    ("new", "Newly tracked countries", True),
    ("corrected", "Corrected backwards (verified — please sanity-check)", True),
    ("regression", "REVIEW: scan found an OLDER period than stored", True),
    ("future", "REVIEW: scan returned a period that has not ended", True),
    ("low_confidence", "Quarantined — low confidence, not written", True),
    ("unparseable", "REVIEW: unparseable period returned", True),
    ("malformed", "REVIEW: malformed candidate entry", True),
    ("failed", "Not resolved this run (entry left untouched)", False),
    ("confirmed", "Confirmed unchanged", False),
]


def write_report(path, events, registry_before, registry_after, scan_date, candidates):
    by_cat = {}
    for ev in events:
        by_cat.setdefault(ev[1], []).append(ev)

    tracked_before = len([k for k in registry_before if not k.startswith("_")])
    tracked_after = len([k for k in registry_after if not k.startswith("_")])
    scanned = len([k for k in candidates if not k.startswith("_")])

    L = []
    L.append(f"# NSO release scan — {scan_date}\n")
    L.append(f"- Countries scanned: **{scanned}**")
    L.append(f"- Tracked in registry: **{tracked_before} -> {tracked_after}**")
    L.append(f"- Dates advanced: **{len(by_cat.get('advanced', []))}**")
    L.append(f"- Newly tracked: **{len(by_cat.get('new', []))}**")
    L.append(f"- Backward corrections applied: **{len(by_cat.get('corrected', []))}**")
    needs_review = sum(len(by_cat.get(c, [])) for c in
                       ("regression", "future", "unparseable", "malformed"))
    L.append(f"- **Needing review: {needs_review}**")
    L.append(f"- Not resolved: **{len(by_cat.get('failed', []))}**\n")

    if needs_review:
        L.append("> Items under REVIEW were **not written** to the registry. "
                 "Check them against the NSO site before accepting.\n")

    for cat, title, always in CATEGORY_TITLES:
        rows = by_cat.get(cat, [])
        if not rows:
            continue
        L.append(f"\n## {title} ({len(rows)})\n")
        L.append("| ISO3 | Stored | Scan found | Detail |")
        L.append("|---|---|---|---|")
        for iso, _c, detail, old, new in sorted(rows):
            L.append(f"| {iso} | {old or '—'} | {new or '—'} | {detail} |")

    L.append("\n---\n")
    L.append("Generated by `merge_nso_scan.py`. Registry drives the "
             "\"pending data\" badges on lfs.empstat.org.\n")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L))


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--candidates", required=True, help="scan candidate JSON")
    ap.add_argument("--registry", default="nso_releases.json", help="registry to update")
    ap.add_argument("--report", default="scan_report.md", help="markdown report to write")
    ap.add_argument("--min-confidence", default="medium",
                    choices=["low", "medium", "high"],
                    help="lowest confidence written to the registry (default: medium)")
    ap.add_argument("--scan-date", default=None, help="YYYY-MM-DD (default: today)")
    ap.add_argument("--dry-run", action="store_true",
                    help="report only; do not modify the registry")
    args = ap.parse_args()

    scan_date = args.scan_date or date.today().isoformat()
    try:
        datetime.strptime(scan_date, "%Y-%m-%d")
    except ValueError:
        sys.exit(f"error: --scan-date must be YYYY-MM-DD, got {scan_date!r}")

    registry = load_json(args.registry, "registry")
    candidates = load_json(args.candidates, "candidates")

    meta = {k: v for k, v in registry.items() if k.startswith("_")}
    data = {k: v for k, v in registry.items() if not k.startswith("_")}

    merged, events = merge(data, candidates, scan_date, args.min_confidence)

    write_report(args.report, events, data, merged, scan_date, candidates)

    if args.dry_run:
        print(f"[dry-run] {args.report} written; {args.registry} untouched")
    else:
        meta.pop("_WARNING", None)
        meta["_last_scan"] = scan_date
        ordered = {}
        ordered.update(meta)
        for iso in sorted(merged):
            ordered[iso] = merged[iso]
        with open(args.registry, "w", encoding="utf-8") as f:
            json.dump(ordered, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"wrote {args.registry} ({len(merged)} countries) and {args.report}")

    counts = {}
    for ev in events:
        counts[ev[1]] = counts.get(ev[1], 0) + 1
    for k in sorted(counts):
        print(f"  {k}: {counts[k]}")


if __name__ == "__main__":
    main()
