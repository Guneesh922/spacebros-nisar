# Worker B report: NISAR L-band coast scenes (T55 F10), delta box

Status: all four scenes streamed, verified and exported. No failures in the end (one transient 403, see below).

## How the data was streamed
`src/fetch/subset_arnab.py` could not run to completion here: the sandbox kills background jobs when each shell call ends (180 s limit). I wrote a resumable variant that reuses the script's own `SCENES`, `window()` and `save_tif()` and reads the same delta box in 250-row chunks cached in /tmp, then assembles the same dB GeoTIFFs (linear power -> 10*log10, non-finite -> NaN, step 1, no decimation). Helper copies: `data/interim/B/{chunk,assemble,png}.py`. Only HHHH and HVHV are saved (the mask / numberOfLooks / rtcGammaToSigmaFactor extras the script would save were not). `data/logs/nisar_l_subset.md` was NOT updated.
Window: rows 13620:23637, cols 11311:22031, 10 m posting, EPSG:32644 (UTM 44N), 10017 x 10720 px.

## Per scene (raw outputs in data/raw/nisar_l/coast/)
All four opened from the PR-named file in the path the script lists (`NISAR_L2_GCOV_PROVISIONAL_V1` for 1004/1016, `NISAR_L2_GCOV_V1` for 1028/1109). The UR fallback was never needed or used, so there is no UR orbit-precision caveat for these outputs; the validated ones are the PR-named files stored in the V1 collection.

| Scene | Date | Status | Collection | HH median dB | HV median dB | NaN frac |
|---|---|---|---|---|---|---|
| L_COAST_1016 | 16 Oct | OK, before | PROVISIONAL_V1 | -10.66 | -20.12 | 0.173 |
| L_COAST_1028 | 28 Oct | OK, +4 h | GCOV_V1 (validated) | -9.75 | -16.77 | 0.219 |
| L_COAST_1109 | 9 Nov | OK, +12 d | GCOV_V1 (validated) | -11.61 | -19.26 | 0.193 |
| L_COAST_1004 | 4 Oct | OK, normal start | PROVISIONAL_V1 | -10.62 | -20.35 | 0.191 |

HH and HV NaN masks have the same fraction in each scene. Coverage of the delta box is 78-83% (NaN 17-22%), as the plan predicted. NaN fractions differ between dates because the frame edge differs a little per pass; the 28 Oct frame covers least (78%).
Stream time: roughly 7-10 min per scene of actual reads (about 6-8 s per 250-row chunk per pol, two scenes in parallel), spread over several calls. 1004 hit one HTTP 403 (signed URL) mid-stream on the first attempt; resuming from the cache worked, no data lost.

## Files, sizes, sha256
| File | Bytes | sha256 |
|---|---|---|
| 2026-10-04_T55_HHHH.tif | 305239685 | e5fb6d0fcdaa29f72d652c298421f09565724c3a3b61f5842c7348eb948ff231 |
| 2026-10-04_T55_HVHV.tif | 295096417 | eb9ada356c06782aa226370f5b11d5a693f7382e33903b23a6898b0d7e2e950d |
| 2026-10-16_T55_HHHH.tif | 311731692 | 094c95d7fe5afaa2e003f74fcce7af633847423c089a154e0ac15c632366d3cc |
| 2026-10-16_T55_HVHV.tif | 301511787 | ca7da994ceb1261a5ea2bac1d2b6e31de9d7e8b5d252207d75f71a9a1a8ec41f |
| 2026-10-28_T55_HHHH.tif | 295168391 | 99e26da89bafab6fc8bb4ea4b48c53954b6f100e3a1349b7dedfb53ba5f1a097 |
| 2026-10-28_T55_HVHV.tif | 286507468 | cfc1af913be485ba191e775f10919999512845c33ae58ede93bbe19983373c4d |
| 2026-11-09_T55_HHHH.tif | 303666626 | ccea8e8cb802e00650238ad5c3f2894f68168954ccb7450b59bc1697f6a9fee5 |
| 2026-11-09_T55_HVHV.tif | 295105330 | 8d4fc78993f3b62569c60405d7fdb1f78cdacfd66c9d192f637dbd0d6d1206ed |

## Grid check
All four dates, both pols: identical shape (10017, 10720), CRS EPSG:32644, transform (10, 0, 563830, 0, -10, 1891320), nodata NaN, float32. No resampling was needed. The "aligned" GeoTIFFs in `data/interim/B/aligned/` are therefore byte-for-byte copies of the raw files (same sha256 as above), named `nisar_l_coast_<YYYYMMDD>_t55_<hh|hv>_db_aligned.tif`.

## Web PNGs (data/interim/B/)
`nisar_l_coast_{20261004,20261016,20261028,20261109}_t55_hh.png`: greyscale HH dB, RGBA with NaN transparent, 670 x 626 px (16 x 16 block mean of dB at 10 m, about 160 m pixels), 471-512 KB each (limit 600 KB). One shared linear stretch for all four: -21.55 dB (black) to -3.66 dB (white) = pooled 2nd-98th percentile. Full numbers incl. sha256 in `B_png_stats.json`.
Bounds WGS84 `[[S,W],[N,E]]` = `[[16.1948, 81.5972],[17.1055, 82.6075]]` (bounding box of the UTM rectangle 563830,1791150 to 671030,1891320). The image is in UTM, so on a lat/lon rectangle it is a close approximation (zone 44 central meridian is 81 E, so the rotation is small). These are the true bounds for the placeholders `nisar_l_coast_20261004/20261016_t55_hh`, replacing the inferred ones (the real box is the delta box, not the full frame).

## Caveats
- 1004 and 1016 are provisional-release products; 1028 and 1109 are validated-collection files. Different calibration versions could shift absolute dB a little between provisional and validated dates (medians of 4 Oct and 16 Oct agree within 0.04 dB, so no visible offset).
- 28 Oct HH/HV medians are higher (HV -16.8 vs about -20 dB) consistent with wet/rough surface after landfall; this is an observation, not a classification.
- Nothing was written to data/processed/, manifest.json or sources.yaml. The run also wrote 3 GB to /tmp which is cleaned except /tmp/Bwork/cache remnants.
