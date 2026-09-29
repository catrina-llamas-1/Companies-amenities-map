# @title EDMONTON OPEN DATA — INTERACTIVE COLUMN FILTER
# Source: City of Edmonton Open Data Portal (dataset qhi4-bdpu)
# Usage: paste this whole file into one Google Colab cell and run it.
# Outputs: an interactive filter panel (one filter per column), a preview of the
#          filtered rows, and an optional CSV download of the filtered data.

import io
import requests
import pandas as pd
import ipywidgets as widgets
from IPython.display import display, clear_output

try:
    from google.colab import files, output
    output.enable_custom_widget_manager()
    IN_COLAB = True
except ImportError:
    IN_COLAB = False

# ── SETTINGS ─────────────────────────────────────────────────────────────────

DATASET_ID = "qhi4-bdpu"
DOMAIN = "https://data.edmonton.ca"
V3_URL = f"{DOMAIN}/api/v3/views/{DATASET_ID}/query.csv"
V2_URL = f"{DOMAIN}/resource/{DATASET_ID}.csv"   # fallback, paged
APP_TOKEN = ""            # optional Socrata app token (avoids throttling)
PAGE_SIZE = 50_000
MAX_LIST_OPTIONS = 2_000  # max values shown in a column's list at one time
PREVIEW_ROWS = 100

# ── 1: LOAD DATA ─────────────────────────────────────────────────────────────

def _headers():
    return {"X-App-Token": APP_TOKEN} if APP_TOKEN else {}


def load_v3():
    r = requests.get(V3_URL, headers=_headers(), timeout=120)
    r.raise_for_status()
    return pd.read_csv(io.StringIO(r.text), dtype=str, keep_default_na=False)


def load_v2_paged():
    pages, offset = [], 0
    while True:
        params = {"$limit": PAGE_SIZE, "$offset": offset, "$order": ":id"}
        r = requests.get(V2_URL, params=params, headers=_headers(), timeout=120)
        r.raise_for_status()
        page = pd.read_csv(io.StringIO(r.text), dtype=str, keep_default_na=False)
        if page.empty:
            break
        pages.append(page)
        print(f"  fetched {offset + len(page):,} rows...")
        if len(page) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return pd.concat(pages, ignore_index=True) if pages else pd.DataFrame()


def load_data():
    print(f"Downloading dataset {DATASET_ID}...")
    try:
        df = load_v3()
        print("  loaded via API v3")
    except Exception as e:
        # The v3 endpoint can reject anonymous requests; SODA 2 is open.
        print(f"  v3 endpoint failed ({e}); falling back to SODA 2 paging")
        df = load_v2_paged()
    df.columns = [c.strip() for c in df.columns]
    df = df.replace("", pd.NA)
    print(f"  {len(df):,} rows x {len(df.columns)} columns")
    return df


# ── 2: DETECT COLUMN TYPES ───────────────────────────────────────────────────

def detect_kind(series):
    """Return 'numeric', 'date' or 'category' for a column of strings."""
    s = series.dropna()
    if s.empty:
        return "category"
    as_num = pd.to_numeric(s, errors="coerce")
    if as_num.notna().mean() >= 0.95 and s.nunique() > 20:
        return "numeric"
    if as_num.notna().mean() < 0.5:
        as_date = pd.to_datetime(s, errors="coerce", format="mixed")
        if as_date.notna().mean() >= 0.95:
            return "date"
    return "category"


def prepare(df):
    """Convert numeric/date columns to real dtypes and record each column's kind."""
    kinds = {}
    for col in df.columns:
        kind = detect_kind(df[col])
        kinds[col] = kind
        if kind == "numeric":
            df[col] = pd.to_numeric(df[col], errors="coerce")
        elif kind == "date":
            df[col] = pd.to_datetime(df[col], errors="coerce", format="mixed")
    return df, kinds


# ── 3: ONE FILTER WIDGET PER COLUMN ──────────────────────────────────────────

BLANK = "(blank)"


class CategoryFilter:
    """Searchable multi-select list. Nothing selected = no filter."""

    def __init__(self, series):
        counts = series.fillna(BLANK).astype(str).value_counts()
        self.all_values = list(counts.index)
        self.counts = counts.to_dict()
        self.selected = set()
        self._updating = False

        self.search = widgets.Text(placeholder="Type to search values...",
                                   layout=widgets.Layout(width="420px"))
        self.select = widgets.SelectMultiple(rows=10,
                                             layout=widgets.Layout(width="420px"))
        self.info = widgets.HTML()
        self.clear_btn = widgets.Button(description="Clear selection",
                                        layout=widgets.Layout(width="140px"))

        self.search.observe(lambda _: self._refresh_options(), names="value")
        self.select.observe(self._on_select, names="value")
        self.clear_btn.on_click(lambda _: self.reset())
        self._refresh_options()

        hint = widgets.HTML("<i>Ctrl/Cmd+click or Shift+click to pick several "
                            "values. Nothing selected = all values kept.</i>")
        self.widget = widgets.VBox([hint, self.search, self.select,
                                    widgets.HBox([self.clear_btn, self.info])])

    def _label(self, v):
        return f"{v}  ({self.counts[v]:,})"

    def _refresh_options(self):
        term = self.search.value.strip().lower()
        matches = [v for v in self.all_values if term in v.lower()] if term else self.all_values
        shown = matches[:MAX_LIST_OPTIONS]
        # Keep already-selected values visible so they are not lost while searching
        shown += [v for v in self.all_values if v in self.selected and v not in shown]
        self._updating = True
        self.select.options = [(self._label(v), v) for v in shown]
        self.select.value = tuple(v for v in shown if v in self.selected)
        self._updating = False
        note = f"{len(matches):,} matching value(s)"
        if len(matches) > MAX_LIST_OPTIONS:
            note += f", showing top {MAX_LIST_OPTIONS:,} — refine the search"
        self.info.value = f"&nbsp;{note} · <b>{len(self.selected)}</b> selected"

    def _on_select(self, change):
        if self._updating:
            return
        visible = {v for _, v in self.select.options}
        self.selected = (self.selected - visible) | set(change["new"])
        self._refresh_options()

    def is_active(self):
        return bool(self.selected)

    def mask(self, series):
        return series.fillna(BLANK).astype(str).isin(self.selected)

    def describe(self):
        vals = sorted(self.selected)
        return ", ".join(vals[:5]) + (f" (+{len(vals) - 5} more)" if len(vals) > 5 else "")

    def reset(self):
        self.selected = set()
        self.search.value = ""
        self._refresh_options()


class NumericFilter:
    """Min/max range. Untouched bounds = no filter."""

    def __init__(self, series):
        self.lo, self.hi = series.min(), series.max()
        self.min_box = widgets.FloatText(value=self.lo, description="Min",
                                         layout=widgets.Layout(width="220px"))
        self.max_box = widgets.FloatText(value=self.hi, description="Max",
                                         layout=widgets.Layout(width="220px"))
        self.keep_blank = widgets.Checkbox(value=True, description="Keep blanks")
        self.widget = widgets.VBox([
            widgets.HTML(f"<i>Range in data: {self.lo:,} to {self.hi:,}</i>"),
            widgets.HBox([self.min_box, self.max_box]), self.keep_blank])

    def is_active(self):
        return (self.min_box.value != self.lo or self.max_box.value != self.hi
                or not self.keep_blank.value)

    def mask(self, series):
        m = series.between(self.min_box.value, self.max_box.value)
        return m | series.isna() if self.keep_blank.value else m

    def describe(self):
        return f"{self.min_box.value:,} to {self.max_box.value:,}"

    def reset(self):
        self.min_box.value, self.max_box.value = self.lo, self.hi
        self.keep_blank.value = True


class DateFilter:
    """Start/end date range. Empty pickers = no filter."""

    def __init__(self, series):
        lo, hi = series.min(), series.max()
        self.start = widgets.DatePicker(description="From")
        self.end = widgets.DatePicker(description="To")
        self.keep_blank = widgets.Checkbox(value=True, description="Keep blanks")
        self.widget = widgets.VBox([
            widgets.HTML(f"<i>Dates in data: {lo:%Y-%m-%d} to {hi:%Y-%m-%d}</i>"),
            widgets.HBox([self.start, self.end]), self.keep_blank])

    def is_active(self):
        return bool(self.start.value or self.end.value or not self.keep_blank.value)

    def mask(self, series):
        m = pd.Series(True, index=series.index)
        day = series.dt.normalize()
        if self.start.value:
            m &= day >= pd.Timestamp(self.start.value)
        if self.end.value:
            m &= day <= pd.Timestamp(self.end.value)
        m &= series.notna()
        return m | series.isna() if self.keep_blank.value else m

    def describe(self):
        return f"{self.start.value or '…'} to {self.end.value or '…'}"

    def reset(self):
        self.start.value = self.end.value = None
        self.keep_blank.value = True


FILTER_TYPES = {"category": CategoryFilter, "numeric": NumericFilter, "date": DateFilter}


# ── 4: BUILD THE DIALOG ──────────────────────────────────────────────────────

def build_dialog(df, kinds):
    filters = {col: FILTER_TYPES[kinds[col]](df[col]) for col in df.columns}
    state = {"filtered": df}

    accordion = widgets.Accordion(children=[f.widget for f in filters.values()])
    for i, col in enumerate(filters):
        accordion.set_title(i, f"{col}  [{kinds[col]}]")
    accordion.selected_index = None

    apply_btn = widgets.Button(description="Apply filters", button_style="primary",
                               icon="filter")
    reset_btn = widgets.Button(description="Reset all", icon="undo")
    download_btn = widgets.Button(description="Download CSV", button_style="success",
                                  icon="download")
    summary = widgets.HTML()
    results = widgets.Output()

    def apply(_=None):
        mask = pd.Series(True, index=df.index)
        active = []
        for col, f in filters.items():
            if f.is_active():
                mask &= f.mask(df[col])
                active.append(f"<li><b>{col}</b>: {f.describe()}</li>")
        state["filtered"] = df[mask]
        summary.value = (
            f"<h4>{len(state['filtered']):,} of {len(df):,} rows match</h4>"
            + (f"<ul>{''.join(active)}</ul>" if active else "<i>No filters active</i>"))
        with results:
            clear_output()
            display(state["filtered"].head(PREVIEW_ROWS))
            if len(state["filtered"]) > PREVIEW_ROWS:
                print(f"Showing first {PREVIEW_ROWS} rows. "
                      "Use `filtered_df` in the next cell for the full result.")
        globals()["filtered_df"] = state["filtered"]

    def reset(_=None):
        for f in filters.values():
            f.reset()
        apply()

    def download(_=None):
        name = f"edmonton_{DATASET_ID}_filtered.csv"
        state["filtered"].to_csv(name, index=False)
        if IN_COLAB:
            files.download(name)
        else:
            print(f"Saved {name}")

    apply_btn.on_click(apply)
    reset_btn.on_click(reset)
    download_btn.on_click(download)

    display(widgets.VBox([
        widgets.HTML("<h3>Edmonton Open Data — Filter by column</h3>"
                     "<i>Expand a column, choose values, then click "
                     "<b>Apply filters</b>. Filters on different columns are "
                     "combined (AND); values within one column are OR.</i>"),
        accordion,
        widgets.HBox([apply_btn, reset_btn, download_btn]),
        summary,
        results,
    ]))
    apply()
    return filters


# ── 5: RUN ───────────────────────────────────────────────────────────────────

raw_df = load_data()
data_df, column_kinds = prepare(raw_df.copy())
filtered_df = data_df
column_filters = build_dialog(data_df, column_kinds)
