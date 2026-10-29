"""Power BI version of the London short-lets metric layer. Run from powerbi/:

    python tools/spec.py        # writes London_Short_Lets.pbip and its folders
    python tools/validate.py    # schema and reference checks
    python tools/expected.py    # what the visuals should show, checked against data/published/

The point of the metric layer is that Power BI does not redefine anything. It reads the published metric table
(numerator and denominator for every metric x dimension member) and has one generic measure,
Metric Value: counts and sums add up (they have no denominator); ratios sum numerators and denominators, then divide.
The named measures only pick a metric and a dimension.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pbikit import C, M, build, card, check_sorts, color, lit, slicer, text_box, visual  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = "London_Short_Lets"
NAVY, RED, GREY = "#1F4E79", "#D9483B", "#B9BDC3"

TABLES = {
    "Metric Values": dict(
        file="metric_values.csv",
        description="The published metric table: one row per metric, dimension and member, with numerator and denominator. "
                    "Every consumer (web page, Power BI, Excel) reads this same table.",
        columns=[("metric_id", "string", {"isHidden": True}), ("metric", "string", {"isHidden": True}), ("version", "int64", {"isHidden": True}),
                 ("certified", "boolean", {"isHidden": True}), ("definition_hash", "string", {"isHidden": True}),
                 ("dimension", "string", {}), ("member", "string", {"sortByColumn": "member_order"}), ("member_1", "string", {"isHidden": True}),
                 ("member_2", "string", {"isHidden": True}), ("numerator", "double", {"isHidden": True}),
                 ("denominator", "double", {"isHidden": True}), ("value", "double", {"isHidden": True}),
                 ("member_order", "int64", {"isHidden": True})]),
    "Definitions": dict(
        file="definitions.csv",
        description="The metric registry (metrics.yml): name, description, whether it is certified, version and definition hash.",
        columns=[("id", "string", {"isKey": True, "isHidden": True}), ("name", "string", {}), ("description", "string", {}),
                 ("certified", "boolean", {}), ("version", "int64", {"summarizeBy": "none"}), ("type", "string", {"isHidden": True}),
                 ("format", "string", {"isHidden": True}), ("filter", "string", {}), ("why_not", "string", {}),
                 ("definition_hash", "string", {})]),
    "Quality Report": dict(
        file="quality_report.csv",
        description="Quality checks run before publishing. An error-level failure stops the build, so this table never contains one.",
        columns=[("id", "string", {"isHidden": True}), ("description", "string", {}), ("severity", "string", {}), ("expect", "int64", {"isHidden": True}),
                 ("result", "int64", {"summarizeBy": "none"}), ("status", "string", {}), ("note", "string", {"isHidden": True})]),
    "Sensitivity": dict(
        file="sensitivity.csv",
        description="Entire homes modelled above 90 nights under three published review-rate assumptions.",
        columns=[("review_rate", "double", {"formatString": "0.0%", "summarizeBy": "none"}), ("label", "string", {}),
                 ("over_90_homes", "int64", {"summarizeBy": "none"}), ("short_let_entire_homes", "int64", {"isHidden": True}),
                 ("share", "double", {"formatString": "0%", "summarizeBy": "none"})]),
}

RELATIONSHIPS = [(("Metric Values", "metric_id"), ("Definitions", "id"), {})]

MVT = "Metric Values"


def pick(metric, dim="total"):
    return f'CALCULATE ( [Metric Value], \'Metric Values\'[metric_id] = "{metric}", \'Metric Values\'[dimension] = "{dim}" )'


MEASURES = [
    ("Metric Value", MVT, "Generic", "#,0.###",
     """VAR num = SUM ( 'Metric Values'[numerator] )
VAR den = SUM ( 'Metric Values'[denominator] )
RETURN IF ( ISBLANK ( den ), num, DIVIDE ( num, den ) )""",
     "The one generic measure: counts and sums (no denominator) add up; ratios sum their numerators and denominators, then divide."),
    ("Metric Value (Percent)", MVT, "Generic", "0.0%", "[Metric Value]", "The same value shown as a percentage, for ratio metrics."),
    ("Listings", MVT, "Headline", "#,0", pick("listings"), "Every listing in the snapshot."),
    ("Active Listings", MVT, "Headline", "#,0", pick("active_listings"), "Listings with a review in the last 12 months."),
    ("Occupancy Rate", MVT, "Headline", "0.0%", pick("occupancy_rate"), "Certified occupancy: modelled booked nights / 365, active listings."),
    ("Entire Homes Over 90 Nights", MVT, "Headline", "#,0", pick("over_90_homes"), "Active short-stay entire homes modelled above 90 nights."),
    ("Share Over 90 Nights", MVT, "Headline", "0.0%", pick("over_90_share"), "Over-90 entire homes as a share of active short-stay entire homes."),
    ("Over 90 Nights by Borough", MVT, "Breakdowns", "#,0", pick("over_90_homes", "borough"), "Over-90 entire homes, borough rows only."),
    ("Share Over 90 by Borough", MVT, "Breakdowns", "0.0%", pick("over_90_share", "borough"), "Over-90 share, borough rows only."),
    ("Active Listings by Borough", MVT, "Breakdowns", "#,0", pick("active_listings", "borough"), "Active listings, borough rows only."),
    ("Occupancy by Borough", MVT, "Breakdowns", "0.0%", pick("occupancy_rate", "borough"), "Certified occupancy, borough rows only."),
    ("Over 90 Nights by Host Size", MVT, "Breakdowns", "#,0", pick("over_90_homes", "host_size"), "Over-90 entire homes by how many listings the host has."),
    ("Occupancy (Any Definition)", MVT, "Definitions", "0.0%",
     "CALCULATE ( [Metric Value], 'Metric Values'[dimension] = \"total\", KEEPFILTERS ( CONTAINSSTRING ( 'Metric Values'[metric_id], \"occupancy\" ) ) )",
     "London's value for each occupancy definition, certified or not: put Definitions[name] on the axis."),
    ("Top 5 Borough Share", MVT, "Headline", "0.0%",
     '''VAR boroughs = FILTER ( ALL ( 'Metric Values'[member], 'Metric Values'[dimension], 'Metric Values'[metric_id] ),
    'Metric Values'[metric_id] = "over_90_homes" && 'Metric Values'[dimension] = "borough" )
VAR top5 = TOPN ( 5, boroughs, CALCULATE ( SUM ( 'Metric Values'[numerator] ) ), DESC )
RETURN DIVIDE ( SUMX ( top5, CALCULATE ( SUM ( 'Metric Values'[numerator] ) ) ), [Entire Homes Over 90 Nights] )''',
     "Share of London's over-90 entire homes in the five boroughs with the most."),
    ("Checks Passed", "Quality Report", "Quality", "0", 'CALCULATE ( COUNTROWS ( \'Quality Report\' ), \'Quality Report\'[status] = "pass" ) + 0',
     "Quality checks that passed."),
    ("Checks Warned", "Quality Report", "Quality", "0", 'CALCULATE ( COUNTROWS ( \'Quality Report\' ), \'Quality Report\'[status] = "warn" ) + 0',
     "Quality checks that published with a warning."),
]

p1, p2, p3, p4 = "one", "where", "explore", "trust"
cw = (1232 - 4 * 12) // 5
cx = [24 + i * (cw + 12) for i in range(5)]
PAGES = [
    (p1, "One number", [
        text_box(p1, "title", 24, 12, 1232, 52, "London short lets: four ways to measure occupancy, one certified", 18),
        card(p1, "lst", cx[0], 76, cw, 96, M(MVT, "Listings", "Listings")),
        card(p1, "act", cx[1], 76, cw, 96, M(MVT, "Active Listings", "Active listings")),
        card(p1, "occ", cx[2], 76, cw, 96, M(MVT, "Occupancy Rate", "Occupancy (certified)")),
        card(p1, "o90", cx[3], 76, cw, 96, M(MVT, "Entire Homes Over 90 Nights", "Entire homes likely over 90 nights")),
        card(p1, "top5", cx[4], 76, cw, 96, M(MVT, "Top 5 Borough Share", "Held by the top 5 boroughs")),
        visual(p1, "defs", "clusteredBarChart", 24, 184, 600, 524,
               {"Category": [C("Definitions", "name", "Definition")], "Y": [M(MVT, "Occupancy (Any Definition)", "London occupancy")]},
               "Same question, four answers (only 'Occupancy rate' is certified)",
               objects={"dataPoint": [{"properties": {"fill": color(NAVY)}}], "labels": [{"properties": {"show": lit(True)}}]},
               sort=(M(MVT, "Occupancy (Any Definition)"), "Ascending"), z=10),
        visual(p1, "reg", "tableEx", 640, 184, 616, 524,
               {"Values": [C("Definitions", "name", "Metric"), C("Definitions", "certified", "Certified"), C("Definitions", "version", "Version"),
                           C("Definitions", "definition_hash", "Hash"), C("Definitions", "why_not", "Why not certified")]},
               "The metric registry (metrics.yml)", objects={"total": [{"properties": {"totals": lit(False)}}]}, z=11),
    ]),
    (p2, "Where", [
        text_box(p2, "title", 24, 12, 1232, 52, "Entire homes likely let for more than 90 nights a year, by borough", 18),
        visual(p2, "bars", "clusteredBarChart", 24, 76, 600, 632,
               {"Category": [C(MVT, "member", "Borough")], "Y": [M(MVT, "Over 90 Nights by Borough", "Entire homes over 90 nights")]},
               "Entire homes likely over 90 nights", objects={"dataPoint": [{"properties": {"fill": color(RED)}}],
                                                              "labels": [{"properties": {"show": lit(True)}}]},
               sort=(M(MVT, "Over 90 Nights by Borough"), "Descending"), z=10),
        visual(p2, "table", "tableEx", 640, 76, 616, 632,
               {"Values": [C(MVT, "member", "Borough"), M(MVT, "Active Listings by Borough", "Active listings"),
                           M(MVT, "Occupancy by Borough", "Occupancy"), M(MVT, "Over 90 Nights by Borough", "Over 90 nights"),
                           M(MVT, "Share Over 90 by Borough", "Share over 90")]},
               "Every borough", sort=(M(MVT, "Over 90 Nights by Borough"), "Descending"),
               objects={"total": [{"properties": {"totals": lit(False)}}]}, z=11),
    ]),
    (p3, "Metric explorer", [
        text_box(p3, "title", 24, 12, 600, 52, "Metric explorer: pick a metric and a dimension", 18),
        slicer(p3, "metric", 640, 8, 300, 64, C("Definitions", "name", "Metric"), "Metric", single=True),
        slicer(p3, "dim", 956, 8, 300, 64, C(MVT, "dimension", "Dimension"), "Dimension", single=True),
        visual(p3, "bars", "clusteredBarChart", 24, 84, 820, 624,
               {"Category": [C(MVT, "member", "Member")], "Y": [M(MVT, "Metric Value", "Value")]},
               "One generic measure: counts add up, ratios re-aggregate from their parts",
               objects={"dataPoint": [{"properties": {"fill": color(NAVY)}}], "labels": [{"properties": {"show": lit(True)}}]},
               sort=(M(MVT, "Metric Value"), "Descending"), z=10),
        visual(p3, "def", "tableEx", 860, 84, 396, 624,
               {"Values": [C("Definitions", "name", "Metric"), C("Definitions", "description", "Definition"), C("Definitions", "filter", "Filter"),
                           C("Definitions", "definition_hash", "Hash")]},
               "The definition behind the chart", objects={"total": [{"properties": {"totals": lit(False)}}]}, z=11),
    ]),
    (p4, "Who and how sure", [
        text_box(p4, "title", 24, 12, 1232, 52, "Who runs the over-90 homes, how sure we are, and the checks behind every number", 18),
        card(p4, "pass", 24, 76, 300, 96, M("Quality Report", "Checks Passed", "Quality checks passed")),
        card(p4, "warn", 336, 76, 300, 96, M("Quality Report", "Checks Warned", "Published with a warning")),
        visual(p4, "hosts", "clusteredColumnChart", 648, 76, 608, 300,
               {"Category": [C(MVT, "member", "Host size")], "Y": [M(MVT, "Over 90 Nights by Host Size", "Entire homes over 90 nights")]},
               "Over-90 entire homes by host size", objects={"dataPoint": [{"properties": {"fill": color(RED)}}],
                                                             "labels": [{"properties": {"show": lit(True)}}]},
               sort=(C(MVT, "member"), "Ascending"), z=10),
        visual(p4, "sens", "tableEx", 24, 184, 612, 192,
               {"Values": [C("Sensitivity", "label", "Assumption"), C("Sensitivity", "over_90_homes", "Over 90 nights"), C("Sensitivity", "share", "Share")]},
               "How the count moves with the review-rate assumption", objects={"total": [{"properties": {"totals": lit(False)}}]}, z=11),
        visual(p4, "checks", "tableEx", 24, 388, 1232, 320,
               {"Values": [C("Quality Report", "description", "Check"), C("Quality Report", "severity", "Level"),
                           C("Quality Report", "result", "Found"), C("Quality Report", "status", "Result")]},
               "Quality checks run before publishing", objects={"total": [{"properties": {"totals": lit(False)}}]}, z=12),
    ]),
]

SPEC = dict(name=NAME, root=ROOT, tables=TABLES, measures=MEASURES, relationships=RELATIONSHIPS, pages=PAGES,
            base_url="https://raw.githubusercontent.com/QaisBello/london-short-lets/main/data/published/",
            base_desc="Folder of published metric files from this repo (data/published). Point it at a local folder or another branch to test.")

if __name__ == "__main__":
    build(SPEC)
    print("sort checks:", check_sorts(SPEC, os.path.join(os.path.dirname(ROOT), "data", "published")) or "ok")
