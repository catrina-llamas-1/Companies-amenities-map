# Input spreadsheets

Upload the map's spreadsheets here:

- **Industrial Companies:** one file whose name starts with `industrial_companies`, e.g. `industrial_companies.xlsx`.
- **Area Amenities:** every other spreadsheet in this folder, one per category, e.g. `Bank.xlsx`, `Gas Station.xlsx`, `Grocery.xlsx`, `Mall.xlsx`, `Restaurant.xlsx`. To add a category, upload another file; to remove one, delete its file.

`.xlsx`, `.xls` and `.csv` all work. Every sheet inside a workbook is read.

Required columns: **Name**, **Type**, **Lat**, **Lng**. **Address**, **Rating**, **Reviews** and **URL** are used when present.

Only places inside the City of Edmonton are shown. `edmonton_boundary.geojson`, the official city boundary, is downloaded here automatically by the build.

To upload on GitHub, open this folder and choose **Add file → Upload files**.
