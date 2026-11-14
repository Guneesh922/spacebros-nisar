# Package D log: ASF / CMR metadata manifest

Run: 2026-11-14T03:52:35+00:00 (UTC), script `src/fetch/D_asf_manifest.py` (python3.10, requests, shapely 2.1.2, pillow; venv at `/tmp/v` because creating `.venv` on the mount failed at ensurepip, a partial empty `.venv/` dir exists and is git-ignored). No credentials used, no HDF5 downloaded.

## Findings that need a human decision (top)

1. **No role mismatch.** All 14 role ids from `src/fetch/subset_arnab.py` (11 PR + 3 UR fallbacks) exist in the ASF response with identical file ids and the same collections. No missing PR. No newer CRID than the planner's: the only multi-CRID granules are UR ones (P05023 and P05036 both listed, 8 granules, e.g. UR 28 Oct T55 F10 DHDH); the script's UR fallbacks use P05036, which is the newer one.
2. **Provisional vs validated:** PR scenes of 3, 4, 10, 15, 16 Oct are `NISAR_L2_GCOV_PROVISIONAL_V1` (CRID P05023); PR scenes from 22 Oct on are `NISAR_L2_GCOV_V1` (P05036, validated). So the pre-storm calm/baseline scenes are provisional, storm and later are validated.
3. **Sea scene vs delta box:** the 27 Oct / 15 Oct / 8 Nov T48 F80 DVDV (2005) scenes cover 0.92 / 0.94 / 0.93 of the delta box, but the T48 F80 DHDH (4005) frames of the same passes cover only ~0.00. The delta chapter must use T55 F10 DHDH (4005, 0.79-0.83) as planned.
4. **Browse KMLs:** the 5 provisional-collection scenes (3 Oct, 4 Oct, 10 Oct, 15 Oct, 16 Oct) have PNG quick-looks (public via 303 to CloudFront) but their `_LATLON.kml` URLs redirect to Earthdata login (HTTP 401), so no KML for those 5. Not attempted further (rule 2). KML footprints for them are not needed for the manifest since footprint polygons come from the API.
5. md5 is null for every granule in the API response, so the manifest has no md5 (not fabricated). Manifest column set follows the lead's request (role, granule_id, track, frame, polarisations, acquisition_utc, processing_level, fraction_of_delta_box_covered, size_bytes, download_url, browse_url, notes), which differs from the FETCH_TASKS.md column list; `scene_manifest_full.csv` carries the extra fields (direction, crid, collection, mode, frame_coverage, sea-box fraction, kml_url, pge, stop time).
6. Browse destination: `data/events/cyclones_bay_of_bengal_2026/browse/` named in FETCH_TASKS does not exist and holds only scenes.csv/json, so quick-looks went to `data/browse/nisar_arnab/` (as the lead asked), naming `<YYYY-MM-DDTHHMM>Z_T<trk>_F<frm>.png`, with `_UR` suffix for urgent-response fallbacks. Check `.gitignore` before committing (3 MB each, 14 PNGs ~ 41 MB total).

## Confirmations requested in FETCH_TASKS step 3

- (a) PR exists for 27 Oct T48 F80 DVDV: YES, `NISAR_L2_PR_GCOV_034_048_D_080_2005_DVDV_A_20261027T130151_20261027T130208_P05036_N_P_J_001` (GCOV_V1, 847,249,408 B). PR exists for 28 Oct T55 F10 DHDH: YES, `..._034_055_A_010_4005_DHDH_A_20261028T000107_20261028T000129_P05036_N_P_J_001` (GCOV_V1, 4,110,417,920 B).
- (b) 4 Oct T55 F10: YES, DHDH PR `..._032_055_A_010_4005_DHDH_A_20261004T000106_..._P05023_N_P_J_001` (PROVISIONAL_V1, 4,273,995,776 B), plus a DVDV 2005 frame (0.06 of delta box).
- (c) 8 Nov T48 F80: YES (DVDV PR P05036, 0.93 delta box; also DHDH F80 ~0.00). 9 Nov T55 F10: YES, DHDH PR P05036 (GCOV_V1, 4,278,190,080 B, 0.81).
- (d) T156 and the delta box: the delta-box query returns **0 T156 granules** (confirmed, planner finding stands). The wider sea-box query (81-85E, 15-18N) does return 10 T156 granules (frames 9-11 on 11 Oct, 23 Oct, 4 Nov); they do not intersect the delta box.

## Method

Queries (GET, no auth; HTTP 200; results saved raw):
- delta: `https://api.daac.asf.alaska.edu/services/search/param?dataset=NISAR&processingLevel=GCOV&intersectsWith=POLYGON((81.6 16.2,82.6 16.2,82.6 17.1,81.6 17.1,81.6 16.2))&start=2026-10-01T00:00:00Z&end=2026-11-14T23:59:59Z&maxResults=1000&output=geojson` -> 30 granules
- sea: same with `POLYGON((81 15,85 15,85 18,81 18,81 15))` -> 124 granules (superset; all 30 delta granules are inside it; 124 unique)
- CMR: `https://cmr.earthdata.nasa.gov/search/collections.json?keyword=NISAR&page_size=200` -> CMR-Hits 52, saved to `data/reference/cmr_nisar_collections.json`
- docs: `https://nisar-docs.asf.alaska.edu/gcov/` (WebFetch)
- browse: `_LATLON.png` and `_LATLON.kml` URLs taken from each granule's `browse` / `additionalUrls` fields.

**Coverage fraction method:** each granule's footprint polygon (GeoJSON geometry from the API) is loaded with shapely; `fraction = footprint.intersection(box).area / box.area` with the box as a rectangle in lon/lat degrees (planar; the box is 1.0 x 0.9 deg so cos(lat) distortion is <1.5 % and cancels in the ratio). Cross-check: 41x41 regular grid of points inside the box, fraction of points the footprint intersects (`grid_delta` in the full CSV). Max |area - grid| over all 124 granules = 0.013. The area fractions also agree (within 0.03) with the planner's probe values for all 30 granules in `asf_probe_delta_box_20261001_20261114.csv`. Box fractions for both boxes are computed for every granule (`frac_delta`, `frac_sea`).

## Role scenes

| role | granule_id | level / collection | CRID | delta frac | sea frac | size_bytes |
|---|---|---|---|---|---|---|
| L_SEA_CALM_1003 | `NISAR_L2_PR_GCOV_032_048_D_080_2005_QPDH_A_20261003T130133_20261003T130207_P05023_N_F_J_001` | PR / NISAR_L2_GCOV_PROVISIONAL_V1 | P05023 | 0.9791 | 0.4125 | 7474249728 |
| L_COAST_1004 | `NISAR_L2_PR_GCOV_032_055_A_010_4005_DHDH_A_20261004T000106_20261004T000129_P05023_N_P_J_001` | PR / NISAR_L2_GCOV_PROVISIONAL_V1 | P05023 | 0.814 | 0.2848 | 4273995776 |
| L_COAST_T149_1010 | `NISAR_L2_PR_GCOV_032_149_D_080_4005_DHDH_A_20261010T130952_20261010T131027_P05023_N_F_J_001` | PR / NISAR_L2_GCOV_PROVISIONAL_V1 | P05023 | 0.3213 | 0.1712 | 6442450944 |
| L_SEA_CALM_1015 | `NISAR_L2_PR_GCOV_033_048_D_080_2005_DVDV_A_20261015T130150_20261015T130208_P05023_N_P_J_001` | PR / NISAR_L2_GCOV_PROVISIONAL_V1 | P05023 | 0.9436 | 0.2254 | 884998144 |
| L_COAST_1016 | `NISAR_L2_PR_GCOV_033_055_A_010_4005_DHDH_A_20261016T000106_20261016T000129_P05023_N_P_J_001` | PR / NISAR_L2_GCOV_PROVISIONAL_V1 | P05023 | 0.8317 | 0.2857 | 4257218560 |
| L_COAST_T149_1022 | `NISAR_L2_PR_GCOV_033_149_D_080_4005_DHDH_A_20261022T130952_20261022T131027_P05036_N_F_J_001` | PR / NISAR_L2_GCOV_V1 | P05036 | 0.3224 | 0.1721 | 6455033856 |
| L_SEA_EYE_1027 | `NISAR_L2_PR_GCOV_034_048_D_080_2005_DVDV_A_20261027T130151_20261027T130208_P05036_N_P_J_001` | PR / NISAR_L2_GCOV_V1 | P05036 | 0.9174 | 0.2135 | 847249408 |
| L_SEA_EYE_1027_URfallback | `NISAR_L2_UR_GCOV_034_048_D_080_2005_DVDV_A_20261027T130151_20261027T130208_P05036_F_P_J_001` | UR / UR_L2_L_GCOV | P05036 | 0.9173 | 0.2135 | 847249408 |
| L_COAST_1028 | `NISAR_L2_PR_GCOV_034_055_A_010_4005_DHDH_A_20261028T000107_20261028T000129_P05036_N_P_J_001` | PR / NISAR_L2_GCOV_V1 | P05036 | 0.7862 | 0.2746 | 4110417920 |
| L_COAST_1028_URfallback | `NISAR_L2_UR_GCOV_034_055_A_010_4005_DHDH_A_20261028T000107_20261028T000129_P05036_F_P_J_001` | UR / UR_L2_L_GCOV | P05036 | 0.7862 | 0.2746 | 4114612224 |
| L_COAST_T149_1103 | `NISAR_L2_PR_GCOV_034_149_D_080_4005_DHDH_A_20261103T130953_20261103T131027_P05036_N_F_J_001` | PR / NISAR_L2_GCOV_V1 | P05036 | 0.3213 | 0.1676 | 6291456000 |
| L_SEA_AFTER_1108 | `NISAR_L2_PR_GCOV_035_048_D_080_2005_DVDV_A_20261108T130151_20261108T130208_P05036_N_P_J_001` | PR / NISAR_L2_GCOV_V1 | P05036 | 0.9319 | 0.2135 | 851443712 |
| L_COAST_1109 | `NISAR_L2_PR_GCOV_035_055_A_010_4005_DHDH_A_20261109T000107_20261109T000130_P05036_N_P_J_001` | PR / NISAR_L2_GCOV_V1 | P05036 | 0.8114 | 0.2846 | 4278190080 |
| L_COAST_1109_URfallback | `NISAR_L2_UR_GCOV_035_055_A_010_4005_DHDH_A_20261109T000107_20261109T000130_P05036_F_P_J_001` | UR / UR_L2_L_GCOV | P05036 | 0.8114 | 0.2847 | 4349493248 |

Processing level values in `scene_manifest.csv`: `PR (provisional)` = NISAR_L2_GCOV_PROVISIONAL_V1, `PR (validated, GCOV_V1)`, `UR (urgent response)`. All 124 `download_url` values start with `https://nisar.asf.earthdatacloud.nasa.gov/`. The manifest lists every granule from the sea-box query; only planner scenes have a `role`. 'Track 55 candidates' (4 Oct, 16 Oct, 28 Oct, 9 Nov) are the L_COAST_* roles; the original plan (T156 pair 23 Oct / 4 Nov) has no granule that covers the delta box so it has no rows with delta coverage; T156 sea-box granules are in the manifest without role.

## S-band check (CMR)

52 CMR hits for keyword NISAR; short names include NISAR_L2_GCOV_{BETA,PROVISIONAL,}_V1, GSLC, GUNW, GOFF, L1 RSLC/RIFG/RUNW/ROFF, L0B RRSD/CRSD, L3_SME2, UR_L1, UR_L2, UR_L0B_RRSD, plus ancillary (OE, RP, TEC, DEM, WATERMASK, VWC, ANC_AUX, COP, LRCLK_UTC, OROST, STUF) and non-NISAR hits (OPERA, UAVSAR, ECMWF, etc.). Full list in `data/reference/cmr_nisar_collections.json`. **None is S-band**: titles/summaries are all L-SAR / generic; no collection title contains 'S-band' (only a title check was done; S-SAR data is expected from ISRO Bhoonidhi, `S_GCOV_DELTA` stays blocked_credentials). Cannot be discovered further without login.

## GCOV dataset paths (documented, https://nisar-docs.asf.alaska.edu/gcov/)

`[A|B]` = frequency A or B:
- mask: `/science/LSAR/GCOV/grids/frequency[A|B]/mask`
- numberOfLooks: `/science/LSAR/GCOV/grids/frequency[A|B]/numberOfLooks`
- rtcGammaToSigmaFactor: `/science/LSAR/GCOV/grids/frequency[A|B]/rtcGammaToSigmaFactor`
- HHHH: `/science/LSAR/GCOV/grids/frequency[A|B]/HHHH`
- VVVV: `/science/LSAR/GCOV/grids/frequency[A|B]/VVVV`
- xCoordinates, projection: NOT documented as paths on that page (page only says products are in UTM for their location). The product spec PDF (https://nisar.asf.earthdatacloud.nasa.gov/NISAR-SAMPLE-DATA/DOCS/NISAR_D-102274_RevD_NASA_SDS_Product_Specification_L2_GCOV_w-sigs.pdf, found by search, not opened) should list them. Note the page text came via a summarising fetch, not verbatim.

## Files written (path, bytes, sha256)

- `data/raw/asf/asf_delta_20261001_20261114.json` 618163 0adc862b6a1053d57462acbd23a1ae832dd80a4b0eb098a547a4b8e22c1323d3
- `data/raw/asf/asf_sea_20261001_20261114.json` 2490934 564788ddafb427744fd93267f4c44c2165efef23dfa0cf6bd6f3e24b306fde65
- `data/reference/scene_manifest.csv` 105796 7e8220d7df188820717b322f9a429677796077ed78a7a243e03525def926438c
- `data/reference/scene_manifest_full.csv` 128678 ce2e94960bf1a8c1186a5cdb9e30ec68988896a7de1b4043f5639166910153a8
- `data/browse/nisar_arnab/2026-10-03T1301Z_T48_F80.png` 3062529 752466813046bc7a9cfc19aef258ded601c46a031bf52c75aaa7129bcbeadd90
- `data/browse/nisar_arnab/2026-10-04T0001Z_T55_F10.png` 2947497 ea9b5eccfc92d2ecc25bac8e2ffba0d21c57b2c34875f068ba6004bf83183270
- `data/browse/nisar_arnab/2026-10-10T1309Z_T149_F80.png` 4725400 e851f8accdda9f55abdedbd240290ec3795fdcc76d5dedcbe71724f7ae236d79
- `data/browse/nisar_arnab/2026-10-15T1301Z_T48_F80.png` 1613656 844c7c159eb511ed4d69cc016a7b475b5a8b1e79690f31b7dacc46dcf8ca7d4b
- `data/browse/nisar_arnab/2026-10-16T0001Z_T55_F10.png` 2908866 f2b573fd3f3b39a46b625aeb5d0e7730eb05297595db8268ecc0fe23b6c80b12
- `data/browse/nisar_arnab/2026-10-22T1309Z_T149_F80.png` 4728234 1b305b9b895ac879fcc27734a4a4b01d912d24717ce0ed63aecb6e81c60f6d85
- `data/browse/nisar_arnab/2026-10-22T1309Z_T149_F80.kml` 571 d72232a1c12d53f10aa2d28834152bce59ece72fd49043ea08b45a65c2af0188
- `data/browse/nisar_arnab/2026-10-27T1301Z_T48_F80.png` 1810606 47c9528f2016cf4327054c65e0004671b77e3ab539606f9f8850889cef11f6cf
- `data/browse/nisar_arnab/2026-10-27T1301Z_T48_F80.kml` 563 4f33dd5901f03f8d955245664ed46991c506fb9e9fc134ff8fff6cc7ea2a954f
- `data/browse/nisar_arnab/2026-10-27T1301Z_T48_F80_UR.png` 1810954 cde491e18734a387d6259991244d9720ba7e00f2cad0aa91ae20f3dfe4c8314e
- `data/browse/nisar_arnab/2026-10-27T1301Z_T48_F80_UR.kml` 563 ddebbf72814be3ccfc9387b848c7377182a5cd33af30a10791ddd203bec9585d
- `data/browse/nisar_arnab/2026-10-28T0001Z_T55_F10.png` 2887429 2c18b7c185791b227421e0b60a21b2b2090bbfa097350aca475be9b7f444da87
- `data/browse/nisar_arnab/2026-10-28T0001Z_T55_F10.kml` 571 0784606a3f1451c283f3089e66b6d6ccce9be6d67d54c6ffd1febb839b6272fa
- `data/browse/nisar_arnab/2026-10-28T0001Z_T55_F10_UR.png` 2908328 037f5527a4473422ed87438e60e1ea7758963056b335faebde83c3b37b1661cc
- `data/browse/nisar_arnab/2026-10-28T0001Z_T55_F10_UR.kml` 571 e1a03682410fda51458424202e160cab109503e45ccd05d21ce868be8d7a0e6a
- `data/browse/nisar_arnab/2026-11-03T1309Z_T149_F80.png` 4619326 7a3a1877b5d016644fbda5067d615b6ae81584a14dcddaf148cdc9a04b4ccfc1
- `data/browse/nisar_arnab/2026-11-03T1309Z_T149_F80.kml` 571 10b56398de257a8fc92f03337cfc683ece5c4df38df55933db5e4f7536baccdd
- `data/browse/nisar_arnab/2026-11-08T1301Z_T48_F80.png` 1742218 befa6885c7b7da0c5a52b89d53b0724dd3f2864839e33d15a52945f5f100d423
- `data/browse/nisar_arnab/2026-11-08T1301Z_T48_F80.kml` 563 3c792310250f3cc850613afa73308af7c6b7f37b329befdbf554698f161190ba
- `data/browse/nisar_arnab/2026-11-09T0001Z_T55_F10.png` 2952541 3b109ae8c308c985d8dafaa1f34ffa8cd0f1df519dc067341e546fb665beb271
- `data/browse/nisar_arnab/2026-11-09T0001Z_T55_F10.kml` 571 3d46fbaf2402083e78a7e58139acedb906e3cbe592660446b954a2705389088c
- `data/browse/nisar_arnab/2026-11-09T0001Z_T55_F10_UR.png` 2981425 3604a188ad5ecba0793b416829d1168f92fea44e9f50e77cd7d2fd30231725d8
- `data/browse/nisar_arnab/2026-11-09T0001Z_T55_F10_UR.kml` 571 450dfbf1fd9bc52b2ca67f34b763e812b1e9aded859a2fdb572ed6d99b8e2541
- `data/reference/cmr_nisar_collections.json` 196033 511de13b38b312cd341c920b747a62d36fde5d08e667b3641524bfe40b71c7dc
- `src/fetch/D_asf_manifest.py` (script); `data/logs/package_D_run.json` (machine log with all URLs).

## Failures

- 15 x HTTP 401 (3 retries x 5 files): `_LATLON.kml` of the 5 provisional-collection scenes (3, 4, 10, 15, 16 Oct), redirect to urs.earthdata.nasa.gov login. Skipped per rule 2.
- `python -m venv .venv` on the mounted folder failed (ensurepip error); used `/tmp/v`.
- Verification: all 14 PNGs open with PIL (`verify()`); manifest parses (124 rows); every role row has h5 url with the required prefix; every browse PNG for role scenes downloaded.

## Status set in data/sources.yaml
- ASF_MANIFEST: done
- NISAR_BROWSE_NEW: done (PNGs for all role scenes; KMLs for 5 provisional scenes blocked, see failures)
- NISAR_S_CMR_CHECK: done (no S-band collection found on CMR)
