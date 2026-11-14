#!/usr/bin/env python3
"""Package D: ASF/CMR metadata-only NISAR GCOV manifest (no HDF5 download, no login).

Outputs (repo-relative):
  data/raw/asf/asf_<box>_20261001_20261114.json    raw API responses (git-ignored)
  data/reference/scene_manifest.csv                requested columns, ALL granules (role filled for planner scenes)
  data/reference/scene_manifest_full.csv           every granule, extra fields, both box fractions
  data/reference/cmr_nisar_collections.json        raw CMR keyword result
  data/browse/nisar_arnab/<YYYY-MM-DDTHHMM>Z_T<trk>_F<frm>.{png,kml}  quick-looks of role scenes
  data/logs/package_D_run.json                     machine log used for package_D.md

Coverage fraction = area(footprint ∩ box) / area(box), planar lon/lat degrees (box 1.0 x 0.9 deg;
cos(lat) varies <1.5 % across it); cross-checked with a 41x41 grid of points in the box (planner's
method) -> grid_* columns.
Usage (repo root): python src/fetch/D_asf_manifest.py   (needs requests, shapely)
"""
import csv, hashlib, json, re, sys, time, datetime as dt
from pathlib import Path
import requests
from shapely.geometry import shape, box, Point

ROOT = Path(__file__).resolve().parents[2]
ASF = "https://api.daac.asf.alaska.edu/services/search/param"
START, END = "2026-10-01T00:00:00Z", "2026-11-14T23:59:59Z"
BOXES = {"delta": (81.6, 16.2, 82.6, 17.1), "sea": (81.0, 15.0, 85.0, 18.0)}
log = {"fetched_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "urls": [], "files": [], "failures": []}


def wkt(b):
    w, s, e, n = b
    return f"POLYGON(({w} {s},{e} {s},{e} {n},{w} {n},{w} {s}))"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def get(url, params=None):
    for i in range(3):
        try:
            r = requests.get(url, params=params, timeout=120)
            log["urls"].append(r.url if len(r.url) < 600 else r.url[:600] + "...")
            if r.status_code == 200:
                return r
            log["failures"].append(f"{r.url[:200]} -> HTTP {r.status_code}")
        except Exception as e:
            log["failures"].append(f"{url[:200]} -> {e!r}")
        time.sleep(3)
    return None


def asf_query(name):
    r = get(ASF, dict(dataset="NISAR", processingLevel="GCOV", intersectsWith=wkt(BOXES[name]), start=START,
                      end=END, maxResults=1000, output="geojson"))
    if r is None:
        sys.exit(f"ASF query {name} failed")
    p = ROOT / f"data/raw/asf/asf_{name}_20261001_20261114.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(r.content)
    log["files"].append((str(p.relative_to(ROOT)), p.stat().st_size, sha(p)))
    return r.json()["features"]


def grid_frac(geom, b, n=41):
    w, s, e, nn = b
    pts = [(w + (e - w) * i / (n - 1), s + (nn - s) * j / (n - 1)) for i in range(n) for j in range(n)]
    return sum(geom.intersects(Point(x, y)) for x, y in pts) / len(pts)


def rec(f):
    p = f["properties"]
    g = shape(f["geometry"])
    fid = p["fileID"]
    m = re.match(r"NISAR_L2_(PR|UR)_GCOV_(\d+)_(\d+)_([AD])_(\d+)_(\d+)_(\w{4})_", fid)
    coll = p["url"].split("/")[-3]  # .../<collection>/<granule>/<granule>.h5
    r = dict(granule_id=fid, track=p["pathNumber"], frame=p["frameNumber"], direction=p["flightDirection"],
             acquisition_utc=p["startTime"], stop_utc=p["stopTime"], processing_level=m.group(1), crid=p["crid"],
             collection=coll, mode=m.group(6) + "_" + m.group(7),
             polarisations="+".join(p.get("mainBandPolarization") or []), frame_coverage=p["frameCoverage"],
             size_bytes=(p.get("bytes") or {}).get(p["fileName"], {}).get("bytes", ""), download_url=p["url"],
             md5=p.get("md5sum") or "", pge=p.get("pgeVersion"), _found=set())
    for k, b in BOXES.items():
        bx = box(*b)
        r[f"frac_{k}"] = round(g.intersection(bx).area / bx.area, 4)
        r[f"grid_{k}"] = round(grid_frac(g, b), 3)
    ll = [u for u in (p.get("browse") or []) if u.endswith("_LATLON.png")]
    r["browse_url"] = ll[0] if ll else ""
    kml = [u for u in (p.get("additionalUrls") or []) if u.endswith("_LATLON.kml")]
    r["kml_url"] = kml[0] if kml else ""
    return r


def roles():
    """Planner's role -> granule id, parsed read-only from src/fetch/subset_arnab.py."""
    txt = (ROOT / "src/fetch/subset_arnab.py").read_text()
    out = {}
    for rid, fid in re.findall(r'"(L_[A-Z0-9_]+)": \("P\d", "\w+", "(NISAR_L2_PR_[^"]+)"', txt):
        out[fid] = rid
    for rid, fid in re.findall(r'"(L_[A-Z0-9_]+)": \("NISAR-UR/UR_L2_L_GCOV", "(NISAR_L2_UR_[^"]+)"', txt):
        out[fid] = rid + "_URfallback"
    return out


def main():
    feats = {"delta": asf_query("delta"), "sea": asf_query("sea")}
    recs = {}
    for k, fs in feats.items():
        for f in fs:
            r = recs.setdefault(f["properties"]["fileID"], rec(f))
            r["_found"].add(k)
    log["counts"] = {k: len(v) for k, v in feats.items()} | {"unique": len(recs)}
    rmap = roles()
    rows = sorted(recs.values(), key=lambda r: (r["acquisition_utc"], r["granule_id"]))
    for r in rows:
        r["role"] = rmap.get(r["granule_id"], "")
        r["found_in"] = "+".join(sorted(r["_found"]))
    log["roles_expected"] = len(rmap)
    log["roles_missing"] = [f"{v}:{k}" for k, v in rmap.items() if k not in recs]
    stems = {}
    for r in rows:
        stems.setdefault(re.sub(r"_P\d{5}_.*", "", r["granule_id"]), set()).add(r["crid"])
    log["multi_crid"] = {k: sorted(v) for k, v in stems.items() if len(v) > 1}
    log["t156_delta_query"] = [r["granule_id"] for r in rows if r["track"] == 156 and "delta" in r["found_in"]]
    log["t156_sea_query"] = [r["granule_id"] for r in rows if r["track"] == 156 and "sea" in r["found_in"]]

    ref = ROOT / "data/reference"

    def level_txt(r):
        if r["processing_level"] == "UR":
            return "UR (urgent response)"
        return "PR (" + ("provisional" if "PROVISIONAL" in r["collection"] else "validated, GCOV_V1") + ")"

    def notes(r):
        n = [f"crid={r['crid']}", f"mode={r['mode']}", f"frame_coverage={r['frame_coverage']}", r["direction"],
             f"collection={r['collection']}", f"found_in={r['found_in']}", f"sea_box_frac={r['frac_sea']}",
             f"delta_grid_check={r['grid_delta']}"]
        if not r["md5"]:
            n.append("md5 not in API")
        return "; ".join(n)

    cols = ("role granule_id track frame polarisations acquisition_utc processing_level fraction_of_delta_box_covered "
            "size_bytes download_url browse_url notes").split()
    with open(ref / "scene_manifest.csv.tmp", "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(cols)
        for r in rows:
            w.writerow([r["role"], r["granule_id"], r["track"], r["frame"], r["polarisations"], r["acquisition_utc"],
                        level_txt(r), r["frac_delta"], r["size_bytes"], r["download_url"], r["browse_url"], notes(r)])
    (ref / "scene_manifest.csv.tmp").replace(ref / "scene_manifest.csv")
    fcols = ["role", "granule_id", "track", "frame", "direction", "acquisition_utc", "stop_utc", "processing_level", "crid",
             "collection", "mode", "polarisations", "frame_coverage", "frac_delta", "grid_delta", "frac_sea", "grid_sea",
             "size_bytes", "md5", "download_url", "browse_url", "kml_url", "pge", "found_in"]
    with open(ref / "scene_manifest_full.csv.tmp", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fcols, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    (ref / "scene_manifest_full.csv.tmp").replace(ref / "scene_manifest_full.csv")
    for n in ("scene_manifest.csv", "scene_manifest_full.csv"):
        log["files"].append((f"data/reference/{n}", (ref / n).stat().st_size, sha(ref / n)))

    bdir = ROOT / "data/browse/nisar_arnab"
    bdir.mkdir(parents=True, exist_ok=True)
    log["browse"] = []
    for r in rows:
        if not r["role"]:
            continue
        stem = r["acquisition_utc"][:16].replace(":", "") + f"Z_T{r['track']}_F{r['frame']}"
        stem = r["acquisition_utc"][:10] + "T" + r["acquisition_utc"][11:16].replace(":", "") + f"Z_T{r['track']}_F{r['frame']}"
        if r["processing_level"] == "UR":
            stem += "_UR"
        for ext, u in (("png", r["browse_url"]), ("kml", r["kml_url"])):
            if not u:
                log["failures"].append(f"{r['granule_id']} no {ext} url"); continue
            dest = bdir / f"{stem}.{ext}"
            if dest.exists() and dest.stat().st_size > 0:
                log["files"].append((str(dest.relative_to(ROOT)), dest.stat().st_size, sha(dest)))
                log["browse"].append((str(dest.relative_to(ROOT)), r["role"], u))
                continue
            resp = get(u)
            if resp is None:
                continue
            dest.write_bytes(resp.content)
            log["files"].append((str(dest.relative_to(ROOT)), dest.stat().st_size, sha(dest)))
            log["browse"].append((str(dest.relative_to(ROOT)), r["role"], u))

    c = get("https://cmr.earthdata.nasa.gov/search/collections.json", dict(keyword="NISAR", page_size=200))
    if c is not None:
        p = ref / "cmr_nisar_collections.json"
        p.write_bytes(c.content)
        log["files"].append((str(p.relative_to(ROOT)), p.stat().st_size, sha(p)))
        log["cmr_hits"] = c.headers.get("CMR-Hits")
        log["cmr"] = [(e.get("short_name"), e.get("version_id"), e.get("title"), e.get("data_center"))
                      for e in c.json()["feed"]["entry"]]
    (ROOT / "data/logs").mkdir(exist_ok=True)
    (ROOT / "data/logs/package_D_run.json").write_text(json.dumps(log, indent=1, default=str))
    print(json.dumps({k: log.get(k) for k in ("counts", "roles_expected", "roles_missing", "multi_crid",
                                                "t156_delta_query", "t156_sea_query", "failures", "cmr_hits")}, indent=1))


if __name__ == "__main__":
    main()
