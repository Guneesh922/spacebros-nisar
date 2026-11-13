"""Simple change detection between two GCOV subsets (same track!).

difference (dB) = after - before
  big positive  -> surface got rougher / more built-up / more vegetation structure
  big negative  -> surface got smoother or wetter-and-flat (e.g. flooding, open water)

Usage:
  python src/change_map.py data/subsets/delhi/2026-06-09_T106_HHHH.tif data/subsets/delhi/2026-08-15_T106_HHHH.tif
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from scipy.ndimage import uniform_filter


def load(path):
    with rasterio.open(path) as src:
        return src.read(1), src.profile


def main(before, after, threshold=3.0, smooth=5):
    a, prof = load(before)
    b, _ = load(after)
    if a.shape != b.shape:
        raise SystemExit("rasters differ in size: use two scenes from the same track")
    # light speckle filter in linear power before differencing
    lin = lambda d: uniform_filter(np.nan_to_num(10 ** (d / 10)), smooth)
    with np.errstate(divide="ignore", invalid="ignore"):
        diff = 10 * np.log10(lin(b)) - 10 * np.log10(lin(a))
    diff[~np.isfinite(diff)] = np.nan

    out = Path(after).with_name(f"change_{Path(before).stem}_to_{Path(after).stem}")
    with rasterio.open(out.with_suffix(".tif"), "w", **prof) as dst:
        dst.write(diff.astype("float32"), 1)

    fig, ax = plt.subplots(1, 3, figsize=(15, 5))
    for axis, img, title, cmap, lim in [(ax[0], a, "before (dB)", "gray", (-25, 0)),
                                        (ax[1], b, "after (dB)", "gray", (-25, 0)),
                                        (ax[2], diff, "after - before (dB)", "RdBu", (-6, 6))]:
        im = axis.imshow(img, cmap=cmap, vmin=lim[0], vmax=lim[1])
        axis.set_title(title)
        axis.axis("off")
        fig.colorbar(im, ax=axis, shrink=0.7)
    fig.tight_layout()
    fig.savefig(out.with_suffix(".png"), dpi=130)
    changed = np.nanmean(np.abs(diff) > threshold) * 100
    print(f"saved {out}.tif/.png - {changed:.1f}% of pixels changed by more than {threshold} dB")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
