#!/usr/bin/env python3
"""Find NISAR L2 GCOV granules over the study area and list the ones we do not have yet.

Source: NASA CMR (public, no login): https://cmr.earthdata.nasa.gov/search/granules.json
Collections (resolved by short name at run time, constants are the fallback):
  NISAR_L2_GCOV_V1              C3622241360-ASF  (validated)
  NISAR_L2_GCOV_PROVISIONAL_V1  C2854338529-ASF  (provisional)

Classification by footprint (granule polygon vs our boxes, see tools/pipeline/common.py):
  SEA    footprint covers >= 20 % of the sea box AND frequency A has VV (L-band VV/VH modes)
  COAST  footprint covers >= 50 % of the delta box AND frequency A has HH (HH/HV modes)
One granule gives at most one role (SEA wins when both match). Duplicates of one pass (same cycle/track/frame:
validated vs provisional, PR vs UR, several modes) collapse to one granule: validated > PR > needed pols >
coverage > smaller file. Then one scene per (role, date, track): the frame with the best coverage.
A scene is NEW when its (role, date, track) is not in data/h5/catalog.json. A provisional scene whose pass is
now available as validated is reported as an UPGRADE (re-ingest replaces the file).

Usage:
  python tools/pipeline/discover.py                      # table of everything found + the NEW list
  python tools/pipeline/discover.py --json new.json      # write NEW (and upgrades) as JSON for ingest.py
  python tools/pipeline/discover.py --all                # show all scenes, not only new ones
Only tracks configured for a role in config/areas.json ("tracks") are ingested. Other qualifying tracks are LISTED under
"other tracks seen, not ingested (add to config/areas.json to include)" and never become NEW. --tracks overrides the config.
Exit code 0 always when the search worked (also with no new scenes); 2 when CMR is unreachable.
"""
import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (AREAS_ENV, CATALOG, GRANULE_RE, area, freq_a_pols, load_json, role_box, scene_key,  # noqa: E402
                    search_box)

CMR = "https://cmr.earthdata.nasa.gov/search"
SHORT_NAMES = {"NISAR_L2_GCOV_V1": "VALIDATED", "NISAR_L2_GCOV_PROVISIONAL_V1": "PROVISIONAL"}
FALLBACK_IDS = {"NISAR_L2_GCOV_V1": "C3622241360-ASF", "NISAR_L2_GCOV_PROVISIONAL_V1": "C2854338529-ASF"}
# Boxes, pols and min_cover per role come from config/areas.json (see common.area()).
# T48 F80 (the eye-pass strip, 17 s long) covers 21-23 % of the sea box, so SEA's min_cover is low (0.2);
# neighbouring frames of the same pass sit at 17-19 %, the margin is real but small.


def http_json(url, retries=3):
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "spacebros-nisar-pipeline"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last = e
            if isinstance(e, urllib.error.HTTPError) and 400 <= e.code < 500:
                break
    raise ConnectionError(f"CMR request failed: {last}")


def collection_ids():
    ids = {}
    for sn in SHORT_NAMES:
        try:
            d = http_json(f"{CMR}/collections.json?short_name={sn}&page_size=5")
            ents = d["feed"]["entry"]
            ids[sn] = ents[0]["id"] if ents else FALLBACK_IDS[sn]
        except ConnectionError:
            raise
        except Exception:  # noqa: BLE001
            ids[sn] = FALLBACK_IDS[sn]
    return ids


def search_granules(cid, since, until, ar):
    w, s, e, n = search_box(ar)   # union of the area's boxes (the sea box contains the delta box)
    out, page = [], 1
    while True:
        q = urllib.parse.urlencode({"collection_concept_id": cid, "bounding_box": f"{w},{s},{e},{n}",
                                    "temporal": f"{since}T00:00:00Z,{until}", "page_size": 500,
                                    "page_num": page, "sort_key": "start_date"})
        ents = http_json(f"{CMR}/granules.json?{q}")["feed"]["entry"]
        out += ents
        if len(ents) < 500:
            return out
        page += 1


def polygon_rings(entry):
    rings = []
    for poly in entry.get("polygons") or []:
        outer = poly[0].split()
        pts = [(float(outer[i + 1]), float(outer[i])) for i in range(0, len(outer) - 1, 2)]   # (lon, lat)
        rings.append(pts)
    for box in entry.get("boxes") or []:
        s, w, n, e = [float(v) for v in box[0].split()] if isinstance(box, list) else [float(v) for v in box.split()]
        rings.append([(w, s), (e, s), (e, n), (w, n)])
    return rings


def inside(ring, px, py):
    """Vectorised ray casting; ring = [(x, y)...]."""
    import math
    res = []
    for x, y in zip(px, py):
        c, j = False, len(ring) - 1
        for i in range(len(ring)):
            xi, yi = ring[i]
            xj, yj = ring[j]
            if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-300) + xi:
                c = not c
            j = i
        res.append(c)
    return res


def coverage(rings, box, n=40):
    """Fraction of the box covered by the footprint (n x n sample points)."""
    w, s, e, nn = box
    xs = [w + (e - w) * (i + 0.5) / n for i in range(n) for _ in range(n)]
    ys = [s + (nn - s) * (j + 0.5) / n for _ in range(n) for j in range(n)]
    hit = [False] * len(xs)
    for ring in rings:
        for k, v in enumerate(inside(ring, xs, ys)):
            hit[k] = hit[k] or v
    return sum(hit) / len(hit)


def parse(entry, status, short_name, ar):
    gid = entry["producer_granule_id"] if "producer_granule_id" in entry else entry["title"]
    m = GRANULE_RE.match(gid)
    if not m:
        return None
    pols = freq_a_pols(m["pols"])
    if not pols:
        return None
    href = next((link["href"] for link in entry.get("links", [])
                 if link.get("rel", "").endswith("/data#") and link["href"].startswith("https://")
                 and link["href"].endswith(".h5")), None)
    if not href:
        return None
    rings = polygon_rings(entry)
    cov = {r: coverage(rings, role_box(ar, r)) for r in ar["boxes"]}
    return {"granule": gid, "url": href, "status": status, "collection": short_name, "kind": m["kind"],
            "cycle": int(m["cycle"]), "track": int(m["track"]), "frame": int(m["frame"]),
            "direction": m["dir"], "mode": m["mode"], "pol_code": m["pols"], "pols": pols,
            "start_utc": entry["time_start"][:19] + "Z", "end_utc": entry["time_end"][:19] + "Z",
            "date": entry["time_start"][:10], "size_mb": round(float(entry.get("granule_size", 0)), 1),
            "production_utc": (entry.get("production_date_time") or "")[:19] + "Z" if entry.get("production_date_time") else None,
            "available_utc": (entry.get("updated") or "")[:19] + "Z" if entry.get("updated") else None,
            "cover_coast": round(cov.get("COAST", 0.0), 3), "cover_sea": round(cov.get("SEA", 0.0), 3)}


def classify(g, ar):
    """SEA is tested first (SEA wins when both match); a role matches when its first configured pol is in frequency A
    and the footprint covers >= min_cover of that role's box."""
    for role in ("SEA", "COAST"):
        cfg = ar["roles"].get(role)
        if cfg and cfg["pols"][0] in g["pols"] and g["cover_" + role.lower()] >= cfg["min_cover"]:
            return role
    return None


def rank(g):
    cov = g["cover_sea"] if g["role"] == "SEA" else g["cover_coast"]
    return (g["status"] == "VALIDATED", g["kind"] == "PR", cov, -g["size_mb"])


def select(granules, ar):
    """Classify, collapse duplicates of one pass, keep one granule per (role, date, track)."""
    by_pass = {}
    for g in granules:
        role = classify(g, ar)
        if not role:
            continue
        g["role"] = role
        by_pass.setdefault((g["cycle"], g["track"], g["frame"], g["direction"], role), []).append(g)
    per_pass = []
    for grp in by_pass.values():
        grp.sort(key=rank, reverse=True)
        best = grp[0]
        best["alternatives"] = [f"{x['status'][:4]} {x['kind']} {x['mode']}_{x['pol_code']}" for x in grp[1:]]
        per_pass.append(best)
    by_scene = {}
    for g in per_pass:
        by_scene.setdefault(scene_key(g["role"], g["date"], g["track"]), []).append(g)
    scenes = []
    for key, grp in by_scene.items():
        grp.sort(key=lambda g: (g["cover_sea"] if g["role"] == "SEA" else g["cover_coast"], g["status"] == "VALIDATED"),
                 reverse=True)
        best = dict(grp[0])
        best["scene_key"] = key
        best["other_frames"] = [x["frame"] for x in grp[1:]]
        scenes.append(best)
    scenes.sort(key=lambda g: (g["start_utc"], g["role"]))
    return scenes


def configured_tracks(ar):
    """{role: {track numbers}} from config/areas.json (`tracks`). Only these are ingested; other tracks are listed, not ingested."""
    return {role: {int(t["track"]) for t in lst} for role, lst in (ar.get("tracks") or {}).items()}


def compare(scenes, catalog_path, tracks=None, ar=None):
    """tracks (explicit --tracks) overrides the config; otherwise a scene is ingested only if its track is configured for its role."""
    cat = load_json(catalog_path, {"scenes": []})
    have = {}
    for e in cat.get("scenes", []):
        have[scene_key(e["role"], e["date"], e["track"])] = e
    conf = configured_tracks(ar) if (ar and not tracks) else None
    new, upgrades, known, other = [], [], [], []
    for s in scenes:
        if tracks:
            ok = s["track"] in tracks
        elif conf is not None:
            ok = s["track"] in conf.get(s["role"], set())
        else:
            ok = True
        if not ok:
            other.append(s)
            continue
        e = have.get(s["scene_key"])
        if e is None:
            new.append(s)
        elif e.get("product_status") == "PROVISIONAL" and s["status"] == "VALIDATED":
            s["replaces"] = e["file"]
            upgrades.append(s)
        else:
            known.append(s)
    return new, upgrades, known, other


def fmt(s):
    cov = s["cover_sea"] if s["role"] == "SEA" else s["cover_coast"]
    alt = f"  (also: {', '.join(s['alternatives'])})" if s.get("alternatives") else ""
    return (f"{s['role']:5s} {s['start_utc']} T{s['track']:03d} F{s['frame']:03d} {s['direction']} "
            f"{s['status'][:4]} {s['kind']} {s['mode']}_{s['pol_code']} cover {cov:.2f} {s['size_mb']/1000:.1f} GB "
            f"{s['granule'][:60]}{alt}")


def run(since=None, until=None, catalog=CATALOG, tracks=None, area_id=None):
    ar = area(area_id)
    since = since or ar["_defaults"]["search_since"]
    until = until or dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ids = collection_ids()
    raw = []
    for sn, cid in ids.items():
        for e in search_granules(cid, since, until, ar):
            g = parse(e, SHORT_NAMES[sn], sn, ar)
            if g:
                raw.append(g)
    scenes = select(raw, ar)
    new, upgrades, known, other = compare(scenes, catalog, tracks, ar)
    return {"collections": ids, "n_granules": len(raw), "scenes": scenes, "new": new, "upgrades": upgrades,
            "known": known, "other_tracks": other}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--since", default=None, help="default: config defaults.search_since")
    ap.add_argument("--area", default=None, help="area id in config/areas.json (default: default_area)")
    ap.add_argument("--config", default=None, help=f"areas config file (default config/areas.json; env {AREAS_ENV})")
    ap.add_argument("--until", default=None, help="default: now (UTC)")
    ap.add_argument("--catalog", default=str(CATALOG))
    ap.add_argument("--tracks", default=None, help="comma list of tracks to keep, e.g. 48,55 (default: all)")
    ap.add_argument("--json", help="write {new, upgrades} to this file for ingest.py")
    ap.add_argument("--all", action="store_true", help="also print scenes we already have")
    a = ap.parse_args()
    if a.config:
        os.environ[AREAS_ENV] = a.config
    try:
        tracks = {int(t) for t in a.tracks.split(',')} if a.tracks else None
        r = run(a.since, a.until, a.catalog, tracks, a.area)
    except ConnectionError as e:
        print(f"CMR unreachable: {e}", file=sys.stderr)
        return 2
    print(f"CMR collections {r['collections']}; {r['n_granules']} usable granules intersect the boxes since {a.since or area(a.area)['_defaults']['search_since']}")
    if a.all:
        print(f"\nAlready in catalog ({len(r['known'])}):")
        for s in r["known"]:
            print("  " + fmt(s))
    print(f"\nNEW scenes ({len(r['new'])}):")
    for s in r["new"]:
        print("  " + fmt(s))
    if r["other_tracks"]:
        print(f"\nOther tracks seen, not ingested ({len(r['other_tracks'])}; add to config/areas.json to include):")
        for s in r["other_tracks"]:
            print("  " + fmt(s))
    if r["upgrades"]:
        print(f"\nUPGRADES provisional -> validated ({len(r['upgrades'])}):")
        for s in r["upgrades"]:
            print("  " + fmt(s) + f"  replaces {s['replaces']}")
    if a.json:
        with open(a.json, "w") as f:
            json.dump({"found_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                       "new": r["new"], "upgrades": r["upgrades"]}, f, indent=1)
        print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
