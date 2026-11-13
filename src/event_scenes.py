"""Catalogue + download public NISAR quick-looks for an event window over a region
(e.g. a cyclone over the Bay of Bengal). No login needed.

Writes:
  data/events/<name>/scenes.csv        every GCOV acquisition in the window
  data/events/<name>/scenes.json       same + bounds, for a viewer
  data/events/<name>/browse/*.png      full quick-look per acquisition (--download)

Usage:
  python src/event_scenes.py --name arnab_2026 --bbox 80 10 93 19 \
      --start 2026-10-12 --end 2026-11-06 --download
"""
import argparse
import csv
import datetime as dt
import json
import os
from concurrent.futures import ThreadPoolExecutor

os.environ.setdefault("TZ", "UTC")  # asf_search date parsing breaks on some local TZ names

import asf_search as asf
import requests

import config
from nisar_search import crid, kml_bounds


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--bbox", nargs=4, type=float, required=True, metavar=("W", "S", "E", "N"))
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--download", action="store_true")
    args = ap.parse_args()

    res = asf.search(dataset="NISAR", intersectsWith=config.aoi_wkt(args.bbox), processingLevel="GCOV",
                     start=dt.datetime.fromisoformat(args.start), end=dt.datetime.fromisoformat(args.end),
                     maxResults=3000)
    best = {}
    for p in res:
        pr = p.properties
        browse = [b for b in pr.get("browse") or [] if b.endswith("_LATLON.png")]
        if not browse:
            continue
        g = p.geometry["coordinates"][0]
        row = {
            "start_time": pr["startTime"], "date": pr["startTime"][:10],
            "direction": pr["flightDirection"], "track": pr["pathNumber"], "frame": pr["frameNumber"],
            "coverage": pr.get("frameCoverage"), "crid": crid(pr["fileID"]),
            "center_lat": round(sum(c[1] for c in g) / len(g), 3),
            "center_lon": round(sum(c[0] for c in g) / len(g), 3),
            "size_gb": round(sum(v["bytes"] for v in pr["bytes"].values()) / 1e9, 2),
            "file_id": pr["fileID"], "h5_url": pr["url"], "browse_png": browse[0],
        }
        key = (row["start_time"][:16], row["track"], row["frame"])
        score = (row["crid"].startswith("P"), row["coverage"] == "Full", row["crid"])
        if key not in best or score > best[key][0]:
            best[key] = (score, row)
    rows = sorted((r for _, r in best.values()), key=lambda r: r["start_time"])
    print(f"{len(rows)} acquisitions")

    out = config.DATA / "events" / args.name
    (out / "browse").mkdir(parents=True, exist_ok=True)
    with open(out / "scenes.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    # bounds: one KML per track/frame (fixed grid), newest first
    tf = {}
    for r in reversed(rows):
        tf.setdefault((r["track"], r["frame"]), []).append(r)

    def tf_bounds(group):
        for r in group[:6]:
            b = kml_bounds(r["browse_png"].replace(".png", ".kml"))
            if b:
                return b
        return None

    with ThreadPoolExecutor(8) as pool:
        tfb = dict(zip(tf, pool.map(tf_bounds, tf.values())))
    for r in rows:
        r["bounds"] = tfb.get((r["track"], r["frame"]))
        r["png"] = f"browse/{r['start_time'][:16].replace(':', '')}_T{r['track']}_F{r['frame']}.png"
    (out / "scenes.json").write_text(json.dumps({"name": args.name, "bbox": args.bbox, "scenes": rows}, indent=1))

    if args.download:
        def get(r):
            p = out / r["png"]
            if not p.exists():
                p.write_bytes(requests.get(r["browse_png"], timeout=180).content)
        with ThreadPoolExecutor(6) as pool:
            list(pool.map(get, rows))
    print("wrote", out)


if __name__ == "__main__":
    main()
