# Companies & Amenities Map

An interactive web map with two views around the base point **21350 Stony Plain Rd, Edmonton**:

- **Industrial Companies**: one pin per row of `data/industrial_companies.*`
- **Area Amenities**: one pin per row of `data/area_amenities.*`

Each pin has a label with its **name** and **type**. Pins are coloured by type, and you can hide or show types in the legend. Clicking a pin opens a popup with its address and distance from the base point. The two buttons at the top switch views, and each view has its own link (`…/#companies`, `…/#amenities`).

## Updating the data

1. Replace the sample files in `data/` with your spreadsheets. Keep exactly one file per view:
   - `data/industrial_companies.xlsx` (or `.xls` / `.csv`)
   - `data/area_amenities.xlsx` (or `.xls` / `.csv`)
2. Each spreadsheet needs these columns (the first sheet is read, header names are not case-sensitive):

   | Column | Required | Also accepted as |
   |---|---|---|
   | Name | yes | Company, Company Name, Business Name, Amenity, Place |
   | Type | yes | Category, Industry, Sector, Amenity Type |
   | Latitude + Longitude | one of these two | Lat / Lng / Long |
   | Address | one of these two | Street Address, Location |

   Rows with an address but no coordinates are geocoded with OpenStreetMap Nominatim. The results are cached in `data/geocode_cache.json`, and any row that can't be found is listed in the build output. For the most precise pins, fill in Latitude/Longitude.
3. Commit and push to `main`. The GitHub Action rebuilds the data and redeploys the site.

The base point's name, address and coordinates, the page title and the view names are set in `config.json`.

## Deploying (one-time setup)

In the GitHub repo, go to **Settings → Pages → Build and deployment → Source** and choose **GitHub Actions**. Every push to `main` then runs `.github/workflows/deploy.yml` and publishes the map at `https://<user>.github.io/<repo>/`. You can also start a deploy from the **Actions** tab ("Build and deploy map" → Run workflow).

## Previewing locally

```bash
pip install pandas openpyxl requests
python build_map_data.py          # writes site/data/map_data.json
python -m http.server -d site 8000
# open http://localhost:8000
```
