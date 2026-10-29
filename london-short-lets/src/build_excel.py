"""Excel consumer: builds excel/London_Short_Lets_Metrics.xlsx from data/published/.

The 'Metric values' sheet is the published table, unchanged. Every other number is a formula over it (SUMIFS on
numerators and denominators), so Excel re-aggregates ratios the same way the dashboard and Power BI do.

    python src/build_excel.py
"""
import json
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

ROOT = Path(__file__).resolve().parents[1]
PUB = ROOT / "data" / "published"
OUT = ROOT / "excel" / "London_Short_Lets_Metrics.xlsx"
mv = pd.read_csv(PUB / "metric_values.csv").fillna({"member_2": ""})
defs = json.load(open(PUB / "definitions.json"))
qr = pd.read_csv(PUB / "quality_report.csv")
S = json.load(open(PUB / "summary.json"))

F = "Arial"
H = Font(name=F, bold=True, color="FFFFFF")
HF = PatternFill("solid", fgColor="1F4E5A")
B = Font(name=F)
BB = Font(name=F, bold=True)
TITLE = Font(name=F, bold=True, size=14)
NOTE = Font(name=F, italic=True, color="595959", size=9)
GREEN = Font(name=F, color="008000")
thin = Side(style="thin", color="D9D9D9")
PCT, INT = "0.0%", "#,##0"
MVS = "'Metric values'"


def header(ws, row, cols, widths=None):
    for i, c in enumerate(cols, 1):
        cell = ws.cell(row=row, column=i, value=c)
        cell.font, cell.fill = H, HF
        cell.alignment = Alignment(wrap_text=True, vertical="center")
    if widths:
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w


def sumifs(col, metric, dim, member_ref):
    c = {"numerator": "L", "denominator": "M"}[col]
    return f"SUMIFS({MVS}!${c}:${c},{MVS}!$A:$A,\"{metric}\",{MVS}!$F:$F,\"{dim}\",{MVS}!$G:$G,{member_ref})"


wb = Workbook()

# ---------------------------------------------------------------- Read me
ws = wb.active
ws.title = "Read me"
ws["A1"], ws["A1"].font = "London short lets: one definition per metric", TITLE
rows = [
    ("Source", f"Inside Airbnb, London, scraped {S['snapshot']['scraped']}"),
    ("What this is", "The Excel consumer of the metric layer. 'Metric values' is the published table; every other sheet is formulas over it."),
    ("Ratios", "Ratios are published as numerator and denominator. Sum the parts, then divide. Never average ratios."),
    ("Certified", "Only certified metrics should be reported. The three uncertified occupancy definitions are kept to show why one was chosen."),
    ("Rebuild", "python src/pipeline.py, then python src/build_excel.py. Definitions live in metrics.yml."),
    ("Model assumptions", f"Review rate {S['parameters']['review_rate']:.0%}, average stay {S['parameters']['avg_stay_nights']} nights, "
                          f"cap {S['parameters']['occupancy_cap']:.0%} of the year (Inside Airbnb's model). See the 'Sensitivity' sheet."),
]
for i, (k, v) in enumerate(rows, 3):
    ws.cell(row=i, column=1, value=k).font = BB
    ws.cell(row=i, column=2, value=v).font = B
    ws.cell(row=i, column=2).alignment = Alignment(wrap_text=True, vertical="top")
ws.column_dimensions["A"].width, ws.column_dimensions["B"].width = 20, 110

# ---------------------------------------------------------------- Metric values (data)
wm = wb.create_sheet("Metric values")
cols = ["metric_id", "metric", "version", "certified", "definition_hash", "dimension", "member", "member_1", "member_2", "value", "unused", "numerator", "denominator"]
data = mv.assign(unused="")[cols]
header(wm, 1, cols, [26, 38, 9, 10, 14, 20, 40, 26, 18, 14, 2, 14, 14])
for r in data.itertuples(index=False):
    wm.append(list(r))
for row in wm.iter_rows(min_row=2):
    for c in row:
        c.font = B
tab = Table(displayName="MetricValues", ref=f"A1:M{len(data) + 1}")
tab.tableStyleInfo = TableStyleInfo(name="TableStyleLight9", showRowStripes=True)
wm.add_table(tab)
wm.freeze_panes = "A2"

# ---------------------------------------------------------------- Boroughs (formulas)
wsb = wb.create_sheet("Boroughs", 1)
wsb["A1"], wsb["A1"].font = "Boroughs, ranked by entire homes likely over 90 nights", TITLE
wsb["A2"], wsb["A2"].font = "Every number is a SUMIFS over 'Metric values'. Ratios are numerator / denominator, re-aggregated, not averaged.", NOTE
bcols = ["Borough", "Listings", "Active listings", "Occupancy rate", "Entire-home share", "Entire homes likely over 90 nights",
         "Share of short-stay entire homes over 90", "Share of London's over-90 homes"]
header(wsb, 4, bcols, [26, 12, 14, 14, 14, 18, 18, 18])
order = (mv[(mv.metric_id == "over_90_homes") & (mv.dimension == "borough")].sort_values("numerator", ascending=False).member.tolist())
first = 5
for i, bname in enumerate(order):
    r = first + i
    a = f"$A{r}"
    wsb.cell(row=r, column=1, value=bname)
    wsb.cell(row=r, column=2, value="=" + sumifs("numerator", "listings", "borough", a))
    wsb.cell(row=r, column=3, value="=" + sumifs("numerator", "active_listings", "borough", a))
    wsb.cell(row=r, column=4, value=f"=IFERROR({sumifs('numerator', 'occupancy_rate', 'borough', a)}/{sumifs('denominator', 'occupancy_rate', 'borough', a)},0)")
    wsb.cell(row=r, column=5, value=f"=IFERROR({sumifs('numerator', 'entire_home_share', 'borough', a)}/{sumifs('denominator', 'entire_home_share', 'borough', a)},0)")
    wsb.cell(row=r, column=6, value="=" + sumifs("numerator", "over_90_homes", "borough", a))
    wsb.cell(row=r, column=7, value=f"=IFERROR({sumifs('numerator', 'over_90_share', 'borough', a)}/{sumifs('denominator', 'over_90_share', 'borough', a)},0)")
    wsb.cell(row=r, column=8, value=f"=IFERROR(F{r}/$F${first + len(order)},0)")
last = first + len(order) - 1
t = last + 1
wsb.cell(row=t, column=1, value="London")
wsb.cell(row=t, column=2, value=f"=SUM(B{first}:B{last})")
wsb.cell(row=t, column=3, value=f"=SUM(C{first}:C{last})")
ref = f'"London"'
wsb.cell(row=t, column=4, value=f"=IFERROR({sumifs('numerator', 'occupancy_rate', 'total', ref)}/{sumifs('denominator', 'occupancy_rate', 'total', ref)},0)")
wsb.cell(row=t, column=5, value=f"=IFERROR({sumifs('numerator', 'entire_home_share', 'total', ref)}/{sumifs('denominator', 'entire_home_share', 'total', ref)},0)")
wsb.cell(row=t, column=6, value=f"=SUM(F{first}:F{last})")
wsb.cell(row=t, column=7, value=f"=IFERROR({sumifs('numerator', 'over_90_share', 'total', ref)}/{sumifs('denominator', 'over_90_share', 'total', ref)},0)")
wsb.cell(row=t, column=8, value=f"=SUM(H{first}:H{last})")
chk = t + 2
wsb.cell(row=chk, column=1, value="Check: boroughs add up to the published London total").font = NOTE
wsb.cell(row=chk, column=6, value=f"=IF(F{t}={sumifs('numerator', 'over_90_homes', 'total', ref)},\"OK\",\"MISMATCH\")")
for r in range(first, t + 1):
    for c in range(1, 9):
        cell = wsb.cell(row=r, column=c)
        cell.font = BB if r == t else (GREEN if c > 1 else B)
        cell.number_format = PCT if c in (4, 5, 7, 8) else INT
        cell.border = Border(bottom=thin)
wsb.freeze_panes = "B5"

# ---------------------------------------------------------------- Occupancy definitions
wo = wb.create_sheet("Occupancy definitions", 2)
wo["A1"], wo["A1"].font = "Four ways to measure occupancy, one certified", TITLE
header(wo, 3, ["Definition", "Certified", "London value", "Why it is or isn't the answer"], [42, 11, 14, 110])
occ = [d for d in defs["metrics"] if d["id"].startswith("occupancy")]
occ.sort(key=lambda d: S["occupancy"][d["id"]])
for i, d in enumerate(occ, 4):
    wo.cell(row=i, column=1, value=d["name"]).font = BB if d["certified"] else B
    wo.cell(row=i, column=2, value="Yes" if d["certified"] else "No").font = B
    c = wo.cell(row=i, column=3, value=f"=IFERROR({sumifs('numerator', d['id'], 'total', ref)}/{sumifs('denominator', d['id'], 'total', ref)},0)")
    c.font, c.number_format = GREEN, PCT
    why = d["description"] if d["certified"] else d["why_not"]
    wo.cell(row=i, column=4, value=why).font = B
    wo.cell(row=i, column=4).alignment = Alignment(wrap_text=True, vertical="top")

# ---------------------------------------------------------------- Sensitivity
sens = pd.read_csv(PUB / "sensitivity.csv").sort_values("review_rate", ascending=False)
wsn = wb.create_sheet("Sensitivity", 3)
wsn["A1"], wsn["A1"].font = "How many entire homes look over 90 nights, by review-rate assumption", TITLE
wsn["A2"], wsn["A2"].font = ("Fewer stays reviewed means more stays per review, so more nights. Review rates as published by Inside Airbnb "
                             "(insideairbnb.com/data-assumptions)."), NOTE
header(wsn, 4, ["Share of stays that leave a review", "Assumption", "Entire homes likely over 90 nights", "Short-stay entire homes", "Share"],
       [16, 62, 18, 18, 12])
for i, r in enumerate(sens.itertuples(), 5):
    vals = [r.review_rate, r.label, r.over_90_homes, r.short_let_entire_homes, f"=C{i}/D{i}"]
    for j, v in enumerate(vals, 1):
        c = wsn.cell(row=i, column=j, value=v)
        c.font = Font(name=F, color="0000FF") if j in (1, 3, 4) else B
        c.number_format = {1: "0.0%", 3: INT, 4: INT, 5: PCT}.get(j, "General")

# ---------------------------------------------------------------- Definitions and checks
wd = wb.create_sheet("Definitions")
dc = ["id", "name", "certified", "version", "type", "numerator", "denominator", "expression", "filter", "description", "why_not", "definition_hash"]
header(wd, 1, dc, [24, 36, 10, 9, 9, 34, 26, 18, 44, 70, 70, 14])
for d in defs["metrics"]:
    wd.append([d.get(k) if not isinstance(d.get(k), bool) else ("Yes" if d.get(k) else "No") for k in dc])
for row in wd.iter_rows(min_row=2):
    for c in row:
        c.font, c.alignment = B, Alignment(wrap_text=True, vertical="top")
wq = wb.create_sheet("Quality checks")
header(wq, 1, list(qr.columns), [22, 70, 10, 10, 10, 10, 50])
for r in qr.fillna("").itertuples(index=False):
    wq.append(list(r))
for row in wq.iter_rows(min_row=2):
    for c in row:
        c.font = B

OUT.parent.mkdir(parents=True, exist_ok=True)
wb.save(OUT)
print("wrote", OUT.relative_to(ROOT))
