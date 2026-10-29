"""Build dashboard/index.html from src/dashboard_template.html. The page reads data/published/ live from GitHub and
falls back to the local copy (or the bundled snapshot when opened from disk)."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tpl = open(os.path.join(ROOT, "src", "dashboard_template.html"), encoding="utf-8").read()
page = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
        '<style>body{margin:0}</style>\n</head>\n<body>\n'
        + tpl.replace("<!--SITEBAR-->", "").replace('/*FALLBACKS*/["../data/published/"]', '["../data/published/"]')
        + "\n</body>\n</html>\n")
out = os.path.join(ROOT, "dashboard", "index.html")
os.makedirs(os.path.dirname(out), exist_ok=True)
open(out, "w", encoding="utf-8").write(page)
print("built dashboard/index.html")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from offline_snapshot import inline  # noqa: E402
FILES = ["summary.json", "metric_values.csv", "map_grid.csv", "definitions.json", "quality_report.csv", "sensitivity.csv"]
inline(out, FILES, "../data/published/", os.path.join(ROOT, "data", "published"))
