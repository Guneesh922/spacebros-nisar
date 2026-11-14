#!/usr/bin/env python3
"""Search and download NISAR S-band products from ISRO Bhoonidhi (STAC API).

Spec: https://bhoonidhi.nrsc.gov.in/bhoonidhi-api/  (API host: bhoonidhi-api.nrsc.gov.in)
Auth: your normal Bhoonidhi userId + password. The password is typed at a prompt
(or read from BHOONIDHI_USER / BHOONIDHI_PASS env vars). It is never written to disk.
Limits per the spec: auth 20/hour/IP, search 3/s, download 2/min and 5 concurrent.

Usage (run in your own terminal):
  python3 src/fetch/bhoonidhi_s_band.py search
      -> writes data/reference/nisar_s_candidates.csv (what sources.yaml S_GCOV_DELTA expects)
  python3 src/fetch/bhoonidhi_s_band.py download --collection NISAR_SSAR_GCOV --id <ITEM_ID> [--id ...]
      -> saves to data/raw/nisar_s/ (git-ignored)
Options for search: --bbox W,S,E,N  --datetime START/END  --collections A,B
If the API answers 401/403 for a correct password, email the Bhoonidhi support
address on the spec page asking for API access (give userId, your IP, endpoint).
"""
import argparse, csv, getpass, http.client, json, os, re, sys, time
import urllib.request, urllib.error, urllib.parse

API = "https://bhoonidhi-api.nrsc.gov.in"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
# covers the delta box and the sea (T48) box of the Arnab event
DEFAULT_BBOX = "80.5,15.0,85.0,18.5"
DEFAULT_DT = "2026-10-01T00:00:00Z/2026-11-14T23:59:59Z"
DEFAULT_COLLS = "NISAR_SSAR_GCOV,NISAR_SSAR_GSLC,NISAR_SSAR_RSLC"


def call(method, path, body=None, token=None, raw=False):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API + path, data=data, headers=headers, method=method)
    try:
        r = urllib.request.urlopen(req, timeout=120)
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code} on {method} {path}: {e.read()[:500].decode(errors='replace')}")
    return r if raw else json.load(r)


def login():
    user = os.environ.get("BHOONIDHI_USER") or input("Bhoonidhi userId: ").strip()
    pw = os.environ.get("BHOONIDHI_PASS") or getpass.getpass("Bhoonidhi password: ")
    t = call("POST", "/auth/token", {"userId": user, "password": pw, "grant_type": "password"})
    return t["access_token"]


def search(a):
    token = login()
    west, south, east, north = [float(x) for x in a.bbox.split(",")]
    rows, seen = [], set()
    for coll in a.collections.split(","):
        body = {"collections": [coll], "datetime": a.datetime,
                "bbox": [west, south, east, north], "limit": 500}
        while True:
            res = call("POST", "/data/search", body, token)
            for f in res.get("features", []):
                if f["id"] in seen:
                    continue
                seen.add(f["id"])
                p = f.get("properties", {}) or {}
                rows.append({"collection": f.get("collection", coll), "id": f["id"],
                             "datetime": p.get("datetime", ""), "online": p.get("Online", ""),
                             "properties": json.dumps(p)})
            nxt = [l for l in res.get("links", []) if l.get("rel") == "next"]
            if not nxt:
                break
            body = nxt[0].get("body") or {**body, "token": nxt[0].get("href", "").split("token=")[-1]}
            time.sleep(0.4)  # stay under 3 searches/second
        print(f"{coll}: {sum(r['collection'] == coll for r in rows)} items")
    out = os.path.join(ROOT, "data", "reference", "nisar_s_candidates.csv")
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["collection", "id", "datetime", "online", "properties"])
        w.writeheader(); w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {out}")
    if not rows:
        print("0 results: widen --bbox/--datetime, or the S-band scene may not be online yet.")


CHUNK = 1 << 20          # 1 MB per read
PROGRESS_SECS = 10       # progress line interval
MAX_RETRIES = 5          # consecutive connection failures allowed (reset on progress)


def _open_download(collection, item, token, start):
    """Open the download stream from byte `start`.
    Returns (response, None), or (None, 416) when the server says the .part is already complete."""
    path = f"/download?id={item}&collection={collection}"
    headers = {"Authorization": "Bearer " + token}
    if start > 0:
        headers["Range"] = f"bytes={start}-"
    req = urllib.request.Request(API + path, headers=headers, method="GET")
    try:
        return urllib.request.urlopen(req, timeout=120), None
    except urllib.error.HTTPError as e:
        if e.code == 416 and start > 0:
            return None, 416
        sys.exit(f"HTTP {e.code} on GET {path}: {e.read()[:500].decode(errors='replace')}")


def _filename_from_cd(value):
    """Return a safe basename from a Content-Disposition header, or None."""
    m = re.search(r"filename\*\s*=\s*[^']*'[^']*'([^;]+)", value, re.I)
    if m:
        name = urllib.parse.unquote(m.group(1).strip().strip('"'))
    else:
        m = re.search(r'filename\s*=\s*"?([^";]+)"?', value, re.I)
        if not m:
            return None
        name = m.group(1).strip()
    name = os.path.basename(name.replace("\\", "/"))
    return None if name in ("", ".", "..") else name


def _part_size(part):
    return os.path.getsize(part) if os.path.exists(part) else 0


def download_one(collection, item, token, dest):
    default = item + ".h5"
    part = os.path.join(dest, default + ".part")
    name = default                      # final name; Content-Disposition may override it
    failures = 0
    while True:
        start = _part_size(part)
        try:
            r, code = _open_download(collection, item, token, start)
            if code == 416:
                print(f"{item}: server returned 416 at {start/1e6:.1f} MB, so the .part is complete")
                break
            ctype = r.headers.get("Content-Type", "unknown")
            cd = r.headers.get("Content-Disposition")
            fn = _filename_from_cd(cd) if cd else None
            if fn:
                name = fn
            cl = r.headers.get("Content-Length")
            cl_n = int(cl) if cl and cl.isdigit() else None
            if r.status == 206:
                mode = "ab"
                m = re.search(r"bytes (\d+)-\d+/(\d+|\*)", r.headers.get("Content-Range", ""))
                if m and int(m.group(1)) != start:
                    sys.exit(f"{item}: Content-Range starts at {m.group(1)}, expected {start}; refusing to append")
                if m and m.group(2) != "*":
                    total = int(m.group(2))
                else:
                    total = start + cl_n if cl_n is not None else None
            else:
                if start > 0:
                    print(f"WARNING: {item}: server ignored Range (HTTP {r.status}, no range support); restarting .part from zero")
                start, mode = 0, "wb"
                total = cl_n
            pct = f" of {total/1e6:.1f} MB" if total else ""
            print(f"{item}: HTTP {r.status}, content-type {ctype}, starting at {start/1e6:.1f} MB{pct}")
            size, win_bytes, last = start, 0, time.time()
            with r, open(part, mode) as fh:
                while chunk := r.read(CHUNK):
                    fh.write(chunk)
                    size += len(chunk)
                    win_bytes += len(chunk)
                    failures = 0
                    now = time.time()
                    if now - last >= PROGRESS_SECS:
                        rate = win_bytes / 1e6 / (now - last)
                        print(f"  {item}: {size/1e6:.1f} MB{pct} at {rate:.2f} MB/s")
                        last, win_bytes = now, 0
            print(f"{item}: transfer finished, {size/1e6:.1f} MB, content-type {ctype}")
            break
        except (urllib.error.URLError, http.client.HTTPException, OSError) as e:
            failures += 1
            if failures > MAX_RETRIES:
                sys.exit(f"{item}: giving up after {MAX_RETRIES} retries ({e}); partial file kept at {part}")
            wait = 2 ** failures
            print(f"{item}: connection error ({e}); retry {failures}/{MAX_RETRIES} in {wait}s from {_part_size(part)/1e6:.1f} MB")
            time.sleep(wait)

    final = os.path.join(dest, name)
    os.replace(part, final)
    print(f"{item}: {os.path.getsize(final)/1e6:.1f} MB -> {final}")


def download(a):
    token = login()
    dest = os.path.join(ROOT, "data", "raw", "nisar_s")
    os.makedirs(dest, exist_ok=True)
    for item in a.id:
        download_one(a.collection, item, token, dest)
        time.sleep(31)  # download limit is 2/min


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search")
    s.add_argument("--bbox", default=DEFAULT_BBOX)
    s.add_argument("--datetime", default=DEFAULT_DT)
    s.add_argument("--collections", default=DEFAULT_COLLS)
    s.set_defaults(fn=search)
    d = sub.add_parser("download")
    d.add_argument("--collection", required=True)
    d.add_argument("--id", action="append", required=True)
    d.set_defaults(fn=download)
    a = ap.parse_args()
    a.fn(a)
