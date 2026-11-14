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

Derived products (W3-A / W3-H, from the coast and sea H5, see docs/METHODS.md): class maps for EVERY coast date after the baseline ->
data/web/class_{date}_{class}.png and class_stats.json; sea difference maps (every track-48 sea scene vs the calm 15 Oct) ->
data/web/nisar_sea_diff_{date}_vs_{ref}.png; data/processed/mandal_rank.json (with by_date); data/processed/profile.json.
Skip with --no-derived. Every normal build retargets the 3 class layers and the sea difference layer of the manifest at the
newest date (only those layers, only when a field changed); --no-write-manifest turns that off.
Every layer json also carries a dB histogram (hist) and, for coast layers, water_threshold_db.

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


HIST_RANGE = (-35.0, 5.0)   # dB
HIST_BIN = 0.5              # dB


def _hist_counts(db):
    """Counts of finite values of ``db`` in HIST_RANGE with HIST_BIN dB bins (values outside the range are clipped into the end bins)."""
    import numpy as np
    v = db[np.isfinite(db)]
    nb = int(round((HIST_RANGE[1] - HIST_RANGE[0]) / HIST_BIN))
    h, _ = np.histogram(np.clip(v, HIST_RANGE[0], HIST_RANGE[1] - 1e-6), bins=nb, range=HIST_RANGE)
    return [int(c) for c in h], int(v.size)


def _pols_in(h5file):
    import h5py
    with h5py.File(h5file, "r") as f:
        return list(f["backscatter"].keys())


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
    # per-pol dB histogram (PRO review #9): raw 20/100 m pixels; coast layers also the 3x3-smoothed image the water threshold is applied to
    hist = {"range_db": list(HIST_RANGE), "bin_db": HIST_BIN, "bins": len(_hist_counts(np.array([0.0]))[0]), "counts": {}, "n_valid": {}}
    for q in _pols_in(h5file):
        dq = db if q == pol else read_backscatter(h5file, q)[0]
        hist["counts"][q], hist["n_valid"][q] = _hist_counts(dq)
        if role == "COAST" and q in ("HH", "HV"):
            hist.setdefault("counts_smoothed3x3", {})[q] = _hist_counts(_box_db(dq, SMOOTH_PX))[0]
        if dq is not db:
            del dq
    meta["hist"] = hist
    with open(os.path.join(out_dir, lid + ".json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=1)
        fh.write("\n")
    return meta


DIFF_RANGE = (-15.0, 15.0)   # dB, diverging stretch of the sea difference map
# Colour-blind-safe diverging ramp (blue - white - orange; no red/green pair; lightness is highest at 0). The same stops
# are written into the json so the UI can draw the legend.
DIFF_STOPS = [(-15.0, "#1D4E89", "much darker (smoother sea)"), (-7.5, "#6BAED6", None), (0.0, "#F7F7F7", "no change"),
              (7.5, "#F6A04D", None), (15.0, "#B54708", "much brighter (rougher sea)")]


def _hex_rgb(h):
    return [int(h[i:i + 2], 16) for i in (1, 3, 5)]


def _diverging_rgb(t):
    """t in 0..1 (0 = most negative, 0.5 = no change, 1 = most positive) -> uint8 RGB along DIFF_STOPS (piecewise linear)."""
    import numpy as np
    lo, hi = DIFF_RANGE
    v = np.clip(t, 0.0, 1.0) * (hi - lo) + lo
    xs = [s[0] for s in DIFF_STOPS]
    chans = [np.interp(v, xs, [_hex_rgb(s[1])[c] for s in DIFF_STOPS]) for c in range(3)]
    return np.rint(np.stack(chans, axis=-1)).astype("uint8")


def _ramp_json():
    return {"name": "blue-white-orange (colour-blind safe)", "kind": "diverging", "unit": "dB", "colour_blind_safe": True,
            "stops": [{"value": s[0], "hex": s[1], "label": s[2]} for s in DIFF_STOPS],
            "note": "negative = sea darker than the calm reference, positive = brighter (rougher); grey-white = no change"}


def _sea_diff_one(pa, pb, pol, lid, max_kb, bound_ref):
    """VV(after) minus VV(before) in dB on the common grid -> data/web/{lid}.png + .json. ``bound_ref`` = (after_h5, before_h5)
    repo-relative strings. If the grids differ the arrays are cropped to the intersection (whole-pixel offsets only)."""
    import numpy as np
    from PIL import Image
    out_dir = bound_ref[2]
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
        crop = "cropped to intersection %dx%d" % (da.shape[1], da.shape[0])
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
        "ramp": _ramp_json(),
        "p2": p2, "p50": p50, "p98": p98, "mean": mean,
        "nan_frac": round(1.0 - float(valid.sum()) / float(valid.size), 4),
        "grid_check": crop,
        "after": {"h5": bound_ref[0], "source_granule": ra.get("source_granule"), "product_status": ra.get("product_status"),
                  "date": str(ra.get("start_utc", ""))[:10], "start_utc": ra.get("start_utc")},
        "before": {"h5": bound_ref[1], "source_granule": rb.get("source_granule"), "product_status": rb.get("product_status"),
                   "date": str(rb.get("start_utc", ""))[:10], "start_utc": rb.get("start_utc")},
        "note": "difference of two calibrated backscatter images; wind-roughened sea appears brighter",
        "image_px": [int(img.shape[1]), int(img.shape[0])],
        "png_kb": round(len(png) / 1024.0, 1),
        "built_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    with open(os.path.join(out_dir, lid + ".json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=1)
        fh.write("\n")
    return meta


def build_sea_difference(manifest, out_dir, max_kb=600):
    """Sea difference maps: VV(scene) minus VV(calm reference), Track 48, for EVERY sea scene of that track newer than the
    reference. The reference is the second ``h5_sources`` entry of the layer nisar_sea_diff_* (the calm 15 Oct scene) and never
    moves. Writes data/web/nisar_sea_diff_{date}_vs_{refdate}.png/.json (blue-white-orange colour-blind-safe ramp, stops in
    the json). Returns the list of metas, oldest to newest (the last one is what the manifest layer points at)."""
    layer = next((l for l in manifest.get("layers", []) if l["id"].startswith("nisar_sea_diff") and l.get("h5_sources")), None)
    if not layer:
        print("skip  sea difference: no nisar_sea_diff layer with h5_sources")
        return []
    ref_rel = layer["h5_sources"][1]
    pb = os.path.join(ROOT, ref_rel)
    if not os.path.exists(pb):
        print("skip  sea difference: reference H5 missing")
        return []
    pol = layer.get("pol", "VV")
    ref_layer = next((l for l in manifest["layers"] if l.get("h5") == ref_rel), {})
    ref_date = _compact(ref_layer.get("date") or layer["h5_sources"][1].split("_")[2])
    track = ref_layer.get("track", layer.get("track"))
    cands = sorted((l for l in manifest["layers"] if l.get("id", "").startswith("nisar_l_sea_") and l.get("h5")
                    and l.get("track") == track and l.get("pol") == pol and _compact(l["date"]) > ref_date
                    and os.path.exists(os.path.join(ROOT, l["h5"]))), key=lambda l: l["date"])
    metas = []
    for l in cands:
        lid = "nisar_sea_diff_%s_vs_%s" % (_compact(l["date"]), ref_date)
        try:
            metas.append(_sea_diff_one(os.path.join(ROOT, l["h5"]), pb, pol, lid, max_kb, (l["h5"], ref_rel, out_dir)))
        except Exception as exc:
            print("FAIL  %s: %s" % (lid, exc))
    return metas


def update_sea_diff_manifest(manifest_path, metas):
    """Point the sea difference layer at the NEWEST difference map (png, bounds, date, time_utc, h5_sources, name, shows, ramp).
    Touches only that layer; writes nothing if nothing changed. Returns the changed fields."""
    if not metas:
        return []
    with open(manifest_path, encoding="utf-8") as fh:
        m = json.load(fh)
    meta = metas[-1]
    layer = next((l for l in m["layers"] if l["id"].startswith("nisar_sea_diff")), None)
    if not layer:
        return []
    ad, bd = meta["after"]["date"], meta["before"]["date"]
    new = {
        "png": meta["png"], "bounds": meta["bounds"], "bounds_inferred": False,
        "date": ad, "time_utc": meta["after"]["start_utc"], "diff_date": ad, "diff_reference_date": bd,
        "diff_dates": [x["after"]["date"] for x in metas],
        "h5_sources": [meta["after"]["h5"], meta["before"]["h5"]],
        "name": "Sea roughness change (%s minus calm %s)" % (_human_date(ad), _human_date(bd)),
        "shows": "Change in sea-surface radar brightness, %s minus calm day %s (dB); difference of two calibrated backscatter images; wind-roughened sea appears brighter" % (_human_date(ad), _human_date(bd)),
        "ramp": meta["ramp"],
        "bounds_source": "H5 subset footprint (data/web/%s.json, built by tools/build_web.py)" % meta["layer_id"],
    }
    changed = []
    for k, v in new.items():
        if layer.get(k) != v:
            layer[k] = v
            changed.append("%s.%s" % (layer["id"], k))
    if changed:
        tmp = manifest_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(m, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        os.replace(tmp, manifest_path)
    return changed


# ----------------------------------------------------------------------------------------------------------
# Derived products (W3-A): class maps, mandal_rank.json, profile.json. All numbers come from data/h5/.
# Method, thresholds and limits are written up in docs/METHODS.md. numpy + PIL + pyproj only.
# ----------------------------------------------------------------------------------------------------------

CLASS_CODES = {"invalid": 0, "no_change": 1, "new_water": 2, "wet_crops": 3, "permanent_water": 4}
CLASS_RGBA = {"new_water": (0x2A, 0x6F, 0xB0, 255), "wet_crops": (0xE0, 0x9A, 0x2B, 255), "no_change": (200, 205, 210, 40)}
SMOOTH_PX = 3            # boxcar (linear power) before classifying: 3x3 px = 60 m, tames 20 m speckle
EDGE_PX = 2              # pixels dropped next to no-data / swath edge
K_SIGMA = 3.0            # change threshold in robust sigmas of the 4->16 Oct "normal fortnight" difference
K_ERR = 1.0              # error = largest share shift when K_SIGMA moves by +/- K_ERR
HV_CROPS_SIGMA = 1.0     # wet crops also need HV to rise by this many sigmas
CLASS_MAX_DIM = 3000     # longest side of class PNGs, px
MIN_COVERAGE_PCT = 50.0  # mandal rank: valid land coverage needed
MIN_BOX_FRAC = 0.5       # mandal rank: share of the mandal inside the coast footprint
MIN_VALID_PX = 1250      # mandal rank: valid 20 m pixels needed (= 200 px of the old 50 m grid)
PROFILE_LAYER_ID = "nisar_l_sea_20261027_t48_vv"
EYE_SIGMA_KM = 5.0       # Gaussian smoothing for the eye search
EYE_SIGMA_VARIANTS_KM = (3.0, 4.0, 5.0, 6.0, 8.0)
EYE_MIN_WINDOW_KM = 10.0 # a local minimum must be the lowest value within this radius
EYE_INTERIOR_KM = 30.0   # eye candidate must be this far from any no-data cell and from land
EYE_SEARCH_KM = 150.0    # storm area: within this distance of the IMD fix at acquisition time
_DERIVED = {}

NOW = lambda: datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path):
    return os.path.relpath(path, ROOT) if path.startswith(ROOT) else path


def _compact(d):
    return d.replace("-", "")


def _read_mask(h5file):
    import h5py
    with h5py.File(h5file, "r") as f:
        return f["aux/mask"][...] if "aux" in f and "mask" in f["aux"] else None


def _shift_sum(a, r):
    """Sum of a over the (2r+1)^2 neighbourhood (zero padded). a: 2-D array."""
    import numpy as np
    h, w = a.shape
    p = np.pad(a, r)
    acc = np.zeros(a.shape, dtype=a.dtype)
    for i in range(2 * r + 1):
        for j in range(2 * r + 1):
            acc += p[i:i + h, j:j + w]
    return acc


def _box_db(db, n):
    """NaN-aware n x n mean in LINEAR power, returned in dB (NaN where the centre pixel is NaN or <half the window is valid)."""
    import numpy as np
    valid = np.isfinite(db)
    z = np.where(valid, np.power(10.0, db / 10.0, dtype="float32"), np.float32(0)).astype("float32")
    s = _shift_sum(z, n // 2)
    c = _shift_sum(valid.astype("uint8"), n // 2)
    del z
    good = valid & (c >= (n * n + 1) // 2)
    out = np.full(db.shape, np.nan, dtype="float32")
    out[good] = 10.0 * np.log10(s[good] / c[good].astype("float32"))
    return out


def _erode(mask, r):
    """Square binary erosion by r pixels (True stays only if the whole (2r+1)^2 window is True; outside = False)."""
    import numpy as np
    h, w = mask.shape
    p = np.pad(mask, r, constant_values=False)
    out = np.ones(mask.shape, dtype=bool)
    # separable: rows then columns
    tmp = np.ones((h + 2 * r, w), dtype=bool)
    for j in range(2 * r + 1):
        tmp &= p[:, j:j + w]
    for i in range(2 * r + 1):
        out &= tmp[i:i + h, :]
    return out


def _otsu(vals, lo, hi, step=0.1):
    """Otsu threshold of ``vals`` using a histogram on [lo, hi). Returns (threshold, centres, counts)."""
    import numpy as np
    nb = int(round((hi - lo) / step))
    h, e = np.histogram(vals, bins=nb, range=(lo, hi))
    c = (e[:-1] + e[1:]) / 2.0
    hf = h.astype("float64")
    w0 = np.cumsum(hf)
    w1 = w0[-1] - w0
    s0 = np.cumsum(hf * c)
    m0 = s0 / np.maximum(w0, 1)
    m1 = (s0[-1] - s0) / np.maximum(w1, 1)
    var = w0 * w1 * (m0 - m1) ** 2
    k = int(np.argmax(var))
    return float(e[k + 1]), c, h


def _hist_valley(c, h):
    """dB of the histogram minimum between the two highest peaks (5-bin smoothed), a cross-check for Otsu."""
    import numpy as np
    k = np.ones(21) / 21.0
    hs = np.convolve(h.astype("float64"), k, mode="same")
    p1 = int(np.argmax(hs))
    far = np.abs(np.arange(len(hs)) - p1) > 40
    p2 = int(np.argmax(np.where(far, hs, -1)))
    a, b = sorted((p1, p2))
    return float(c[a + int(np.argmin(hs[a:b + 1]))]), float(c[a]), float(c[b])


def _robust(d):
    import numpy as np
    med = float(np.median(d))
    return med, float(1.4826 * np.median(np.abs(d - med)))


def _iso(d):
    """20261109 -> 2026-11-09"""
    return "%s-%s-%s" % (d[:4], d[4:6], d[6:])


def _catalog_by_file():
    """{repo-relative h5 path: catalog entry} (empty if there is no catalog)."""
    p = os.path.join(ROOT, "data", "h5", "catalog.json")
    if not os.path.exists(p):
        return {}
    with open(p, encoding="utf-8") as fh:
        return {s["file"]: s for s in json.load(fh).get("scenes", [])}


def _coast_sources(manifest):
    """(pre, events, by_date): pre = the two baseline dates (analysis normal_period, yyyymmdd), events = EVERY coast
    scene of the baseline track newer than the baseline (sorted, yyyymmdd; this is what makes a new scene show up
    without any code change), by_date = {yyyymmdd: absolute h5 path}."""
    an = manifest["analyses"][0]
    pre = [_compact(d) for d in an["normal_period"]]
    by_date, track = {}, {}
    for l in manifest["layers"]:
        if l.get("id", "").startswith("nisar_l_coast_") and l.get("h5") and os.path.exists(os.path.join(ROOT, l["h5"])):
            dd = _compact(l["date"])
            by_date[dd] = os.path.join(ROOT, l["h5"])
            track[dd] = l.get("track")
    for d in pre:
        if d not in by_date:
            raise FileNotFoundError("coast H5 for baseline %s not found (layers with h5: %s)" % (d, sorted(by_date)))
    events = sorted(d for d in by_date if d > pre[1] and track.get(d) == track.get(pre[1]))
    if not events:
        raise FileNotFoundError("no coast scene newer than the baseline %s" % pre[1])
    return pre, events, by_date


def compute_coast_classes(manifest):
    """Class arrays on the coast 20 m grid for EVERY coast scene after the baseline. Cached for the process.
    See docs/METHODS.md. Baseline-derived quantities (valid mask, water threshold, permanent water, noise sigma) use the
    two baseline scenes only, so a new scene never changes the numbers of an older date."""
    import numpy as np
    if "classes" in _DERIVED:
        return _DERIVED["classes"]
    pre, events_all, by_date = _coast_sources(manifest)
    cat = _catalog_by_file()
    S, scene = {}, {}
    st = {"grid": None}

    def load(d):
        """smoothed HH, HV (dB) of one date + its valid mask; (None, None) if the grid differs from the baseline grid"""
        out, ok = {}, None
        for pol in ("HH", "HV"):
            db, x, y, epsg, root = read_backscatter(by_date[d], pol)
            if st["grid"] is None:
                st["grid"] = (x, y, epsg)
            else:
                g = st["grid"]
                if db.shape != g[1].shape + g[0].shape or not (np.array_equal(x, g[0]) and np.array_equal(y, g[1]) and epsg == g[2]):
                    print("WARN  coast grid of %s differs from the baseline grid: skipped for class maps" % d)
                    return None, None
            out[pol] = _box_db(db, SMOOTH_PX)
            del db
            ok = np.isfinite(out[pol]) if ok is None else ok & np.isfinite(out[pol])
        m = _read_mask(by_date[d])
        if m is not None:
            ok &= (m == 1)
        rel = _rel(by_date[d])
        scene[d] = {"scene_id": root.get("scene_id"), "product_status": root.get("product_status"), "start_utc": root.get("start_utc"),
                    "track": int(root.get("track", 0)), "h5": rel, "cataloged_utc": (cat.get(rel) or {}).get("cataloged_utc")}
        return out, ok

    ok_base = None
    for d in pre:
        o, ok = load(d)
        if o is None:
            raise ValueError("baseline grids differ")
        S[(d, "HH")], S[(d, "HV")] = o["HH"], o["HV"]
        ok_base = ok if ok_base is None else ok_base & ok
    valid = _erode(ok_base, EDGE_PX)
    del ok_base
    grid = st["grid"]
    x, y, epsg = grid
    px_km2 = abs(float(x[1] - x[0]) * float(y[1] - y[0])) / 1e6

    # water threshold: Otsu on the pooled baseline HH histogram (smoothed dB, valid pixels)
    pool = np.concatenate([S[(pre[0], "HH")][valid], S[(pre[1], "HH")][valid]])
    T, c, h = _otsu(pool, -40.0, 10.0, 0.1)
    valley, pk1, pk2 = _hist_valley(c, h)
    del pool
    perm = valid & (S[(pre[0], "HH")] < T) & (S[(pre[1], "HH")] < T)
    land = valid & ~perm

    # noise of the change measure from the normal fortnight (4 vs 16 Oct), robust (MAD) sigma and median offset
    d_hh = (S[(pre[1], "HH")] - S[(pre[0], "HH")])[land]
    d_hv = (S[(pre[1], "HV")] - S[(pre[0], "HV")])[land]
    med_hh, sig_hh = _robust(d_hh)
    med_hv, sig_hv = _robust(d_hv)
    del d_hh, d_hv

    def lin_mean_db(a, b):
        return (10.0 * np.log10(0.5 * (np.power(10.0, a / 10.0, dtype="float32") + np.power(10.0, b / 10.0, dtype="float32")))).astype("float32")
    base_hh = lin_mean_db(S[(pre[0], "HH")], S[(pre[1], "HH")])
    base_hv = lin_mean_db(S[(pre[0], "HV")], S[(pre[1], "HV")])

    def classify(ev_hh, ev_hv, b_hh, b_hv, k, thr=T, perm_=perm, land_=land):
        dh = ev_hh - b_hh - np.float32(med_hh)
        dv = ev_hv - b_hv - np.float32(med_hv)
        with np.errstate(invalid="ignore"):
            water = land_ & (b_hh >= thr) & (ev_hh < thr) & (dh <= -k * sig_hh) & (dv <= -k * sig_hv)
            crops = land_ & ~water & (ev_hh >= thr) & (dh >= k * sig_hh) & (dv >= HV_CROPS_SIGMA * sig_hv)
        cls = np.zeros(land_.shape, dtype="uint8")
        cls[land_] = CLASS_CODES["no_change"]
        cls[water] = CLASS_CODES["new_water"]
        cls[crops] = CLASS_CODES["wet_crops"]
        cls[perm_] = CLASS_CODES["permanent_water"]
        return cls

    ks = (K_SIGMA - K_ERR, K_SIGMA, K_SIGMA + K_ERR)
    cls, sens, shifts, events = {}, {}, {}, []
    perm_v = valid & (S[(pre[0], "HH")] < valley) & (S[(pre[1], "HH")] < valley)
    land_v = valid & ~perm_v

    def sens_of(a):
        lp = max(int(((a > 0) & (a != 4)).sum()), 1)
        return {"threshold_hh_db": round(valley, 2), "new_water_km2": round(float((a == 2).sum()) * px_km2, 2),
                "wet_crops_km2": round(float((a == 3).sum()) * px_km2, 2), "new_water_pct_of_land": round(100.0 * float((a == 2).sum()) / lp, 3),
                "wet_crops_pct_of_land": round(100.0 * float((a == 3).sum()) / lp, 3), "permanent_water_km2": round(float((a == 4).sum()) * px_km2, 1)}

    for d in events_all:                      # one event date at a time: memory stays at "baseline + one date"
        o, ok = load(d)
        if o is None:
            continue
        valid_d = valid & _erode(ok, EDGE_PX)
        del ok
        land_d, perm_d = land & valid_d, perm & valid_d
        for k in ks:
            cls[(d, k)] = classify(o["HH"], o["HV"], base_hh, base_hv, k, T, perm_d, land_d)
        sens[d] = sens_of(classify(o["HH"], o["HV"], base_hh, base_hv, K_SIGMA, valley, perm_v & valid_d, land_v & valid_d))
        shifts[d] = {"median_dHH_vs_baseline_db": round(float(np.median((o["HH"] - base_hh)[land_d])), 2),
                     "median_dHV_vs_baseline_db": round(float(np.median((o["HV"] - base_hv)[land_d])), 2)}
        events.append(d)
        del o, valid_d, land_d, perm_d
    if not events:
        raise ValueError("no coast scene on the baseline grid after the baseline")
    # control: normal fortnight with the same rules (16 Oct against 4 Oct only)
    for k in ks:
        cls[("normal", k)] = classify(S[(pre[1], "HH")], S[(pre[1], "HV")], S[(pre[0], "HH")], S[(pre[0], "HV")], k)
    sens["normal"] = sens_of(classify(S[(pre[1], "HH")], S[(pre[1], "HV")], S[(pre[0], "HH")], S[(pre[0], "HV")], K_SIGMA, valley, perm_v, land_v))

    def count(a):
        return {"valid_px": int((a > 0).sum()), "land_px": int(((a > 0) & (a != 4)).sum()),
                "permanent_water_px": int((a == 4).sum()), "new_water_px": int((a == 2).sum()),
                "wet_crops_px": int((a == 3).sum()), "no_change_px": int((a == 1).sum())}
    stats = {}
    for key, a in cls.items():
        cnt = count(a)
        for nm in ("new_water", "wet_crops", "no_change", "permanent_water"):
            cnt[nm + "_km2"] = round(cnt[nm + "_px"] * px_km2, 3)
        lp = max(cnt["land_px"], 1)
        for nm in ("new_water", "wet_crops", "no_change"):
            cnt[nm + "_pct_of_land"] = round(100.0 * cnt[nm + "_px"] / lp, 3)
        cnt["valid_km2"] = round(cnt["valid_px"] * px_km2, 1)
        stats["%s|k=%.1f" % (key[0], key[1])] = cnt
    res = {
        "pre": pre, "events": events, "by_date": by_date, "grid": grid, "px_km2": px_km2, "valid": valid, "perm": perm,
        "cls": cls, "ks": ks, "stats": stats, "shifts": shifts, "sens": sens, "scene": scene,
        "thresholds": {"water_hh_db": round(T, 2), "otsu_hh_db": round(T, 2), "histogram_valley_hh_db": round(valley, 2),
                       "histogram_modes_hh_db": [round(pk1, 1), round(pk2, 1)],
                       "k_sigma": K_SIGMA, "hv_crops_sigma": HV_CROPS_SIGMA,
                       "sigma_hh_db": round(sig_hh, 3), "sigma_hv_db": round(sig_hv, 3),
                       "normal_median_hh_db": round(med_hh, 3), "normal_median_hv_db": round(med_hv, 3),
                       "change_hh_db": round(K_SIGMA * sig_hh, 2), "change_hv_db": round(K_SIGMA * sig_hv, 2),
                       "crops_hv_rise_db": round(HV_CROPS_SIGMA * sig_hv, 2)},
        "smooth_px": SMOOTH_PX, "edge_px": EDGE_PX,
    }
    _DERIVED["classes"] = res
    return res


def _png_rgba(codes_img, which):
    import numpy as np
    from PIL import Image
    codes = np.nan_to_num(codes_img, nan=0).astype("uint8")
    sel = codes == CLASS_CODES[which]
    rgba = np.zeros(codes.shape + (4,), dtype="uint8")
    rgba[sel] = CLASS_RGBA[which]
    buf = io.BytesIO()
    Image.fromarray(rgba, "RGBA").save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def build_class_maps(manifest, out_dir):
    """Class maps (new open water, wet or flooded crops, no change) for EVERY coast date after the baseline, on the
    coast 20 m grid. Writes data/web/class_{yyyymmdd}_{new_water|wet_crops|no_change}.png (RGBA, lat/lon, same bounds as
    the coast PNGs) and data/web/class_stats.json (``latest_date`` = newest). Returns the computed result dict."""
    import numpy as np
    r = compute_coast_classes(manifest)
    x, y, epsg = r["grid"]
    os.makedirs(out_dir, exist_ok=True)
    files, bounds, image_px = {}, None, None
    for d in r["events"]:
        codes = r["cls"][(d, K_SIGMA)].astype("float32")
        codes[codes == 0] = np.nan
        img, bounds = warp_to_latlon(codes, x, y, epsg, CLASS_MAX_DIM)
        del codes
        for which in ("new_water", "wet_crops", "no_change"):
            png = _png_rgba(img, which)
            name = "class_%s_%s.png" % (d, which)
            with open(os.path.join(out_dir, name), "wb") as fh:
                fh.write(png)
            files["%s/%s" % (d, which)] = {"png": "data/web/" + name, "png_kb": round(len(png) / 1024.0, 1)}
        image_px = [int(img.shape[1]), int(img.shape[0])]
        del img
    bnd = [[round(bounds[0][0], 5), round(bounds[0][1], 5)], [round(bounds[1][0], 5), round(bounds[1][1], 5)]]
    sources = {d: _rel(r["by_date"][d]) for d in r["pre"] + r["events"]}
    out = {
        "schema": "spacebros-class-stats-v1",
        "created_utc": NOW(),
        "analysis_id": manifest["analyses"][0]["id"],
        "baseline_dates": r["pre"], "event_dates": r["events"], "latest_date": r["events"][-1],
        "scenes": {_iso(d): r["scene"][d] for d in r["pre"] + r["events"] if d in r["scene"]},
        "h5_sources": sources,
        "grid": {"epsg": epsg, "posting_m": abs(float(x[1] - x[0])), "shape": [int(len(y)), int(len(x))],
                 "pixel_km2": r["px_km2"], "png_bounds_latlon": bnd, "png_px": image_px},
        "method": {"smoothing": "%dx%d boxcar in linear power before classifying" % (r["smooth_px"], r["smooth_px"]),
                   "edge_buffer_px": r["edge_px"], "valid": "baseline: finite HH and HV on both baseline dates and aux/mask == 1; each event date: the same on that date",
                   "baseline": "mean of the two pre-event dates in linear power",
                   "permanent_water": "smoothed HH below the water threshold on BOTH baseline dates (excluded from all shares)",
                   "new_water": "baseline HH >= T, event HH < T, HH and HV both fall by >= k sigma (after removing the normal-fortnight median)",
                   "wet_crops": "not new water, event HH >= T, HH rises >= k sigma and HV rises >= %.1f sigma" % HV_CROPS_SIGMA,
                   "no_change": "every other valid land pixel", "sigma_source": "robust (MAD) sigma of the 4 to 16 Oct difference over land",
                   "error": "shares recomputed at k = %s sigma; error = largest shift from the k = %.1f result" % (", ".join("%.1f" % k for k in r["ks"]), K_SIGMA)},
        "thresholds": r["thresholds"],
        "event_median_shifts_vs_baseline": r["shifts"],
        "sensitivity_to_water_threshold": r["sens"],
        "classes": r["stats"],
        "files": files,
    }
    with open(os.path.join(out_dir, "class_stats.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
        fh.write("\n")
    r["files"], r["bounds"], r["image_px"] = files, bnd, image_px
    return r


def _human_date(iso):
    dt_ = datetime.date.fromisoformat(iso)
    return "%d %s" % (dt_.day, dt_.strftime("%b"))


def _join_and(parts):
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]


def _date_span(a, b):
    """'4-16 Oct' (same month) or '28 Oct-9 Nov'"""
    da, db_ = datetime.date.fromisoformat(_iso(a)), datetime.date.fromisoformat(_iso(b))
    return "%d-%d %s" % (da.day, db_.day, db_.strftime("%b")) if da.month == db_.month else "%s-%s" % (_human_date(_iso(a)), _human_date(_iso(b)))


def _date_pair(a, b):
    """'4 and 16 Oct' (same month) or '4 Oct and 9 Nov'"""
    da, db_ = datetime.date.fromisoformat(_iso(a)), datetime.date.fromisoformat(_iso(b))
    return "%d and %d %s" % (da.day, db_.day, db_.strftime("%b")) if da.month == db_.month else "%s and %s" % (_human_date(_iso(a)), _human_date(_iso(b)))


def _event_confounders(iso_date):
    """Confounder entries of every active event file (data/events/*.json) whose ``affects_dates`` list this scene date:
    [{"event", "name", "text", "limit_text"}, ...]."""
    out = []
    for p in sorted(glob.glob(os.path.join(ROOT, "data", "events", "*.json"))):
        try:
            with open(p, encoding="utf-8") as fh:
                ev = json.load(fh)
        except (OSError, ValueError):
            continue
        if ev.get("status") not in ("active", "recovering"):
            continue
        for c in ev.get("confounders") or []:
            if iso_date in (c.get("affects_dates") or []):
                out.append({"event": ev.get("name") or ev.get("id"), "name": c.get("name"), "text": c.get("text"),
                            "limit_text": c.get("limit_text") or c.get("name")})
    return out


def update_class_manifest(manifest_path, r):
    """Point the three class layers at the NEWEST coast date (png, bounds, date, class_date, period, h5_sources, limit text...).
    Read-modify-write that touches ONLY those three layer entries, and writes nothing when nothing changed. Runs in every
    normal build (also in CI), not only with --write-manifest. Returns the list of changed fields."""
    with open(manifest_path, encoding="utf-8") as fh:
        m = json.load(fh)
    d = r["events"][-1]
    iso = _iso(d)
    s = r["stats"]["%s|k=%.1f" % (d, K_SIGMA)]
    n = r["stats"]["normal|k=%.1f" % K_SIGMA]
    srcs = [_rel(r["by_date"][q]) for q in r["pre"] + r["events"]]
    conf = _event_confounders(iso)
    water_lim = "water under dense crops (it can be missed); wind-roughened water can look bright"
    if conf:
        water_lim += "; %s also reflects %s, not %s alone" % (_human_date(iso), " and ".join(c["limit_text"] for c in conf), conf[0]["event"].replace("Cyclone ", ""))
    crops_lim = ("water under dense crops; a normal fortnight (%s) already flags %.1f%% of land by the same rule, against %s, so this class is "
                 "not clearly above normal field change and is not proven flooding"
                 % (_date_span(r["pre"][0], r["pre"][1]), n["wet_crops_pct_of_land"],
                    _join_and(["%.1f%% on %s" % (r["stats"]["%s|k=%.1f" % (q, K_SIGMA)]["wet_crops_pct_of_land"], _human_date(_iso(q))) for q in r["events"]])))
    limits = {"nisar_class_new_water": water_lim, "nisar_class_wet_crops": crops_lim,
              "nisar_class_no_change": "small changes (it is a threshold, not a measurement)"}
    prov = [q for q in r["pre"] if (r["scene"].get(q) or {}).get("product_status") != "VALIDATED"]
    processing = ("single-band L (HH+HV); baseline %s are %s products; thresholds in data/web/class_stats.json and docs/METHODS.md"
                  % (_date_pair(r["pre"][0], r["pre"][1]), "PROVISIONAL" if prov else "VALIDATED"))
    changed = []
    for l in m["layers"]:
        if l["id"] in limits:
            which = l["id"].replace("nisar_class_", "")
            new = {
                "png": r["files"]["%s/%s" % (d, which)]["png"], "bounds": r["bounds"], "bounds_inferred": False,
                "bounds_source": "class grid warped to lat/lon from the NISAR T55 F10 H5 subsets (tools/build_web.py)",
                "status": "ready", "placeholder": None, "h5_sources": srcs, "limit": limits[l["id"]], "processing": processing,
                "date": iso, "class_date": iso, "period": [_iso(r["pre"][1]), iso],
            }
            for k, v in new.items():
                if l.get(k) != v:
                    l[k] = v
                    changed.append("%s.%s" % (l["id"], k))
    if changed:
        tmp = manifest_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(m, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        os.replace(tmp, manifest_path)
    return changed


def patch_water_threshold(out_dir, manifest, r):
    """Write the HH water threshold into every coast layer json (data/web/{layer}.json): the line the UI draws on the histogram."""
    T = r["thresholds"]["water_hh_db"]
    n = 0
    for l in manifest.get("layers", []):
        if l.get("id", "").startswith("nisar_l_coast_") and l.get("h5"):
            p = os.path.join(out_dir, l["id"] + ".json")
            if not os.path.exists(p):
                continue
            with open(p, encoding="utf-8") as fh:
                meta = json.load(fh)
            meta["water_threshold_db"] = {"pol": "HH", "value": T, "applies_to": "3x3-smoothed HH (hist.counts_smoothed3x3.HH)",
                                          "definition": "Otsu threshold of the pooled baseline HH histogram; HH below it = open water", "source": "data/web/class_stats.json"}
            with open(p, "w", encoding="utf-8") as fh:
                json.dump(meta, fh, indent=1)
                fh.write("\n")
            n += 1
    return n


def _polys(g):
    t = g["type"]
    if t == "Polygon":
        yield g["coordinates"]
    elif t == "MultiPolygon":
        for p in g["coordinates"]:
            yield p
    elif t == "GeometryCollection":
        for q in g["geometries"]:
            for p in _polys(q):
                yield p


def _district_table():
    import csv
    p = os.path.join(ROOT, "data", "interim", "C", "mandal_district_2022_complete.csv")
    if not os.path.exists(p):
        return {}
    with open(p, encoding="utf-8") as fh:
        return {r["shapeID"]: (r.get("district_2022") or None) for r in csv.DictReader(fh)}


def _provenance(r, what):
    return {
        "created_utc": NOW(), "tool": "tools/build_web.py (%s)" % what, "h5_sources": {d: _rel(r["by_date"][d]) for d in r["pre"] + r["events"]},
        "baseline_dates": r["pre"], "event_dates": r["events"],
        "method": ("L-band HH+HV on the 20 m coast grid; %dx%d boxcar in linear power; baseline = mean of the two pre-event dates; "
                   "permanent water = HH below the water threshold on both baseline dates (excluded); new water = HH and HV both fall by >= %.0f sigma and HH ends below the threshold; "
                   "wet crops = HH rises >= %.0f sigma and HV >= %.0f sigma and not water; shares are of valid, non-permanent-water land pixels inside each mandal polygon. See docs/METHODS.md."
                   % (r["smooth_px"], r["smooth_px"], K_SIGMA, K_SIGMA, HV_CROPS_SIGMA)),
        "thresholds": r["thresholds"],
        "caveats": ["single band (L); S-band not used yet", "baseline scenes 4 and 16 Oct are PROVISIONAL products",
                    "no ground truth: classes are radar-only and not validated against a flood map",
                    "speckle: 20 m pixels are noisy, errors show the effect of moving the threshold by one sigma only",
                    "9 Nov also reflects Cyclone Murasu (1-3 Nov) and the Godavari peak, not Arnab alone"],
    }


def build_mandal_rank(manifest, out_dir, r=None):
    """data/processed/mandal_rank.json: share of valid land pixels of each class inside each mandal polygon, for EVERY coast
    date after the baseline.

    Top level (kept for the dashboard): ``rows`` / ``flagged_not_ranked`` = the NEWEST date, plus ``oct28`` (the landfall-day
    scene) on every row. Added: ``by_date`` {iso date: {rows: [all mandals with a district, ranked or flagged]}}, per row
    water_pct, crops_pct, err (= water_err), total_pct, coverage_pct, area_km2, water_km2, flooded_km2 (= water + crops),
    change_vs_normal_pp, rank (by total likely flooded) and rank_water (by new open water). Needs compute_coast_classes (cached).
    """
    import numpy as np
    from PIL import Image, ImageDraw
    from pyproj import Transformer
    r = r or compute_coast_classes(manifest)
    x, y, epsg = r["grid"]
    nrow, ncol = len(y), len(x)
    dx, dy = float(x[1] - x[0]), float(y[1] - y[0])
    tf = Transformer.from_crs(4326, epsg, always_xy=True)
    with open(os.path.join(ROOT, "data", "processed", "mandals.geojson"), encoding="utf-8") as fh:
        gj = json.load(fh)
    dist = _district_table()
    feats = []
    for ft in gj["features"]:
        rings = []
        for poly in _polys(ft["geometry"]):
            rr = []
            for ring in poly:
                X, Y = tf.transform([q[0] for q in ring], [q[1] for q in ring])
                rr.append(list(zip(X, Y)))
            rings.append(rr)
        feats.append((ft["properties"], rings))
    # label raster on the class grid (mode I, 32-bit) and polygon share inside the footprint (coarse, 200 m canvas)
    lab = Image.new("I", (ncol, nrow), 0)
    dr = ImageDraw.Draw(lab)
    x_lo, x_hi = float(x[0]) - abs(dx) / 2, float(x[-1]) + abs(dx) / 2
    y_hi, y_lo = float(y[0]) + abs(dy) / 2, float(y[-1]) - abs(dy) / 2
    frac_box = []
    for i, (pr, rings) in enumerate(feats):
        allp = [p for rr in rings for ring in rr for p in ring]
        for rr in rings:
            for k, ring in enumerate(rr):
                dr.polygon([((px - x[0]) / dx, (py - y[0]) / dy) for px, py in ring], fill=(i + 1) if k == 0 else 0)
        xs, ys = [p[0] for p in allp], [p[1] for p in allp]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        cs = 200.0
        w, h = max(1, int(np.ceil((x1 - x0) / cs))), max(1, int(np.ceil((y1 - y0) / cs)))
        im = Image.new("L", (w, h), 0)
        d2 = ImageDraw.Draw(im)
        for rr in rings:
            for k, ring in enumerate(rr):
                d2.polygon([((px - x0) / cs, (y1 - py) / cs) for px, py in ring], fill=255 if k == 0 else 0)
        m = np.array(im) > 0
        cx = x0 + (np.arange(w) + 0.5) * cs
        cy = y1 - (np.arange(h) + 0.5) * cs
        ins = ((cx >= x_lo) & (cx <= x_hi))[None, :] & ((cy >= y_lo) & (cy <= y_hi))[:, None]
        frac_box.append(float((m & ins).sum()) / max(1, int(m.sum())))
    ids = np.array(lab).ravel()
    del lab
    n = len(feats) + 1

    def tally(a):
        c = {}
        flat = a.ravel()
        for code in (1, 2, 3, 4):
            c[code] = np.bincount(ids[flat == code], minlength=n)
        return c
    poly_px = np.bincount(ids, minlength=n)
    ks = r["ks"]
    kc = ks.index(K_SIGMA)
    events = r["events"]
    t = {}
    for d in events + ["normal"]:
        for k in ks:
            t[(d, k)] = tally(r["cls"][(d, k)])
    newest = events[-1]
    ev0 = (manifest.get("events") or [{}])[0].get("dates", {})
    landfall = _compact(ev0["during"]) if ev0.get("during") and _compact(ev0["during"]) in events else events[0]
    nn = t[("normal", K_SIGMA)]

    def shares(d, i, code):
        out = []
        for k in ks:
            tt = t[(d, k)]
            land = tt[1][i] + tt[2][i] + tt[3][i]
            out.append(100.0 * tt[code][i] / land if land else float("nan"))
        return out

    def tot_shares(d, i):
        out = []
        for k in ks:
            tt = t[(d, k)]
            land = tt[1][i] + tt[2][i] + tt[3][i]
            out.append(100.0 * (tt[2][i] + tt[3][i]) / land if land else float("nan"))
        return out

    def date_rows(d):
        rows = []
        for i, (pr, rings) in enumerate(feats, start=1):
            tt = t[(d, K_SIGMA)]
            land_valid = int(tt[1][i] + tt[2][i] + tt[3][i])
            if land_valid == 0:
                continue
            district = dist.get(pr.get("shapeID")) or pr.get("district")
            denom = int(poly_px[i] - tt[4][i])
            cov = round(100.0 * land_valid / denom, 1) if denom > 0 else 0.0
            sw, sc, sn, st_ = shares(d, i, 2), shares(d, i, 3), shares(d, i, 1), tot_shares(d, i)
            w_, c_, tot = sw[kc], sc[kc], st_[kc]
            nl = nn[1][i] + nn[2][i] + nn[3][i]
            normal = round(100.0 * (nn[2][i] + nn[3][i]) / nl, 2) if nl else 0.0
            normal_w = round(100.0 * nn[2][i] / nl, 2) if nl else 0.0
            fl = []
            if not district:
                fl.append("no district")
            if land_valid < MIN_VALID_PX:
                fl.append("<%d valid px" % MIN_VALID_PX)
            if cov < MIN_COVERAGE_PCT:
                fl.append("valid coverage <%d%%" % MIN_COVERAGE_PCT)
            if frac_box[i - 1] < MIN_BOX_FRAC:
                fl.append("<50% of mandal inside coast footprint")
            area = land_valid * r["px_km2"]
            wkm, ckm = tt[2][i] * r["px_km2"], tt[3][i] * r["px_km2"]
            werr = round(max(abs(a - w_) for a in sw), 2)
            rows.append({
                "mandal": pr["name"], "district": district,
                "water_pct": round(w_, 2), "water_err": werr, "crops_pct": round(c_, 2),
                "crops_err": round(max(abs(a - c_) for a in sc), 2),
                "err": werr, "total_pct": round(tot, 2), "total_err": round(max(abs(a - tot) for a in st_), 2),
                "normal_pct": normal, "normal_water_pct": normal_w,
                "change_vs_normal_pp": round(tot - normal, 2), "water_change_vs_normal_pp": round(w_ - normal_w, 2),
                "rank": None, "rank_water": None, "coverage_pct": cov, "flag": "; ".join(fl) or None,
                "no_change_pct": round(sn[kc], 2), "land_km2": round(area, 2), "area_km2": round(area, 2),
                "water_km2": round(float(wkm), 3), "crops_km2": round(float(ckm), 3), "flooded_km2": round(float(wkm + ckm), 3),
                "frac_in_footprint": round(frac_box[i - 1], 3),
            })
        ok = [q for q in rows if not q["flag"]]
        for k, q in enumerate(sorted(ok, key=lambda q: (-q["total_pct"], q["mandal"])), start=1):
            q["rank"] = k
        for k, q in enumerate(sorted(ok, key=lambda q: (-q["water_pct"], q["mandal"])), start=1):
            q["rank_water"] = k
        return rows

    by_date = {}
    for d in events:
        sc = r["scene"].get(d) or {}
        by_date[_iso(d)] = {"date": _iso(d), "scene_id": sc.get("scene_id"), "product_status": sc.get("product_status"),
                            "start_utc": sc.get("start_utc"), "rows": [q for q in date_rows(d) if q["district"]]}
        by_date[_iso(d)]["n_ranked"] = sum(1 for q in by_date[_iso(d)]["rows"] if q["rank"])
    rows_new = by_date[_iso(newest)]["rows"]
    lf = {q["mandal"]: q for q in by_date[_iso(landfall)]["rows"]}
    ranked = sorted([dict(q) for q in rows_new if not q["flag"]], key=lambda q: q["rank"])
    flagged = sorted([dict(q) for q in rows_new if q["flag"]], key=lambda q: -q["water_pct"])
    for q in ranked + flagged:     # the landfall-day block the dashboard already reads
        o = lf.get(q["mandal"])
        if o:
            q["oct28"] = {"water_pct": o["water_pct"], "water_err": o["water_err"], "crops_pct": o["crops_pct"], "crops_err": o["crops_err"],
                          "no_change_pct": o["no_change_pct"], "rank": o["rank"], "rank_water": o["rank_water"]}
    an = manifest["analyses"][0]
    out = {
        "analysis_id": an["id"], "period": [an["normal_period"][1], _iso(newest)], "normal_period": an["normal_period"],
        "latest_date": _iso(newest), "landfall_date": _iso(landfall),
        "note": ("Shares of valid, non-permanent-water 20 m land pixels in percent: likely new open water (water_pct), likely wet or flooded crops (crops_pct), total_pct = both. "
                 "normal_pct = water+crops share for the normal pair 4-16 Oct with the same thresholds; change_vs_normal_pp = total_pct - normal_pct. *_err = largest shift when the change threshold moves by +/-1 sigma. "
                 "rank = by total_pct (likely flooded = water + crops) among mandals with >=50% valid coverage and >=50% of the mandal inside the footprint; rank_water = by water_pct only (use this for headlines: the wet-crops class is not separable from normal field change, docs/METHODS.md); null = flagged, not ranked. "
                 "area_km2 = valid non-permanent-water land seen by the radar; water_km2, crops_km2, flooded_km2 = share x area. "
                 "Top-level rows = newest date; oct28 = the landfall-day scene; by_date holds every coast date after the baseline. 9 Nov combines Arnab (27-28 Oct), Murasu (1-3 Nov) and the river peak."),
        "rank_basis": "total_pct", "rank_water_basis": "water_pct",
        "dates": sorted(by_date),
        "rows": ranked, "flagged_not_ranked": flagged, "by_date": by_date,
        "provenance": _provenance(r, "build_mandal_rank"),
    }
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "mandal_rank.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
        fh.write("\n")
    return out


# ----------------------------------------------------------------------------------------------------------
# Eye profile
# ----------------------------------------------------------------------------------------------------------

def _imd_fix_at(track_path, t_utc):
    """Linear interpolation of the IMD point fixes to t_utc (datetime). Returns dict with lat, lon, bracket, method."""
    with open(track_path, encoding="utf-8") as fh:
        g = json.load(fh)
    pts = {}
    for f in g["features"]:
        if f["geometry"]["type"] != "Point":
            continue
        ts = str(f["properties"].get("time_utc", ""))[:17]
        try:
            t = datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%MZ").replace(tzinfo=datetime.timezone.utc)
        except ValueError:
            continue
        pts.setdefault(t, f["geometry"]["coordinates"])
    ts_sorted = sorted(pts)
    before = [t for t in ts_sorted if t <= t_utc]
    after = [t for t in ts_sorted if t >= t_utc]
    if not before or not after:
        raise ValueError("acquisition time outside the IMD fixes")
    t0, t1 = before[-1], after[0]
    w = 0.0 if t1 == t0 else (t_utc - t0).total_seconds() / (t1 - t0).total_seconds()
    lon = pts[t0][0] + w * (pts[t1][0] - pts[t0][0])
    lat = pts[t0][1] + w * (pts[t1][1] - pts[t0][1])
    return {"lat": round(lat, 3), "lon": round(lon, 3), "time_utc": t_utc.strftime("%Y-%m-%dT%H:%MZ"),
            "method": "linear interpolation between IMD %s (%.2fN,%.2fE) and %s (%.2fN,%.2fE) fixes; IMD positions are given to 0.1 deg (~11 km)"
                      % (t0.strftime("%H:%M UTC"), pts[t0][1], pts[t0][0], t1.strftime("%H:%M UTC"), pts[t1][1], pts[t1][0])}


def _hav_km(lat1, lon1, lat2, lon2):
    import math
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(a))


def _land_mask(shape, x, y, epsg, step=1):
    """Rasterise data/reference/land_osm_clip.geojson on (a subsampled) grid. True = land."""
    import numpy as np
    from PIL import Image, ImageDraw
    from pyproj import Transformer
    p = os.path.join(ROOT, "data", "reference", "land_osm_clip.geojson")
    if not os.path.exists(p):
        return np.zeros(shape, dtype=bool)
    with open(p, encoding="utf-8") as fh:
        gj = json.load(fh)
    tf = Transformer.from_crs(4326, epsg, always_xy=True)
    im = Image.new("L", (shape[1], shape[0]), 0)
    dr = ImageDraw.Draw(im)
    dx, dy = float(x[1] - x[0]) * step, float(y[1] - y[0]) * step
    for f in (gj["features"] if "features" in gj else [gj]):
        for poly in _polys(f.get("geometry", f)):
            for k, ring in enumerate(poly):
                X, Y = tf.transform([q[0] for q in ring], [q[1] for q in ring])
                if len(X) > 2:
                    dr.polygon([((a - x[0]) / dx, (b - y[0]) / dy) for a, b in zip(X, Y)], fill=255 if k == 0 else 0)
    return np.array(im) > 0


def _gauss_nan(blk, ok, sig):
    """NaN-aware separable Gaussian smoothing of linear power ``blk`` (zeros where not ok); sigma in cells. Returns dB (NaN if <60% weight)."""
    import numpy as np
    rad = int(np.ceil(3 * sig))
    k = np.exp(-0.5 * (np.arange(-rad, rad + 1) / sig) ** 2)

    def conv(z, ax):
        pad = [(0, 0), (0, 0)]
        pad[ax] = (rad, rad)
        zp = np.pad(z, pad)
        out = np.zeros_like(z)
        for i, kk in enumerate(k):
            sl = [slice(None), slice(None)]
            sl[ax] = slice(i, i + z.shape[ax])
            out += kk * zp[tuple(sl)]
        return out
    num = conv(conv(blk * ok, 0), 1)
    den = conv(conv(ok.astype("float64"), 0), 1)
    with np.errstate(divide="ignore", invalid="ignore"):
        s = 10.0 * np.log10(num / den)
    s[den < 0.6] = np.nan
    return s


def _wmin(a, r):
    import numpy as np
    mn = a.copy()
    for ax in (0, 1):
        z = mn.copy()
        for d in range(1, r + 1):
            for sgn in (-1, 1):
                z = np.minimum(z, np.roll(mn, sgn * d, axis=ax))
        mn = z
    return mn


def find_eye(vv_db, x, y, epsg, imd_fix, sigma_km=EYE_SIGMA_KM, cell_px=5):
    """Objective eye finder. Block-mean to 500 m cells (linear power), NaN-aware Gaussian smoothing (sigma_km),
    keep only cells >= EYE_INTERIOR_KM from any no-data cell and from land and within EYE_SEARCH_KM of the IMD fix,
    take local minima (lowest value within EYE_MIN_WINDOW_KM) and choose the one with the largest prominence
    (mean of the 12-25 km annulus minus the minimum value). Returns dict or None."""
    import numpy as np
    from pyproj import Transformer
    B = cell_px
    H, W = vv_db.shape
    h2, w2 = H // B, W // B
    v = np.isfinite(vv_db[:h2 * B, :w2 * B])
    lin = np.where(v, np.power(10.0, vv_db[:h2 * B, :w2 * B] / 10.0), 0.0)
    s = lin.reshape(h2, B, w2, B).sum((1, 3))
    c = v.reshape(h2, B, w2, B).sum((1, 3))
    ok = c >= B * B * 0.5
    blk = np.where(ok, s / np.maximum(c, 1), 0.0)
    cell_m = abs(float(x[1] - x[0])) * B
    cx = x[:w2 * B].reshape(w2, B).mean(1)
    cy = y[:h2 * B].reshape(h2, B).mean(1)
    S = _gauss_nan(blk, ok, sigma_km * 1000.0 / cell_m)
    land = _land_mask((h2, w2), cx, cy, epsg)
    rin = int(round(EYE_INTERIOR_KM * 1000.0 / cell_m))
    inter = _erode(np.isfinite(S), rin) & _erode(~land, rin)
    tr = Transformer.from_crs(epsg, 4326, always_xy=True)
    CX, CY = np.meshgrid(cx, cy)
    LON, LAT = tr.transform(CX, CY)
    d_km = np.hypot((LON - imd_fix["lon"]) * 111.32 * np.cos(np.radians(imd_fix["lat"])), (LAT - imd_fix["lat"]) * 110.57)
    storm = inter & (d_km < EYE_SEARCH_KM)
    Sf = np.where(np.isfinite(S), S, 1e9)
    lm = (Sf == _wmin(Sf, int(round(EYE_MIN_WINDOW_KM * 1000.0 / cell_m)))) & storm
    ra = int(round(25000.0 / cell_m))
    yy, xx = np.mgrid[-ra:ra + 1, -ra:ra + 1]
    rr = np.hypot(yy, xx) * cell_m / 1000.0
    ann = (rr >= 12) & (rr <= 25)
    cands = []
    for i, j in zip(*np.where(lm)):
        if i < ra or j < ra or i + ra + 1 > h2 or j + ra + 1 > w2:
            continue
        win = S[i - ra:i + ra + 1, j - ra:j + ra + 1]
        m = ann & np.isfinite(win)
        if m.sum() < 0.8 * ann.sum():
            continue
        cands.append({"lat": float(LAT[i, j]), "lon": float(LON[i, j]), "x": float(cx[j]), "y": float(cy[i]), "smoothed_vv_db": float(S[i, j]),
                      "prominence_db": float(win[m].mean() - S[i, j]), "dist_to_imd_km": float(d_km[i, j])})
    cands.sort(key=lambda q: -q["prominence_db"])
    return {"best": cands[0] if cands else None, "candidates": cands, "cell_m": cell_m, "n_local_minima": int(lm.sum())}


def build_profile(manifest, out_dir):
    """data/processed/profile.json: eye position and radial/along-track profile of 27 Oct VV (L-band, Track 48).

    Eye = unique prominent interior local minimum of 5 km Gaussian-smoothed VV near the IMD fix (see find_eye).
    ``points`` = azimuthal-mean VV in 5 km rings relative to the eye floor (mean VV inside 3 km), as the dashboard
    chart expects (-2..8 dB); ``points_abs_vv_db`` = absolute VV in 1 km rings; ``transect`` = absolute VV along the
    azimuth (along-track) direction through the eye, where the incidence angle is constant.
    """
    import numpy as np
    from pyproj import Transformer
    lay = next(l for l in manifest["layers"] if l["id"] == PROFILE_LAYER_ID)
    h5file = os.path.join(ROOT, lay["h5"])
    vv, x, y, epsg, root = read_backscatter(h5file, "VV")
    t0 = datetime.datetime.strptime(root["start_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
    t1 = datetime.datetime.strptime(root["end_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
    tm = t0 + (t1 - t0) / 2
    imd = _imd_fix_at(os.path.join(ROOT, "data", "processed", "imd_track_arnab.geojson"), tm.replace(second=0, microsecond=0))
    found = find_eye(vv, x, y, epsg, imd)
    if not found["best"]:
        raise RuntimeError("no interior local minimum of smoothed VV near the IMD fix: no eye found")
    best = found["best"]
    # stability of the centre over the smoothing scale
    spread = []
    for sg in EYE_SIGMA_VARIANTS_KM:
        f = find_eye(vv, x, y, epsg, imd, sigma_km=sg)
        if f["best"]:
            spread.append((sg, f["best"]["lat"], f["best"]["lon"], _hav_km(best["lat"], best["lon"], f["best"]["lat"], f["best"]["lon"])))
    err_km = round(max([0.5 * found["cell_m"] / 1000.0] + [q[3] for q in spread]), 1)
    tr_ll = Transformer.from_crs(epsg, 4326, always_xy=True)
    ex, ey = best["x"], best["y"]
    lon_e, lat_e = tr_ll.transform(ex, ey)

    # radial geometry on the 100 m grid, sea only
    land = _land_mask(vv.shape, x, y, epsg)
    X, Y = np.meshgrid(x, y)
    dxm, dym = X - ex, Y - ey
    rkm = np.hypot(dxm, dym) / 1000.0
    az = (np.degrees(np.arctan2(dxm, dym)) + 360.0) % 360.0
    ok = np.isfinite(vv) & ~land & (rkm < 130)
    lin = np.where(ok, np.power(10.0, np.where(ok, vv, 0) / 10.0), 0.0)
    sec = (az // 45).astype(int) % 8

    selm = ok & (rkm < 130)
    r_sel, sec_sel, lin_sel = rkm[selm], sec[selm], lin[selm]

    def ring_profile(step):
        """Per ring (width step km): pooled mean dB, standard error across azimuth sectors, pixel count."""
        nb = int(round(130 / step))
        b = np.minimum((r_sel / step).astype(int), nb - 1)
        idx = sec_sel * nb + b
        sm = np.bincount(idx, weights=lin_sel, minlength=8 * nb).reshape(8, nb)
        ct = np.bincount(idx, minlength=8 * nb).reshape(8, nb)
        res = []
        for k in range(nb):
            if ct[:, k].sum() < 30:
                res.append(None)
                continue
            secs = [10 * np.log10(sm[s_, k] / ct[s_, k]) for s_ in range(8) if ct[s_, k] >= 30]
            err = float(np.std(secs, ddof=1) / np.sqrt(len(secs))) if len(secs) >= 3 else None
            res.append({"db": float(10 * np.log10(sm[:, k].sum() / ct[:, k].sum())), "err": err, "n_px": int(ct[:, k].sum()), "n_sectors": len(secs)})
        return res, sm, ct
    p1, sm1, ct1 = ring_profile(1.0)
    cm = r_sel < 3.0
    floor_db = float(10 * np.log10(lin_sel[cm].mean()))
    fs = [10 * np.log10(lin_sel[cm & (sec_sel == s_)].mean()) for s_ in range(8) if (cm & (sec_sel == s_)).sum() >= 30]
    floor_err = float(np.std(fs, ddof=1) / np.sqrt(len(fs))) if len(fs) >= 3 else 0.0
    p5, _, _ = ring_profile(5.0)
    points = []
    for b, q in enumerate(p5):
        if q is None or q["err"] is None:
            continue
        points.append({"r_km": round(b * 5.0 + 2.5, 1), "db": round(q["db"] - floor_db, 2), "err": round(float(np.hypot(q["err"], floor_err)), 2)})
    abs_pts = []
    for b, q in enumerate(p1[:60]):
        if q is None or q["err"] is None:
            continue
        abs_pts.append({"r_km": round(b + 0.5, 1), "db": round(q["db"], 2), "err": round(q["err"], 2), "n_px": q["n_px"]})
    # eyewall ring and half-contrast radius from the 1 km profile (3-bin running mean)
    def ring_and_radius(prof, z):
        ps = np.convolve(np.pad(prof, 1, mode="edge"), np.ones(3) / 3, mode="valid")
        zi = int(np.argmax(np.where((z >= 3) & (z <= 40), ps, -1e9)))
        cdb = float(ps[z < 3].mean())
        hf = cdb + (ps[zi] - cdb) / 2
        rad = None
        for i in range(1, zi + 1):
            if ps[i - 1] < hf <= ps[i]:
                rad = float(z[i - 1] + (hf - ps[i - 1]) / (ps[i] - ps[i - 1]) * (z[i] - z[i - 1]))
                break
        return zi, cdb, float(ps[zi]) - cdb, rad
    rk = np.array([q["r_km"] for q in abs_pts])
    vb = np.array([q["db"] for q in abs_pts])
    ring_i, core_db, contrast, eye_r = ring_and_radius(vb, rk)
    # radius uncertainty: bootstrap over the 8 azimuth sectors
    rng = np.random.default_rng(0)
    radii = []
    z60 = np.arange(60) + 0.5
    for _ in range(300):
        pick = rng.integers(0, 8, 8)
        sm_ = sm1[pick, :60].sum(0)
        ct_ = ct1[pick, :60].sum(0)
        if (ct_ < 30).any():
            continue
        rad = ring_and_radius(10 * np.log10(sm_ / ct_), z60)[3]
        if rad is not None:
            radii.append(rad)
    eye_r_err = round(float(np.std(radii)), 1) if len(radii) >= 20 else None

    # transect along the azimuth (along-track) direction: principal axis of the valid footprint, constant incidence angle
    # along-track direction from the swath edges: fit x = a + b*y to the first and last valid pixel of every row that is not
    # cut by the subset box (the box clips the footprint, so a principal-axis fit of the valid area would be wrong)
    vd = np.isfinite(vv[::10, ::10])
    xd, yd = x[::10], y[::10]
    rows = np.where(vd.any(1))[0]
    first = {ri: np.where(vd[ri])[0][0] for ri in rows}
    last = {ri: np.where(vd[ri])[0][-1] for ri in rows}
    wmax = max(last[ri] - first[ri] for ri in rows)
    full = [ri for ri in rows if (last[ri] - first[ri]) >= 0.95 * wmax]   # rows between the slanted frame ends: both edges run along track
    pts_l = [(yd[ri], xd[first[ri]]) for ri in full]
    pts_r = [(yd[ri], xd[last[ri]]) for ri in full]
    slopes = []
    for pts in (pts_l, pts_r):
        if len(pts) >= 10:
            a_ = np.array(pts)
            slopes.append(np.polyfit(a_[:, 0], a_[:, 1], 1)[0])
    if not slopes:
        raise RuntimeError("could not find the swath edges for the along-track direction")
    b_ = float(np.mean(slopes))
    nrm = float(np.hypot(b_, 1.0))
    ux, uy = b_ / nrm, 1.0 / nrm              # unit vector along track, pointing north
    bearing = float((np.degrees(np.arctan2(ux, uy)) + 360) % 360)
    s_al = dxm * ux + dym * uy
    c_al = -dxm * uy + dym * ux
    strip = ok & (np.abs(c_al) <= 2000.0) & (np.abs(s_al) <= 125000.0)
    sb = np.floor(s_al / 1000.0).astype(int)
    mb_ = strip & np.isfinite(vv)
    sbin = (np.floor(s_al[mb_] / 1000.0).astype(int) + 125)
    lv, dv = lin[mb_], vv[mb_]
    n_t = np.bincount(sbin, minlength=250)
    sum_t = np.bincount(sbin, weights=lv, minlength=250)
    s1 = np.bincount(sbin, weights=dv, minlength=250)
    s2 = np.bincount(sbin, weights=dv * dv, minlength=250)
    tpts = []
    for b in range(250):
        if n_t[b] < 20:
            continue
        var = max(s2[b] / n_t[b] - (s1[b] / n_t[b]) ** 2, 0.0)
        tpts.append({"s_km": round(b - 125 + 0.5, 1), "db": round(float(10 * np.log10(sum_t[b] / n_t[b])), 2),
                     "err": round(float(np.sqrt(var / n_t[b])), 2), "n_px": int(n_t[b])})

    imd_off = round(_hav_km(lat_e, lon_e, imd["lat"], imd["lon"]), 1)
    prev = None
    pj = os.path.join(out_dir, "profile.json")
    if os.path.exists(pj):
        try:
            with open(pj, encoding="utf-8") as fh:
                old = json.load(fh)
            if old.get("provenance"):
                prev = old["provenance"].get("previous_placeholder_eye")
            elif old.get("eye"):
                prev = {"eye": old["eye"], "offset_to_new_eye_km": round(_hav_km(lat_e, lon_e, old["eye"][0], old["eye"][1]), 1)}
        except Exception:
            prev = None
    out = {
        "layer_id": PROFILE_LAYER_ID,
        "eye": [round(lat_e, 3), round(lon_e, 3)],
        "eye_centre_err_km": err_km,
        "eye_radius_km": None if eye_r is None else round(eye_r, 1),
        "eye_radius_err": eye_r_err,
        "eye_radius_definition": "half-contrast radius of the azimuthal-mean VV profile (midway between the inner-core mean, r<3 km, and the eyewall ring maximum, 1 km rings, 3-ring running mean)",
        "eyewall_ring_km": round(float(rk[ring_i]), 1),
        "core_contrast_db": round(contrast, 2),
        "imd_fix": imd,
        "imd_offset_km": imd_off,
        "acquisition_utc": "%s to %s" % (root["start_utc"], root["end_utc"][11:]),
        "bin_km": 1,
        "sea_only_land_masked": True,
        "points": points,
        "points_definition": "points: azimuthal-mean VV (linear power, 5 km rings) minus the eye floor (mean VV inside 3 km: %.2f dB); err = standard error across up to 8 azimuth sectors, combined with the floor's. points_abs_vv_db: absolute VV dB in 1 km rings (err across sectors). transect: absolute VV along the azimuth direction." % floor_db,
        "points_abs_vv_db": abs_pts,
        "eye_floor_vv_db": round(floor_db, 2),
        "transect": {
            "direction": "along-track (azimuth) axis through the eye, from a line fit to the swath edges; positive s = toward the north, bearing %.0f deg from north" % bearing,
            "bearing_deg": round(bearing, 1), "strip_halfwidth_km": 2.0, "bin_km": 1,
            "why": "the radar incidence angle changes across the swath (range), so a line along the azimuth direction keeps it constant",
            "points": tpts,
        },
        "notes": "Backscatter only; no wind speed is derived. The eye is faint in L-band VV (prominence %.2f dB over the 12-25 km annulus at 5 km smoothing); the ring profile mixes near and far range, so the level carries an incidence-angle trend. Single scene, VALIDATED product, no ground truth." % best["prominence_db"],
        "eye_search": {"method": "unique prominent interior local minimum of %.0f km Gaussian-smoothed VV (500 m cells), >= %.0f km from no-data and land, within %.0f km of the IMD fix, lowest within %.0f km radius; prominence = 12-25 km annulus mean minus minimum"
                       % (EYE_SIGMA_KM, EYE_INTERIOR_KM, EYE_SEARCH_KM, EYE_MIN_WINDOW_KM),
                       "n_local_minima": found["n_local_minima"], "n_candidates": len(found["candidates"]),
                       "prominence_db": round(best["prominence_db"], 2), "smoothed_vv_db": round(best["smoothed_vv_db"], 2),
                       "centre_by_sigma_km": [{"sigma_km": q[0], "lat": round(q[1], 3), "lon": round(q[2], 3), "offset_km": round(q[3], 1)} for q in spread]},
        "provenance": {"created_utc": NOW(), "tool": "tools/build_web.py (build_profile)", "h5_sources": [lay["h5"]], "source_granule": root.get("source_granule"),
                       "product_status": root.get("product_status"), "band": "L", "pol": "VV", "track": root.get("track"),
                       "method": "see eye_search, points_definition and transect; docs/METHODS.md",
                       "caveats": ["single scene, single band", "weak eye contrast", "level carries an incidence-angle trend across the swath", "no ground truth or best-track comparison beyond the IMD fix interpolation"],
                       "previous_placeholder_eye": prev},
    }
    os.makedirs(out_dir, exist_ok=True)
    with open(pj, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
        fh.write("\n")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--manifest", default=os.path.join(ROOT, "data", "processed", "manifest.json"))
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "web"), help="output directory (default data/web)")
    ap.add_argument("--only", nargs="*", help="build only these layer ids")
    ap.add_argument("--max-kb", type=int, default=600, help="PNG size cap in KB (default 600)")
    ap.add_argument("--processed-out", default=os.path.join(ROOT, "data", "processed"),
                    help="where mandal_rank.json and profile.json go (default data/processed)")
    ap.add_argument("--no-derived", action="store_true", help="skip class maps, mandal_rank.json and profile.json")
    ap.add_argument("--derived-only", action="store_true", help="build only class maps, mandal_rank.json and profile.json")
    ap.add_argument("--write-manifest", action="store_true", help="(default now) point the class layers and the sea difference layer of --manifest at the newest built products")
    ap.add_argument("--no-write-manifest", action="store_true", help="do not touch the manifest (default: class layers + sea difference layer are retargeted at the newest date)")
    args = ap.parse_args()

    with open(args.manifest, encoding="utf-8") as f:
        manifest = json.load(f)
    layers = [l for l in manifest.get("layers", []) if l.get("h5")]
    if args.derived_only:
        layers = []
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
    if not todo and not args.derived_only:
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
    if not args.derived_only and (not args.only or any(q.startswith("nisar_sea_diff") for q in args.only)):
        try:
            metas = build_sea_difference(manifest, args.out, args.max_kb)
            for m in metas:
                b = m["bounds"]
                print("%-40s %-5s %-11s %9.1f  p2 %.2f p50 %.2f p98 %.2f dB  nan %.2f  [[%.4f,%.4f],[%.4f,%.4f]]  (%s)" % (
                    m["layer_id"], m["pol"], "%dx%d" % tuple(m["image_px"]), m["png_kb"], m["p2"], m["p50"], m["p98"],
                    m["nan_frac"], b[0][0], b[0][1], b[1][0], b[1][1], m["grid_check"]))
            if metas and not args.no_write_manifest:
                ch = update_sea_diff_manifest(args.manifest, metas)
                print("manifest sea difference layer -> %s (%s)" % (metas[-1]["layer_id"], "%d fields changed" % len(ch) if ch else "already current"))
        except Exception as exc:
            failed += 1
            print("FAIL  sea difference: %s" % exc)
    if not args.no_derived and not args.only:
        res = None
        try:
            res = build_class_maps(manifest, args.out)
            for d in res["events"]:
                st = res["stats"]["%s|k=%.1f" % (d, K_SIGMA)]
                print("class %s: new water %.1f km2 (%.2f%% of land), wet crops %.1f km2 (%.2f%%), no change %.1f km2; permanent water %.1f km2"
                      % (d, st["new_water_km2"], st["new_water_pct_of_land"], st["wet_crops_km2"], st["wet_crops_pct_of_land"], st["no_change_km2"], st["permanent_water_km2"]))
            print("thresholds: %s" % json.dumps(res["thresholds"]))
            patch_water_threshold(args.out, manifest, res)
            if not args.no_write_manifest:     # normal builds (CI too) retarget the class layers at the newest coast date
                ch = update_class_manifest(args.manifest, res)
                print("manifest class layers -> %s (%s)" % (res["events"][-1], "%d fields changed" % len(ch) if ch else "already current"))
        except Exception as exc:
            failed += 1
            print("FAIL  class maps: %s" % exc)
        if res is not None:
            try:
                o = build_mandal_rank(manifest, args.processed_out, res)
                print("mandal_rank.json: %d ranked, %d flagged" % (len(o["rows"]), len(o["flagged_not_ranked"])))
            except Exception as exc:
                failed += 1
                print("FAIL  mandal_rank.json: %s" % exc)
        try:
            o = build_profile(manifest, args.processed_out)
            print("profile.json: eye %.3f N %.3f E, radius %s km, IMD offset %.1f km" % (o["eye"][0], o["eye"][1], o["eye_radius_km"], o["imd_offset_km"]))
        except Exception as exc:
            failed += 1
            print("FAIL  profile.json: %s" % exc)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
