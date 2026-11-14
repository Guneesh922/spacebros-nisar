"""Stream the Cyclone Arnab NISAR L-band GCOV scenes and save only the study boxes as GeoTIFF (dB).

NEEDS A NASA EARTHDATA LOGIN (~/.netrc or EARTHDATA_USERNAME/EARTHDATA_PASSWORD). Never commit credentials.
Never downloads whole files: opens each HDF5 over HTTPS (earthaccess fsspec) and reads only the box.
Reuses find_grid / epsg_of / save_tif from src/gcov_subset.py. Scene ids come from
docs/DATA_ACQUISITION_PLAN.md (ASF search probe, 14 Nov 2026).

Usage (from 05_Code/spacebros-nisar):
  python src/fetch/subset_arnab.py --probe L_SEA_EYE_1027     # login + list layers of one file
  python src/fetch/subset_arnab.py --ids P0                    # all P0 scenes
  python src/fetch/subset_arnab.py --ids L_SEA_AFTER_1108      # one scene
"""
import argparse
import datetime as dt
import hashlib
import sys
from pathlib import Path

import numpy as np
from pyproj import Transformer
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from gcov_subset import epsg_of, find_grid, save_tif  # noqa: E402

BASE = "https://nisar.asf.earthdatacloud.nasa.gov/NISAR"
BOX = {"delta": (81.6, 16.2, 82.6, 17.1), "sea": (81.0, 15.0, 85.0, 18.0)}
SEA_POLS, COAST_POLS = ["VVVV", "VHVH"], ["HHHH", "HVHV"]

# id: (priority, collection, file_id, box, pols, decimation step, short name)
SCENES = {
    "L_SEA_CALM_1015": ("P0", "NISAR_L2_GCOV_PROVISIONAL_V1", "NISAR_L2_PR_GCOV_033_048_D_080_2005_DVDV_A_20261015T130150_20261015T130208_P05023_N_P_J_001", "sea", SEA_POLS, 5, "2026-10-15_T48"),
    "L_SEA_EYE_1027": ("P0", "NISAR_L2_GCOV_V1", "NISAR_L2_PR_GCOV_034_048_D_080_2005_DVDV_A_20261027T130151_20261027T130208_P05036_N_P_J_001", "sea", SEA_POLS, 5, "2026-10-27_T48"),
    "L_COAST_1004": ("P0", "NISAR_L2_GCOV_PROVISIONAL_V1", "NISAR_L2_PR_GCOV_032_055_A_010_4005_DHDH_A_20261004T000106_20261004T000129_P05023_N_P_J_001", "delta", COAST_POLS, 1, "2026-10-04_T55"),
    "L_COAST_1016": ("P0", "NISAR_L2_GCOV_PROVISIONAL_V1", "NISAR_L2_PR_GCOV_033_055_A_010_4005_DHDH_A_20261016T000106_20261016T000129_P05023_N_P_J_001", "delta", COAST_POLS, 1, "2026-10-16_T55"),
    "L_COAST_1028": ("P0", "NISAR_L2_GCOV_V1", "NISAR_L2_PR_GCOV_034_055_A_010_4005_DHDH_A_20261028T000107_20261028T000129_P05036_N_P_J_001", "delta", COAST_POLS, 1, "2026-10-28_T55"),
    "L_COAST_1109": ("P0", "NISAR_L2_GCOV_V1", "NISAR_L2_PR_GCOV_035_055_A_010_4005_DHDH_A_20261109T000107_20261109T000130_P05036_N_P_J_001", "delta", COAST_POLS, 1, "2026-11-09_T55"),
    "L_SEA_AFTER_1108": ("P1", "NISAR_L2_GCOV_V1", "NISAR_L2_PR_GCOV_035_048_D_080_2005_DVDV_A_20261108T130151_20261108T130208_P05036_N_P_J_001", "sea", SEA_POLS, 5, "2026-11-08_T48"),
    "L_SEA_CALM_1003": ("P1", "NISAR_L2_GCOV_PROVISIONAL_V1", "NISAR_L2_PR_GCOV_032_048_D_080_2005_QPDH_A_20261003T130133_20261003T130207_P05023_N_F_J_001", "sea", ["VVVV", "HVHV"], 5, "2026-10-03_T48"),
    "L_COAST_T149_1010": ("P2", "NISAR_L2_GCOV_PROVISIONAL_V1", "NISAR_L2_PR_GCOV_032_149_D_080_4005_DHDH_A_20261010T130952_20261010T131027_P05023_N_F_J_001", "delta", COAST_POLS, 1, "2026-10-10_T149"),
    "L_COAST_T149_1022": ("P2", "NISAR_L2_GCOV_V1", "NISAR_L2_PR_GCOV_033_149_D_080_4005_DHDH_A_20261022T130952_20261022T131027_P05036_N_F_J_001", "delta", COAST_POLS, 1, "2026-10-22_T149"),
    "L_COAST_T149_1103": ("P2", "NISAR_L2_GCOV_V1", "NISAR_L2_PR_GCOV_034_149_D_080_4005_DHDH_A_20261103T130953_20261103T131027_P05036_N_F_J_001", "delta", COAST_POLS, 1, "2026-11-03_T149"),
}
# UR fallbacks if a PR file fails to open
UR_FALLBACK = {
    "L_SEA_EYE_1027": ("NISAR-UR/UR_L2_L_GCOV", "NISAR_L2_UR_GCOV_034_048_D_080_2005_DVDV_A_20261027T130151_20261027T130208_P05036_F_P_J_001"),
    "L_COAST_1028": ("NISAR-UR/UR_L2_L_GCOV", "NISAR_L2_UR_GCOV_034_055_A_010_4005_DHDH_A_20261028T000107_20261028T000129_P05036_F_P_J_001"),
    "L_COAST_1109": ("NISAR-UR/UR_L2_L_GCOV", "NISAR_L2_UR_GCOV_035_055_A_010_4005_DHDH_A_20261109T000107_20261109T000130_P05036_F_P_J_001"),
}
EXTRA_LAYERS = ["mask", "numberOfLooks", "rtcGammaToSigmaFactor"]  # saved if present (not in dB)


def url(base_dir, fid):
    if base_dir.startswith("NISAR-UR"):
        return f"https://nisar.asf.earthdatacloud.nasa.gov/{base_dir}/{fid}/{fid}.h5"
    return f"{BASE}/{base_dir}/{fid}/{fid}.h5"


def window(grid, bbox, epsg):
    x, y = grid["xCoordinates"][:], grid["yCoordinates"][:]
    w, s, e, n = bbox
    tr = Transformer.from_crs(4326, epsg, always_xy=True)
    xs, ys = tr.transform([w, e, e, w], [s, s, n, n])
    cols = np.where((x >= min(xs)) & (x <= max(xs)))[0]
    rows = np.where((y >= min(ys)) & (y <= max(ys)))[0]
    if cols.size == 0 or rows.size == 0:
        raise ValueError("box does not overlap this scene")
    return x, y, cols[0], cols[-1] + 1, rows[0], rows[-1] + 1


def block_mean(arr, k):
    if k == 1:
        return arr
    h, w = (arr.shape[0] // k) * k, (arr.shape[1] // k) * k
    with np.errstate(invalid="ignore"):
        return np.nanmean(arr[:h, :w].reshape(h // k, k, w // k, k), axis=(1, 3))


def subset_scene(h5, bbox, pols, step):
    grid = find_grid(h5, "A")
    epsg = epsg_of(grid)
    x, y, c0, c1, r0, r1 = window(grid, bbox, epsg)
    dx, dy = float(x[1] - x[0]), float(y[1] - y[0])
    top = y[r0] - dy / 2 if dy < 0 else y[r1 - 1] + dy / 2
    transform = from_origin(x[c0] - dx / 2, top, dx * step, abs(dy) * step)
    out = {}
    for name in pols + EXTRA_LAYERS:
        if name not in grid:
            print(f"    {name}: not in file")
            continue
        try:
            arr = grid[name][r0:r1, c0:c1]
        except Exception as exc:  # noqa: BLE001  (an extra layer on a different grid must not kill the scene)
            print(f"    {name}: skipped ({exc})")
            continue
        arr = arr[::-1] if dy > 0 else arr
        if name in pols:  # linear power -> block mean in linear -> dB
            arr = block_mean(arr.astype("float32"), step)
            with np.errstate(divide="ignore", invalid="ignore"):
                arr = 10 * np.log10(arr)
            arr[~np.isfinite(arr)] = np.nan
        else:
            arr = arr[::step, ::step].astype("float32")
        out[name] = arr
    return out, transform, epsg


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", nargs="+", help="scene ids, or P0 / P1 / P2")
    ap.add_argument("--probe", help="one scene id: list layers only")
    args = ap.parse_args()

    import earthaccess
    import h5py
    earthaccess.login(persist=False)
    fs = earthaccess.get_fsspec_https_session()

    def open_h5(sid, fallback=False):
        _, coll, fid, *_ = SCENES[sid]
        u = url(*UR_FALLBACK[sid]) if fallback else url(coll, fid)
        print(f"  opening {u}")
        return h5py.File(fs.open(u, block_size=8 * 1024 * 1024, cache_type="blockcache"), "r")

    if args.probe:
        with open_h5(args.probe) as h5:
            g = find_grid(h5, "A")
            print("frequencyA layers:", sorted(g.keys()), "EPSG", epsg_of(g))
        return

    sel = []
    for i in args.ids or []:
        sel += [k for k, v in SCENES.items() if v[0] == i] if i in ("P0", "P1", "P2") else [i]
    log = ROOT / "data" / "logs" / "nisar_l_subset.md"
    lines = [f"\n## Run {dt.datetime.utcnow():%Y-%m-%d %H:%MZ}\n"]
    for sid in sel:
        prio, coll, fid, box, pols, step, short = SCENES[sid]
        sub = "sea" if box == "sea" else "coast"
        out_dir = ROOT / "data" / "raw" / "nisar_l" / sub
        out_dir.mkdir(parents=True, exist_ok=True)
        print(f"- {sid} ({prio}) {fid}")
        for fb in ([False, True] if sid in UR_FALLBACK else [False]):
            try:
                with open_h5(sid, fb) as h5:
                    layers, transform, epsg = subset_scene(h5, BOX[box], pols, step)
                used = UR_FALLBACK[sid][1] if fb else fid
                for name, arr in layers.items():
                    p = out_dir / f"{short}_{name}.tif"
                    save_tif(p, arr, transform, epsg)
                    med = np.nanmedian(arr) if np.isfinite(arr).any() else float("nan")
                    nanf = float(np.isnan(arr).mean())
                    msg = f"{p.relative_to(ROOT)} shape={arr.shape} EPSG={epsg} median={med:.2f} nan={nanf:.2f} bytes={p.stat().st_size} sha256={sha256(p)} src={used}"
                    print("   ", msg)
                    lines.append(f"- {msg}\n")
                break
            except Exception as exc:  # noqa: BLE001
                print("    failed:", exc)
                lines.append(f"- FAILED {sid} ({'UR' if fb else 'PR'}): {exc}\n")
    with open(log, "a") as f:
        f.writelines(lines)
    print("log:", log)


if __name__ == "__main__":
    main()
