import sys, json, glob, shutil, hashlib, numpy as np
from pathlib import Path
R=Path.home()/"mnt/nsa/05_Code/spacebros-nisar"
sys.path.insert(0,str(R/"src")); sys.path.insert(0,str(R/"src/fetch"))
import subset_arnab as sa
from gcov_subset import save_tif
from rasterio.transform import from_origin
sid,tag=sys.argv[1],sys.argv[2]
C=Path("/tmp/Bwork/cache")/f"{sid}_{tag}"; m=json.load(open(C/"meta.json"))
short=sa.SCENES[sid][6]; pols=sa.SCENES[sid][4]
assert m["dy"]<0
tr=from_origin(m["x0"]-m["dx"]/2, m["y0"]-m["dy"]/2, m["dx"], abs(m["dy"]))
out=R/"data/raw/nisar_l/coast"
for p in pols:
    fs=sorted(glob.glob(str(C/f"{p}_*.npy"))); assert len(fs)==41,len(fs)
    a=np.concatenate([np.load(f) for f in fs],0)
    assert a.shape==(m["r1"]-m["r0"],m["c1"]-m["c0"]),a.shape
    with np.errstate(divide="ignore",invalid="ignore"): a=10*np.log10(a)
    a[~np.isfinite(a)]=np.nan
    f=out/f"{short}_{p}.tif"; save_tif(f,a,tr,m["epsg"])
    print(f.name,a.shape,m["epsg"],f"median={np.nanmedian(a):.2f} nan={np.isnan(a).mean():.3f} bytes={f.stat().st_size} sha256={hashlib.sha256(f.read_bytes()).hexdigest()} src={Path(m['url']).name}",flush=True)
    del a
shutil.rmtree(C)
