# Logos for map pins

The map uses three icons, all placeholders you can customise:

| File | Used for | Colour |
|---|---|---|
| `industrial.svg` | every **Industrial Companies** pin | `#7e9cd1` |
| `amenities.svg` | every **Area Amenities** pin: banks, gas stations, grocery stores, malls, restaurants and any other category file in `data/` | `#4db595` |
| `base.svg` | the **base point**, 21350 Stony Plain Rd | orange map pin |

The **All** view uses both pin logos. Each pin shows its logo in a round frame. With **Rings** on, the frame takes the colour of the place's category in the legend.

## Replacing a logo

1. Make your image. Square images with a transparent or white background look best, and 128 × 128 px is plenty. Supported formats: `.svg`, `.png`, `.jpg`, `.jpeg`, `.webp`.
2. Upload it to this folder (`site/logos/`) on GitHub via **Add file → Upload files**. Then use one of these:
   - **Same name:** give it the same name as the placeholder (e.g. `industrial.svg`) so it replaces it, or
   - **Different name:** keep your own file name, such as `industrial.png`, and change `"logo"` for that view in `config.json`. For the base point, change `"logo"` under `"base"`.
3. After the site rebuilds, the map uses the new icon.

The base point icon is placed by `"anchor"` under `"base"` in `config.json`: the spot on the image that marks the address, as fractions of its width and height. `[0.52, 0.905]` is the tip of the current map pin. Use `[0.5, 0.5]` for an icon centred on the address, like a circle or star, and `[0.5, 1]` for a pin whose tip is at the very bottom.

If an icon file is missing, the build log says so. Pins then fall back to dots in their view's colour, and the base point to a black diamond.
