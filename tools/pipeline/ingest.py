#!/usr/bin/env python3
"""Turn newly discovered NISAR scenes into study-box H5 subsets in data/h5/ and refresh data/h5/catalog.json.

For every scene from discover.py (run in-process, or read from `--from new.json`):
  1. stream-subset the granule with src/fetch/subset_h5.py (HTTP range requests, only the box window is read,
     nothing large touches the disk): COAST at 20 m (2x2 multilook of the 10 m grid), SEA at 100 m;
  2. write into a temp dir first; REFUSE (and discard) any subset > 90 MB (GitHub's hard limit is 100 MB);
  3. move it into data/h5/ (an UPGRADE provisional -> validated replaces the same file name);
  4. rebuild data/h5/catalog.json (tools/pipeline/catalog.py).
Login: env EARTHDATA_TOKEN (Earthdata "user token" from urs.earthdata.nasa.gov, used as a bearer token), else
~/.netrc through earthaccess. The token is never printed.

Usage:
  python tools/pipeline/ingest.py --dry-run                 # discover + show what would be run, download nothing
  python tools/pipeline/ingest.py                           # discover + ingest every NEW scene (+ upgrades)
  python tools/pipeline/ingest.py --from new.json --max 2   # use a saved discover.py --json list
  python tools/pipeline/ingest.py --local <file.h5> --role COAST [--band S] [--scene-id S_COAST_20261016_T055]
                                  [--status PROVISIONAL] [--granule <id>]   # manual / S-band file on disk
Exit 0 = ok (also when nothing is new), 1 = a scene failed, 2 = CMR unreachable / no login.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import catalog as catalog_mod  # noqa: E402
import discover  # noqa: E402
from common import CATALOG, H5_DIR, MAX_SUBSET_BYTES, POSTING_M, ROOT, load_json  # noqa: E402

SUBSET = ROOT / "src" / "fetch" / "subset_h5.py"


def have_login():
    return bool(os.environ.get("EARTHDATA_TOKEN")) or (Path.home() / ".netrc").exists()


def scene_id_of(s):
    return f"L_{s['role']}_{s['date'].replace('-', '')}_T{s['track']:03d}"


def subset_cmd(py, src, scene_id, role, outdir, status=None, granule=None, collection=None, band=None, posting=None):
    cmd = [py, str(SUBSET), "--scene", scene_id, "--role", role, "--src", src, "--out", str(outdir),
           "--posting", str(posting or POSTING_M[role]), "--no-log"]
    for flag, val in (("--status", status), ("--granule", granule), ("--collection", collection), ("--band", band)):
        if val:
            cmd += [flag, val]
    return cmd


def run_subset(cmd, label):
    """Run subset_h5.py into a temp dir; return the produced file or None (error / too big)."""
    tmp = Path(cmd[cmd.index("--out") + 1])
    r = subprocess.run(cmd, text=True, capture_output=True)
    tail = "\n".join((r.stdout + r.stderr).strip().splitlines()[-6:])
    token = os.environ.get("EARTHDATA_TOKEN")
    if token:
        tail = tail.replace(token, "***")
    if r.returncode != 0:
        print(f"  FAILED {label}:\n{tail}")
        return None
    files = sorted(tmp.glob("*.h5"))
    if len(files) != 1:
        print(f"  FAILED {label}: expected 1 output file, found {[f.name for f in files]}")
        return None
    f = files[0]
    if f.stat().st_size > MAX_SUBSET_BYTES:
        print(f"  REFUSED {label}: {f.name} is {f.stat().st_size / 1e6:.0f} MB > {MAX_SUBSET_BYTES / 1e6:.0f} MB limit "
              f"(not kept; use a larger --posting)")
        return None
    print(tail.splitlines()[-1] if tail else "", f"-> {f.name} {f.stat().st_size / 1e6:.1f} MB")
    return f


def install(f):
    dest = H5_DIR / f.name
    H5_DIR.mkdir(parents=True, exist_ok=True)
    shutil.move(str(f), str(dest))   # replaces on an upgrade
    return dest


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="show the subset commands, download nothing, write nothing")
    ap.add_argument("--from", dest="from_json", help="scene list written by discover.py --json")
    ap.add_argument("--max", type=int, default=6, help="at most this many scenes per run (default 6)")
    ap.add_argument("--no-upgrades", action="store_true", help="ignore provisional -> validated upgrades")
    ap.add_argument("--tracks", default=None, help="restrict to these tracks, e.g. 48,55")
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--local", help="local H5 (S-band or manual download) to subset instead of discovering")
    ap.add_argument("--role", choices=["COAST", "SEA"], help="with --local")
    ap.add_argument("--band", choices=["L", "S"], help="with --local (default: detected)")
    ap.add_argument("--scene-id", help="with --local (default: LOCAL_<file stem>)")
    ap.add_argument("--status", choices=["PROVISIONAL", "VALIDATED"], help="with --local")
    ap.add_argument("--granule", help="with --local: source granule id (default: file stem)")
    ap.add_argument("--posting", type=float, help="with --local: output posting in m (default 20 COAST / 100 SEA)")
    a = ap.parse_args()

    jobs = []   # (label, cmd-builder args)
    times = {}  # source granule -> CMR production / available time (goes to data/h5/granule_times.json)
    if a.local:
        if not a.role:
            ap.error("--local needs --role COAST|SEA")
        src = str(Path(a.local).resolve())
        sid = a.scene_id or f"LOCAL_{Path(src).stem}"
        jobs.append((sid, dict(src=src, scene_id=sid, role=a.role, status=a.status, granule=a.granule,
                               band=a.band, posting=a.posting)))
    else:
        if a.from_json:
            d = load_json(a.from_json, {})
            todo = d.get("new", []) + ([] if a.no_upgrades else d.get("upgrades", []))
        else:
            try:
                tracks = {int(t) for t in a.tracks.split(",")} if a.tracks else None
                r = discover.run(tracks=tracks)
            except ConnectionError as e:
                print(f"CMR unreachable: {e}", file=sys.stderr)
                return 2
            todo = r["new"] + ([] if a.no_upgrades else r["upgrades"])
        if not todo:
            print("No new NISAR scenes. Nothing to do.")
            return 0
        if len(todo) > a.max:
            print(f"{len(todo)} scenes found, taking the first {a.max} (oldest first); the rest next run.")
            todo = todo[:a.max]
        for s in todo:
            if s.get("production_utc") or s.get("available_utc"):
                times[s["granule"]] = {k: s[k] for k in ("production_utc", "available_utc") if s.get(k)}
            jobs.append((f"{scene_id_of(s)} {s['status']} {s['granule'][:48]}",
                         dict(src=s["url"], scene_id=scene_id_of(s), role=s["role"], status=s["status"],
                              granule=s["granule"], collection=s["collection"], band="L")))

    if not a.dry_run and not a.local and not have_login():
        print("No Earthdata login: set env EARTHDATA_TOKEN (urs.earthdata.nasa.gov -> Generate Token) or create ~/.netrc.",
              file=sys.stderr)
        return 2

    failed, done = 0, 0
    for label, kw in jobs:
        print(f"\n== {label}")
        tmp = Path(tempfile.mkdtemp(prefix="nisar_ingest_"))
        try:
            cmd = subset_cmd(a.python, outdir=tmp, **kw)
            shown = [("<url>" if c.startswith("http") else c) for c in cmd]
            print("  " + " ".join(shown))
            if a.dry_run:
                print(f"  [dry-run] would stream {kw['src'][:100]}... -> temp dir -> data/h5/ "
                      f"(size limit {MAX_SUBSET_BYTES // 1000000} MB)")
                continue
            f = run_subset(cmd, label)
            if f is None:
                failed += 1
                continue
            print(f"  installed {install(f).relative_to(ROOT)}")
            done += 1
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    if a.dry_run:
        print("\n[dry-run] nothing downloaded, catalog untouched.")
        return 0
    if done:
        if times:
            side = catalog_mod.TIMES_SIDECAR
            have = load_json(side, {}) or {}
            have.update(times)
            catalog_mod.dump_json(have, side)
        scenes = catalog_mod.build(H5_DIR, catalog_mod.load_json(CATALOG, {}))
        catalog_mod.dump_json({"schema": catalog_mod.CATALOG_SCHEMA,
                               "generated_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
                               .strftime("%Y-%m-%dT%H:%M:%SZ"), "scenes": scenes}, CATALOG)
        print(f"\ncatalog rebuilt: {len(scenes)} scenes")
    print(f"\ningested {done}, failed {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
