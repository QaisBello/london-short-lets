"""Checks on the published metrics. Run: pytest -q"""
import json
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
PUB = ROOT / "data" / "published"
REG = yaml.safe_load(open(ROOT / "metrics.yml", encoding="utf-8"))
MV = pd.read_csv(PUB / "metric_values.csv")
S = json.load(open(PUB / "summary.json"))
Q = pd.read_csv(PUB / "quality_report.csv")


def test_no_error_check_failed():
    assert not (Q.status == "fail").any()


def test_every_registered_metric_is_published_for_every_dimension():
    for m in REG["metrics"]:
        dims = set(MV[MV.metric_id == m["id"]].dimension)
        for d in REG["publish"]["dimensions"]:
            assert d in dims, (m["id"], d)


def test_ratios_reaggregate_from_parts():
    """Borough numerators and denominators add up to London's: the reason ratios are published as parts."""
    for mid in ["occupancy_rate", "entire_home_share", "over_90_share", "listings", "over_90_homes"]:
        tot = MV[(MV.metric_id == mid) & (MV.dimension == "total")].iloc[0]
        b = MV[(MV.metric_id == mid) & (MV.dimension == "borough")]
        assert abs(b.numerator.sum() - tot.numerator) < 1e-6
        if mid in {"occupancy_rate", "entire_home_share", "over_90_share"}:
            assert abs(b.denominator.sum() - tot.denominator) < 1e-6


def test_crosses_add_up_to_their_rows():
    x = MV[(MV.metric_id == "over_90_homes") & (MV.dimension == "borough x room_type")]
    b = MV[(MV.metric_id == "over_90_homes") & (MV.dimension == "borough")].set_index("member")
    for borough, g in x.groupby("member_1"):
        assert g.numerator.sum() == b.loc[borough, "numerator"]


def test_only_one_certified_occupancy():
    occ = [m for m in REG["metrics"] if m["id"].startswith("occupancy")]
    assert sum(bool(m.get("certified")) for m in occ) == 1
    assert all(m.get("why_not") for m in occ if not m.get("certified"))


def test_definitions_disagree_as_reported():
    o = S["occupancy"]
    assert o["occupancy_all_listings"] < o["occupancy_rate"] < o["occupancy_of_bookable"] < o["occupancy_calendar_unavailable"]


def test_occupancy_never_above_cap():
    cap = REG["parameters"]["occupancy_cap"]
    occ = MV[MV.metric_id == "occupancy_rate"]
    assert (occ.value <= cap + 1e-9).all()


def test_sensitivity_moves_the_right_way():
    s = pd.read_csv(PUB / "sensitivity.csv").sort_values("review_rate")
    assert s.over_90_homes.is_monotonic_decreasing


def test_headline_matches_metric_table():
    r = MV[(MV.metric_id == "over_90_homes") & (MV.dimension == "total")].iloc[0]
    assert r.numerator == S["over_90_homes"]
