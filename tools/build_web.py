#!/usr/bin/env python3
"""Build browser display assets from the committed H5 subsets.

Reads data/processed/manifest.json. For every layer that has an ``h5`` field (path under data/h5/) and whose
file exists, it reads ``/backscatter/{pol}`` (schema spacebros-subset-v1, see docs/DATA_STORAGE.md), reprojects
the projected grid (UTM) to a regular EPSG:4326 lat/lon grid by inverse mapping (nearest neighbour, numpy only)
and writes, into data/web/ (git-ignored, rebuilt by the Pages workflow):

    {layer_id}.png   8-bit greyscale + alpha (alpha 0 = no data), fixed dB stretch, for Leaflet imageOverlay
    {layer_id}.json  bounds [[S,W],[N,E]], p2/p50/p98 (dB), nan_frac, source_granule, product_status, ...

Stretch (dB, linear map to 0..255): COAST -25..0, SEA -25..0; a layer may override with ``"stretch": [lo, hi]``.
PNGs are kept <= 600 KB by shrinking the output grid if needed.

Usage:
    python tools/build_web.py [--manifest PATH] [--out DIR] [--only LAYER_ID ...] [--max-kb 600]

Exit 0 also when there is nothing to build (no H5 files yet). Deps: h5py numpy pyproj Pillow.
"""
import argparse
import datetime
import glob
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STRETCH = {"COAST": (-25.0, 0.0), "SEA": (-25.0, 0.0)}
MAX_DIM = 2400          # longest side of the first-try output image, px
MIN_DIM = 200           # never shrink below this when meeting the size cap


def _attr(v):
    """h5py attribute -> plain python (bytes -> str, numpy scalar -> python)."""
    if isinstance(v, bytes):
        return v.decode("utf-8", "replace")
    if hasattr(v, "item") and getattr(v, "ndim", 1) == 0:
        return v.item()
    if hasattr(v, "tolist"):
        return v.tolist()
    return v


def _epsg_int(v):
    if v is None:
        return None
    s = str(_attr(v)).upper().replace("EPSG:", "").strip()
    return int(float(s))


def role_of(layer, root_attrs):
    r = str(root_attrs.get("role") or "").upper()
    if r in STRETCH:
        return r
    return "SEA" if "_sea_" in layer["id"] else "COAST"


def read_backscatter(h5file, pol):
    """Return (db float32 array with NaN for fill, x, y, epsg, root_attrs). Applies scale_factor and _FillValue."""
    import h5py
    import numpy as np
    with h5py.File(h5file, "r") as f:
        root = {k: _attr(v) for k, v in f.attrs.items()}
        if pol not in f["backscatter"]:
            raise KeyError("pol %s not in /backscatter (has %s)" % (pol, list(f["backscatter"].keys())))
        ds = f["backscatter/" + pol]
        raw = ds[...]
        scale = float(_attr(ds.attrs.get("scale_factor", 1.0)))
        fill = ds.attrs.get("_FillValue")
        fill = None if fill is None else _attr(fill)
        x = f["grid/x"][...].astype("float64")
        y = f["grid/y"][...].astype("float64")
        epsg = _epsg_int(root.get("epsg", f["grid/x"].attrs.get("epsg")))
    bad = ~np.isfinite(raw.astype("float64")) if raw.dtype.kind == "f" else np.zeros(raw.shape, bool)
    if fill is not None:
        bad |= raw == fill
    db = raw.astype("float32") * np.float32(scale)
    db[bad] = np.nan
    return db, x, y, epsg, root


def footprint_latlon(x, y, epsg):
    """Lat/lon extent [[S,W],[N,E]] of the projected grid (pixel edges), sampled along the whole border."""
    import numpy as np
    from pyproj import Transformer
    dx = float(abs(x[1] - x[0])) if len(x) > 1 else 1.0
    dy = float(abs(y[1] - y[0])) if len(y) > 1 else 1.0
    xs = np.linspace(x.min() - dx / 2, x.max() + dx / 2, 50)
    ys = np.linspace(y.min() - dy / 2, y.max() + dy / 2, 50)
    bx = np.concatenate([xs, xs, np.full_like(ys, xs[0]), np.full_like(ys, xs[-1])])
    by = np.concatenate([np.full_like(xs, ys[0]), np.full_like(xs, ys[-1]), ys, ys])
    t = Transformer.from_crs(epsg, 4326, always_xy=True)
    lon, lat = t.transform(bx, by)
    return float(lat.min()), float(lon.min()), float(lat.max()), float(lon.max())


def warp_to_latlon(db, x, y, epsg, max_dim=MAX_DIM):
    """Nearest-neighbour inverse mapping of ``db`` (nrow, ncol; y descending) onto a regular lat/lon grid.

    Output pixel size is the source posting converted to degrees (so we never oversample), enlarged if the
    longest side would exceed ``max_dim``. Returns (out float32 with NaN outside/no-data, bounds [[S,W],[N,E]]).
    """
    import numpy as np
    from pyproj import Transformer
    s, w, n, e = footprint_latlon(x, y, epsg)
    dx = float(abs(x[1] - x[0]))
    dy = float(abs(y[1] - y[0]))
    lat0 = (s + n) / 2.0
    dlat = dy / 111320.0
    dlon = dx / (111320.0 * np.cos(np.radians(lat0)))
    ncol = max(2, int(round((e - w) / dlon)))
    nrow = max(2, int(round((n - s) / dlat)))
    k = max(ncol, nrow) / float(max_dim)
    if k > 1:
        ncol, nrow = max(2, int(ncol / k)), max(2, int(nrow / k))
    dlon = (e - w) / ncol
    dlat = (n - s) / nrow
    lon = w + (np.arange(ncol) + 0.5) * dlon
    lat = n - (np.arange(nrow) + 0.5) * dlat
    LON, LAT = np.meshgrid(lon, lat)
    t = Transformer.from_crs(4326, epsg, always_xy=True)
    X, Y = t.transform(LON, LAT)
    col = np.rint((X - x[0]) / (x[1] - x[0])).astype("int64")
    row = np.rint((Y - y[0]) / (y[1] - y[0])).astype("int64")
    inside = (col >= 0) & (col < db.shape[1]) & (row >= 0) & (row < db.shape[0])
    out = np.full((nrow, ncol), np.nan, dtype="float32")
    out[inside] = db[row[inside], col[inside]]
    return out, [[s, w], [n, e]]


def to_png_bytes(img_db, lo, hi):
    """dB array (NaN = no data) -> 8-bit greyscale + alpha PNG bytes."""
    import numpy as np
    from PIL import Image
    valid = np.isfinite(img_db)
    g = np.zeros(img_db.shape, dtype="uint8")
    g[valid] = np.clip(np.rint((img_db[valid] - lo) / (hi - lo) * 255.0), 0, 255).astype("uint8")
    a = np.where(valid, 255, 0).astype("uint8")
    im = Image.merge("LA", (Image.fromarray(g), Image.fromarray(a)))
    buf = io.BytesIO()
    im.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def build_layer(layer, h5file, out_dir, max_kb):
    import numpy as np
    pol = layer.get("pol")
    if not pol:
        raise ValueError("layer has no 'pol'")
    db, x, y, epsg, root = read_backscatter(h5file, pol)
    role = role_of(layer, root)
    lo, hi = layer.get("stretch") or STRETCH[role]
    valid = np.isfinite(db)
    nv = int(valid.sum())
    if nv:
        p2, p50, p98 = [round(float(v), 2) for v in np.percentile(db[valid], [2, 50, 98])]
    else:
        p2 = p50 = p98 = None
    nan_frac = 1.0 - nv / float(db.size)

    max_dim = MAX_DIM
    while True:
        img, bounds = warp_to_latlon(db, x, y, epsg, max_dim)
        png = to_png_bytes(img, lo, hi)
        if len(png) <= max_kb * 1024 or max_dim <= MIN_DIM:
            break
        max_dim = max(MIN_DIM, int(max_dim * 0.8))
    lid = layer["id"]
    with open(os.path.join(out_dir, lid + ".png"), "wb") as fh:
        fh.write(png)
    meta = {
        "layer_id": lid,
        "png": "data/web/%s.png" % lid,
        "bounds": [[round(bounds[0][0], 5), round(bounds[0][1], 5)], [round(bounds[1][0], 5), round(bounds[1][1], 5)]],
        "pol": pol,
        "role": role,
        "stretch_db": [lo, hi],
        "p2": p2, "p50": p50, "p98": p98,
        "nan_frac": round(nan_frac, 4),
        "source_granule": root.get("source_granule"),
        "product_status": root.get("product_status"),
        "scene_id": root.get("scene_id"),
        "h5": os.path.relpath(h5file, ROOT) if h5file.startswith(ROOT) else h5file,
        "image_px": [int(img.shape[1]), int(img.shape[0])],
        "png_kb": round(len(png) / 1024.0, 1),
        "built_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    with open(os.path.join(out_dir, lid + ".json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=1)
        fh.write("\n")
    return meta


# ----------------------------------------------------------------------------------------------------------
# Derived products: NOT implemented yet (phase 2). Stubs only so the pipeline shape is fixed.
# ----------------------------------------------------------------------------------------------------------

def build_class_maps(manifest, out_dir):
    """TODO (phase 2): class maps from the coast H5 series -> data/web/nisar_class_*.png (+ .json).

    Planned classes (labels always start with "likely"): new water (HH/HV drop vs. pre-storm baseline 20261004/
    20261016 below a dB threshold, 20261028 and 20261109 epochs), wet crops, no change. Output: one RGBA PNG per
    class layer in the manifest (fill colour from layer.classes[0].colour), same lat/lon grid and bounds as the
    source coast PNGs. Must mask permanent water and carry a per-class pixel count in the JSON.
    """
    raise NotImplementedError("class maps: TODO phase 2")


DIFF_RANGE = (-15.0, 15.0)   # dB, diverging stretch of the sea difference map


def _diverging_rgb(t):
    """t in 0..1 (0 = most negative, 0.5 = no change, 1 = most positive) -> uint8 RGB, blue-white-red."""
    import numpy as np
    neg = np.array([33, 102, 172], dtype="float32")    # darker sea (smoother)
    mid = np.array([247, 247, 247], dtype="float32")
    pos = np.array([178, 24, 43], dtype="float32")     # brighter sea (rougher)
    t = np.clip(t, 0.0, 1.0)[..., None]
    lo = mid + (neg - mid) * np.clip((0.5 - t) / 0.5, 0, 1)
    hi = mid + (pos - mid) * np.clip((t - 0.5) / 0.5, 0, 1)
    return np.rint(np.where(t < 0.5, lo, hi)).astype("uint8")


def build_sea_difference(manifest, out_dir, max_kb=600):
    """Sea difference map: VV(27 Oct) minus VV(15 Oct), Track 48, in dB, on the common grid.

    Reads the two ``h5_sources`` of layer nisar_sea_diff_20261027_vs_20261015 (after first, before second). If the
    grids differ the arrays are cropped to the intersection (grids must share posting and be offset by whole
    pixels, otherwise this raises). Diverging ramp -15..+15 dB, alpha 0 where either input is fill. Writes
    data/web/{id}.png and .json (bounds, p2/p50/p98 of the difference, nan_frac, grid check).
    """
    import numpy as np
    from PIL import Image
    layer = next((l for l in manifest.get("layers", []) if l["id"] == "nisar_sea_diff_20261027_vs_20261015"), None)
    if not layer or not layer.get("h5_sources"):
        print("skip  nisar_sea_diff_20261027_vs_20261015: no h5_sources")
        return None
    pa, pb = [os.path.join(ROOT, q) for q in layer["h5_sources"][:2]]
    if not (os.path.exists(pa) and os.path.exists(pb)):
        print("skip  sea difference: input H5 missing")
        return None
    pol = layer.get("pol", "VV")
    da, xa, ya, epsg_a, ra = read_backscatter(pa, pol)
    db_, xb, yb, epsg_b, rb = read_backscatter(pb, pol)
    if epsg_a != epsg_b:
        raise ValueError("sea difference: different CRS (%s vs %s)" % (epsg_a, epsg_b))
    step = float(xa[1] - xa[0])
    identical = (da.shape == db_.shape and np.array_equal(xa, xb) and np.array_equal(ya, yb))
    if identical:
        crop = "grids identical"
    else:
        if abs(step - float(xb[1] - xb[0])) > 1e-6 or abs(float(ya[1] - ya[0]) - float(yb[1] - yb[0])) > 1e-6:
            raise ValueError("sea difference: different posting")
        x0, x1 = max(xa.min(), xb.min()), min(xa.max(), xb.max())
        y0, y1 = max(ya.min(), yb.min()), min(ya.max(), yb.max())
        if x0 > x1 or y0 > y1:
            raise ValueError("sea difference: grids do not overlap")
        def idx(v, lo, hi):
            return np.where((v >= lo - 1e-6) & (v <= hi + 1e-6))[0]
        ia_c, ia_r = idx(xa, x0, x1), idx(ya, y0, y1)
        ib_c, ib_r = idx(xb, x0, x1), idx(yb, y0, y1)
        if len(ia_c) != len(ib_c) or len(ia_r) != len(ib_r):
            raise ValueError("sea difference: grids not aligned on whole pixels")
        if (abs(xa[ia_c[0]] - xb[ib_c[0]]) > 1e-3) or (abs(ya[ia_r[0]] - yb[ib_r[0]]) > 1e-3):
            raise ValueError("sea difference: grids offset by a fraction of a pixel")
        da = da[np.ix_(ia_r, ia_c)]
        db_ = db_[np.ix_(ib_r, ib_c)]
        xa, ya = xa[ia_c], ya[ia_r]
        crop = "cropped to intersection %dx%d (A %s, B %s)" % (da.shape[1], da.shape[0], "see inputs", "see inputs")
    diff = da - db_                     # NaN wherever either input is fill
    valid = np.isfinite(diff)
    if valid.any():
        p2, p50, p98 = [round(float(v), 2) for v in np.percentile(diff[valid], [2, 50, 98])]
        mean = round(float(diff[valid].mean()), 2)
    else:
        p2 = p50 = p98 = mean = None
    lo, hi = DIFF_RANGE
    max_dim = MAX_DIM
    while True:
        img, bounds = warp_to_latlon(diff, xa, ya, epsg_a, max_dim)
        ok = np.isfinite(img)
        rgb = _diverging_rgb((np.nan_to_num(img, nan=0.0) - lo) / (hi - lo))
        a = np.where(ok, 255, 0).astype("uint8")
        im = Image.fromarray(np.dstack([rgb, a]), "RGBA")
        buf = io.BytesIO()
        im.save(buf, format="PNG", optimize=True)
        png = buf.getvalue()
        if len(png) <= max_kb * 1024 or max_dim <= MIN_DIM:
            break
        max_dim = max(MIN_DIM, int(max_dim * 0.8))
    lid = layer["id"]
    with open(os.path.join(out_dir, lid + ".png"), "wb") as fh:
        fh.write(png)
    meta = {
        "layer_id": lid,
        "png": "data/web/%s.png" % lid,
        "bounds": [[round(bounds[0][0], 5), round(bounds[0][1], 5)], [round(bounds[1][0], 5), round(bounds[1][1], 5)]],
        "pol": pol,
        "kind": "difference_db",
        "definition": "VV(after) minus VV(before), dB",
        "ramp_db": [lo, hi],
        "p2": p2, "p50": p50, "p98": p98, "mean": mean,
        "nan_frac": round(1.0 - float(valid.sum()) / float(valid.size), 4),
        "grid_check": crop,
        "after": {"h5": layer["h5_sources"][0], "source_granule": ra.get("source_granule"), "product_status": ra.get("product_status")},
        "before": {"h5": layer["h5_sources"][1], "source_granule": rb.get("source_granule"), "product_status": rb.get("product_status")},
        "note": "difference of two calibrated backscatter images; wind-roughened sea appears brighter",
        "image_px": [int(img.shape[1]), int(img.shape[0])],
        "png_kb": round(len(png) / 1024.0, 1),
        "built_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    with open(os.path.join(out_dir, lid + ".json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=1)
        fh.write("\n")
    return meta


def build_mandal_rank(manifest, out_dir):
    """TODO (phase 2): data/web/mandal_rank.json (same shape as data/processed/mandal_rank.json).

    Zonal statistics of the class maps over data/processed/mandals.geojson polygons: water_pct, water_err,
    crops_pct, crops_err, normal_pct, rank (1..N sorted by water_pct descending). No invented numbers: every
    value must come from the H5 via the class maps.
    """
    raise NotImplementedError("mandal_rank.json: TODO phase 2")


def build_profile(manifest, out_dir):
    """TODO (phase 2): data/web/profile.json, the eye-profile (radial backscatter vs distance from the track).

    points[] of {r_km, db, err} (20+ points) taken from the SEA scene nearest the eye pass, with
    layer_id = the SEA layer used. Error = standard error of the mean over each radial bin.
    """
    raise NotImplementedError("profile.json: TODO phase 2")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--manifest", default=os.path.join(ROOT, "data", "processed", "manifest.json"))
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "web"), help="output directory (default data/web)")
    ap.add_argument("--only", nargs="*", help="build only these layer ids")
    ap.add_argument("--max-kb", type=int, default=600, help="PNG size cap in KB (default 600)")
    args = ap.parse_args()

    with open(args.manifest, encoding="utf-8") as f:
        manifest = json.load(f)
    layers = [l for l in manifest.get("layers", []) if l.get("h5")]
    if args.only:
        layers = [l for l in layers if l["id"] in args.only]

    h5_dir = os.path.join(ROOT, "data", "h5")
    present = sorted(glob.glob(os.path.join(h5_dir, "*.h5")))
    todo = []
    for l in layers:
        p = l["h5"] if os.path.isabs(l["h5"]) else os.path.join(ROOT, l["h5"])
        if os.path.exists(p):
            todo.append((l, p))
        else:
            print("skip  %s: %s not found" % (l["id"], l["h5"]))
    if not todo:
        print("No H5 files to build from (%d layer(s) declare 'h5', %d file(s) in data/h5/). Nothing to do."
              % (len(layers), len(present)))
        return 0

    os.makedirs(args.out, exist_ok=True)
    rows, failed = [], 0
    for l, p in todo:
        try:
            rows.append(build_layer(l, p, args.out, args.max_kb))
        except Exception as exc:  # keep building the others
            failed += 1
            print("FAIL  %s: %s" % (l["id"], exc))

    if rows:
        hdr = "%-34s %-5s %-11s %9s %6s %6s %6s %6s  %s" % ("layer", "pol", "px", "png KB", "p2", "p50", "p98", "nan", "bounds [[S,W],[N,E]]")
        print(hdr)
        print("-" * len(hdr))
        for m in rows:
            b = m["bounds"]
            f = lambda v: "   n/a" if v is None else "%6.1f" % v
            print("%-34s %-5s %-11s %9.1f %s %s %s %6.2f  [[%.4f,%.4f],[%.4f,%.4f]]" % (
                m["layer_id"], m["pol"], "%dx%d" % tuple(m["image_px"]), m["png_kb"], f(m["p2"]), f(m["p50"]), f(m["p98"]),
                m["nan_frac"], b[0][0], b[0][1], b[1][0], b[1][1]))
    print("built %d layer(s), %d failed -> %s" % (len(rows), failed, args.out))
    if not args.only or "nisar_sea_diff_20261027_vs_20261015" in args.only:
        try:
            m = build_sea_difference(manifest, args.out, args.max_kb)
            if m:
                b = m["bounds"]
                print("%-34s %-5s %-11s %9.1f  p2 %.2f p50 %.2f p98 %.2f dB  nan %.2f  [[%.4f,%.4f],[%.4f,%.4f]]  (%s)" % (
                    m["layer_id"], m["pol"], "%dx%d" % tuple(m["image_px"]), m["png_kb"], m["p2"], m["p50"], m["p98"],
                    m["nan_frac"], b[0][0], b[0][1], b[1][0], b[1][1], m["grid_check"]))
        except Exception as exc:
            failed += 1
            print("FAIL  nisar_sea_diff_20261027_vs_20261015: %s" % exc)
    # Class maps, mandal_rank.json and profile.json are still stubs (see functions above).
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
