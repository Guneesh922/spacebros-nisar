# Placeholders: every sample value and the real file that replaces it

Everything below is flagged in the data (`placeholder.is: true`, or `bounds_inferred: true`, or a `[... to confirm]` string) and shows a visible tag in the page. To replace one: drop the real file at the path in the "Replaced by" column, then set `placeholder` to `null` (or `is:false`) on that layer in `data/processed/manifest.json`. No code change. Run `python3 tools/check_manifest.py --files` to see what is still missing on disk.

"Who" is the role that owes the file. "Source id" is the id in `data/sources.yaml` (or `manifest.json` `sources[]` where `sources.yaml` has none).

## 1. NISAR quick-look layers (tag "Quick-look sample")

Replaced by: the same path, as a greyscale dB PNG (VV for sea, HH for coast, at most 600 KB) made from the GCOV GeoTIFF subset. Until then the page shows the converted NISAR quick-look browse image (display only). Blocked on Earthdata login (`~/.netrc`).

| Layer id | Replaced by | Who | Source id | Processing | Bounds |
|---|---|---|---|---|---|
| `nisar_l_coast_20261109_t55_hh` | `data/processed/img/nisar_l_coast_20261109_t55_hh.png` | backend | L_COAST_1109 | validated (GCOV_V1) | from KML |
| `nisar_l_coast_20261028_t55_hh` | `data/processed/img/nisar_l_coast_20261028_t55_hh.png` | backend | L_COAST_1028 | validated (GCOV_V1) | from KML |
| `nisar_l_coast_20261016_t55_hh` | `data/web/nisar_l_coast_20261016_t55_hh.png` | backend | L_COAST_1016 | provisional (PR) | **inferred** (no KML) |  **REAL since 14 Nov: built from `data/h5/` by tools/build_web.py; placeholder null; bounds from the H5, not inferred.**
| `nisar_l_coast_20261004_t55_hh` | `data/web/nisar_l_coast_20261004_t55_hh.png` | backend | L_COAST_1004 | provisional (PR) | **inferred** (no KML) |  **REAL since 14 Nov: built from `data/h5/` by tools/build_web.py; placeholder null; bounds from the H5, not inferred.**
| `nisar_l_sea_20261108_t48_vv` | `data/processed/img/nisar_l_sea_20261108_t48_vv.png` | backend | L_SEA_AFTER_1108 | validated (GCOV_V1) | from KML |
| `nisar_l_sea_20261027_t48_vv` | `data/web/nisar_l_sea_20261027_t48_vv.png` | backend | L_SEA_EYE_1027 | validated (GCOV_V1) | from KML |  **REAL since 14 Nov: built from `data/h5/` by tools/build_web.py; placeholder null; bounds from the H5, not inferred.**
| `nisar_l_sea_20261015_t48_vv` | `data/web/nisar_l_sea_20261015_t48_vv.png` | backend | L_SEA_CALM_1015 | provisional (PR) | **inferred** (no KML) |  **REAL since 14 Nov: built from `data/h5/` by tools/build_web.py; placeholder null; bounds from the H5, not inferred.**
| `nisar_l_sea_20261003_t48_vv` | `data/web/nisar_l_sea_20261003_t48_vv.png` | backend | L_SEA_CALM_1003 | provisional (PR) | **inferred** (no KML) |  **REAL since 14 Nov: built from `data/h5/` by tools/build_web.py; placeholder null; bounds from the H5, not inferred.**

## 2. Bounds inferred (`bounds_inferred: true`)

The four provisional scenes have no KML (the `_LATLON.kml` URLs redirect to Earthdata login). Their bounds are copied from the same track and frame of the nearest later KML. When the real GeoTIFF is subset, write the true bounds into the layer and set `bounds_inferred` to false.

| Layer ids | Bounds used `[[S,W],[N,E]]` | Copied from | Who | Source id |
|---|---|---|---|---|
| `nisar_l_sea_20261003_t48_vv`, `nisar_l_sea_20261015_t48_vv` | `[[15.297,81.272],[18.331,84.490]]` | KML of 2026-10-27 T48 F80 | backend | L_SEA_CALM_1003, L_SEA_CALM_1015 |  **REAL since 14 Nov: built from `data/h5/` by tools/build_web.py; placeholder null; bounds from the H5, not inferred.**
| `nisar_l_coast_20261004_t55_hh`, `nisar_l_coast_20261016_t55_hh` | `[[15.289,80.534],[18.337,83.768]]` | KML of 2026-10-28 T55 F10 | backend | L_COAST_1004, L_COAST_1016 |  **REAL since 14 Nov: built from `data/h5/` by tools/build_web.py; placeholder null; bounds from the H5, not inferred.**
| `nisar_class_*` (3 layers) | T55 frame bounds as above | placeholder only; real class maps will be on the delta subset grid | backend | L_COAST_1016, L_COAST_1109 |
| `nisar_sea_diff_20261027_vs_20261015` | T48 frame bounds as above | placeholder only | backend | L_SEA_EYE_1027, L_SEA_CALM_1015 | (superseded: real bounds from the H5)

## 3. Derived products (status `unavailable`, tag "Sample values")

No image exists and none is drawn from quick-looks (a difference of colour composites is not meaningful). The layer shows as unavailable until the file lands.

| Layer id | Replaced by | Who | Source id |
|---|---|---|---|
| `nisar_class_new_water` (likely new open water, #2A6FB0) | `data/processed/img/class_20261109_new_water.png` | backend | L_COAST_1004, L_COAST_1016, L_COAST_1109 |
| `nisar_class_wet_crops` (likely wet or flooded crops, #E09A2B) | `data/processed/img/class_20261109_wet_crops.png` | backend | same |
| `nisar_class_no_change` (likely no change, outline) | `data/processed/img/class_20261109_no_change.png` | backend | same |
| `nisar_sea_diff_20261027_vs_20261015` | `data/web/nisar_sea_diff_20261027_vs_20261015.png` | backend | L_SEA_EYE_1027, L_SEA_CALM_1015 |  **REAL since 14 Nov: VV 27 Oct minus VV 15 Oct from the two H5 subsets (build_sea_difference).**

## 4. Companion JSON files (tag "Sample values")

| Placeholder | Replaced by | Who | Source id |
|---|---|---|---|
| analysis `ap_delta_oct_nov_2026` and `data/processed/mandal_rank.json` (45 invented rows, Konaseema + West Godavari + Kakinada only; East Godavari not included) | `data/processed/mandal_rank.json` with real zonal statistics (same shape, keep `placeholder` off) | backend (due Sun 09:00) | L_COAST_1004, L_COAST_1016, L_COAST_1109 + GB_ADM3 + DOCS_DISTRICTS |
| `data/processed/profile.json` (curve copied from the mockup formula, eye 18 km +/-3, 22 km from the IMD fix) | `data/processed/profile.json` from the 27 Oct VV subset (eye centre, radius, radial mean) | backend | L_SEA_EYE_1027 |
| `data/processed/alerts.json` and layer `alerts_sachet_snapshot` (three bracketed headlines, snapshot 27 Oct 17:30 IST) | `data/processed/alerts.json` from a SACHET snapshot script (none exists yet in `src/fetch/`) | backend | none in sources.yaml; `ndma_sachet` in the manifest |
| `data/processed/mandals.geojson`, `imd_track_arnab.geojson`, `img/*` | made by `tools/make_web_assets.py` (task A2); not placeholders, listed for completeness | frontend (A2) | GB_ADM3, DOCS_DISTRICTS, IMD_TRACK_CSV |

## 5. Values to confirm (not files)

| Item | Where | Needed | Who | Source id |
|---|---|---|---|---|
| Open-Meteo marine sea point `16.0 N, 82.0 E` (`coordinates_confirmed:false`) | layer `open_meteo_marine`, `config` | pick a sea point per region (for example off Narsapur) | backend | none in sources.yaml (ERA5_WIND uses Open-Meteo archive only) |
| Open-Meteo flood river point `16.94 N, 81.77 E` (near Dowleswaram barrage, `coordinates_confirmed:false`) | layer `open_meteo_flood`, `config` | confirm the GloFAS grid cell with the Godavari | backend | none in sources.yaml |
| GDACS endpoint and browser (CORS) access from github.io | layer `alerts_gdacs_live` | test once Pages is on; if blocked the strip shows the snapshot only | backend / owner | none in sources.yaml |
| VIIRS satellite (NOAA-21 used; SNPP stops 2 Nov in `gibs_layers.json`) and the 27 Oct delta image (near-uniform, probably cloud) | layer `gibs_viirs_truecolor` | a human picks the satellite for saved events | owner | GIBS_VIIRS_TC |
| Landfall time (`time_utc: null`, note "time being confirmed (IMD)") | event `arnab_2026` | a human decides what to state (IMD texts disagree) | owner | IMD_BULLETINS |
| Licence wording for ASF NISAR and SACHET | `sources[]` `asf_nisar_l`, `ndma_sachet` | check against each site's terms | backend | L_* , none |

## 6. Credit lines to confirm

`07_BACKEND_RESOURCE_REGISTRY.pdf` was not readable when this manifest was written, so every credit line comes from `docs/handoff/06_PLAN_Eye_of_the_Storm.md` section 2e, `data/sources.yaml`, or the mockup copy. Two are unknown and carry the plain text `[credit line to confirm]` (`credit_confirmed:false`). The rest should still be checked against the registry.

| Source id (manifest) | Current credit line | Status | Who |
|---|---|---|---|
| `mosdac` (also layer `mosdac_insat_link`) | `[credit line to confirm]` | **unknown** | backend |
| `osm` | `[credit line to confirm]` | **unknown** (licence ODbL-1.0 is in sources.yaml OSM_COAST) | backend |
| `asf_nisar_l` | NASA/JPL-Caltech and ISRO via ASF DAAC | from mockup; check | backend |
| `nasa_gibs` | NASA GIBS | from 2e (CC0); check | backend |
| `open_meteo_marine`, `open_meteo_flood` | Open-Meteo.com, CC BY 4.0 | from 2e; check | backend |
| `gdacs` | GDACS | from 2e | backend |
| `ndma_sachet` | NDMA SACHET | from 2e | backend |
| `imd_bulletins` | IMD / RSMC New Delhi bulletins | from mockup; check | backend |
| `geoboundaries` | geoBoundaries, ODbL-1.0 (boundary year 2018) | from sources.yaml GB_ADM3 | backend |
| `spacebros_derived` | SpaceBros, from NISAR data | team text | owner |

## 7. Added during frontend review (Sat 14 Nov 2026)

| Placeholder | Where | Shown as | Replaced by | Who |
|---|---|---|---|---|
| Case study **wave diagram** (24 cm vs 9 cm slider) is an illustrative SVG drawn in code, not data or a measured profile | `app/js/case.js` (`GEO`, wave diagram) | caption says illustration | a real S-band vs L-band pair, or an owner-approved static figure | owner |
| Case study **"what radar can't show"** claims and verdicts (four) | `app/strings/case.en.json`, keys `case.radar.c1..c4.*`, `case.verdict.*` | small tag "Draft: to be reviewed" on each verdict (`case.tag.draft`) | expert-reviewed wording; then delete the tag line in `stepRadar()` | domain expert |
| Case study chapter 3 numbers (eye radius, +6.2 dB peak, 22 km IMD offset) | `data/processed/profile.json` | tag "Sample values" | real `profile.json` | backend |
| Case study images use the quick-look browse crops | `data/processed/img/*` | tag "Quick-look sample" | greyscale dB PNGs (section 1) | backend |
| SACHET sample headlines: three entries, each `[Sample headline: official alert text from the saved SACHET feed]` (no cyclone wording on the landing view); snapshot time 27 Oct 17:30 IST is invented | `data/processed/alerts.json` | tag "Sample values" (short "Sample" at 1100 px and below) | real SACHET snapshot (BACKEND_GAPS section 13, item 3) | backend |
| Open-Meteo marine and flood **coordinates** (16.0 N 82.0 E; 16.94 N 81.77 E) | manifest `layers[open_meteo_*].config` | "coordinates to be confirmed" | confirmed points per region | backend |
| Ranking card, mandal card and A4 brief numbers | `mandal_rank.json` | "Sample values" (also printed on the brief) | real zonal statistics | backend |
| Default compare pair: Left = the latest layer of the same series filed under `before` in the manifest (16 Oct), Right = newest | `app/js/compare.js` `defaults()` | n/a | none: driven by manifest `group` values | frontend |
