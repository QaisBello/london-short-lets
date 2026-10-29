"""One pipeline, one set of definitions: stage -> check -> compute metrics -> publish.

    python src/pipeline.py

Reads data/raw/ when it is there (the full Inside Airbnb files) and otherwise the committed data/staged/ copies, so
the metrics can always be rebuilt. Writes data/published/, which every consumer reads (web dashboard, Power BI, Excel).
If an error-level quality check fails, nothing is published.
"""
import hashlib
import json
import sys
from pathlib import Path

import duckdb
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
RAW, STAGED, PUB, MODELS = (ROOT / "data" / "raw", ROOT / "data" / "staged", ROOT / "data" / "published", ROOT / "models")
REG = yaml.safe_load(open(ROOT / "metrics.yml", encoding="utf-8"))
P = REG["parameters"]
INSIDE_AIRBNB_DEFAULTS = {"review_rate": 0.5, "avg_stay_nights": 4.6, "occupancy_cap": 0.70}


def sql_file(name, **kw):
    return (MODELS / f"{name}.sql").read_text(encoding="utf-8").format(**kw)


def stage(con):
    """Raw files -> staged tables. Saves the staged tables so the repo can rebuild without the 130 MB raw files."""
    STAGED.mkdir(parents=True, exist_ok=True)
    if (RAW / "listings.csv.gz").exists():
        for t in ["stg_listings", "stg_calendar_365", "stg_reviews_ltm"]:
            con.execute(f"create or replace table {t} as " + sql_file(t, raw=RAW.as_posix()))
            con.execute(f"copy (select * from {t} order by 1) to '{(STAGED / (t + '.csv')).as_posix()}' (header, delimiter ',')")
        print("staged from data/raw")
    else:
        for t in ["stg_listings", "stg_calendar_365", "stg_reviews_ltm"]:
            con.execute(f"create or replace table {t} as select * from read_csv_auto('{(STAGED / (t + '.csv')).as_posix()}')")
        print("loaded data/staged (no raw files)")
    con.execute("create or replace table fct_listing as " + sql_file("fct_listing", **P))


def run_checks(con):
    default_params = all(abs(P[k] - v) < 1e-12 for k, v in INSIDE_AIRBNB_DEFAULTS.items())
    rows = []
    for c in REG["checks"]:
        if c["id"] == "model_reproduced" and not default_params:
            rows.append({**c, "result": None, "status": "skipped", "note": "parameters differ from Inside Airbnb's, so the estimates should differ"})
            continue
        got = con.execute(c["sql"]).fetchone()[0]
        ok = got == c["expect"]
        rows.append({**c, "result": got, "status": "pass" if ok else ("fail" if c["severity"] == "error" else "warn"), "note": ""})
    rep = pd.DataFrame(rows)[["id", "description", "severity", "expect", "result", "status", "note"]]
    return rep


def metric_sql(m, dims):
    cols = [REG["dimensions"][d]["column"] for d in dims]
    sel = ", ".join(f"{c} as d{i}" for i, c in enumerate(cols))
    where = f"where {m['filter']}" if m.get("filter") else ""
    if m["type"] == "count":
        num, den = "count(*)", "null"
    elif m["type"] == "sum":
        num, den = f"sum({m['expression']})", "null"
    else:
        num, den = m["numerator"], m["denominator"]
    group = "group by all" if dims else ""
    return f"select {sel}{',' if sel else ''} {num} as numerator, {den} as denominator from fct_listing {where} {group}"


def definition_hash(m):
    keys = ["type", "numerator", "denominator", "expression", "filter"]
    blob = json.dumps({k: m.get(k) for k in keys}, sort_keys=True) + json.dumps(P, sort_keys=True)
    return hashlib.sha1(blob.encode()).hexdigest()[:10]


def compute(con):
    combos = [[d] for d in REG["publish"]["dimensions"]] + REG["publish"]["crosses"]
    out = []
    for m in REG["metrics"]:
        h = definition_hash(m)
        for dims in combos:
            df = con.execute(metric_sql(m, dims)).df()
            for _, r in df.iterrows():
                members = [str(r[f"d{i}"]) for i in range(len(dims))]
                den = None if pd.isna(r.denominator) else float(r.denominator)  # counts and sums have no denominator
                out.append(dict(metric_id=m["id"], metric=m["name"], version=m.get("version", 0), certified=bool(m.get("certified")),
                                definition_hash=h, dimension=" x ".join(dims), member=" | ".join(members),
                                member_1=members[0], member_2=members[1] if len(members) > 1 else "",
                                numerator=float(r.numerator), denominator=den, value=float(r.numerator) if den is None else (float(r.numerator) / den if den else None)))
    return pd.DataFrame(out)


def extras(con):
    """Inputs for the memo and the map that are not single metrics."""
    # grid of ~500 m cells for the map: active entire homes and the over-90 ones
    grid = con.execute(f"""
        select round(latitude / 0.0045) * 0.0045 as lat, round(longitude / 0.0072) * 0.0072 as lon,
               count(*) as active_entire_homes,
               count(*) filter (where is_short_let and modelled_nights > {P['short_let_limit_nights']}) as over_90_homes
        from fct_listing where is_active and is_entire_home group by all order by 1, 2""").df()
    # how sensitive is the over-90 count to the review-rate assumption?
    sens = []
    for rate, label in [(0.72, "72% of stays are reviewed (a figure attributed to Airbnb, unverified)"),
                        (0.5, "50% of stays are reviewed (Inside Airbnb's default)"),
                        (0.305, "30.5% of stays are reviewed (from a New York comparison)")]:
        n = con.execute(f"""select count(*) filter (where least(round(reviews_ltm / {rate} * greatest({P['avg_stay_nights']}, minimum_nights)), floor(365 * {P['occupancy_cap']})) > {P['short_let_limit_nights']}),
                                   count(*)
                            from fct_listing where is_active and is_entire_home and is_short_let""").fetchone()
        sens.append(dict(review_rate=rate, label=label, over_90_homes=n[0], short_let_entire_homes=n[1], share=n[0] / n[1]))
    # host concentration of the over-90 homes
    hosts = con.execute(f"""
        select host_id, count(*) as over_90_homes, any_value(host_listings) as host_listings
        from fct_listing where is_active and is_entire_home and is_short_let and modelled_nights > {P['short_let_limit_nights']}
        group by 1 order by 2 desc""").df()
    return grid, pd.DataFrame(sens), hosts


def main():
    PUB.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    stage(con)
    rep = run_checks(con)
    rep.to_csv(PUB / "quality_report.csv", index=False)
    print(rep[["id", "status", "result"]].to_string(index=False))
    if (rep.status == "fail").any():
        print("ERROR-level check failed: nothing published")
        sys.exit(1)

    mv = compute(con).sort_values(["metric_id", "dimension", "member"]).reset_index(drop=True)
    # a sort key for members that have a natural order (host size); 0 elsewhere. One value per member, for Power BI sort-by.
    orders = {m: i + 1 for d in REG["dimensions"].values() for i, m in enumerate(d.get("order", []))}
    mv["member_order"] = mv.member.map(orders).fillna(0).astype(int)
    mv.to_csv(PUB / "metric_values.csv", index=False)
    grid, sens, hosts = extras(con)
    grid.to_csv(PUB / "map_grid.csv", index=False)
    sens.to_csv(PUB / "sensitivity.csv", index=False)

    defs = [{k: m.get(k) for k in ["id", "name", "description", "type", "numerator", "denominator", "expression", "filter", "format",
                                   "certified", "version", "changelog", "why_not"]} | {"definition_hash": definition_hash(m)} for m in REG["metrics"]]
    json.dump({"snapshot": REG["snapshot"], "parameters": P, "dimensions": REG["dimensions"], "metrics": defs},
              open(PUB / "definitions.json", "w"), indent=2)
    pd.DataFrame([{"id": d["id"], "name": d["name"], "description": d["description"], "certified": bool(d["certified"]),
                   "version": d.get("version") or 0, "type": d["type"], "format": d.get("format") or "number",
                   "filter": d.get("filter") or "", "why_not": d.get("why_not") or "", "definition_hash": d["definition_hash"]}
                  for d in defs]).to_csv(PUB / "definitions.csv", index=False)

    def v(mid, dim="total", member="London"):
        r = mv[(mv.metric_id == mid) & (mv.dimension == dim) & (mv.member == member)]
        return float(r.value.iloc[0]) if len(r) else None

    over = mv[(mv.metric_id == "over_90_homes") & (mv.dimension == "borough")].sort_values("numerator", ascending=False)
    top5 = over.head(5)
    total_over = v("over_90_homes")
    big = hosts[hosts.host_listings >= 20].over_90_homes.sum()
    summary = dict(
        snapshot=REG["snapshot"], parameters=P,
        listings=v("listings"), active_listings=v("active_listings"),
        occupancy={m: v(m) for m in ["occupancy_rate", "occupancy_all_listings", "occupancy_of_bookable", "occupancy_calendar_unavailable"]},
        entire_home_share=v("entire_home_share"), multi_listing_share=v("multi_listing_share"),
        over_90_homes=total_over, over_90_share=v("over_90_share"),
        short_let_entire_homes=float(mv[(mv.metric_id == "over_90_share") & (mv.dimension == "total")].denominator.iloc[0]),
        top5_boroughs=[dict(borough=r.member, over_90_homes=r.numerator) for r in top5.itertuples()],
        top5_share=float(top5.numerator.sum() / total_over),
        over_90_hosts=int(len(hosts)), over_90_from_20plus_hosts=float(big), over_90_from_20plus_share=float(big / total_over),
        sensitivity=sens.to_dict("records"),
        checks={"pass": int((rep.status == "pass").sum()), "warn": int((rep.status == "warn").sum()), "skipped": int((rep.status == "skipped").sum())},
    )
    json.dump(summary, open(PUB / "summary.json", "w"), indent=2, default=float)
    print(json.dumps({k: summary[k] for k in ["listings", "active_listings", "occupancy", "over_90_homes", "over_90_share", "top5_boroughs",
                                             "top5_share", "over_90_hosts", "over_90_from_20plus_share"]}, indent=1, default=float))
    print(sens.to_string(index=False))


if __name__ == "__main__":
    main()
