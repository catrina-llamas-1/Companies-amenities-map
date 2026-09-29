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
3. Give GitHub permission to deploy by adding a service-account secret. Use either method.

   **Option A (recommended): Firebase CLI.** Run this from [Google Cloud Shell](https://shell.cloud.google.com) or any computer with Node.js:

   ```bash
   npm install -g firebase-tools    # skip if `firebase --version` already works
   firebase login                   # in Cloud Shell: firebase login --no-localhost
   git clone https://github.com/catrina-llamas-1/Companies-amenities-map.git
   cd Companies-amenities-map
   firebase init hosting:github
   ```

   Answer the prompts as follows:
   - **Repository:** `catrina-llamas-1/Companies-amenities-map`
   - **Set up the workflow to run a build script:** No
   - **Set up automatic deployment when a PR is merged:** No
   - **Overwrite** any existing file: No

   This creates a service account with the right permissions and stores it as the GitHub secret `FIREBASE_SERVICE_ACCOUNT_STONY_PLAIN_RD_COMPANIES_MAP`. The workflows already use that name.

   **Option B: by hand.**
   1. In the [Google Cloud console](https://console.cloud.google.com/iam-admin/serviceaccounts?project=stony-plain-rd-companies-map), go to **IAM & Admin → Service accounts → Create service account**. Give it the roles **Firebase Hosting Admin**, **Cloud Run Viewer** and **API Keys Viewer**.
   2. Open the new account and go to **Keys → Add key → Create new key → JSON**. A JSON file downloads.
   3. In GitHub, go to **Settings → Secrets and variables → Actions → New repository secret**. Name it `FIREBASE_SERVICE_ACCOUNT`, paste the whole JSON file as the value, and save.
   4. Delete the downloaded file afterwards. It's a password for your Firebase project.

### What happens after setup

- **Push to `main`** → `.github/workflows/firebase-hosting-merge.yml` builds the map data and deploys it live to `https://<project-id>.web.app`.
- **Pull request** → `.github/workflows/firebase-hosting-pull-request.yml` deploys a 7-day preview and comments its link on the PR.
- Until the secret and project ID are set, both workflows only build the data and skip the deploy, so checks stay green.

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
