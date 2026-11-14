# L-band tests: wet-crops signal (WP6) and sea calibration (14 Nov 2026)
Scripts: scratchpad `wp6/testA*.py`, `testB2.py` (not in repo). Reuses `tools/build_web.py` functions (`_box_db`, `_erode`, `_otsu`, `_robust`, `read_backscatter`). No repo code or data changed.

## TEST A. Wet crops: is any signal separable from the "normal fortnight"?
Method (as build_web.py): valid = finite HH+HV, mask==1 on both baselines (and on the event date), 2 px edge erosion; 3x3 linear-power smoothing; baseline = linear mean of 4+16 Oct;
permanent water = smoothed HH < Otsu T (-12.30 dB) on both baselines; land = valid, not permanent (13.10 M px = 5241 km2); flag requires event HH >= T (not water).
Control = 16 Oct vs 4 Oct. Sigma per signal = MAD sigma of the control difference over land: HH 0.883, HV 0.928, HH-HV ratio 1.028 dB. Reproduces the current rule: 28 Oct 2.66 %, 9 Nov 0.91 %, control 2.14 % (k=3).
Signals: (1) dHH rise; (2) dHV rise; (3) ratio rise = (HH-HV)_event - (HH-HV)_baseline. Flag = signal - offset >= k sigma.
"normal" offset = control median (what build_web does). "own" = the event date's own land median removed (HV +1.93 dB 28 Oct, +0.84 9 Nov; HH +0.05 / -0.34; ratio -1.51 / -1.10).

Table A1: % of land flagged, 28 Oct / 9 Nov / control, ratio = event/control (28 Oct, 9 Nov)
| signal, offset | k=2 | k=3 | k=4 |
|---|---|---|---|
| current rule (HH>=3s and HV>=1s), normal | 8.61 / 2.56 / 3.52 (2.4, 0.7) | 2.66 / 0.91 / 2.14 (1.2, 0.4) | 0.71 / 0.34 / 1.44 (0.5, 0.2) |
| current rule, own | 2.72 / 2.35 / 3.52 (0.8, 0.7) | 1.28 / 0.99 / 2.14 (0.6, 0.5) | 0.48 / 0.40 / 1.44 (0.3, 0.3) |
| HH alone, normal | 10.66 / 5.06 / 5.52 (1.9, 0.9) | 3.03 / 1.54 / 2.81 (1.1, 0.5) | 0.78 / 0.51 / 1.74 (0.5, 0.3) |
| HH alone, own | 11.53 / 9.40 / 5.52 (2.1, 1.7) | 3.34 / 2.78 / 2.81 (1.2, 1.0) | 0.86 / 0.88 / 1.74 (0.5, 0.5) |
| HV alone, normal | 47.4 / 26.1 / 5.15 (9.2, 5.1) | 33.3 / 18.0 / 1.75 (19.0, 10.3) | 24.2 / 11.7 / 0.68 (35.7, 17.3) |
| HV alone, own | 25.3 / 20.2 / 5.15 (4.9, 3.9) | 17.7 / 13.5 / 1.75 (10.1, 7.7) | 11.3 / 8.1 / 0.68 (16.7, 11.9) |
| ratio alone, normal | 1.36 / 2.36 / 4.24 (0.3, 0.6) | 0.27 / 0.57 / 1.30 (0.2, 0.4) | 0.07 / 0.14 / 0.48 (0.1, 0.3) |
| ratio alone, own | 11.97 / 9.52 / 4.24 (2.8, 2.3) | 2.63 / 2.34 / 1.30 (2.0, 1.8) | 0.49 / 0.57 / 0.48 (1.0, 1.2) |

Spatial check at k=3, own offset (28 Oct / 9 Nov / control). Land within 100 m of permanent water = 22.0 % (500 m: 75.5 %).
| signal | flagged within 100 m of perm. water | within 500 m | flagged px with >=4 of 8 neighbours flagged |
|---|---|---|---|
| current rule | 40 / 30 / 25 % | 90 / 86 / 86 % | 59 / 60 / 82 % |
| HH | 36 / 26 / 30 % | 88 / 82 / 87 % | 61 / 65 / 83 % |
| HV | 5 / 4 / 15 % | 60 / 56 / 77 % | 93 / 92 / 75 % |
| ratio | 32 / 30 / 33 % | 86 / 82 / 83 % | 44 / 52 / 63 % |
(Mandal-level split not done.)

Findings
- HH alone: no separation (ratio 1.2 on 28 Oct, 1.0 on 9 Nov at k=3, own offset). Not a candidate.
- Ratio: after own-median removal 2.0 (28 Oct) and 1.8 (9 Nov) at k=3, 1.0 at k=4. Marginal, hinges on the median removal, and it sits as close to permanent water as the control does (32 vs 33 %). The ratio is mostly HV-driven (HH has no offset), so it adds nothing over HV.
- HV alone: without median removal 33 % of land is flagged on 28 Oct = the +1.9 dB land-wide offset (the shift, not a flood pattern). With it removed HV still gives 17.7 % (928 km2) on 28 Oct and 13.5 % on 9 Nov, event/control 10.1 and 7.7. It meets the numeric rule and is inland (5 % near permanent water vs 22 % of land), patchy-clustered (93 %).
- But HV is not a clean flood signal:
  * Event dispersion is doubled in ALL channels (MAD sigma of event-minus-baseline over land 28 Oct: HV 1.89, HH 1.76, ratio 2.84 dB vs 0.93 / 0.88 / 1.03 in the control). The control (12 days apart, both PROVISIONAL) is not a valid null for events 12 to 36 days later and a different product version, so event/control ratios are inflated by the sigma mismatch.
  * It is not uniform: median dHV by baseline-HV level on 28 Oct is +4.7 dB at -20..-18 dB, +3.6 at -18..-16, +1.8 at -16..-14, +0.7 at -12..-8 (control: +0.8 to -0.2). Dark (-20..-14 dB) fields rise; bright land does not. By region it is +2.5 dB in the west columns and +0.6 to -0.4 in the east / south rows. This pattern fits crop growth or rain wetting of a particular cover class just as well as flooding, or a PROVISIONAL-vs-VALIDATED product effect (baselines are PROVISIONAL, all events VALIDATED, so the two cannot be separated with this data).
  * 928 km2 of flooded crops on 28 Oct next to 7.7 km2 of new open water is not physically credible as inundation.
- Restricting to baseline HV >= -18 dB (80 % of land, sigma re-estimated) gives the same picture: HV 14.2 % vs 1.43 % (9.9x), ratio 2.8x, HH 3.0x.

VERDICT A: HV-alone passes the pre-set numeric rule (>= 2 at k=3, own offset, inland), the ratio marginally (2.0, k=4 fails), HH fails. None CLEARLY wins: the control is not a valid null (2x wider event dispersion), HV's rise is a land-cover-dependent shift that cannot be separated from product version or crop phenology, and no ground truth exists. NO ADOPTION. Keep wet crops labelled unproven and out of headlines. HV change could be shown later as a separate "L-band HV change (not flood proof)" layer only after a same-product-version baseline exists (e.g. a VALIDATED scene before the storm) or an optical/field check.

Proposed METHODS.md text (replace the "Wet crops is not separable..." limitation or add after it):
> Tested and not adopted (14 Nov). Three alternatives to the wet-crops rule were compared with the normal-fortnight control (16 vs 4 Oct) at k = 2, 3, 4 sigma, with and without removing each date's own land-median change: HH rise alone, HV rise alone, and HH-minus-HV (dB) rise. HH alone is no better than the control (event/control 1.2 on 28 Oct at k = 3). The HH/HV ratio reaches 2.0 only after median removal and falls to 1.0 at k = 4. HV alone flags 18 % of land on 28 Oct (control 1.8 %), but the 1.9 dB land-wide HV offset accounts for most of the raw flag (33 %) and the remainder follows baseline brightness and region, the event-minus-baseline spread is twice the control's, and baselines (PROVISIONAL) and events (VALIDATED) differ in product version. This is not evidence of flooding, so the wet-crops class stays unproven and the headline uses open water only.

## TEST B. Sea calibration (track 48, 100 m, VV and cross-pol)
Scenes: 3 Oct (PROVISIONAL, mode QPDH: HV+VV, mask holds values 0-4), 15 Oct (PROVISIONAL, DVDV: VH+VV), 27 Oct and 8 Nov (VALIDATED, VH+VV); identical 3006x3398 grids. HV and VH are treated as the same cross-pol.
Sea criterion: outside `data/reference/land_osm_clip.geojson` land polygon, further than 1 km (10 px) from it, finite in all four scenes, mask==1 on 15 Oct, 27 Oct, 8 Nov. Two sets: (a) also mask==1 on 3 Oct, n = 177,352 px (west part of the swath only); (b) 3 Oct not mask-filtered, n = 2.35 M px. Only 0-200 km from the eye is covered, so there is no storm-free far field.
Weather: ERA5 (`era5_wind_summary.csv`) has only 15 Oct (13 UTC median 2.9 m/s, max 4.6) and 27 Oct (13.3, max 18.6). 3 Oct and 8 Nov wind is NOT in the file, so "calm" is unchecked for them.

Table B1: median dB
| set | 3 Oct | 15 Oct | 27 Oct | 8 Nov |
|---|---|---|---|---|
| (a) VV / cross | -15.19 / -27.32 | -12.89 / -25.82 | -8.69 / -23.89 | -12.78 / -25.99 |
Table B2: median differences, VV / cross-pol (dB)
| pair | (a) mask-matched | (b) full |
|---|---|---|
| 15 Oct - 3 Oct | +2.25 / +1.54 | +5.01 / +0.44 |
| 27 Oct - 3 Oct | +6.58 / +3.44 | +10.04 / +2.87 |
| 8 Nov - 3 Oct | +2.42 / +1.30 | +7.36 / +0.47 |
| 27 Oct - 15 Oct (the map) | +4.24 / +1.88 | +4.64 / +2.18 |
| 8 Nov - 15 Oct | +0.10 / -0.23 | +0.35 / 0.00 |
(27 Oct - 15 Oct VV p5..p95 = +0.1..+11.7 dB in set (b).) Map median +3.7 dB in STATUS is the whole-scene value; sea-only it is +4.2 to +4.6 VV, +1.9 to +2.2 cross.

Trend by column decile (west to east), VV differences, set (b): 8 Nov - 15 Oct: -0.6 +0.1 +0.4 +0.6 +0.2 +0.8 +0.6 -0.1 +0.6 (flat, within 1 dB). 27 Oct - 15 Oct: +2.4 +3.9 +5.2 +5.4 +5.8 +5.7 +3.0 +0.9 +1.6 (storm-shaped, peak in mid swath, tiny in the east). 15 Oct - 3 Oct: +1.6 +2.5 +2.7 -0.3 +2.2 +7.5 +7.5 +9.5 +8.3 (cross-pol: +0.1 to +1.9, flat to the east). 3 Oct VV falls from -13.5 (west) to -24.5 dB (east); 15 Oct VV only from -11.9 to -15.7. Median by distance from the IMD fix: 100 km bins give similar numbers (27-15: +5.2 / +1.1 dB), but only two bins exist.

Conclusions
- The +3.7 dB (4.2 over sea only) is mostly storm signal, not reference calibration. The two VALIDATED/PROVISIONAL pairs that should expose a product-version offset agree: 8 Nov - 15 Oct = +0.1 dB VV, -0.2 cross, flat across the swath (assuming 8 Nov was calm, which is unchecked). The 27 Oct excess is mid-swath-peaked and larger in VV than cross-pol, as expected for roughening in a 13 m/s wind field.
- 3 Oct is NOT a usable second reference for VV: a different acquisition mode (QPDH), different mask semantics, VV 2 to 9 dB above/below 15 Oct depending on range while cross-pol agrees to about 0.5 dB in the east. That points to a mode/range-dependent difference in the 3 Oct VV (not a global calibration offset), or real but unverified wind differences. Cause not determined.
- NISAR documentation: not checked against the Data User Guide itself. A web search of the ASF NISAR docs (provisional known-issues page, dated 30 Jul 2026, CRID P05023) says provisional products are calibrated and validated only at a limited set of sites, intended for exploration, and that no per-scene offset is quoted; Frequency B (5 MHz) has larger radiometric residuals. I did not read that page in full or find a numeric offset, so the 0.1 dB above is our own measurement, not a guide value.
- Recommendation: one sea number may be quoted: "27 Oct VV over the sea within the swath was about +4 dB (cross-pol about +2 dB) brighter than 15 Oct", with the text "reference is a PROVISIONAL scene; the 8 Nov scene differs from it by 0.1 dB (+-1 dB across the swath), so a product-version offset is small compared with the signal". No correction is applied. Do not quote any difference against 3 Oct. Do not turn the number into wind speed. The map's per-pixel colours should keep the PROVISIONAL badge.

Proposed METHODS.md text (add to Limitations, and to section 3 / sea difference):
> Sea calibration check (14 Nov). The sea difference uses the 15 Oct scene (PROVISIONAL) as reference. Over the sea (> 1 km offshore, common valid pixels) 27 Oct is +4.2 dB brighter in VV (+1.9 dB in cross-pol) and 8 Nov is +0.1 dB (-0.2 dB), with the 8 Nov difference flat across the swath within about 1 dB. A product-version offset between PROVISIONAL and VALIDATED scenes is therefore small next to the 27 Oct signal, which is storm roughening. The 3 Oct scene was not used as a second reference: it is a different acquisition mode and its VV differs from 15 Oct by +2 dB (west) to +9 dB (east) while cross-pol agrees within 0.5 dB, cause not determined. ERA5 winds exist only for 15 and 27 Oct, so the calm state of 3 Oct and 8 Nov is unverified. The ASF NISAR documentation says provisional products are calibrated at limited sites only; the Data User Guide itself was not checked. No wind speed is derived.
