# Worker F report: three-class change maps and mandal ranking (Sat 14 Nov 2026)

All outputs are in `data/interim/F/`. Nothing in data/processed, app, manifest.json or sources.yaml was touched. Scripts: `ml.py` (multilook), `jrc.py` (water mask), `cls.py` (classifier), `final.py` (PNGs, mandal stats).

## Method and parameters
- Input: the four aligned dB GeoTIFFs (T55, 10 m). Multilook 5x5 block mean in LINEAR power, back to dB, giving a 50 m grid of 2003 x 2144 (edge rows 10016-10017 dropped). A block is NaN if any of its 25 pixels is NaN.
- Reference: 16 Oct (provisional product). Storm pairs: 16 Oct to 28 Oct and 16 Oct to 9 Nov. Normal pair: 4 Oct to 16 Oct (both provisional, so same calibration; medians differ by 0.04 dB). Change = later minus earlier, per polarisation.
- Masks: NaN in any of the 8 rasters; JRC permanent water (occurrence >= 90 %, max-resampled to 50 m, then dilated by 1 px = 50 m; this masks 47 % of the delta box, mostly sea); NaN-union dilated by 2 px (100 m) as a swath-edge guard. Layover/shadow: no mask layer was saved by Worker B (only HHHH and HVHV), so layover was NOT separately masked. Valid land pixels after masks: 2,261,289 (50.6 % of the grid).
- Normal-pair spread (valid land): HH change median +0.128 dB, robust sigma (1.4826 MAD) 0.965 dB; HV median +0.195 dB, sigma 1.006 dB. HH percentiles (0.5/1/2.5/5/50/95/97.5/99/99.5): -3.18, -2.65, -2.02, -1.58, +0.13, +2.15, +3.12, +4.84, +6.13 dB. The distribution is right-skewed: a heavy positive tail exists even without a storm.
- Deviation d' = change minus the normal-pair median. Thresholds (k = 3 sigma base):
  - Likely new open water: HH after < -17 dB AND HH before >= -17 dB AND d'HH <= -3 sigma (-2.9 dB). The -17 dB level: land HH on 16 Oct has p1 = -18.4, p5 = -15.1, median -5.8 dB, with no bimodal split once permanent water is masked; only 2.5 % of land is already below -17 dB before the storm, so -17 dB picks the dark tail, and the "before >= -17" clause stops pre-existing dark ponds, aquaculture and wet fallow from counting as new. Sensitivity of this level on 9 Nov: -16 dB gives 1.32 %, -17 dB 0.97 %, -18 dB 0.49 %.
  - Likely wet or flooded crops: d'HH >= +3 sigma (+2.9 dB) AND d'HV >= +1 sigma (HV agreement), not water.
  - Likely no change: everything else valid.
- Sensitivity: k = 2 and k = 4 (that is +/-1 sigma on both thresholds; the -17 dB level fixed). The error per class (global or per mandal) = largest absolute shift of the share across k = 2 and 4. This captures threshold uncertainty only, not calibration, speckle or the Murasu confound.

## Class shares (percent of valid land pixels)
| Pair | water k=3 (k=4 to k=2) | crops k=3 (k=4 to k=2) |
|---|---|---|
| Normal 4 to 16 Oct (false-positive rate) | 0.015 (0.006 to 0.045) | 1.89 (1.23 to 3.17) |
| 16 Oct to 28 Oct | 0.075 (0.056 to 0.097) | 3.29 (0.98 to 9.12) |
| 16 Oct to 9 Nov (primary) | 0.97 (0.83 to 1.33) | 0.99 (0.35 to 2.81) |

False-positive reading: applying the same thresholds to the normal pair labels 0.015 % of land as "new water" (347 px, 81 % of them within 2 km of permanent water, i.e. coastal and river margin pixels) and 1.9 % as "wet crops".

## Honest assessment
- New open water on 9 Nov (0.97 %) is about 60x the normal-pair rate (0.015 %), so that signal clearly stands out. Affected pixels drop from a median HH of -6.8 dB to -18.0 dB (HV -17.9 to -22.7 dB), which fits flooded or ponded fields, not noise. But it is the combined Arnab + Murasu + river-peak (about 2 Nov) state: the 9 Nov scene cannot be attributed to Arnab alone. The top mandals are mostly inland (Nidadavole, Undrajavaram, Tanuku), not coastal, which also fits post-storm river or canal overflow and field ponding rather than surge. Ponding for rabi transplanting or harvest-season drainage is also dark in HH and could contribute; paddy calendar not checked against crop data.
- Wet/flooded crops is NOT a reliable storm signal here. The normal pair already gives 1.9 % at k = 3, which is higher than the 9 Nov storm pair (0.99 %). The 28 Oct pair gives 3.3 % (about 1.7x normal) and is very threshold-sensitive (1.0 % to 9.1 %), with HV rising a median 1.8 dB overall (rain-wet surfaces, rain still falling about 4 h after landfall). Do not present the crops class as measured flooding; it is "change in HH/HV brightness, mixed with the usual crop-calendar change".
- 28 Oct water share (0.075 %) is tiny: with rain falling and a wind-roughened surface, open water was not calm and dark then; do not read this as "no flooding on 28 Oct".
- Normal change is not small: sigma about 1 dB and a 1.9 % false-positive crops rate, so mandal-level crops_pct values below about 2 % are indistinguishable from normal change. Use `normal_pct` next to every mandal bar.
- Not done: layover masking, incidence-angle/ soil moisture normalisation, optical validation, accuracy assessment against any reference flood map. The thresholds are heuristic, derived from the normal pair, not trained.

## PNGs (WGS84, paletted, all under 100 KB)
`class_20261109_{new_water,wet_crops,no_change}.png` and `class_20261028_*.png`; 2246 x 2023 px, nearest-neighbour warp of the 50 m UTM grid to 0.00045 deg. Colours new water #2A6FB0, wet crops #E09A2B, no_change a light grey (alpha 40/255); everything else transparent. Bounds `[[S,W],[N,E]]` in `class_png_bounds.json` (exact for these PNGs; they cover the delta-box bounding box). Class shares per pair: `class_shares_summary.json`.

## Mandal ranking
- `mandal_rank.json`: schema of the placeholder (mandal, district, water_pct, water_err, crops_pct, crops_err, normal_pct, rank) with extra `coverage_pct` and `flag`; no placeholder flag. Primary pair 16 Oct to 9 Nov. `normal_pct` = water + crops share of the normal pair with the same thresholds. `rank` = by water_pct among mandals not flagged; `rank: null` means flagged and not ranked (flag text says why).
- `mandal_rank.csv`: all 146 polygons, both pairs (water/crops/none, errors, ranks for 28 Oct as `rank_20261028`), normal water and crops separately, valid and land pixel counts, coverage, in-box fraction.
- Coverage = valid pixels / non-permanent-water pixels in the mandal. Flags: no district (Unguturu, plus polygons without a mapping), under 200 valid pixels, coverage under 50 %, or under 50 % of the mandal inside the delta box (12 districted mandals; only their in-box part was measured). 66 rows with a district and data; 54 ranked. Coverage was 100 % for most ranked mandals (the NaN areas are sea and out-of-swath).
- Top 5 by likely-new-water share (9 Nov): Nidadavole (East Godavari) 7.4 %, Undrajavaram (East Godavari) 5.1 %, Tanuku (West Godavari) 5.0 %, Narasapuram (West Godavari) 2.6 %, Samalkota (Kakinada) 2.5 %. Narasapuram and Samalkota have normal_pct of 4.9 and 5.0 (mostly crops), so their crops figures are weak evidence. K Gangavaram (Konaseema) has water_err 4.7, i.e. its rank is unstable. Mandal vintage is 2018 geoBoundaries; district names from `mandal_district_2022_complete.csv`.
- Ranks 1 to 3 look robust (water_err of 0.03 to 0.14 points); ranks below about 5 are close together and should be treated as bands, not exact positions.

## Not published
No flooded area in km2 is given anywhere. All wording should say "likely".
