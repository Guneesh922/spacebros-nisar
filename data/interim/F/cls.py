import numpy as np
L=lambda d,p:np.load(f'/tmp/F/{d}_{p}.npy')
pw=np.load('/tmp/F/jrc_mask.npy')
PAIRS={'normal':('20261004','20261016'),'20261028':('20261016','20261028'),'20261109':('20261016','20261109')}
def load(pair):
    a,b=PAIRS[pair]; return L(a,'hh'),L(b,'hh'),L(a,'hv'),L(b,'hv')
def valid(hh0,hh1,hv0,hv1): return ~pw&np.isfinite(hh0)&np.isfinite(hh1)&np.isfinite(hv0)&np.isfinite(hv1)
# normal-pair stats
n=load('normal'); vn=valid(*n)
dn_hh=(n[1]-n[0])[vn]; dn_hv=(n[3]-n[2])[vn]
MED_HH,MED_HV=np.median(dn_hh),np.median(dn_hv)
SIG_HH=1.4826*np.median(abs(dn_hh-MED_HH)); SIG_HV=1.4826*np.median(abs(dn_hv-MED_HV))
def classify(pair,kw=3.0,kc=3.0,kv=1.0,tw=-17.0):
    hh0,hh1,hv0,hv1=load(pair); v=valid(hh0,hh1,hv0,hv1)
    dh=(hh1-hh0)-MED_HH; dv=(hv1-hv0)-MED_HV
    with np.errstate(invalid='ignore'):
        w=(hh1<tw)&(hh0>=tw)&(dh<=-kw*SIG_HH)
        c=(dh>=kc*SIG_HH)&(dv>=kv*SIG_HV)&~w
    cls=np.zeros(hh0.shape,np.uint8); cls[v]=1; cls[v&c]=3; cls[v&w]=2   # 0 invalid,1 none,2 water,3 crops
    return cls
if __name__=='__main__':
    print('MED',MED_HH,MED_HV,'SIG',SIG_HH,SIG_HV)
    for kw,kc,kv in [(3,3,1),(3,3,0),(3,3,1.5),(2,2,1),(4,4,1),(3,4,1),(2,3,1)]:
        r=[]
        for p in PAIRS:
            c=classify(p,kw,kc,kv); nv=(c>0).sum(); r.append((p,round(100*(c==2).sum()/nv,2),round(100*(c==3).sum()/nv,2)))
        print(kw,kc,kv,r)
    for tw in (-16,-17,-18):
        print('tw',tw,[(p,round(100*(classify(p,3,3,1,tw)==2).sum()/(classify(p)>0).sum(),2)) for p in PAIRS])
