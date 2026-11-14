#!/usr/bin/env python3
"""(Re)build data/h5/catalog.json from the attributes of every data/h5/*.h5 (schema spacebros-subset-v1).

One entry per subset file: file, scene_id, band, role, date, track, frame, direction, product_status,
source_granule, posting_m, size_bytes, sha256, bounds_latlon, plus start_utc, pols, multilook, shape, epsg,
source_collection. The H5 attributes are the source of truth; the catalog is a derived index that the other
pipeline steps and the dashboard read without opening 50 MB files.

Timestamps (added W3-H phase 2):
  cataloged_utc   first time this scene entered the catalog; preserved on every rebuild (matched by scene_id). Scenes that
                  were already in a catalog without this field get that catalog's generated_utc (a lower bound: they may
                  have been held earlier).
  produced_utc / available_utc   NASA's production time and CMR "updated" (available) time of the source granule, when
                  known: from H5 root attrs production_utc / available_utc if present, else from the sidecar
                  data/h5/granule_times.json {source_granule: {production_utc, available_utc}} written by ingest.py
                  (CMR fields). Omitted when unknown.
`generated_utc` only changes when the content changes, so a run with nothing new leaves the file byte-identical.

Usage: python tools/pipeline/catalog.py [--h5-dir data/h5] [--out data/h5/catalog.json] [--check]
  --check  exit 1 if the catalog on disk differs from what the H5 files say (no write)
Deps: h5py.
"""
import argparse
import datetime as dt
import hashlib
import sys
from pathlib import Path

import h5py

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CATALOG, CATALOG_SCHEMA, H5_DIR, ROOT, dump_json, load_json  # noqa: E402


def py(v):
    if isinstance(v, bytes):
        return v.decode()
    if hasattr(v, "tolist"):
        return v.tolist()
    return v


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


TIMES_SIDECAR = H5_DIR / "granule_times.json"


def entry(path, times=None):
    with h5py.File(path, "r") as h:
        a = {k: py(v) for k, v in h.attrs.items()}
        if a.get("schema") != "spacebros-subset-v1":
            raise ValueError(f"{path.name}: unknown schema {a.get('schema')!r}")
        pols = list(h["backscatter"].keys())
        shape = list(h["backscatter"][pols[0]].shape)
    t = (times or {}).get(a["source_granule"], {})
    out = {
        "file": f"data/h5/{path.name}",
        "scene_id": a["scene_id"],
        "band": a["band"],
        "role": a["role"],
        "date": a["start_utc"][:10],
        "start_utc": a["start_utc"],
        "track": int(a["track"]),
        "frame": int(a["frame"]),
        "direction": a["direction"],
        "product_status": a["product_status"],
        "source_granule": a["source_granule"],
        "source_collection": a.get("source_collection"),
        "pols": pols,
        "posting_m": float(a["posting_m"]),
        "multilook": int(a.get("multilook", 1)),
        "shape": shape,
        "epsg": int(a["epsg"]),
        "size_bytes": path.stat().st_size,
        "sha256": sha256(path),
        "bounds_latlon": [[round(x, 6) for x in row] for row in a["bounds_latlon"]],
    }
    for key in ("produced_utc", "available_utc"):
        v = a.get(key) or t.get(key)
        if v:
            out[key] = str(v)
    return out


def build(h5_dir, old=None):
    """Scene list. ``old`` = the previous catalog dict: its cataloged_utc values are carried over."""
    times = load_json(TIMES_SIDECAR, {}) or {}
    scenes = [entry(p, times) for p in sorted(Path(h5_dir).glob("*.h5"))]
    scenes.sort(key=lambda e: (e["date"], e["band"], e["role"], e["track"]))
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    prev = {s["scene_id"]: s for s in (old or {}).get("scenes", [])}
    fallback = (old or {}).get("generated_utc")
    for e in scenes:
        p = prev.get(e["scene_id"])
        if p is not None:
            e["cataloged_utc"] = p.get("cataloged_utc") or fallback or now
            # keep a production/available time learned earlier if the sidecar no longer has it
            for key in ("produced_utc", "available_utc"):
                if key not in e and p.get(key):
                    e[key] = p[key]
        else:
            e["cataloged_utc"] = now
    return scenes


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--h5-dir", default=str(H5_DIR))
    ap.add_argument("--out", default=str(CATALOG))
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    old = load_json(a.out, {})
    scenes = build(a.h5_dir, old)
    same = old.get("scenes") == scenes
    if a.check:
        print("catalog up to date" if same else "catalog DIFFERS from the H5 files")
        return 0 if same else 1
    if same:
        print(f"{a.out}: unchanged ({len(scenes)} scenes)")
        return 0
    dump_json({"schema": CATALOG_SCHEMA,
               "generated_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "scenes": scenes}, a.out)
    total = sum(e["size_bytes"] for e in scenes) / 1e6
    print(f"wrote {a.out}: {len(scenes)} scenes, {total:.0f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
