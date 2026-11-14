#!/usr/bin/env python3
"""Download the full NISAR L-band GCOV HDF5 (.h5) granules for the Cyclone Arnab study.

Picks every row of data/reference/scene_manifest_full.csv that has a `role` of L_SEA_* / L_COAST_*
(the 8 scenes the app uses, about 27 GB in total; the 3 Oct quad-pol sea scene is 7.5 GB of that).
Saves to data/raw/nisar_l_h5/ (git-ignored), resumes partial files, checks the MD5 from the manifest.

Auth: NASA Earthdata login through a netrc file (urs.earthdata.nasa.gov). This script never reads or
prints the credentials, it only hands the file path to curl. Netrc lookup order:
  --netrc-file PATH, then $NETRC, then ~/.netrc, then ~/Documents/nsa/.netrc

Usage (from 05_Code/spacebros-nisar):
  python3 src/fetch/download_l_band_h5.py --list          # show what would be downloaded
  python3 src/fetch/download_l_band_h5.py                 # download all 8
  python3 src/fetch/download_l_band_h5.py --role L_SEA_EYE_1027   # just one
"""
import argparse, csv, hashlib, os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "data/reference/scene_manifest_full.csv"
DEST = ROOT / "data/raw/nisar_l_h5"


def find_netrc(arg):
    for c in [arg, os.environ.get("NETRC"), Path.home() / ".netrc", Path.home() / "Documents/nsa/.netrc"]:
        if c and Path(c).expanduser().is_file():
            return str(Path(c).expanduser())
    sys.exit("No netrc file found. Pass --netrc-file PATH (needs a urs.earthdata.nasa.gov entry).")


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--role", action="append", help="only these roles (repeatable)")
    ap.add_argument("--netrc-file")
    a = ap.parse_args()
    rows = [r for r in csv.DictReader(open(MANIFEST))
            if r["role"].startswith(("L_SEA_", "L_COAST_")) and "fallback" not in r["role"] and "T149" not in r["role"]
            and (not a.role or r["role"] in a.role)]
    total = sum(int(r["size_bytes"]) for r in rows)
    for r in rows:
        print(f"{r['role']:18s} {r['acquisition_utc'][:16]} T{r['track']} {int(r['size_bytes'])/1e9:5.2f} GB")
    print(f"total {total/1e9:.1f} GB -> {DEST}")
    if a.list:
        return
    netrc = find_netrc(a.netrc_file)
    DEST.mkdir(parents=True, exist_ok=True)
    bad = []
    for r in rows:
        out = DEST / (r["granule_id"] + ".h5")
        want = int(r["size_bytes"])
        if out.exists() and out.stat().st_size == want and (not r["md5"] or md5(out) == r["md5"]):
            print("have", out.name); continue
        print("downloading", out.name, flush=True)
        subprocess.run(["curl", "-L", "--fail", "-C", "-", "--retry", "3", "--netrc-file", netrc,
                        "--location-trusted", "-c", "/dev/null", "-b", "/dev/null",
                        "-o", str(out), r["download_url"]], check=False)
        ok = out.exists() and out.stat().st_size == want and (not r["md5"] or md5(out) == r["md5"])
        print("  OK" if ok else "  FAILED size/md5 check", flush=True)
        if not ok:
            bad.append(r["role"])
    print("done." if not bad else f"failed: {bad} (re-run to resume)")


if __name__ == "__main__":
    main()
