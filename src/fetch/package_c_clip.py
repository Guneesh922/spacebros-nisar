"""Package C: clip boundaries, GSW and coastlines to the study region.
Usage: PYTHONPATH=... python src/fetch/package_c_clip.py [--osm]
Run from the repo root. No data is invented; everything is a clip of the raw files."""
import sys, json, shutil, os, tempfile
import geopandas as gpd, pandas as pd, numpy as np, rasterio
from rasterio.windows import from_bounds
from shapely.geometry import box

def save(gdf, path):
    """write via /tmp then copy in place (mounted folder forbids unlink/replace)"""
    t = os.path.join("/tmp", os.path.basename(path))
    if os.path.exists(t): os.remove(t)
    gdf.to_file(t, driver="GeoJSON"); shutil.copyfile(t, path)

BOX = (81.0, 15.8, 83.0, 17.6)          # clip_vectors box
DELTA = (81.6, 16.2, 82.6, 17.1)        # study box
CTX = (78, 12, 88, 20)                  # coast context box
REF, RAW, INT = "data/reference/", "data/raw/", "data/interim/"

def clip_adm(path, out, level):
    g = gpd.read_file(path)
    assert g.crs.to_epsg() == 4326
    g = g[g.intersects(box(*BOX))].copy()
    g["area_km2"] = g.to_crs(32644).area / 1e6
    save(g[["shapeName", "shapeID", "area_km2", "geometry"]], out)
    print(level, len(g), out)
    return g

d2 = clip_adm(RAW + "boundaries/geoBoundaries-IND-ADM2.geojson", REF + "districts_delta_gb2021.geojson", "ADM2")
m3 = clip_adm(RAW + "boundaries/geoBoundaries-IND-ADM3.geojson", REF + "mandals_delta.geojson", "ADM3")

# mandal list CSV
pts = m3.copy(); pts["geometry"] = m3.representative_point()
j = gpd.sjoin(pts[["shapeID", "geometry"]], d2[["shapeName", "geometry"]].rename(columns={"shapeName": "adm2"}), how="left", predicate="within")
j = j.drop_duplicates("shapeID").set_index("shapeID")["adm2"]
dbox = box(*DELTA); dbox_km2 = gpd.GeoSeries([dbox], crs=4326).to_crs(32644).iloc[0]
m3p = m3.to_crs(32644)
dbp = dbox_km2
m3["frac_inside_delta_box"] = [round(g.intersection(dbp).area / g.area, 4) for g in m3p.geometry]
m3["parent_ADM2_name"] = m3.shapeID.map(j)
m3[["shapeID", "shapeName", "parent_ADM2_name", "area_km2", "frac_inside_delta_box"]].sort_values("frac_inside_delta_box", ascending=False).to_csv(REF + "mandals_delta_list.csv", index=False)

# GSW window
with rasterio.open(RAW + "water/occurrence_80E_20Nv1_4_2021.tif") as src:
    w = from_bounds(*BOX, transform=src.transform).round_offsets().round_lengths()
    arr = src.read(1, window=w)
    prof = src.profile.copy()
    prof.update(height=arr.shape[0], width=arr.shape[1], transform=src.window_transform(w), compress="deflate", tiled=False)
    prof.pop("blockxsize", None); prof.pop("blockysize", None)
    with rasterio.open("/tmp/gsw_tmp.tif", "w", **prof) as dst:
        dst.write(arr, 1)
    shutil.copyfile("/tmp/gsw_tmp.tif", INT + "gsw_occurrence_delta.tif")
    print("GSW", arr.shape, src.crs, src.nodata)
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(7, 6))
a = np.ma.masked_equal(arr[::8, ::8], 255)
ext = (BOX[0], BOX[2], BOX[1], BOX[3])
ax.imshow(a, extent=ext, cmap="Blues", vmin=0, vmax=100)
m3.boundary.plot(ax=ax, color="grey", lw=0.3)
x0, y0, x1, y1 = DELTA; ax.plot([x0, x1, x1, x0, x0], [y0, y0, y1, y1, y0], "r-", lw=1)
ax.set_title("JRC GSW occurrence (%) + mandals; red = delta box")
fig.savefig(INT + "gsw_occurrence_delta_preview.png", dpi=110, bbox_inches="tight")

# NE coastline
ne = gpd.read_file("zip://" + RAW + "coast/ne_10m_coastline.zip", bbox=CTX)
ne = gpd.clip(ne, box(*CTX))
save(ne[["geometry"]], REF + "coastline_ne10m_clip.geojson")
print("NE", len(ne))

if "--osm" in sys.argv or "--osm-land" in sys.argv:
    import glob
    for name, out in (("coastlines-split-4326", "coastline_osm_clip.geojson"), ("land-polygons-split-4326", "land_osm_clip.geojson")):
        if "--osm-land" in sys.argv and name.startswith("coast"): continue
        z = RAW + f"coast/{name}.zip!{name}/" + ("lines.shp" if name.startswith("coast") else "land_polygons.shp")
        g = gpd.read_file("zip://" + z, bbox=CTX)
        g = gpd.clip(g, box(*CTX))
        save(g[["geometry"]], REF + out)
        print(name, len(g), out)
