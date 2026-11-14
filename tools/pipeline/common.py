"""Shared constants for the automatic update pipeline (stdlib only)."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
H5_DIR = ROOT / "data" / "h5"
CATALOG = H5_DIR / "catalog.json"
MANIFEST = ROOT / "data" / "processed" / "manifest.json"

# WGS84 W, S, E, N (same as data/sources.yaml and src/fetch/subset_h5.py)
BOX = {"COAST": (81.6, 16.2, 82.6, 17.1), "SEA": (81.0, 15.0, 85.0, 18.0)}
START_DATE = "2026-10-01"

# Output posting (m): COAST 20 m (2x2 of the native 10 m grid), SEA 100 m. See docs/DATA_STORAGE.md.
POSTING_M = {"COAST": 20, "SEA": 100}
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
