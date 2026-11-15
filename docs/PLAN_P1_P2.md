# Plan P1 / P2 (research and planning only, 15 Nov 2026)

Nothing here is built. No existing file was edited. Only new items: this file, `data/external/gmw/` (3 small GMW tiles, section P2-B).
Builders are Sonnet agents. Effort = agent-hours (one agent working) and wall-clock (with parallel agents). Time assumption: code freeze Sun 15 Nov 16:00 IST, submission 20:00, about 14 h to submission, so about 10 h to freeze if "now" is about 06:00 IST. Re-check the clock before committing to the order in section 4.
"Verified" below = read in a file or fetched in this session. "Not verified" is said where it applies.

## 0. What the repo actually does today (read first, it changes the plan)

- The live site is `app/dashboard-mockup/` (`pages.yml` writes a root redirect to it). `app/js/brief.js` belongs to the OLD shell `app/index.html` (needs `window.App`, `core.js`, manifest regions and `strings.en.json` `brief.*` keys). The dashboard page loads only Leaflet, `findings.js`, `dash.js`. So **brief.js cannot be loaded as is**; reuse = port its pure geometry and row code, not import it.
- `dash.js` is one IIFE (`X` data, `S` state are private). Anything new needs a small hook added to `dash.js`.
- Existing pieces to reuse: `csv()` (line ~1596, ranked rows of the newest date only), `classId(date)` (line ~1252, gives the class PNG for ANY date by renaming `class_YYYYMMDD_`), `primaryDate()`, `shareDate()`, `X.rowsBy[date]`, `X.rank.by_date`, `buildDayCard()` / `bindDay()` (the "This view" card), `dlBlock()` (Downloads card, `#d-files`), hash state `toHash/parseHash`, saved days (`S.saved`, localStorage).
- Floods (P2-A) are already handled end to end: `alerts.py` keeps GDACS `FL`, `events.py` makes drafts from them, and **a flood draft already exists live**: `auto_GDACS_1104248` ("Flood in India", Green, linked to the delta passes). See P2-A for the problem with it.

---

## P1. "Official brief" download (Data tab)

### P1.1 Zip library decision

| lib | version checked | licence (source read) | min.js size (measured with curl, this session) | fits classic scripts |
|---|---|---|---|---|
| **fflate** | 0.8.2 (npm latest is 0.8.3, MIT per registry) | MIT. jsDelivr `fflate@0.8.2/LICENSE` and GitHub `101arrowz/fflate` LICENSE both "MIT License" (Arjun Barrett) | `umd/index.js` 32,665 B raw, 12,467 B gzip (already minified) | yes, UMD global `fflate` |
| JSZip | 3.10.1 (npm 3.10.2) | "MIT OR GPL-3.0-or-later"; `LICENSE.markdown`: "At your choice you may use it under the MIT license" (read on GitHub and jsDelivr) | `jszip.min.js` 97,630 B raw, 28,379 B gzip | yes |
| client-zip | 2.5.0 | npm registry says MIT. **LICENSE file not opened** (404 on the two paths tried), so not verified from the file | `index.js` 6,463 B raw, 2,668 B gzip | **ES module only**, needs `type=module`, no compression |
| zip.js | 2.7.62 (npm shows a newer 2.25.0) | npm registry says BSD-3-Clause; LICENSE file not opened | `dist/zip.min.js` 100,468 B | yes |

**Recommend fflate 0.8.2**: smallest checked MIT lib that compresses, classic-script global, `fflate.zipSync({ 'a.csv': fflate.strToU8(text) }, { level: 6 })` is enough for a bundle under 1 MB.
Vendor plan (new files, nothing existing touched except `index.html`):
- `app/vendor/fflate-0.8.2.min.js` = `https://cdn.jsdelivr.net/npm/fflate@0.8.2/umd/index.js` (32,665 B expected; builder records sha256).
- `app/vendor/fflate-0.8.2.LICENSE.txt` = MIT text from `https://cdn.jsdelivr.net/npm/fflate@0.8.2/LICENSE`.
- `app/vendor/VENDOR.txt`: name, version, URL, sha256, licence, date vendored.
- `pages.yml` already copies all of `app/` (`cp -r app _site/app`), so `app/vendor/` ships with no workflow change. Load with a local `<script src="../vendor/fflate-0.8.2.min.js">` (no CDN at runtime; the zip must work offline once the page is loaded).
- The vendored file is downloaded content: the builder must not execute it outside the browser; check the sha256 against a second fetch (jsDelivr and unpkg) before committing.

### P1.2 Map snapshot method

Observed: `server.arcgisonline.com/.../World_Dark_Gray_Base/tile/...` answers with `Access-Control-Allow-Origin: *` (curl HEAD, this session), so a canvas export is technically possible. Esri terms for exporting or printing tiles: **not verified for this service** (search found only: attribution required on printed maps, an older notice that offline caching is limited to Esri products; the Master Licence and the item's Terms of Use were not opened).

| option | verdict |
|---|---|
| Static PNG per mandal and date composed in Python at build time | Works, but 66 mandals x every pass, new pipeline step, new tests gating deploy, cannot cover a new pass until the pipeline reruns. Reject for time. Keep as fallback only. |
| html2canvas / dom-to-image on the Leaflet map | Leaflet CSS transforms and cross-origin tiles taint or mis-render; extra 40+ KB lib; fragile at 390 px. Reject. |
| leaflet-image | Needs CORS tiles and brings the Esri licence question. Not evaluated further. Reject. |
| **Canvas crop of the class PNG + inline SVG mandal outlines (no basemap)** | **Recommend.** Same-origin PNG (`data/web/class_YYYYMMDD_new_water.png` via `classId(date)`), so the canvas is not tainted. Crop to the mandal bbox + 30 % padding with `drawImage(img, sx, sy, sw, sh, 0, 0, w, h)`, `toDataURL('image/png')`, embed as an SVG `<image>`. Outlines from `mandals.geojson` drawn exactly like `brief.js buildMap()` (lon scaled by cos(lat), neighbours thin, selected mandal thick with halo). No Esri content in the file, no licence question, prints cleanly in black ink, self-contained. |

Output of the brief is a **self-contained HTML file** (inline CSS, inline SVG, data-URI crop): it can be downloaded, emailed, opened offline and printed. The button opens it in a new tab (Blob URL, `window.open` inside the click handler) and also puts it in the zip.

### P1.3 Files to touch

| file | change |
|---|---|
| `app/vendor/fflate-0.8.2.min.js`, `fflate-0.8.2.LICENSE.txt`, `VENDOR.txt` | NEW (above) |
| `app/dashboard-mockup/js/export.js` | NEW, classic script, `window.SpacebrosExport = { build(ctx) -> {briefHtml, files}, zip(ctx), openBrief(ctx) }`. About 350 lines: `COLUMNS` table (one source for CSV header and README text), `csvFor`, `geojsonFor`, `readme`, `cropPng`, `briefHtml` (ported from `brief.js`: `rings, bboxOf, pathD, findFeat, buildMap, nbRow, neighbourTable, lineGroup`; `T()` replaced by constants; inline CSS copied from `app/css/brief.css` rules, with the `@page { size: A4; margin: 0 }` and print block adapted to a standalone document), `download(blob, name)` via `URL.createObjectURL`. |
| `app/dashboard-mockup/js/dash.js` | (1) in the `Promise.all` result path / `init()` expose a read-only context: `window.__spacebros.exportCtx = function(){ return { rank: X.rank, mandals: X.mandals, manifest: X.manifest, catalog: X.catalog, cfg: X.cfg, events: X.events, date: primaryDate(), coastDate: coast date for the view, classPng: layer for classId(date), selected: S.sel } }`. (2) `buildDayCard()`: add `<button data-day="brief">Official brief and data bundle</button>`. (3) `bindDay()` click handler: `else if (a === 'brief') runExport()`; `runExport` shows progress through the existing `say()` (`#dc-msg`), disables the button while working, and reports errors in plain English. (4) `dlBlock()` (Downloads card): one `<li>` with the same action for the selected mandal and date. About 40 lines. Choose the pass: a coast date from the current view (`share`, `radar`, `swipe` after-date); for sea passes and the eye mode the button says "Brief needs a coast pass" and offers the newest coast pass. |
| `app/dashboard-mockup/index.html` | add two `<script>` tags before `dash.js`: vendor lib, then `js/export.js`. |
| `app/dashboard-mockup/css/dash.css` | about 10 lines: busy state and message style of the new button. |
| `tools/tests/test_english_only.py` | optional (+15 lines): scan `export.js` string literals and the README template for non-Latin letters. This file runs in `run_all` and `pages.yml`, so keep the change small and run it. |
| NOT touched | `app/js/brief.js`, `app/css/brief.css` (old shell keeps working), pipeline, data. |

Mandal selection: use `S.sel` (selected mandal). Data tab has the mandal table; the brief button reads `S.sel` and the chosen date. Join mandal geometry by name, preferring the feature whose `district` matches the ranked row (`Yelamanchili` appears twice in `mandals.geojson`; `dash.js` already handles this for the map).

### P1.4 Data fields: field -> file -> key

| in brief / CSV | file | key |
|---|---|---|
| mandal, district | `data/processed/mandal_rank.json` | `by_date[YYYY-MM-DD].rows[].mandal`, `.district` (top-level `rows` = newest date only) |
| likely new open water share, error | same | `.water_pct`, `.water_err` |
| wet or flooded crops share, error | same | `.crops_pct`, `.crops_err` (brief shows it with the "unproven" tag; headline is water only per `data/story_rules.json`) |
| total, error | same | `.total_pct`, `.total_err` |
| normal fortnight comparison | same | `.normal_pct`, `.normal_water_pct`, `.change_vs_normal_pp`, `.water_change_vs_normal_pp` |
| ranks | same | `.rank` (total), `.rank_water` (null = not ranked) |
| coverage, area | same | `.coverage_pct`, `.area_km2`, `.land_km2`, `.frac_in_footprint`, `.flag` |
| km2 | same | `.water_km2`, `.crops_km2`, `.flooded_km2` |
| neighbours (3 above and below by rank) | same | rows sorted by `rank_water`, same district rule as `brief.js regionRows` |
| scene id, product status, UTC start | same | `by_date[d].scene_id`, `.product_status`, `.start_utc` |
| pass headline, caveats, confidence | `data/processed/findings/<date>.json` | `headline`, `caveats[]`, `confidence.level/reasons[]`, `provisional_text`, `official_banner`, `data_as_of_text`, `event_chips[]` |
| three numbers | same | `three_numbers[]` (`value`, `err`, `label`) |
| baseline dates, thresholds, method text | `mandal_rank.json` | `provenance.baseline_dates`, `.thresholds`, `.caveats`, `.method` |
| map crop | `data/web/class_<yyyymmdd>_new_water.png` | path from `classId(date)` -> layer `.png`, `.bounds` |
| mandal outlines | `data/processed/mandals.geojson` | `features[].geometry`, `.properties.name/.district` |
| NISAR credit line | `manifest.json` | `sources[id=asf_nisar_l].credit_line` = "NISAR L2 GCOV, NASA/JPL-Caltech and ISRO, via ASF DAAC (NASA Earthdata)", `.licence` |
| derived credit | `manifest.json` | `sources[id=spacebros_derived].credit_line` = "SpaceBros, from NISAR data" |
| boundary credit | `manifest.json` | `sources[id=geoboundaries].credit_line`; district assignment note from the same entry |
| generated stamp | browser | `new Date()` in IST, page URL |

Zip contents: `brief_<mandal>_<date>.html`, `mandals_<date>.csv`, `mandals_<date>.geojson` (the 66 listed mandals with all CSV columns joined as properties, plus `ranked`), `findings_<date>.json` (verbatim copy of the findings file), `README.txt`. Expected size: under 250 KB zipped.
`README.txt`: pass, generated time, file list, **column definitions generated from the same `COLUMNS` table as the CSV header**, units (shares in percent of valid non-permanent-water land pixels, errors in percentage points, km2), method in six lines (from METHODS.md section 1), limits (baselines PROVISIONAL, no ground truth, wet crops unproven, 9 Nov includes Murasu and the river peak), credits and licences:
- NISAR: line above; licence text from the manifest source ("NASA Earth science data, open by default (CC0 unless marked); follow ASF DAAC terms").
- Boundaries: geoBoundaries, acknowledgement required. **Licence conflict found**: `geoboundaries.org` states CC BY 4.0 (fetched this session, "the only requirement for use is acknowledgement"; cite Runfola et al. 2020 PLoS ONE 15(4): e0231866 for written works); `manifest.json` says "check ... our earlier note said ODbL"; `dash.js` `DL` list still labels it ODbL-1.0. Use CC BY 4.0 in the README and fix the `dash.js` label in the same edit.
- District assignment: `data/reference/mandal_district_2022.csv`, "Wikipedia-sourced" per the manifest note. Licence status not checked: name the source in the README.
- SpaceBros derived products: the manifest gives no licence ("team product from NISAR data"). **The team must pick one** (CC BY 4.0 would match the inputs) before the README is final.

### P1.5 Test plan

| test | how | pass when |
|---|---|---|
| 28 Oct pass | `#tab=data&mode=share&d=2026-10-28`, select Nidadavole, click button | brief shows 28 Oct dates, rank 29 / 45 style values from `by_date['2026-10-28']`, headline "No mandal looks probably flooded in this radar picture." appears if the brief shows the pass headline; zip numbers equal `mandal_rank.json` |
| 9 Nov pass | same with `d=2026-11-09` | Nidadavole water 10.9 +/- 1.61 %, rank_water 1; provisional and Murasu caveat text present |
| Zip opens and CSV matches README | download, `unzip -t`, then `.venv/bin/python -I` script: read CSV header, parse README column lines, assert same names and order; 66 rows; ranked count 54; every numeric cell equals the source JSON | exact match |
| Credits | grep brief HTML and README | NISAR line, SpaceBros line, geoBoundaries line, licence lines, "no basemap" so no Esri line needed |
| English only | scan brief and README for non-Latin letters (reuse `bad_letters` from `test_english_only.py`), including a mandal with a Telugu alias if any | none |
| Phone 390 px | browser resize 390x844; button visible, message in `#dc-msg`, no horizontal scroll; the generated brief opened in a new tab scales (fixed A4 width, `zoom`/`transform` to viewport) and is readable | no overflow, tap targets >= 40 px |
| Print preview A4 | Chrome print preview of the brief tab: one page, no cut-off, background colours kept (`print-color-adjust: exact`), map crop visible | exactly 1 page |
| Failure cases | block `findings/<date>.json` (404), block the class PNG, sea date selected, mandal with `flag` (unranked) | brief still builds with a plain "not available" line, never invented numbers; unranked mandal shows the `flag` text |
| Pipeline tests | `python tools/tests/test_story.py`, `test_findings.py`, `test_events.py`, `test_english_only.py`, `python tools/check_manifest.py` | all pass (P1 touches no pipeline file, so this is a regression check) |
| Hash/saved days | open a saved day then export; hash unchanged after export | unchanged |

### P1.6 Effort and go/no-go

| item | agent-h | wall-clock |
|---|---|---|
| vendor lib + licence record | 0.3 | 0.2 h |
| `export.js` data side (CSV, GeoJSON, README, zip, download) | 1.5 | 1.5 h |
| `export.js` brief HTML (port of brief.js geometry, A4 CSS, PNG crop) | 2.0 | 2 h |
| `dash.js` / `index.html` / css wiring | 0.5 | 0.5 h |
| testing and fixes (both dates, 390 px, print, zip check) | 1.0 | 1 h |
| **Total** | **about 5** | **about 3 h with two builders in parallel** (A: data side + wiring, B: brief HTML; B delivers a pure function so only A edits `dash.js`), plus 1 h QA |

**GO.** Highest visible value, no pipeline change, so the five pipeline tests cannot be broken by it. Tight but fits before 16:00 if started by 08:00.

---

## P2-A. Floods in general (GDACS `FL`)

### What already works (verified in code and data)
- `alerts.py`: `GDACS_TYPES = ("TC","FL")`; keeps an item when its centroid or bbox touches `alert_match.bbox` [79.5,15.0,85.0,18.5]. Failed fetch keeps old items.
- `events.py alert_candidates`: `GDACS_KIND = {"TC":"cyclone","FL":"flood"}` -> a draft `auto_GDACS_<id>`, `status alert_only`, `reviewed_by_human false`, severity "as given" ("Green alert"), 30 days aftermath, `edit_log`.
- Link rule: passes in `[start, end + aftermath]` are linked; first link moves the draft to `radar_linked`.
- Never published: `build_story.py` `event_publishable()` needs `status == "active"` and `reviewed_by_human is not False`; a draft only produces a chip "After Flood in India (alert, not reviewed)" and an archive entry tagged "Draft from alert, not reviewed". Hero text, event story and the eye profile come only from reviewed active events.
- A human reviewed event of the same type and overlapping dates absorbs the alert as an `alert_ref` (no duplicate).

### What is wrong or missing
1. **A GDACS flood is a point from a river model, not a footprint near our radar box.** Live draft `auto_GDACS_1104248`: GDACS says source `GLOFAS`, Green, "Magnitude 0", point 80.17E 15.45N; its `Poly_Affected` polygon (fetched from `.../api/polygons/getgeometry?eventtype=FL&eventid=1104248&episodeid=4`) spans 80.12-80.21E, 15.40-15.49N, about 150 km west and 80 km south of the COAST box [81.6,16.2,82.6,17.1]. The draft is still linked to the four delta/sea passes and the two COAST links carry `radar_finding` "change_seen" / "no_clear_change", which reads as if radar looked at that flood. It did not. The 9 Nov findings show the chip "After Flood in India (alert, not reviewed)".
2. No FL test: `tools/tests/test_events.py` has cyclone, J&K and SACHET cases only.
3. Wording for floods: `cannot_tell` is the generic cyclone-style line; nothing says the alert is a model estimate or how far it is from the radar box.

### Exact changes
| file | change |
|---|---|
| `tools/pipeline/alerts.py` | `norm_gdacs`: keep `bbox` as is; add a second call for `FL` items only: GET the `url.geometry` (already in the API response, `properties.url.geometry`) and store the `Poly_Affected` bbox as `affected_bbox`; on failure keep the centroid only. `out_gdacs_item`: pass `affected_bbox` and `source` (`properties.source`, "GLOFAS") through. Keep `alerts-v2` schema, new keys optional. |
| `tools/pipeline/events.py` | new helper `radar_distance_km(item, ar)` (haversine, stdlib) from the footprint (else the point) to the COAST box; in `alert_candidates` carry `affected_bbox`, `point`, `source_model`. In `new_draft` for `flood`: add `cannot_tell` lines: "GDACS flood alerts here come from a river-flow model (GloFAS) and give a point or a small area, not a flood map." and "This alert is about N km from the radar area." In `link_passes`: for a flood draft that is not reviewed and whose footprint is farther than `defaults.flood_link_km` (new, default 50) from the COAST box, **do not link passes**; keep `alert_only`, `status_text` "Alert only, outside the radar area". For existing unreviewed drafts, `update()` may drop links that no longer qualify (drafts only; reviewed events are never edited). |
| `config/areas.json` | `defaults.flood_link_km: 50` (read by `common.area()` `_defaults`; check it passes through). |
| `tools/tests/test_events.py` | add 5 cases: FL inside the box -> draft + links; FL like 1104248 (outside) -> draft, no links, text says outside; FL with failed footprint fetch -> centroid rule; human flood event absorbs FL alert; idempotent second run. Add FL fixtures in `tools/tests/fixtures/`. |
| `app/dashboard-mockup/js/dash.js` | none required (status text and `cannot_tell` already render). |
| `app/strings/story.en.json` | none: `chip_draft` already says "alert, not reviewed". Optional: do not show a chip at all for a draft with no linked passes (one `if` in `build_story.chips_for`). |
| wording | keep "likely new open water" for anything radar-derived; the flood draft text must say "alert", "model", "not confirmed by radar". The pipeline already refuses the word "confirm" in draft text (test `test_ap_cyclone_alert_makes_draft_alert_only`). |

Side effect to plan for: removing the flood chip changes `event_chips` in `findings/2026-10-28.json` and `2026-11-09.json`, so their input hash changes and each gets a revision +1 (write-once rule, logged). Land this **before** P1 QA so the zip copies the final findings.

Effort 1.5 agent-h, wall 1.5 h (includes `run_all.py --offline` and the `tools/sim/run_sim.py ap_alert` scenarios). **GO**, small and removes a misleading chip. If short of time, cheaper cut: tests plus the `cannot_tell` line only (0.5 agent-h) and leave linking as is.

---

## P2-B. Mangrove change at Coringa (EXPERIMENTAL)

### B.1 Citable open source: Global Mangrove Watch (GMW)

Checked on Zenodo (API, this session):

| item | v4.0.19 "Annual Mangrove Extent" | v4.1.12 "Timeseries of Mangrove Extent" | v3.0 (1996-2020) |
|---|---|---|---|
| DOI | 10.5281/zenodo.12756047 (concept 10.5281/zenodo.12756046) | 10.5281/zenodo.21346457 (concept 10.5281/zenodo.21346456) | 10.5281/zenodo.6894273 |
| date | 17 Jul 2024 | 13 Jul 2026 | 24 Jul 2022 |
| content | 2020 extent, 10 m (Sentinel-2) | annual 1985-2025, 10 m class extent | 25 m, 1996-2020; its page says v4.1 supersedes it |
| licence | Creative Commons Attribution 4.0 International (Zenodo metadata `cc-by-4.0`; record page text read) | CC BY 4.0 (metadata) | CC BY 4.0 (metadata) |
| files | `gmw_mng_2020_v4019_gtiff.zip` 180,055,707 B (md5 a94b1600d891cda0e1ea0f17b312990b); `..._vec.zip` 392,767,631 B | per year `gmw_v4112_<year>_mng_ext_cntry_info_vec.gpkg.gz` 150-190 MB each (2025: 189,517,714 B), 41-band stack tar.gz 1.4 GB, README.txt, `gmw_v4112_tiles.geojson` | many |
| tile format | 1,647 GeoTIFF tiles of 1 deg x 1 deg, name = **top-left** corner (e.g. `GMW_N17E082` = 16-17N, 82-83E), EPSG:4326, 0.0001 deg pixel, uint8 0/1 | global GeoPackage or stack, not tiled | |

Download route: Zenodo file URLs `https://zenodo.org/api/records/12756047/files/<file>/content`. The server answers HTTP Range requests (206 confirmed), so single tiles can be pulled out of the 180 MB zip by reading its central directory and only the needed member (done, below). v4.1.12 has no per-tile download: the cheapest route is the 2025 GeoPackage (about 190 MB gz) then `ogr2ogr -clipsrc 81.6 16.2 82.6 17.1`.
**Recommend v4.0.19 2020** for the experiment (only 10 m product that is tile-addressable; extent is 6 years old, say so) and v4.1.12 2025 as the upgrade if time allows.

Credit line (built from the Zenodo record metadata; the record shows no "Cite as", so confirm wording on globalmangrovewatch.org before submission):
"Bunting, P., Hilarides, L., Rosenqvist, A., Zanaga, D., Van De Kerchove, R., Lucas, R., Castro Brandao Vaz dos Santos, P. (2024). Global Mangrove Watch: Annual Mangrove Extent (Version 4.0.19) [Data set]. Zenodo. https://doi.org/10.5281/zenodo.12756047. CC BY 4.0." The record's description also credits Copernicus Sentinel-2 imagery, the ESA WorldCover 2020 pre-processing (Zanaga et al., 2021) and CoastTrain (Murray et al., 2022).
For v4.1.12 the record's own suggested citation (printed on the v3.0 page) is: Bunting, Hilarides, Rosenqvist, Oakes, Castro Brandao Vaz dos Santos, Worthington, Rosenqvist, Zanaga, Van De Kerchove, Tadono, Kobayashi (2026), Timeseries of Mangrove Extent (Version 4.1.12), Zenodo, https://doi.org/10.5281/zenodo.21346456. Its README gives global F1 0.9276 (omission 6.4 %, commission 8.1 %), "will vary locally".

### B.2 Downloaded extract (licence allows: CC BY 4.0)

New dir `data/external/gmw/` (was empty). Pulled with Range requests from the v4.0.19 zip, members read and CRC-checked by Python `zipfile`; never executed; analysed with `python -I`.

| file | bytes | sha256 |
|---|---|---|
| `GMW_N17E081_v4019_mng.tif` | 477,518 | 3d1cbd4929bcce40eb06257247ef164c985d48d0b8d6c12b965e31c60ab5f263 |
| `GMW_N17E082_v4019_mng.tif` | 500,918 | 111ec426e104bcb70a376f90e81dd18574b78dd9a401edcbaca265ce705446cc |
| `GMW_N18E082_v4019_mng.tif` | 412,285 | a50d2f134dc0e28ce6814cae033620c1c84ab0ff7179cb37d4602af72aeaad4b |

Total 1.39 MB. `N18E082` holds no mangrove inside the COAST box (its 4,984 mangrove pixels are at 82.86-82.88E, 17.43-17.46N, outside); kept only as the record of what was checked. Needed: `N17E082` and `N17E081`. No clipping done (tiles are small; clip when building).
Reproduce: Range-read the zip central directory, extract the three members (the helper used is in the session scratchpad, not in the repo; a builder can use `zipfile` over an HTTP Range file object, or simply download the 180 MB zip once and `unzip -j` the three names).

### B.3 Does Coringa lie inside the COAST box? Yes (computed)

GMW 2020 mangrove pixels (value 1) from the two tiles, tested against COAST box [81.6,16.2,82.6,17.1] and the Coringa window 82.2-82.4E, 16.7-17.0N:
- `N17E082`: 1,676,063 pixels, lon 82.024-82.364, lat 16.440-16.983, **all inside the box**, about 197.5 km2 (cos(lat) area).
- `N17E081`: 466,645 pixels (lon 81.066-81.968, lat 16.00-16.49), 22,828 px inside the box (about 2.7 km2, Godavari estuary side). The rest of that tile lies south or west of the box.
- Inside the Coringa window: 1,121,909 pixels, about 132 km2.
- Mapped onto the 20 m UTM 44N grid of `data/h5/L_COAST_20261028_T055.h5` (5008 x 5360, x0 563840, y0 1891310, dx 20, dy -20, EPSG 32644): **515,334 grid cells (about 206 km2)** hit by a mangrove pixel; all have `aux/mask == 1` on 28 Oct. (A cell counts if any 11 m source pixel lands in it, so this slightly overstates area.)
So the mask is about 200 km2 in the box, about two thirds of it in the 16.7-17.0N window you quoted; the forest runs south to about 16.44N.

### B.4 Method (all new code in a new file, outside the gated pipeline)

New: `tools/experimental/mangrove_hvhh.py` (not in `run_all.py`, not in `pages.yml`), importing `read_backscatter`, `_box_db`, `_erode`, `_read_mask`, `SMOOTH_PX`, `EDGE_PX` from `tools/build_web.py` (module is `__main__` guarded) so smoothing and validity are identical to the class maps (3 x 3 linear-power boxcar, 2 px edge drop, `aux/mask == 1` on all used dates).

1. Mask M: GMW 2020 pixels -> 20 m grid (pyproj EPSG:4326 -> 32644, as in B.3); a cell is mangrove if at least half of its source pixels are 1 (build via counts); erode 1 cell (20 m) to avoid edge mixing with water and mud; drop permanent water (HH < -12.3 dB on both baseline dates, from `compute_coast_classes()["perm"]`, whose result also gives `valid` and `grid`).
2. Statistic per pixel: R = HV_dB - HH_dB (cross-pol ratio in dB, after the 3 x 3 smoothing in linear power). Baseline R_b from the linear-power mean of 4 and 16 Oct (same as the class maps). Event change D(d) = R_d - R_b for d = 28 Oct, 9 Nov.
3. Median change inside M: m_M(d) = median of D(d) over M.
4. Offset correction (provisional baselines vs validated events): `docs/METHODS.md` and `docs/review/LBAND_TEST.md` give land-wide HV +1.93 dB (28 Oct) and +0.84 dB (9 Nov), HH +0.05 and -0.34 dB, so the HV minus HH ratio shifts about +1.5 and +1.1 dB land-wide before any storm effect. Correction: delta(d) = m_M(d) - m_ref(d), m_ref = median D(d) over land outside M. **Assumes** the offset is additive in dB, is the same for mangrove as for the reference pixels, and is not caused by the storm. That assumption is doubtful: LBAND_TEST.md measured that the HV rise depends on baseline brightness (+4.7 dB for dark fields at -20..-18 dB, +0.7 dB at -12..-8 dB, +2.5 dB in the west) and mangrove is bright. A land-wide median would then over-subtract. So report three numbers: uncorrected, land-wide corrected, and **matched-reference corrected** (reference = non-mangrove land pixels in the same 1 dB baseline-HV bin and the same range band, at least 2 km from the mangrove mask). If they disagree in sign, say the change cannot be separated from calibration differences.
5. Normal-fortnight control: same recipe for 16 Oct against 4 Oct inside M (baseline = 4 Oct only, so its noise is slightly higher than the two-date baseline; say so). delta_ctrl is the false-alarm scale. Quote `delta(d)` next to `delta_ctrl`.
6. Error: block bootstrap over M. Blocks are squares on the UTM grid, side L. Speckle is already averaged (20 m posting from a 2 x 2 multilook of 10 m, then 3 x 3 boxcar), so speckle correlation reaches about 3-5 cells (60-100 m); tide, canopy wetness, wind and local incidence-angle effects are correlated over kilometres. L = 1 km (50 x 50 cells, at least 10 x the speckle length) gives about 200 blocks over 206 km2; sensitivity L = 500 m (about 800 blocks) and 2 km (about 50 blocks, intervals widen). 2,000 resamples; resample blocks with replacement; compute the median from per-block histograms of D (0.05 dB bins) so it is fast; bootstrap the reference median at the same time (its own blocks over land outside M) and subtract per resample; report the 2.5-97.5 percentile interval. Fewer than about 30 blocks = do not quote an interval.
7. Outputs: `data/web/mangrove_experimental.json` (new, schema `mangrove-hvhh-v0`, with `provenance`, mask source + sha256 of tiles, thresholds, all three corrections, L sensitivity, control) and one table in a doc. No map layer, no km2 of "loss".

### B.5 What the result may say (and not)

Allowed wording, only if the interval excludes the control and the three corrections agree in sign: "Experimental. In the area mapped as mangrove by Global Mangrove Watch (2020 extent), the median HV minus HH radar difference changed by about X dB (95 % range a to b) between early October and 28 Oct, compared with Y dB between two normal pre-storm passes. We have not checked this against any ground or optical observation."
Not allowed: damage, loss, die-back, deforestation, cause (cyclone), area in km2 or percent of mangrove affected, "healthy", any comparison with other studies.
Must state: no ground truth; baselines PROVISIONAL; acquisition time is 00:01 UTC every date but tide state differs by date and **tide level was not checked** (no tide source retrieved); post-cyclone canopy and soil wetness and standing water under the canopy change HH and HV (standard SAR scattering expectation, not tested here); the 9 Nov pass also contains Murasu and the river peak; Oct-Nov is post-monsoon with kharif harvest nearby, so the reference (agriculture) and the target (mangrove) respond to different seasonal drivers; 2020 extent is 6 years old; GMW accuracy is global (F1 0.9276 for v4.1.12) and varies locally.

### B.6 Effort and go/no-go

| item | agent-h | wall-clock |
|---|---|---|
| mask rasterisation, recompute smoothed HH/HV for 4 dates (about 1 GB), medians | 1.0 | 1 h |
| offsets, matched reference, control | 0.75 | 0.75 h |
| block bootstrap and sensitivity | 0.75 | 0.75 h |
| JSON, short doc table, wording review | 0.5 | 0.5 h |
| UI card, legend, mask layer, tests, English-only, story template | 3-4 | 3 h |

**Analysis only (about 3 agent-h, about 2.5 h wall): GO if capacity is free**, as a separate agent in parallel (read-only on `data/h5`, writes only new files). **UI/feature before freeze: NO-GO.** It needs a new card in `dash.js` (conflicts with P1 wiring), copy that passes the story banned-word guard, and the science is unproven (HV offset is not uniform; no ground truth). A single honest paragraph plus table in the submission docs is the safe form. Fallback if the Python analysis cannot be finished by about 13:00: drop it and leave this section as the "future work" text (the existing `docs/handoff/06_PLAN_Eye_of_the_Storm.md` line 195 already allows that).

---

## 1. Dependencies

- P2-A before P1 QA (it changes `event_chips`, so findings files revise; P1 copies findings into the zip).
- P1 and P2-B are independent if P2-B stays analysis-only (different files).
- P2-B UI would depend on P1 (both edit `dash.js`) and on P2-A not at all.
- P1 needs the licence decisions below (README text), not code.

## 2. Go / no-go and value per hour

| feature | agent-h | wall | value | call |
|---|---|---|---|---|
| P2-A footprint guard + FL tests | 1.5 (0.5 minimal) | 1.5 h | removes a misleading live chip, closes an untested path | GO (first, parallel) |
| P1 official brief + zip | 5 | 3 h (+1 h QA) | most visible to officials and judges, no pipeline risk | GO (main) |
| P2-B analysis only | 3 | 2.5 h | one honest "experimental" paragraph; moderate | GO only if a spare agent exists |
| P2-B UI | 7 | 4-5 h | low, scientifically unproven | NO-GO |

## 3. Recommended order and cut-line

1. **P2-A** (agent 1, start now; merge by about 10:00, run all five pipeline tests + sim).
2. **P1** (agents 2 and 3 in parallel from now: data side + wiring, brief HTML); integrate by about 12:00; QA 12:00-13:30 (both dates, 390 px, print, zip check).
3. **P2-B analysis only** (agent 4, parallel from now, read-only on the repo; stop at 13:00 either way).
4. **Cut-line: 14:00.** Anything not passing its tests by 14:00 is cut, in this order: P2-B first, then the P1 GeoJSON/CSV extras, then P2-A beyond tests. P1's minimum shippable cut = CSV + findings JSON + README zip with the brief opened as HTML (print from the browser). 14:00-16:00 is for the five pipeline tests, a final browser check and the push.

## 4. Open decisions for the team (not answerable from the repo)

1. Licence for SpaceBros derived products (README) and the exact attribution wording for the mandal-to-district CSV (Wikipedia-sourced).
2. Final site name (config has three options; the brief header reads `site.title`).
3. Whether the bundle may carry the brief for sea passes (plan: no, coast passes only).

## 5. Risks

- **Brief A4 overflow**: long mandal or district names ("Dr. B.R. Ambedkar Konaseema", "Yanam (Puducherry UT, not Andhra Pradesh)") break one-page layout; test with the longest names and use CSS clamp.
- **Class PNG is 36 m display resolution** (METHODS.md): the crop looks coarse at mandal zoom; caption must say "display image, 20 m data".
- **Same-origin canvas**: `toDataURL` fails if the page is opened from `file://` or the PNG is cross-origin; the brief then omits the image and says so.
- **Findings revise after P2-A** (revision +1); P1 test numbers must be read from the final files, not hard-coded.
- **geoBoundaries licence label** wrong in `dash.js` (ODbL) vs site (CC BY 4.0): fix with P1 or the README contradicts the page.
- **Popup blockers**: opening the brief tab must happen inside the click handler; fall back to a plain download link.
- **fflate vendored file integrity**: check sha256 against two CDNs; the file is third-party code that runs on the page.
- **Memory**: P2-B holds 8 float32 arrays of 107 MB (about 1 GB) plus masks; run on the Mac, not in CI.
- **P2-B science**: HV offset not uniform; tide not checked; mask 6 years old; no ground truth; 9 Nov mixes three events. Any number that reaches the page must carry "experimental".
- **Esri basemap**: no Esri content is exported by the plan; if a basemap is later wanted in the brief, read the Esri terms for this service first (not verified here).
- **GDACS footprint call** adds one request per FL item; failure must keep the centroid rule and never blank `alerts.json`.
- **Freeze**: the pipeline gate is five test commands (`run_all.py` `TEST_CMDS`); any failure = no deploy. P1 does not touch them; P2-A does.

## Sources

- fflate: https://github.com/101arrowz/fflate (LICENSE MIT), https://cdn.jsdelivr.net/npm/fflate@0.8.2/ , https://registry.npmjs.org/fflate/latest
- JSZip: https://github.com/Stuk/jszip/blob/main/LICENSE.markdown , https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js
- client-zip: https://cdn.jsdelivr.net/npm/client-zip@2.5.0/index.js , https://registry.npmjs.org/client-zip/latest
- zip.js: https://registry.npmjs.org/@zip.js/zip.js/latest , https://cdn.jsdelivr.net/npm/@zip.js/zip.js@2.7.62/dist/zip.min.js
- GMW v4.0.19: https://zenodo.org/records/12756047 (API https://zenodo.org/api/records/12756047)
- GMW v4.1.12: https://zenodo.org/api/records/21346457 (DOI 10.5281/zenodo.21346456 / .21346457); v3.0: https://zenodo.org/record/6894273
- geoBoundaries licence and attribution: https://www.geoboundaries.org/
- GDACS FL event and geometry: https://www.gdacs.org/gdacsapi/api/events/geteventdata?eventtype=FL&eventid=1104248 , https://www.gdacs.org/gdacsapi/api/polygons/getgeometry?eventtype=FL&eventid=1104248&episodeid=4
- Esri basemap terms (search only, not read in full): https://downloads2.esri.com/arcgisonline/docs/tou_summary.pdf , https://resources.esri.ca/education-and-research/how-to-cite-arcgis-maps-and-data
