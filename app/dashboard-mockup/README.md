# Dashboard mockup: one page, two sections, one map

Mockup only. It does not touch `app/` (it reuses `app/css/tokens.css`, read-only).

## Run
From the repo root: `python3 -m http.server 8000`, then open http://localhost:8000/app/dashboard-mockup/ (add `#data` for the second section). Needs internet for Leaflet, fonts and the dark basemap (same CDNs as the main app).

## What it is
- Tabs: **What happened** (plain words, one finding per card, graphics, confidence, "what radar cannot tell you") and **Data for officials and researchers** (layer list, sortable mandal table with units and ±, eye profile chart, scene catalogue, alerts snapshot, downloads).
- One shared Leaflet map. "What happened" has four map modes (flood share, radar after, before/after swipe, cyclone eye). The data section ticks layers individually. Hovering the eye profile draws that radius on the map.
- Hide/Show panel button; the data section widens the panel.

## Real vs sample
- Real: layer list, sources, licences, scene catalogue, mandal outlines, IMD track, radar quick-looks (tagged "Quick-look sample").
- Sample (tagged "Sample values" on screen, as in the app): `mandal_rank.json`, `profile.json`, `alerts.json`. All finding sentences are computed from these, so every number is a placeholder until the real files land (`docs/PLACEHOLDERS.md`).
- The "what radar cannot tell you" verdicts carry the "Draft: to be reviewed" tag.

## Findings text
All plain-language copy is in `js/findings.js` as one `FINDINGS` object (`{placeholders}` are filled from the data; optional per-mandal overrides in `FINDINGS.mandals`). Swap that file for a backend-generated one.

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

