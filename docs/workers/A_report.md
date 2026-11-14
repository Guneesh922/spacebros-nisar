# Worker A report: NISAR sea scenes, difference map, eye analysis (14 Nov 2026)

## 1. Subsets (data/raw/nisar_l/sea/, VV only, dB, EPSG:32644, 100 m, 3006 x 3398, identical grid for all three)
`src/fetch/subset_arnab.py` was NOT used for the run: it reads the whole sea window (about 15000 x 17000 px) into RAM and the 3.9 GB device VM cannot hold it (process killed silently). I used a strip-wise reader (same maths: 5x5 block mean in linear power, then dB; same transform) kept in /tmp/A_strip.py (not in the repo). Only VVVV was written, not VHVH or the extra layers.

| Scene | File | median dB | NaN frac | sha256 |
|---|---|---|---|---|
| 15 Oct (PROVISIONAL PR) | 2026-10-15_T48_VVVV.tif | -14.20 | 0.686 | 2eeb7a08...9ed4c3 (full: 2eeb7a081392dbca72e21e317ba62469ad3baf5bd8be31410e34dc680ed9b4c3) |
| 27 Oct (validated) | 2026-10-27_T48_VVVV.tif | -9.69 | 0.703 | 0ca7a401a3d518dfe652462b248820b142a4d2b4115ea608cbc46e481db45118 |
| 8 Nov (validated) | 2026-11-08_T48_VVVV.tif | -14.06 | 0.703 | e385a9e909d32b7ef8fdec1733c78ffc475da1f2e9eb043895a48edb2343da3e |

NaN is high because the rotated swath fills about 30% of the 4 x 3 degree box. Sea values are in the plausible -25 to -6 dB range (calm 1st percentile -25.0, so the noise floor is touched in dark patches). The scenes do share one grid, no reprojection needed between them.
Not run: the script's own log `data/logs/nisar_l_subset.md` was not updated.

## 2. Web PNGs (data/interim/A/)
Greyscale VV dB, reprojected to a north-up WGS84 grid (0.0025 deg, area-average in linear power), NaN transparent (alpha), cropped to data, one shared stretch **-25 to -6 dB** (1st to 99.5th percentile of sea pixels over the three dates; land saturates white). Bounds are [[S,W],[N,E]], also in `bounds.json`.

| File | bytes | bounds | sha256 |
|---|---|---|---|
| nisar_l_sea_20261015_t48_vv.png | 472876 | [[15.52,81.435],[17.1875,83.985]] | ebfa4680...5ac9 (ebfa468019646e49ee183604a5e5ece97df890c94b350049a6b81970d5f07ac9) |
| nisar_l_sea_20261027_t48_vv.png | 398631 | [[15.5375,81.4375],[17.1525,83.975]] | 98ab34640d36a4a0cdafb1e16e7972a3ea5bc3856e2b895b1acf82dd4db55db3 |
| nisar_l_sea_20261108_t48_vv.png | 396741 | [[15.5575,81.4425],[17.1725,83.98]] | d056b029e13a52a68bf94b7dcf4babe527aa9c1899359143a9f44aaf6d1e69de |
| nisar_sea_diff_20261027_vs_20261015.png | 513903 | [[15.5375,81.4375],[17.1525,83.975]] | 76875667eb79d8713ac138693eea49eb50b587e3316a392cbb6d688cbb12965f |
| nisar_sea_diff_20261027_vs_20261015.tif (native UTM 44N, float32 dB, land not masked, 11.1 MB) | 11102628 | native grid, same as subsets | 2ef2fc8b5fda7f103dfd41095f58c460a0adf945238ca656ea144581155482c4 |
| profile.json | 7933 | | b00de162160c33c7deb0002b6add803383dab23a9c4a5f01de11fda7c682f296 |

Bounds differ slightly per date (swath footprints differ). The inferred bounds in PLACEHOLDERS.md for 15 Oct ([[15.297,81.272],[18.331,84.490]]) are frame bounds; the real data footprint is the one above, so set `bounds_inferred` false and use these.
The 8 Nov scene (a bonus) is delivered too.

## 3. Difference map
27 Oct minus 15 Oct, VV dB, native 100 m grid. PNG: muted diverging ramp, blue #2E6496 at -8 dB, grey at 0, amber #E09A2B at +8 dB (clipped); land masked transparent in the PNG (heuristic mask: smoothed backscatter above -10.5 dB in both the 15 Oct and 8 Nov scenes, dilated 1.5 km), not in the GeoTIFF. Sea pixels: median +4.5 dB, 5th to 95th percentile 0.0 to +11.5 dB.
Proposed caption: "Change in radar backscatter (VV, dB), 27 Oct 2026 minus 15 Oct 2026. The 27 Oct scene is validated NISAR L-band data; the 15 Oct calm reference is a PROVISIONAL product. Brighter amber means a rougher sea surface; backscatter is not wind speed."
Caveat the lead must see: the 15 Oct "calm" scene is not uniformly calm. It has large dark low-backscatter patches (probably low-wind or rain/slick areas, I did not verify the cause), so the difference is inflated there. The 8 Nov scene (median -14.1 dB) looks like a better calm reference but is after the event.

## 4. Eye analysis (27 Oct, 13:01:51 to 13:02:08 UTC)
The eye is clearly visible as a dark spot with a bright ring. Method: land masked; centre = mean of (a) the backscatter minimum of a 1 to 1.5 km Gaussian-smoothed field within 25 km of the IMD fix and (b) the centre maximising the steepest rise of the 1 km radial mean (grid search +/-8 km); the two agree within about 1.3 km. At smoothing of 2.5 km or more the minimum jumps to an unrelated low-backscatter patch 33 km east, so "global minimum" is not used.
- Centre: **16.257 N, 82.514 E**, uncertainty about +/-1.5 km.
- Radial mean VV profile (1 km bins to 60 km, errors = spread across 8 azimuth octants / sqrt 8): minimum -11.5 dB at the centre, rising to a ring maximum of about -8.0 dB at 12.5 to 14.5 km, then falling slowly to -8.8 dB at 30 km. Core-to-ring contrast about 3.3 dB (weak).
- Eye radius: **4.7 +/- 2.2 km** (half-contrast radius; spread over 9 centre shifts of 1.5 km and 4 quadrants, 3.6 to 8.9 km). The edge is soft and asymmetric, so treat the uncertainty as real. Eyewall ring brightness maximum at about 13.7 km (range 10.5 to 15.5 by quadrant). The old placeholder (18 km) is not supported by the data.
- IMD fix interpolated linearly between the 12:00 UTC (16.3 N, 82.7 E) and 15:00 UTC (16.3 N, 82.4 E) advisories at 13:02 UTC: 16.300 N, 82.597 E. Offset from SAR centre **10.1 km** (IMD positions are to 0.1 deg, about 11 km, so the offset is about the reporting precision; linear interpolation is an assumption).
- No wind speed is given anywhere. The profile.json also holds `points_calm_1015_provisional` (same centre) as an extra field.

## 5. Decisions for the lead
1. Which radius to show: 4.7 +/- 2.2 km (half-contrast) or the ring at about 13.7 km. I put the first in `eye_radius_km` and the second in `eyewall_ring_km`. profile.json `eye` is [lat, lon] like the placeholder; `points` use r_km, db (VV dB, not a difference), err. The "+6.2 dB peak" claim in the case study cannot be taken from this profile (the raw ring-to-core contrast is 3.3 dB); a difference profile needs a decision on the calm reference.
2. Whether to use the 15 Oct frame as "calm" (see section 3).
3. Files I could not remove: `data/interim/A/_look/` (three diagnostic PNGs) because deletion is blocked; ignore or delete it.
4. `src/fetch/subset_arnab.py` needs a strip-wise reader for sea scenes on small-RAM machines (not changed, per instructions).
