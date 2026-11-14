#!/usr/bin/env python3
"""Export web-ready assets from git-ignored data/raw + data/browse into tracked data/processed/.

Re-runnable. Run from repo root:  python tools/make_web_assets.py
Needs: pillow, numpy, shapely.

NISAR quick-looks are DISPLAY-ONLY greyscale (Rec.601 luminance of the colour composite),
NOT calibrated dB. Fully black / transparent nodata pixels become transparent.
No geographic cropping: image bounds stay identical to the KML LatLonQuad.
"""
import argparse, csv, io, json, re, shutil, sys
from pathlib import Path
import numpy as np
from PIL import Image
from shapely.geometry import shape, mapping

ROOT = Path(__file__).resolve().parents[1]
BROWSE = ROOT / "data/browse/nisar_arnab"
GIBS = ROOT / "data/raw/gibs"
REF = ROOT / "data/reference"
OUT = ROOT / "data/processed"
IMG = OUT / "img"

NISAR_LIMIT = 600 * 1024
GIBS_LIMIT = 400 * 1024
MAX_W = 1400
STEPS = [1400, 1200, 1000, 900, 800, 700, 600, 500]

# output name -> (source stem, kml source stem used for bounds)
NISAR = {
    "nisar_l_sea_20261003_t48_vv": "2026-10-03T1301Z_T48_F80",
    "nisar_l_sea_20261015_t48_vv": "2026-10-15T1301Z_T48_F80",
    "nisar_l_sea_20261027_t48_vv": "2026-10-27T1301Z_T48_F80",
    "nisar_l_sea_20261108_t48_vv": "2026-11-08T1301Z_T48_F80",
    "nisar_l_coast_20261004_t55_hh": "2026-10-04T0001Z_T55_F10",
    "nisar_l_coast_20261016_t55_hh": "2026-10-16T0001Z_T55_F10",
    "nisar_l_coast_20261028_t55_hh": "2026-10-28T0001Z_T55_F10",
    "nisar_l_coast_20261109_t55_hh": "2026-11-09T0001Z_T55_F10",
}
KML_ORDER = {  # same track/frame, chronological KML stems
    "T48_F80": ["2026-10-27T1301Z_T48_F80", "2026-11-08T1301Z_T48_F80"],
    "T55_F10": ["2026-10-28T0001Z_T55_F10", "2026-11-09T0001Z_T55_F10"],
}


def kml_bounds(stem):
    p = BROWSE / (stem + ".kml")
    if not p.exists():
        return None
    m = re.search(r"<coordinates>(.*?)</coordinates>", p.read_text(), re.S)
    pts = [tuple(map(float, c.split(","))) for c in m.group(1).split()]
    lons = [x[0] for x in pts]; lats = [x[1] for x in pts]
    return [[min(lats), min(lons)], [max(lats), max(lons)]]


def inferred_bounds(stem):
    key = re.search(r"(T\d+_F\d+)", stem).group(1)
    date = stem[:10]
    for k in KML_ORDER[key]:
        if k[:10] > date and kml_bounds(k):
            return kml_bounds(k), k
    raise RuntimeError("no later KML for " + stem)


def to_grey_la(im):
    """Colour composite -> luminance L plus alpha (0 where source alpha 0 or pure black)."""
    a = np.array(im.convert("RGBA"))
    lum = (0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]).round().astype(np.uint8)
    nodata = (a[..., 3] == 0) | (a[..., :3].sum(-1) == 0)
    alpha = np.where(nodata, 0, 255).astype(np.uint8)
    lum[nodata] = 0
    return Image.fromarray(np.dstack([lum, alpha]), "LA")


def png_bytes(im):
    b = io.BytesIO(); im.save(b, "PNG", optimize=True); return b.getvalue()


def fit_png(im, limit):
    w0, h0 = im.size
    for w in [s for s in STEPS if s <= max(w0, MAX_W)]:
        w = min(w, w0)
        r = im if w == w0 else im.resize((w, round(h0 * w / w0)), Image.LANCZOS)
        data = png_bytes(r)
        if len(data) <= limit:
            return data, r.size
    return data, r.size  # best effort (smallest tried)


def do_nisar(entries, problems):
    for out, stem in NISAR.items():
        src = BROWSE / (stem + ".png")
        if not src.exists():
            problems.append("missing source " + str(src)); continue
        im = Image.open(src); im.load()
        la = to_grey_la(im)
        data, size = fit_png(la, NISAR_LIMIT)
        (IMG / (out + ".png")).write_bytes(data)
        b = kml_bounds(stem); inferred = b is None; note = None
        if inferred:
            b, k = inferred_bounds(stem); note = "bounds from KML of " + k
        if len(data) > NISAR_LIMIT:
            problems.append(f"{out}.png {len(data)} B exceeds limit")
        entries.append({"file": f"img/{out}.png", "source": f"data/browse/nisar_arnab/{stem}.png",
                        "width": size[0], "height": size[1], "source_width": im.size[0],
                        "source_height": im.size[1], "bytes": len(data), "bounds": b,
                        "bounds_inferred": inferred, "bounds_note": note,
                        "display_only_greyscale": True})


def std_of(p):
    return float(np.asarray(Image.open(p).convert("L"), dtype=float).std())


def save_small(src, dst_stem, limit):
    im = Image.open(src); im.load()
    ext = src.suffix.lower()
    if src.stat().st_size <= limit:
        dst = IMG / (dst_stem + ext); shutil.copyfile(src, dst); return dst, im.size
    # shrink progressively
    for w in [1200, 1000, 800, 600]:
        r = im.resize((w, round(im.size[1] * w / im.size[0])), Image.LANCZOS)
        dst = IMG / (dst_stem + ext)
        if ext == ".png": r.save(dst, "PNG", optimize=True)
        else: r.convert("RGB").save(dst, "JPEG", quality=82, optimize=True)
        if dst.stat().st_size <= limit: return dst, r.size
    return dst, r.size


def do_gibs(entries, problems):
    picks = []
    picks.append(("himawari_b13_20261027T1300Z_sea.png", "Himawari B13 clean IR 2026-10-27 13:00Z, sea box"))
    picks.append(("imerg_daily_2026-10-27_sea.png", "IMERG daily precipitation 2026-10-27, sea box"))
    cands = sorted(GIBS.glob("viirs_*_truecolor_2026-10-27_sea.jpg"))
    if cands:
        best = max(cands, key=std_of)
        picks.append((best.name, f"VIIRS true colour 2026-10-27, sea box (highest std of {len(cands)} satellites)"))
    else:
        c2 = sorted(GIBS.glob("viirs_*_truecolor_2026-10-27_context.jpg"))
        if c2:
            best = max(c2, key=std_of); picks.append((best.name, "VIIRS true colour 2026-10-27, context box"))
    for name, desc in picks:
        src = GIBS / name
        if not src.exists():
            problems.append("missing GIBS " + name); continue
        if "Reference_Labels" in name:
            continue
        side = json.loads(src.with_suffix(".json").read_text())
        w, s, e, n = side["bbox_wsen"]
        dst, size = save_small(src, "gibs_" + src.stem, GIBS_LIMIT)
        if dst.stat().st_size > GIBS_LIMIT: problems.append(f"{dst.name} exceeds {GIBS_LIMIT}")
        entries.append({"file": f"img/{dst.name}", "source": str(src.relative_to(ROOT)),
                        "width": size[0], "height": size[1], "bytes": dst.stat().st_size,
                        "bounds": [[s, w], [n, e]], "bounds_inferred": False,
                        "layer": side.get("layer"), "time": side.get("time"), "description": desc})


def do_mandals(report, problems):
    dmap = {}
    with open(REF / "mandal_district_2022.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            dmap[r["mandal_name_geoboundaries"].strip()] = (r["mandal_name_official"].strip(), r["district_2022"].strip())
    gj = json.loads((REF / "mandals_delta.geojson").read_text())
    feats, unmatched, per = [], [], {}
    # Name-only joins are ambiguous when geoBoundaries reuses a name (e.g. two "Yelamanchili").
    # Rule: if a name is UNIQUE among polygons, the CSV name match stands (partially clipped
    # real mandals such as Pithapuram keep their district). If a name is DUPLICATED, the match
    # applies only to a polygon with frac_inside_delta_box >= MIN_FRAC_INSIDE (joined on
    # shapeID, from mandals_delta_list.csv); the other polygon(s) get district = null.
    MIN_FRAC_INSIDE = 0.5
    frac = {}
    with open(REF / "mandals_delta_list.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            frac[r["shapeID"].strip()] = float(r["frac_inside_delta_box"])
    names = [ft["properties"]["shapeName"].strip() for ft in gj["features"]]
    dups = sorted({n for n in names if names.count(n) > 1})
    report["mandals_duplicate_names"] = dups
    report["mandals_outside_box_nulled"] = []

    def rnd(c):
        return [rnd(x) for x in c] if isinstance(c[0], (list, tuple)) else [round(c[0], 4), round(c[1], 4)]

    for ft in gj["features"]:
        nm = ft["properties"]["shapeName"].strip()
        sid = ft["properties"].get("shapeID")
        off, dist = dmap.get(nm, (None, None))
        off, dist = (off or None), (dist or None)
        fr = frac.get(sid)
        if fr is None:
            problems.append(f"mandal {nm} shapeID {sid} missing from mandals_delta_list.csv")
        if dist is not None and nm in dups and (fr is None or fr < MIN_FRAC_INSIDE):
            report["mandals_outside_box_nulled"].append(f"{nm} ({sid}, frac_inside={fr})")
            off, dist = None, None
        if dist is None: unmatched.append(nm)
        g = shape(ft["geometry"]).simplify(0.0005, preserve_topology=True)
        if g.is_empty: g = shape(ft["geometry"])
        geom = mapping(g)
        geom = {"type": geom["type"], "coordinates": rnd(list(geom["coordinates"]))}
        per[dist or '(no match)'] = per.get(dist or '(no match)', 0) + 1
        feats.append({"type": "Feature", "properties": {"shapeID": sid, "name": nm, "official_name": off, "district": dist}, "geometry": geom})
    p = OUT / "mandals.geojson"
    p.write_text(json.dumps({"type": "FeatureCollection", "features": feats}, separators=(",", ":"), ensure_ascii=False))
    report.update({"mandals_total": len(feats), "mandals_per_district": per, "mandals_unmatched": unmatched,
                   "mandals_bytes": p.stat().st_size})
    if p.stat().st_size > 400 * 1024: problems.append(f"mandals.geojson {p.stat().st_size} B > 400 KB")


def do_track(report):
    rows = list(csv.DictReader(open(REF / "imd_track_arnab.csv", newline="", encoding="utf-8")))
    for i, r in enumerate(rows): r["_i"] = i
    rows.sort(key=lambda r: (r["time_utc"].split("/")[0], r["_i"]))
    pts = [{"type": "Feature", "properties": {"time_utc": r["time_utc"], "intensity": r["intensity"],
            "category": r["category"] or None, "source_pdf": r["source_pdf"], "page": r["page"]},
            "geometry": {"type": "Point", "coordinates": [float(r["lon"]), float(r["lat"])]}} for r in rows]
    coords = []
    for r in rows:
        c = [float(r["lon"]), float(r["lat"])]
        if not coords or coords[-1] != c: coords.append(c)
    line = {"type": "Feature", "properties": {"name": "Cyclone Arnab IMD track", "interpolated": True,
            "note": "straight segments between IMD-reported fixes; not a best track"},
            "geometry": {"type": "LineString", "coordinates": coords}}
    p = OUT / "imd_track_arnab.geojson"
    p.write_text(json.dumps({"type": "FeatureCollection", "features": [line] + pts}, indent=1))
    report["track_fixes"] = len(pts); report["track_line_vertices"] = len(coords)


def dir_size(p):
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--skip-nisar", action="store_true", help="skip slow image conversion")
    args = ap.parse_args()
    IMG.mkdir(parents=True, exist_ok=True)
    entries, problems, report = [], [], {}
    if not args.skip_nisar: do_nisar(entries, problems)
    do_gibs(entries, problems)
    do_mandals(report, problems)
    do_track(report)
    (IMG / "_index.json").write_text(json.dumps({"note": "NISAR images are display-only greyscale (luminance of colour quick-look), not dB. bounds=[[S,W],[N,E]].",
                                                 "images": entries}, indent=1))
    for e in entries:
        print(f"{e['file']:55s} {e['width']}x{e['height']} {e['bytes']/1024:7.1f} KB inferred={e['bounds_inferred']}")
    total = dir_size(OUT)
    print(json.dumps(report, indent=1))
    print(f"data/processed total: {total/1024/1024:.2f} MB")
    for pr in problems: print("PROBLEM:", pr)
    if total > 8 * 1024 * 1024: print("PROBLEM: processed total > 8 MB"); return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
