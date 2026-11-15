# Dashboard mockup: one page, two sections, one map

This is the Pass by Pass dashboard. It uses `app/css/tokens.css`, `app/strings/` and `app/vendor/`.

## Run
From the repo root: `python3 -m http.server 8000`, then open http://localhost:8000/app/dashboard-mockup/ (add `#data` for the second section). Needs internet for Leaflet, fonts and the dark basemap (same CDNs as the main app).

## What it is
- Tabs: **What happened** (plain words, one finding per card, graphics, confidence, "what radar cannot tell you") and **Data for officials and researchers** (layer list, sortable mandal table with units and ±, eye profile chart, scene catalogue, alerts snapshot, downloads).
- One shared Leaflet map. "What happened" has four map modes (flood share, radar after, before/after swipe, cyclone eye). The data section ticks layers individually. Hovering the eye profile draws that radius on the map.
- Hide/Show panel button; the data section widens the panel.

## Real vs sample
- Real: layer list, sources, licences, scene catalogue, mandal outlines, IMD track, radar quick-looks (tagged "Quick-look sample").
- Sample badges now appear only where a layer, `mandal_rank.json` or `profile.json` carries `placeholder.is` (see the W3-H and WP3 sections below for what the page reads today). Older text in this section ("every number is a placeholder") describes the first mockup and is superseded.
- The "what radar cannot tell you" verdicts carry the "Draft: to be reviewed" tag.

## Findings text
All plain-language copy is in `js/findings.js` as one `FINDINGS` object (`{placeholders}` are filled from the data; optional per-mandal overrides in `FINDINGS.mandals`). It is now only generic explanatory copy and neutral fallbacks; the live summary comes from `data/processed/findings/latest.json` (see WP3).

## Needs from the backend
1. A findings JSON (same shape as `FINDINGS`), or per-mandal sentences and confidence levels.
2. Real `mandal_rank.json`, `profile.json`, `alerts.json`, and class rasters (the share map colours polygons, not pixels).
3. Confirmation that `normal_pct` is on the same basis as water + crops (assumed), and a confirmed landfall time.
4. Greyscale dB PNGs; true bounds for the 16 Oct scene (inferred today).

## Presentation
Header with title and subtitle, underline tabs, one card/badge system, "Sample values" style tags shown as small amber badges (never removed). If a radar overlay image is missing (data moving to HDF5), the map shows "Radar layer data not loaded yet", the layer tick box is disabled and nothing breaks. Browser consoles will still log the 404 for those images.

## Known limits
Desktop first, phone is a simple stack, English only. Swipe uses CSS clip and can lag during zoom animation.

## Dates, permalinks and saved days (W3-C)
The NISAR dates come from manifest layers (`type: nisar`, `status: ready`, with `date`, `png`, `bounds`); a new layer entry appears in the date selector on the map with no code change. The view (tab, mode, dates, mandal, map centre and zoom) is kept in the URL hash (`#tab=happened&mode=swipe&role=coast&d=...&b=...`; plain `#data` still works). The "This view" card offers Copy link, Save this day (localStorage, this browser only, by date and role, never by array position) and Download this day (PNG, H5 of record, JSON).

## Live story, archive and pro tab (W3-H phase 2)
- "What happened" is rendered from `data/web/story.json` (built by `tools/build_story.py`). If that file is missing the page falls back to the text in `js/findings.js`. Fields used: state, headline, since_last, lead, confounders, class_summary, big_numbers, map, next_pass, timestamps, badges (+ provisional_text), mandal_sentences / mandals, updates[] (archive, each linked by `hash`), feed. Strings for stale/missing text come from `app/strings/story.en.json` (built-in English fallback).
- Badges: "Provisional data" from `badges.provisional`; "Sample values" only if `badges.sample` is true, or a layer / `mandal_rank.json` / `profile.json` carries `placeholder.is`. The wet-crops layer carries a "Weak signal" tag.
- To test a state without editing data: `window.__spacebros.setStory({...JSON.parse(JSON.stringify(window.__spacebros.story())), state: 'watch'})` in the console (null = built-in text).
- Mandal numbers: public tab = open water only (`rank_water`); data tab can rank by water or water + crops. `by_date` of `mandal_rank.json` feeds the sparklines and the flood-share day selector (hash `mode=share&d=YYYY-MM-DD`).
- Data tab cards added: Radar by date (small multiples), Brightness histogram (`hist` + `water_threshold_db` of each layer json); map legends come from the layers on the map (dB bar, sea-difference `ramp.stops`, class colours).
- Test viewports: 1400x900 and 800 wide, both tabs, all four map modes.


## WP3 (Wave 4): what reads what
Page start-up reads, all relative to the repo root (any failure of an optional file shows a neutral message, never invented text):
| file | used for |
|---|---|
| `data/processed/findings/latest.json` (fallback `data/web/story.json`, then the neutral "Summary not available yet") | the Latest radar pass card: pass time IST, area, headline, `comparison_line`, `three_numbers` with ±, `caveats`, `confidence` ("Lower confidence" + reasons), `next_pass`, `age`, `event_chips` (list) or `event_chip`, mandal sentences, archive list `updates[]`. The newest pass date is `pass.date`. |
| `data/processed/findings/<date>.json` | frozen summary of one coast pass. Opens when the map shows that date (flood-share day buttons, archive links, saved days, old hashes). Only dates listed in `updates[]` are fetched. "Back to the latest pass" returns. |
| `data/processed/events.json` | Events archive card (name, type, dates, source and credit, severity as given, status, linked passes with finding text, cannot-tell list, edit log). `reviewed_by_human: false` shows "Draft from alert, not reviewed". `story` supplies ALL Arnab-style wording (landfall caption, eye profile, wind, before/after, other-water caveat); slots `{eye} {eye_err} {peak} {before} {after}` are filled from `profile.json` and the scene dates, and a sentence whose slot cannot be filled is left out. This wording shows only with an event chip or in the archive. |
| `data/processed/alerts.json` (schema alerts-v2) | Alerts card (home) and Alerts card (data tab): GDACS and SACHET items, each with its own timestamp; `ok:false` shows "Could not refresh, showing snapshot from ...", `none_text` when both are empty, credits shown. |
| `config/areas.json` | `site.title` -> `document.title` and header title, `site.tagline` -> header subtitle, area name in the pass and alerts cards. `index.html` holds neutral defaults. |
| `app/strings/strings.en.json` (keys `dash.*`) | "How radar sees water" panel, Events archive intro and draft tag, "About and sources". |
| `app/strings/story.en.json` | read-only; stale/missing-number strings. |
| `data/h5/catalog.json`, `manifest.json`, `mandal_rank.json`, `profile.json`, `mandals.geojson`, `imd_track_arnab.geojson` | unchanged: scenes, layers, mandal numbers, eye profile, outlines, track. |
`js/findings.js` now holds only generic explanatory copy and neutral fallbacks (no event wording). `data/events/arnab-2026.json` is no longer read.

Side panel: "Close panel" (inside the panel) and "Hide panel" (on the map) both toggle it; `aria-expanded` is kept in step, focus moves to the map button, state is saved in localStorage (`spacebros.nisar.panelCollapsed.v1`, in try/catch) and the map is resized afterwards. Works at 390 px (panel sits under the map; collapsed, the map grows).

Permalinks: format unchanged (`#tab=..&mode=..&m=..&l=..&c=..&z=..&d=..`). A `c`/`z` that is outside the study area (with a margin) or at a zoom below 5 is ignored and the map fits the area bounds. The page no longer writes `c`/`z` while the map has no real size (hidden or not laid out).

## Name, credits and labels (15 Nov)

- Visible name: "Pass by Pass" (`config/areas.json` `site.title`; earlier "Coast Radar Watch", dropped because "Watch" can read as an official flood watch and clashes with NOAA CoastWatch). Header org line: "Team SpaceBros".
- Footer (in `index.html`, `#site-foot`) and the About intro (`app/strings/strings.en.json`, `dash.about.intro`): "Built by team SpaceBros for the NASA Space Apps Challenge 2026. Not an official NASA, ISRO, IMD or government product, and not a warning service."
- About and sources list: `dash.about.sN.name/what/url` in `app/strings/strings.en.json` (not in dash.js). Background-reading items are marked "not a data source".
- Credit string for NISAR layers: "NISAR L2 GCOV, NASA/JPL-Caltech and ISRO, via ASF DAAC (NASA Earthdata)" plus scene date, track, polarisation and PROVISIONAL/VALIDATED. `data/web/story.json` carries it in `credits` (`nisar`, `nisar_line`, `derived`, `imd`, `ndma_sachet`, `gdacs`, `boundaries`, `basemap`, `disclaimer`), written by `tools/build_story.py`.
- No NASA, ISRO or Space Apps logo, insignia or look-alike is used. The header mark (`.hdr__mark`) is the team's own two teal rings.

