# BUILD MAP DATA
# Reads the two input spreadsheets (industrial companies, area amenities) and
# writes site/data/map_data.json, which the web map loads.
#
# Usage:  pip install pandas openpyxl
#         python build_map_data.py
#
# Each spreadsheet needs Name, Type, Lat and Lng columns (Address, Rating,
# Reviews and URL are used when present). Every sheet in a workbook is read and
# duplicate rows (same name and coordinates) are merged. Only places inside the
# City of Edmonton boundary are kept; the boundary is downloaded from the City's
# open data portal on first run and saved to data/edmonton_boundary.geojson.
# A place gets a logo pin when site/logos holds an image named after it, or
# when an optional Logo column names a file in site/logos.

import json
import math
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
BOUNDARY_PATH = ROOT / "data" / "edmonton_boundary.geojson"
OUTPUT_PATH = ROOT / "site" / "data" / "map_data.json"
LOGO_DIR = ROOT / "site" / "logos"
SPREADSHEET_EXTENSIONS = [".xlsx", ".xls", ".csv"]
LOGO_EXTENSIONS = [".svg", ".png", ".jpg", ".jpeg", ".webp"]

OPEN_DATA = "https://data.edmonton.ca"
BOUNDARY_SEARCH = "corporate boundary"
BOUNDARY_HELP = (
    "Download the boundary by hand: on data.edmonton.ca search for "
    "'City of Edmonton - Corporate Boundary', choose Export -> GeoJSON, and "
    f"upload the file as {BOUNDARY_PATH.relative_to(ROOT)}")

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
    "logo": ["logo", "logofile", "icon"],
}
REQUIRED = ["name", "type", "lat", "lon"]

# ── 1: READ SPREADSHEETS ─────────────────────────────────────────────────────

def find_input(prefix):
    """Return the single spreadsheet whose name starts with <prefix>
    (so 'area_amenities.xlsx', 'area_amenities_.csv' etc. all match)."""
    folder, stem = (ROOT / prefix).parent, Path(prefix).name
    matches = sorted(p for p in folder.glob(f"{stem}*")
                     if p.suffix.lower() in SPREADSHEET_EXTENSIONS)
    if not matches:
        sys.exit(f"ERROR: no spreadsheet found for {prefix}* "
                 f"(expected one of {', '.join(SPREADSHEET_EXTENSIONS)})")
    if len(matches) > 1:
        sys.exit(f"ERROR: several spreadsheets for {prefix}*: "
                 f"{', '.join(m.name for m in matches)} — keep only one")
    return matches[0]


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

# ── 2: CITY OF EDMONTON BOUNDARY ─────────────────────────────────────────────

def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "companies-amenities-map"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def boundary_polygons(geojson):
    """Return a list of polygons, each a list of rings of (lon, lat)."""
    features = geojson.get("features", [geojson])
    polygons = []
    for f in features:
        geom = f.get("geometry") or {}
        if geom.get("type") == "Polygon":
            polygons.append(geom["coordinates"])
        elif geom.get("type") == "MultiPolygon":
            polygons.extend(geom["coordinates"])
    return polygons


def point_in_polygons(lon, lat, polygons):
    """Even-odd ray casting; holes are handled because every ring is counted."""
    for rings in polygons:
        inside = False
        for ring in rings:
            for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
                if (y1 > lat) != (y2 > lat) and lon < x1 + (lat - y1) * (x2 - x1) / (y2 - y1):
                    inside = not inside
        if inside:
            return True
    return False


def download_boundary(base):
    """Find the Corporate Boundary dataset on data.edmonton.ca and download it."""
    query = urllib.parse.urlencode({"q": BOUNDARY_SEARCH, "only": "datasets,maps", "limit": 20})
    results = fetch_json(f"{OPEN_DATA}/api/catalog/v1?{query}")["results"]
    ids, names = [], {}
    for r in results:
        name = r["resource"]["name"]
        if "corporate boundary" in name.lower():
            for dataset_id in [r["resource"]["id"], *(r["resource"].get("parent_fxf") or [])]:
                ids.append(dataset_id)
                names.setdefault(dataset_id, name)
    if not ids:
        raise RuntimeError(f"no 'Corporate Boundary' dataset found on {OPEN_DATA}")

    for dataset_id in dict.fromkeys(ids):
        for url in (f"{OPEN_DATA}/resource/{dataset_id}.geojson",
                    f"{OPEN_DATA}/api/geospatial/{dataset_id}?method=export&format=GeoJSON"):
            try:
                geojson = fetch_json(url)
            except Exception as e:
                print(f"  (tried {url}: {e})")
                continue
            polygons = boundary_polygons(geojson)
            if polygons and point_in_polygons(base["lon"], base["lat"], polygons):
                lons = [x for rings in polygons for x, _ in rings[0]]
                lats = [y for rings in polygons for _, y in rings[0]]
                print(f"  downloaded '{names[dataset_id]}' from {url}: {len(polygons)} polygon(s), "
                      f"lat {min(lats):.3f}..{max(lats):.3f}, lon {min(lons):.3f}..{max(lons):.3f}")
                return geojson
            print(f"  (skipped '{names[dataset_id]}' at {url}: no polygon containing the base point)")
    raise RuntimeError("could not download a usable boundary")


def load_boundary(base):
    if BOUNDARY_PATH.exists():
        geojson = json.loads(BOUNDARY_PATH.read_text())
    else:
        print("City of Edmonton boundary not found locally, downloading...")
        try:
            geojson = download_boundary(base)
        except Exception as e:
            sys.exit(f"ERROR: could not get the City of Edmonton boundary ({e}).\n{BOUNDARY_HELP}")
        BOUNDARY_PATH.write_text(json.dumps(geojson) + "\n")
    polygons = boundary_polygons(geojson)
    if not polygons or not point_in_polygons(base["lon"], base["lat"], polygons):
        sys.exit(f"ERROR: {BOUNDARY_PATH.name} does not contain the base point. {BOUNDARY_HELP}")
    return polygons

# ── 3: HELPERS ───────────────────────────────────────────────────────────────

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

def load_logos(placeholder):
    """Return {normalized file name: file name} for the images in site/logos,
    so 'Empire Metal & Recycling Ltd..png' matches the company of that name."""
    if not LOGO_DIR.is_dir():
        return {}
    return {normalize(p.stem): p.name for p in sorted(LOGO_DIR.iterdir())
            if p.suffix.lower() in LOGO_EXTENSIONS and p.name != placeholder}

# ── 4: BUILD ─────────────────────────────────────────────────────────────────

def build_view(view_cfg, base, city, logos):
    path = find_input(view_cfg["input"])
    points, seen = [], set()
    no_coords, outside, missing_logos, dupes = [], [], [], 0

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
            key = (name.lower(), round(lat, 5), round(lon, 5))
            if key in seen:
                dupes += 1
                continue
            seen.add(key)
            km = distance_km(base["lat"], base["lon"], lat, lon)
            if not point_in_polygons(lon, lat, city):
                outside.append(f"'{sheet}' row {i + 2}: {name} ({km:,.1f} km from base)")
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

            # Logo: named in a Logo column, or a file in site/logos named after the place
            logo = get(row, "logo")
            if logo and not (LOGO_DIR / logo).is_file():
                missing_logos.append(f"'{sheet}' row {i + 2}: {name} -> logos/{logo}")
                logo = ""
            logo = logo or logos.get(normalize(name), "")
            if logo:
                point["logo"] = logo
            points.append(point)

    points.sort(key=lambda p: p["km"])
    with_logo = sum("logo" in p for p in points)
    print(f"{view_cfg['label']}: {path.name} -> {len(points)} pins in Edmonton "
          f"({dupes} duplicates merged, {with_logo} with a logo)")
    for label, rows in (("no coordinates", no_coords), ("outside Edmonton", outside),
                        ("a Logo file that is not in site/logos", missing_logos)):
        if rows:
            print(f"  skipped {len(rows)} row(s) with {label}:")
            for r in rows:
                print(f"    - {r}")
    return {"label": view_cfg["label"], "points": points}


def main():
    config = json.loads(CONFIG_PATH.read_text())
    base = config["base"]
    city = load_boundary(base)
    logo_cfg = config.get("logos", {})
    logos = load_logos(logo_cfg.get("placeholder", ""))
    views = {key: build_view(cfg, base, city, logos) for key, cfg in config["views"].items()}

    data = {"title": config["title"], "base": base,
            "radius_options_km": config["radius_options_km"],
            "default_radius_km": config["default_radius_km"],
            "logos": logo_cfg, "views": views}
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"Wrote {OUTPUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
