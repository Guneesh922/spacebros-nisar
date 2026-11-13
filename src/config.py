"""Shared settings for the SpaceBros NISAR project.

Change the study area here and every script picks it up.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CATALOGUE = DATA / "catalogue"
BROWSE = DATA / "browse"
SUBSETS = DATA / "subsets"      # git-ignored: real GCOV pixels
APP = ROOT / "app"

# Study area: name and bounding box (west, south, east, north) in degrees.
# Default = Delhi NCR. Swap for any place on Earth.
AOI_NAME = "delhi"
AOI_BBOX = (76.8, 28.35, 77.6, 28.95)


def aoi_wkt(bbox=AOI_BBOX) -> str:
    w, s, e, n = bbox
    return f"POLYGON(({w} {s},{e} {s},{e} {n},{w} {n},{w} {s}))"
