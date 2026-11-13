"""Cut the study area out of real NISAR GCOV backscatter files and save GeoTIFFs (dB).

Needs a free NASA Earthdata login (https://urs.earthdata.nasa.gov/users/new).
Give it to earthaccess in ONE of these ways (never commit it to git):
  * ~/.netrc line:  machine urs.earthdata.nasa.gov login YOUR_USER password YOUR_PASS
  * env vars:       EARTHDATA_USERNAME / EARTHDATA_PASSWORD
  * or just run it: earthaccess will prompt you

By default it streams only the bytes it needs over HTTPS (a full GCOV file is 2-9 GB).

Usage:
  python src/gcov_subset.py --track 106 --start 2026-06-01 --end 2026-11-30 --pols HHHH HVHV
  python src/gcov_subset.py --file-id NISAR_L2_PR_GCOV_...   # one specific scene
"""
import argparse
import csv
from pathlib import Path

import earthaccess
import h5py
import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.transform import from_origin

import config


def find_grid(h5, freq):
    """Return the HDF5 group holding the GCOV grids for one frequency (A = main band)."""
    for base in ("/science/LSAR/GCOV/grids", "/science/SSAR/GCOV/grids"):
        path = f"{base}/frequency{freq}"
        if path in h5:
            return h5[path]
    found = []
    h5.visit(lambda n: found.append(n) if n.endswith(f"frequency{freq}") and "grids" in n else None)
    if not found:
        raise KeyError(f"frequency{freq} grid not found in file")
    return h5[found[0]]


def epsg_of(grid):
    proj = grid["projection"]
    for key in ("epsg_code", "epsg"):
        if key in proj.attrs:
            return int(proj.attrs[key])
    return int(proj[()])


def subset(h5file, bbox, pols, freq="A"):
    grid = find_grid(h5file, freq)
    epsg = epsg_of(grid)
    x = grid["xCoordinates"][:]
    y = grid["yCoordinates"][:]

    w, s, e, n = bbox
    tr = Transformer.from_crs(4326, epsg, always_xy=True)
    xs, ys = tr.transform([w, e, e, w], [s, s, n, n])
    xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)

    cols = np.where((x >= xmin) & (x <= xmax))[0]
    rows = np.where((y >= ymin) & (y <= ymax))[0]
    if cols.size == 0 or rows.size == 0:
        raise ValueError("study area does not overlap this scene")
    c0, c1, r0, r1 = cols[0], cols[-1] + 1, rows[0], rows[-1] + 1

    dx = float(x[1] - x[0])
    dy = float(y[1] - y[0])  # usually negative (north-up)
    top = y[r0] - dy / 2 if dy < 0 else y[r1 - 1] + dy / 2
    transform = from_origin(x[c0] - dx / 2, top, dx, abs(dy))

    out = {}
    for pol in pols:
        if pol not in grid:
            print(f"  {pol} not in this scene (has: {[k for k in grid.keys() if len(k) == 4]})")
            continue
        arr = grid[pol][r0:r1, c0:c1].astype("float32")
        if dy > 0:
            arr = arr[::-1]
        with np.errstate(divide="ignore", invalid="ignore"):
            db = 10 * np.log10(arr)
        db[~np.isfinite(db)] = np.nan
        out[pol] = db
    return out, transform, epsg


def save_tif(path, arr, transform, epsg):
    with rasterio.open(path, "w", driver="GTiff", height=arr.shape[0], width=arr.shape[1], count=1,
                       dtype="float32", crs=f"EPSG:{epsg}", transform=transform, nodata=np.nan,
                       compress="deflate") as dst:
        dst.write(arr, 1)


def pick_scenes(args):
    cat = config.CATALOGUE / f"{config.AOI_NAME}_scenes.csv"
    rows = [r for r in csv.DictReader(open(cat)) if r["level"] == "GCOV"]
    if args.file_id:
        return [r for r in rows if r["file_id"] in args.file_id]
    rows = [r for r in rows if str(r["track"]) == str(args.track)
            and args.start <= r["date"] <= args.end]
    best = {}
    for r in rows:  # one product per date: prefer production (P) + full-frame
        score = (r["crid"].startswith("P"), r["coverage"] == "Full", r["crid"])
        if r["date"] not in best or score > best[r["date"]][0]:
            best[r["date"]] = (score, r)
    return [r for _, r in sorted(best.values(), key=lambda t: t[1]["date"])]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--track", type=int)
    ap.add_argument("--start", default="2025-01-01")
    ap.add_argument("--end", default="2099-12-31")
    ap.add_argument("--file-id", nargs="+")
    ap.add_argument("--pols", nargs="+", default=["HHHH", "HVHV"])
    ap.add_argument("--freq", default="A", help="A = main L-band (20/40 MHz), B = side band")
    ap.add_argument("--download", action="store_true", help="download whole file instead of streaming")
    args = ap.parse_args()
    if not args.file_id and args.track is None:
        ap.error("give --track or --file-id")

    scenes = pick_scenes(args)
    print(f"{len(scenes)} scene(s) selected")
    if not scenes:
        return

    earthaccess.login(persist=False)  # .netrc, env vars, or interactive prompt
    out_dir = config.SUBSETS / config.AOI_NAME
    out_dir.mkdir(parents=True, exist_ok=True)

    for r in scenes:
        print(f"- {r['date']} track {r['track']}  ({r['size_gb']} GB full file)")
        try:
            if args.download:
                local = earthaccess.download([r["h5_url"]], str(config.DATA / "raw"))[0]
                h5 = h5py.File(local, "r")
            else:
                fs = earthaccess.get_fsspec_https_session()
                remote = fs.open(r["h5_url"], block_size=8 * 1024 * 1024, cache_type="blockcache")
                h5 = h5py.File(remote, "r")
            with h5:
                layers, transform, epsg = subset(h5, config.AOI_BBOX, args.pols, args.freq)
            for pol, arr in layers.items():
                p = out_dir / f"{r['date']}_T{r['track']}_{pol}.tif"
                save_tif(p, arr, transform, epsg)
                print(f"    saved {p.relative_to(config.ROOT)}  {arr.shape}  median {np.nanmedian(arr):.1f} dB")
        except Exception as exc:
            print("    failed:", exc)


if __name__ == "__main__":
    main()
