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
  python3 src/fetch/bhoonidhi_s_band.py subset --preset arnab
      -> NO 10 GB download: streams only the study-box chunks with HTTP Range requests and writes the small
         schema-v1 H5 files straight to data/h5/ (S_COAST_20261004_T055.h5 ...). Add --plan first to see how many
         bytes each scene needs without writing anything. Single item: subset --id <ID> --role COAST|SEA
         [--scene-id S_COAST_1004]. Already have the full file from the portal: subset --local <file.h5> --role COAST.
Options for search: --bbox W,S,E,N  --datetime START/END  --collections A,B
If the API answers 401/403 for a correct password, email the Bhoonidhi support
address on the spec page asking for API access (give userId, your IP, endpoint).
"""
import argparse, csv, getpass, http.client, json, os, re, sys, time
import urllib.request, urllib.error, urllib.parse

API = os.environ.get("BHOONIDHI_API", "https://bhoonidhi-api.nrsc.gov.in")   # env override only for local tests
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


class Session:
    """Bhoonidhi login. The password stays in this process's memory only (to renew an expired token); it is never
    printed, logged or written. `token` is likewise never printed."""

    def __init__(self):
        self._user = os.environ.get("BHOONIDHI_USER") or input("Bhoonidhi userId: ").strip()
        self._pw = os.environ.get("BHOONIDHI_PASS") or getpass.getpass("Bhoonidhi password: ")
        self.token = None
        self.renew()

    def renew(self):
        t = call("POST", "/auth/token", {"userId": self._user, "password": self._pw, "grant_type": "password"})
        self.token = t["access_token"]
        return self.token


def login():
    return Session().token


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


# ---------------------------------------------------------------------------------------------------------------
# subset: stream only the study-box chunks of a 10 GB GCOV file over HTTP Range requests
# ---------------------------------------------------------------------------------------------------------------
import io, threading
from concurrent.futures import ThreadPoolExecutor

# role, scene id, item id, collection: the 4 S-band GCOV scenes of Cyclone Arnab (ids from data/reference/nisar_s_candidates.csv)
ARNAB = [
    ("COAST", "S_COAST_1004", "NISAR_S2_PR_GCOV_032_055_A_010_3700_DHNA_A_20261004T000102_20261004T000131_P00500_M_P_I_001"),
    ("COAST", "S_COAST_1016", "NISAR_S2_PR_GCOV_033_055_A_010_3700_DHNA_A_20261016T000103_20261016T000131_P00500_M_P_I_001"),
    ("COAST", "S_COAST_1028", "NISAR_S2_PR_GCOV_034_055_A_010_3700_DHNA_A_20261028T000103_20261028T000131_P00500_M_P_I_001"),
    ("SEA", "S_SEA_1003", "NISAR_S2_PR_GCOV_032_048_D_080_2500_CRNA_A_20261003T130133_20261003T130204_P00500_M_P_I_001"),
]
GCOV_COLLECTION = "NISAR_SSAR_GCOV"


class RangeUnsupported(RuntimeError):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


class RangeFile(io.RawIOBase):
    """Read-only, seekable file object over an HTTPS URL using HTTP Range requests (stdlib only).

    * Blocks of `block` bytes are fetched and kept in an LRU cache (h5py reads many nearby bytes). When a read needs
      several missing blocks they are fetched in parallel (`workers`).
    * Redirects are followed by hand. The Authorization header is sent on every request to the Bhoonidhi host
      (nrsc.gov.in and subdomains) and NOT to any other host (a presigned storage URL needs no token, and the token must not
      leak to a third party). A 401/403/410 re-resolves the redirect once and renews the token.
    * The first request is a probe: anything but 206 Partial Content (or Accept-Ranges: none) raises
      RangeUnsupported, so a server that ignores Range can never make us pull the whole file.
    * Transient errors (timeouts, 5xx, connection resets) are retried with exponential backoff; 429 waits
      Retry-After (default 30 s) and drops to one worker for the rest of the run.
    Counters: .bytes_fetched, .requests."""

    def __init__(self, url, session=None, token=None, block=4 << 20, cache_blocks=96, workers=3,
                 timeout=120, retries=6, quiet=False):
        self.url, self.session, self._token = url, session, token
        self.block, self.cache_blocks, self.workers = block, cache_blocks, workers
        self.timeout, self.retries, self.quiet = timeout, retries, quiet
        self.pos, self.cache, self._final = 0, {}, None
        self.bytes_fetched = self.requests = 0
        self.t0 = time.time()
        self._lock = threading.Lock()
        self._last_print = time.time()
        self._opener = urllib.request.build_opener(_NoRedirect)
        self.size = self._probe()

    # --- plumbing -------------------------------------------------------------------------------------------------
    def _tok(self):
        return self.session.token if self.session else self._token

    auth_hosts = ("nrsc.gov.in", urllib.parse.urlparse(API).hostname or "nrsc.gov.in")   # token goes only to these hosts (+subdomains)

    @classmethod
    def _is_auth_host(cls, host):
        return any(host == h or host.endswith("." + h) for h in cls.auth_hosts)

    def _headers(self, url, start, end):
        h = {"Range": f"bytes={start}-{end}", "User-Agent": "spacebros-nisar"}
        if self._is_auth_host(urllib.parse.urlparse(url).hostname or "") and self._tok():
            h["Authorization"] = "Bearer " + self._tok()
        return h

    def _open(self, start, end):
        """GET the byte range, following redirects by hand. Returns the open response (caller closes it)."""
        url = self._final or self.url
        for _ in range(8):
            req = urllib.request.Request(url, headers=self._headers(url, start, end))
            try:
                return self._opener.open(req, timeout=self.timeout), url
            except urllib.error.HTTPError as e:
                if e.code in (301, 302, 303, 307, 308) and e.headers.get("Location"):
                    url = urllib.parse.urljoin(url, e.headers["Location"])
                    e.close()
                    continue
                raise
        raise OSError("too many redirects")

    def _fetch(self, start, end):
        """Bytes [start, end] inclusive. Returns (data, total_size_or_None)."""
        last, renewed = None, False
        for attempt in range(self.retries + 1):
            try:
                r, url = self._open(start, end)
                with r:
                    if r.status != 206:
                        code = r.status
                        raise RangeUnsupported(f"HTTP {code} (not 206) for a Range request")
                    cr = r.headers.get("Content-Range", "")
                    m = re.match(r"bytes (\d+)-(\d+)/(\d+|\*)", cr)
                    if not m or int(m.group(1)) != start:
                        raise RangeUnsupported(f"bad Content-Range {cr!r} for bytes={start}-{end}")
                    data = r.read()
                if len(data) != int(m.group(2)) - start + 1:
                    raise OSError(f"short read {len(data)} B for bytes={start}-{end}")
                with self._lock:
                    self._final = url
                    self.bytes_fetched += len(data)
                    self.requests += 1
                self._progress()
                return data, (int(m.group(3)) if m.group(3).isdigit() else None)
            except urllib.error.HTTPError as e:
                last = e
                code = e.code
                e.close()
                if code in (401, 403, 410) and not renewed:
                    renewed = True
                    self._final = None
                    if self.session:
                        self.session.renew()
                    continue
                if code == 416:
                    raise OSError(f"HTTP 416 for bytes={start}-{end}: range beyond end of file") from e
                if code == 429:
                    wait = int(e.headers.get("Retry-After", 30)) if (e.headers.get("Retry-After") or "").isdigit() else 30
                    self.workers = 1
                    print(f"  server says 429 (rate limit); waiting {wait}s, then one request at a time")
                    time.sleep(wait)
                    continue
                if code < 500:
                    raise OSError(f"HTTP {code} on range request") from e
            except RangeUnsupported:
                raise
            except (urllib.error.URLError, http.client.HTTPException, TimeoutError, ConnectionError, OSError) as e:
                last = e
            wait = min(60, 2 ** attempt)
            print(f"  range request failed ({type(last).__name__}); retry {attempt + 1}/{self.retries} in {wait}s")
            time.sleep(wait)
        raise OSError(f"range read of bytes={start}-{end} failed after {self.retries} retries: {last}")

    def _probe(self):
        try:
            r, url = self._open(0, 1023)
        except urllib.error.HTTPError as e:
            raise OSError(f"probe failed: HTTP {e.code} {e.read()[:200].decode(errors='replace')}") from e
        with r:
            status, hdr = r.status, r.headers
            if status != 206:
                raise RangeUnsupported(f"probe got HTTP {status} instead of 206 Partial Content")
            if (hdr.get("Accept-Ranges") or "").lower() == "none":
                raise RangeUnsupported("server answers Accept-Ranges: none")
            m = re.match(r"bytes (\d+)-(\d+)/(\d+)", hdr.get("Content-Range", ""))
            if not m:
                raise RangeUnsupported("no usable Content-Range on the probe")
            data = r.read()
        self._final = url
        self.bytes_fetched += len(data)
        self.requests += 1
        return int(m.group(3))

    def _progress(self, force=False):
        if self.quiet:
            return
        now = time.time()
        if force or now - self._last_print >= 10:
            self._last_print = now
            el = max(now - self.t0, 1e-9)
            print(f"  fetched {self.bytes_fetched / 1e6:.1f} MB of {self.size / 1e6:.0f} MB "
                  f"({100 * self.bytes_fetched / self.size:.2f} % of the file) in {self.requests} requests, "
                  f"{self.bytes_fetched / 1e6 / el:.2f} MB/s average")

    # --- file protocol --------------------------------------------------------------------------------------------
    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else self.pos + off if whence == 1 else self.size + off
        return self.pos

    def _get_blocks(self, idx):
        missing = [i for i in idx if i not in self.cache]
        if missing:
            def one(i):
                a = i * self.block
                return i, self._fetch(a, min(a + self.block, self.size) - 1)[0]
            if len(missing) > 1 and self.workers > 1:
                with ThreadPoolExecutor(max_workers=self.workers) as ex:
                    got = list(ex.map(one, missing))
            else:
                got = [one(i) for i in missing]
            for i, d in got:
                while len(self.cache) >= self.cache_blocks:
                    self.cache.pop(next(iter(self.cache)))
                self.cache[i] = d
        for i in idx:
            if i in self.cache:                     # LRU: move to the end
                self.cache[i] = self.cache.pop(i)
        return {i: self.cache[i] for i in idx}

    def readinto(self, b):
        n = min(len(b), self.size - self.pos)
        if n <= 0:
            return 0
        first, last = self.pos // self.block, (self.pos + n - 1) // self.block
        blocks = self._get_blocks(list(range(first, last + 1)))
        out, got = memoryview(b), 0
        while got < n:
            i, off = divmod(self.pos, self.block)
            chunk = blocks[i][off:off + (n - got)]
            out[got:got + len(chunk)] = chunk
            got += len(chunk)
            self.pos += len(chunk)
        return got


def download_url(collection, item):
    return f"{API}/download?id={urllib.parse.quote(item)}&collection={urllib.parse.quote(collection)}"


def _run_subset(argv, h5_obj=None):
    sys.path.insert(0, os.path.join(ROOT, "src", "fetch"))
    import subset_h5
    return subset_h5.main(argv, h5_obj=h5_obj)


def _passthrough(a):
    out = ["--plan"] if a.plan else []
    if a.out:
        out += ["--out", a.out]
    if a.no_log:
        out.append("--no-log")
    return out


def subset(a):
    import h5py
    jobs = []
    if a.local:
        if not a.role:
            sys.exit("--local needs --role COAST|SEA")
        sid = a.scene_id or f"S_{a.role}_LOCAL"
        argv = ["--scene", sid, "--role", a.role, "--band", "S", "--src", os.path.abspath(a.local),
                "--status", "PROVISIONAL"] + (["--granule", a.granule] if a.granule else [])
        argv += _passthrough(a)
        _run_subset(argv)
        return
    if a.preset:
        jobs = [j for j in ARNAB if not a.only or j[0] == a.only]
    for item in a.id or []:
        if not a.role:
            sys.exit("--id needs --role COAST|SEA")
        m = re.search(r"_(\d{8})T\d{6}_", item)
        sid = a.scene_id if (a.scene_id and len(a.id) == 1) else f"S_{a.role}_{m.group(1)[4:] if m else item[-8:]}"
        jobs.append((a.role, sid, item))
    if not jobs:
        sys.exit("give --preset arnab, or --id <ITEM_ID> --role COAST|SEA, or --local <file.h5> --role ...")
    sess = Session()
    print(f"logged in. {len(jobs)} scene(s). Only the study-box chunks are requested (HTTP Range); "
          f"the full files (~10 GB each) are NOT downloaded.")
    total = 0
    for n, (role, sid, item) in enumerate(jobs, 1):
        coll = a.collection or GCOV_COLLECTION
        url = download_url(coll, item)
        print(f"\n[{n}/{len(jobs)}] {sid}  {role}  {item}")
        try:
            rf = RangeFile(url, session=sess, block=int(a.block_mb * (1 << 20)), workers=a.workers)
        except RangeUnsupported as e:
            sys.exit(f"STOPPING: the Bhoonidhi download endpoint does not support HTTP Range ({e}).\n"
                     "I will not fall back to downloading ~10 GB. Use the portal's subset/clip download instead "
                     "(delta box 81.6,16.2,82.6,17.1), then run:\n"
                     "  python3 src/fetch/bhoonidhi_s_band.py subset --local <file.h5> --role COAST")
        print(f"  range requests OK, file size {rf.size / 1e9:.2f} GB")
        argv = ["--scene", sid, "--role", role, "--band", "S", "--src", url,
                "--granule", item, "--collection", coll, "--status", "PROVISIONAL",
                "--source-url", url]
        argv += _passthrough(a)
        try:
            with h5py.File(rf, "r", rdcc_nbytes=128 << 20, rdcc_nslots=100003) as h5:
                _run_subset(argv, h5_obj=h5)
        except RangeUnsupported as e:
            sys.exit(f"STOPPING: server stopped honouring Range ({e}). Use the portal's subset download + --local.")
        rf._progress(force=True)
        total += rf.bytes_fetched
        print(f"  {sid}: fetched {rf.bytes_fetched / 1e6:.1f} MB ({100 * rf.bytes_fetched / rf.size:.2f} % of the file)")
        if n < len(jobs):
            time.sleep(2)
    print(f"\ndone. Total fetched {total / 1e6:.0f} MB for {len(jobs)} scene(s). "
          + ("(plan only, nothing written)" if a.plan else "Files are in data/h5/. Next: python3 tools/pipeline/catalog.py "
             "(refresh data/h5/catalog.json), then sync_manifest and build_web."))


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
    u = sub.add_parser("subset", help="stream only the study-box chunks (HTTP Range) into data/h5/")
    u.add_argument("--preset", choices=["arnab"], help="the 4 Arnab GCOV scenes (3 coast, 1 sea)")
    u.add_argument("--id", action="append", help="item id (repeatable); needs --role")
    u.add_argument("--role", choices=["COAST", "SEA"])
    u.add_argument("--scene-id", help="e.g. S_COAST_1004 (default S_<ROLE>_<MMDD>)")
    u.add_argument("--collection", default=None, help=f"default {GCOV_COLLECTION}")
    u.add_argument("--local", help="complete GCOV .h5 already on disk (portal download); no login needed")
    u.add_argument("--granule", help="with --local: source granule id")
    u.add_argument("--plan", action="store_true", help="login, probe Range, print the bytes each scene needs; write nothing")
    u.add_argument("--only", choices=["COAST", "SEA"], help="with --preset: just the 3 coast scenes or just the sea scene")
    u.add_argument("--out", help="output folder (default data/h5/)")
    u.add_argument("--no-log", action="store_true", help="do not append to data/logs/nisar_h5_subset.md")
    u.add_argument("--block-mb", type=float, default=4.0, help="range block size in MB (default 4)")
    u.add_argument("--workers", type=int, default=3, help="parallel range requests (default 3; drops to 1 on HTTP 429)")
    u.set_defaults(fn=subset)
    a = ap.parse_args()
    a.fn(a)
