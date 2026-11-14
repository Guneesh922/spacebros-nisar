import sys, time, json, numpy as np
from pathlib import Path
T0=time.time(); DEADLINE=float(sys.argv[3]) if len(sys.argv)>3 else 160
R=Path.home()/"mnt/nsa/05_Code/spacebros-nisar"
sys.path.insert(0,str(R/"src")); sys.path.insert(0,str(R/"src/fetch"))
import subset_arnab as sa
from gcov_subset import epsg_of, find_grid, save_tif
import earthaccess, h5py
sid=sys.argv[1]; fb=sys.argv[2]=="UR"
earthaccess.login(persist=False); fs=earthaccess.get_fsspec_https_session()
prio,coll,fid,box,pols,step,short=sa.SCENES[sid]
u=sa.url(*sa.UR_FALLBACK[sid]) if fb else sa.url(coll,fid)
C=Path("/tmp/Bwork/cache")/f"{sid}_{'UR' if fb else 'PR'}"; C.mkdir(parents=True,exist_ok=True)
h5=h5py.File(fs.open(u,block_size=8*1024*1024,cache_type="blockcache"),"r")
g=find_grid(h5,"A"); epsg=epsg_of(g)
x,y,c0,c1,r0,r1=sa.window(g,sa.BOX[box],epsg)
print(f"opened in {time.time()-T0:.0f}s EPSG {epsg} rows {r0}:{r1} cols {c0}:{c1} dy_sign {np.sign(y[1]-y[0])}",flush=True)
meta=dict(epsg=int(epsg),r0=int(r0),r1=int(r1),c0=int(c0),c1=int(c1),x0=float(x[c0]),dx=float(x[1]-x[0]),y0=float(y[r0]),y1=float(y[r1-1]),dy=float(y[1]-y[0]),url=u)
json.dump(meta,open(C/"meta.json","w"))
CH=250; done=True
for p in pols:
    for i,rs in enumerate(range(r0,r1,CH)):
        f=C/f"{p}_{i:03d}.npy"
        if f.exists(): continue
        if time.time()-T0>DEADLINE: done=False; break
        re=min(rs+CH,r1); a=g[p][rs:re,c0:c1].astype("float32"); np.save(f,a)
        print(f"{p} chunk {i} rows {rs}:{re} t={time.time()-T0:.0f}s",flush=True)
    if not done: break
print("COMPLETE" if done else "PARTIAL",flush=True)
