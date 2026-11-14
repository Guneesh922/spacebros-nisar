"""Cut a study-box subset out of one NISAR L-band GCOV granule and write it as a small HDF5 (schema v1).

Schema: docs/DATA_STORAGE.md ("H5 subset schema (v1)"). No rasterio needed (h5py, numpy, pyproj only;
earthaccess+fsspec are imported lazily and only for https sources).

Usage (from the repo root):
  python src/fetch/subset_h5.py --scene L_COAST_1004 --src data/raw/nisar_l_h5/<granule>.h5
  python src/fetch/subset_h5.py --scene L_COAST_1004 --src <local.h5> --multilook 2 --suffix _ml2
  python src/fetch/subset_h5.py --scene L_SEA_EYE_1027 --src https://nisar.asf.earthdatacloud.nasa.gov/...h5
Any scene not in the SCENES table (new passes found by tools/pipeline/discover.py, or S-band) is described on the
command line instead:
  python src/fetch/subset_h5.py --scene L_COAST_20261121_T055 --role COAST --status VALIDATED --posting 20 \
      --granule NISAR_L2_PR_GCOV_036_055_A_010_4005_DHDH_A_20261121T000107_20261121T000130_P05036_N_P_J_001 \
      --src https://nisar.asf.earthdatacloud.nasa.gov/.../....h5          # streams; uses $EARTHDATA_TOKEN if set
  python src/fetch/subset_h5.py --scene S_COAST_20261016_T055 --role COAST --band S --src <local S-band GCOV.h5>
S-band (ISRO NISAR_SSAR_GCOV, /science/SSAR/GCOV/grids/frequencyA): same schema, band "S". COAST uses the GCOV
diagonal terms the file holds (DH products: HHHH, HVHV -> /backscatter/HH, HV); SEA compact-pol products (CRNA) hold
RHRH, RVRV -> /backscatter/RH, RV and root attr pol_basis="compact-circular-transmit". Default posting 20 m COAST /
100 m SEA (multilook computed from the native spacing). src/fetch/bhoonidhi_s_band.py `subset` calls main() with an
already-open range-read file object (h5_obj=), so only the box chunks are fetched from Bhoonidhi.
Streaming: with env EARTHDATA_TOKEN (Earthdata user token) the https source is read with HTTP range requests and
a bearer token (stdlib only); without it earthaccess (netrc login) is used as before.
Only the box window is read from the granule (row bands), never the full layer.
"""
import argparse
import contextlib
import datetime as dt
import io
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import h5py
import numpy as np
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[2]
BASE = "https://nisar.asf.earthdatacloud.nasa.gov/NISAR"
BOX = {"delta": (81.6, 16.2, 82.6, 17.1), "sea": (81.0, 15.0, 85.0, 18.0)}
SEA_POLS, COAST_POLS = ["VVVV", "VHVH"], ["HHHH", "HVHV"]
FILL = -32768
SEA_POSTING_M = 100.0

# id: (collection, file_id, box, GCOV pol datasets)
SCENES = {
    "L_SEA_CALM_1015": ("NISAR_L2_GCOV_PROVISIONAL_V1", "NISAR_L2_PR_GCOV_033_048_D_080_2005_DVDV_A_20261015T130150_20261015T130208_P05023_N_P_J_001", "sea", SEA_POLS),
    "L_SEA_EYE_1027": ("NISAR_L2_GCOV_V1", "NISAR_L2_PR_GCOV_034_048_D_080_2005_DVDV_A_20261027T130151_20261027T130208_P05036_N_P_J_001", "sea", SEA_POLS),
    "L_COAST_1004": ("NISAR_L2_GCOV_PROVISIONAL_V1", "NISAR_L2_PR_GCOV_032_055_A_010_4005_DHDH_A_20261004T000106_20261004T000129_P05023_N_P_J_001", "delta", COAST_POLS),
    "L_COAST_1016": ("NISAR_L2_GCOV_PROVISIONAL_V1", "NISAR_L2_PR_GCOV_033_055_A_010_4005_DHDH_A_20261016T000106_20261016T000129_P05023_N_P_J_001", "delta", COAST_POLS),
    "L_COAST_1028": ("NISAR_L2_GCOV_V1", "NISAR_L2_PR_GCOV_034_055_A_010_4005_DHDH_A_20261028T000107_20261028T000129_P05036_N_P_J_001", "delta", COAST_POLS),
    "L_COAST_1109": ("NISAR_L2_GCOV_V1", "NISAR_L2_PR_GCOV_035_055_A_010_4005_DHDH_A_20261109T000107_20261109T000130_P05036_N_P_J_001", "delta", COAST_POLS),
    "L_SEA_AFTER_1108": ("NISAR_L2_GCOV_V1", "NISAR_L2_PR_GCOV_035_048_D_080_2005_DVDV_A_20261108T130151_20261108T130208_P05036_N_P_J_001", "sea", SEA_POLS),
    "L_SEA_CALM_1003": ("NISAR_L2_GCOV_PROVISIONAL_V1", "NISAR_L2_PR_GCOV_032_048_D_080_2005_QPDH_A_20261003T130133_20261003T130207_P05023_N_F_J_001", "sea", ["VVVV", "HVHV"]),
    "L_COAST_T149_1010": ("NISAR_L2_GCOV_PROVISIONAL_V1", "NISAR_L2_PR_GCOV_032_149_D_080_4005_DHDH_A_20261010T130952_20261010T131027_P05023_N_F_J_001", "delta", COAST_POLS),
    "L_COAST_T149_1022": ("NISAR_L2_GCOV_V1", "NISAR_L2_PR_GCOV_033_149_D_080_4005_DHDH_A_20261022T130952_20261022T131027_P05036_N_F_J_001", "delta", COAST_POLS),
    "L_COAST_T149_1103": ("NISAR_L2_GCOV_V1", "NISAR_L2_PR_GCOV_034_149_D_080_4005_DHDH_A_20261103T130953_20261103T131027_P05036_N_F_J_001", "delta", COAST_POLS),
}


def find_grid(h5, freq="A", band=None):
    """HDF5 group holding the GCOV grids for one frequency (same logic as src/gcov_subset.py).
    band "L" / "S" restricts the search to /science/LSAR or /science/SSAR; None tries LSAR then SSAR."""
    bases = {"L": ("/science/LSAR/GCOV/grids",), "S": ("/science/SSAR/GCOV/grids",)}.get(
        band, ("/science/LSAR/GCOV/grids", "/science/SSAR/GCOV/grids"))
    for base in bases:
        path = f"{base}/frequency{freq}"
        if path in h5:
            return h5[path]
    found = []
    pick = {"L": "LSAR", "S": "SSAR"}.get(band, "")
    h5.visit(lambda n: found.append(n) if n.endswith(f"frequency{freq}") and "grids" in n and pick in n else None)
    if not found:
        raise KeyError(f"frequency{freq} grid not found in file")
    return h5[found[0]]


def epsg_of(grid):
    proj = grid["projection"]
    for key in ("epsg_code", "epsg"):
        if key in proj.attrs:
            return int(proj.attrs[key])
    return int(proj[()])


def txt(v):
    return v.decode() if isinstance(v, bytes) else str(v)


def ident(h5, name, default=None):
    for base in ("/science/LSAR/identification", "/science/SSAR/identification"):
        try:
            if base in h5 and name in h5[base]:
                return h5[base][name][()]
        except (KeyError, OSError):    # truncated / unreadable small field: fall back to the file name
            pass
    return default


LINEAR_RX = {"HH", "HV", "VH", "VV"}
COMPACT_RX = {"RH", "RV", "LH", "LV"}   # circular transmit, linear receive


def diag_terms(grid):
    """Diagonal covariance datasets present in a GCOV frequency group (HHHH, HVHV, RHRH, RVRV...), in file order."""
    return [k for k in grid.keys()
            if len(k) == 4 and k[:2] == k[2:] and k[:2] in (LINEAR_RX | COMPACT_RX)]


def pol_basis_of(names):
    """'linear' for HH/HV/VH/VV; 'compact-circular-transmit' for RH/RV (right) or LH/LV (left)."""
    return "compact-circular-transmit" if any(n[:2] in COMPACT_RX for n in names) else "linear"


def default_pols(band, role, grid):
    """L-band: fixed lists. S-band: whatever diagonal terms the file holds (COAST: co/cross H first)."""
    if band != "S":
        return SEA_POLS if role == "SEA" else COAST_POLS
    have = diag_terms(grid)
    want = ["HHHH", "HVHV"] if role == "COAST" else ["VVVV", "VHVH", "RHRH", "RVRV", "LHLH", "LVLV", "HHHH", "HVHV"]
    pols = [p for p in want if p in have] or have
    if role == "COAST":
        pols = [p for p in pols if p in ("HHHH", "HVHV")] or pols   # never mix pol bases on a coast layer
    return pols


def chunk_bytes(ds, r0, r1, c0, c1, cap=120):
    """Compressed bytes of the chunks that overlap the window (reads only HDF5 metadata). Returns (n_chunks, bytes,
    sampled) or None for contiguous datasets. Large windows are estimated from `cap` evenly spaced chunks."""
    if ds.chunks is None:
        return None
    cr, cc = ds.chunks[-2:]
    keys = [(r, c) for r in range(r0 // cr * cr, r1, cr) for c in range(c0 // cc * cc, c1, cc)]
    step = max(1, len(keys) // cap)
    tot = n = 0
    for r, c in keys[::step]:
        try:
            info = ds.id.get_chunk_info_by_coord((r, c))
        except Exception:  # noqa: BLE001  (chunk never written)
            continue
        tot += info.size
        n += 1
    return len(keys), tot * (len(keys) / max(1, n)) if n else 0.0, step > 1


def git_sha():
    try:
        return subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
                                       stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:  # noqa: BLE001
        return "nogit"


def window(x, y, bbox, epsg):
    w, s, e, n = bbox
    tr = Transformer.from_crs(4326, epsg, always_xy=True)
    xs, ys = tr.transform([w, e, e, w], [s, s, n, n])
    cols = np.where((x >= min(xs)) & (x <= max(xs)))[0]
    rows = np.where((y >= min(ys)) & (y <= max(ys)))[0]
    if cols.size == 0 or rows.size == 0:
        raise ValueError("box does not overlap this scene")
    return cols[0], cols[-1] + 1, rows[0], rows[-1] + 1


def block_mean_db(arr, k):
    """Block mean in LINEAR power over valid (finite, >0) samples, then dB. Returns float32 with NaN."""
    arr = arr.astype("float32")
    valid = np.isfinite(arr) & (arr > 0)
    arr = np.where(valid, arr, 0).astype("float64") if k > 1 else np.where(valid, arr, np.nan)
    if k > 1:
        h, w = arr.shape[0] // k * k, arr.shape[1] // k * k
        s = arr[:h, :w].reshape(h // k, k, w // k, k).sum(axis=(1, 3))
        c = valid[:h, :w].reshape(h // k, k, w // k, k).sum(axis=(1, 3))
        with np.errstate(divide="ignore", invalid="ignore"):
            arr = np.where(c > 0, s / np.maximum(c, 1), np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        db = 10 * np.log10(arr)
    db[~np.isfinite(db)] = np.nan
    return db.astype("float32")


class TokenRangeFile(io.RawIOBase):
    """Read-only file object over an https URL using HTTP range requests and an Earthdata bearer token.

    stdlib only. The bearer token is sent only to *.earthdata.nasa.gov / *.earthdatacloud.nasa.gov hosts; redirects
    (to a presigned S3 URL) are followed by hand so the token never reaches a third-party host. Blocks of
    `block` bytes are cached (small LRU) because h5py reads many nearby chunks. Re-resolves the redirect on 401/403
    (presigned URLs expire)."""

    def __init__(self, url, token, block=8 * 1024 * 1024, cache_blocks=24):
        self.url, self.token, self.block, self.cache_blocks = url, token, block, cache_blocks
        self.pos, self.cache, self._final = 0, {}, None
        self.size = int(self._get(0, 0)[1])

    @staticmethod
    def _trusted(host):
        return host.endswith(".earthdata.nasa.gov") or host.endswith(".earthdatacloud.nasa.gov") or host == "earthdata.nasa.gov"

    def _resolve(self):
        """Follow redirects from the DAAC URL; remember the final (presigned) URL."""
        url = self.url
        for _ in range(6):
            host = urllib.parse.urlparse(url).hostname or ""
            hdr = {"Range": "bytes=0-0", "User-Agent": "spacebros-nisar"}
            if self._trusted(host):
                hdr["Authorization"] = "Bearer " + self.token
            req = urllib.request.Request(url, headers=hdr)
            opener = urllib.request.build_opener(_NoRedirect)
            try:
                resp = opener.open(req, timeout=120)
                resp.close()
                self._final = url
                return
            except urllib.error.HTTPError as e:
                if e.code in (301, 302, 303, 307, 308) and e.headers.get("Location"):
                    url = urllib.parse.urljoin(url, e.headers["Location"])
                    continue
                raise
        raise OSError("too many redirects")

    def _get(self, start, end, _retry=True):
        if self._final is None:
            self._resolve()
        hdr = {"Range": f"bytes={start}-{end}", "User-Agent": "spacebros-nisar"}
        if self._trusted(urllib.parse.urlparse(self._final).hostname or ""):
            hdr["Authorization"] = "Bearer " + self.token
        last = None
        for attempt in range(5):
            try:
                with urllib.request.urlopen(urllib.request.Request(self._final, headers=hdr), timeout=120) as r:
                    cr = r.headers.get("Content-Range", "")
                    total = cr.rsplit("/", 1)[-1] if "/" in cr else r.headers.get("Content-Length", "0")
                    return r.read(), total
            except urllib.error.HTTPError as e:
                if e.code in (401, 403) and _retry:
                    self._final = None
                    return self._get(start, end, _retry=False)
                last = e
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                last = e
            time.sleep(2 ** attempt)
        raise OSError(f"range read failed: {last}")

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else self.pos + off if whence == 1 else self.size + off
        return self.pos

    def _block(self, i):
        if i not in self.cache:
            if len(self.cache) >= self.cache_blocks:
                self.cache.pop(next(iter(self.cache)))
            a = i * self.block
            self.cache[i] = self._get(a, min(a + self.block, self.size) - 1)[0]
        return self.cache[i]

    def readinto(self, b):
        n = min(len(b), self.size - self.pos)
        if n <= 0:
            return 0
        out, got = memoryview(b), 0
        while got < n:
            i, off = divmod(self.pos, self.block)
            chunk = self._block(i)[off:off + (n - got)]
            out[got:got + len(chunk)] = chunk
            got += len(chunk)
            self.pos += len(chunk)
        return got


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def open_source(src):
    if re.match(r"https?://", src) and os.environ.get("EARTHDATA_TOKEN"):
        return h5py.File(TokenRangeFile(src, os.environ["EARTHDATA_TOKEN"].strip()), "r")
    if re.match(r"https?://", src):
        import earthaccess  # lazy: only needed for streaming
        earthaccess.login(persist=False)
        fs = earthaccess.get_fsspec_https_session()
        return h5py.File(fs.open(src, block_size=8 * 1024 * 1024, cache_type="blockcache"), "r")
    return h5py.File(src, "r")


def main(argv=None, h5_obj=None):
    """CLI entry. h5_obj: an already-open h5py.File (e.g. over a range-read file object); --src is then only recorded
    as source_url (never opened)."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", required=True,
                    help="id from the SCENES table, or any new id (then --role and usually --granule are needed)")
    ap.add_argument("--src", required=True, help="local .h5 path or https URL of the full granule")
    ap.add_argument("--multilook", type=int, default=None,
                    help="k x k block mean (COAST default 1 = native; SEA default = round(100 m / spacing))")
    ap.add_argument("--posting", type=float, default=None,
                    help="target posting in m; multilook = round(posting / native spacing), min 1 (overridden by --multilook)")
    ap.add_argument("--role", choices=["COAST", "SEA"], help="needed for scenes that are not in the SCENES table")
    ap.add_argument("--band", choices=["L", "S"], default=None, help="default: detected from the file (LSAR/SSAR)")
    ap.add_argument("--granule", default=None, help="source granule id (default: SCENES table, else the file stem)")
    ap.add_argument("--status", choices=["PROVISIONAL", "VALIDATED"], default=None)
    ap.add_argument("--collection", default=None)
    ap.add_argument("--pols", default=None, help="comma list of GCOV datasets, e.g. HHHH,HVHV (default: role default)")
    ap.add_argument("--source-url", default=None, help="recorded as source_url (default: ASF URL for L, none for local S)")
    ap.add_argument("--plan", action="store_true", help="print window, chunk counts and the compressed bytes to be "
                    "fetched per polarisation, then stop without writing")
    ap.add_argument("--no-log", action="store_true", help="do not append to data/logs/nisar_h5_subset.md")
    ap.add_argument("--out", default="data/h5/")
    ap.add_argument("--suffix", default="", help="appended to the file stem, e.g. _ml2")
    args = ap.parse_args(argv)
    t0 = time.time()

    if args.scene in SCENES:
        coll, fid, boxname, pols = SCENES[args.scene]
        role = "SEA" if boxname == "sea" else "COAST"
    else:
        if not args.role:
            ap.error(f"scene {args.scene!r} is not in the SCENES table: pass --role COAST|SEA (and --granule)")
        role = args.role
        boxname = "sea" if role == "SEA" else "delta"
        pols = None            # decided from the file once the band is known
        fid = args.granule or re.sub(r"\.h5$", "", Path(args.src.split("?")[0]).name)
        s_hint = args.band == "S" or args.scene.startswith("S_") or fid.startswith("NISAR_S")
        coll = args.collection or ("NISAR_SSAR_GCOV" if s_hint else
                                   "NISAR_L2_GCOV_V1" if args.status == "VALIDATED" else "NISAR_L2_GCOV_PROVISIONAL_V1")
    if args.granule:
        fid = args.granule
    coll = args.collection or coll
    if args.pols:
        pols = [p.strip().upper() for p in args.pols.split(",")]
    bbox = BOX[boxname]
    status = args.status or ("PROVISIONAL" if "PROVISIONAL" in coll or "SSAR" in coll else "VALIDATED")
    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    opener = contextlib.nullcontext(h5_obj) if h5_obj is not None else open_source(args.src)
    with opener as h5:
        band = args.band or ("S" if "/science/SSAR" in h5 and "/science/LSAR" not in h5 else "L")
        grid = find_grid(h5, "A", band)
        if pols is None:
            pols = default_pols(band, role, grid)
        epsg = epsg_of(grid)
        x = grid["xCoordinates"][:]
        y = grid["yCoordinates"][:]
        dx, dy = float(x[1] - x[0]), float(y[1] - y[0])
        if dy > 0:
            raise ValueError("south-up grid not supported (expected y descending)")
        if args.multilook:
            k = args.multilook
        elif args.posting:
            k = max(1, round(args.posting / abs(dx)))
        elif role == "SEA":
            k = max(1, round(SEA_POSTING_M / abs(dx)))
        else:
            k = max(1, round(20.0 / abs(dx))) if band == "S" else 1   # S-band COAST: 20 m by default
        c0, c1, r0, r1 = window(x, y, bbox, epsg)
        nrow, ncol = (r1 - r0) // k, (c1 - c0) // k
        r1, c1 = r0 + nrow * k, c0 + ncol * k
        gx = x[c0:c1].reshape(ncol, k).mean(axis=1)
        gy = y[r0:r1].reshape(nrow, k).mean(axis=1)
        posting = abs(dx) * k

        track = int(ident(h5, "trackNumber", int(re.search(r"GCOV_\d+_(\d+)_", fid).group(1))))
        frame = int(ident(h5, "frameNumber", int(re.search(r"GCOV_\d+_\d+_[AD]_(\d+)_", fid).group(1))))
        direction = txt(ident(h5, "orbitPassDirection", b"Ascending" if "_A_" in fid[:30] else b"Descending"))[0].upper()
        m = re.search(r"_(\d{8}T\d{6})_(\d{8}T\d{6})_", fid)
        fmt = lambda s: dt.datetime.strptime(s, "%Y%m%dT%H%M%S").strftime("%Y-%m-%dT%H:%M:%SZ")  # noqa: E731
        st = ident(h5, "zeroDopplerStartTime")
        en = ident(h5, "zeroDopplerEndTime")
        start_utc = txt(st)[:19] + "Z" if st is not None else fmt(m.group(1))
        end_utc = txt(en)[:19] + "Z" if en is not None else fmt(m.group(2))
        date = start_utc[:10].replace("-", "")
        fname = f"{band}_{role}_{date}_T{track:03d}{args.suffix}.h5"
        out = out_dir / fname

        # true footprint: pixel-edge rectangle -> lat/lon (sample all four edges)
        xe0, xe1 = gx[0] - posting / 2, gx[-1] + posting / 2
        yn, ys_ = gy[0] + posting / 2, gy[-1] - posting / 2
        t = np.linspace(0, 1, 21)
        ex = np.concatenate([xe0 + t * (xe1 - xe0), np.full(21, xe1), xe1 - t * (xe1 - xe0), np.full(21, xe0)])
        ey = np.concatenate([np.full(21, yn), yn + t * (ys_ - yn), np.full(21, ys_), ys_ + t * (yn - ys_)])
        lon, lat = Transformer.from_crs(epsg, 4326, always_xy=True).transform(ex, ey)
        bounds = [[float(lat.min()), float(lon.min())], [float(lat.max()), float(lon.max())]]

        if args.source_url:
            src_url = args.source_url
        elif re.match(r"https?://", args.src):
            src_url = args.src
        elif band == "S":
            src_url = f"https://bhoonidhi-api.nrsc.gov.in/download?id={fid}&collection={coll}"
        else:
            src_url = f"{BASE}/{coll}/{fid}/{fid}.h5"
        print(f"{args.scene}: grid EPSG:{epsg} spacing {abs(dx):g} m, window rows {r0}:{r1} cols {c0}:{c1}, "
              f"multilook {k} -> {nrow}x{ncol} @ {posting:g} m")

        pol_names = [n for n in pols if n in grid]
        basis = pol_basis_of(pol_names or pols)
        band_rows = max(k, (min(2048, int(3e7) // max(1, c1 - c0)) // k) * k)   # <= ~30 M samples per read band
        if args.plan:
            tot = 0.0
            for name in pol_names + (["mask"] if "mask" in grid else []):
                cb = chunk_bytes(grid[name], r0, r1, c0, c1)
                if cb:
                    tot += cb[1]
                    print(f"  plan {name}: {cb[0]} chunks {grid[name].chunks} dtype {grid[name].dtype}, "
                          f"~{cb[1] / 1e6:.0f} MB compressed{' (sampled)' if cb[2] else ''}")
                else:
                    print(f"  plan {name}: contiguous (uncompressed) dataset, "
                          f"~{(r1 - r0) * (c1 - c0) * grid[name].dtype.itemsize / 1e6:.0f} MB if read by rows")
            print(f"  plan total ~{tot / 1e6:.0f} MB for pols {pol_names} (pol_basis {basis}); nothing written")
            return None
        tmp = out.with_suffix(".h5.part")
        stats = {}
        with h5py.File(tmp, "w") as o:
            a = o.attrs
            a["schema"] = "spacebros-subset-v1"
            a["scene_id"] = args.scene
            a["band"] = band
            a["role"] = role
            a["source_granule"] = fid
            a["source_url"] = src_url
            a["source_collection"] = coll
            a["product_status"] = status
            a["track"] = track
            a["frame"] = frame
            a["direction"] = direction
            a["start_utc"] = start_utc
            a["end_utc"] = end_utc
            a["box_name"] = boxname
            a["bbox_wgs84"] = np.array(bbox, dtype="float64")
            a["epsg"] = epsg
            a["posting_m"] = posting
            a["multilook"] = k
            a["pol_basis"] = basis
            a["created_utc"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            a["software"] = f"src/fetch/subset_h5.py@{git_sha()}"
            a["bounds_latlon"] = np.array(bounds, dtype="float64")
            dgx = o.create_dataset("grid/x", data=gx.astype("float64"))
            dgy = o.create_dataset("grid/y", data=gy.astype("float64"))
            dgx.attrs["epsg"] = epsg
            dgy.attrs["epsg"] = epsg
            chunks = (min(256, nrow), min(256, ncol))
            for name in pols:
                if name not in grid:
                    print(f"  {name}: not in file (has {[q for q in grid.keys() if len(q) == 4]})")
                    continue
                pol = name[:2]
                d = o.create_dataset(f"backscatter/{pol}", shape=(nrow, ncol), dtype="int16", fillvalue=FILL,
                                     chunks=chunks, compression="gzip", compression_opts=6, shuffle=True)
                d.attrs["scale_factor"] = np.float64(0.01)
                d.attrs["units"] = "dB"
                d.attrs["quantity"] = f"gamma0 (RTC), from GCOV {name} linear power"
                d.attrs["_FillValue"] = np.int16(FILL)
                for rs in range(0, nrow * k, band_rows):
                    re_ = min(rs + band_rows, nrow * k)
                    blk = grid[name][r0 + rs:r0 + re_, c0:c1]
                    db = block_mean_db(blk, k)
                    q = np.full(db.shape, FILL, dtype="int16")
                    ok = np.isfinite(db)
                    q[ok] = np.clip(np.rint(db[ok] * 100), -32767, 32767).astype("int16")
                    d[rs // k:rs // k + db.shape[0], :] = q
                v = d[::4, ::4]
                vm = v != FILL
                stats[pol] = (float(np.median(v[vm]) / 100) if vm.any() else float("nan"),
                              float(1 - (d[::2, ::2] != FILL).mean()))
            if not stats:
                raise ValueError(f"none of {pols} found in the file; its datasets: "
                                 f"{[q for q in grid.keys() if len(q) == 4]}")
            if "mask" in grid:
                mk = o.create_dataset("aux/mask", shape=(nrow, ncol), dtype="uint8", chunks=chunks,
                                      compression="gzip", compression_opts=6, shuffle=True)
                off = k // 2
                for rs in range(0, nrow * k, band_rows):
                    re_ = min(rs + band_rows, nrow * k)
                    blk = grid["mask"][r0 + rs:r0 + re_, c0:c1]
                    sub = blk[off::k, off::k][:(re_ - rs) // k, :ncol]
                    mk[rs // k:rs // k + sub.shape[0], :] = sub
            o.create_dataset("metadata/orbit_pass", data=direction)
            o.create_dataset("metadata/track", data=track)
            o.create_dataset("metadata/frame", data=frame)
        tmp.replace(out)

    mb = out.stat().st_size / 1e6
    shown = out.relative_to(ROOT) if out.is_relative_to(ROOT) else out   # --out may be outside the repo
    print(f"wrote {shown}  shape={nrow}x{ncol}  posting={posting:g} m  size={mb:.1f} MB")
    sline = "; ".join(f"{p} median {m_:.2f} dB nan {n_:.3f}" for p, (m_, n_) in stats.items())
    for p, (m_, n_) in stats.items():
        print(f"  {p}: median {m_:.2f} dB, NaN fraction {n_:.3f}")
    print(f"  bounds_latlon {bounds}  runtime {time.time() - t0:.0f} s")
    if args.no_log:
        return
    log = ROOT / "data" / "logs" / "nisar_h5_subset.md"
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "a") as f:
        f.write(f"- {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%MZ} {args.scene} -> data/h5/{fname} "
                f"shape={nrow}x{ncol} posting={posting:g}m multilook={k} size={mb:.1f}MB {sline} "
                f"runtime={time.time() - t0:.0f}s src={fid}\n")


if __name__ == "__main__":
    main()
