# Mangrove HV-minus-HH change at Coringa (EXPERIMENTAL, analysis only)

Plan: `docs/PLAN_P1_P2.md` section P2-B. Code: `tools/experimental/mangrove_change.py` (not in `run_all.py`, not in the UI).
Output: `data/processed/experimental/mangrove_change.json` (schema `mangrove-change-v0`, with provenance and sha256 of every input).
Credit: **Global Mangrove Watch (CC BY 4.0)**. Full citation (built from the Zenodo record, confirm on globalmangrovewatch.org before submission): Bunting, P., Hilarides, L., Rosenqvist, A., Zanaga, D., Van De Kerchove, R., Lucas, R., Castro Brandao Vaz dos Santos, P. (2024). Global Mangrove Watch: Annual Mangrove Extent (Version 4.0.19) [Data set]. Zenodo. https://doi.org/10.5281/zenodo.12756047. CC BY 4.0.

Run: `.venv/bin/python -I tools/experimental/mangrove_change.py` (about 2 min, 1000 resamples, peak memory about 2.6-2.9 GB).

## Method in one paragraph
GMW 2020 extent (3 tiles) is put on the 20 m UTM 44N grid of the COAST H5 files (a cell is mangrove if at least half of its source pixels are 1; eroded 1 cell; permanent water removed): 453,180 cells = 181.3 km2 (203.3 km2 before erosion). HH and HV are smoothed 3 x 3 in linear power with the same code as the class maps. R = HV_dB - HH_dB. Change D = R(event) - R(baseline), baseline = linear-power mean of 4 and 16 Oct. Control = R(16 Oct) - R(4 Oct) in the same mask (one-date baseline, so slightly noisier). Three numbers per date: **uncorrected** (median D in mangrove), **land-wide** (minus median D over all other valid land at least 2 km from the mask), **matched** (minus the median D of reference land reweighted to the same mix of baseline-HV 1 dB bin and 10 km ground-range band as the mangrove; 91 strata, all mangrove pixels matched). Error bars: block bootstrap on the UTM grid, 1000 resamples, 1 km blocks (408 mangrove blocks), sensitivity 500 m (1220) and 2 km (146); the same resamples are used for control and events so the event-minus-control difference is paired.

## Results (dB, median change of HV minus HH; 95 % range from the 1 km bootstrap; 500 m and 2 km give the same picture)
| | uncorrected | land-wide corrected | matched corrected |
|---|---|---|---|
| normal fortnight (16 vs 4 Oct) | +0.02 (0.01 to 0.03) | -0.07 (-0.09 to -0.06) | +0.01 (-0.02 to 0.04) |
| 28 Oct | +0.00 (-0.02 to 0.03) | -1.88 (-1.98 to -1.79) | -1.07 (-1.24 to -0.93) |
| 9 Nov | +0.13 (0.11 to 0.16) | -1.20 (-1.26 to -1.14) | -0.77 (-0.90 to -0.64) |

Components, uncorrected medians in mangrove (point estimates, no interval): 28 Oct HH +1.90 dB, HV +1.91 dB; 9 Nov HH +0.96, HV +1.10. Land-wide reference: 28 Oct HH -0.08, HV +2.06; 9 Nov HH -0.48, HV +0.87.

## Honest reading
- The ratio itself did not move in the mangrove (uncorrected about 0 on 28 Oct, +0.13 on 9 Nov, within what two normal passes can differ by, 0.02), because HH and HV rose together by about 1.9 dB on 28 Oct. In the reference land only HV rose (the known +1.9 to +2.1 dB HV offset, LBAND_TEST.md), so the ratio rose there.
- The corrected numbers (-1.1 and -1.9 dB on 28 Oct, -0.8 and -1.2 on 9 Nov) are therefore the reference offset subtracted, not a mangrove effect: it is statistically separated from the control (intervals exclude zero and the control at every block size) but the three corrections **disagree in sign** (uncorrected >= 0, corrected < 0). Per the plan this means the change **cannot be separated from calibration differences**. Verdict code for both dates: `not_separable_from_calibration`. If forced to a one-liner: no detectable change in the HV minus HH ratio inside the mangrove before correction; the correction's size and sign depend on an offset that is not uniform across land cover.
- The bootstrap error bars are small (hundredths of a dB) because the mask has about 450,000 cells; they say nothing about the unmodelled systematic (calibration, tide, wetness) which is far larger than them.
- The one thing that stands out is the equal HH and HV rise of about 1.9 dB in the mangrove on 28 Oct, against no HH rise in the reference land. This is observed, not explained: it could be tide or standing water under the canopy, canopy wetness, or a product-version offset; none was tested.

## What may be said
Allowed (also in the JSON, per date): "Experimental. Area mapped as mangrove by Global Mangrove Watch (2020 extent), L-band HV minus HH ... The size and sign of the difference depend on the reference used (uncorrected +0.0 dB, land-wide corrected -1.9 dB, matched corrected -1.1 dB), so any change cannot be separated from calibration differences between the scenes. No ground truth was used, tide state was not controlled, and the baseline scenes are provisional."
Not allowed: damage, loss, die-back, deforestation, cause, area or percent of mangrove affected, "healthy".
Must state: no ground truth; tide not controlled (no tide source retrieved); baselines PROVISIONAL, events VALIDATED; 9 Nov also holds Murasu and the river peak; mask is the 2020 extent, 6 years old, GMW accuracy is global; canopy and soil wetness effects not tested; reference (agriculture) and target (mangrove) have different seasonal drivers.

## Limits of this implementation
- Range band is a proxy: the H5 files carry no incidence angle, so the range direction (14.4 deg north of east in UTM) was fitted from the straight frame-end edge of the swath (1278 rows). The box holds only part of the swath, so bands are in km from the grid origin along that direction.
- Medians in the bootstrap come from 0.05 dB histograms (change clipped to +-10 dB); point estimates are exact medians.
- Reference excludes a 2 km square window around the mask, so land-wide is "all land farther than 2 km".
- Control uses the same strata (from the two-date baseline HV) and the same mask.
