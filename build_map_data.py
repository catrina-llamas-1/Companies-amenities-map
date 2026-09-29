# BUILD MAP DATA
# Reads the two input spreadsheets (industrial companies, area amenities) and
# writes site/data/map_data.json, which the web map loads.
#
# Usage:  pip install pandas openpyxl requests
#         python build_map_data.py
#
# Each spreadsheet needs a Name and a Type column, plus either Latitude/Longitude
# columns or an Address column. Rows with an address but no coordinates are
# geocoded with OpenStreetMap Nominatim; results are cached in
# data/geocode_cache.json so each address is only looked up once.

import json
import sys
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
CACHE_PATH = ROOT / "data" / "geocode_cache.json"
OUTPUT_PATH = ROOT / "site" / "data" / "map_data.json"

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "companies-amenities-map/1.0 (github.com/catrina-llamas-1/companies-amenities-map)"
SPREADSHEET_EXTENSIONS = [".xlsx", ".xls", ".csv"]

# Accepted header spellings (compared lower-case, ignoring spaces/underscores)
COLUMN_ALIASES = {
    "name": ["name", "companyname", "company", "businessname", "business",
             "amenityname", "amenity", "placename", "place"],
    "type": ["type", "category", "industry", "amenitytype", "companytype",
             "businesstype", "sector", "kind"],
    "address": ["address", "streetaddress", "fulladdress", "location"],
    "lat": ["lat", "latitude", "y"],
    "lon": ["lon", "lng", "long", "longitude", "x"],
}

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


def read_sheet(path):
    if path.suffix == ".csv":
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
    else:
        df = pd.read_excel(path, dtype=str, keep_default_na=False)
    return df


def normalize(header):
    return "".join(ch for ch in str(header).lower() if ch.isalnum())


def map_columns(df, path):
    """Map our field names (name, type, ...) to the sheet's actual headers."""
    by_norm = {normalize(c): c for c in df.columns}
    mapping = {}
    for field, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in by_norm:
                mapping[field] = by_norm[alias]
                break
    missing = [f for f in ("name", "type") if f not in mapping]
    if missing:
        sys.exit(f"ERROR: {path.name} has no {' / '.join(missing)} column. "
                 f"Headers found: {list(df.columns)}")
    has_coords = "lat" in mapping and "lon" in mapping
    if not has_coords and "address" not in mapping:
        sys.exit(f"ERROR: {path.name} needs Latitude/Longitude columns "
                 f"or an Address column. Headers found: {list(df.columns)}")
    return mapping

# ── 2: GEOCODING ─────────────────────────────────────────────────────────────

def load_cache():
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text())
    return {}


def save_cache(cache):
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, indent=2, sort_keys=True) + "\n")


def geocode(address, suffix, cache):
    query = f"{address}, {suffix}" if suffix and suffix.lower() not in address.lower() else address
    if query in cache:
        return cache[query]
    time.sleep(1.1)  # Nominatim usage policy: max 1 request per second
    try:
        r = requests.get(NOMINATIM_URL,
                         params={"q": query, "format": "json", "limit": 1},
                         headers={"User-Agent": USER_AGENT}, timeout=30)
        r.raise_for_status()
        hits = r.json()
    except Exception as e:
        print(f"  ! geocoding failed for '{query}': {e}")
        return None  # not cached, so it is retried next run
    result = [float(hits[0]["lat"]), float(hits[0]["lon"])] if hits else None
    cache[query] = result
    return result


def to_float(value):
    try:
        return float(str(value).strip())
    except ValueError:
        return None

# ── 3: BUILD ─────────────────────────────────────────────────────────────────

def build_view(key, view_cfg, suffix, cache):
    path = find_input(view_cfg["input"])
    df = read_sheet(path)
    cols = map_columns(df, path)
    print(f"{view_cfg['label']}: {path.name} ({len(df)} rows)")

    points, skipped = [], []
    for i, row in df.iterrows():
        name = str(row[cols["name"]]).strip()
        if not name:
            continue
        type_ = str(row[cols["type"]]).strip() or "Other"
        address = str(row[cols["address"]]).strip() if "address" in cols else ""

        lat = to_float(row[cols["lat"]]) if "lat" in cols else None
        lon = to_float(row[cols["lon"]]) if "lon" in cols else None
        if (lat is None or lon is None) and address:
            coords = geocode(address, suffix, cache)
            if coords:
                lat, lon = coords
        if lat is None or lon is None:
            skipped.append(f"row {i + 2}: {name}")
            continue
        points.append({"name": name, "type": type_, "address": address,
                       "lat": round(lat, 6), "lon": round(lon, 6)})

    print(f"  {len(points)} pins placed")
    for s in skipped:
        print(f"  ! skipped (no coordinates, address not found) — {s}")
    return {"label": view_cfg["label"], "points": points}, skipped


def main():
    config = json.loads(CONFIG_PATH.read_text())
    cache = load_cache()
    suffix = config.get("geocode_suffix", "")

    views, all_skipped = {}, []
    for key, view_cfg in config["views"].items():
        views[key], skipped = build_view(key, view_cfg, suffix, cache)
        all_skipped += skipped
    save_cache(cache)

    data = {"title": config["title"], "base": config["base"], "views": views}
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {OUTPUT_PATH.relative_to(ROOT)}")
    if all_skipped:
        print(f"WARNING: {len(all_skipped)} row(s) could not be placed on the map")


if __name__ == "__main__":
    main()
