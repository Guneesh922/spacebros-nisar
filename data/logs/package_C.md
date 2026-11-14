# Package C log: boundaries, permanent water, coastlines

Run: 2026-11-14 (agent). Scripts: src/fetch/package_c_clip.py (all clips), src/fetch/package_c_osm_land.py (OSM land, run on the shp extracted from the raw zip to a scratch dir, removed afterwards). Python deps (geopandas 1.1.4, rasterio, pyogrio) installed with pip --target /tmp/pylib because the session home disk was full; no repo files affected.
Clip boxes: vectors/GSW 81.0,15.8,83.0,17.6; coast context 78,12,88,20; delta box 81.6,16.2,82.6,17.1. All outputs EPSG:4326. Nothing failed; no fallback used.

## Raw downloads (data/raw, git-ignored)
| file | bytes | sha256 |
|---|---|---|
| boundaries/geoBoundaries-IND-ADM3.geojson | 106291594 | f9c38b47f2b8755af59d30bb846f66d0823aba127872668ccc2fa9f0dc3cd48f |
| boundaries/geoBoundaries-IND-ADM2.geojson | 48317735 | 8bef6929fd65432e7dc775e7c44473e84efff064ebddbfd6b834e6291546db40 |
| water/occurrence_80E_20Nv1_4_2021.tif | 28168808 | a29874b9443d8da884e4edf1ad1e526340f64e058f67a3d1141547bcd8c12cf0 |
| coast/ne_10m_coastline.zip | 3069451 | bfa04cdbcbef07ef90dfca1dabb48062eca29900a113df0f389303e255484017 |
| coast/coastlines-split-4326.zip (OSM) | 926496748 | f2bfe1548d1dd622d787abbe8cc7629695f7ac0f1d532ca908249438fcb1d754 |
| coast/land-polygons-split-4326.zip (OSM) | 929939758 | 2e8dca254d422be90499affc9f99674c522fd955faa2e5165e0e311e709021b0 |
OSM zips were fetched with parallel HTTP range requests (tool call time limit), reassembled; byte sizes match the server Content-Length (OSM build dated 2026-11-14 01:50/01:56 GMT) and both zips open. The OSM URLs are the rolling "latest" files, so the sha256 above is the only way to identify the build.

## Derived files
| file | bytes | features | sha256 |
|---|---|---|---|
| data/reference/mandals_delta.geojson | 791571 | 146 | 7cf7a0d2e1ee5ffaf8be5d19654ddc634e6947b576d914be06901e36dfb85b06 |
| data/reference/districts_delta_gb2021.geojson | 221884 | 6 | ef132795d92bafcfa7ca82cc98ade7827459a9f8d6d36413bcbd75e3ee1c4bfa |
| data/reference/mandals_delta_list.csv | 10279 | 146 rows | 1ba5bccae08e8e57f00948ec60ba8a22af2f08a9a9315c6c72568d930b6d3373 |
| data/reference/coastline_ne10m_clip.geojson | 29763 | 2 | 7a455a52226187a511dd8b9c196ee31088ba53d35f5a77562707f809633f6e7c |
| data/reference/coastline_osm_clip.geojson | 476354 | 34 | 2b63f8a82ed22641a71862fa95b43352965e00e4eed9b7db849c498308ada787 |
| data/reference/land_osm_clip.geojson | 490967 | 78 | e24af40b02a28bb07371cd704e66f5dea81c4f018f3351537f3409e68c028778 |
| data/reference/geoboundaries_meta_ADM2.json / ADM3.json | 1767 / 1772 | API responses (licence evidence) | facae06e1656838ebcbd6fc9198cdba8dd568ca2aec19d69759b3263a1511962 / 7dc8e3f41533eeb5144d0284cb372bb0f39863aa12cf196910b5d303a1676cee |
| data/interim/gsw_occurrence_delta.tif | 5359715 | 8000x7200 px, deflate, uint8 | 92500bcaff8aa32cc2964f9a8f3e191415c95d549542dce3f640f61417c27ceb |
| data/interim/gsw_occurrence_delta_preview.png | 187756 | preview | b9a6b71f4c931776d1f2c34e8be3f3c327929f99a70d2d9449753c7cedf742e1 |
All reference files < 5 MB, no simplification applied (polygons kept whole, not cut). GSW tif is 5.4 MB (interim, not a reference file; plan expected 2-5 MB).

## Verification
- Mandals: 146 polygons intersect the clip box (>= 30 required); 66 have non-zero overlap with the delta box; every mandal has a parent ADM2 (spatial join on representative point). Columns: shapeName, shapeID, area_km2 (EPSG:32644).
- Spelling of "Narsapur": the file has `Narasapuram` (West Godavari) and, separately, `T.Narasapuram`. Other delta coastal names present exactly as: Thallarevu, Katrenikona, Mamidikuduru, Uppalaguptam, Allavaram, Amalapuram, Mummidivaram, I. Polavaram, Polavaram, Kakinada (Rural), Kakinada (Urban), Yanam Taluk. Note Kakinada is split into (Rural)/(Urban) and Yanam appears as `Yanam Taluk` (Puducherry enclave).
- Districts (GB ADM2, year 2021): Bhadradri, East Godavari, Krishna, Visakhapatnam, West Godavari, Yanam. This is the PRE-2022 layout: it does NOT contain Dr. B.R. Ambedkar Konaseema, Kakinada, Eluru etc. The 2022 split matters for names: the delta mandals (e.g. Amalapuram, Mummidivaram, Katrenikona, Uppalaguptam, Thallarevu) sit in "East Godavari" here but are now in Konaseema/Kakinada; Narasapuram/Mamidikuduru-type mandals in West Godavari are now in West Godavari/Konaseema/Eluru as applicable. The 2018 ADM3 vintage is even older. Captions must map mandal -> 2022 district via data/reference/mandal_district_2022.csv (package E), not via parent_ADM2_name. ADM3 parent_ADM2_name in the csv is the 2021 district.
- GSW: CRS EPSG:4326, bounds exactly 81.0,15.8,83.0,17.6, min 0 max 100 plus 255 (nodata flag; file nodata metadata is unset, so mask 255 yourself): 31.5% of the clip is 255. In the delta box 13.5% is 255. Godavari main channel at Dowleswaram barrage (81.7695E, 16.937N, 13x13 px neighbourhood) max = 90 (> 80, OK). Caveat: the open sea has occurrence ~100, so ">80 = permanent water" includes the Bay of Bengal (47% of the delta box > 80); use together with the land polygons for a river/lagoon-only mask. My two other spot checks (Vasishta near 81.70,16.43 and Gautami near 82.27,16.72) returned 0 but the coordinates were rough guesses, not verified channel positions: do not treat as evidence either way.
- NE coastline: 2 line features (clipped to context box), non-empty. OSM coastline 34 lines, OSM land 78 polygons, same extent roughly 79.86-86.4E (matches NE).

## Licences (cite these)
- geoBoundaries gbOpen IND ADM3 (year 2018) and ADM2 (year 2021): "Open Data Commons Open Database License 1.0" (ODbL-1.0). Source per API: Pathways Data Pvt. Ltd., lgdirectory.gov.in; licenseSource geonode.pathwaysdata.com/layers/geonode; sourceDataUpdateDate Thu Jan 19 07:31:04 2023; buildDate Dec 12, 2023. API: https://www.geoboundaries.org/api/current/gbOpen/IND/ADM3/ and /ADM2/. Cite: Runfola et al. 2020, geoBoundaries, PLoS ONE 15(4): e0231866. ODbL needs attribution and share-alike for derived databases.
- JRC Global Surface Water v1.4 (2021 download set): free to use with citation, Pekel, J.-F., Cottam, A., Gorelick, N., Belward, A.S. (2016) High-resolution mapping of global surface water and its long-term changes, Nature 540, 418-422. Provided by EC JRC / Google. I did not retrieve a licence page (none in the tile); the citation requirement is from the plan.
- Natural Earth 10m coastline: public domain (per naturalearthdata.com terms of use; not re-fetched in this run).
- OSM coastlines / land polygons (osmdata.openstreetmap.de): ODbL-1.0, (c) OpenStreetMap contributors. The README.txt inside each zip was not copied into the log.

## Failures / caveats
- None in downloads. Environment: session home volume was full (pip failed with ENOSPC), worked around with /tmp/pylib. The mounted folder forbids deletion, so overwriting outputs required write-to-/tmp then copy in place (handled in the script).
- sources.yaml: status of GB_ADM3, GB_ADM2, JRC_GSW, NE_COAST, OSM_COAST set to done with log: data/logs/package_C.md. FETCH_TASKS.md names the log C_boundaries_water.md; this file is package_C.md as instructed by the caller.
