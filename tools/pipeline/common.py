"""Shared constants for the automatic update pipeline (stdlib only)."""
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
H5_DIR = ROOT / "data" / "h5"
CATALOG = H5_DIR / "catalog.json"
MANIFEST = ROOT / "data" / "processed" / "manifest.json"

# Boxes, roles, posting, min_cover, baselines and alert matching come from config/areas.json (schema areas-v1):
# use load_areas() / area(). A scratch config can be selected with env SPACEBROS_AREAS=<path> (or --config on the
# pipeline scripts, which set the same variable). Boxes are WGS84 W, S, E, N. See docs/DATA_STORAGE.md.
AREAS_FILE = ROOT / "config" / "areas.json"
AREAS_ENV = "SPACEBROS_AREAS"
DEFAULT_AFTERMATH_DAYS = 30
DEFAULT_SEARCH_SINCE = "2026-10-01"

MAX_SUBSET_BYTES = 90 * 1000 * 1000   # refuse to keep a subset bigger than this (GitHub hard limit is 100 MB)

CATALOG_SCHEMA = "spacebros-h5-catalog-v1"

# NISAR granule names, e.g.
# NISAR_L2_PR_GCOV_034_055_A_010_4005_DHDH_A_20261028T000107_20261028T000129_P05036_N_P_J_001
GRANULE_RE = re.compile(
    r"^NISAR_L2_(?P<kind>PR|UR)_GCOV_(?P<cycle>\d{3})_(?P<track>\d{3})_(?P<dir>[AD])_(?P<frame>\d{3})_"
    r"(?P<mode>\d{4})_(?P<pols>[A-Z]{4})_(?P<x>[A-Z])_(?P<start>\d{8}T\d{6})_(?P<end>\d{8}T\d{6})_"
    r"(?P<crid>[PX]\d{5})_")

# first two letters of the pol code = frequency A (the one subset_h5.py reads); NA = not acquired
POL_CODE = {"DH": ["HH", "HV"], "DV": ["VV", "VH"], "SH": ["HH"], "SV": ["VV"],
            "QP": ["HH", "HV", "VH", "VV"], "QQ": ["HH", "HV", "VH", "VV"], "NA": []}


def areas_path(root=None, path=None):
    """Config file in use: explicit path > env SPACEBROS_AREAS > <root>/config/areas.json."""
    if path:
        return Path(path)
    if os.environ.get(AREAS_ENV):
        return Path(os.environ[AREAS_ENV])
    return Path(root or ROOT) / "config" / "areas.json"


def load_areas(root=None, path=None):
    """The whole areas-v1 document (raises if missing or the wrong schema)."""
    p = areas_path(root, path)
    d = load_json(p)
    if not d or d.get("schema") != "areas-v1":
        raise ValueError(f"{p}: missing or not schema areas-v1")
    return d


def area(id=None, root=None, path=None):
    """One area dict (default: default_area). Adds `_defaults` (config defaults) for convenience."""
    d = load_areas(root, path)
    aid = id or d["default_area"]
    for a in d["areas"]:
        if a["id"] == aid:
            a = dict(a)
            a["_defaults"] = {"aftermath_days": DEFAULT_AFTERMATH_DAYS, "search_since": DEFAULT_SEARCH_SINCE,
                              **(d.get("defaults") or {})}
            return a
    raise KeyError(f"area {aid!r} not in {areas_path(root, path)}")


def role_box(a, role):
    return tuple(a["boxes"][role])


def search_box(a):
    """Union of all the area's boxes (W, S, E, N): the CMR search window."""
    bs = [tuple(b) for b in a["boxes"].values()]
    return (min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs))


def freq_a_pols(code):
    return POL_CODE.get(code[:2], [])


def load_json(path, default=None):
    p = Path(path)
    if not p.exists():
        return default
    with open(p) as f:
        return json.load(f)


def dump_json(obj, path):
    with open(path, "w") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)
        f.write("\n")


def scene_key(role, date, track):
    """Identity of a scene in the catalog: role + acquisition date (YYYYMMDD or YYYY-MM-DD) + track."""
    return f"{role}_{str(date).replace('-', '')}_T{int(track):03d}"
