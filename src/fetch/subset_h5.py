"""Cut a study-box subset out of one NISAR L-band GCOV granule and write it as a small HDF5 (schema v1).

Schema: docs/DATA_STORAGE.md ("H5 subset schema (v1)"). No rasterio needed (h5py, numpy, pyproj only;
earthaccess+fsspec are imported lazily and only for https sources).

Usage (from the repo root):
  python src/fetch/subset_h5.py --scene L_COAST_1004 --src data/raw/nisar_l_h5/<granule>.h5
  python src/fetch/subset_h5.py --scene L_COAST_1004 --src <local.h5> --multilook 2 --suffix _ml2
  python src/fetch/subset_h5.py --scene L_SEA_EYE_1027 --src https://nisar.asf.earthdatacloud.nasa.gov/...h5
Only the box window is read from the granule (row bands), never the full layer.
"""
import argparse
import datetime as dt
import re
import subprocess
import sys
import time
from pathlib import Path

import h5py
import numpy as np
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[2]
BASE = "https://nisar.asf.earthdatacloud.nasa.gov/NISAR"
BOX = {"delta": (81.6, 16.2, 82.6, 17.1), "sea": (81.0, 15.0, 85.0, 18.0)}
SEA_POLS, COAST_POLS = ["VVVV", "VHVH"], ["HHHH", "HVHV"]
FILL = -32768
SEA_POSTING_M = 100.0

# id: (collection, file_id, box, GCOV pol datasets)
SCENES = {
    "L_SEA_CALM_1015": ("NISAR_L2_GCOV_PROVISIONAL_V1", "NISAR_L2_PR_GCOV_033_048_D_080_2005_DVDV_A_20261015T130150_20261015T130208_P05023_N_P_J_001", "sea", SEA_POLS),
    "L_SEA_EYE_1027": ("NISAR_L2_GCOV_V1", "NISAR_L2_PR_GCOV_034_048_D_080_2005_DVDV_A_20261027T130151_20261027T130208_P05036_N_P_J_001", "sea", SEA_POLS),
    "L_COAST_1004": ("NISAR_L2_GCOV_PROVISIONAL_V1", "NISAR_L2_PR_GCOV_032_055_A_010_4005_DHDH_A_20261004T000106_20261004T000129_P05023_N_P_J_001", "delta", COAST_POLS),
    "L_COAST_1016": ("NISAR_L2_GCOV_PROVISIONAL_V1", "NISAR_L2_PR_GCOV_033_055_A_010_4005_DHDH_A_20261016T000106_20261016T000129_P05023_N_P_J_001", "delta", COAST_POLS),
    "L_COAST_1028": ("NISAR_L2_GCOV_V1", "NISAR_L2_PR_GCOV_034_055_A_010_4005_DHDH_A_20261028T000107_20261028T000129_P05036_N_P_J_001", "delta", COAST_POLS),
    "L_COAST_1109": ("NISAR_L2_GCOV_V1", "NISAR_L2_PR_GCOV_035_055_A_010_4005_DHDH_A_20261109T000107_20261109T000130_P05036_N_P_J_001", "delta", COAST_POLS),
    "L_SEA_AFTER_1108": ("NISAR_L2_GCOV_V1", "NISAR_L2_PR_GCOV_035_048_D_080_2005_DVDV_A_20261108T130151_20261108T130208_P05036_N_P_J_001", "sea", SEA_POLS),
    "L_SEA_CALM_1003": ("NISAR_L2_GCOV_PROVISIONAL_V1", "NISAR_L2_PR_GCOV_032_048_D_080_2005_QPDH_A_20261003T130133_20261003T130207_P05023_N_F_J_001", "sea", ["VVVV", "HVHV"]),
    "L_COAST_T149_1010": ("NISAR_L2_GCOV_PROVISIONAL_V1", "NISAR_L2_PR_GCOV_032_149_D_080_4005_DHDH_A_20261010T130952_20261010T131027_P05023_N_F_J_001", "delta", COAST_POLS),
    "L_COAST_T149_1022": ("NISAR_L2_GCOV_V1", "NISAR_L2_PR_GCOV_033_149_D_080_4005_DHDH_A_20261022T130952_20261022T131027_P05036_N_F_J_001", "delta", COAST_POLS),
    "L_COAST_T149_1103": ("NISAR_L2_GCOV_V1", "NISAR_L2_PR_GCOV_034_149_D_080_4005_DHDH_A_20261103T130953_20261103T131027_P05036_N_F_J_001", "delta", COAST_POLS),
}


def find_grid(h5, freq="A"):
    """HDF5 group holding the GCOV grids for one frequency (same logic as src/gcov_subset.py)."""
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


def txt(v):
    return v.decode() if isinstance(v, bytes) else str(v)


def ident(h5, name, default=None):
    for base in ("/science/LSAR/identification", "/science/SSAR/identification"):
        if base in h5 and name in h5[base]:
            return h5[base][name][()]
    return default


def git_sha():
    try:
        return subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
                                       stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:  # noqa: BLE001
        return "nogit"


def window(x, y, bbox, epsg):
    w, s, e, n = bbox
    tr = Transformer.from_crs(4326, epsg, always_xy=True)
    xs, ys = tr.transform([w, e, e, w], [s, s, n, n])
    cols = np.where((x >= min(xs)) & (x <= max(xs)))[0]
    rows = np.where((y >= min(ys)) & (y <= max(ys)))[0]
    if cols.size == 0 or rows.size == 0:
        raise ValueError("box does not overlap this scene")
    return cols[0], cols[-1] + 1, rows[0], rows[-1] + 1


def block_mean_db(arr, k):
    """Block mean in LINEAR power over valid (finite, >0) samples, then dB. Returns float32 with NaN."""
    arr = arr.astype("float32")
    valid = np.isfinite(arr) & (arr > 0)
    arr = np.where(valid, arr, 0).astype("float64") if k > 1 else np.where(valid, arr, np.nan)
    if k > 1:
        h, w = arr.shape[0] // k * k, arr.shape[1] // k * k
        s = arr[:h, :w].reshape(h // k, k, w // k, k).sum(axis=(1, 3))
        c = valid[:h, :w].reshape(h // k, k, w // k, k).sum(axis=(1, 3))
        with np.errstate(divide="ignore", invalid="ignore"):
            arr = np.where(c > 0, s / np.maximum(c, 1), np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        db = 10 * np.log10(arr)
    db[~np.isfinite(db)] = np.nan
    return db.astype("float32")


def open_source(src):
    if re.match(r"https?://", src):
        import earthaccess  # lazy: only needed for streaming
        earthaccess.login(persist=False)
        fs = earthaccess.get_fsspec_https_session()
        return h5py.File(fs.open(src, block_size=8 * 1024 * 1024, cache_type="blockcache"), "r")
    return h5py.File(src, "r")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", required=True, choices=sorted(SCENES))
    ap.add_argument("--src", required=True, help="local .h5 path or https URL of the full granule")
    ap.add_argument("--multilook", type=int, default=None,
                    help="k x k block mean (COAST default 1 = native; SEA default = round(100 m / spacing))")
    ap.add_argument("--out", default="data/h5/")
    ap.add_argument("--suffix", default="", help="appended to the file stem, e.g. _ml2")
    args = ap.parse_args()
    t0 = time.time()

    coll, fid, boxname, pols = SCENES[args.scene]
    role = "SEA" if boxname == "sea" else "COAST"
    bbox = BOX[boxname]
    status = "PROVISIONAL" if "PROVISIONAL" in coll else "VALIDATED"
    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    with open_source(args.src) as h5:
        grid = find_grid(h5, "A")
        epsg = epsg_of(grid)
        x = grid["xCoordinates"][:]
        y = grid["yCoordinates"][:]
        dx, dy = float(x[1] - x[0]), float(y[1] - y[0])
        if dy > 0:
            raise ValueError("south-up grid not supported (expected y descending)")
        k = args.multilook or (max(1, round(SEA_POSTING_M / abs(dx))) if role == "SEA" else 1)
        c0, c1, r0, r1 = window(x, y, bbox, epsg)
        nrow, ncol = (r1 - r0) // k, (c1 - c0) // k
        r1, c1 = r0 + nrow * k, c0 + ncol * k
        gx = x[c0:c1].reshape(ncol, k).mean(axis=1)
        gy = y[r0:r1].reshape(nrow, k).mean(axis=1)
        posting = abs(dx) * k

        track = int(ident(h5, "trackNumber", int(re.search(r"GCOV_\d+_(\d+)_", fid).group(1))))
        frame = int(ident(h5, "frameNumber", int(re.search(r"GCOV_\d+_\d+_[AD]_(\d+)_", fid).group(1))))
        direction = txt(ident(h5, "orbitPassDirection", b"Ascending" if "_A_" in fid[:30] else b"Descending"))[0].upper()
        m = re.search(r"_(\d{8}T\d{6})_(\d{8}T\d{6})_", fid)
        fmt = lambda s: dt.datetime.strptime(s, "%Y%m%dT%H%M%S").strftime("%Y-%m-%dT%H:%M:%SZ")  # noqa: E731
        st = ident(h5, "zeroDopplerStartTime")
        en = ident(h5, "zeroDopplerEndTime")
        start_utc = txt(st)[:19] + "Z" if st is not None else fmt(m.group(1))
        end_utc = txt(en)[:19] + "Z" if en is not None else fmt(m.group(2))
        date = start_utc[:10].replace("-", "")
        fname = f"L_{role}_{date}_T{track:03d}{args.suffix}.h5"
        out = out_dir / fname

        # true footprint: pixel-edge rectangle -> lat/lon (sample all four edges)
        xe0, xe1 = gx[0] - posting / 2, gx[-1] + posting / 2
        yn, ys_ = gy[0] + posting / 2, gy[-1] - posting / 2
        t = np.linspace(0, 1, 21)
        ex = np.concatenate([xe0 + t * (xe1 - xe0), np.full(21, xe1), xe1 - t * (xe1 - xe0), np.full(21, xe0)])
        ey = np.concatenate([np.full(21, yn), yn + t * (ys_ - yn), np.full(21, ys_), ys_ + t * (yn - ys_)])
        lon, lat = Transformer.from_crs(epsg, 4326, always_xy=True).transform(ex, ey)
        bounds = [[float(lat.min()), float(lon.min())], [float(lat.max()), float(lon.max())]]

        src_url = args.src if re.match(r"https?://", args.src) else f"{BASE}/{coll}/{fid}/{fid}.h5"
        print(f"{args.scene}: grid EPSG:{epsg} spacing {abs(dx):g} m, window rows {r0}:{r1} cols {c0}:{c1}, "
              f"multilook {k} -> {nrow}x{ncol} @ {posting:g} m")

        tmp = out.with_suffix(".h5.part")
        stats = {}
        with h5py.File(tmp, "w") as o:
            a = o.attrs
            a["schema"] = "spacebros-subset-v1"
            a["scene_id"] = args.scene
            a["band"] = "L"
            a["role"] = role
            a["source_granule"] = fid
            a["source_url"] = src_url
            a["source_collection"] = coll
            a["product_status"] = status
            a["track"] = track
            a["frame"] = frame
            a["direction"] = direction
            a["start_utc"] = start_utc
            a["end_utc"] = end_utc
            a["box_name"] = boxname
            a["bbox_wgs84"] = np.array(bbox, dtype="float64")
            a["epsg"] = epsg
            a["posting_m"] = posting
            a["multilook"] = k
            a["created_utc"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            a["software"] = f"src/fetch/subset_h5.py@{git_sha()}"
            a["bounds_latlon"] = np.array(bounds, dtype="float64")
            dgx = o.create_dataset("grid/x", data=gx.astype("float64"))
            dgy = o.create_dataset("grid/y", data=gy.astype("float64"))
            dgx.attrs["epsg"] = epsg
            dgy.attrs["epsg"] = epsg
            chunks = (min(256, nrow), min(256, ncol))
            band_rows = max(k, (2048 // k) * k)
            for name in pols:
                if name not in grid:
                    print(f"  {name}: not in file (has {[q for q in grid.keys() if len(q) == 4]})")
                    continue
                pol = name[:2]
                d = o.create_dataset(f"backscatter/{pol}", shape=(nrow, ncol), dtype="int16", fillvalue=FILL,
                                     chunks=chunks, compression="gzip", compression_opts=6, shuffle=True)
                d.attrs["scale_factor"] = np.float64(0.01)
                d.attrs["units"] = "dB"
                d.attrs["quantity"] = f"gamma0 (RTC), from GCOV {name} linear power"
                d.attrs["_FillValue"] = np.int16(FILL)
                for rs in range(0, nrow * k, band_rows):
                    re_ = min(rs + band_rows, nrow * k)
                    blk = grid[name][r0 + rs:r0 + re_, c0:c1]
                    db = block_mean_db(blk, k)
                    q = np.full(db.shape, FILL, dtype="int16")
                    ok = np.isfinite(db)
                    q[ok] = np.clip(np.rint(db[ok] * 100), -32767, 32767).astype("int16")
                    d[rs // k:rs // k + db.shape[0], :] = q
                v = d[::4, ::4]
                vm = v != FILL
                stats[pol] = (float(np.median(v[vm]) / 100) if vm.any() else float("nan"),
                              float(1 - (d[::2, ::2] != FILL).mean()))
            if "mask" in grid:
                mk = o.create_dataset("aux/mask", shape=(nrow, ncol), dtype="uint8", chunks=chunks,
                                      compression="gzip", compression_opts=6, shuffle=True)
                off = k // 2
                for rs in range(0, nrow * k, band_rows):
                    re_ = min(rs + band_rows, nrow * k)
                    blk = grid["mask"][r0 + rs:r0 + re_, c0:c1]
                    sub = blk[off::k, off::k][:(re_ - rs) // k, :ncol]
                    mk[rs // k:rs // k + sub.shape[0], :] = sub
            o.create_dataset("metadata/orbit_pass", data=direction)
            o.create_dataset("metadata/track", data=track)
            o.create_dataset("metadata/frame", data=frame)
        tmp.replace(out)

    mb = out.stat().st_size / 1e6
    print(f"wrote {out.relative_to(ROOT)}  shape={nrow}x{ncol}  posting={posting:g} m  size={mb:.1f} MB")
    sline = "; ".join(f"{p} median {m_:.2f} dB nan {n_:.3f}" for p, (m_, n_) in stats.items())
    for p, (m_, n_) in stats.items():
        print(f"  {p}: median {m_:.2f} dB, NaN fraction {n_:.3f}")
    print(f"  bounds_latlon {bounds}  runtime {time.time() - t0:.0f} s")
    log = ROOT / "data" / "logs" / "nisar_h5_subset.md"
    with open(log, "a") as f:
        f.write(f"- {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%MZ} {args.scene} -> data/h5/{fname} "
                f"shape={nrow}x{ncol} posting={posting:g}m multilook={k} size={mb:.1f}MB {sline} "
                f"runtime={time.time() - t0:.0f}s src={fid}\n")


if __name__ == "__main__":
    main()
