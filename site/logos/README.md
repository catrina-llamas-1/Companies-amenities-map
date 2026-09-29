# Logos for map pins

Put logo images here to show them as pins on the map instead of coloured dots.

## Adding a logo

1. Name the image after the place **exactly as it appears in the spreadsheet's Name column**. Capitals, spaces and punctuation don't matter. For example, each of these matches "Empire Metal & Recycling Ltd.":
   - `Empire Metal & Recycling Ltd.png`
   - `empire-metal-recycling-ltd.png`
   - `EmpireMetalRecyclingLtd.svg`
2. Upload it to this folder (`site/logos/`). On GitHub, open the folder and choose **Add file → Upload files**.
3. After the site rebuilds, that place's pin shows the logo. The build log reports how many pins have a logo.

Instead of matching by name, you can add a **Logo** column to the spreadsheet and type the file name, e.g. `empire.png`. The build log lists any Logo file that can't be found here.

Supported formats: `.svg`, `.png`, `.jpg`, `.jpeg`, `.webp`. Square images with a transparent or white background look best, and 128 × 128 px is plenty.

## The placeholder

`placeholder.svg` is a generic logo that you can customise. Replace it with your own image under the same name, or point `logos.placeholder` in `config.json` at another file. It's used:

- when a logo image fails to load;
- on **every pin without a logo**, if you set `"placeholder_for_all": true` under `logos` in `config.json`. This is off by default, so places without a logo keep their coloured dot.
