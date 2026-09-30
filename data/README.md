# Input spreadsheets

Upload the map's spreadsheets here:

- **Industrial Companies:** one file whose name starts with `industrial_companies`, e.g. `industrial_companies.xlsx`.
- **Area Amenities:** every other spreadsheet in this folder, one per category, e.g. `Bank.xlsx`, `Gas Station.xlsx`, `Grocery.xlsx`, `Mall.xlsx`, `Restaurant.xlsx`. To add a category, upload another file; to remove one, delete its file.

`.xlsx`, `.xls` and `.csv` all work. Every sheet inside a workbook is read.

Required columns: **Name**, **Type**, **Lat**, **Lng**. **Address**, **Rating**, **Reviews** and **URL** are used when present.

Only places within 5 km of the base point (21350 Stony Plain Rd) are shown; rows farther away can stay in the files and are simply left off the map.

To upload on GitHub, open this folder and choose **Add file → Upload files**.
