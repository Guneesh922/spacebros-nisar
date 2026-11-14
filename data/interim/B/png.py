import json, hashlib, numpy as np, rasterio
from rasterio.warp import transform_bounds
from PIL import Image
from pathlib import Path
R=Path.home()/"mnt/nsa/05_Code/spacebros-nisar"; al=R/"data/interim/B/aligned"; out=R/"data/interim/B"
D=["20261004","20261016","20261028","20261109"]; K=16
def bm(a):
    h,w=(a.shape[0]//K)*K,(a.shape[1]//K)*K
    r=a[:h,:w].reshape(h//K,K,w//K,K)
    with np.errstate(all="ignore"):
        n=np.isfinite(r).sum((1,3)); s=np.nansum(r,(1,3))
    return np.where(n>=K*K//2, s/np.maximum(n,1), np.nan).astype("float32")
small={}; stats={}
for d in D:
    with rasterio.open(al/f"nisar_l_coast_{d}_t55_hh_db_aligned.tif") as ds:
        a=ds.read(1); ref=ds
        stats[d]=dict(hh_med=float(np.nanmedian(a)),hh_nan=float(np.isnan(a).mean()))
        small[d]=bm(a); b=transform_bounds(ds.crs,"EPSG:4326",*ds.bounds); bb=ds.bounds
    with rasterio.open(al/f"nisar_l_coast_{d}_t55_hv_db_aligned.tif") as ds:
        a=ds.read(1); stats[d].update(hv_med=float(np.nanmedian(a)),hv_nan=float(np.isnan(a).mean()))
    print(d,stats[d],flush=True)
allv=np.concatenate([small[d][np.isfinite(small[d])] for d in D])
lo,hi=[float(v) for v in np.percentile(allv,[2,98])]
files={}
for d in D:
    a=small[d]; v=np.isfinite(a)
    g=np.nan_to_num(np.clip((a-lo)/(hi-lo),0,1))*255
    im=Image.fromarray(np.dstack([g,g,g,v*255]).astype("uint8"),"RGBA")
    f=out/f"nisar_l_coast_{d}_t55_hh.png"; im.save(f,optimize=True)
    files[d]=dict(png=f.name,px=im.size,bytes=f.stat().st_size,sha256=hashlib.sha256(f.read_bytes()).hexdigest(),valid_frac=float(v.mean()))
res=dict(stretch_db=[lo,hi],bounds_wgs84_SW_NE=[[b[1],b[0]],[b[3],b[2]]],utm44n_bounds=list(bb),stats=stats,png=files)
json.dump(res,open(out/"B_png_stats.json","w"),indent=1); print(json.dumps(res,indent=1))
