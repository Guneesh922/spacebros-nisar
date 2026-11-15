#!/usr/bin/env python
"""EXPERIMENTAL, analysis only (docs/PLAN_P1_P2.md section P2-B). Not part of run_all.py or its tests, not wired into the UI.

Question: did the L-band cross-pol ratio (HV minus HH, dB) change inside the area mapped as mangrove by Global Mangrove
Watch (GMW v4.0.19, 2020 extent) at Coringa between the early-October baseline and 28 Oct / 9 Nov 2026, compared with a
normal fortnight (16 Oct against 4 Oct)?  Output: data/processed/experimental/mangrove_change.json.

Run (from the repo root; -I keeps the downloaded tiles' folder out of the import path):
    .venv/bin/python -I tools/experimental/mangrove_change.py [--resamples 1000] [--seed 20261115]

Smoothing, validity and edge handling come from tools/build_web.py (read_backscatter, _box_db, _erode, _read_mask,
SMOOTH_PX, EDGE_PX, _otsu), so they are identical to the class maps. No ground truth, tide state not controlled.
"""
import argparse
import datetime
import hashlib
import json
import math
import os
import platform
import resource
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
from pyproj import Transformer  # noqa: E402

import build_web as bw  # noqa: E402  (module is __main__ guarded)

SCHEMA = "mangrove-change-v0"
BOX = (81.6, 16.2, 82.6, 17.1)                    # COAST box: lon_min, lat_min, lon_max, lat_max
GMW_DIR = os.path.join(ROOT, "data", "external", "gmw")
TILES = ["GMW_N17E081_v4019_mng.tif", "GMW_N17E082_v4019_mng.tif", "GMW_N18E082_v4019_mng.tif"]
H5 = {d: os.path.join(ROOT, "data", "h5", "L_COAST_%s_T055.h5" % d) for d in ("20261004", "20261016", "20261028", "20261109")}
OUT_JSON = os.path.join(ROOT, "data", "processed", "experimental", "mangrove_change.json")
CREDIT = "Global Mangrove Watch (CC BY 4.0)"
CITATION = ("Bunting, P., Hilarides, L., Rosenqvist, A., Zanaga, D., Van De Kerchove, R., Lucas, R., Castro Brandao Vaz dos Santos, P. "
            "(2024). Global Mangrove Watch: Annual Mangrove Extent (Version 4.0.19) [Data set]. Zenodo. "
            "https://doi.org/10.5281/zenodo.12756047. CC BY 4.0.")
CITATION_NOTE = "Citation wording is built from the Zenodo record metadata (docs/PLAN_P1_P2.md B.1); confirm on globalmangrovewatch.org before submission."
MIN_HALF = 0.5            # cell is mangrove if at least this share of its GMW source pixels is 1
BUFFER_M = 2000.0         # reference pixels stay at least this far (square window half-width) from the mangrove mask
STRATUM_HV_DB = 1.0       # baseline HV bin width for the matched reference
RANGE_BAND_KM = 10.0      # range band width for the matched reference
MIN_REF_PX = 500          # a stratum needs this many reference pixels to be used for matching
DBIN = 0.05               # histogram bin of the change (dB) for the bootstrap
DLIM = 10.0               # change values are clipped to +-DLIM dB in the histograms
L_PRIMARY = 1000
L_SENS = (500, 2000)
MIN_BLOCKS = 30           # fewer mangrove blocks than this: no interval is quoted
VARIANTS = ("uncorrected", "landwide", "matched")

T0 = time.time()


def log(*a):
    print("[%6.1fs]" % (time.time() - T0), *a, flush=True)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------------------------------------------------------
# 1. GMW tiles -> share of mangrove source pixels per 20 m UTM cell
# --------------------------------------------------------------------------------------------------------------------
def gmw_to_grid(x, y, epsg):
    """(ones, total) int32 arrays on the H5 grid: number of GMW source pixels = 1 / all source pixels whose centre falls in each
    20 m cell. Cell (i, j) spans x[j] +- dx/2, y[i] +- dy/2 (x, y are cell centres). Only the COAST box is read."""
    H, W = len(y), len(x)
    dx, dy = float(x[1] - x[0]), float(y[1] - y[0])          # +20, -20
    xe0, ye0 = float(x[0]) - dx / 2.0, float(y[0]) - dy / 2.0
    ones = np.zeros((H, W), dtype=np.int32)
    total = np.zeros((H, W), dtype=np.int32)
    tr = Transformer.from_crs(4326, epsg, always_xy=True)
    tiles = []
    for name in TILES:
        path = os.path.join(GMW_DIR, name)
        with Image.open(path) as im:
            tags = im.tag_v2
            sx, sy, _ = tags[33550]
            tp = tags[33922]
            lon0, lat0 = float(tp[3]), float(tp[4])           # top-left corner of the raster (PixelIsArea)
            arr = np.array(im)
        if arr.dtype != np.uint8 or not set(np.unique(arr).tolist()) <= {0, 1}:
            raise ValueError("%s: expected uint8 0/1" % name)
        h, w = arr.shape
        # pixel index range inside the box (centres)
        c_lo = max(int(math.ceil((BOX[0] - lon0) / sx - 0.5)), 0)
        c_hi = min(int(math.floor((BOX[2] - lon0) / sx - 0.5)), w - 1)
        r_lo = max(int(math.ceil((lat0 - BOX[3]) / sy - 0.5)), 0)
        r_hi = min(int(math.floor((lat0 - BOX[1]) / sy - 0.5)), h - 1)
        if c_lo > c_hi or r_lo > r_hi:
            tiles.append({"file": name, "pixels_in_box": 0, "mangrove_pixels_in_box": 0})
            del arr
            continue
        sub = arr[r_lo:r_hi + 1, c_lo:c_hi + 1]
        del arr
        n_ones = int(sub.sum())
        tiles.append({"file": name, "pixels_in_box": int(sub.size), "mangrove_pixels_in_box": n_ones,
                      "lon_range": [round(lon0 + (c_lo + 0.5) * sx, 4), round(lon0 + (c_hi + 0.5) * sx, 4)],
                      "lat_range": [round(lat0 - (r_hi + 0.5) * sy, 4), round(lat0 - (r_lo + 0.5) * sy, 4)]})
        if n_ones == 0:
            continue
        lons = lon0 + (np.arange(c_lo, c_hi + 1) + 0.5) * sx
        CH = 400
        nch = (sub.shape[0] + CH - 1) // CH
        has = [bool(sub[k * CH:(k + 1) * CH].any()) for k in range(nch)]
        for k in range(nch):
            if not (has[k] or (k > 0 and has[k - 1]) or (k + 1 < nch and has[k + 1])):
                continue                                       # no mangrove in this or the neighbouring chunk: cells are irrelevant
            rr = np.arange(r_lo + k * CH, r_lo + min((k + 1) * CH, sub.shape[0]))
            lats = lat0 - (rr + 0.5) * sy
            lg, lt = np.meshgrid(lons, lats)
            X, Y = tr.transform(lg.ravel(), lt.ravel())
            del lg, lt
            j = np.floor((np.asarray(X) - xe0) / dx).astype(np.int64)
            i = np.floor((np.asarray(Y) - ye0) / dy).astype(np.int64)
            inside = (i >= 0) & (i < H) & (j >= 0) & (j < W)
            flat = (i * W + j)[inside]
            val = sub[k * CH:k * CH + len(rr)].ravel()[inside]
            u, c = np.unique(flat, return_counts=True)
            total.reshape(-1)[u] += c.astype(np.int32)
            f1 = flat[val == 1]
            if f1.size:
                u1, c1 = np.unique(f1, return_counts=True)
                ones.reshape(-1)[u1] += c1.astype(np.int32)
        del sub
        log("tile %s read, %d mangrove source px in box" % (name, n_ones))
    return ones, total, tiles


# --------------------------------------------------------------------------------------------------------------------
# 2. radar
# --------------------------------------------------------------------------------------------------------------------
def load_smoothed(path):
    """smoothed HH, HV (dB, 3x3 linear power) and ok = finite both and aux/mask == 1 (as compute_coast_classes.load)."""
    out, ok = {}, None
    grid = None
    for pol in ("HH", "HV"):
        db, x, y, epsg, root = bw.read_backscatter(path, pol)
        grid = (x, y, epsg)
        out[pol] = bw._box_db(db, bw.SMOOTH_PX)
        del db
        ok = np.isfinite(out[pol]) if ok is None else ok & np.isfinite(out[pol])
    m = bw._read_mask(path)
    if m is not None:
        ok &= (m == 1)
    return out["HH"], out["HV"], ok, grid, root


def lin_mean_db(a, b):
    return (10.0 * np.log10(0.5 * (np.power(10.0, a / 10.0, dtype="float32") + np.power(10.0, b / 10.0, dtype="float32")))).astype("float32")


def box_any(mask, r):
    """True where any True lies inside the (2r+1)^2 window (square dilation) via cumulative sums."""
    h, w = mask.shape
    p = np.pad(mask.astype(np.int32), ((r + 1, r), (r + 1, r)))
    cs = p.cumsum(0, dtype=np.int32).cumsum(1, dtype=np.int32)
    del p
    n = 2 * r + 1
    s = cs[n:n + h, n:n + w] - cs[0:h, n:n + w] - cs[n:n + h, 0:w] + cs[0:h, 0:w]
    return s > 0


def range_axis(ok_b, x, y):
    """Ground-range unit vector (ux, uy) in the UTM grid, from the straight frame-end edge of the swath in the box (valid pixels
    end along a line that is perpendicular to the flight track, so that line's direction is the range direction). Returns
    (ux, uy, theta_deg, n_rows, slope_cols_per_row)."""
    H, W = ok_b.shape
    anyr = ok_b.any(1)
    last = np.where(anyr, W - 1 - ok_b[:, ::-1].argmax(1), -1)
    rows = np.where((last > 0) & (last < W - 1))[0]
    if len(rows) < 100:
        raise RuntimeError("cannot fit swath edge (%d rows)" % len(rows))
    s, b = np.polyfit(rows, last[rows], 1)
    dx = float(x[1] - x[0])
    dy = float(y[1] - y[0])
    vx, vy = s * dx, 1.0 * dy                      # edge direction for +1 row
    n = math.hypot(vx, vy)
    vx, vy = vx / n, vy / n
    if vx < 0:
        vx, vy = -vx, -vy
    return vx, vy, math.degrees(math.atan2(vy, vx)), int(len(rows)), float(s)


# --------------------------------------------------------------------------------------------------------------------
# 3. block bootstrap on histograms
# --------------------------------------------------------------------------------------------------------------------
NBINS = int(round(2 * DLIM / DBIN))


def dbin(d):
    return np.clip(((d + DLIM) / DBIN).astype(np.int32), 0, NBINS - 1)


def hist_median(h):
    cs = np.cumsum(h)
    tot = cs[-1]
    if tot <= 0:
        return np.nan
    k = int(np.searchsorted(cs, tot / 2.0))
    prev = cs[k - 1] if k > 0 else 0.0
    return -DLIM + (k + (tot / 2.0 - prev) / max(h[k], 1e-12)) * DBIN


def weighted_median(v, w):
    o = np.argsort(v, kind="stable")
    v, w = v[o], w[o]
    cw = np.cumsum(w, dtype=np.float64)
    return float(v[int(np.searchsorted(cw, cw[-1] / 2.0))])


def sparse_rows(rows, cols, ncols):
    """(row, col, count) triplets of the (row, col) pairs, rows already compact."""
    key = rows.astype(np.int64) * ncols + cols.astype(np.int64)
    u, c = np.unique(key, return_counts=True)
    return (u // ncols).astype(np.int32), (u % ncols).astype(np.int32), c.astype(np.float64)


class Dataset:
    """Compact pixel lists of one comparison (control, 28 Oct, 9 Nov) on the shared grid."""

    def __init__(self, name):
        self.name = name


def run_bootstrap(datasets, W, L_m, posting_m, n_res, rng, strata_ids):
    """Block bootstrap at block side L_m for all datasets with ONE set of block resamples (so event minus control is paired).
    Returns {dataset: {variant: array(n_res)}} plus block counts."""
    nb = int(round(L_m / posting_m))
    ncb = (W + nb - 1) // nb
    S = len(strata_ids)

    def bid(flat):
        return (flat // W // nb) * ncb + (flat % W) // nb

    # block lists (union over datasets) for mangrove and reference
    mb = np.unique(np.concatenate([bid(d.m_flat) for d in datasets]))
    rb = np.unique(np.concatenate([bid(d.r_flat) for d in datasets]))
    nM, nR = len(mb), len(rb)
    prep = {}
    for d in datasets:
        pm = np.searchsorted(mb, bid(d.m_flat)).astype(np.int64)
        pr = np.searchsorted(rb, bid(d.r_flat)).astype(np.int64)
        m_rows, m_cols, m_vals = sparse_rows(pm, d.m_bin, NBINS)
        # mangrove composition per block and stratum (eligible strata only)
        el = d.m_s >= 0
        comp = np.bincount(pm[el] * S + d.m_s[el], minlength=nM * S).reshape(nM, S).astype(np.float64)
        ra_rows, ra_cols, ra_vals = sparse_rows(pr, d.r_bin, NBINS)
        er = d.r_s >= 0
        rs_rows, rs_cols, rs_vals = sparse_rows(pr[er], d.r_s[er].astype(np.int64) * NBINS + d.r_bin[er], S * NBINS)
        prep[d.name] = (m_rows, m_cols, m_vals, comp, ra_rows, ra_cols, ra_vals, rs_rows, rs_cols, rs_vals)
    res = {d.name: {v: np.empty(n_res) for v in VARIANTS} for d in datasets}
    res_m = {d.name: np.empty(n_res) for d in datasets}       # plain median in M (== uncorrected), kept separate for clarity
    for r in range(n_res):
        cM = rng.multinomial(nM, np.full(nM, 1.0 / nM)).astype(np.float64)
        cR = rng.multinomial(nR, np.full(nR, 1.0 / nR)).astype(np.float64)
        for d in datasets:
            (m_rows, m_cols, m_vals, comp, ra_rows, ra_cols, ra_vals, rs_rows, rs_cols, rs_vals) = prep[d.name]
            hm = np.bincount(m_cols, weights=cM[m_rows] * m_vals, minlength=NBINS)
            mM = hist_median(hm)
            ha = np.bincount(ra_cols, weights=cR[ra_rows] * ra_vals, minlength=NBINS)
            mlw = hist_median(ha)
            hs = np.bincount(rs_cols, weights=cR[rs_rows] * rs_vals, minlength=S * NBINS).reshape(S, NBINS)
            nr_s = hs.sum(1)
            nm_s = cM @ comp
            w = np.where(nr_s > 0, nm_s / np.maximum(nr_s, 1e-12), 0.0)
            mmt = hist_median((w[:, None] * hs).sum(0))
            res[d.name]["uncorrected"][r] = mM
            res[d.name]["landwide"][r] = mM - mlw
            res[d.name]["matched"][r] = mM - mmt
    return res, {"block_side_m": int(L_m), "cells_per_block_side": nb, "mangrove_blocks": int(nM), "reference_blocks": int(nR)}


def interval(a):
    lo, hi = np.percentile(a, [2.5, 97.5])
    return [round(float(lo), 3), round(float(hi), 3)]


# --------------------------------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--resamples", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=20261115)
    ap.add_argument("--out", default=OUT_JSON)
    args = ap.parse_args()

    for p in list(H5.values()) + [os.path.join(GMW_DIR, t) for t in TILES]:
        if not os.path.exists(p):
            raise SystemExit("missing input: %s" % p)

    # ---- baseline scenes: validity, permanent water, baseline ratio ----------------------------------------------------
    hh4, hv4, ok4, grid, root4 = load_smoothed(H5["20261004"])
    hh16, hv16, ok16, grid2, root16 = load_smoothed(H5["20261016"])
    x, y, epsg = grid
    if not (np.array_equal(x, grid2[0]) and np.array_equal(y, grid2[1])):
        raise SystemExit("baseline grids differ")
    H, W = len(y), len(x)
    posting = abs(float(x[1] - x[0]))
    px_km2 = abs(float(x[1] - x[0]) * float(y[1] - y[0])) / 1e6
    ok_b = ok4 & ok16
    del ok4, ok16
    valid = bw._erode(ok_b, bw.EDGE_PX)
    pool = np.concatenate([hh4[valid], hh16[valid]])
    T, c, h = bw._otsu(pool, -40.0, 10.0, 0.1)
    del pool
    perm = valid & (hh4 < T) & (hh16 < T)
    base_hh = lin_mean_db(hh4, hh16)
    base_hv = lin_mean_db(hv4, hv16)
    R4 = hv4 - hh4
    R16 = hv16 - hh16
    D_ctrl = R16 - R4                       # control: 16 Oct against 4 Oct only
    D_ctrl_hh = hh16 - hh4
    D_ctrl_hv = hv16 - hv4
    Rb = base_hv - base_hh
    del hh4, hv4, hh16, hv16, R4, R16
    log("baseline loaded: grid %dx%d, valid %.1f%%, Otsu T %.2f dB, perm water %.0f km2" % (H, W, 100.0 * valid.mean(), T, perm.sum() * px_km2))

    # range axis (for the matched reference)
    ux, uy, theta, nrow_fit, slope = range_axis(ok_b, x, y)
    del ok_b
    rng_km = ((x[None, :] - x[0]) * ux + (y[:, None] - y[0]) * uy) / 1000.0     # (H, W) float64 -> 214 MB; make float32
    rng_km = rng_km.astype(np.float32)
    rband = np.floor(rng_km / RANGE_BAND_KM).astype(np.int16)
    del rng_km
    hvbin = np.floor(np.clip(base_hv, -60.0, 20.0) / STRATUM_HV_DB)
    hvbin = np.where(np.isfinite(hvbin), hvbin, -99).astype(np.int16)
    skey = (hvbin.astype(np.int32) + 100) * 100 + (rband.astype(np.int32) + 20)      # unique combined key
    del hvbin, rband
    log("range axis theta=%.1f deg from %d edge rows" % (theta, nrow_fit))

    # ---- mangrove mask --------------------------------------------------------------------------------------------------
    ones, total, tiles = gmw_to_grid(x, y, epsg)
    M0 = (total > 0) & (ones.astype(np.float32) >= MIN_HALF * total.astype(np.float32))
    n_hit = int((ones > 0).sum())
    del ones, total
    Me = bw._erode(M0, 1)
    M = Me & valid & ~perm
    buf = box_any(M0, int(round(BUFFER_M / posting)))
    ref_ok = valid & ~perm & ~buf
    log("mask: any-hit cells %d, >=half cells %d (%.1f km2), eroded %d, final M %d (%.1f km2), reference px %d" %
        (n_hit, M0.sum(), M0.sum() * px_km2, Me.sum(), M.sum(), M.sum() * px_km2, ref_ok.sum()))

    # eligible strata for matching
    kM = skey[M]
    ukeys, cM_ = np.unique(kM, return_counts=True)
    kR = skey[ref_ok]
    ur, cR_ = np.unique(kR, return_counts=True)
    ref_count = dict(zip(ur.tolist(), cR_.tolist()))
    strata_ids = np.array([k for k in ukeys.tolist() if ref_count.get(k, 0) >= MIN_REF_PX], dtype=np.int64)
    del kM, kR

    def decode(k):
        return {"baseline_hv_db_bin": [int(k // 100 - 100), int(k // 100 - 100 + 1)], "range_band_km": [int((k % 100 - 20) * RANGE_BAND_KM), int((k % 100 - 20 + 1) * RANGE_BAND_KM)]}

    # ---- datasets ------------------------------------------------------------------------------------------------------
    datasets = []
    point = {}

    def extract(name, Dd, valid_k, Dhh, Dhv):
        d = Dataset(name)
        m = M & valid_k
        r = ref_ok & valid_k
        d.m_flat = np.flatnonzero(m.ravel()).astype(np.int32)
        d.r_flat = np.flatnonzero(r.ravel()).astype(np.int32)
        dm = Dd.ravel()[d.m_flat]
        dr = Dd.ravel()[d.r_flat]
        d.m_bin, d.r_bin = dbin(dm), dbin(dr)
        sm = np.searchsorted(strata_ids, skey.ravel()[d.m_flat])
        sm_c = np.clip(sm, 0, max(len(strata_ids) - 1, 0))
        d.m_s = np.where(strata_ids[sm_c] == skey.ravel()[d.m_flat], sm_c, -1).astype(np.int64)
        sr = np.searchsorted(strata_ids, skey.ravel()[d.r_flat])
        sr_c = np.clip(sr, 0, max(len(strata_ids) - 1, 0))
        d.r_s = np.where(strata_ids[sr_c] == skey.ravel()[d.r_flat], sr_c, -1).astype(np.int64)
        # point estimates (exact medians)
        S = len(strata_ids)
        nm_s = np.bincount(d.m_s[d.m_s >= 0], minlength=S).astype(np.float64)
        nr_s = np.bincount(d.r_s[d.r_s >= 0], minlength=S).astype(np.float64)
        w_s = np.where(nr_s > 0, nm_s / np.maximum(nr_s, 1), 0.0)
        wr = np.where(d.r_s >= 0, w_s[np.clip(d.r_s, 0, None)], 0.0)
        keep = wr > 0
        m_M = float(np.median(dm))
        m_lw = float(np.median(dr))
        m_mt = weighted_median(dr[keep], wr[keep])
        m_M_match = float(np.median(dm[d.m_s >= 0])) if (d.m_s >= 0).any() else float("nan")
        dh_m = float(np.median(Dhh.ravel()[d.m_flat]))
        dv_m = float(np.median(Dhv.ravel()[d.m_flat]))
        dh_r = float(np.median(Dhh.ravel()[d.r_flat]))
        dv_r = float(np.median(Dhv.ravel()[d.r_flat]))
        point[name] = {
            "n_mangrove_px": int(len(dm)), "mangrove_area_km2_valid": round(len(dm) * px_km2, 1), "n_reference_px": int(len(dr)),
            "median_change_in_mangrove_db": round(m_M, 3),
            "median_change_reference_landwide_db": round(m_lw, 3),
            "median_change_reference_matched_db": round(m_mt, 3),
            "delta_uncorrected_db": round(m_M, 3),
            "delta_landwide_db": round(m_M - m_lw, 3),
            "delta_matched_db": round(m_M - m_mt, 3),
            "mangrove_px_in_matched_strata_pct": round(100.0 * float((d.m_s >= 0).mean()), 2),
            "median_mangrove_in_matched_strata_db": round(m_M_match, 3),
            "components_point_estimates_db": {
                "HH_change_median_mangrove": round(dh_m, 3), "HV_change_median_mangrove": round(dv_m, 3),
                "HH_change_median_reference_landwide": round(dh_r, 3), "HV_change_median_reference_landwide": round(dv_r, 3)},
            "baseline_hv_median_mangrove_db": round(float(np.median(base_hv.ravel()[d.m_flat])), 2),
            "baseline_hv_median_reference_db": round(float(np.median(base_hv.ravel()[d.r_flat])), 2),
        }
        datasets.append(d)

    extract("control_16Oct_vs_4Oct", D_ctrl, valid, D_ctrl_hh, D_ctrl_hv)
    del D_ctrl, D_ctrl_hh, D_ctrl_hv
    log("control extracted: %s" % json.dumps(point["control_16Oct_vs_4Oct"]))
    scene = {"20261004": root4, "20261016": root16}
    for dd, nm in (("20261028", "event_28Oct"), ("20261109", "event_9Nov")):
        hh, hv, ok, g, root = load_smoothed(H5[dd])
        if not (np.array_equal(g[0], x) and np.array_equal(g[1], y)):
            raise SystemExit("grid of %s differs from baseline" % dd)
        Dd = (hv - hh) - Rb
        Dhh = hh - base_hh
        Dhv = hv - base_hv
        del hh, hv
        extract(nm, Dd, valid & ok, Dhh, Dhv)
        scene[dd] = root
        del Dd, Dhh, Dhv, ok
        log("%s extracted: %s" % (nm, json.dumps(point[nm])))
    del Rb, base_hh, skey

    # ---- bootstrap -----------------------------------------------------------------------------------------------------
    boot = {}
    for L in (L_PRIMARY,) + L_SENS:
        rng = np.random.default_rng(args.seed)
        res, info = run_bootstrap(datasets, W, L, posting, args.resamples, rng, strata_ids)
        out = {"info": info, "interval_quoted": info["mangrove_blocks"] >= MIN_BLOCKS}
        for d in datasets:
            out[d.name] = {}
            for v in VARIANTS:
                a = res[d.name][v]
                out[d.name][v] = {"ci95": interval(a) if out["interval_quoted"] else None, "se": round(float(a.std(ddof=1)), 3)}
        for nm in ("event_28Oct", "event_9Nov"):
            out["paired_event_minus_control_" + nm] = {}
            for v in VARIANTS:
                dlt = res[nm][v] - res["control_16Oct_vs_4Oct"][v]
                out["paired_event_minus_control_" + nm][v] = {
                    "ci95": interval(dlt) if out["interval_quoted"] else None, "se": round(float(dlt.std(ddof=1)), 3),
                    "share_of_resamples_event_above_control": round(float((dlt > 0).mean()), 3)}
        boot["L%dm" % L] = out
        log("bootstrap L=%d m done: %d / %d blocks" % (L, info["mangrove_blocks"], info["reference_blocks"]))

    # ---- verdict -------------------------------------------------------------------------------------------------------
    def excludes0(ci):
        return ci is not None and (ci[0] > 0 or ci[1] < 0)

    verdict = {}
    for nm in ("event_28Oct", "event_9Nov"):
        p = point[nm]
        signs = {v: int(np.sign(p["delta_" + v + "_db"])) for v in VARIANTS}
        agree = len(set(signs.values())) == 1 and 0 not in signs.values()
        flags = {}
        for Lk in boot:
            pc = boot[Lk]["paired_event_minus_control_" + nm]["matched"]["ci95"]
            ev = boot[Lk][nm]["matched"]["ci95"]
            flags[Lk] = {"paired_event_minus_control_excludes_zero": excludes0(pc), "event_delta_excludes_zero": excludes0(ev)}
        sep_all_L = all(f["paired_event_minus_control_excludes_zero"] for f in flags.values())
        sep_prim = flags["L%dm" % L_PRIMARY]["paired_event_minus_control_excludes_zero"]
        if sep_all_L and agree:
            code = "change_detected_experimental"
        elif sep_prim and not agree:
            code = "not_separable_from_calibration"
        else:
            code = "no_detectable_change"
        verdict[nm] = {"code": code, "three_corrections_agree_in_sign": agree, "signs": signs, "by_block_size": flags,
                       "rule": "change_detected_experimental only if the matched-corrected event-minus-control paired 95% interval excludes 0 at all block sizes "
                               "(500 m, 1 km, 2 km) AND uncorrected, land-wide and matched deltas agree in sign; "
                               "not_separable_from_calibration if separated from the control at 1 km but the corrections disagree in sign; otherwise no_detectable_change"}

    ctrl = point["control_16Oct_vs_4Oct"]
    prim = boot["L%dm" % L_PRIMARY]

    def wording(nm, label):
        p, v = point[nm], verdict[nm]
        base = ("Experimental. Area mapped as mangrove by Global Mangrove Watch (2020 extent), L-band HV minus HH, %s against the early-October baseline. " % label)
        tail = " No ground truth was used, tide state was not controlled, and the baseline scenes are provisional."
        if v["code"] == "change_detected_experimental":
            ci = prim[nm]["matched"]["ci95"]
            return (base + "The median difference changed by about %+.1f dB (95%% range %.1f to %.1f, matched reference), compared with %+.1f dB between two normal pre-storm passes."
                    % (p["delta_matched_db"], ci[0], ci[1], ctrl["delta_matched_db"]) + tail)
        if v["code"] == "not_separable_from_calibration":
            return (base + "The size and sign of the difference depend on the reference used (uncorrected %+.1f dB, land-wide corrected %+.1f dB, matched corrected %+.1f dB), "
                    "so any change cannot be separated from calibration differences between the scenes." % (p["delta_uncorrected_db"], p["delta_landwide_db"], p["delta_matched_db"]) + tail)
        ci = prim[nm]["matched"]["ci95"]
        return (base + "No detectable change: the matched-reference change is %+.1f dB (95%% range %.1f to %.1f), not distinguishable from the %+.1f dB seen between two normal pre-storm passes."
                % (p["delta_matched_db"], ci[0], ci[1], ctrl["delta_matched_db"]) + tail)

    allowed = {"overall": ("Experimental, analysis only. Global Mangrove Watch 2020 mangrove extent used as the mask. No ground truth. Tide state not controlled. "
                           "Only the verdict string of each date may be quoted; no damage, loss, die-back, area or cause."),
               "event_28Oct": wording("event_28Oct", "28 Oct"), "event_9Nov": wording("event_9Nov", "9 Nov (also contains Murasu and the river peak)")}

    runtime = time.time() - T0
    doc = {
        "schema": SCHEMA,
        "status": "EXPERIMENTAL: analysis only, not in run_all, not wired into the UI",
        "credit": CREDIT,
        "citation": CITATION,
        "citation_note": CITATION_NOTE,
        "allowed_wording": allowed,
        "must_state": ["experimental", "no ground truth", "tide state not controlled (no tide source retrieved)",
                       "baselines (4 and 16 Oct) are PROVISIONAL products, events are VALIDATED",
                       "9 Nov pass also contains Cyclone Murasu and the Godavari river peak",
                       "GMW 2020 extent is 6 years old; GMW accuracy is global and varies locally",
                       "post-cyclone canopy and soil wetness and standing water change HH and HV (not tested here)",
                       "reference land (agriculture) and target (mangrove) have different seasonal drivers"],
        "not_allowed": ["damage", "loss", "die-back", "deforestation", "cause (cyclone)", "area in km2 or percent of mangrove affected", "healthy"],
        "verdict": verdict,
        "statistic": "R = HV_dB - HH_dB after 3x3 linear-power boxcar; D = R(event) - R(baseline); baseline = linear-power mean of 4 and 16 Oct. "
                     "Control: R(16 Oct) - R(4 Oct) (baseline of one date, so its noise is slightly higher).",
        "point_estimates": point,
        "bootstrap": boot,
        "bootstrap_settings": {"method": "block bootstrap on the UTM grid, blocks resampled with replacement; mangrove blocks and reference blocks resampled independently, the same resamples used for control and both events (paired); "
                                         "medians from 0.05 dB histograms (change clipped to +-10 dB)",
                               "resamples": args.resamples, "seed": args.seed, "primary_block_m": L_PRIMARY, "sensitivity_block_m": list(L_SENS),
                               "min_blocks_for_interval": MIN_BLOCKS, "interval": "2.5 to 97.5 percentile"},
        "corrections": {
            "uncorrected": "median of D over mangrove cells",
            "landwide": "median D in mangrove minus median D over all valid non-permanent-water land at least %d m (square window) from the mangrove mask" % BUFFER_M,
            "matched": "as landwide, but the reference distribution is reweighted so that it has the same mix of (baseline HV 1 dB bin, 10 km ground-range band) as the mangrove cells; "
                       "strata need >= %d reference pixels, mangrove pixels in other strata (%.2f%% / %.2f%% / %.2f%% for control / 28 Oct / 9 Nov missing) are not used for the composition"
                       % (MIN_REF_PX, 100 - point["control_16Oct_vs_4Oct"]["mangrove_px_in_matched_strata_pct"], 100 - point["event_28Oct"]["mangrove_px_in_matched_strata_pct"], 100 - point["event_9Nov"]["mangrove_px_in_matched_strata_pct"]),
            "assumption": "the offset between the provisional baseline and the validated event scenes is additive in dB, equal for mangrove and matched reference pixels, and not caused by the storm"},
        "mask": {
            "source": "GMW v4.0.19 Annual Mangrove Extent, 2020 (Zenodo 10.5281/zenodo.12756047)",
            "rule": "20 m UTM 44N cell (EPSG:%s, grid of data/h5/L_COAST_*.h5) is mangrove if >= %.0f%% of the GMW 0.0001 deg source pixels whose centre falls in it are 1; "
                    "eroded by 1 cell; permanent water (smoothed HH < Otsu T on both baseline dates) and invalid cells removed" % (epsg, MIN_HALF * 100),
            "cells_any_source_pixel_hit": n_hit, "cells_mask_before_erosion": int(M0.sum()), "area_km2_before_erosion": round(float(M0.sum()) * px_km2, 1),
            "cells_final_mask": int(M.sum()), "area_km2_final": round(float(M.sum()) * px_km2, 1),
            "tiles": tiles, "coast_box_lonlat": list(BOX)},
        "reference": {"rule": "valid, not permanent water, not in 2 km (square) buffer of the mangrove mask", "n_pixels": int(ref_ok.sum()),
                      "matching_strata_used": int(len(strata_ids)),
                      "strata": [dict(decode(int(k)), mangrove_px=int(dict(zip(ukeys.tolist(), cM_.tolist()))[int(k)]), reference_px=int(ref_count[int(k)])) for k in strata_ids],
                      "range_axis": {"derived_from": "straight frame-end edge of the valid swath inside the box (perpendicular to the flight track), %d rows fitted" % nrow_fit,
                                     "direction_deg_ccw_from_east_in_utm": round(theta, 2), "band_km": RANGE_BAND_KM}},
        "thresholds": {"water_otsu_hh_db": round(float(T), 2), "smooth_px": bw.SMOOTH_PX, "edge_px": bw.EDGE_PX, "min_mangrove_share": MIN_HALF,
                       "buffer_m": BUFFER_M, "stratum_hv_db": STRATUM_HV_DB, "range_band_km": RANGE_BAND_KM, "min_ref_px": MIN_REF_PX},
        "provenance": {
            "script": "tools/experimental/mangrove_change.py", "created_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "command": ".venv/bin/python -I tools/experimental/mangrove_change.py --resamples %d --seed %d" % (args.resamples, args.seed),
            "python": platform.python_version(), "numpy": np.__version__, "runtime_s": round(runtime, 1),
            "peak_rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024.0 * 1024.0), 0),
            "inputs_sha256": dict({os.path.relpath(os.path.join(GMW_DIR, t), ROOT): sha256(os.path.join(GMW_DIR, t)) for t in TILES},
                                  **{os.path.relpath(p, ROOT): sha256(p) for p in H5.values()}),
            "scenes": {dd: {"scene_id": str(s.get("scene_id")), "product_status": str(s.get("product_status")), "start_utc": str(s.get("start_utc"))} for dd, s in scene.items()},
            "radar_helpers": "tools/build_web.py (read_backscatter, _box_db, _erode, _read_mask, _otsu)"},
        "limitations": ["no ground truth; tide not checked; mask is the 2020 extent", "HV offset between provisional baselines and validated events is not uniform (docs/review/LBAND_TEST.md)",
                        "the control uses a one-date baseline, so its noise is slightly higher than the events'",
                        "range band is a proxy derived from the swath edge, not from incidence-angle metadata (none in the H5)"],
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1)
    log("wrote %s  (peak RSS %.0f MB)" % (os.path.relpath(args.out, ROOT), doc["provenance"]["peak_rss_mb"]))


if __name__ == "__main__":
    main()
