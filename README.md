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

1. Replace the spreadsheets in `data/`, keeping exactly one file per view: `industrial_companies.xlsx` and `area_amenities.xlsx` (`.xls` or `.csv` also work).
2. Required columns: **Name**, **Type**, **Lat**, **Lng** ("Latitude" and "Longitude" also work). **Address**, **Rating**, **Reviews** and **URL** (the Google Maps link) are used when present, and other columns are ignored.
3. Every sheet in a workbook is read. Rows that appear more than once (same name and coordinates) are merged. Rows without coordinates, or more than 50 km from the base point, are skipped and listed in the build log.
4. Commit and push to `main`, and the site redeploys automatically.

The base point's name and coordinates, the page title, the view names and the distance options are set in `config.json`.

## Deploying to Firebase Hosting

### One-time setup

1. Create a project in the [Firebase console](https://console.firebase.google.com/). Hosting is included on the free Spark plan.
2. Put its project ID in `.firebaserc` in place of `your-firebase-project-id`.
3. Connect GitHub so pushes deploy automatically. From a computer with Node.js installed:

   ```bash
   npm install -g firebase-tools
   firebase login
   firebase init hosting:github
   ```

   When asked, choose this repository. Answer **No** to "set up a workflow to run a build script" and **No** to overwriting the existing workflow files. This step creates a service account and saves it as a repository secret. The secret name ends with your project ID (for example `FIREBASE_SERVICE_ACCOUNT_MY_PROJECT`). Either rename it to `FIREBASE_SERVICE_ACCOUNT` in **GitHub → Settings → Secrets and variables → Actions**, or change the secret name in both files under `.github/workflows/`.

   Alternatively, create the secret by hand. Go to **Firebase console → Project settings → Service accounts → Generate new private key**. Then add a repository secret named `FIREBASE_SERVICE_ACCOUNT` and paste the whole JSON file as its value.

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
