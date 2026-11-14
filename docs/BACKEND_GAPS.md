# Backend gaps: everything the frontend needs that is NOT in the repo yet

Written Sat 14 Nov 2026 while planning the frontend (`docs/FRONTEND_BUILD_PLAN.md`). Checked against the real files, not against what the plan documents say should exist.
The frontend ships with **sample placeholders** for everything in sections 1 to 5 and reads only from `data/processed/`. Replace the files named in the "Replaced by" column and the page updates, with no code changes. (`docs/PLACEHOLDERS.md` will list each placeholder id once the manifest is built.)

Legend: **BLOCKED** needs a login or a human decision · **TODO** no login needed, just not done · **PARTIAL** exists but not usable as-is.

## 0. Why `data/processed/` matters

`data/processed/` is empty today. `data/raw/` is git-ignored, so nothing in it (not even the 13 MB of GIBS PNGs that were fetched) can be served by GitHub Pages. Everything the page uses must be exported into `data/processed/` (web-ready, tracked). Page budget: whole first load < 15 MB; each map image ≤ 600 KB.

## 1. NISAR L-band products (the core) · all BLOCKED on Earthdata login

No `~/.netrc` exists on this machine. Every row of `data/sources.yaml` with `group: nisar_l` is `blocked_credentials`; `data/raw/nisar_l/{sea,coast}/` hold only `.gitkeep`. Command once logged in: `python src/fetch/subset_arnab.py --ids <ID>` (streams the box, never downloads whole files).

| Needed | Source id | Date (UTC) | Status | Frontend placeholder until then | Replaced by (file the page will load) |
|---|---|---|---|---|---|
| Calm sea reference (VV) | L_SEA_CALM_1015 | 15 Oct 13:01 | BLOCKED | greyscale quick-look crop (`data/browse/nisar_arnab/2026-10-15T1301Z_T48_F80.png`) | `data/processed/img/nisar_l_sea_20261015_t48_vv.png` |
| **Eye pass** (VV) | L_SEA_EYE_1027 | 27 Oct 13:01 | BLOCKED | quick-look crop (27 Oct, `_UR` and non-UR both present) | `…/nisar_l_sea_20261027_t48_vv.png` |
| Sea after storm (stretch) | L_SEA_AFTER_1108 | 8 Nov 13:01 | BLOCKED | quick-look crop | `…/nisar_l_sea_20261108_t48_vv.png` |
| Extra calm sea (stretch, quad-pol 7.5 GB) | L_SEA_CALM_1003 | 3 Oct | BLOCKED | quick-look crop | `…/nisar_l_sea_20261003_t48_vv.png` |
| Normal-period start (coast) | L_COAST_1004 | 4 Oct 00:01 | BLOCKED | quick-look crop | `…/nisar_l_coast_20261004_t55_hh.png` |
| Coast before (HH, HV) | L_COAST_1016 | 16 Oct 00:01 | BLOCKED | quick-look crop | `…/nisar_l_coast_20261016_t55_hh.png` |
| Coast +4 h (HH, HV) | L_COAST_1028 | 28 Oct 00:01 | BLOCKED | quick-look crop | `…/nisar_l_coast_20261028_t55_hh.png` |
| Coast +12 d (HH, HV) | L_COAST_1109 | 9 Nov 00:01 | BLOCKED | quick-look crop | `…/nisar_l_coast_20261109_t55_hh.png` |
| T149 side view (optional) | L_COAST_T149_* | 10 Oct, 22 Oct, 3 Nov | BLOCKED, P2 | skipped (covers only ~32% of the delta box) | n/a |

Notes the backend person must know:
- **Greyscale dB, not the quick-look colours.** Quick-looks are NISAR's magenta/green composite, 1.6 to 4.7 MB each. The page wants greyscale (VV for sea, HH for land) PNGs ≤ 600 KB, cropped to the area. Until real GeoTIFFs exist the frontend's asset script converts the quick-looks; those images are **display-only and tagged "Sample values / quick-look"**.
- **Bounds.** KMLs exist for 27 Oct, 28 Oct, 9 Nov, 8 Nov (and 3 Nov, 22 Oct T149). **No KML for the five provisional scenes (3, 4, 10, 15, 16 Oct)** because their `_LATLON.kml` URLs redirect to Earthdata login (`data/logs/package_D.md`). Those include both "before" scenes. The frontend infers bounds from the same track/frame on a later pass and marks `bounds_inferred: true`. The real GeoTIFF bounds replace this.
- **Provisional vs validated products:** scenes up to 16 Oct are `PROVISIONAL_V1`, from 22 Oct on `GCOV_V1` (validated). Captions must say so; the manifest has room for it, the data does not say more.
- **T156 does not cover the delta** (0 granules for the delta box). The flood pair is T55 F10: 16 Oct, 28 Oct, 9 Nov. Any copy that says "23 Oct → 4 Nov" is obsolete.
- Delta box coverage by T55 F10 is only 79 to 83%; the rest is NaN by design. T48 DVDV covers the delta for the sea scenes at 92 to 98%.

## 2. NISAR-derived products · all TODO (blocked by section 1)

| Product | What the page expects | Placeholder | Replaced by |
|---|---|---|---|
| Sea difference map (storm minus calm, dB) | PNG + bounds | none yet; sample image drawn from quick-look difference is NOT computed (not scientifically meaningful on colour composites) | `data/processed/img/nisar_sea_diff_20261027_vs_20261015.png` |
| Class maps: **likely new open water**, **likely wet or flooded crops**, likely no change (outline) | 8-bit palette PNG per class or one paletted PNG + `classes` in manifest; bounds | sample blocky mask clearly tagged "Sample values" | `data/processed/img/class_<date>_<class>.png` |
| **Mandal statistics** with ± uncertainty and a normal-period baseline | `mandal_rank.json` (shape in `docs/FRONTEND_BUILD_PLAN.md` §3): `mandal, district, water_pct, water_err, crops_pct, crops_err, normal_pct, rank` | invented numbers for the mockup's five mandals plus filler, tagged "Sample values" | `data/processed/mandal_rank.json` (owner: backend, due Sun 09:00 per R4) |
| **Eye + radial profile** | `profile.json`: eye lat/lon, eye radius ± km, offset to IMD fix, `points:[{r_km, db, err}]` | smooth made-up curve, tagged | `data/processed/profile.json` |
| Normal-fortnight baseline (4 to 16 Oct) | feeds `normal_pct` in the ranking | n/a | part of `mandal_rank.json` |
| Flooded-area km² | **Not built on purpose.** The UI says "Not a flooded area in km²." | n/a | n/a |

## 3. NISAR S-band (ISRO) · BLOCKED on Bhoonidhi login and on whether a scene exists

- No Bhoonidhi registration/credentials; `data/raw/nisar_s/` empty; `data/reference/nisar_s_candidates.csv` (named in `sources.yaml` S_GCOV_DELTA) **does not exist**.
- It is **not verified that any S-band scene covers 81.6 to 82.6 E, 16.2 to 17.1 N between 16 Oct and 10 Nov**. CMR check found no S-band collections (Bhoonidhi only).
- Frontend behaviour: the L/S toggle is **disabled** unless a layer with `band: "S"` exists in the manifest. No placeholder S-band layer is shipped.
- The case-study "24 cm vs 9 cm waves" slider needs either real S-band or an illustrative diagram: **missing asset**.

## 4. Alerts · SACHET and GDACS

| Item | State | Needed |
|---|---|---|
| **SACHET snapshot** (`data/processed/alerts.json`, with `saved_at_ist`) | **TODO.** No fetch script exists in `src/fetch/`, no entry in `sources.yaml`. The feed blocks browser (CORS) access. | A script (cron/GitHub Action or manual) that saves the feed into the JSON shape in the plan and records `saved_at_ist`. Feed URL and format to be confirmed by the backend person (the plan only says "RSS, no key"; I did not verify an endpoint). |
| GDACS live | Frontend fetches from the browser. **Not yet tested from github.io in Chrome/Safari** (risk R1). | Test after Pages is on; if it fails, the alerts strip shows the snapshot only. |
| Placeholder shipped | headline strings in `[brackets]`, snapshot time visible | real `alerts.json` |

## 5. Live sources the frontend calls directly (no backend file, but details are undecided)

| Source | State | Decision needed from the backend person |
|---|---|---|
| NASA GIBS WMTS (VIIRS true colour, IMERG, Himawari) | `data/reference/gibs_layers.json` has the 10 layers, formats and time ranges. | None. Note: `Reference_Labels_15m` returns an empty PNG (`GIBS_REF` = failed): no GIBS place labels; use OSM labels. Himawari B13 is a rolling window (older dates vanish): the saved 27 Oct stills in `data/raw/gibs/` are the only reliable copy and must be exported to `data/processed/img/` to be usable. |
| VIIRS true colour 27 Oct **delta** box | PARTIAL: pixel std 3.2 to 3.4 (near-uniform, probably cloud). | A human to look at it and pick SNPP / NOAA-20 / NOAA-21 for 27 Oct (the log says "Human should pick visually"). |
| Open-Meteo Marine (waves) and Flood (GloFAS river discharge) | Not in `sources.yaml` (only ERA5 archive is). | **Which coordinates?** A sea point (e.g. off Narsapur) and a Godavari discharge point per region must be chosen; the frontend takes them from the manifest (`live` layer config). Placeholder: sea point 16.0 N 82.0 E, river point at Dowleswaram barrage, marked "to be confirmed". Credit: Open-Meteo, CC BY 4.0, non-commercial, < 10,000 calls/day. |

## 6. Reference geography · PARTIAL

| Item | State |
|---|---|
| Mandal boundaries | `data/reference/mandals_delta.geojson`: 146 polygons, 0.79 MB, geoBoundaries ADM3 **2018 vintage** (pre-2022 districts). Needs simplifying for the web; that is done by the frontend asset script into `data/processed/mandals.geojson`. |
| Mandal → district (2022) | `mandal_district_2022.csv` (Wikipedia-sourced, geoBoundaries vs official spellings differ, e.g. Alamuru/Alumuru). **Completeness not verified**; the asset script reports unmapped mandals. A government source (LGD directory) would be better. |
| District outlines | `districts_delta_gb2021.geojson` is the **pre-split 2021** layout (East Godavari/West Godavari); only for outlines. |
| Regions other than the delta | None. "AP coast" is a view over the same data; no other region has any layer. |

## 7. Cyclone event material · PARTIAL

| Item | State |
|---|---|
| IMD track | `data/reference/imd_track_arnab.csv` (15 fixes, each with source PDF + page). Frontend asset script converts to `imd_track_arnab.geojson`. |
| **Landfall time** | **Disputed** inside IMD's own texts (see `data/logs/package_B.md`: 21 to 23 h IST vs 02 to 04 vs 02 to 08 IST on 28 Oct; position 16.45 N 81.90 E is stable). The manifest holds `time_utc: null`; the UI says "time being confirmed (IMD)". A human must decide what to state. |
| INSAT-3DS / MOSDAC | **Link only** (their rules forbid redistribution). `data/raw/insat/` empty. Frontend shows a credited link. |
| IMD API | Not used (needs whitelisted IP). IMD bulletins: PDFs in `docs/imd_bulletins/` (16 files); linked, not re-hosted unless allowed. |
| INCOIS surge/wave services | No API key requested. Link only. |
| SCAT-3 (Oceansat-3) winds | `data/raw/scat3/` empty. Caption for calm-day wind uses ERA5 via Open-Meteo (`data/reference/era5_wind_summary.csv`) instead. |

## 8. Case-study assets · mostly TODO

| Item | State |
|---|---|
| Optical image + track (chapter 1) | VIIRS true colour exists in `data/raw/gibs/` (not exported); needs a human pick of the satellite (see §5). |
| "What radar can't show": four claims, four verdicts | Text is in `docs/handoff/06_PLAN_Eye_of_the_Storm.md` (§4); frontend drafts the strings, **content owner must review**. |
| 24 cm vs 9 cm slider | missing (see §3). |
| About: data, methods, limits, credits | frontend drafts from `sources.yaml` and plan §2; credit lines per source need checking against each licence (registry PDF `07_BACKEND_RESOURCE_REGISTRY.pdf` was not readable here). |
| Telugu strings | none; toggle shows "soon", structure ready (`strings.te.json`). |

## 9. Refresh pipeline (needed for a *daily* tool) · TODO

Nothing regenerates `manifest.json` from ASF or the live services. For the page to stay "now" after the hackathon someone must: (1) run `D_asf_manifest.py`-style search for new NISAR passes over each region, (2) subset and convert them to web PNGs, (3) append layers to `manifest.json`, (4) re-save `alerts.json`. The frontend only reads what is there. This is future work to state honestly in the submission.

## 10. Stretch items from the plan (not started, not needed by the frontend)

Aquaculture-pond toggle · mangrove (Coringa) change · INSAT eye beside radar eye · StormCard 1080×1350 export · S-band dual-frequency (see §3). They appear in the UI only as greyed "Coming next" entries if at all.

## 11. Files the frontend work will create (so nobody is surprised)

`data/processed/manifest.json`, `alerts.json`, `mandal_rank.json`, `profile.json`, `mandals.geojson`, `imd_track_arnab.geojson`, `img/*`, `tools/make_web_assets.py`, `tools/check_manifest.py`, `docs/MANIFEST_SCHEMA.md`, `docs/PLACEHOLDERS.md`, `docs/WEB_ASSETS_LOG.md`. The five sample files carry a `placeholder` flag; replace the file and set the flag false (or remove it).

## 12. Items outside the repo that this planning could not read

- `04_Project_Idea/07_BACKEND_RESOURCE_REGISTRY.pdf` and `08_EVIDENCE_PACK.pdf` (no PDF reader available here). Per-source licence and credit-line text should be copied from the registry into `manifest.json` `sources[]` by whoever can open it.
- `docs/handoff/PROJECT_CONTEXT.md`, `UI_MOCKUP_SPEC.md`, `mockup-png/`: named in the brief but absent everywhere on this machine.

## 13. Added during frontend review (Sat 14 Nov 2026)

Found while reviewing the built page. "Blocks" says what stays a sample or an open question until it is done. Nothing here is a frontend code task unless stated.

| # | Item | File or place the page expects | Who / state | Blocks |
|---|---|---|---|---|
| 1 | **Class-map PNGs** `class_*.png` (likely new open water, likely wet or flooded crops, likely no change) and the **sea difference PNG** | `data/processed/img/class_20261109_new_water.png`, `…_wet_crops.png`, `…_no_change.png`, `…/nisar_sea_diff_20261027_vs_20261015.png` | backend; all four layers are `status: unavailable` | Classes toggles in "Classes and band", ranking colours on the map, brief map |
| 2 | **Real `mandal_rank.json` and `profile.json`** (today: invented numbers, tagged "Sample values") | `data/processed/mandal_rank.json`, `data/processed/profile.json` | backend (due Sun 09:00) | Ranking card, mandal card, A4 brief, Case study chapter 3 (eye radius, +6.2 dB peak) |
| 3 | **Real `alerts.json` plus a SACHET snapshot script** (none in `src/fetch/`; feed endpoint unverified) | `data/processed/alerts.json` with `saved_at_ist` and `sachet[]` | backend; sample headline is now a generic bracketed placeholder | Alerts strip |
| 4 | **Greyscale dB PNGs** to replace the converted quick-looks (magenta/green composites converted to grey, display only) | `data/processed/img/nisar_l_*_t55_hh.png`, `…_t48_vv.png` (8 files) | backend, blocked on Earthdata login | Every NISAR layer shows "Quick-look sample". Bounds for 3, 4, 15 and 16 Oct are **inferred** (`bounds_inferred: true`); the 16 Oct and 15 Oct frames are the two "before" scenes, so compare and the Case study both rely on inferred positions. |
| 5 | **S-band scene** (Bhoonidhi) | a layer with `band: "S"` in the manifest | owner/backend; existence of a scene over the area is unverified | L/S toggle stays disabled ("S-band: no scene available") |
| 6 | **24 cm vs 9 cm wave illustration** in the Case study | the slider is drawn by `case.js` as an illustrative SVG diagram, not data | owner (confirm that a diagram is acceptable, or supply real S-band) | Case study chapter 5 slider; tagged as illustration |
| 7 | **GDACS from github.io (CORS)** unverified. The bare `…/geteventlist/MAP` endpoint answers HTTP 400 ("Eventtype is required"); the page now uses `…/geteventlist/SEARCH?eventlist=TC;FL&fromdate=…&todate=…&alertlevel=…` | `layers[alerts_gdacs_live].url_template` | owner after Pages is on | Live GDACS in the strip and Events tab (falls back to "unavailable" text) |
| 8 | **Open-Meteo marine and flood point coordinates unconfirmed** (16.0 N 82.0 E sea; 16.94 N 81.77 E river, `coordinates_confirmed:false`; both answer HTTP 200) | `layers[open_meteo_*].config` | backend | Waves and river readouts say "coordinates to be confirmed" |
| 9 | **Credit lines unconfirmed**: MOSDAC and OSM are `[credit line to confirm]`; others have `credit_confirmed: false`. The registry PDF `07_BACKEND_RESOURCE_REGISTRY.pdf` was never read | `manifest.json` `sources[]` | backend/owner | Captions, About dialog, brief lineage |
| 10 | **VIIRS satellite pick** for 27 Oct (NOAA-21 used; delta box near-uniform, probably cloud) needs a human look | `data/processed/img/gibs_viirs_noaa21_truecolor_2026-10-27_sea.jpg` | owner | Case study chapter "From above" |
| 11 | **Basemap and attribution**: Esri World Dark Gray Base tiles (`server.arcgisonline.com`) are used with the attribution "Tiles © Esri — Esri, HERE, Garmin, © OpenStreetMap contributors". Esri's terms for a public non-commercial site must be confirmed; CARTO basemaps now need an API key, so they are not an easy swap | `app/js/map.js` (`BASEMAP`) | owner | Public launch |
| 12 | **CDN dependencies, no offline use**: Leaflet 1.9.4 and Chart.js 4.4.1 (cdnjs), Scrollama 3.2.0 (jsDelivr, Case study only), Google Fonts (Anek Latin, Anek Telugu, IBM Plex Mono). leaflet-side-by-side is NOT used (own divider). The page shows a banner if Leaflet fails; the app does not work offline | `app/index.html`, `app/css/tokens.css`, `app/js/case.js` | owner (decide whether to vendor them into the repo) | Offline demos |
| 13 | **Mandal geography**: only 65 of 146 polygons carry a district (81 have none), so district filters and rank rows cover Konaseema, West Godavari and Kakinada only; East Godavari (20 mandals) and the other districts have no rank rows. Boundaries are the 2018 geoBoundaries vintage. The duplicate-name **Yelamanchili** case (two polygons, two districts) is not disambiguated | `data/processed/mandals.geojson`, `mandal_rank.json` | backend | "All N mandals" counts, any region beyond the three districts |
| 14 | **Telugu strings** | `app/strings/strings.te.json` (and `case.te.json`, `shell.te.json`) | owner/translator | Language toggle shows "soon" |
| 15 | **Landfall time decision** (`time_utc: null`, "time being confirmed (IMD)") | `manifest.json` event `landfall` | owner | Events tab and map marker tooltip; Case study intro copy |
| 16 | **Refresh pipeline**: nothing regenerates `manifest.json`, `alerts.json` or the images, so "latest" never advances past 9 Nov | n/a | backend | The "daily tool" claim; say so in the submission |
| 17 | **GitHub Pages and committed data**: Pages must be enabled, and `data/processed/` (4.0 MB, many files untracked) must be committed or the page loads with empty state | repo settings, `git add data/processed app docs` | owner | Anything public |
| 18 | **Case study copy needs expert review**: the science claims and the four "what radar can't show" verdicts were written without a source document. Each verdict now carries an on-screen tag "Draft: to be reviewed" | `app/strings/case.en.json` (`case.radar.*`, `case.rough.*`, `case.clouds.*`) | radar domain expert | Remove the tag (`case.tag.draft`) only after review |
| 19 | **Sea frame for the calm reference**: the Case study uses the sea layer of the event's `before` list closest in time before the eye pass (15 Oct). The 3 Oct frame is an average sea with partial coverage and is not used | `case.js` `pickLayers()` | frontend (done), backend to confirm 15 Oct bounds | Case study chapter 2 |
| 20 | **Quick-look PNGs ship 0.4 to 0.5 MB each** (eight in `data/processed/img`); first page load is about 1.8 MB, well under the 15 MB budget | n/a | none | none |
