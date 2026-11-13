"""Find every NISAR scene over the study area (no login needed).

Writes:
  data/catalogue/<aoi>_scenes.csv   one row per product (GCOV + GUNW)
  app/scenes.json                   GCOV scenes with public browse image + bounds,
                                    used by the web viewer

Usage:
  python src/nisar_search.py                       # uses config.py AOI
  python src/nisar_search.py --bbox 88.0 21.5 89.2 22.5 --name sundarbans
"""
import argparse
import csv
import json
import re
from concurrent.futures import ThreadPoolExecutor

import asf_search as asf
import requests

import config

KML_COORDS = re.compile(r"<coordinates>\s*([^<]+)</coordinates>")


def kml_bounds(kml_url: str):
    """Read the public browse KML and return [[south, west], [north, east]]."""
    try:
        resp = requests.get(kml_url, timeout=30)
        if resp.status_code != 200:
            return None
        txt = resp.text
        pts = [tuple(map(float, p.split(",")[:2])) for p in KML_COORDS.search(txt).group(1).split()]
        lons, lats = zip(*pts)
        return [[min(lats), min(lons)], [max(lats), max(lons)]]
    except Exception as exc:  # network hiccup or missing KML
        print("  bounds failed:", kml_url[-60:], exc)
        return None


def crid(file_id: str) -> str:
    # e.g. ..._P05023_N_F_J_00 -> P05023 (P = production processing, X = experimental)
    m = re.search(r"_([PX]\d{5})_", file_id)
    return m.group(1) if m else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bbox", nargs=4, type=float, default=config.AOI_BBOX,
                    metavar=("W", "S", "E", "N"))
    ap.add_argument("--name", default=config.AOI_NAME)
    ap.add_argument("--levels", nargs="+", default=["GCOV", "GUNW"])
    args = ap.parse_args()

    wkt = config.aoi_wkt(args.bbox)
    rows = []
    for lvl in args.levels:
        res = asf.search(dataset="NISAR", intersectsWith=wkt, processingLevel=lvl, maxResults=2000)
        print(f"{lvl}: {len(res)} products")
        for p in res:
            pr = p.properties
            browse = [b for b in pr.get("browse") or [] if b.endswith("_LATLON.png")]
            rows.append({
                "date": (pr.get("startTime") or "")[:10],
                "start_time": pr.get("startTime"),
                "level": lvl,
                "direction": pr.get("flightDirection"),
                "track": pr.get("pathNumber"),
                "frame": pr.get("frameNumber"),
                "coverage": pr.get("frameCoverage"),
                "crid": crid(pr["fileID"]),
                "size_gb": round(sum(v["bytes"] for v in pr["bytes"].values()) / 1e9, 2),
                "file_id": pr["fileID"],
                "h5_url": pr.get("url"),
                "browse_png": browse[0] if browse else "",
            })

    rows.sort(key=lambda r: (r["level"], r["start_time"] or ""))
    config.CATALOGUE.mkdir(parents=True, exist_ok=True)
    out_csv = config.CATALOGUE / f"{args.name}_scenes.csv"
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("wrote", out_csv)

    # Viewer list: one GCOV per acquisition (prefer production 'P' runs, full frames)
    best = {}
    for r in rows:
        if r["level"] != "GCOV" or not r["browse_png"]:
            continue
        key = (r["start_time"][:16], r["track"], r["frame"])
        score = (r["crid"].startswith("P"), r["coverage"] == "Full", r["crid"])
        if key not in best or score > best[key][0]:
            best[key] = (score, r)
    scenes = [r for _, r in best.values()]

    # NISAR uses a fixed geocoding grid per track+frame, so every scene on the same
    # track/frame shares one footprint. Older browse KMLs are no longer served, so we
    # read the newest available KML per track/frame and reuse it.
    by_tf = {}
    for r in sorted(scenes, key=lambda r: r["start_time"], reverse=True):
        by_tf.setdefault((r["track"], r["frame"]), []).append(r)

    def tf_bounds(group):
        for r in group[:6]:
            b = kml_bounds(r["browse_png"].replace(".png", ".kml"))
            if b:
                return b
        return None

    with ThreadPoolExecutor(8) as pool:
        tf_b = dict(zip(by_tf.keys(), pool.map(tf_bounds, by_tf.values())))
    bounds = [tf_b.get((r["track"], r["frame"])) for r in scenes]
    view = []
    for r, b in zip(scenes, bounds):
        if b:
            view.append({k: r[k] for k in ("date", "direction", "track", "frame", "coverage", "file_id", "browse_png")}
                        | {"bounds": b})
    view.sort(key=lambda r: r["date"])
    out_json = config.APP / "scenes.json"
    payload = json.dumps({"aoi": args.name, "bbox": list(args.bbox), "scenes": view}, indent=1)
    out_json.write_text(payload)
    # Same data as a script so app/index.html also works when opened straight from disk
    (config.APP / "scenes.js").write_text("window.SCENES = " + payload + ";\n")
    print(f"wrote {out_json} ({len(view)} scenes)")


if __name__ == "__main__":
    main()
