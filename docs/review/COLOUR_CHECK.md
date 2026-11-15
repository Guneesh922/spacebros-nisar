# Colour check (15 Nov 2026)

Task 1B: colour coding with real contrast, computed from the H5 values by `tools/build_web.py`; checked by `tools/colour_check.py`
(`python tools/colour_check.py --md` rewrites the tables below, `--sheet OUT.png --before DIR` makes the contact sheet).
Sheet: `docs/review/COLOUR_CHECK.png` (top = BEFORE, bottom = AFTER, every layer over the dark basemap colour **#2B2B2B**,
an approximation of Esri Dark Gray Canvas chosen once; layers at their manifest opacity).

## What changed
1. **Backscatter (greyscale kept).** The fixed -25..0 dB stretch is replaced by 2 and 98 percent of the pooled valid pixels of all dates of a role:
   COAST HH -22.16 .. -1.06 dB (86.6 M pixels, 4 dates), SEA VV -26.50 .. -4.22 dB (15.1 M pixels, 4 dates; the 3 Oct scene is included as asked, it is a different acquisition mode and has the darkest tail). Stored in each layer json under `stretch` (lo, hi, percentiles, n_pixels, pooled_over); `stretch_db` is kept.
2. **Change maps.** Sea difference (old fixed +-15 dB, now +-6.0 dB) and a new coast change layer per coast date after the baseline (`nisar_l_coast_change_YYYYMMDD_hh`, event HH minus the 4/16 Oct linear-power baseline, 20 m class grid, 3 x 3 smoothed in linear power, land only, permanent water blank as in the class maps). Ramp: blue (darker), white (no change), orange-red (brighter), symmetric about 0. Pixels with |change| < 1 sigma are grey (#9BA1A7, alpha 175). Limit = min(3 x P99 of |change|, 6 dB). `ramp` in each json holds stops, sigma, limit, P99, words.
3. **Classes.** new open water #2A6FB0 -> #3FA7F5 (alpha 235); wet crops #E09A2B -> #F2A93B (alpha 210); no change #C4D0D2 at alpha 36. The class layers' manifest opacity goes 0.75 -> 1.0 for water and crops, so the alpha is not dimmed a second time.

| value | sea 27 Oct | sea 8 Nov | coast 28 Oct | coast 9 Nov |
|---|---|---|---|---|
| sigma (dB) | 3.11 | 1.29 | 0.88 | 0.88 |
| P99 of abs(change) (dB) | 15.51 | 11.05 | 6.14 | 9.78 |
| 3 x P99 (dB) | 46.5 | 33.2 | 18.4 | 29.3 |
| limit used (dB) | 6.0 | 6.0 | 6.0 | 6.0 |

The 6 dB cap decides every limit today (the old sea range was +-15 dB). Sigma for the coast = robust (MAD) sigma of 16 Oct minus 4 Oct HH over land (METHODS step 6). The sea has no usable calm-fortnight pair (3 Oct is a different acquisition mode, LBAND_TEST.md), so its sigma is the robust sigma of the map's own difference over common valid pixels more than 1 km offshore; for 27 Oct that mostly measures the storm's own spatial spread, so the grey band is wide (+-3.1 dB) and is stated as such in the json (`ramp.sigma.source`).

## Colour choices and reasons
- **new_water #3FA7F5.** Same hue as `--water` (209 deg vs 206 deg), lightness raised from L* 46 to 66: `--water` itself is only 2.7:1 on the dark map. Near opaque (235), the main class.
- **wet_crops #F2A93B.** Same hue as `--crops` (37 vs 36 deg), slightly lighter. Alpha 210: it is the weak, unproven class, a little more see-through than water, still clearly visible.
- **no_change #C4D0D2 alpha 36.** The `--on-stage-muted` tint, near transparent on purpose (about 5 dE00 from the basemap).
- **Ramp ends #2F7DC4 / #D9541E.** Blue from the `--water` family, orange-red from `--crops` pulled towards red; both ends have L* about 51 to 53 (3.3 and 3.5:1 on the basemap) so the strong values stay visible and the pale middle (#8FBFE8, #F6B48A, white) carries "a little".
- **Grey #9BA1A7.** Chosen by numbers: the first grey (#8A9096) was 19.2 dE00 from the blue end under protanopia, below the 20 criterion; lightening to L* 66 gives at least 21.3 against the ends and the white centre.
- No red-green pair anywhere; blue/orange stays separable under both colour-vision simulations.

## Honest notes
- Everything meets the criteria in the tables below (min dE00 21.3), except the 'no_change' tint, which is meant to be near invisible and is outside the class-pair criterion. The white centre and the grey are close (about 21 dE00) on purpose: both say "no clear change".
- The class contrast on the map is computed for the blended colour (alpha x layer opacity); the UI must keep the layer opacity at 1.0 for water and crops, otherwise water falls back to about 3.4:1.
- The coast change map is mostly pale blue across the centre of the delta on both dates (darker than the baseline), orange along the coast. This is what the data show; it is brightness change, not a flood map, and the baselines are PROVISIONAL products.
- 20 m class pixels are thin at the 36 m display warp; the sheet tiles are shrunk, so classes look sparser there than on screen.
- The sea 27 Oct difference is mostly saturated orange (median +4.6 dB against a 6 dB limit); the 6 dB cap is the rule given, so the eye structure is compressed.
- Legend text/background checked against dash.css (`.legend`: `--stage-glass`, white and `--on-stage-muted`): all text pairs >= 4.5:1. The map legend swatches and `.sw--w` / `.sw--c` in dash.css still use `--water` / `--crops` (not edited here, another agent wires the legends).

## Numbers (generated by tools/colour_check.py)
<!-- colour_check:begin -->

Basemap assumed: #2B2B2B (approximation of Esri Dark Gray Canvas)
Distance measure: CIEDE2000 (dE00). Colour-vision model: Machado et al. 2009, severity 1.0, in linear RGB.

### Class colours
| class | colour | alpha | layer opacity | contrast vs basemap (raw colour) | contrast vs basemap (as drawn: alpha x layer opacity) |
|---|---|---|---|---|---|
| new_water | #3FA7F5 | 235 | 1.00 | 5.43:1 | 4.84:1 (drawn as #3D9DE5) |
| wet_crops | #F2A93B | 210 | 1.00 | 7.09:1 | 5.30:1 (drawn as #CF9338) |
| no_change | #C4D0D2 | 36 | 0.75 | 8.97:1 | 1.29:1 (drawn as #3B3C3D) |

Pairwise dE00 between the classes that carry meaning (no_change is a near-transparent tint, listed apart):
| pair | normal vision | protanopia | deuteranopia |
|---|---|---|---|
| new_water vs wet_crops | 51.0 | 54.5 | 58.1 |
Minimum over the pairs: normal 51.0, protanopia 54.5, deuteranopia 58.1 (criterion >= 20)

Each class colour against the basemap as drawn (dE00, alpha x layer opacity), so a class does not vanish into the map:
| class | normal | protanopia | deuteranopia |
|---|---|---|---|
| new_water | 45.3 | 48.5 | 43.5 |
| wet_crops | 49.5 | 46.0 | 51.5 |

no_change tint: #C4D0D2 alpha 36; effective over the basemap #3B3C3D (dE00 to basemap 5.6); intentionally faint.

Hue family check: each map colour against the UI token it is derived from (HLS hue in degrees; same family = within 10 degrees):
| class | token | token hue | map hue | token L* | map L* |
|---|---|---|---|---|---|
| new_water | --water #2A6FB0 | 209 | 206 | 46 | 66 |
| wet_crops | --crops #E09A2B | 37 | 36 | 69 | 75 |

### UI contrast (WCAG 2.x, AA needs >= 4.5:1 for text)
Legend (dash.css .legend): background = --stage-glass = 92 % of --stage #0F1B1F over the basemap = #111C20; text --white #FFFFFF; muted text --on-stage-muted #C4D0D2.
| pair | ratio | AA text (4.5) |
|---|---|---|
| legend text (--white) on legend background | 17.30:1 | pass |
| legend muted text (--on-stage-muted) on legend background | 10.96:1 | pass |
| card text (--ink) on --card | 16.98:1 | pass |
| card secondary text (--ink-2) on --card | 8.76:1 | pass |
| muted text (--muted) on --card | 6.10:1 | pass |
| muted text (--muted) on --paper | 5.51:1 | pass |

Map colours against the legend background and the card (non-text graphics need >= 3:1, WCAG 1.4.11):
| colour | vs legend bg | vs --card |
|---|---|---|
| new_water #3FA7F5 | 6.64:1 | 2.61:1 |
| wet_crops #F2A93B | 8.66:1 | 2.00:1 |

### Diverging ramp (blue = darker, white = no change, orange-red = brighter)
Stops at fractions of the saturation limit: -1.00 #2F7DC4, -0.50 #8FBFE8, +0.00 #F7F7F7, +0.50 #F6B48A, +1.00 #D9541E
| stop | L* | contrast vs basemap | contrast vs legend bg |
|---|---|---|---|
| -1.00 #2F7DC4 | 51.0 | 3.27:1 | 4.00:1 |
| -0.50 #8FBFE8 | 75.4 | 7.27:1 | 8.89:1 |
| +0.00 #F7F7F7 | 97.2 | 13.22:1 | 16.15:1 |
| +0.50 #F6B48A | 78.5 | 7.97:1 | 9.73:1 |
| +1.00 #D9541E | 53.2 | 3.53:1 | 4.31:1 |

dE00 from the centre (white) outwards, per colour vision; must grow with |value| on each side:
- normal: -0.50:21.9, -1.00:40.6, +0.50:24.2, +1.00:42.5 -> monotone
- protanopia: -0.50:20.1, -1.00:37.9, +0.50:22.2, +1.00:45.5 -> monotone
- deuteranopia: -0.50:22.8, -1.00:42.8, +0.50:21.8, +1.00:37.9 -> monotone
L* rises from the blue end to the centre and falls to the orange end (monotone): yes (neg side 51, 75, 97; pos side 97, 79, 53)

Blue end, orange end, white centre and the 'no clear change' grey, pairwise dE00:
| pair | normal | protanopia | deuteranopia |
|---|---|---|---|
| blue end #2F7DC4 vs orange end #D9541E | 47.7 | 50.1 | 55.1 |
| blue end #2F7DC4 vs white centre #F7F7F7 | 40.6 | 37.9 | 42.8 |
| blue end #2F7DC4 vs grey (|change| < 1 sigma) #9BA1A7 | 22.4 | 21.3 | 24.9 |
| orange end #D9541E vs white centre #F7F7F7 | 42.5 | 45.5 | 37.9 |
| orange end #D9541E vs grey (|change| < 1 sigma) #9BA1A7 | 33.6 | 33.3 | 30.8 |
| white centre #F7F7F7 vs grey (|change| < 1 sigma) #9BA1A7 | 21.6 | 21.3 | 21.8 |
Minimum over these pairs: normal 21.6, protanopia 21.3, deuteranopia 21.8 (criterion >= 20)
(the white centre and the grey are meant to be close: they both say 'no clear change'; that pair is the minimum if it is low)


<!-- colour_check:end -->
