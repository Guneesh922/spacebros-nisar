"""Clip OSM land polygons (shp extracted from the raw zip to a scratch dir) to the context box.
Usage: python src/fetch/package_c_osm_land.py <land_polygons.shp>"""
import sys, os, shutil, geopandas as gpd
from shapely.geometry import box
CTX = (78, 12, 88, 20)
g = gpd.read_file(sys.argv[1], bbox=CTX)
g = gpd.clip(g, box(*CTX))
t = "/tmp/land_osm_clip.geojson"
if os.path.exists(t): os.remove(t)
g[["geometry"]].to_file(t, driver="GeoJSON")
shutil.copyfile(t, "data/reference/land_osm_clip.geojson")
print("land", len(g), g.crs)
