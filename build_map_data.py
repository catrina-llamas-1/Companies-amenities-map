# BUILD MAP DATA
# Reads the two input spreadsheets (industrial companies, area amenities) and
# writes site/data/map_data.json, which the web map loads.
#
# Usage:  pip install pandas openpyxl
#         python build_map_data.py
#
# Each spreadsheet needs Name, Type, Lat and Lng columns (Address, Rating,
# Reviews and URL are used when present). Every sheet in a workbook is read and
# duplicate rows (same name and coordinates) are merged. Rows without
# coordinates, or farther than max_distance_km from the base point, are skipped.

import json
import math
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
OUTPUT_PATH = ROOT / "site" / "data" / "map_data.json"
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

def find_input(stem):
    """Return the single spreadsheet at <stem>.xlsx/.xls/.csv."""
    matches = [ROOT / f"{stem}{ext}" for ext in SPREADSHEET_EXTENSIONS
               if (ROOT / f"{stem}{ext}").exists()]
    if not matches:
        sys.exit(f"ERROR: no spreadsheet found for {stem} "
                 f"(expected one of {', '.join(SPREADSHEET_EXTENSIONS)})")
    if len(matches) > 1:
        sys.exit(f"ERROR: several spreadsheets for {stem}: "
                 f"{', '.join(m.name for m in matches)} — keep only one")
    return matches[0]


def read_sheets(path):
    """Return {sheet name: DataFrame} for every sheet in the file."""
    if path.suffix == ".csv":
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

def build_view(view_cfg, base, max_km):
    path = find_input(view_cfg["input"])
    points, seen = [], set()
    no_coords, too_far, dupes = [], [], 0

    for sheet, df in read_sheets(path).items():
        cols = map_columns(df, f"{path.name} / sheet '{sheet}'")
        get = lambda row, field: str(row[cols[field]]).strip() if field in cols else ""
        for i, row in df.iterrows():
            name = get(row, "name")
            if not name:
                continue
            lat, lon = to_float(get(row, "lat")), to_float(get(row, "lon"))
            if lat is None or lon is None:
                # Name left out of the log: stray rows here can hold personal data
                no_coords.append(f"'{sheet}' row {i + 2}")
                continue
            where = f"'{sheet}' row {i + 2}: {name}"
            key = (name.lower(), round(lat, 5), round(lon, 5))
            if key in seen:
                dupes += 1
                continue
            seen.add(key)
            km = distance_km(base["lat"], base["lon"], lat, lon)
            if km > max_km:
                too_far.append(f"{where} ({km:,.0f} km away)")
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
    print(f"{view_cfg['label']}: {path.name} -> {len(points)} pins "
          f"({dupes} duplicates merged)")
    for label, rows in (("no coordinates", no_coords),
                        (f"more than {max_km:g} km from base", too_far)):
        if rows:
            print(f"  skipped {len(rows)} row(s) with {label}:")
            for r in rows:
                print(f"    - {r}")
    return {"label": view_cfg["label"], "points": points}


def main():
    config = json.loads(CONFIG_PATH.read_text())
    base = config["base"]
    views = {key: build_view(cfg, base, config["max_distance_km"])
             for key, cfg in config["views"].items()}

    data = {"title": config["title"], "base": base,
            "radius_options_km": config["radius_options_km"],
            "default_radius_km": config["default_radius_km"], "views": views}
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"Wrote {OUTPUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
