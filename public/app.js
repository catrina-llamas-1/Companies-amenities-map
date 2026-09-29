import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js";
import {
  getFirestore, doc, getDoc,
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore-lite.js";
import { firebaseConfig } from "./firebase-config.js";

const EDMONTON = [53.5461, -113.4938];
const MAX_FILTER_OPTIONS = 60;   // category columns with more values get no checklist
const NAME_HINTS = ["trade_name", "business_name", "company", "name", "title"];

const els = {
  count: document.getElementById("count"),
  search: document.getElementById("search"),
  filters: document.getElementById("filters"),
  reset: document.getElementById("reset"),
  meta: document.getElementById("meta"),
};

const map = L.map("map").setView(EDMONTON, 11);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
}).addTo(map);
const cluster = L.markerClusterGroup({ chunkedLoading: true });
map.addLayer(cluster);

// ── Load ────────────────────────────────────────────────────────────────────

async function loadData() {
  const db = getFirestore(initializeApp(firebaseConfig));
  const metaSnap = await getDoc(doc(db, "map_meta", "current"));
  if (!metaSnap.exists()) return { meta: null, rows: [] };
  const meta = metaSnap.data();
  const ids = Array.from({ length: meta.chunkCount },
    (_, i) => `${meta.version}_${String(i).padStart(4, "0")}`);
  const chunks = await Promise.all(ids.map((id) => getDoc(doc(db, "map_chunks", id))));
  const rows = chunks.flatMap((snap) => (snap.exists() ? JSON.parse(snap.data().rows_json) : []));
  return { meta, rows };
}

// ── Helpers ─────────────────────────────────────────────────────────────────

const escapeHtml = (s) => String(s).replace(/[&<>"']/g,
  (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const BLANK = "(blank)";
const valueOf = (row, col) => (row[col] == null || row[col] === "" ? BLANK : String(row[col]));

function pickNameColumn(columns) {
  const lower = columns.map((c) => c.toLowerCase());
  for (const hint of NAME_HINTS) {
    const i = lower.findIndex((c) => c === hint || c.includes(hint));
    if (i >= 0) return columns[i];
  }
  return columns[0];
}

function popupHtml(row, columns, nameCol) {
  const cells = columns
    .filter((c) => row[c] != null && row[c] !== "")
    .map((c) => `<tr><th>${escapeHtml(c)}</th><td>${escapeHtml(row[c])}</td></tr>`)
    .join("");
  return `<div class="popup"><h3>${escapeHtml(row[nameCol] ?? "")}</h3><table>${cells}</table></div>`;
}

// ── Filters ─────────────────────────────────────────────────────────────────

function buildFilters(rows, columns, kinds, onChange) {
  const selected = {};   // column -> Set of chosen values
  els.filters.innerHTML = "";

  for (const col of columns) {
    if ((kinds[col] ?? "category") !== "category") continue;
    const counts = new Map();
    for (const r of rows) counts.set(valueOf(r, col), (counts.get(valueOf(r, col)) ?? 0) + 1);
    if (counts.size < 2 || counts.size > MAX_FILTER_OPTIONS) continue;

    selected[col] = new Set();
    const box = document.createElement("details");
    const summary = document.createElement("summary");
    const badge = document.createElement("span");
    badge.className = "active";
    summary.append(`${col} `, badge);
    const options = document.createElement("div");
    options.className = "options";

    [...counts.entries()].sort((a, b) => b[1] - a[1]).forEach(([value, n]) => {
      const label = document.createElement("label");
      const input = document.createElement("input");
      input.type = "checkbox";
      input.value = value;
      input.addEventListener("change", () => {
        if (input.checked) selected[col].add(value); else selected[col].delete(value);
        badge.textContent = selected[col].size ? `(${selected[col].size})` : "";
        onChange();
      });
      const n_ = document.createElement("span");
      n_.className = "n";
      n_.textContent = n.toLocaleString();
      label.append(input, value, n_);
      options.append(label);
    });

    box.append(summary, options);
    els.filters.append(box);
  }

  const reset = () => {
    for (const set of Object.values(selected)) set.clear();
    els.filters.querySelectorAll("input[type=checkbox]").forEach((i) => { i.checked = false; });
    els.filters.querySelectorAll(".active").forEach((b) => { b.textContent = ""; });
  };
  return { selected, reset };
}

// ── Main ────────────────────────────────────────────────────────────────────

async function main() {
  let data;
  try {
    data = await loadData();
  } catch (e) {
    els.count.textContent = "Could not load data.";
    els.meta.textContent = e.message;
    console.error(e);
    return;
  }
  const { meta, rows } = data;
  if (!meta) {
    els.count.textContent = "No data published yet.";
    els.meta.textContent = "Run the Colab tool and click “Publish to map”.";
    return;
  }

  const columns = meta.columns ?? Object.keys(rows[0] ?? {}).filter((c) => !c.startsWith("_"));
  const nameCol = pickNameColumn(columns);
  const items = rows.map((row) => ({
    row,
    text: columns.map((c) => row[c] ?? "").join(" ").toLowerCase(),
    marker: row._lat == null ? null
      : L.marker([row._lat, row._lng]).bindPopup(() => popupHtml(row, columns, nameCol)),
  }));

  const filters = buildFilters(rows, columns, meta.kinds ?? {}, render);

  function render() {
    const term = els.search.value.trim().toLowerCase();
    const active = Object.entries(filters.selected).filter(([, set]) => set.size);
    const matches = items.filter(({ row, text }) =>
      (!term || text.includes(term))
      && active.every(([col, set]) => set.has(valueOf(row, col))));
    const markers = matches.map((m) => m.marker).filter(Boolean);
    cluster.clearLayers();
    cluster.addLayers(markers);
    const unmapped = matches.length - markers.length;
    els.count.textContent = `${matches.length.toLocaleString()} of ${items.length.toLocaleString()} places`
      + (unmapped ? ` (${unmapped.toLocaleString()} without a location)` : "");
    return markers;
  }

  let timer;
  els.search.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(render, 200); });
  els.reset.addEventListener("click", () => { els.search.value = ""; filters.reset(); render(); });

  const markers = render();
  if (markers.length) map.fitBounds(L.featureGroup(markers).getBounds(), { padding: [30, 30] });

  const updated = meta.updatedAt?.toDate?.();
  els.meta.innerHTML = `Source: <a href="${escapeHtml(meta.source ?? "#")}" target="_blank" rel="noopener">City of Edmonton Open Data</a>`
    + (updated ? ` · updated ${updated.toLocaleDateString()}` : "");
}

main();
