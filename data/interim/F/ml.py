# 5x5 block mean in linear power, back to dB. Resumable per (date,pol). NaN if any of the 25 px NaN (strict).
import rasterio, numpy as np, os, sys, time
B=os.path.expanduser('~/mnt/nsa/05_Code/spacebros-nisar/data/interim/B/aligned/')
K=5; t0=time.time()
for d in ['20261016','20261028','20261109','20261004']:
  for p in ['hh','hv']:
    out=f'/tmp/F/{d}_{p}.npy'
    if os.path.exists(out): continue
    if time.time()-t0>110: sys.exit(0)
    with rasterio.open(B+f'nisar_l_coast_{d}_t55_{p}_db_aligned.tif') as s:
      H,W=s.height,s.width; nr=H//K; nc=W//K; res=np.full((nr,nc),np.nan,np.float32)
      for r0 in range(0,nr,100):
        r1=min(nr,r0+100)
        a=s.read(1,window=((r0*K,r1*K),(0,nc*K))).astype(np.float32)
        lin=10**(a/10); lin=lin.reshape(r1-r0,K,nc,K)
        m=lin.mean(axis=(1,3)); m[np.isnan(lin).any(axis=(1,3))]=np.nan
        res[r0:r1]=10*np.log10(m)
    np.save(out+'.tmp.npy',res); os.rename(out+'.tmp.npy',out); print(d,p,time.time()-t0,flush=True)
print('done')
