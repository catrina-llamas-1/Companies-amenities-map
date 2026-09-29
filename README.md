# Companies & Amenities Map

An interactive web map with two views around the base point **21350 Stony Plain Rd, Edmonton**:

- **Industrial Companies**: from `data/industrial_companies.xlsx`
- **Area Amenities**: from `data/area_amenities.xlsx`

Pins are plotted from each row's Lat/Lng and labelled with the place's **name**. Labels appear whenever 60 or fewer pins are on screen, or at street-level zoom.

The map has these controls:
- **Views:** the two buttons at the top switch views. Each view has its own link (`…/#companies`, `…/#amenities`).
- **Distance:** the drop-down limits pins to a radius around the base point (1–50 km, default 2.5 km) and draws that radius as a dashed circle.
- **Search:** filters pins by name, type or address.
- **Legend:** the 10 most common types within the chosen radius get their own colour, and the rest are grouped as "Other types". Untick a type to hide it.
- **Base map:** the layers button under the zoom controls switches between Street (OpenStreetMap), Street (Esri) and Satellite (Esri). None of these needs an API key. The page remembers the last choice, and if a map's tiles fail to load it switches to the next one automatically.
- **Popups:** clicking a pin shows its type, address, rating, distance from the base point and a Google Maps link.

## Updating the data

1. Replace the spreadsheets in `data/`, keeping exactly one file per view. The file name must start with `industrial_companies` or `area_amenities` (for example `area_amenities.xlsx` or `area_amenities_.csv`). `.xlsx`, `.xls` and `.csv` all work.
2. Required columns: **Name**, **Type**, **Lat**, **Lng** ("Latitude" and "Longitude" also work). **Address**, **Rating**, **Reviews** and **URL** (the Google Maps link) are used when present, and other columns are ignored.
3. Every sheet in a workbook is read. Rows that appear more than once (same name and coordinates) are merged. Rows without coordinates are skipped, and so are rows **outside the City of Edmonton**. Every skipped row is listed in the build log.

   The Edmonton check uses the official City of Edmonton Corporate Boundary. The build downloads it from [data.edmonton.ca](https://data.edmonton.ca) and saves it as `data/edmonton_boundary.geojson`. If the download fails, the build stops rather than include places outside the city. To fix that, open the dataset on data.edmonton.ca, choose **Export → GeoJSON**, and upload the file to `data/` with that name.
4. Commit and push to `main`, and the site redeploys automatically.

The base point's name and coordinates, the page title, the view names and the distance options are set in `config.json`.

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
