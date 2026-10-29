"""What the Power BI report should show, recomputed from data/published/metric_values.csv the way the DAX does it
(sum numerators, sum denominators, divide) and checked against summary.json. Run from powerbi/:  python tools/expected.py"""
import json
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(os.path.dirname(ROOT), "data", "published")
mv = pd.read_csv(os.path.join(PUB, "metric_values.csv"))
S = json.load(open(os.path.join(PUB, "summary.json")))
q = pd.read_csv(os.path.join(PUB, "quality_report.csv"))
problems = []


def value(metric, dim="total", member=None):
    r = mv[(mv.metric_id == metric) & (mv.dimension == dim)]
    if member is not None:
        r = r[r.member == member]
    # mirrors the DAX: no denominator (counts, sums) -> add up; otherwise sum the parts and divide
    return r.numerator.sum() if r.denominator.isna().all() else r.numerator.sum() / r.denominator.sum()


def check(label, got, want, tol=1e-9):
    if abs(got - want) > tol:
        problems.append(f"{label}: {got} vs {want}")


check("Listings", value("listings"), S["listings"])
check("Active listings", value("active_listings"), S["active_listings"])
check("Occupancy (certified)", value("occupancy_rate"), S["occupancy"]["occupancy_rate"])
check("Over 90 homes", value("over_90_homes"), S["over_90_homes"])
check("Share over 90", value("over_90_share"), S["over_90_share"])
b = mv[(mv.metric_id == "over_90_homes") & (mv.dimension == "borough")].sort_values("numerator", ascending=False)
top5 = b.head(5).numerator.sum() / S["over_90_homes"]
check("Top 5 borough share", top5, S["top5_share"])
for mid in ["occupancy_rate", "over_90_share", "active_listings"]:
    whole = value(mid)
    rebuilt = value(mid, "borough")  # all boroughs together, re-aggregated from parts
    check(f"{mid}: boroughs re-aggregate to London", rebuilt, whole)
occ = {m: value(m) for m in ["occupancy_all_listings", "occupancy_rate", "occupancy_of_bookable", "occupancy_calendar_unavailable"]}
names = {"occupancy_all_listings": "Occupancy: modelled, all listings", "occupancy_rate": "Occupancy rate (certified)",
         "occupancy_of_bookable": "Occupancy: booked share of bookable nights", "occupancy_calendar_unavailable": "Occupancy: calendar unavailable"}
hs = mv[(mv.metric_id == "over_90_homes") & (mv.dimension == "host_size")].sort_values("member_order")
lines = ["# Expected values", "", "From `tools/expected.py`, re-aggregated from `metric_values.csv` the way the DAX does it, checked against `summary.json`: "
         f"**{'all agree' if not problems else 'DISAGREEMENTS: ' + '; '.join(problems)}**.", "",
         "## Page 1: One number", "", "| Card | Expected |", "|---|---:|",
         f"| Listings | {value('listings'):,.0f} |", f"| Active listings | {value('active_listings'):,.0f} |",
         f"| Occupancy (certified) | {value('occupancy_rate'):.1%} |", f"| Entire homes likely over 90 nights | {value('over_90_homes'):,.0f} |",
         f"| Held by the top 5 boroughs | {top5:.1%} |", "", "| Definition | London |", "|---|---:|",
         *[f"| {names[k]} | {v:.1%} |" for k, v in sorted(occ.items(), key=lambda kv: kv[1])],
         "", "## Page 2: Where (top 10)", "", "| Borough | Over 90 nights | Share over 90 | Occupancy |", "|---|---:|---:|---:|",
         *[f"| {r.member} | {r.numerator:,.0f} | {value('over_90_share', 'borough', r.member):.1%} | {value('occupancy_rate', 'borough', r.member):.1%} |"
           for r in b.head(10).itertuples()],
         "", "## Page 4: Who and how sure", "", "| Card | Expected |", "|---|---:|",
         f"| Quality checks passed | {(q.status == 'pass').sum()} |", f"| Published with a warning | {(q.status == 'warn').sum()} |",
         "", "| Host size | Over 90 nights |", "|---|---:|", *[f"| {r.member} | {r.numerator:,.0f} |" for r in hs.itertuples()]]
os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
open(os.path.join(ROOT, "docs", "expected_values.md"), "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
sys.exit(1 if problems else 0)
