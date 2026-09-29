# Companies & Amenities Map

Filter City of Edmonton open data (dataset `qhi4-bdpu`) in Google Colab, publish
the result to Firebase, and view it on a public, read-only web map.

- **Colab tool**: `edmonton_open_data_filter.py`, pasted into one Colab cell
- **Map site**: `public/`, served by Firebase Hosting at
  <https://stony-plain-rd-companies-map.web.app>
- **Data**: Firestore (`nam5`), public read and no client writes (`firestore.rules`)

## How the data flows

1. Run the Colab cell, filter the rows, and click **Publish to map**.
2. The rows are written to Firestore as a few large JSON documents in
   `map_chunks`, and `map_meta/current` points at the latest set. Loading the
   map therefore costs only a few document reads, not one read per row.
3. The map reads `map_meta/current` and its chunks, then plots every row that
   has a location. Location comes from `latitude`/`longitude` columns or from a
   `POINT (lng lat)` / `(lat, lng)` column. Rows without a location still count
   towards the totals and the search results.

Each publish replaces what the map shows. New chunks are written first and the
old ones are deleted afterwards, so visitors never see a half-finished upload.

## One-time setup

### 1. Service account key for Colab (to publish)

1. Firebase console → Project settings → **Service accounts** →
   **Generate new private key**. A JSON file downloads.
2. In Colab, open the key icon (**Secrets**) in the left sidebar and add a
   secret named `FIREBASE_SERVICE_ACCOUNT`. Paste the whole JSON file contents
   as its value and turn on notebook access.
   Alternatively, upload the file to the Colab session as `service-account.json`.

Never commit this key. `.gitignore` blocks the usual file names.

### 2. Deploy the rules and the map site

Do this from any computer with Node.js installed:

```bash
npm install -g firebase-tools
firebase login
firebase deploy --only firestore,hosting
```

`.firebaserc` already points at `stony-plain-rd-companies-map`. Run the deploy
again whenever `public/` or `firestore.rules` changes. Publishing new data from
Colab needs no redeploy.

## Local preview

```bash
firebase serve --only hosting     # http://localhost:5000
```

The preview reads the live Firestore data.
