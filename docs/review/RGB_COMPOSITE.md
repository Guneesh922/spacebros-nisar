# Dual-pol radar colour composite (15 Nov 2026)

Built by `build_coast_rgb()` in `tools/build_web.py`; checked and sheeted by `python tools/colour_check.py --rgb-sheet docs/review/RGB_COMPOSITE.png`.
Sheet: `docs/review/RGB_COMPOSITE.png` (row 1: coast 4 Oct, 16 Oct, 28 Oct, 9 Nov; row 2: sea 3 Oct, 15 Oct, 27 Oct, 8 Nov; over the dark basemap #2B2B2B at the layer opacity 0.9; row 3: coast 9 Nov and sea 27 Oct as protanopia and deuteranopia see them; bottom: both legends with text labels).

**Generic since 15 Nov (second pass):** the composite is built for EVERY H5 in `data/h5` by band and role (`L-band COAST`, `L-band SEA` today). The co-pol (HH or VV) and cross-pol (HV or VH) are read from the H5 `/backscatter` keys, nothing is hard-coded, so S-band scenes (or a future role) get layers automatically once they are in the manifest with an `h5` field and both polarisations; unknown groups use the coast gamma (2.0, 1.0, 2.0) until tuned by eye. The sea 3 Oct scene has HV instead of VH (different acquisition mode); both count as cross-pol.

## What it is, and what it is not
The L-band coast scenes are **dual-pol (HH, HV) only**. A Freeman-Durden or Yamaguchi decomposition (surface / double-bounce / volume power) needs the full polarimetric matrix (HH, HV, VV and phase) and is **not possible** here. This is the standard dual-pol colour composite instead. Its colours are *hints* about the scattering, not a decomposition and not proof of anything. The layer names, legend and caption say so ("Two polarisations only (HH, HV): hints, not proof").

## Recipe
| channel | content | stretch (dB, fixed, pooled 2 to 98 percent of all 4 coast dates, 84.5 M valid pixels) | gamma |
|---|---|---|---|
| R | HH | -21.14 .. -1.64 | 2.0 |
| G | HV | -26.85 .. -10.63 | 1.0 |
| B | HH/HV ratio = HH minus HV in dB | 3.95 .. 14.72 | 2.0 |

- 3 x 3 average in LINEAR power per polarisation (as the class maps), then back to dB; the ratio is taken on the smoothed dB images.
- Valid pixel = finite HH and HV and `aux/mask == 1`. Everything else is transparent.
- Limits are fixed for all dates (so dates are comparable) and stored per channel in each layer json under `stretch.R/G/B` (`lo`, `hi`, `gamma`, `channel`, `percentiles`, `n_pixels` in `stretch_scope`). A new coast date moves them on the next build, as for the grey layers.
- Same lat/lon nearest-neighbour warp (`warp_to_latlon`) and size cap as the other layers: PNG <= 600 KB. Because speckle makes RGB PNGs compress badly (about 1.3 MB at the grey layers' 785 px; quantising to 24 levels per channel only saves 25 percent), the cap forces **502 x 472 px (about 200 m per pixel)**, coarser than the grey layers (785 px). Detail such as a single village is therefore not resolved. Raising the cap would give more detail.
- Layers: `nisar_l_coast_rgb_YYYYMMDD` (4, 16 Oct, 28 Oct, 9 Nov), type `derived`, chip `nisar`, polarisation `HH+HV`, credit string identical to the other NISAR layers, `latest_of` `nisar_l_coast_rgb`.

### How the channel recipe was chosen (by eye, on the rendered PNGs over #2B2B2B)
Plain linear R = HH, G = HV, B = ratio gave yellow-green land (red and green add to yellow) and violet water: it does not read like the table. Gamma 2 on HH and on the ratio fixes both: water drops to dark, mid HH no longer pushes the land to yellow so vegetation is green, and only pixels with really bright HH turn red; a high ratio with low HH is blue. Tried and dropped: gamma 2.5 on HH with G 0.8, gamma 3 on HH, gamma 3 on the ratio (greener but flatter, less contrast between crop types). No change to the percentile limits was needed.

## What each colour means here against the table
Legend swatches are the MEDIAN colour the recipe gives to pixels that follow a plain dB rule (all dates pooled; stored in the layer json `legend`); the rules only choose representative pixels, they are not classes and feed no count.

| colour (legend swatch) | rule used to pick the swatch | table says | what it can and cannot mean with HH and HV only |
|---|---|---|---|
| dark (#030E0F) | HH < -18 dB | open water, deep flood = black | Matches for smooth water: low HH and HV both. Also any other very smooth or radar-shadowed surface. Wind-roughened water is brighter and is NOT dark (28 Oct: only 2.6 percent of valid pixels have HH < -18 dB against 23 to 29 percent on the other dates, because the storm roughened the sea). |
| green (#7BB71A) | HH -12 to -6 dB and HV -18 to -13 dB | dry vegetation = volume scattering = green | Matches in spirit: HV (cross-pol) is what volume scattering raises, and G is HV. It is "moderately bright with clear cross-pol", which is also paddy, scrub and wet crops. Not a measurement of vegetation type. |
| red or magenta, pink (#FFB5E7) | HH > -3 dB and HH minus HV > 11 dB | flooded forest/crops = double bounce = bright red/magenta; urban = white/yellow/bright red | **Only partly transfers.** The colour means "very bright HH with weak HV". Double bounce (flooded vegetation, buildings) produces that, but so do rough bare soil, tilled or wet fields, corner-like structures, metal and other bright targets. Dual-pol cannot separate double bounce from other bright HH. Pale pink/white means HH and HV are both high (the stretch saturates), which is where towns and very rough surfaces sit. The swatch is pink rather than saturated red because the ratio (blue) is also high there. |
| bluish (#151944, dark navy) | HH -17 to -12 dB and HH minus HV > 9 dB | saturated/wet soil = surface scattering = bright blue/cyan | **Does not transfer well.** The table's bright cyan would need a strong surface-scattering signal; the dual-pol blue here is dark navy: lowish HH with the cross-pol much weaker, which is what smooth surfaces give. It cannot tell wet soil from dry smooth bare ground, and it is dark enough to be hard to tell from water (see colour-blind and contrast numbers). |
| white / yellow for urban | none | urban = white/yellow/bright red | Not a separate colour. Bright pale pink or white pixels in towns exist but cannot be told from other bright surfaces. No yellow-urban class. |

Other limits (as in docs/METHODS.md):
- **Wet crops (the class map's weak signal) is not made visible by this composite**: that class is unproven (the HH/HV ratio test of 14 Nov did not separate it from normal field change). A red/magenta patch is not "wet crops" or "flooded forest" proof.
- **The baseline scenes (4 and 16 Oct) are PROVISIONAL; 28 Oct and 9 Nov are VALIDATED.** On this composite the two baseline dates show large pink and lilac land patches (4.6 and 5.1 percent of valid pixels meet the bright-weak-cross-pol rule) while 28 Oct and 9 Nov show far fewer (1.5 and 1.7 percent), and the median HV is about 3.6 dB higher on 28 Oct than on 4 Oct. METHODS.md already records a land-wide HV offset (+1.9 dB on 28 Oct). This colour change between dates is therefore **not** a flood signal: it can come from product version or calibration (provisional against validated), crop stage and soil moisture, and the storm. Do not read colour differences between 16 Oct and 28 Oct as flooding.
- 28 Oct: the sea is bluish in the picture (rough, bright sea off the coast on landfall day), the only date where open sea is not near black.
- No ground truth was used; nothing in the composite is validated against a flood map or an optical image.
- Colours are per-pixel speckled even after 3 x 3 averaging (60 m); at 200 m display pixels the single colours of fields blend.

## Sea recipe (L-band SEA, VV and VH, 100 m)
| channel | content | stretch (dB, pooled 2 to 98 percent of all 4 sea dates) | gamma |
|---|---|---|---|
| R | VV | -21.35 .. -3.80 | 2.0 |
| G | VH (HV on 3 Oct) | -27.25 .. -10.15 | 1.0 |
| B | VV minus VH | 3.46 .. 15.42 | 3.0 |

- The sea H5 is already a 100 m multilook (5 x 5 of 20 m), so it is **not smoothed again** (3 x 3 is applied only where the posting is 30 m or finer). Valid = finite VV and VH and `aux/mask == 1`.
- The limits include the 3 Oct scene, a different acquisition mode that is mostly land (12 percent valid pixels, HV, not VH); this is as for the grey sea stretch. Layers `nisar_l_sea_rgb_YYYYMMDD` (the id gets a `_tNN` suffix only if a group has more than one track).
- Tuned by eye over #2B2B2B on all four dates (variants 2/2/2, 1.5/1/2, 2/1/3, 1/1/1, 1.5/0.7/2): 2/1/3 keeps the calm sea dark with its natural slicks, and gives the 27 Oct eye pass a clear dark eye, an orange-brown eyewall and the spiral bands in purple. Calm 15 Oct and 8 Nov are plain dark navy with a few darker slicks (15 Oct).
- Size: the composites fit **785 x 699 px** at the 600 KB cap (3 Oct: 1228 px), against 1536 px for the grey sea layers. A higher cap would give the sea more detail.

### What the colours mean over the sea (legend swatches = median colour of pixels following a dB rule, all sea dates pooled)
| colour | rule | meaning |
|---|---|---|
| dark (#001200) | VV < -18 dB | calm or smooth sea (and radar shadow) |
| dark purple (#2E1D4C) | VV -15 to -11 dB, VH < -22 dB | moderately rough sea |
| purple or violet (#8041B3) | VV > -11 dB, VH < -21 dB | rough, wind-driven sea (strong wind, big waves): the storm field on 27 Oct |
| green or yellow (#B8CF04) | VH > -18 dB | land and vegetation (the delta in the corner of the box) |

Honest reading: **over the sea, bright VV with weak VH (purple, violet) means a rough surface (wind and waves), not a flood.** The "flooded forest = red" and "wet soil = blue" meanings of the table do not exist over open water. The swatch is violet, not red or pink as on land, because the VV/VH ratio is high there. Dual-pol colour gives no wind speed. Cross-pol (green channel) over the sea stays near the noise floor for most wind speeds, so it only lights up in the eyewall and at very high winds (the orange-brown ring around the 27 Oct eye); 28 Oct on the coast scene (storm-roughened nearshore sea) shows the same bluish tone. 3 Oct differs in mode and cannot be compared by colour with the other dates.

Sea legend colour distances (as drawn, same method): minimum normal 20.1, protanopia 18.7, deuteranopia 19.3 (moderate vs rough sea: dark purple vs violet); dark vs dark purple 28.2 / 24.4 / 22.5. The dark and dark purple swatches are nearly invisible on the #2B2B2B basemap (contrast 1.33:1 and 1.06:1, dE00 12.8 and 19.7), so the text labels carry them. Under both colour-blindness simulations the sea turns blue and the land yellow; the eye and rings stay visible by lightness.

## Colour-blind check (Machado 2009, severity 1.0, linear RGB; CIEDE2000)
Colour-vision distances between the four legend colours, as drawn (colour x 0.9 over #2B2B2B):

| pair | normal | protanopia | deuteranopia |
|---|---|---|---|
| dark vs green | 55.7 | 56.3 | 54.5 |
| dark vs red/magenta | 65.9 | 61.4 | 65.6 |
| dark vs bluish | 19.1 | 16.1 | 15.8 |
| green vs red/magenta | 63.6 | 43.5 | 37.2 |
| green vs bluish | 66.0 | 65.0 | 63.4 |
| red/magenta vs bluish | 61.9 | 56.6 | 62.8 |
| minimum | 19.1 | 16.1 | 15.8 |

Honest result:
- The green / pink-red pair that is a problem in general **stays separable** here (dE00 43.5 protanopia, 37.2 deuteranopia, above the 20 used for the other layers) because the pink is much lighter than the green (they differ in lightness, not only hue). In the simulated sheet the whole land turns yellow-ochre for both types of colour-blindness: **green land and yellow/orange land can no longer be told apart by hue**, and the picture loses the "green = vegetation" cue; pale pink patches still stand out as light.
- **Dark vs bluish fails the 20 criterion even for normal vision (19.1), and falls to 16.1 / 15.8 in colour-blind vision.** The bluish class is dark navy next to near-black water and is nearly invisible against the dark basemap (swatch contrast 1.17:1, dE00 18.5 from the basemap; dark swatch 1.35:1, 9.2). Colour alone cannot carry these two classes.
- Therefore the legend does not rely on colour: each of the four rows has a swatch and a plain text label (Dark: smooth water; Green: vegetation; Red or magenta: very bright with weak cross-pol, possible double bounce; Bluish: smooth bare or wet ground), and the Grey / Colour switch offers the greyscale picture for every date. The recipe was not changed to fix the dark/bluish pair because lifting the navy would break the table's "water dark".

## Dashboard
- A LOOK row "Grey | Colour" (same style as the DATE rows) in Radar mode (coast and sea), Before and after (when both dates have a colour picture, both are swapped) and Cyclone eye. It is one global choice; `look=colour` is in the hash and in saved days, and falls back to grey with a notice if a picture is missing. Default is Grey.
- Data tab: "Radar by date" has the same Grey | Colour choice and shows the colour thumbnails; clicking one puts its colour layer on the map. The Layers table lists all colour layers (8). A "Colour key" card sits right after the Layers card (chip "Colour key" in the jump bar): per band and area the channel recipe, the scale limits and the swatch rows with plain words. The Scene catalogue rows offer a grey and a colour PNG with the colour layer's credit line; Downloads list the 8 colour PNGs with credit.
- Legend with colour on: the swatch rows with plain words, "Red = VV, green = VH, blue = VV minus VH." and the credit caption. The old line "Two polarisations only (HH, HV): hints, not proof." was removed from the product (user rule: no data-quality disclaimers on the public pages); the honesty notes live here and in METHODS.md.
