# Frontend build plan: NISAR coastal-hazard workspace

> ## Build status (updated Sat 14 Nov 2026, after the review pass)
>
> - **Done:** batches 1 to 4 (data contract and assets, core, shell, map, panels, layer drawer, live layers, compare, events tab, A4 brief). **Batch 5** (Case study tab: `case.js`, `case.css`, `case.en.json`) was written by a Haiku agent and has had one review pass. **Batch 6** (final phone and accessibility pass, `docs/ADDING_CONTENT.md`, `tools/audit_page.sh`) is pending.
> - **Deviations from this plan:**
>   - D3 (`analysis.js`) was dropped: analysis selection lives in `panels.js` (`pickAnalysis`). `index.html` no longer loads it.
>   - Haiku, not Sonnet, was used for batches 4 and 5 at the owner's request.
>   - Header: compact (hamburger) menu now applies up to 1199 px; the single row at 1200 px and wider shows the full app name. Alerts strip is one 44 px line at every width, with a short date ("27 Oct, 17:30 IST") and a "Sample" tag at 1100 px and below.
>   - Compare: the old bar plus legend card plus band card is replaced by a top-left row [Compare] [Classes and band]; the compare bar is one compact row; classes, band and credits sit in one collapsed popover (max 40% of map height); while comparing, the map caption shrinks to one line (chip, date, Details). Default Left = latest `before` layer of the series (16 Oct).
>   - Basemap switched to Esri World Dark Gray (CARTO needs an API key now).
>   - The 28 Oct coast layer sits under DURING (not AFTER).
>   - Derived class layers are one manifest layer per class, not one paletted PNG.
>   - Series rows: only the newest row of a time series follows the header date picker; older dated rows draw their own scene.
>   - Compare uses its own divider, not leaflet-side-by-side (that plugin cannot clip `L.ImageOverlay`).
> - **Known leftovers:** real data (see `docs/BACKEND_GAPS.md` section 13); Telugu strings; Case study copy review; live-readout cards on phones can overlap the compare bar when both are open; quick-look images are display-only; no offline mode (CDN scripts and fonts); `tools/audit_page.sh` and `docs/ADDING_CONTENT.md` not written.


Team SpaceBros · NASA Space Apps 2026 · "Dancing with the SARs" · written Sat 14 Nov 2026
Deadline Sun 15 Nov 20:00 IST. Gates (from the plan): Sat 23:00 first viewable page, Sun 11:30 MVP, Sun 16:00 freeze, Sun 20:00 submit.

Status: the original plan text below is kept as written; see the Build status box above for what changed.

---

## 0. What differs from the brief (read first)

| # | The brief says | What is really in the repo / workspace | Consequence |
|---|---|---|---|
| 1 | `docs/handoff/PROJECT_CONTEXT.md`, `UI_MOCKUP_SPEC.md`, `mockup-png/` exist | **None of them exist**, anywhere on this machine. `docs/handoff/` did not exist. | I rebuilt the context from the files that do exist: `04_Project_Idea/06_PLAN…md`, `09_UI_MOCKUP_PROMPT.md`, `10_UI_DIRECTION_AND_RISKS.md` (copied to `docs/handoff/`), the repo's `docs/DATA_ACQUISITION_PLAN.md`, `FETCH_TASKS.md`, `data/sources.yaml`, `data/logs/*`. `07_BACKEND_RESOURCE_REGISTRY.pdf` and `08_EVIDENCE_PACK.pdf` could not be read (no PDF tool here); their content is mirrored in plan §2b–2e, which I did read. **If the real handoff files exist elsewhere, send them and I will diff this plan against them before any code.** |
| 2 | UI spec "written out" with a binding "what changes from the mockup" table | There is no spec. There **is** the real mockup: a Design canvas (https://claude.ai/artifact/AhKDZ8HmCuVyTeWSxy4zuE, 8 artboards). I saved its source to `docs/handoff/mockup-src/*.dc.html`; those files hold the exact CSS values, copy, and component markup. | Sonnet agents will read `mockup-src/` directly. The "what changes" rules are the ones in your message (daily tool, not a story). |
| 3 | `data/` has GIBS PNGs, `data/browse/nisar_arnab` quick-looks, reference CSVs, raw boundaries/water/coast | All true, **but** `data/raw/` (incl. all GIBS PNGs, 13 MB) is **git-ignored**, so GitHub Pages cannot serve it. Web-ready copies must be exported into the tracked `data/processed/`, which is **empty (0 bytes)** today. | Task A2 (asset prep) is mandatory, not optional. |
| 4 | Quick-looks are usable as map PNGs | The 10 `data/browse/nisar_arnab` PNGs are **1.6–4.7 MB each** (47 MB total), in NISAR's magenta/green colour composite. Plan rule: ≤ 600 KB each, greyscale. | A2 crops, downsamples and greys them. They are not shipped as-is. |
| 5 | Quick-looks come with bounds | 5 scenes (3, 4, 10, 15, 16 Oct, all NISAR *provisional* products) have **no KML** (HTTP 401). The calm-sea 15 Oct and pre-storm coast 16 Oct, the two "before" scenes, are among them. | A2 infers bounds from the same track/frame on a later pass (T48 F80 and T55 F10 are fixed frames), marks them `bounds_inferred: true` and logs it in `docs/BACKEND_GAPS.md`. |
| 6 | Track 55 vs 156 dates are in the manifest | Confirmed and worse: **T156 does not cover the delta at all** (`DATA_ACQUISITION_PLAN.md` §1). The delta pair is T55 F10: 16 Oct, 28 Oct, 9 Nov (+ 4 Oct baseline). The mockup still says "23 Oct → 4 Nov (T156)". | Manifest uses T55 dates. No date or track is hard-coded in JS or HTML. Mockup copy that cites T156 is replaced by manifest-driven text. |
| 7 | Mockup layers/numbers are real | Every number in the mockup is a **sample value**. Real NISAR subsets, flood classes, mandal stats, profile and SACHET snapshot **do not exist** (all NISAR GeoTIFF fetches are `blocked_credentials`; no `~/.netrc`; no SACHET script in `src/fetch/`). | Sample JSON + visible "Sample values" tag. Full list in `docs/BACKEND_GAPS.md`. |
| 8 | Mandals: "All 14 mandals" (mockup) | `mandals_delta.geojson` has **146** polygons (the clip box reaches beyond the three districts). Boundary vintage is geoBoundaries 2018 (pre-2022 districts); districts come from `mandal_district_2022.csv` (Wikipedia-sourced, some spelling differences like "Alamuru"/"Alumuru"). | Region picker filters by district via that CSV. A2 reports how many mandals map to each district and any unmapped ones. "All N mandals" uses the real count. |
| 9 | Landfall time | IMD's own texts disagree (advisory 13: 21–23 h IST *or* UTC; hourly bulletin: 02–04 IST; final statement: 02–08 IST 28 Oct, near 16.45 N 81.90 E). `DATA_ACQUISITION_PLAN.md` says "~01:30 IST". | `landfall.time_utc = null` in the manifest; the UI shows "time being confirmed (IMD)". Position (lat/lon) is shown. |
| 10 | Existing `app/` is a Leaflet viewer (tag `v0.1-pre-event`) | Confirmed: 4.6 KB `index.html` + 69 KB `scenes.js`, Delhi AOI, dark theme, date slider, no manifest. | **Replace, do not reuse** (decision in §1). |
| 11 | Repo state | `git status`: `.gitignore` modified and `data/{browse,interim,logs,processed,reference}`, `data/sources.yaml`, `docs/CROP_CALENDAR_NOTES.md` are **untracked**. Remote `origin` = `Guneesh922/spacebros-nisar`. | Nothing is committed or pushed by this plan. Committing the data and enabling GitHub Pages are manual steps for the owner (§8). |
| 12 | Alerts file named `data/alerts.json` (your brief) vs `alerts_snapshot.json` (handoff doc 10) | Two names in two documents. | I use **`data/processed/alerts.json`** and document it; backend can symlink/copy. |
| 13 | "Latest available date for each layer" on the landing view | The newest NISAR scenes we have are **8 Nov (T48 sea) and 9 Nov (T55 coast)**. Nothing newer will exist unless the backend re-runs. GIBS layers can show yesterday; NISAR cannot. | Landing shows each layer's own latest date, with its age ("5 days ago"). That is honest and generic. See open question Q2. |

---

## 1. Decisions

1. **Replace `app/`.** The old viewer is Delhi-only, dark-themed, has no manifest, no layer metadata and no captions. The only reusable ideas (image overlay with bounds, opacity slider) are ten lines. The old files move to `app/legacy/` untouched (tag `v0.1-pre-event` already preserves them); nothing links to them.
2. **Site layout** (served from the repo root, so `python3 -m http.server` at the repo root gives `http://localhost:8000/app/`):

```
app/
  index.html                 shell: header, tabs, alerts strip, panels, map, drawer, brief mount
  css/tokens.css             design tokens (colours, fonts, spacing)  ← only place hex values live
  css/app.css                shell + panels
  css/layers.css             drawer / sheet
  css/events.css             events panel
  css/brief.css              A4 print brief (@media print)
  css/case.css               case-study tab
  css/responsive.css         phone overrides that are not owned by one component
  strings/strings.en.json    ALL user-visible text (+ strings.te.json later)
  js/core.js                 App namespace: state, events bus, manifest loader, t(), fetch-with-fallback, formatters
  js/map.js                  Leaflet map, overlay manager, opacity, caption card, scale
  js/panels.js               header controls (region, date), alerts strip, ranking card, selected-mandal card
  js/layers.js               layer drawer / bottom sheet
  js/live.js                 live layers: GIBS WMTS, Open-Meteo marine + flood, GDACS
  js/compare.js              swipe between two layers/dates, class toggles, L/S toggle
  js/events.js               events panel (GDACS + saved events)
  js/brief.js                A4 brief generator
  js/case.js                 case-study tab (Scrollama) + radial chart
  legacy/                    old viewer, untouched
data/processed/              ← backend-owned. The page reads ONLY from here
  manifest.json              schema v2 (§3)
  alerts.json  mandal_rank.json  profile.json  imd_track_arnab.geojson  mandals.geojson
  img/*.png|jpg              web-ready map images (≤ 600 KB each)
tools/make_web_assets.py     one-off: raw/browse → data/processed (A2)
docs/FRONTEND_BUILD_PLAN.md  this file
docs/PLACEHOLDERS.md         every placeholder → real file that replaces it
docs/BACKEND_GAPS.md         everything the backend still owes
```

3. **Libraries (CDN, pinned, no build step):** Leaflet 1.9.4, a Leaflet swipe plugin (`leaflet-side-by-side` 2.2.0), Chart.js 4.4.x, Scrollama 3.2.x (case study only, lazy-loaded). Each `<script>` loads from cdnjs/jsDelivr with an exact version. If a CDN script fails the page shows a clear banner instead of a blank screen. (Fonts: Anek Latin, Anek Telugu, IBM Plex Mono from Google Fonts, as in the mockup.)
4. **Plain script tags + one global `App` namespace**, no ES-module bundling, so `file://`-free local serving and GitHub Pages behave identically. Module contracts are fixed in §4 so parallel agents never need to read each other's code.
5. **Generic vocabulary.** UI strings say "event", "selected period", "normal period". The word "Arnab" and "Narsapur" appear only (a) in manifest/event data, (b) inside the Case study tab. A CI-style grep (check C1 in §6) enforces this on `index.html` and `strings.en.json` shell keys.
6. **Landing view = "now".** Region `ap_coast`, latest date per layer, no event loaded, no chapter bar, no hero headline. The default analysis for the ranking card is the latest before/after pair for the region, labelled with dates only ("16 Oct → 9 Nov vs 4–16 Oct normal period"), never with the event name (see Q3).
7. **NISAR stays first and visibly the core**: NISAR group is first in the drawer; every NISAR layer carries the teal "NISAR L-band" chip; context sources are grey and off by default.

## 2. Design system (binding; taken from `10_UI_DIRECTION_AND_RISKS.md` §5 and verified against `mockup-src/`)

| Token | Value | Use |
|---|---|---|
| ink / ink-2 / muted | #131E22 / #3F4D53 / #586469 | text |
| paper / quiet fill / line | #F1F4F3 / #E6EBEA / #D3DAD8 | page, fills, borders |
| card | #FFFFFF | cards, header, drawer |
| map stage | #0F1B1F | map area, behind radar |
| NISAR teal | #17635F (hover #0E4542, tint #D8EAE7, on-map #5FD0C3) | brand + NISAR only |
| likely new open water | #2A6FB0 | that class only |
| likely wet or flooded crops | #E09A2B | that class only |
| likely no change | outline only | |
| Fonts | Anek Latin (UI/headings, headings `font-stretch:88%`, 600), Anek Telugu (Telugu), IBM Plex Mono (numbers, dates, scene ids only) | |
| Sizes | body 16 px desktop / 15 px phone; nothing under 13 px except mono metadata + chips (12 px) | |
| Touch | ≥ 44 px targets everywhere; contrast ≥ 4.5:1 | |
| Radar | greyscale (VV sea, HH land, dB) on the dark stage; never the magenta quick-look colours | |

Components to reproduce exactly (source file in `docs/handoff/mockup-src/`): header (Main), alerts strip (Main), mandal ranking card with stacked bar + ± whisker + normal-period tick (Main), caption card Shows / Can't show / Source (Main), Layers button + zoom (Main), layer drawer ON NOW / grouped rows / Coming next (Layers, LayersMobile), compare swipe + class legend toggles + L/S toggle + selected-mandal card (Shore), radial profile chart + ring (Rough), A4 brief (Brief), phone variants (`*Mobile`).

**Changes from the mockup (binding, from your brief):** header becomes logo + name | region picker | date/range control | Workspace · Events · Case study tabs | language toggle | About and data | Download brief. Header sub-line "Godavari coast · Cyclone Arnab" is dropped. Hero headline, "Scroll to begin", the 7-segment chapter rail and the story column are removed from the main screen; the left column becomes the ranking + selected-mandal panel. Chapters 1–5 + About move into the Case study tab. Layer groups: by source type (NISAR first); BEFORE / DURING / AFTER only while an event is loaded.

## 3. manifest.json schema v2 (backward-compatible with v1)

v1 layer fields are kept with the same meaning: `id, group (before|during|after|next), name, chip (nisar|context|model|reference), date, shows, source, credit, limit, png, bounds, default_on`. A v1 file with only those fields still loads (missing v2 fields get defaults).

```jsonc
{
  "schema_version": 2,
  "generated_utc": "2026-11-14T06:00:00Z",         // shown as "data last updated"
  "app": { "default_region": "ap_coast", "default_lang": "en", "page_budget_mb": 15 },

  "regions": [{
    "id": "ap_coast", "name": "Andhra Pradesh coast", "default": true,
    "bounds": [[15.0,80.8],[18.0,85.0]],           // [[S,W],[N,E]] as Leaflet wants
    "districts": null,                             // null = all
    "children": ["konaseema","west_godavari","kakinada"]
  },{
    "id": "konaseema", "name": "Konaseema", "parent": "ap_coast",
    "bounds": [[16.2,81.6],[17.1,82.6]],
    "districts": ["Dr. B.R. Ambedkar Konaseema"]   // matched to mandal_district_2022.csv
  }],

  "sources": [{                                    // the registry (one entry per provider)
    "id": "asf_nisar_l", "provider": "NASA/JPL-Caltech and ISRO via ASF DAAC",
    "access": "pipeline",                          // live | snapshot | pipeline | link
    "licence": "…", "credit_line": "…",            // credit_line is what every caption shows
    "can_host": true, "delay_hint": "1–3 days after pass", "url": "https://…"
  }],

  "layers": [{
    "id": "nisar_l_coast_20261109_t55_hh",
    "group": "after",                              // v1: before|during|after|next (only used when an event is loaded)
    "type": "nisar",                               // NEW: nisar | derived | optical | weather | reference | alerts  (drawer grouping)
    "chip": "nisar",
    "name": "Coast, HH backscatter",
    "kind": "image",                               // image | wmts | geojson | live | link
    "date": "2026-11-09", "time_utc": "2026-11-09T00:01:07Z",
    "latest_of": "nisar_l_coast_hh",               // NEW: layers sharing this key form a time series; the newest is "latest"
    "shows": "Land backscatter: radar brightness, HH (γ⁰, dB)",
    "limit": "…",                                  // text after "Can't show:"
    "source_id": "asf_nisar_l", "credit": "…",     // credit overrides source credit_line if present
    "png": "data/processed/img/nisar_l_coast_20261109_t55_hh.png",
    "bounds": [[15.29,80.53],[18.34,83.77]], "bounds_inferred": false,
    "url_template": null,                          // wmts/live only, {z}/{x}/{y}/{time}
    "band": "L", "pol": "HH", "track": 55, "frame": 10, "direction": "ascending",
    "regions": ["ap_coast"],                       // where it is offered
    "event_id": null,                              // set => only listed when that event is loaded
    "classes": null,                               // class layers only: [{id,label,colour,default_on}]
    "default_on": true, "opacity": 0.85,
    "status": "ready",                             // ready | coming_next | link_only | unavailable
    "placeholder": { "is": true, "tag": "Sample values", "replaced_by": "data/processed/img/….png" }
  }],

  "events": [{
    "id": "arnab_2026", "name": "Cyclone Arnab", "hazard": "cyclone_flood", "gdacs_id": null,
    "region": "konaseema",                         // region to fly to
    "dates": { "before": "2026-10-16", "during": "2026-10-28", "after": "2026-11-09",
               "normal_period": ["2026-10-04","2026-10-16"] },
    "layers": { "before": ["…"], "during": ["…"], "after": ["…"] },
    "default_on": ["…NISAR layer ids first…"],
    "analysis_id": "ap_delta_oct_nov_2026",
    "track_geojson": "data/processed/imd_track_arnab.geojson",
    "landfall": { "lat": 16.45, "lon": 81.90, "time_utc": null, "note": "time being confirmed (IMD)" },
    "case_study": true
  }],

  "analyses": [{                                   // before/after analysis the ranking card reads
    "id": "ap_delta_oct_nov_2026", "region": "ap_coast",
    "period": ["2026-10-16","2026-11-09"], "normal_period": ["2026-10-04","2026-10-16"],
    "rank_file": "data/processed/mandal_rank.json",
    "class_layers": ["…"], "placeholder": { "is": true, "tag": "Sample values", "replaced_by": "…" }
  }],

  "files": { "mandals": "data/processed/mandals.geojson", "alerts": "data/processed/alerts.json",
             "profile": "data/processed/profile.json" },

  "coming_next": [{ "id": "quake", "name": "Earthquake and landslide" }, { "id": "oil", "name": "Oil spill" }, { "id": "fire", "name": "Wildfire" }]
}
```

Companion files (shapes from handoff doc 10 §4, extended only with optional fields):

- `mandal_rank.json`: `{analysis_id, period, normal_period, placeholder?, rows:[{mandal, district, water_pct, water_err, crops_pct, crops_err, normal_pct, rank}]}` (a bare v1 array is also accepted).
- `profile.json`: `{eye:[lat,lon], eye_radius_km, eye_radius_err, imd_offset_km, points:[{r_km, db, err}], layer_id}`.
- `alerts.json`: `{saved_at_ist, sachet:[{headline, area, issued}], gdacs:[…]}`; the strip always prints `saved_at_ist`.
- `mandals.geojson`: simplified polygons, properties `{name, district}` (A2 builds from `data/reference/mandals_delta.geojson` + `mandal_district_2022.csv`).

Rules the code enforces from the manifest: every caption shows `credit`/`credit_line`; any layer or analysis with `placeholder.is` shows a visible tag; class labels are rendered as `"likely " + label` by code if the label does not already start with "likely"; unknown `status` is treated as `unavailable`.

**Adding an event, region, layer or hazard = edit `manifest.json` only** (plus dropping the image/JSON files it points to). This is verified by check C7.

## 4. Module contracts (so parallel agents never read each other's code)

`js/core.js` is written first (Batch 1) and defines:

```js
window.App = {
  manifest,                       // parsed manifest after load, defaults applied
  state: { region, view /* 'workspace'|'events'|'case' */, eventId, date /* ISO or null=latest */,
           range /* [from,to] or null */, layersOn /* Set of ids */, opacity /* {id:0..1} */,
           band /* 'L'|'S' */, compare /* {on,a,b} */, classesOn /* Set */, mandal /* name|null */, lang },
  on(evt, fn), off(evt, fn), emit(evt, payload),   // events: 'state', 'manifest', 'region', 'event', 'layers', 'mandal', 'compare', 'view'
  setState(patch),                // merges, emits 'state' + specific events
  t(key, vars),                   // string lookup from strings/strings.en.json; missing key → "⟨key⟩" and console.warn
  fetchJSON(url, {fallbackLabel}),// resolves {ok, data, error, fetchedAt}; never throws
  fmt: { date(iso), dateTime(iso, tz), ageDays(iso), pct(n), pm(n) },
  latestFor(layerKey), layerById(id), layersFor({region, eventId}), eventById(id), regionById(id)
};
```

Each later module is `App.<name> = { init(rootEl) }` and talks to the others only through `App.state`/events. File ownership means **no two agents ever edit the same file**.

## 5. Tasks, owners and batches

All coding by **Sonnet subagents** (`Agent` with `model: "sonnet"`). Each brief contains: files it owns (and "touch nothing else"), the schema (§3), contracts (§4), tokens (§2), the specific mockup source files to read, the global rules (§7) and a definition of done with commands to run. Independent tasks in a batch run in parallel. After each batch: I review diffs, serve with `python3 -m http.server` from the repo root, and check at **1440 px and 390 px** in the browser pane (console clean, no horizontal scroll at 390, page weight) before the next batch.

### Batch 1: data contract + assets + core (Sat, by ~16:00 IST)

| Task | Owns (exclusive) | Reads | Done when |
|---|---|---|---|
| **A1 manifest + samples** | `data/processed/manifest.json`, `mandal_rank.json`, `profile.json`, `alerts.json`, `docs/MANIFEST_SCHEMA.md`, `docs/PLACEHOLDERS.md` | §3, `data/reference/scene_manifest.csv`, `imd_track_arnab.csv`, `mandal_district_2022.csv`, `docs/handoff/mockup-src/Layers*.html` (layer list), `gibs_layers.json` | JSON validates against the schema checker (A1 writes `tools/check_manifest.py`); has: 4 regions, ≥ 14 layers across all `type`s, 1 event (Arnab) with before/during/after, 1 analysis, 3 coming-next; every sample is flagged `placeholder`; PLACEHOLDERS.md lists every placeholder → replacing file |
| **A2 web assets** | `tools/make_web_assets.py`, `data/processed/img/*`, `data/processed/mandals.geojson`, `data/processed/imd_track_arnab.geojson`, `docs/WEB_ASSETS_LOG.md` | `data/browse/nisar_arnab/*.png|kml`, `data/raw/gibs/*`, `data/reference/*` | each image ≤ 600 KB, greyscale for radar, cropped to AOI, ≤ 1400 px; bounds JSON per image (KML where it exists; inferred + flagged where not); mandals.geojson ≤ 400 KB simplified with district joined; log reports unmapped mandals and total `data/processed` size (< 8 MB) |
| **A3 core + tokens** | `app/js/core.js`, `app/css/tokens.css`, `app/strings/strings.en.json`, `app/legacy/*` (move of old files) | §2, §4, `mockup-src/Main.dc.html` | `App` contract implemented; `t()`, `fetchJSON()` fallback behaviour unit-checked with a tiny `app/js/core.test.html` (assertions print PASS/FAIL); strings file has every string used in the mockup, generic wording |

A2 needs Pillow (system Python lacks it): agent creates a venv in the scratchpad and `pip install pillow numpy`; no changes to the repo's `.venv`.

### Batch 2: workspace shell (Sat, by 23:00 gate)

| Task | Owns | Done when |
|---|---|---|
| **B1 shell** | `app/index.html`, `app/css/app.css`, `app/css/responsive.css` (shell part) | header (logo, region select, date control, tabs, language toggle with "soon", About and data, Download brief), alerts strip mount, 38/62 grid, map mount, layers button; no event name anywhere; keyboard-navigable; 44 px targets |
| **B2 map** | `app/js/map.js` | Leaflet map fits the region; overlays from `App.layersFor`; per-layer opacity; scale bar; caption card (Shows / Can't show / Source, chip, credit, placeholder tag, "likely" rule); "unavailable + last-known time" state for failed layers |
| **B3 panels** | `app/js/panels.js` | region picker + date control wired to state; alerts strip reads `alerts.json` (SACHET snapshot time always visible) and fetches GDACS live with fallback text; ranking card renders stacked bar + ± whisker + normal tick + legend + "Not a warning. Not a flooded area in km²."; selected-mandal card; mandal polygons highlight on map via event bus |

Interface risk: B1 provides empty mount ids (`#alerts`, `#left-panel`, `#map`, `#drawer`, `#brief-root`, `#tab-events`, `#tab-case`) that B2/B3 attach to; those ids are fixed in the briefs.

### Batch 3: layers, live data, compare (Sun morning)

| Task | Owns | Done when |
|---|---|---|
| **C1 drawer** | `app/js/layers.js`, `app/css/layers.css` | grouped by source type with NISAR first; BEFORE/DURING/AFTER only when an event is loaded; "ON NOW" detail rows, one-line expandable others, "Coming next" greyed; chips; bottom sheet < 768 px |
| **C2 live layers** | `app/js/live.js` | GIBS WMTS (VIIRS true colour, IMERG) with date fallback (try today, then −1, −2 days), Open-Meteo marine + flood JSON → small readout card, GDACS list; every fetch has timeout, error → "unavailable" + last-known time (stored in `localStorage` guarded by try/catch) |
| **C3 compare** | `app/js/compare.js` | Compare/swipe between any two layers or dates (leaflet-side-by-side); class toggles in legend (likely new water / wet or flooded crops / likely no change outline); L/S toggle: **S disabled with a tooltip when no layer with `band:"S"` exists** |

### Batch 4: events, brief, analysis wiring (Sun, by 11:30 MVP)

| Task | Owns | Done when |
|---|---|---|
| **D1 events** | `app/js/events.js`, `app/css/events.css` | Events tab lists GDACS (live) + manifest events; choosing one sets region, dates, before/after layers, NISAR layers on by default, track and landfall marker (time "being confirmed" when null); "Back to workspace now" restores landing |
| **D2 brief** | `app/js/brief.js`, `app/css/brief.css` | A4 page (map crop via the current overlay + 3 numbers + neighbour ranking + "What this is / is not" + data lineage) built in DOM, `window.print()`; `@media print` hides app; Sample tag prints; works for any selected mandal |
| **D3 analysis wiring** | `app/js/analysis.js` | picks the analysis for the selected region and period (or the "no change analysis for this period" state), feeds ranking/classes; ranking for Konaseema/West Godavari/Kakinada filters by district |

### Batch 5: case study (Sun, by ~13:30)

| Task | Owns | Done when |
|---|---|---|
| **E1 case study** | `app/js/case.js`, `app/css/case.css` | tab holds the story: radar eye, calm vs storm swipe, how rough + radial chart (hover moves a ring; static 25/50/100 km fallback), what radar can't show (4 claims, 4 verdicts, 24 cm vs 9 cm slider), about; Scrollama lazy-loaded; copy kept in `strings.en.json` under `case.*` keys (E1 may add keys only in a new file `app/strings/case.en.json` to avoid editing A3's file) |

### Batch 6: phone, weight, accessibility, README (Sun, by 16:00 freeze)

| Task | Owns | Done when |
|---|---|---|
| **F1 phone + a11y** | `app/css/responsive.css` (final pass), a11y fixes via written change requests to the owning files (see below) | 390 px: text above map ≈ 40/60, drawer as bottom sheet, no horizontal scroll, 44 px targets; focus rings; `aria-*` on toggles; contrast check |
| **F2 docs + audit** | `README.md` section, `docs/ADDING_CONTENT.md`, `tools/audit_page.sh` | README section "Add an event, layer or region"; audit script prints total bytes of everything fetched on first load (target < 15 MB), greps for forbidden hard-codes (C1, C2) |

Cross-file fixes after a batch go to a **fixer agent given the single file** (never two agents on one file at once).

## 6. How each part is checked (every batch, by me, in the browser pane)

| # | Check | How |
|---|---|---|
| C1 | No event wording on the landing view | load `/app/`; `get_page_text` must contain no "Arnab", "Narsapur", "cyclone" outside the Events/Case tabs; grep shell files |
| C2 | No hard-coded dates/tracks/landfall | grep `app/js app/index.html` for `2026-`, `T55`, `T156`, `landfall`; only manifest-sourced |
| C3 | Manifest drives everything | edit a copy of manifest (rename a layer, add an event) → UI changes without code edits |
| C4 | Graceful failure | block `gibs.earthdata.nasa.gov`, `api.open-meteo.com`, `gdacs.org` (devtools/offline) → "unavailable" + last-known time, no console exceptions |
| C5 | Captions | every active layer's caption has Shows / Can't show / Source with a credit line; placeholder layers show the tag |
| C6 | "likely" + disclaimers | every class label starts with "likely"; "Not a warning. Not a flooded area in km²." next to mandal numbers |
| C7 | Add-content test | add a fake second event and region to a manifest copy, reload: appears in picker/Events, loads layers |
| C8 | Layout | screenshot at 1440 and 390; no horizontal scroll at 390; targets ≥ 44 px (script measures buttons) |
| C9 | Weight | sum of transferred bytes on first load < 15 MB (`read_network_requests`), `du -sh data/processed` < 8 MB |
| C10 | Brief | print preview of one mandal = one A4 page, includes Sample tag and credit lines |
| C11 | Strings | grep for visible English text in `.js`/`.html` outside `strings/` (allow-list for tag names) |
| C12 | Console | zero errors/warnings except the documented CDN/font ones |

## 7. Global rules every brief repeats

1. Plain HTML/CSS/JS, no build step, no frameworks. Own files only.
2. Every class label begins "likely"; "Not a warning. Not a flooded area in km²." beside mandal numbers; every caption has its credit line.
3. All UI strings via `App.t(key)`; buttons/cards use padding, never fixed widths (Telugu ≈ 30% longer).
4. Live sources fail soft: "unavailable" + last-known time. Link-out sources (MOSDAC, INCOIS, IMD PDFs) are links only, never re-hosted.
5. One colour, one meaning (teal = NISAR/brand, blue/amber = the two classes only).
6. Placeholder data must show a visible tag and be listed in `docs/PLACEHOLDERS.md`.
7. Never write code that hard-codes landfall time, track numbers or dates.

## 8. Manual steps only the owner can do

- Commit and push (many files are untracked), enable **GitHub Pages** on `Guneesh922/spacebros-nisar` (branch `main`, root). Expected URL if enabled: `https://guneesh922.github.io/spacebros-nisar/app/` (**unverified**; I did not check that Pages is on).
- Earthdata login (`~/.netrc`) and Bhoonidhi registration for the backend person; see `docs/BACKEND_GAPS.md`.

## 9. Open questions (my default in bold; I will proceed with it unless told otherwise)

- **Q1.** Are the real `PROJECT_CONTEXT.md` / `UI_MOCKUP_SPEC.md` somewhere I can read? **Default: build from the mockup source + docs listed in §0.**
- **Q2.** Landing date: NISAR layers can't be newer than 9 Nov. **Default: each layer shows its own latest date and its age.**
- **Q3.** Landing ranking: with no event loaded, show the latest before/after analysis for the region, labelled by dates only. **Default: yes.** Alternative: hide ranking until an event/period with an analysis is chosen (cleaner "daily tool" story, emptier first screen).
- **Q4.** Replace T156 with T55 9 Nov (+12 days) in all copy. **Default: yes, per `DATA_ACQUISITION_PLAN.md` H4.**
- **Q5.** Telugu: toggle shows "soon", strings file ready. **Default: English only.**
