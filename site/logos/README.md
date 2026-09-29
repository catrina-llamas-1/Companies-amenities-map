# Logos for map pins

The map uses **two logos**, one for each view:

| File | Used for |
|---|---|
| `industrial.svg` | every pin in **Industrial Companies** |
| `amenities.svg` | every pin in **Area Amenities**: banks, gas stations, grocery stores, malls, restaurants and any other category file in `data/` |

Both are placeholders you can customise. Each pin shows its view's logo in a round frame, and the frame's colour matches the place's type in the legend.

## Replacing a logo

1. Make your image. Square images with a transparent or white background look best, and 128 × 128 px is plenty. Supported formats: `.svg`, `.png`, `.jpg`, `.jpeg`, `.webp`.
2. Upload it to this folder (`site/logos/`) on GitHub via **Add file → Upload files**. Then use one of these:
   - **Same name:** give it the same name as the placeholder (e.g. `industrial.svg`) so it replaces it, or
   - **Different name:** keep your own file name, such as `industrial.png`, and change `"logo"` for that view in `config.json`.
3. After the site rebuilds, every pin in that view shows the new logo.

If a view's logo file is missing, the build log says so and that view falls back to plain coloured dots.
