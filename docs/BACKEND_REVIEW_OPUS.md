# Backend review (Opus): gaps for the two-audience dashboard

Reviewed Sat 14 Nov 2026, about 14:45 IST (09:15 UTC), by reading every file named in the brief and checking it against the data on disk. About 33 hours remain before the deadline (Sun 15 Nov 23:59 IST). No existing file was changed and nothing was downloaded. Where a number below comes from my own quick checks, the method is given and it is marked **[my check]**. Those checks used numpy and PIL only, on decimated or block-averaged rasters, with no reprojection and no water mask. They are good enough to steer decisions and too rough to publish.

---

## 0. Verdict in ten lines

1. **The docs are out of date, and the data is better than they say.** `BACKEND_GAPS.md`, `PLACEHOLDERS.md`, `sources.yaml` (`status: blocked_credentials`) and the manifest notes all claim the NISAR GeoTIFFs are blocked on an Earthdata login. They are not. Real GCOV subsets exist for all four T55 coast dates (HH and HV, 10 m, about 300 MB each) and for three T48 sea dates (VV only, 100 m). Anyone planning from the docs will plan the wrong work.
2. **There is no findings layer at all.** No file, no schema, no method, no thresholds, no confidence rules and no plain-language templates. The only interpreted output, `mandal_rank.json`, is 45 invented rows.
3. **There is no classification method written down anywhere.** Not in the plan, the registry, the evidence pack or the code. `src/change_map.py` is a Delhi-era dB difference with a fixed ±3 dB cut. This is the critical path. Without it there is nothing honest to turn into plain language.
4. **The 28 Oct coast pass cannot be used to find open water.** Wind roughened the water at pass time **[my check]**: open sea sits at about -16.9 dB HH, against -19.6 dB before and -18.6 dB after. A threshold method will report *less* water during the storm than before it. Use 9 Nov for water and treat 28 Oct as "storm-time surface", not as flooding.
5. **The strongest land signal is not "new open water".** It is a 3 dB or larger *drop* in brightness over bright land: 14.8% of land blocks from 16 Oct to 9 Nov, against 0.2% in the normal fortnight **[my check]**. Pixels that turned dark enough to look like open water are only about 0.2 to 0.5% of land. That pattern fits flattened (lodged) or harvested paddy, or saturated soil, better than standing water. The label "likely wet or flooded crops" may not describe what the radar saw. A human has to decide this before any plain-language sentence is written.
6. **The "before" and "after" scenes were made by different processing versions.** 4 and 16 Oct are PROVISIONAL; 28 Oct and 9 Nov are validated GCOV_V1. Towns (stable bright targets) agree to within about 0.5 dB, so there is no gross calibration jump **[my check]**. The dark end (water, noise floor) does differ: the 0.5th percentile is about -24 dB in the provisional scenes and about -19 dB in the validated ones. So any **fixed** water threshold is biased between "before" and "after". Thresholds must be set per scene.
7. **The eye is unverified.** `profile.json` is invented. A 3 km scan of the 27 Oct VV image within ±45 km of IMD's 13:01 UTC position (about 16.3 N, 82.6 E) shows no clear low-backscatter eye disc **[my check, rough]**. Do not promise an eye radius ± km until someone has actually found the eye.
8. **The alerts problem cannot be fixed with this feed.** The real SACHET snapshot (`data/interim/C/alerts.json`) was taken *today*. The feed only holds about 4 days of alerts (98 items from 10 Nov onwards) and **none mention Andhra Pradesh**. Alerts from Arnab's time (27 Oct) cannot be recovered from SACHET RSS.
9. **The landfall wording is wrong in data as well as in code.** The 28 Oct layer is named "Coast, 4 hours after landfall" in `manifest.json`, which breaks the manifest's own rule against putting a landfall time in the data. Under IMD's final statement it is also wrong: at 05:31 IST IMD still had the storm's centre about 30 km offshore, inside the 02:00–08:00 IST crossing window.
10. **Realistic scope.** All the MUST items below add up to about 14 to 18 person-hours, plus pipeline compute. That is achievable with two people working, and only if the method decision (M3) is made in the next 2 hours. If it slips, ship real greyscale radar plus raw per-mandal statistics with a "change in brightness" finding (Option B in section 5), not flood claims.

---

## 1. Inventory: what is real and what is a sample (checked on disk)

### 1a. NISAR L-band

| Item | On disk | Real? | Verified how | Problems |
|---|---|---|---|---|
| Coast T55 F10 HH and HV, 4, 16 and 28 Oct and 9 Nov | `data/raw/nisar_l/coast/<date>_T55_{HHHH,HVHV}.tif`, 10720×10017, float32, 10 m, EPSG:32644 (UTM 44N), origin 563830 E / 1891320 N, NaN nodata, deflate | **Real** | GeoTIFF tags read with PIL. All 8 files share **the same grid** (same tie point and size), so they are same-track, same-frame and pixel-aligned with no resampling needed | File names say `HHHH` but the **values are already dB** (`subset_arnab.py` converts with 10·log10). `mask`, `numberOfLooks` and `rtcGammaToSigmaFactor` were **not saved**, though `sources.yaml` lists them as outputs. Without `mask` we have no layover, shadow or invalid flags. 78 to 83% of the delta box has data **[my check]**. |
| Sea T48 F80 VV, 15 and 27 Oct and 8 Nov | `data/raw/nisar_l/sea/<date>_T48_VVVV.tif`, 3398×3006, 100 m (5×5 block mean in linear power), EPSG:32644 | **Real** | Tags read; median VV is -14.2 / -9.7 / -14.1 dB (calm / eye pass / after), which makes sense | **VH is missing** even though `SEA_POLS` asks for it. Only about 30% of the 4°×3° sea box has data: rows 983 to 2750, roughly 16 to 18 N, 81 to 84 E. The 3 Oct quad-pol scene was never subset, so layer `nisar_l_sea_20261003_t48_vv` can only ever be a quick-look. |
| "Aligned" stack | `data/interim/B/aligned/*_db_aligned.tif` (6 files so far, still being written at 09:16 UTC) | Copies | Byte sizes **identical** to the raw files, same grid | Since the raw files already share a grid, this is about 1.8 GB of duplicate data, harmless but wasted. Make sure nobody "aligns" them a second time by resampling. |
| Subset provenance | none | missing | `data/logs/` has **no `nisar_l_subset.md`** although the script writes one | No sha256, granule ID or run log next to the rasters. The raw-data audience needs this. |
| Display PNGs, 8 files | `data/processed/img/nisar_l_*.png` (0.40 to 0.54 MB each) | **Sample** | `_index.json` says: "luminance of colour quick-look, not dB" | Placed with axis-aligned bounds taken from the KML *LatLonQuad* (a rotated quad), so they are geolocated approximately. Bounds for 3, 4, 15 and 16 Oct are inferred. All can now be replaced from the real GeoTIFFs. |
| Derived class maps and sea difference | none | missing | `check_manifest.py --files` reports 4 missing | Blocked only by the method decision, no longer by login. |
| S-band | `data/raw/nisar_s/` empty; `nisar_s_candidates.csv` does not exist | none | n/a | No evidence of any scene. Licence also unconfirmed (registry says "Open Data, non-commercial, derivatives allowed"; worker D could not confirm). Keep the toggle off. |

### 1b. Companion JSON files and reference data

| File | Status | Notes |
|---|---|---|
| `data/processed/mandal_rank.json` | **Sample** (45 invented rows; `placeholder.is: true`) | Only 3 districts. Keyed by `mandal` name, which is not unique (see Yelamanchili). No coverage fraction, no pixel count, no method ID. |
| `data/processed/profile.json` | **Sample** | Eye at 16.3, 82.6 with "18 ± 3 km" and "+6.2 dB" are invented. In the real data that point is about 6.5 dB *brighter* than calm sea (storm area), not a calm eye **[my check]**. |
| `data/processed/alerts.json` | **Sample** | A real snapshot exists in `data/interim/C/alerts.json` with an honest `credit` and the feed URL, but it is from 14 Nov with 0 AP items, so it is not about the event. |
| `data/processed/mandals.geojson` | Real geometry, **stale attributes** | 146 polygons, 81 with `district: null`. A **complete** mapping already exists in `data/interim/C/mandal_district_2022_complete.csv`: 142 of 146 mapped, with source and confidence per row. It has not been promoted to `data/reference/` or fed through `make_web_assets.py`. |
| `data/processed/imd_track_arnab.geojson`, `data/reference/imd_track_arnab.csv` | Real | 15 fixes with PDF page references. Good provenance. |
| `data/interim/gsw_occurrence_delta.tif` | Real (JRC GSW occurrence, **v1.4 / 2021** tile, EPSG:4326, 0.00025°) | The registry names v1.5 / 2024. Either is fine; the version must be stated. It needs reprojecting to the UTM 44N grid before it can serve as a permanent-water mask. |
| ERA5 / Open-Meteo archive points | Real (`era5_wind_summary.csv`) | Useful for the calm-day caption (about 3 to 4 m/s on 15 Oct). |
| GIBS stills | Real, mostly in `raw/` (git-ignored) | Only 3 are exported to `processed/img`. |
| IMD PDFs (16, about 50 MB) | Real, **untracked** in `docs/imd_bulletins/` | `.gitignore` comments say they "stay tracked". The registry says "do not re-host PDFs". See R7. |
| Licence facts | Mixed | `geoboundaries_meta_ADM3.json` says **ODbL 1.0**, source Pathways Data / lgdirectory.gov.in. Worker D's "CC BY 4.0" is the site-wide default and **does not apply to this release**: keep ODbL. The OSM and MOSDAC credit lines can now be filled in from the registry and worker D. |

### 1c. Measurements from the real rasters **[my check]**

Method: T55 HH, linear-power block means over 20×20 px (200 m) in the native UTM grid; only blocks valid on all 4 dates (210,112 blocks). "Land" means 16 Oct HH > -12 dB. Sea and river are included in the frame-wide numbers. There is no GSW mask and no reprojection.

| Quantity | 4 Oct (PR) | 16 Oct (PR) | 28 Oct (V1) | 9 Nov (V1) |
|---|---|---|---|---|
| Median HH, all blocks | -7.37 | -7.21 | -7.22 | -8.10 |
| 0.5th percentile HH | -23.9 | -25.8 | **-18.6** | **-19.4** |
| Share of blocks < -18 dB | 28.7% | 24.8% | **1.0%** | 24.1% |
| Water-like blocks (dark on both 4 and 16 Oct), median HH | -19.6 | -19.7 | **-16.9** (wind) | -18.6 |
| Towns, 2 km window (Kakinada / Rajahmundry / Amalapuram / Narsapur) | -1.4 / -0.5 / -5.0 / +0.5 | -1.1 / -0.6 / -5.1 / +0.3 | +0.1 / +0.3 / -4.3 / +1.2 | -1.0 / -0.6 / -5.0 / +1.2 |

| Change on land | Normal 4→16 Oct (12 d) | 16→28 Oct (12 d) | 16 Oct→9 Nov (24 d) | 28 Oct→9 Nov (12 d) |
|---|---|---|---|---|
| Blocks with a drop > 3 dB | 0.2% | 6.8% | **14.8%** | 3.4% |
| Blocks with a rise > 3 dB | 1.1% | 0.8% | 0.4% | 0.3% |
| Land turning water-dark (< -15 dB) | 0.04% | 0.07% | 0.50% | n/a |
| Median change, brightest land (16 Oct > -3 dB) | +0.13 | -1.69 | **-2.06** | n/a |

What this means:
- **There is a clear event signal against the normal fortnight.** The question is what it is. The drop is concentrated in the brightest land, which in the delta is mature paddy canopy. Towns do not drop, so this is not a processing-version artefact. Wind-flattened (lodged) paddy is the physically obvious reading, and it matches news reports of "flattened paddy crops". **Unsure:** harvest, which starts in the first week of November in the eastern delta according to `CROP_CALENDAR_NOTES.md`, would also produce a drop by 9 Nov. Comparing 16 Oct with 9 Nov over 24 days mixes the two causes.
- **The open-water signal is small at this resolution.** It may still be locally important, for example near Narsapur. The headline example in the brief ("38% of the mandal flooded") is **not** what this data looks like. Do not seed the templates with numbers of that size.
- **Ratios to "normal" blow up.** 14.8% against 0.2% is "74×". Plain-language comparisons must use bands, not raw ratios (see section 6).

---

## 2. Gaps for the two-audience requirement

### 2a. Findings layer (laypeople): nothing exists

| Needed | State | Gap |
|---|---|---|
| Classification method with thresholds | **Missing** | No document, no code. Decisions needed: which date pair; per-scene water threshold (from GSW occurrence ≥ 90% pixels, or Otsu per scene, *not* a fixed -18 dB); a change threshold (for example a drop of 3 dB or more after a 5×5 linear speckle filter); a minimum mapping unit; and exclusions (permanent water from GSW, no-data, slopes and layover from `mask`, which was **not saved**). |
| Class definitions that match the physics | **At risk** | The current classes are "likely new open water", "likely wet or flooded crops" and "likely no change". The data suggests a 4th, dominant class: **"likely crops flattened or changed"** (strong brightness drop on vegetated land). L-band HH flooded vegetation usually gets *brighter* (double bounce), not darker. Labelling drops as "wet or flooded crops" is scientifically shaky. Needs a domain call (see S-list and "Unsure"). |
| Per-mandal summary numbers | Sample only | Need: share of the *observed* area per class, ± (from threshold sensitivity), normal-period share with the same method, **coverage %** (the fraction of the mandal with valid data; T55 covers 79 to 83% of the box and the box itself cuts off western West Godavari, for example Bhimavaram), and pixel count. |
| Per-event summaries | Missing | The sea chapter (storm-minus-calm), the "what changed on land" headline, and the delta-wide totals behind the R4 fallback ("delta-wide figures only"). |
| Normal baseline | Defined in the manifest (4→16 Oct), never computed | It is 12 days long while the event pair is 24 days. Either compare 12-day pairs (16→28 Oct, but storm-wet; or 28 Oct→9 Nov) or scale. State this in the "cannot tell" note. Both baseline scenes are PROVISIONAL and the event "after" is V1 (see 1c). |
| Confidence levels | Missing | Need explicit rules (proposal in section 6). |
| Plain-language templates and "what this cannot tell you" | Missing | `strings.en.json` has UI strings only. Templates must be backend data (keys plus parameters) so the brief, the map card and future Telugu all use the same sentences. |
| Traceability | Missing | Every finding needs `evidence[]` pointing at a raw row or file plus the method version. |

### 2b. Raw-data layer (advanced users)

| Needed | State | Gap |
|---|---|---|
| File index with units, CRS, resolution, nodata, encoding | Missing | `_index.json` covers the display PNGs only, and says "not dB". Need `datasets.json` (schema in section 6). |
| Downloadable numbers | Missing | `mandal_stats.csv` and `.json` (per mandal × period × class, with err, coverage and n). Per-scene summary stats (median, percentiles) for the case study. |
| Downloadable rasters | Missing | 300 MB float32 GeoTIFFs cannot go in git (100 MB GitHub limit, `*.tif` ignored). Options: (a) int16 dB×100 COG at 40 m per scene, roughly 10 to 20 MB, attached to a **GitHub Release** (not Pages), or (b) link only to the ASF granule ID plus box plus the script command. Do (b) now and (a) only if time allows. |
| Source granule IDs | In `sources.yaml` and `subset_arnab.py` only | Put them in the manifest and the dataset index (as an `asf_granule` field). |
| Licence and attribution per file | Partly in `manifest.sources[]` | Two `[credit line to confirm]` entries can now be filled. NISAR licence wording: CC0 per NASA policy, per worker D. GSW and IBTrACS sources are absent from `sources[]` although both are used. |
| Units per layer | Free text in `shows` | Add machine fields: `units`, `value_range` or `stretch` (for the legend), `quantity`. |

### 2c. Manifest additions (details in section 6)

`files.findings`, `files.datasets`, `files.templates`; `layers[].dataset_id`, `units`, `stretch`, `finding_ids`; `analyses[].method_id`, `findings_file`, `stats_file`, `coverage_note`; `sources[].licence_url`, `attribution_text`; `events[].landfall.time_window_utc` plus `statement_ref`; and new sources `jrc_gsw` and `ibtracs`. Bump `schema_version` to 3 and extend `tools/check_manifest.py` to match.

---

## 3. Data correctness and consistency risks

| # | Risk | Evidence | Consequence | Fix |
|---|---|---|---|---|
| R1 | **Landfall time** | IMD final (28 Oct press release p1): crossing 02:00–08:00 IST 28 Oct = 20:30 UTC 27 Oct to 02:30 UTC 28 Oct, centre fully inland by 08:00 IST. IBTrACS (JTWC-based, provisional) has first land contact at 15–18 UTC 27 Oct, 50 to 60 km west of IMD. TC advisory 13 p1 "2100–2300 IST 27 Oct" is a unit slip. The 10_UI doc row 11 still cites the IBTrACS time. | **Eye pass 13:01 UTC 27 Oct = 7.5 to 13.5 h before IMD's crossing window** (2 to 5 h before IBTrACS contact). The mockup's "~6 h before landfall" matches neither source. **Coast pass 00:01 UTC 28 Oct = 05:31 IST falls inside IMD's crossing window, with the centre still offshore.** | Use worker C's recommended wording (section E of `docs/workers/C_landfall_evidence.md`). Rename layer `nisar_l_coast_20261028_t55_hh` to "Coast, during landfall (night of 27–28 Oct)". Store `time_window_utc` and no single time. |
| R2 | Same-track comparability | All T55 dates share the exact grid. T48 dates share the exact grid. | Good: no resampling. But **4 and 16 Oct are PR and 28 Oct / 9 Nov are V1**; the dark tail differs by about 5 dB at the 0.5th percentile. | Per-scene water threshold. Optional control: T149 10 Oct (PR) against 22 Oct (V1), both before the storm, to measure the processing-version effect (P2 data, not fetched). |
| R3 | Wind on water on 28 Oct | Water-like blocks at -16.9 dB against about -19.6 dB | Thresholding the 28 Oct pass misses water and reverses the story | Exclude 28 Oct from the water class. Use it only for "storm-time surface". |
| R4 | Harvest and lodging confound | Bright-land drop; harvest window opens early November | "Flood" over-claim | Wording "crops flattened or changed"; a "cannot tell" note naming harvest. Cross-check with a 12-day pair. |
| R5 | Eye location and visibility | No obvious eye disc in a ±45 km scan **[rough check]**; the sea scene covers only about 30% of its box | Chapter 3 numbers may be undeliverable | Look for the eye properly at 100 m (a rain-band and eye pattern may need VV vs calm ratio and a radial profile from several centres). If it is not found by Sun 12:00, ship the storm-minus-calm map plus a "brighter than calm by X dB within N km of the IMD fix" statement and drop the eye radius. |
| R6 | Units and CRS | Rasters are UTM 44N, dB values despite power-style names. Leaflet `imageOverlay` assumes Web Mercator. UTM grid convergence at 82.6 E is about 0.45°, so placing a UTM image with lat/lon bounds misplaces edges by roughly 0.5 to 0.8 km. | Class pixels misaligned with mandal outlines | **Warp to EPSG:3857** (or 4326 for small extents) before writing PNGs; write bounds from the warped raster. |
| R7 | Licences | NRSC/Bhoonidhi: derived products only, licence unconfirmed. MOSDAC: link-only (value-added products allowed but the plan keeps a link). IMD: "do not re-host PDFs" (registry). IMD API: whitelisted IP only, impossible from a static page. SACHET: feed says "public domain". GDACS terms unread. Esri basemap free use unconfirmed. | Re-hosting IMD PDFs in a public repo or on Pages breaches the registry rule | Keep `docs/imd_bulletins/` out of git (add it to `.gitignore`; record the source URLs instead). Quote facts with page references. |
| R8 | CORS for live feeds | Registry curl test: `Access-Control-Allow-Origin: *` on GIBS, Open-Meteo marine and flood, and GDACS. SACHET none. Never tested from the deployed origin. | Live strips fail silently | Snapshot-first (already the design). Test from github.io after deploy. |
| R9 | Alerts timing | SACHET RSS keeps about 4 days. The current snapshot has no AP items. | An "official alerts" strip presented next to Arnab would be either fake (sample) or unrelated (today's Rajasthan alerts) | Label it plainly as "today's official alerts (not from Arnab's time)" with `filter` applied, **or** replace the event-time strip with IMD bulletin headlines quoted with page references. Never mix the two. |
| R10 | Mandal identity | Names are not unique (two Yelamanchili). 2018 boundaries against 2022 districts. Polavaram district was created in Dec 2025. | Wrong rows or joins | Key everything on `shapeID`; show the 2022 district; note that boundary vintage is 2018. |
| R11 | Box clipping | The delta box (81.6 to 82.6 E) cuts western West Godavari (Bhimavaram is outside). The T55 frame covers 79 to 83% of the box. | Rankings imply full mandals | Per-mandal `coverage_pct`; hide a ranking below 60% coverage. |
| R12 | Sample values leaking | `profile.json` "+6.2 dB" happens to be close to the real median storm-minus-calm (+6 dB), which makes a sample look real | False credibility | Keep the tags until replaced. Never copy sample numbers into the submission text (`PROJECT_PAGE_DRAFT.md` already marks them `[TBD]`). |

---

## 4. Fit with static hosting (GitHub Pages, no server)

- **Sizes:** `data/processed` is 4.0 MB and the app 0.56 MB, so first load is about 1.8 MB (under the 15 MB budget). Adding real PNGs: 8 greyscale at ≤ 600 KB plus 3 or 4 paletted class PNGs at ≤ 150 KB plus 1 difference map, about 6 MB in total. `findings.json` for 146 mandals × about 4 findings × about 1 KB is about 0.6 MB raw and about 80 KB gzipped (Pages gzips JSON). Fine. **Split** it: `findings_event.json` (small, loaded at start) and `findings_mandal.json` (lazy-loaded when a mandal is opened), or keep one file if it is under 300 KB.
- **Formats:** greyscale 8-bit PNG with the dB stretch recorded in the manifest (for example -25 to 0 dB mapped to 0 to 255, so a raw user can invert pixel values; say so in `datasets.json`). Class maps as **paletted PNG** with alpha. Statistics as JSON plus the same as CSV for download. No GeoTIFF on Pages.
- **Caching:** Pages sends `Cache-Control: max-age=600`. Add a `?v=<generated_utc>` query from the manifest to the data URLs so a re-run is picked up. `core.js` already caches the last-seen manifest time in localStorage. Fine.
- **Fail-soft:** `core.js` wraps the fetch in try/catch, and the alerts and live layers fall back to text. Gaps: (1) if `findings.json` is missing, the lay view must fall back to "Numbers not ready, here is the radar" and **never** to raw dB; (2) the app needs CDN libraries (Leaflet, Chart.js, Scrollama, Google Fonts), so there is **no offline use** (BACKEND_GAPS item 12). For the demo, vendor Leaflet and Chart.js into `app/vendor/` (15 min, about 0.4 MB).
- **Untracked data:** `data/interim/C/*`, `docs/workers`, `docs/submission` and new scripts are untracked. Commit the small ones. Do **not** `git add docs/imd_bulletins` (R7) or `data/browse/nisar_arnab` (60 MB of quick-looks).

---

## 5. Prioritised punch list

Effort is for one competent person who already has a Python environment with rasterio, pyproj and scipy. **This VM has only numpy and PIL, and `.venv` is empty.** The machine that produced the GeoTIFFs must do the pipeline work. **Unsure:** which machine and person that is. Budget roughly 30 min to set up an environment if it has to be rebuilt.

Two paths, to be chosen by about 17:00 IST Sat:
- **Option A (full):** M1 to M12. About 16 to 18 h.
- **Option B (safe):** M1, M2, M4b, M5 (brightness-change wording only), M6 to M12. About 10 to 12 h. The findings speak of "radar brightness changed strongly / normally", not flood shares.

### MUST (before 15 Nov 23:59 IST)

| # | Task | Effort | Files | Acceptance check |
|---|---|---|---|---|
| M1 | Bring the docs in line with reality: the NISAR rasters exist. Set `status: done` in `sources.yaml` for the 7 subset scenes; add a "superseded" header to `BACKEND_GAPS.md` §1 and `PLACEHOLDERS.md` §1–2; write `data/logs/nisar_l_subset.md` (granule ID, sha256, size, grid, valid %, units dB, "mask not saved", "VH not saved") | 40 min | `data/sources.yaml`, `docs/BACKEND_GAPS.md`, `docs/PLACEHOLDERS.md`, new `data/logs/nisar_l_subset.md` | `grep blocked_credentials data/sources.yaml` lists only S-band, 3 Oct and T149; the log has 14 sha256 lines |
| M2 | **Real greyscale dB PNGs**: warp each GeoTIFF to EPSG:3857, stretch HH -25..0 and VV -25..0 dB to 8-bit, crop to the AOI, ≤ 1400 px; write true bounds; set `placeholder: null` and `bounds_inferred: false`. Replace the 3 Oct sea layer with `status: unavailable` (no GeoTIFF) | 2 h | `tools/make_web_assets.py` (or a new `src/analysis/export_png.py`), `data/processed/img/nisar_l_*.png`, `manifest.json` layers | `check_manifest.py --files` passes; every NISAR PNG ≤ 600 KB; the Godavari mouth and coastline in the PNG line up with `coastline_osm_clip.geojson` within about 2 px at zoom 11 (visual check); `_index.json` no longer says "display only" |
| M3 | **Freeze the method** (human plus backend, 1 h meeting): pairs = normal 4→16 Oct, event 16 Oct→9 Nov (plus 16→28 Oct for "storm-time"); per-scene water threshold = 5th percentile of HH over GSW occurrence ≥ 90% pixels, plus 2 dB; change threshold = drop or rise ≥ 3 dB after a 5×5 linear mean; exclude GSW ≥ 50% from change classes; minimum unit 0.5 ha; class set (decide whether "wet or flooded crops" becomes "crops flattened or changed"). Write it down | 1 h decision + 30 min doc | new `docs/METHOD.md` (method_id `delta-change-v1`) | The document lists every threshold with a number, its origin, and one line on its limit; the decision-maker's name and time are recorded |
| M4 | **Class rasters plus per-mandal statistics** by the M3 method: rasterise mandals on the UTM grid by `shapeID`; per mandal and pair compute class shares of the *valid* area, coverage %, n pixels, and ± as half the range over threshold ±1 dB (and change threshold 2 to 4 dB). Same for the normal pair. Write `mandal_stats.json` and `.csv` (raw) and regenerate `mandal_rank.json` (keep its shape, add `shapeID`, `coverage_pct`) | 3 h code + about 20 min compute | new `src/analysis/classify_delta.py`, `data/processed/mandal_stats.json`, `.csv`, `mandal_rank.json`, `img/class_20261109_*.png` | Rows = mandals with coverage ≥ 20%; `water_pct` for the normal pair is near 0 on dry inland mandals; the sum over classes plus unclassified = 100 ± 0.1; the class PNGs are paletted, ≤ 150 KB, same bounds as M2 |
| M4b | (Option B) Brightness-change statistics only: per mandal, % of land with a drop ≥ 3 dB and a rise ≥ 3 dB, event against normal, with threshold sensitivity | 1.5 h | as M4 | as M4 |
| M5 | **Findings generator**: reads `mandal_stats.json` plus `METHOD.md` parameters plus `templates.en.json`; writes `findings.json` (schema in section 6) with confidence rules and `evidence[]` references | 2.5 h | new `src/analysis/make_findings.py`, `data/processed/findings.json`, `data/processed/templates.en.json` | Every finding has `confidence.level`, ≥ 1 `cannot_tell` entry and ≥ 1 resolvable `evidence.ref`; a script check confirms each `evidence.ref` resolves to a row or file that exists; no finding text contains "dB" (lay text) |
| M6 | Promote the complete mandal→district mapping; key on `shapeID`; fix Yelamanchili; regenerate `mandals.geojson` | 45 min | `data/reference/mandal_district_2022.csv` (replace from `data/interim/C/..._complete.csv`), `tools/make_web_assets.py`, `data/processed/mandals.geojson` | `district: null` count ≤ 4; no duplicate `shapeID`; regions `konaseema`, `west_godavari`, `kakinada` plus a new `east_godavari` region resolve |
| M7 | Landfall: a human picks wording (worker C §E); set `landfall.time_window_utc: ["2026-10-27T20:30Z","2026-10-28T02:30Z"]`, keep `time_utc: null`; rename the 28 Oct layer; fix "~6 h before" copy | 20 min | `manifest.json`, `app/strings/*.json`, `docs/handoff/10_UI_DIRECTION_AND_RISKS.md` (copy only) | `grep -ri "4 hours after\|6 h before" data app` returns nothing |
| M8 | Alerts decision: either (a) ship `interim/C/alerts.json` run with `--filter` and the label "today, not Arnab-time", or (b) keep the sample tag and add IMD bulletin headline quotes as the event-time strip | 30 min | `data/processed/alerts.json`, `manifest.json` (layer `alerts_sachet_snapshot`) | The strip never shows sample text without a tag; `saved_at_ist` matches the file's real save time |
| M9 | Sea difference PNG (27 Oct minus 15 Oct VV, linear 3×3 then dB, diverging -6..+12 dB) plus per-ring statistics around the IMD 13:01 position | 1 h | `img/nisar_sea_diff_20261027_vs_20261015.png`, `profile.json` | `profile.json` `placeholder` off; if no eye was found, `eye: null` and `eye_radius_km: null` with `note`; the frontend hides the radius tile when it is null (check `case.js`: **unsure** whether it handles null) |
| M10 | **Raw index** `datasets.json`: one entry per raster, table and vector (section 6), with ASF granule IDs, units, CRS, licence and download mode | 1.5 h | new `data/processed/datasets.json`, `manifest.json` (`files.datasets`, `layers[].dataset_id`) | The checker validates that every `dataset_id` exists and every `files[].path` exists or has an external URL |
| M11 | Credits and licences: fill OSM ("© OpenStreetMap contributors", ODbL) and MOSDAC ("Data Source MOSDAC/SAC/ISRO"); keep geoBoundaries **ODbL** (per meta file); add `jrc_gsw` and `ibtracs` sources; change the NISAR licence line to the NASA CC0 wording with no endorsement | 20 min | `manifest.json` `sources[]`, `docs/PLACEHOLDERS.md` §6 | No `[credit line to confirm]` left; `credit_confirmed:false` only on SACHET and GDACS |
| M12 | Keep IMD PDFs out of git; record their source URLs | 10 min | `.gitignore`, `data/logs/B_imd.md` | `git check-ignore docs/imd_bulletins/x.pdf` succeeds |

### SHOULD (if time remains on Sunday)

| # | Task | Effort | Files | Acceptance |
|---|---|---|---|---|
| S1 | Extend `check_manifest.py` for schema v3 (findings, datasets, units, evidence refs) | 1 h | `tools/check_manifest.py` | All new checks PASS; a deliberately broken ref FAILS |
| S2 | Commit `data/processed`, small `data/interim/C/*.csv/json`, `docs/workers`, `docs/submission`, new scripts; enable Pages; test GDACS and Open-Meteo CORS from github.io in Chrome and Safari | 45 min | repo | The live strip says "live" on the deployed page, or falls back with a dated note |
| S3 | Pick and confirm the Open-Meteo points (sea off Narsapur, Godavari at Dowleswaram on the GloFAS grid) | 30 min | `manifest.json` `config` | `coordinates_confirmed: true` with a note giving the GloFAS cell |
| S4 | Cross-check findings against an independent source: Daily Pioneer district paddy-inundation % and VIIRS cloud-free patches; attach as `corroboration` | 45 min | `findings.json` | Each district finding has 0 or 1 corroboration reference with URL and date, and the sources are not mixed |
| S5 | Vendor Leaflet and Chart.js for offline demo | 15 min | `app/vendor/`, `app/index.html` | The page works with the network cut except basemap and live feeds |
| S6 | Human look at Bhoonidhi guest catalogue and ROP for S-band over the box (16 Oct to 10 Nov); record the result | 30 min (Sachin/Guneesh) | `docs/PLACEHOLDERS.md`, `manifest.json` note | A recorded "no scene" or a scene ID |
| S7 | Save `mask` and `numberOfLooks` for the T55 scenes (re-run the subset for those layers only) and apply the layover/shadow/invalid mask | 1 h plus streaming | `src/fetch/subset_arnab.py` run, M4 | Masked pixel % is reported per mandal |

### LATER (after the hackathon; say so honestly in the submission)

T149 PR-vs-V1 control pair; a VH or HV-based crop-structure class; COG downloads as Release assets; a refresh pipeline (ASF search, then subset, then findings, then manifest) as a GitHub Action; LGD boundaries in place of 2018 geoBoundaries; Telugu templates; an aquaculture-pond mask (ponds change constantly in this delta and will pollute "new water"); SCAT-3 or ASCAT wind for a quantitative sea-roughness to wind link.

---

## 6. Proposed schema: findings layer, raw index, manifest changes

### 6a. `data/processed/findings.json` (example; the **numbers are illustrative only**)

```json
{
  "schema": "findings/1",
  "generated_utc": "2026-11-15T06:00:00Z",
  "analysis_id": "ap_delta_oct_nov_2026",
  "method": {"id": "delta-change-v1", "doc": "docs/METHOD.md", "code": "src/analysis/classify_delta.py", "code_commit": "<git sha>"},
  "placeholder": null,
  "confidence_rules": {
    "high":   "coverage >= 90% AND signal outside the threshold-sensitivity range AND event share >= 3x normal share AND (corroborated OR both scenes same processing level)",
    "medium": "coverage >= 60% AND signal outside the sensitivity range",
    "low":    "otherwise; shown greyed, never ranked",
    "none":   "coverage < 20%: no finding issued"
  },
  "comparison_bands": [
    {"id": "much_more", "min_ratio": 3,   "text_key": "cmp.much_more"},
    {"id": "more",      "min_ratio": 1.5, "text_key": "cmp.more"},
    {"id": "similar",   "min_ratio": 0.67, "text_key": "cmp.similar"},
    {"id": "less",      "min_ratio": 0,   "text_key": "cmp.less"}
  ],
  "ratio_floor_pct": 1.0,
  "event_findings": [
    {
      "id": "evt.land_change",
      "subject": {"type": "region", "id": "konaseema"},
      "topic": "crops_changed",
      "headline": {"key": "f.crops_changed.region", "params": {"share_pct": 15, "share_err": 4, "band": "much_more"}},
      "plain": "Radar shows the crop canopy changed sharply on about 15% (±4) of the farmland it could see, far more than in a normal fortnight. This fits crops flattened by wind or harvested.",
      "value": {"quantity": "share_of_observed_land", "class": "drop_ge_3db", "value": 15.0, "err": 4.0, "unit": "%", "period": ["2026-10-16", "2026-11-09"]},
      "baseline": {"value": 0.2, "err": 0.2, "unit": "%", "period": ["2026-10-04", "2026-10-16"], "note": "normal pair is 12 days, event pair 24 days"},
      "comparison": {"band": "much_more", "ratio": null, "ratio_suppressed_reason": "baseline below ratio_floor_pct"},
      "confidence": {"level": "medium", "reasons": ["coverage_81pct", "processing_level_mixed", "no_ground_truth"], "plain": "Medium: the change is clear, but radar cannot tell flattening from harvesting."},
      "cannot_tell": [
        {"key": "ct.cause", "plain": "Whether the change is storm damage, harvest, or both."},
        {"key": "ct.depth", "plain": "Water depth, or how long fields stayed wet."},
        {"key": "ct.loss", "plain": "Crop loss in tonnes or rupees."}
      ],
      "evidence": [
        {"ref": "mandal_stats.json#/regions/konaseema/pairs/event/drop_ge_3db", "role": "value"},
        {"ref": "mandal_stats.json#/regions/konaseema/pairs/normal/drop_ge_3db", "role": "baseline"},
        {"dataset_id": "nisar_l_coast_20261016_t55_hh_db", "role": "input"},
        {"dataset_id": "nisar_l_coast_20261109_t55_hh_db", "role": "input"}
      ],
      "layer_ids": ["nisar_class_crops_changed", "nisar_l_coast_20261109_t55_hh"],
      "corroboration": [{"source": "Daily Pioneer, 29 Oct 2026", "url": "https://dailypioneer.com/...", "says": "Konaseema paddy-area inundation about 75% (preliminary, news)", "agrees": "partly"}]
    }
  ],
  "mandal_findings_file": "data/processed/findings_mandal.json"
}
```

`findings_mandal.json`: `{ "<shapeID>": { "mandal": "Narasapuram", "district": "West Godavari", "coverage_pct": 94, "rank": 3, "findings": [ <same finding object, subject.type "mandal"> ] } }`. Topics per mandal: `open_water_new`, `crops_changed`, `no_change`, and `data_gap` (issued when coverage < 60%, so the lay view can say "the radar did not see most of this mandal").

Rules the generator enforces:
1. Lay text has no units other than % and km and no jargon ("backscatter", "dB", "HH"); those belong only in `value`.
2. Numbers in lay text are rounded: < 10% to the nearest 1, ≥ 10% to the nearest 5, and always with ±.
3. Ratios are shown only when the baseline is ≥ `ratio_floor_pct`; otherwise only the band word is shown.
4. "likely" or "probably" starts every class phrase.
5. `plain` is always the template rendered with `params`, so Telugu can render from the same key.

### 6b. `data/processed/templates.en.json` (excerpt)

```json
{
  "f.open_water_new.mandal": "Probably new open water on about {share_pct}% (±{share_err}) of the land radar could see in {mandal}. That is {band_text} a normal fortnight.",
  "f.crops_changed.mandal": "Crops probably flattened or changed on about {share_pct}% (±{share_err}) of {mandal}'s visible farmland, {band_text} a normal fortnight.",
  "f.data_gap.mandal": "The radar saw only {coverage_pct}% of {mandal}, too little to say what changed.",
  "cmp.much_more": "far more than in",
  "cmp.more": "more than in",
  "cmp.similar": "about the same as in",
  "cmp.less": "less than in",
  "conf.high": "High confidence", "conf.medium": "Medium confidence", "conf.low": "Low confidence: treat as a hint",
  "ct.cause": "Whether the change is storm damage, harvest, or both.",
  "ct.depth": "Water depth, or how long fields stayed wet.",
  "ct.single_date": "Anything that happened between the radar passes (12 days apart)."
}
```

### 6c. `data/processed/datasets.json` (raw index, one entry shown)

```json
{
  "schema": "datasets/1",
  "datasets": [{
    "id": "nisar_l_coast_20261109_t55_hh_db",
    "title": "NISAR L-band HH backscatter, Godavari delta box, 9 Nov 2026 00:01 UTC",
    "kind": "raster", "quantity": "gamma0 (RTC), HH", "units": "dB", "value_encoding": "float32 dB; NaN = no data",
    "crs": "EPSG:32644", "resolution_m": 10, "grid": {"origin_xy": [563830, 1891320], "size": [10720, 10017]},
    "bounds_wgs84": [[16.2, 81.6], [17.1, 82.6]], "valid_pct_of_box": 80.7,
    "time_utc": "2026-11-09T00:01:07Z", "track": 55, "frame": 10, "direction": "ascending",
    "processing_level": "validated (GCOV_V1)",
    "asf_granule": "NISAR_L2_PR_GCOV_035_055_A_010_4005_DHDH_A_20261109T000107_20261109T000130_P05036_N_P_J_001",
    "derived_by": {"script": "src/fetch/subset_arnab.py", "command": "python src/fetch/subset_arnab.py --ids L_COAST_1109", "sha256": "<from log>"},
    "source_id": "asf_nisar_l", "licence": "NASA data policy: CC0 unless marked; no endorsement implied", "credit": "NISAR L-band data: NASA/JPL-Caltech and ISRO, via ASF DAAC. Processed by SpaceBros.",
    "files": [
      {"role": "display", "path": "data/processed/img/nisar_l_coast_20261109_t55_hh.png", "format": "PNG 8-bit, EPSG:3857", "stretch_db": [-25, 0], "bytes": null},
      {"role": "source", "url": "https://search.asf.alaska.edu/#/?searchType=List%20Search&searchList=<granule>", "format": "HDF5 (login)", "note": "full product, 4 GB"},
      {"role": "download", "url": null, "format": "COG int16 dB*100, 40 m", "status": "later"}
    ],
    "known_limits": ["mask layer not saved: layover/shadow not excluded", "VH/HV only for coast scenes"]
  }],
  "tables": [{"id": "mandal_stats", "path": "data/processed/mandal_stats.csv", "columns": [
    {"name": "shapeID"}, {"name": "pair", "values": ["normal", "event", "storm"]}, {"name": "class"},
    {"name": "share_pct", "unit": "% of valid area"}, {"name": "share_err", "unit": "± percentage points (threshold sensitivity)"},
    {"name": "coverage_pct", "unit": "% of mandal area with valid data"}, {"name": "n_pixels"}]}]
}
```

### 6d. `manifest.json` changes (schema v3)

| Where | Add or change | Why |
|---|---|---|
| top | `schema_version: 3`; `files.findings`, `files.findings_mandal`, `files.templates`, `files.datasets`, `files.mandal_stats` | The two layers and the templates |
| `layers[]` | `dataset_id`, `units`, `stretch: {min, max, unit}`, `finding_ids[]`; for classes `class_id` must match `findings` topics | Legend values and traceability |
| `layers[]` | Rename the 28 Oct layer; remove the 3 Oct layer or set it `unavailable`; add `nisar_class_crops_changed` if M3 says so | R1, R4 |
| `analyses[]` | `method_id`, `stats_file`, `findings_file`, `pairs: {normal:[...], event:[...], storm:[...]}`, `coverage_min_pct: 60` | Findings generator input |
| `events[].landfall` | `time_window_utc`, `statement_ref: "docs/workers/C_landfall_evidence.md#E"`, `alt_sources: [{source:"IBTrACS", first_contact_utc:["2026-10-27T15:00Z","2026-10-27T18:00Z"]}]` | Honest, one-click traceable |
| `sources[]` | `licence_url`, `attribution_text`; new `jrc_gsw`, `ibtracs` | Raw audience |
| `regions[]` | Add `east_godavari` once M6 is done | 20 mandals currently unreachable |
| checker | Validate all of the above (S1) | Prevents silent drift |

---

## 7. Things I am not sure of (do not treat as facts)

- What the 3 dB drop over bright land really is (lodging, harvest, saturated soil, or an RTC/processing quirk in bright vegetation). Towns argue against a processing cause, but this needs a radar person's judgement.
- Whether the eye is visible in the 100 m VV at all. My scan was coarse (3 km blocks) and centred on an interpolated IMD position.
- Whether `case.js` and `panels.js` handle `null` eye values and missing findings gracefully. I did not test the frontend.
- Which machine and person ran `subset_arnab.py` (the files appeared between 08:56 and 09:15 UTC today), and whether that environment is still available for M2 to M4.
- The SACHET licence ("public domain" is the feed's own `<copyright>` tag; NDMA terms unread), GDACS re-hosting, the Esri basemap terms and the Bhoonidhi S-band licence.
- The GSW version (the file is v1.4/2021 and the registry says v1.5/2024). It does not matter for the method, but the stated version must match the file used.

## 8. Things worth remembering

- The T55 and T48 subsets are pixel-aligned across dates; no co-registration step is needed.
- The 28 Oct coast pass is wind-contaminated for water detection.
- The geoBoundaries IND ADM3 release is ODbL (meta file), not CC BY.
- SACHET RSS keeps only about 4 days; event-time alerts must be snapshotted during the event.
