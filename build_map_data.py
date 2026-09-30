# BUILD MAP DATA
# Reads the input spreadsheets for each map view (industrial companies, area
# amenities) and writes site/data/map_data.json, which the web map loads.
#
# Usage:  pip install pandas openpyxl
#         python build_map_data.py
#
# Each spreadsheet needs Name, Type, Lat and Lng columns (Address, Rating,
# Reviews and URL are used when present). Every sheet in a workbook is read and
# duplicate rows (same name and coordinates) are merged. Only places within
# max_distance_km (config.json) of the base point are kept.
# A view whose "input" ends in "*" (the amenities view) reads every spreadsheet
# in that folder not used by another view, one file per category. Each view's
# pins use that view's logo and colour. A view with "combine" (the "All" view)
# shows the points of the listed views together, each keeping its own logo.

import json
import math
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
OUTPUT_PATH = ROOT / "site" / "data" / "map_data.json"
LOGO_DIR = ROOT / "site" / "logos"
SPREADSHEET_EXTENSIONS = [".xlsx", ".xls", ".csv"]

# Accepted header spellings (compared lower-case, ignoring spaces/underscores)
COLUMN_ALIASES = {
    "name": ["name", "companyname", "company", "businessname", "amenityname", "placename"],
    "type": ["type", "category", "industry", "amenitytype", "companytype", "businesstype"],
    "lat": ["lat", "latitude"],
    "lon": ["lng", "lon", "long", "longitude"],
    "address": ["address", "streetaddress", "fulladdress"],
    "rating": ["rating"],
    "reviews": ["reviews", "reviewcount"],
    "url": ["url", "link", "mapsurl"],
}
REQUIRED = ["name", "type", "lat", "lon"]

# ── 1: READ SPREADSHEETS ─────────────────────────────────────────────────────

def spreadsheets(folder, pattern="*"):
    return sorted(p for p in folder.glob(pattern)
                  if p.suffix.lower() in SPREADSHEET_EXTENSIONS and not p.name.startswith("~$"))


def find_input(prefix):
    """Return the single spreadsheet whose name starts with <prefix>
    (so 'area_amenities.xlsx', 'area_amenities_.csv' etc. all match)."""
    matches = spreadsheets((ROOT / prefix).parent, f"{Path(prefix).name}*")
    if not matches:
        sys.exit(f"ERROR: no spreadsheet found for {prefix}* "
                 f"(expected one of {', '.join(SPREADSHEET_EXTENSIONS)})")
    if len(matches) > 1:
        sys.exit(f"ERROR: several spreadsheets for {prefix}*: "
                 f"{', '.join(m.name for m in matches)} — keep only one")
    return matches[0]


def find_inputs(views):
    """Return {view key: [spreadsheet paths]}. An input ending in '*' takes every
    spreadsheet in its folder that no other view uses."""
    views = {k: v for k, v in views.items() if "input" in v}
    inputs = {k: [find_input(v["input"])] for k, v in views.items()
              if not v["input"].endswith("*")}
    claimed = {p for paths in inputs.values() for p in paths}
    for key, v in views.items():
        if v["input"].endswith("*"):
            paths = [p for p in spreadsheets((ROOT / v["input"]).parent) if p not in claimed]
            if not paths:
                sys.exit(f"ERROR: no spreadsheets found for {v['label']} in {v['input']}")
            inputs[key] = paths
    return inputs


def read_sheets(path):
    """Return {sheet name: DataFrame} for every sheet in the file."""
    if path.suffix.lower() == ".csv":
        return {path.stem: pd.read_csv(path, dtype=str, keep_default_na=False)}
    return pd.read_excel(path, sheet_name=None, dtype=str, keep_default_na=False)


def normalize(header):
    return "".join(ch for ch in str(header).lower() if ch.isalnum())


def map_columns(df, where):
    """Map our field names (name, type, ...) to the sheet's actual headers."""
    by_norm = {normalize(c): c for c in df.columns}
    mapping = {}
    for field, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in by_norm:
                mapping[field] = by_norm[alias]
                break
    missing = [f for f in REQUIRED if f not in mapping]
    if missing:
        sys.exit(f"ERROR: {where} is missing column(s): {', '.join(missing)}. "
                 f"Headers found: {list(df.columns)}")
    return mapping

# ── 2: HELPERS ───────────────────────────────────────────────────────────────

def to_float(value):
    try:
        f = float(str(value).strip())
    except ValueError:
        return None
    return f if math.isfinite(f) else None


def distance_km(lat1, lon1, lat2, lon2):
    rad = math.pi / 180
    h = (math.sin((lat2 - lat1) * rad / 2) ** 2 + math.cos(lat1 * rad) * math.cos(lat2 * rad)
         * math.sin((lon2 - lon1) * rad / 2) ** 2)
    return 2 * 6371 * math.asin(math.sqrt(h))

# ── 3: BUILD ─────────────────────────────────────────────────────────────────

def build_view(view_cfg, paths, base, max_km):
    points, seen = [], set()
    no_coords, too_far, dupes = [], [], 0

    for path, sheet, df in ((p, s, df) for p in paths for s, df in read_sheets(p).items()):
        cols = map_columns(df, f"{path.name} / sheet '{sheet}'")
        get = lambda row, field: str(row[cols[field]]).strip() if field in cols else ""
        for i, row in df.iterrows():
            name = get(row, "name")
            if not name:
                continue
            lat, lon = to_float(get(row, "lat")), to_float(get(row, "lon"))
            if lat is None or lon is None:
                # Name left out of the log: stray rows here can hold personal data
                no_coords.append(f"{path.name} '{sheet}' row {i + 2}")
                continue
            key = (name.lower(), round(lat, 5), round(lon, 5))
            if key in seen:
                dupes += 1
                continue
            seen.add(key)
            km = distance_km(base["lat"], base["lon"], lat, lon)
            if km > max_km:
                too_far.append(f"{path.name} '{sheet}' row {i + 2}: {name} ({km:,.1f} km from base)")
                continue

            url = get(row, "url")
            point = {"name": name, "type": get(row, "type") or "Unspecified",
                     "address": get(row, "address"), "lat": round(lat, 6),
                     "lon": round(lon, 6), "km": round(km, 2)}
            rating, reviews = to_float(get(row, "rating")), to_float(get(row, "reviews"))
            if rating is not None:
                point["rating"] = rating
            if reviews is not None:
                point["reviews"] = int(reviews)
            place_id = re.search(r"!19s(ChIJ[\w-]+)", url)
            if place_id:
                point["place_id"] = place_id.group(1)
            points.append(point)

    points.sort(key=lambda p: p["km"])
    print(f"{view_cfg['label']}: {', '.join(p.name for p in paths)} -> {len(points)} pins "
          f"within {max_km:g} km ({dupes} duplicates merged)")
    if no_coords:
        print(f"  skipped {len(no_coords)} row(s) with no coordinates:")
        for r in no_coords:
            print(f"    - {r}")
    if too_far:
        # Summarised: far rows are expected, since the sheets cover a wide area
        print(f"  left out {len(too_far)} row(s) more than {max_km:g} km from the base")
    view = {"label": view_cfg["label"], "color": view_cfg.get("color", "#8c8c8c"),
            "points": points}
    logo = checked_logo(view_cfg.get("logo"), f"{view_cfg['label']} pins")
    if logo:
        view["logo"] = logo
    return view


def checked_logo(logo, what):
    """Return the logo file name if it exists in site/logos, else warn and return None."""
    if logo and (LOGO_DIR / logo).is_file():
        return logo
    if logo:
        print(f"  WARNING: logo site/logos/{logo} not found; {what} will use the default marker")
    return None


def combine_views(view_cfg, views):
    """Merge the points of other views; each point keeps its source's logo and colour."""
    points = [{**p, "logo": views[k].get("logo"), "color": views[k]["color"],
               "source": views[k]["label"]}
              for k in view_cfg["combine"] for p in views[k]["points"]]
    points.sort(key=lambda p: p["km"])
    print(f"{view_cfg['label']}: {len(points)} pins from "
          f"{', '.join(views[k]['label'] for k in view_cfg['combine'])}")
    return {"label": view_cfg["label"], "points": points}


def main():
    config = json.loads(CONFIG_PATH.read_text())
    base = config["base"]
    inputs = find_inputs(config["views"])
    views = {key: build_view(cfg, inputs[key], base, config["max_distance_km"])
             for key, cfg in config["views"].items() if "combine" not in cfg}
    # Keep the order views are listed in config.json (it sets the button order)
    views = {key: combine_views(cfg, views) if "combine" in cfg else views[key]
             for key, cfg in config["views"].items()}
    base = {**base, "logo": checked_logo(base.get("logo"), "the base point")}

    data = {"title": config["title"], "base": base,
            "radius_options_km": config["radius_options_km"],
            "default_radius_km": config["default_radius_km"], "views": views}
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"Wrote {OUTPUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
