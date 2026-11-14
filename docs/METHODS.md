# Methods: how the derived products are made (W3-A, 14 Nov 2026)

Everything below is computed by `tools/build_web.py` from the H5 subsets in `data/h5/`. Nothing is typed in by hand.
Run `python tools/build_web.py` (add `--write-manifest` once to point the class layers at the PNGs). Numbers quoted here are from the
14 Nov build; the exact values for every build are in `data/web/class_stats.json`, `data/processed/mandal_rank.json` and
`data/processed/profile.json` (each has a `provenance` block).

## 1. Class maps (new open water, wet or flooded crops, no change)
Input: the L-band coast scenes of track 55 on one 20 m UTM 44N grid (5008 x 5360 px, checked identical): baseline 4 Oct and 16 Oct
(both PROVISIONAL products) and EVERY later coast scene (today 28 Oct, landfall day, scene 00:01 UTC, and 9 Nov; a new scene is picked up automatically, a scene on a different grid is skipped with a warning), HH and HV.

Steps
1. Valid pixel = finite HH and HV and `aux/mask == 1` on both baseline dates (threshold, permanent water and noise use only these) and, for each event date, on that date too; 2 px next to no-data are dropped.
2. Speckle: each image is averaged 3 x 3 pixels (60 m) in linear power, then converted back to dB.
3. Baseline = mean of 4 and 16 Oct in linear power.
4. Water threshold T on HH: Otsu on the pooled baseline HH histogram = **-12.3 dB** (histogram modes -18.8 and -5.2 dB, histogram valley -14.45 dB).
5. Permanent water (excluded from every share): smoothed HH < T on both baseline dates (3098 km2 in the box, sea and ponds).
6. Noise of the change measure: robust (MAD) sigma of the 16 Oct minus 4 Oct difference over land, HH 0.88 dB, HV 0.93 dB; its median (+0.11 / +0.19 dB) is removed from event changes.
7. Classes, change = event minus baseline, k = 3 sigma:
   - likely new open water: baseline HH >= T, event HH < T, HH falls >= 2.65 dB and HV falls >= 2.78 dB
   - likely wet or flooded crops: not water, event HH >= T, HH rises >= 2.65 dB (double bounce) and HV rises >= 0.93 dB (1 sigma)
   - likely no change: every other valid land pixel
8. Uncertainty: the same rules at k = 2 and 4 sigma. In mandal tables the error is the largest share shift between k = 3 and k = 2 or 4.
9. Control: the same rules applied to 16 Oct against 4 Oct (a "normal fortnight") give the share of land that changes anyway.

Result (km2 and % of valid land, k = 3): 9 Nov new water 83.7 km2 (1.60 %, range 61 to 108 km2 for k 4 to 2), wet crops 47.5 km2 (0.91 %);
28 Oct new water 7.7 km2 (0.15 %), wet crops 139.7 km2 (2.67 %); normal fortnight new water 1.8 km2 (0.04 %), wet crops 112.4 km2 (2.14 %).
With the histogram valley (-14.45 dB) as T instead of Otsu, 9 Nov new water is 60 km2.

Display PNGs: `data/web/class_{20261028,20261109}_{new_water,wet_crops,no_change}.png`, RGBA, lat/lon, nearest-neighbour warp to <= 3000 px
(about 36 m, so thin 20 m features thin out on screen; all counts are on the 20 m grid). Colours from the manifest: water #2A6FB0, crops #E09A2B, no change pale grey, low alpha.

## 2. Mandal ranking (W3-H update)
Every coast date after the baseline is tallied; `mandal_rank.json` top level (`rows`, `flagged_not_ranked`) = the newest date, `by_date[YYYY-MM-DD].rows` = every date (ranked and flagged rows).
Per row: `water_pct`, `crops_pct`, `err` (= `water_err`), `total_pct` (water + crops) and `total_err`, `normal_pct`, `normal_water_pct`, `change_vs_normal_pp` (= total_pct - normal_pct) and `water_change_vs_normal_pp`,
`coverage_pct`, `area_km2` (valid, non-permanent-water land the radar saw; also `land_km2`), `water_km2`, `crops_km2`, `flooded_km2` (= water + crops, i.e. share x area), `rank`, `rank_water`.
**`rank` follows total likely flooded (water + crops)**, as PRO review #3 asks. **Headlines use water only** (`rank_water`, `water_pct`, `water_km2`): the wet-crops class is not separable from normal field change (limitations below), so a mandal is never called flooded because of crops. The story rule is in `data/story_rules.json` (`flooded_mandal.class_basis = "water"`). The old text below describes the first version, which ranked by water only.

(first version) 
`data/processed/mandals.geojson` polygons are rasterised on the 20 m grid. For each mandal: share of valid, non-permanent-water pixels in each class
(9 Nov = `water_pct`, `crops_pct`; 28 Oct under `oct28`), `normal_pct` = water + crops share of the normal-fortnight control, `coverage_pct` = valid land share of
the mandal inside the grid. Ranked by `water_pct` (9 Nov) among mandals with >= 50 % valid coverage, >= 50 % of the mandal inside the coast footprint and >= 1250 valid pixels;
the rest are listed in `flagged_not_ranked`. District names come from `data/interim/C/mandal_district_2022_complete.csv`.

## 3. Eye profile
Scene: `L_SEA_20261027_T048.h5`, VV, 100 m, acquired 13:01:51 to 13:02:08 UTC (VALIDATED).
- Eye centre: VV block-averaged to 500 m cells, 5 km Gaussian smoothing (NaN aware), candidates only >= 30 km from no-data and from land and within 150 km of the interpolated IMD fix;
  the eye is the local minimum (lowest within 10 km) with the largest prominence (12 to 25 km ring mean minus minimum). Exactly one candidate qualified. Centre moves <= 1.4 km for smoothing 3 to 8 km.
- `points`: azimuthal-mean VV (linear power) in 5 km rings, minus the eye floor (mean inside 3 km), error = standard error across 8 azimuth sectors. `points_abs_vv_db`: absolute VV, 1 km rings.
- Eye radius: where the 1 km profile reaches half way between the core and the eyewall maximum; error = bootstrap over sectors.
- `transect`: absolute VV along the along-track (azimuth) direction through the eye (bearing from a fit to the swath edges), 4 km wide strip, 1 km bins; chosen along track because the incidence angle, and so the VV level, is constant along it.

## Limitations (read before quoting a number)
- Single band: L-band only. S-band is not used yet.
- The two baseline scenes (4 and 16 Oct) are PROVISIONAL products; the event scenes are VALIDATED. For the land classes a calibration offset between them cannot be excluded; for the sea difference it was checked, see "Sea difference calibration check" below. HV on 28 Oct sits +1.9 dB above baseline over the whole land area (HH +0.05 dB), 9 Nov +0.8 dB.
- Speckle: 20 m pixels are noisy even after 3 x 3 averaging; the "normal fortnight" control shows the false-alarm level.
- Wet crops is not separable from normal field change: the control flags 2.1 % of land, 28 Oct 2.7 %, 9 Nov 0.9 %. Treat that class as unproven.
- New open water is clearly above the control (1.6 % against 0.04 %), but 9 Nov also contains Cyclone Murasu (1 to 3 Nov) and the Godavari river peak, not Arnab alone. Water under dense crops can be missed; wind-roughened water can look bright and be missed.
- No ground truth: no flood extent map, field data or optical image was used to validate any class.
- The water threshold changes the water area by about 30 % (Otsu against valley); the sigma threshold by about 25 % either way.
- Eye: faint in L-band VV (prominence 0.8 dB, core to ring contrast 2.4 dB); the azimuthal profile mixes near and far range, so its level beyond about 60 km carries an incidence-angle trend. One scene, no wind speed is derived.

## Histograms and ramps (W3-H phase 2)
- Every layer json has `hist`: `range_db` [-35, 5], `bin_db` 0.5, `counts[pol]` (raw pixels, HH/HV or VV/VH, out-of-range values clipped into the end bins), `n_valid[pol]`. Coast layers also have `counts_smoothed3x3.HH/HV` (the 3 x 3 smoothed image the class rules use) and `water_threshold_db` {pol HH, value -12.3} drawn on the smoothed histogram.
- Backscatter PNGs stay greyscale (-25..0 dB). The sea difference PNG uses a colour-blind-safe diverging blue - white - orange ramp, -15..+15 dB; the stops are in the json (`ramp.stops`, with labels) and in the manifest layer so the UI can draw the legend.

## Live story (W3-H phase 2)
`tools/build_story.py` turns the numbers above into plain-language text with templates only (no model at build time). A mandal counts as flooded when likely new open water (water class only) is >= 3 % of its seen land, >= 2 times its normal-fortnight water share, and the radar saw >= 50 % of it. "Went down / up" needs a change of at least max(1 point, 2 x error). The `provisional` badge is on when the newest scene or either baseline scene is a PROVISIONAL product (today the baseline is). Where an event file lists a confounder for a scene date (9 Nov: Cyclone Murasu and the river peak) the text says so.

## Findings files and where thresholds may not hold
Each coast pass after the baseline gets `data/processed/findings/<date>.json`, written once and revised only when its inputs hash changes. The thresholds (water -12.3 dB, 3 sigma, normal-fortnight control) were tuned on Arnab-era scenes: track 55, 4 and 16 Oct baseline (both PROVISIONAL), post-monsoon, kharif paddy standing, then 28 Oct and 9 Nov. They may not hold in other conditions. In the dry season or at rabi harvest, drained and bare fields can look like change; during kharif harvest from November, cut or flooded paddy fields change brightness without any storm. Wind-roughened water, dense crop cover over water and a different incidence angle (another track) all shift the HH threshold. The control is one fortnight only, so its false-alarm level is a single sample. A pass in an adjacent season gets lower confidence and a caveat; a pass in a distant season or on a track with no baseline gets no change numbers. Provisional baselines may carry a calibration offset against validated passes. No sea finding is made, because the sea method is not validated.

## Wet crops: HH, HV and HH/HV ratio tested, not adopted (14 Nov)
Three alternatives to the wet-crops rule were compared with the normal-fortnight control (16 vs 4 Oct) at k = 2, 3, 4 sigma, with and without removing each date's own land-median change: HH rise alone, HV rise alone, and HH-minus-HV (dB) rise. HH alone is no better than the control (event/control 1.2 on 28 Oct at k = 3). The HH/HV ratio reaches 2.0 only after median removal and falls to 1.0 at k = 4. HV alone flags 18 % of land on 28 Oct (control 1.8 %), but the 1.9 dB land-wide HV offset accounts for most of the raw flag (33 %) and the remainder follows baseline brightness and region, the event-minus-baseline spread is twice the control's, and baselines (PROVISIONAL) and events (VALIDATED) differ in product version. This is not evidence of flooding, so the wet-crops class stays unproven and the headline uses open water only. Details: `docs/review/LBAND_TEST.md`.

## Sea difference calibration check
The sea difference uses the 15 Oct scene (PROVISIONAL) as reference. Over the sea (more than 1 km offshore, common valid pixels) 27 Oct is about 4.2 dB brighter in VV (about 1.9 dB in cross-pol) and 8 Nov is about 0.1 dB (-0.2 dB), with the 8 Nov difference flat across the swath within about 1 dB. A product-version offset between PROVISIONAL and VALIDATED scenes is therefore likely small next to the 27 Oct signal, which is probably storm roughening. The 3 Oct scene was not used as a second reference: it is a different acquisition mode and its VV differs from 15 Oct by +2 dB (west) to +9 dB (east) while cross-pol agrees within 0.5 dB, cause not determined. ERA5 winds exist only for 15 and 27 Oct, so the calm state of 3 Oct and 8 Nov is unverified. The ASF NISAR documentation says provisional products are calibrated at limited sites only; the Data User Guide itself was not checked. No wind speed is derived. Details: `docs/review/LBAND_TEST.md`.
