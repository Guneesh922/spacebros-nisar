# Data acquisition plan – Eye of the Storm (Cyclone Arnab through NISAR)

Written Sat 14 Nov 2026 ~09:00 IST by the planner agent, from the master plan (Claude Doc "Eye of the Storm – one-page plan", sections 2–4, 6), this repo and live probes from the device shell.
Machine-readable twin: `data/sources.yaml`. Parallel work packages for no-login sources: `docs/FETCH_TASKS.md`.

## 0. Read this first – three findings that change the master plan

1. **Track 156 frame 10 does NOT cover the Godavari delta.** An ASF search with the delta box (81.6–82.6E, 16.2–17.1N) as footprint returns **no T156 granule at all** for 1 Oct–14 Nov (T156 F10 ends at ~81.66E on its bounding box; its tilted footprint misses the box). The master plan's "Flood pair T156 23 Oct → 4 Nov" and "Coast +7 d T156 4 Nov" cannot be used.
   **Decision:** the whole delta chapter uses **one track, T55 F10 ascending, DHDH (HH+HV, mode 4005)** which covers 78–82 % of the delta box on every pass:
   `4 Oct` (normal-fortnight start) → `16 Oct` (before) → `28 Oct 00:01 UTC` (+4 h) → **`9 Nov 00:01 UTC` (+12 d, replaces "+7 d")**.
   Optional (P1) "+6 d" view: **T149 F80 descending DHDH, 22 Oct → 3 Nov** (covers only the western ~33 % of the box). Evidence: `data/reference/asf_probe_delta_box_20261001_20261114.csv` (30 granules, with footprint-coverage fraction per granule).
2. **PR (production) versions now exist** for both UR scenes: 27 Oct T48 F80 DVDV (`..._P05036_N_P_J_001`) and 28 Oct T55 F10 DHDH (`..._P05036_N_P_J_001`). Use PR. Also confirmed: 4 Oct T55 F10, 8 Nov T48 F80, 9 Nov T55 F10 exist (all PR), plus a 3 Oct T48 F80 **quad-pol** (QPDH, 7.5 GB) calm-sea scene.
3. **Calibration caveat:** pre-21-Oct scenes are in collection `NISAR_L2_GCOV_PROVISIONAL_V1`, post-21-Oct ones in `NISAR_L2_GCOV_V1` (validated). Every storm-minus-calm and before/after pair crosses that boundary. The normal-fortnight pair (4→16 Oct) is provisional→provisional; the 28 Oct→9 Nov pair is V1→V1. Say this in the caption/About ("product versions differ; differences under ~1 dB are not interpreted").
4. Bonus: **Himawari-9 AHI Band 13 IR is on NASA GIBS for 27 Oct 13:00 UTC** (probed: real image over the storm). This is a no-login cloud-top eye at the same 10-min slot as the NISAR pass – the fallback (or replacement) for INSAT/MOSDAC. GIBS keeps Himawari for a rolling window (earliest time in capabilities today: 3 Oct), so **fetch it today**.

## 1. Host reachability (probed from the device shell, 14 Nov ~09:00 IST)

| Host | Result | Notes |
|---|---|---|
| gibs.earthdata.nasa.gov (WMTS caps, WMTS tiles, WMS GetMap) | reachable, 200 | layer ids verified below |
| cmr.earthdata.nasa.gov | reachable | GCOV collections: `NISAR_L2_GCOV_V1` (C3622241360-ASF), `NISAR_L2_GCOV_PROVISIONAL_V1` (C2854338529-ASF), `NISAR_L2_GCOV_BETA_V1` |
| api.daac.asf.alaska.edu (ASF search API, no login) | reachable | used for the probe in section 0 |
| nisar.asf.earthdatacloud.nasa.gov (HDF5) | 403 without login | Earthdata login needed – blocked for agents |
| urs.earthdata.nasa.gov | reachable | |
| www.geoboundaries.org API, github.com | reachable | IND ADM3 = 2018 boundaries, ODbL 1.0, 6836 units |
| storage.googleapis.com/global-surface-water | reachable | tile `occurrence_80E_20Nv1_4_2021.tif` = 28 MB, covers 80–90E, 10–20N |
| naciscdn.org (Natural Earth) | reachable | `ne_10m_coastline.zip` 3 MB |
| osmdata.openstreetmap.de | file URLs 200 (directory index 403) | coastlines/water polygons |
| rsmcnewdelhi.imd.gov.in, mausam.imd.gov.in | reachable | RSMC listings are behind a POST year form – see package B |
| archive-api.open-meteo.com | reachable | ERA5 hourly wind, no login |
| pypi.org | reachable | device has python 3.10 + pip but **no asf_search/earthaccess/h5py/rasterio installed** |
| bhoonidhi.nrsc.gov.in | reachable (302 to login) | login needed – blocked |
| www.mosdac.gov.in | **unreachable** from device shell (connection fails) | human step in a normal browser |
| www.spaceappschallenge.org | **unreachable** from device shell | agent must use WebFetch/WebSearch |

Agents should `python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt geopandas shapely pyyaml` inside the repo (`.venv/` is git-ignored) before anything that needs these libraries.

## 2. Boxes and dates (single source of truth)

| Name | W, S, E, N | Used for |
|---|---|---|
| delta | 81.6, 16.2, 82.6, 17.1 | delta chapter, mandal brief, all T55 subsets |
| sea | 81.0, 15.0, 85.0, 18.0 | sea chapter (T48 F80 frame is 81.27–84.49E, 15.3–18.33N, so the subset is the overlap) |
| context | 78.0, 12.0, 88.0, 20.0 | chapter 1 overview maps (GIBS) |
| clip_vectors | 81.0, 15.8, 83.0, 17.6 | boundaries / coastline / GSW clips (delta + 0.4° margin) |

Key times (UTC): landfall ~20:00 UTC 27 Oct (01:30 IST 28 Oct, to be confirmed by IMD); eye pass 27 Oct 13:01:51; coast pass 28 Oct 00:01:07.

## 3. Resource table

Priority: **P0** = MVP, **P1** = if time (master plan section 6), **P2** = stretch. Status values match `data/sources.yaml`.

### 3a. NISAR L-band GCOV (ASF) – all BLOCKED on Earthdata login (human runs `src/fetch/subset_arnab.py`)

All URLs below come from the ASF search probe (`data/reference/asf_probe_delta_box_20261001_20261114.csv`) or the existing `data/events/cyclones_bay_of_bengal_2026/scenes.csv`. Base: `https://nisar.asf.earthdatacloud.nasa.gov/NISAR/<collection>/<file_id>/<file_id>.h5`.

| id | What / why (chapter) | file_id (PR) | Collection | Full size | Subset | Expected subset | Dest | Prio |
|---|---|---|---|---|---|---|---|---|
| L_SEA_CALM_1015 | calm reference for storm-minus-calm (ch 2–3) | `NISAR_L2_PR_GCOV_033_048_D_080_2005_DVDV_A_20261015T130150_20261015T130208_P05023_N_P_J_001` | PROVISIONAL_V1 | 0.89 GB | sea box, VVVV+VHVH, decimated to 100 m | ~60–150 MB | `data/raw/nisar_l/sea/2026-10-15_T48_{VVVV,VHVH}.tif` | P0 |
| L_SEA_EYE_1027 | the eye (hero, ch 2–3) | `NISAR_L2_PR_GCOV_034_048_D_080_2005_DVDV_A_20261027T130151_20261027T130208_P05036_N_P_J_001` (UR fallback `..._P05036_F_P_J_001`) | GCOV_V1 | 0.85 GB | same | same | `data/raw/nisar_l/sea/2026-10-27_T48_*.tif` | P0 |
| L_COAST_1016 | before (ch 4) | `NISAR_L2_PR_GCOV_033_055_A_010_4005_DHDH_A_20261016T000106_20261016T000129_P05023_N_P_J_001` | PROVISIONAL_V1 | 4.27 GB | delta box, HHHH+HVHV, native 20 m (+ mask, numberOfLooks if present) | ~100–200 MB/pol | `data/raw/nisar_l/coast/2026-10-16_T55_*.tif` | P0 |
| L_COAST_1028 | +4 h after landfall (ch 4) | `NISAR_L2_PR_GCOV_034_055_A_010_4005_DHDH_A_20261028T000107_20261028T000129_P05036_N_P_J_001` | GCOV_V1 | 4.12 GB | same | same | `.../coast/2026-10-28_T55_*.tif` | P0 |
| L_COAST_1109 | +12 d (flood/waterlogging, brief) – replaces T156 4 Nov | `NISAR_L2_PR_GCOV_035_055_A_010_4005_DHDH_A_20261109T000107_20261109T000130_P05036_N_P_J_001` | GCOV_V1 | 4.29 GB | same | same | `.../coast/2026-11-09_T55_*.tif` | P0 |
| L_COAST_1004 | normal fortnight start (4 Oct → 16 Oct) for thresholds | `NISAR_L2_PR_GCOV_032_055_A_010_4005_DHDH_A_20261004T000106_20261004T000129_P05023_N_P_J_001` | PROVISIONAL_V1 | 4.28 GB | same | same | `.../coast/2026-10-04_T55_*.tif` | P0 |
| L_SEA_AFTER_1108 | "sea after the storm" (section 6 #4) | `NISAR_L2_PR_GCOV_035_048_D_080_2005_DVDV_A_20261108T130151_20261108T130208_P05036_N_P_J_001` | GCOV_V1 | 0.86 GB | sea box | ~60–150 MB | `.../sea/2026-11-08_T48_*.tif` | P1 |
| L_SEA_CALM_1003 | 2nd calm day → uncertainty of calm baseline | `NISAR_L2_PR_GCOV_032_048_D_080_2005_QPDH_A_20261003T130133_20261003T130207_P05023_N_F_J_001` (quad-pol; use VVVV+HVHV) | PROVISIONAL_V1 | 7.50 GB | sea box | ~100 MB | `.../sea/2026-10-03_T48_*.tif` | P1 |
| L_COAST_T149_1022 / _1103 / _1010 | +6 d view, west third of the box only | `NISAR_L2_PR_GCOV_033_149_D_080_4005_DHDH_A_20261022T130952_20261022T131027_P05036_N_F_J_001`, `NISAR_L2_PR_GCOV_034_149_D_080_4005_DHDH_A_20261103T130953_20261103T131027_P05036_N_F_J_001`, `NISAR_L2_PR_GCOV_032_149_D_080_4005_DHDH_A_20261010T130952_20261010T131027_P05023_N_F_J_001` | V1 / V1 / PROV | 6.3–6.5 GB | delta box | ~70 MB/pol | `.../coast/<date>_T149_*.tif` | P2 |

Auth: NASA Earthdata (free). Cost: free. Method: `earthaccess` HTTPS fsspec stream + `h5py`, reusing `subset()` and `save_tif()` from `src/gcov_subset.py` (that script's CLI reads the Delhi catalogue, so it is not called directly). Ready-made driver: **`src/fetch/subset_arnab.py`** (written by the planner; never downloads whole files):

```bash
cd 05_Code/spacebros-nisar && . .venv/bin/activate
python src/fetch/subset_arnab.py --probe L_SEA_EYE_1027      # step 0: login + list HDF5 layers (checklist: streaming works, layer names)
python src/fetch/subset_arnab.py --ids P0                     # all P0 scenes (~6 files, streams only the boxes)
python src/fetch/subset_arnab.py --ids L_SEA_AFTER_1108 L_SEA_CALM_1003   # P1 when time allows
```

Verification (per output GeoTIFF): opens with rasterio; CRS = UTM EPSG from the file (expected 32644 for 81–84E); bounds intersect the box; date in filename matches `file_id`; median dB plausible (sea VV ≈ −15…−25 dB calm, higher in storm; land HH ≈ −5…−15 dB; water HH < −18 dB); NaN fraction < 30 % (T55 covers ~80 % of the delta box, the rest is NaN by design). The script writes `data/logs/nisar_l_subset.md` with sizes and sha256.
Fallback: if streaming is too slow from the laptop, run the same script in Google Colab (`pip install -r requirements.txt`, upload `~/.netrc` content via `os.environ["EARTHDATA_USERNAME"/"EARTHDATA_PASSWORD"]`); if Earthdata fails entirely, the quick-look PNGs in `data/events/.../browse/` remain the hero images (master plan 2a).

### 3b. No-login sources (agents, see `docs/FETCH_TASKS.md`)

| id | What / why | Source (verified) | Auth / cost | Subset | Size | Dest | Method | Verify | Fallback | Prio | Pkg |
|---|---|---|---|---|---|---|---|---|---|---|---|
| GIBS_VIIRS_TC | ch 1 "From above": cameras see only cloud, 26–29 Oct | GIBS layers `VIIRS_SNPP_CorrectedReflectance_TrueColor` (to 2 Nov), `VIIRS_NOAA20_CorrectedReflectance_TrueColor`, `VIIRS_NOAA21_CorrectedReflectance_TrueColor`; WMS `https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi`; WMTS template `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/<layer>/default/<YYYY-MM-DD>/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg` (200 for 2026-10-27) | none, free | context + sea + delta boxes, daily 26–29 Oct | ~0.1–1 MB each | `data/raw/gibs/viirs_<sat>_truecolor_<date>_<box>.jpg` + `.json` bounds | curl WMS GetMap | JPEG opens, non-uniform (std > 5), bounds sidecar | Worldview manual snapshot | P0 | A |
| GIBS_IMERG | rain 26–29 Oct; rain mask for sea map (6 #2) | `IMERG_Precipitation_Rate` (daily, Level6) and `IMERG_Precipitation_Rate_30min` (half-hourly) | none | context + sea boxes; daily 26–29 Oct; 30-min 27 Oct 12:30/13:00/13:30Z and 28 Oct 00:00Z | ~20 KB each | `data/raw/gibs/imerg_*.png` | curl WMS | PNG with alpha; not fully transparent | numeric IMERG from GES DISC (needs Earthdata) | P1 | A |
| GIBS_HIMAWARI_IR | cloud-top eye at 13:00 UTC 27 Oct beside the radar eye (6 #5); replaces INSAT if MOSDAC is slow | `Himawari_AHI_Band13_Clean_Infrared` (10-min, rolling window – fetch today) | none | sea + context boxes, 27 Oct 12:50, 13:00, 13:10Z; 28 Oct 00:00Z | ~100 KB | `data/raw/gibs/himawari_b13_<time>_<box>.png` | curl WMS with `TIME=2026-10-27T13:00:00Z` | std > 20 (probe: std 94) | INSAT-3DS (MOSDAC, human) | P1 (urgent) | A |
| GIBS_VIIRS_I5_NIGHT | night IR ~20 UTC 27 Oct (near landfall) | `VIIRS_SNPP_Brightness_Temp_BandI5_Night`, `VIIRS_NOAA20_Brightness_Temp_BandI5_Night` | none | context box, 27 Oct | small | `data/raw/gibs/` | WMS | non-empty | skip | P2 | A |
| GIBS_REF | coastline/labels overlay for static PNGs | `Coastlines_15m`, `Reference_Labels_15m` | none | context box | small | `data/raw/gibs/` | WMS | | Natural Earth | P2 | A |
| IMD_BULLETINS | validation of eye position; landfall statement | RSMC New Delhi `https://rsmcnewdelhi.imd.gov.in/` – Bulletins `report.php?internal_menu=MzQ=`, Preliminary report `report.php?internal_menu=MjY=`, Best track `report.php?internal_menu=MzM=` (POST form field `search_year=2026`), satellite bulletins `archive-information.php?internal_menu=MjI=&menu_id=OQ==` and `...NzM=...`; also `https://mausam.imd.gov.in/` press releases | none | bulletins for 27 Oct nearest 12 and 15 UTC, the 28 Oct landfall statement, any preliminary report | ~0.2–2 MB each | `docs/imd_bulletins/<YYYYMMDD>_<HHMM>UTC_<type>.pdf` (tracked) | browser (Claude_Browser) / WebFetch / curl | PDF opens, mentions ARNAB and the date | news reports cited as "secondary, unverified by IMD" | P0 | B |
| IMD_TRACK_CSV | track line + fixes (ch 1, ch 3 distance) | typed from the PDFs above | – | all fixes 25–29 Oct | <10 KB | `data/reference/imd_track_arnab.csv` (tracked) | manual typing from PDFs | each row cites its PDF and page | – | P0 | B |
| GB_ADM3 | mandal outlines for the brief (ch 4) | geoBoundaries API `https://www.geoboundaries.org/api/current/gbOpen/IND/ADM3/` → `gjDownloadURL` `https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/IND/ADM3/geoBoundaries-IND-ADM3.geojson` (106 MB; ODbL 1.0; boundaries year 2018) | none | clip to clip_vectors box | ~1 MB clipped | raw: `data/raw/boundaries/`; clip: `data/reference/mandals_delta.geojson` | requests + geopandas | EPSG:4326, ≥ 30 polygons, names include e.g. Narsapur | OSM admin_level=6/7 via Overpass (not probed) | P0 | C |
| GB_ADM2 | district names (pre-2022 split) | same API, `/ADM2/` (2021, ODbL) | none | clip | small | `data/reference/districts_delta_gb2021.geojson` | same | | | P0 | C |
| JRC_GSW | permanent-water mask (do not call rivers "new water") | `https://storage.googleapis.com/global-surface-water/downloads2021/occurrence/occurrence_80E_20Nv1_4_2021.tif` (28 MB, 200) | none, free (JRC/Google, cite Pekel et al. 2016) | clip to clip_vectors box | ~2–5 MB | raw tile `data/raw/water/`; clip `data/interim/gsw_occurrence_delta.tif` | curl + rasterio window | EPSG:4326, values 0–100, river Godavari visible > 80 | GIBS `OSM_Land_Water_Map` | P0 | C |
| NE_COAST | coastline for sea mask (land + 2 km buffer) | `https://naciscdn.org/naturalearth/10m/physical/ne_10m_coastline.zip` | none, public domain | clip to sea + context | <1 MB | `data/reference/coastline_ne10m_clip.geojson` | curl + geopandas | lines within box | OSM below | P0 | C |
| OSM_COAST | high-res coastline / land polygons | `https://osmdata.openstreetmap.de/download/coastlines-split-4326.zip` and `.../land-polygons-split-4326.zip` (ODbL) | none | clip | raw ~0.5–1 GB zip; clip small | raw `data/raw/coast/`; clip `data/reference/coastline_osm_clip.geojson` | curl + geopandas | | NE coastline | P1 | C |
| ASF_MANIFEST | final scene-id manifest; browse of new scenes | ASF search API `https://api.daac.asf.alaska.edu/services/search/param` (no login), CMR | none | delta and sea boxes, 1 Oct–14 Nov, GCOV | <1 MB | `data/reference/scene_manifest.csv`, browse PNGs → `data/events/cyclones_bay_of_bengal_2026/browse/` | asf_search or curl | every P0 file_id present, PR preferred | the probe CSV already in `data/reference/` | P0 | D |
| ERA5_WIND | calm-day (15 Oct) and eye-day wind caption if SCAT-3 is blocked; **caption only, no wind map** | `https://archive-api.open-meteo.com/v1/archive?...&models=era5` (probed: returns hourly wind) | none, free (ECMWF ERA5 via Open-Meteo, CC BY 4.0) | 5×5 points over sea box, 15 Oct + 27 Oct, 12–14 UTC | <50 KB | `data/raw/era5/openmeteo_era5_<date>.json` | curl | 24 hourly values per point | none | P1 | E |
| DOCS_SUBMISSION | 2026 submission guide fields + FAQ on pre-event work | spaceappschallenge.org (unreachable from shell → WebFetch/WebSearch) | none | – | – | `docs/SUBMISSION_GUIDE_NOTES.md` | WebFetch | quotes with URLs | human reads it | P0 | E |
| DOCS_CROP | Godavari-delta crop calendar late Oct | web (WebSearch) | none | – | – | `docs/CROP_CALENDAR_NOTES.md` | WebSearch | ≥ 2 independent sources | caption says "kharif paddy, stage uncertain" | P1 | E |
| DOCS_DISTRICTS | mandal → 2022 district (Konaseema, Kakinada, West Godavari, Eluru) | web (AP govt district sites / LGD) | none | mandals in the delta box | <10 KB | `data/reference/mandal_district_2022.csv` | WebSearch/WebFetch | every mandal in the clip has a row + source | keep 2018 names, footnote | P1 | E |

### 3c. Login-only sources – BLOCKED for agents

| id | What / why | Source | Auth | Cost | Subset | Dest | Prio | Fallback |
|---|---|---|---|---|---|---|---|---|
| S_GCOV_DELTA | NISAR S-band GCOV before/after over the delta → L/S toggle (6 #1) | Bhoonidhi `https://bhoonidhi.nrsc.gov.in/NISAR/NisarProducts.html` (ISRO release: https://www.isro.gov.in/ISRO%5FEN/NISARS_Band_SAR_Data_Products_Release.html) | Bhoonidhi login | free | delta box, 16 Oct–10 Nov; use Bhoonidhi HDF→GeoTIFF subset tool | `data/raw/nisar_s/` + ids in `data/reference/nisar_s_candidates.csv` | P1 | no toggle; nothing else changes |
| SCAT3_1015 | calm-day wind for the 15 Oct caption | Bhoonidhi, EOS-06 SCAT-3 binned wind vectors (12.5 km) | Bhoonidhi login | free (open data) | 15–18N, 81–85E, 15 Oct (and 27 Oct) | `data/raw/scat3/` | P1 | ERA5_WIND (no login) |
| INSAT_IR_1027 | cloud-top eye 13:00 UTC 27 Oct | MOSDAC (https://mosdac.gov.in/node/2070 API manual); host unreachable from device shell | MOSDAC login (approval may take time) | free | IR1 L1C nearest 13:00 UTC 27 Oct, sea box | `data/raw/insat/` | P1 | GIBS_HIMAWARI_IR (no login, verified) |
| EOS04_MRS | C-band third frequency | Bhoonidhi (MRS/CRS open, FRS priced – do not buy) | Bhoonidhi login | free for MRS | only if a pass falls 16 Oct–10 Nov | `data/raw/` (new subdir if used) | P2 | skip |
| RS2_LISS3 | clear-sky optical check after 4 Nov | Bhoonidhi Resourcesat-2/2A LISS-III/AWiFS | Bhoonidhi login | free | delta box, cloud-free after 4 Nov | `data/raw/` | P2 | skip |
| IMERG_NUMERIC | rain totals as numbers | GES DISC (gpm1.gesdisc.eosdis.nasa.gov reachable) | Earthdata login | free | sea box 26–29 Oct | `data/raw/` | P2 | GIBS PNG colour only |

Never fetch (master plan): wind-speed maps, Murasu, Delhi, GUNW, RADARSAT/SAOCOM data, anything needing a live server.

## 4. Blocked on a human (do these in this order; ~1 min each plus approval time)

Credentials go **only** in `~/.netrc` (chmod 600) or shell env vars / Colab secrets. Never in the repo, never in a notebook cell that is committed. `.netrc`, `_netrc`, `.env` are already git-ignored.

**H1 – NASA Earthdata (P0, blocks the whole radar pipeline).**
1. Log in / register at https://urs.earthdata.nasa.gov (free).
2. Log in once at https://search.asf.alaska.edu with the same account (accepts the ASF EULA so HDF5 downloads authorise).
3. On the Mac: `printf 'machine urs.earthdata.nasa.gov login YOUR_USER password YOUR_PASS\n' >> ~/.netrc && chmod 600 ~/.netrc`
4. `cd 05_Code/spacebros-nisar && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt pyyaml`
5. `python src/fetch/subset_arnab.py --probe L_SEA_EYE_1027` – must print the frequencyA layer list (expect `VVVV`, `VHVH`, `mask`, `numberOfLooks`, `rtcGammaToSigmaFactor`, `xCoordinates`, `yCoordinates`, `projection`). This ticks checklist items 1 and 10.
6. `python src/fetch/subset_arnab.py --ids P0`. If too slow (> 15 min per coast file), use Colab with `EARTHDATA_USERNAME`/`EARTHDATA_PASSWORD` set as Colab secrets.

**H2 – Bhoonidhi (P1: S-band toggle + SCAT-3).**
1. Register at https://bhoonidhi.nrsc.gov.in (both team members; free).
2. Search NISAR → S-band → GCOV, AOI 81.6–82.6E 16.2–17.1N, 16 Oct–10 Nov. Write every hit (scene id, date/time UTC, pols, size) to `data/reference/nisar_s_candidates.csv`. No hit = no toggle.
3. If hits: subset with Bhoonidhi's HDF→GeoTIFF tool to the delta box, save to `data/raw/nisar_s/`.
4. Search EOS-06 SCAT-3 wind vector product for 15 Oct (and 27 Oct), save to `data/raw/scat3/`.
5. If you use the API, keep creds in env vars `BHOONIDHI_USER` / `BHOONIDHI_PASS` only.

**H3 – MOSDAC (P1, optional).** mosdac.gov.in is not reachable from the agent shell. In a normal browser, sign up at https://www.mosdac.gov.in; once approved, download the INSAT-3DS IR1 (10.8 µm) image nearest 13:00 UTC 27 Oct into `data/raw/insat/`. If approval is not through by Sat 18:00, use the Himawari IR from package A and drop this.

**H4 – decide/confirm** (2 min): accept the T156 → T55 9 Nov substitution above (chapter 4 caption becomes "12 days after landfall"), and whether the P2 T149 +6 d view is wanted.

## 5. Master-plan section 3 checklist → who resolves it

| # | Loose end | Status now | Resolved by |
|---|---|---|---|
| 1 | Earthdata streaming works on the 27 Oct eye file | open | **H1** step 5 (`--probe`) |
| 2 | Bhoonidhi accounts + S-band GCOV search over delta | open | **H2** (blocked: login) |
| 3 | PR versions of 27 Oct T48 F80 and 28 Oct T55 F10 | **resolved by planner probe**: both exist (P05036, `_N_`) | package **D** re-confirms in `scene_manifest.csv` |
| 4 | 4 Oct T55 F10 and 8–9 Nov scenes exist | **resolved by probe**: all exist, PR | package **D** |
| 5 | SCAT-3 wind 15 Oct | open | **H2**; no-login fallback ERA5 caption in package **E** |
| 6 | IMD bulletins 27 Oct 12/15 UTC + 28 Oct landfall PDFs, track CSV | open | package **B** |
| 7 | INSAT-3DS IR near 13:00 UTC 27 Oct | open | **H3**; verified no-login substitute Himawari B13 IR in package **A** |
| 8 | Mandal boundaries, licence, 2022 split | licence checked (ODbL 1.0, 2018 boundaries – pre-split) | package **C** (geometry) + package **E** (mandal → 2022 district table) |
| 9 | JRC GSW tile + OSM coastline | URLs verified | package **C** |
| 10 | GCOV layer names (`mask`, `numberOfLooks`, `rtcGammaToSigmaFactor`) | open | **H1** `--probe`; package **D** records the names from the ASF GCOV docs for comparison |
| 11 | Exact GIBS layer ids | **resolved by probe** (see 3b) | package **A** records them in `data/reference/gibs_layers.json` |
| 12 | 2026 Submission Guide fields + FAQ wording | open | package **E** (WebFetch; site unreachable from shell) |
| 13 | Crop calendar (harvest vs standing kharif paddy) | open | package **E** |
| new | T156 does not cover the delta | **found by planner** | **H4** confirms the T55 substitution |

## 6. Folder layout and git rules

See `data/README.md`. Short version: big things under `data/raw/` (already git-ignored wholesale by the existing `.gitignore`, so the `.gitkeep` files there are not tracked – the layout is documented instead), clipped/typed small things under `data/reference/` (tracked), intermediate rasters under `data/interim/` (rasters ignored), web-ready PNG/JSON under `data/processed/` (tracked, page budget 15 MB), per-package reports under `data/logs/` (tracked), IMD PDFs under `docs/imd_bulletins/` (tracked). Fetch scripts written by agents go in `src/fetch/` (tracked).

## 7. Assumptions recorded (no questions asked)

- Delta "+7 d" becomes "+12 d" (T55 9 Nov) because no T156 coverage exists; T149 3 Nov is optional extra.
- Sea subsets are block-averaged to 100 m to keep files small; the eye/eyewall analysis does not need 20 m.
- PR products preferred over UR everywhere; UR kept as fallback ids.
- geoBoundaries ADM3 (2018) is acceptable for mandal geometry; district names are mapped to the 2022 districts by a separate table.
- Himawari via GIBS is an acceptable NASA-served stand-in for INSAT; parallax at ~58° from sub-satellite point is noted in the caption.
- Landfall time ~20:00 UTC 27 Oct is from news (03_Data/README_DATA.md) until IMD PDFs confirm it.
