# Fetch tasks for parallel agents (no-login sources only)

Planner: 14 Nov 2026 ~09:00 IST. Full context: `docs/DATA_ACQUISITION_PLAN.md`; source list: `data/sources.yaml`.
Five independent packages, A–E. They share no files except `data/sources.yaml` (each package edits only its own entries' `status`).

## Rules for every package (read before starting)

1. **Never fabricate data.** Do not invent URLs, scene ids, coordinates, times, track points or numbers. If something cannot be fetched, leave it missing and say so in the log. Typed values (track CSV) must each cite the PDF + page they came from.
2. **No logins.** If a step turns out to need an account (Earthdata, Bhoonidhi, MOSDAC, anything), stop that step, set the entry's status to `blocked_credentials`, note it in the log. Never create accounts or ask for passwords.
3. Work in the repo root `$HOME/mnt/nsa/05_Code/spacebros-nisar` (device shell). Use a venv: `python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt geopandas shapely pyyaml` (only if the package needs those libs; `.venv/` is ignored; if another package already made it, reuse it).
4. Put any script you write in `src/fetch/<package>_*.py` (tracked) so the fetch is reproducible. Do not modify existing files in `src/`, `app/`, `notebooks/` or the master plan.
5. Deleting files is not permitted on this mount: write to a temp name and `mv` over it if you must replace something.
6. Host notes (probed): device shell reaches GIBS, CMR, ASF search API, geoBoundaries, github, storage.googleapis.com, naciscdn, osmdata (file URLs), rsmcnewdelhi.imd.gov.in, mausam.imd.gov.in, open-meteo, pypi. It does **not** reach www.spaceappschallenge.org or www.mosdac.gov.in – use WebFetch/WebSearch (or the built-in browser) for those, and save what you learn as text with URLs.
7. Finish with **`data/logs/<package>.md`** containing: date/time, every file written (path, bytes, `sha256sum`), every URL used, every failure with the HTTP code/error, what is still missing, and the `status` you set in `sources.yaml`. Then stop.
8. Time box: 60 min per package. If not done, write the log with what exists and stop.

---

## Package A – NASA GIBS imagery (chapter 1 "From above", rain, cloud-top IR)

**Goal:** static, georeferenced snapshots for the page and the layer ids/templates for Leaflet. Sources `GIBS_VIIRS_TC`, `GIBS_IMERG`, `GIBS_HIMAWARI_IR` (urgent: rolling archive), `GIBS_VIIRS_I5_NIGHT`, `GIBS_REF`.

**Steps**
1. Download capabilities once: `curl -s https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/1.0.0/WMTSCapabilities.xml -o /tmp/caps.xml`. For each layer below, confirm the Identifier exists and that the requested date/time lies inside one of its `<Value>` time ranges; record layer id, format, TileMatrixSet and the matching time range in `data/reference/gibs_layers.json` (also the Leaflet template `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/{layer}/default/{time}/{tms}/{z}/{y}/{x}.{jpg|png}`).
   Layers verified by the planner: `VIIRS_SNPP_CorrectedReflectance_TrueColor`, `VIIRS_NOAA20_CorrectedReflectance_TrueColor`, `VIIRS_NOAA21_CorrectedReflectance_TrueColor` (jpeg, Level9), `IMERG_Precipitation_Rate` (daily png, Level6), `IMERG_Precipitation_Rate_30min` (png, Level6), `Himawari_AHI_Band13_Clean_Infrared` (png, Level6, 10-min), `VIIRS_SNPP_Brightness_Temp_BandI5_Night`, `VIIRS_NOAA20_Brightness_Temp_BandI5_Night`, `Coastlines_15m`, `Reference_Labels_15m`.
2. WMS GetMap (EPSG:4326, WMS 1.3.0 axis order = lat,lon):
   `https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi?SERVICE=WMS&REQUEST=GetMap&VERSION=1.3.0&LAYERS=<layer>&CRS=EPSG:4326&BBOX=<S>,<W>,<N>,<E>&WIDTH=<w>&HEIGHT=<h>&FORMAT=<image/jpeg|image/png>&TIME=<time>`
   Boxes: context 78,12,88,20 (2000×1600 px), sea 81,15,85,18 (1600×1200), delta 81.6,16.2,82.6,17.1 (1000×900).
   - Himawari B13 **first**: TIME `2026-10-27T12:50:00Z`, `T13:00:00Z`, `T13:10:00Z`, `2026-10-28T00:00:00Z`; boxes context + sea.
   - VIIRS true colour, 3 satellites × dates 2026-10-26, -27, -28, -29 × boxes context + sea + delta (jpeg).
   - IMERG daily 2026-10-26..29 (context, sea); IMERG 30 min `2026-10-27T12:30:00Z`, `T13:00:00Z`, `T13:30:00Z`, `2026-10-28T00:00:00Z` (context, sea).
   - P2: I5 night for 2026-10-27 (context); Coastlines_15m and Reference_Labels_15m (no TIME) for context + sea + delta.
3. Filenames: `data/raw/gibs/<short>_<time>_<box>.<ext>` e.g. `viirs_snpp_truecolor_2026-10-27_sea.jpg`, `himawari_b13_20261027T1300Z_sea.png`. For each image write `<same>.json`: `{"layer","time","bbox_wsen","crs":"EPSG:4326","width","height","url","fetched_utc"}`.
4. Pick the best VIIRS image for 27 Oct (the satellite whose swath fully covers the storm) and note it in the log – do not judge visually beyond "nodata stripes present yes/no" from pixel statistics.

**Verify:** each file opens with PIL; size > 2 KB; pixel std > 5 (jpeg) or alpha not all 0 (png); Himawari 13:00Z std > 20 (planner probe: 94). A WMS XML error (`ServiceException`) saved as an image = failure.
**On failure:** retry once with WMTS tiles at zoom 6 (Level6/Level9 layers) stitched with PIL; if a time is outside the layer's range, log it and skip. Never substitute another date silently.
**Log:** `data/logs/A_gibs.md`. Update statuses of the GIBS_* entries.

---

## Package B – IMD / RSMC New Delhi bulletins, landfall statement, typed track CSV

**Goal:** the official record of Cyclone Arnab: bulletins nearest 12 and 15 UTC on 27 Oct, the landfall statement (28 Oct), any preliminary report / best track, and a typed track CSV. Sources `IMD_BULLETINS`, `IMD_TRACK_CSV`.

**Steps**
1. Start at https://rsmcnewdelhi.imd.gov.in/ (reachable from the shell). Known pages: Bulletins `report.php?internal_menu=MzQ=`, Preliminary report `report.php?internal_menu=MjY=`, Best track `report.php?internal_menu=MzM=` – each lists items only after selecting a year (HTML form, `method="post"`, field `search_year`; a bare `curl -d search_year=2026` did not show items to the planner, so use the built-in browser or inspect `js/custom.js` / the form's submit button name). Also: satellite bulletins `archive-information.php?internal_menu=MjI=&menu_id=OQ==` (routine) and `archive-information.php?internal_menu=NzM=&menu_id=OQ==` (special); downloads are `download.php?path=uploads/...`. Also check https://mausam.imd.gov.in/ press releases / "Cyclone" section for 27–28 Oct 2026.
2. If the IMD site gives nothing for Arnab, use WebSearch for "Cyclone Arnab IMD bulletin 27 October 2026" and fetch only **IMD-hosted** PDFs (imd.gov.in domains). News articles may be listed in the log as secondary context but never typed into the CSV.
3. Save PDFs to `docs/imd_bulletins/<YYYYMMDD>_<HHMM>UTC_<type>.pdf` (`type` = national_bulletin, tc_advisory, landfall_press_release, prelim_report, best_track, sat_bulletin). Keep the original URL in the log.
4. Type the fixes into `data/reference/imd_track_arnab.csv` with columns
   `time_utc,lat_n,lon_e,category,max_wind_kt,max_wind_kmh,central_pressure_hpa,source_pdf,page,note` – one row per fix stated in a PDF (no interpolation in this file; leave unknown cells empty). Add a separate row type `note=landfall` with the landfall time/position exactly as IMD states it (planner expects ~16.45N 81.90E near Narsapur – confirm or correct, never copy the expectation).
5. Copy the exact landfall sentence into the log as a quote.

**Verify:** PDFs open (`python -c "import pypdf"` or `pdftotext` if available) and contain "ARNAB"; CSV parses; lat 10–20, lon 80–90; times increasing; every row has source_pdf + page.
**On failure:** if no IMD PDF is reachable, write the log with what was tried and set status `pending` with a note "needs human: open IMD site in a normal browser". Do not build a track from news.
**Log:** `data/logs/B_imd.md`.

---

## Package C – Boundaries, permanent water, coastline

**Goal:** mandal + district outlines, a permanent-water mask and coastlines clipped to the study region. Sources `GB_ADM3`, `GB_ADM2`, `JRC_GSW`, `NE_COAST`, `OSM_COAST` (P1).

**Steps**
1. geoBoundaries: `curl -s https://www.geoboundaries.org/api/current/gbOpen/IND/ADM3/` → read `gjDownloadURL` (planner saw `https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/IND/ADM3/geoBoundaries-IND-ADM3.geojson`, 106 MB, ODbL 1.0, boundary year 2018). `curl -L -o data/raw/boundaries/geoBoundaries-IND-ADM3.geojson <url>`. Same for ADM2 (year 2021). Save the two API JSON responses to `data/reference/geoboundaries_meta_ADM{2,3}.json` (licence evidence).
2. Clip with geopandas to box 81.0,15.8,83.0,17.6 (keep polygons that intersect; do not cut them): write `data/reference/mandals_delta.geojson` and `data/reference/districts_delta_gb2021.geojson` (EPSG:4326, keep `shapeName`, `shapeID`, add `area_km2` computed in EPSG:32644). Also a CSV `data/reference/mandals_delta_list.csv` (shapeID, shapeName, parent ADM2 name via spatial join on representative point, area_km2, frac_inside_delta_box).
3. JRC GSW: `curl -o data/raw/water/occurrence_80E_20Nv1_4_2021.tif https://storage.googleapis.com/global-surface-water/downloads2021/occurrence/occurrence_80E_20Nv1_4_2021.tif` (28 MB). Window-read box 81.0,15.8,83.0,17.6 with rasterio, write `data/interim/gsw_occurrence_delta.tif` (deflate) and a preview `data/interim/gsw_occurrence_delta_preview.png` (not tracked if tif; PNG is fine).
4. Natural Earth: `curl -L -o data/raw/coast/ne_10m_coastline.zip https://naciscdn.org/naturalearth/10m/physical/ne_10m_coastline.zip`; clip to context box 78,12,88,20 → `data/reference/coastline_ne10m_clip.geojson`.
5. P1 OSM: `https://osmdata.openstreetmap.de/download/coastlines-split-4326.zip` and `.../land-polygons-split-4326.zip` (large; read with `geopandas.read_file("zip://...", bbox=(78,12,88,20))`) → `data/reference/coastline_osm_clip.geojson`, `data/reference/land_osm_clip.geojson`.

**Verify:** CRS EPSG:4326; mandal clip has ≥ 30 features and names include coastal mandals of the delta (check that "Narsapur"/"Narasapuram" or similar is present and log the exact spelling found); GSW clip values 0–100 (255 = nodata), main Godavari channels > 80; coastline clip non-empty. Each reference file < 5 MB (simplify with tolerance 0.0005° if larger and say so).
**On failure:** geoBoundaries → try `simplifiedGeometryGeoJSON` from the API; GSW → log, the fallback is GIBS `OSM_Land_Water_Map` (human decision). Never draw boundaries by hand.
**Log:** `data/logs/C_boundaries_water.md` including the licence lines to cite (ODbL for geoBoundaries/OSM; JRC/Google GSW citation Pekel et al. 2016; Natural Earth public domain).

---

## Package D – ASF / CMR metadata: final scene manifest (no data download)

**Goal:** a definitive scene-id manifest so the human's Earthdata run is mechanical. Sources `ASF_MANIFEST`, `NISAR_BROWSE_NEW`, `NISAR_S_CMR_CHECK`. Search needs no login; HDF5 downloads do (do not attempt them).

**Steps**
1. Query the ASF search API for GCOV, 2026-10-01 → 2026-11-14, twice: delta box polygon `POLYGON((81.6 16.2,82.6 16.2,82.6 17.1,81.6 17.1,81.6 16.2))` and sea box `POLYGON((81 15,85 15,85 18,81 18,81 15))`:
   `curl -s "https://api.daac.asf.alaska.edu/services/search/param?dataset=NISAR&processingLevel=GCOV&intersectsWith=<urlencoded WKT>&start=2026-10-01T00:00:00Z&end=2026-11-14T23:59:59Z&maxResults=1000&output=geojson"` (or `asf_search` in the venv with `TZ=UTC`).
2. For each granule compute the fraction of the box covered by its footprint polygon (grid of points, as the planner did in `data/reference/asf_probe_delta_box_20261001_20261114.csv`). Write `data/reference/scene_manifest.csv` with columns `role,start_time,track,frame,direction,product_type(PR|UR),mode,pols,crid,collection,frame_coverage,box,box_cover_frac,size_gb,file_id,h5_url,browse_url,md5`.
   Fill `role` only for the planner's chosen scenes (L_SEA_CALM_1015, L_SEA_EYE_1027, L_COAST_1004/1016/1028/1109, L_SEA_AFTER_1108, L_SEA_CALM_1003, L_COAST_T149_*) and check each `file_id` in `src/fetch/subset_arnab.py` matches a row exactly. Any mismatch, missing PR, or a newer CRID than the planner's → list it at the top of the log (do not edit the script; the human decides).
3. Confirm explicitly in the log: (a) PR exists for 27 Oct T48 F80 DVDV and 28 Oct T55 F10 DHDH; (b) 4 Oct T55 F10 exists; (c) 8 Nov T48 F80 and 9 Nov T55 F10 exist; (d) no T156 granule intersects the delta box.
4. Download the public `*_LATLON.png` browse (and `.kml`) for the new chosen scenes not yet in `data/events/cyclones_bay_of_bengal_2026/browse/` (3 Oct T48 F80, 4 Oct T55 F10, 8 Nov T48 F80, 9 Nov T55 F10, 10/22 Oct + 3 Nov T149 F80) into that folder, using the naming of `src/event_scenes.py` (`<YYYY-MM-DDTHHMM>Z_T<track>_F<frame>.png`, colons removed). Note: that folder is git-ignored by an existing rule.
5. CMR check for S-band: `https://cmr.earthdata.nasa.gov/search/collections.json?keyword=NISAR&page_size=200` – list every NISAR collection short_name; state whether any is S-band (expected none: S-band is distributed by ISRO Bhoonidhi).
6. Expected GCOV layer names: WebFetch the ASF NISAR docs (https://nisar-docs.asf.alaska.edu/) GCOV product page and record the documented dataset paths for `mask`, `numberOfLooks`, `rtcGammaToSigmaFactor`, `HHHH`, `VVVV`, `xCoordinates`, `projection` into the log (the human's `--probe` run compares against it).

**Verify:** manifest parses; every role row has an `h5_url` starting `https://nisar.asf.earthdatacloud.nasa.gov/`; browse PNGs open.
**On failure:** ASF API down → retry later, or use CMR granule search (`https://cmr.earthdata.nasa.gov/search/granules.json?short_name=NISAR_L2_GCOV_V1&bounding_box=81.6,16.2,82.6,17.1&temporal=...`). Never guess file names from patterns.
**Log:** `data/logs/D_asf_cmr.md`.

---

## Package E – Context: calm-day wind (ERA5), submission guide, crop calendar, mandal → 2022 districts

**Goal:** the small facts that captions and the submission need. Sources `ERA5_WIND`, `DOCS_SUBMISSION`, `DOCS_CROP`, `DOCS_DISTRICTS`.

**Steps**
1. ERA5 via Open-Meteo (no login, probed OK): for a 5×5 grid over the sea box (lat 15.0..18.0 step 0.75, lon 81.0..85.0 step 1.0) fetch
   `https://archive-api.open-meteo.com/v1/archive?latitude=<lat>&longitude=<lon>&start_date=2026-10-15&end_date=2026-10-15&hourly=wind_speed_10m,wind_direction_10m&models=era5&wind_speed_unit=ms` and the same for 2026-10-27. Save raw JSON to `data/raw/era5/openmeteo_era5_<date>_<lat>_<lon>.json`; write `data/reference/era5_wind_summary.csv` (`date,hour_utc,lat,lon,wind_ms,dir_deg`) for 12–14 UTC only, plus in the log the sea-box median and range at 13 UTC on 15 Oct. This is a **caption number** ("reference-day wind ≈ X m/s, ERA5"), not a wind map. Note that ERA5 data for recent days may be ERA5T (preliminary) and say so.
2. Submission guide + FAQ (released 13 Nov): WebSearch/WebFetch on spaceappschallenge.org (unreachable from the shell). Write `docs/SUBMISSION_GUIDE_NOTES.md`: every required project-submission field with its character limits, the deadline, video/demo rules, the exact FAQ wording on work done before the event and on using AI, each with the source URL. Quote; do not paraphrase rules.
3. Crop calendar: WebSearch for the Godavari delta (East/West Godavari, Konaseema) kharif paddy calendar and the state of the crop in late October 2026 (also any 2026 news on Arnab crop damage). Write `docs/CROP_CALENDAR_NOTES.md` with ≥ 2 independent sources (agri dept / ICAR / IMD agromet preferred), and a one-line suggested caption.
4. Mandal → 2022 district: after package C has written `data/reference/mandals_delta_list.csv` (if not yet there, use WebSearch for the 2022 AP district reorganisation lists for Dr. B.R. Ambedkar Konaseema, Kakinada, East Godavari, West Godavari, Eluru), write `data/reference/mandal_district_2022.csv` (`mandal_name_geoboundaries,mandal_name_official,district_2022,source_url`). Leave a cell empty rather than guess.

**Verify:** ERA5 CSV has numbers for every grid point (land points are fine but flag them); notes files contain URLs for every claim.
**On failure:** log and move on; none of these blocks the MVP.
**Log:** `data/logs/E_context.md`.

---

## Not for agents (blocked on a human – see plan section 4)

| Item | Why blocked | Human step |
|---|---|---|
| All NISAR L-band HDF5 subsets (`L_*` in sources.yaml) | Earthdata login | H1: `~/.netrc`, then `python src/fetch/subset_arnab.py --probe L_SEA_EYE_1027` and `--ids P0` |
| NISAR S-band GCOV (`S_GCOV_DELTA`), SCAT-3 wind (`SCAT3_1015`), EOS-04, Resourcesat | Bhoonidhi login | H2 |
| INSAT-3DS IR (`INSAT_IR_1027`) | MOSDAC login; host unreachable from shell | H3 (fallback: package A Himawari) |
| IMERG numeric (`IMERG_NUMERIC`) | Earthdata (GES DISC) | only if needed |
