# Companies & Amenities Map

An interactive web map with three views around the base point **21350 Stony Plain Rd, Edmonton**:

- **Industrial Companies**: from `data/industrial_companies.xlsx`
- **Area Amenities**: from every other spreadsheet in `data/`, one file per category (e.g. `Bank.xlsx`, `Gas Station.xlsx`, `Grocery.xlsx`, `Mall.xlsx`, `Restaurant.xlsx`)
- **All**: both of the above together, each keeping its own logo

Pins are plotted from each row's Lat/Lng and labelled with the place's **name**. Labels appear whenever 60 or fewer pins are on screen, or at street-level zoom.

The map has these controls:
- **Views:** the buttons at the top switch views. Each view has its own link (`…/#companies`, `…/#amenities`, `…/#all`).
- **Distance:** the drop-down narrows pins to 1, 2.5 or 5 km around the base point and draws that radius as a dashed circle. The **Radius** checkbox shows or hides the circle.
- **Search:** filters pins by name, type or address.
- **Legend:** the 10 most common types within the chosen radius get their own colour, and the rest are grouped as "Other types". Untick a type to hide it.
- **Base map:** the **Map / Satellite** buttons at the top switch between the street map and satellite imagery, which is overlaid with road and place names. The layers button under the zoom controls also offers Street (OpenStreetMap), Street (Esri) and Satellite (Esri). None of these needs an API key. The page remembers the last choice, and if a map's tiles fail to load it switches to the next one automatically.
- **Logo pins:** Industrial Companies pins show `site/logos/industrial.svg` (colour `#3a4458`), Area Amenities pins show `site/logos/amenities.svg` (colour `#55489d`), and the base point shows `site/logos/base.svg`. All three are placeholders; see [`site/logos/README.md`](site/logos/README.md) to replace them.
- **Rings:** each pin is framed in its category's colour from the legend. The **Rings** checkbox shows or hides these rings.
- **Print / PDF:** prints the map on its own, without the top bar, legend or map buttons. Choose "Save as PDF" in the print dialog to get a file. Set up the view first, including labels, rings, radius and satellite.
- **Popups:** clicking a pin shows its type, address, rating, distance from the base point and a Google Maps link.

## Updating the data

1. Put the spreadsheets in `data/`. `.xlsx`, `.xls` and `.csv` all work.
   - **Industrial Companies:** exactly one file whose name starts with `industrial_companies`.
   - **Area Amenities:** any number of other spreadsheets, one per category. To add a category, upload another file, e.g. `Pharmacy.xlsx`; to remove one, delete its file.
2. Required columns: **Name**, **Type**, **Lat**, **Lng** ("Latitude" and "Longitude" also work). **Address**, **Rating**, **Reviews** and **URL** (the Google Maps link) are used when present, and other columns are ignored.
3. Every sheet in a workbook is read. Rows that appear more than once (same name and coordinates) are merged. Only places **within 5 km of the base point** are kept (`max_distance_km` in `config.json`). Rows without coordinates are skipped and listed in the build log, and the log also reports how many rows were too far away.
4. Commit and push to `main`, and the site redeploys automatically.

The base point's name and coordinates, the page title, the view names, the 5 km limit and the distance options are set in `config.json`.

## Deploying to Firebase Hosting

### One-time setup

1. Create a project in the [Firebase console](https://console.firebase.google.com/). Hosting is included on the free Spark plan.
2. Put its project ID in `.firebaserc` in place of `your-firebase-project-id`.
3. Let GitHub deploy to the project. This uses Google's keyless [Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation), so no service-account key or secret is needed. It works even when your organisation blocks key creation (`iam.disableServiceAccountKeyCreation`).
   1. Open [Google Cloud Shell](https://shell.cloud.google.com), signed in as an owner of the Firebase project, and run:

      ```bash
      cd ~
      git clone https://github.com/catrina-llamas-1/Companies-amenities-map.git map-setup
      bash ~/map-setup/scripts/setup_github_deploy.sh
      ```

      The script creates a `github-deploy` service account with only the roles needed to deploy Hosting. It then allows only this repository's GitHub Actions to use that account. It's safe to run again. Before the pull request is merged, the script only exists on its branch, so add `-b claude/sweet-turing-k7tqx7` after `git clone`.
   2. The script prints two values. In GitHub, go to **Settings → Secrets and variables → Actions → Variables** tab, click **New repository variable**, and add both:
      - `GCP_WORKLOAD_IDENTITY_PROVIDER`
      - `GCP_SERVICE_ACCOUNT`

      These are variables, not secrets. They aren't sensitive, because only this repository can use them.

### What happens after setup

- **Push to `main`** → `.github/workflows/firebase-hosting-merge.yml` builds the map data and deploys it live to `https://<project-id>.web.app`.
- **Pull request** → `.github/workflows/firebase-hosting-pull-request.yml` deploys a 7-day preview and comments its link on the PR.
- Until those two variables are set, both workflows only build the data and skip the deploy, so checks stay green.

### Deploying by hand

```bash
pip install -r requirements.txt
firebase deploy --only hosting   # runs build_map_data.py first (predeploy)
```

## Previewing locally

```bash
pip install -r requirements.txt
python build_map_data.py          # writes site/data/map_data.json
python -m http.server -d site 8000
# open http://localhost:8000
```

Or run `firebase emulators:start --only hosting` to serve it exactly as Firebase will.
