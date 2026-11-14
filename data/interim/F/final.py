import numpy as np, json, csv, os, sys
sys.path.insert(0,'.')
import cls as C
from scipy.ndimage import binary_dilation
import rasterio
from rasterio.features import rasterize
from rasterio.transform import Affine
from rasterio.warp import reproject, Resampling, calculate_default_transform, array_bounds
from shapely.geometry import shape, mapping
from shapely.ops import transform as stransform
from pyproj import Transformer
from PIL import Image
R=os.path.expanduser('~/mnt/nsa/05_Code/spacebros-nisar/')
TR=Affine(50,0,563830,0,-50,1891320); SH=(2003,2144)
# edge mask: union of NaN over all 8 rasters, dilated 2 px (100 m)
allnan=np.zeros(SH,bool)
for d in ['20261004','20261016','20261028','20261109']:
    for p in ['hh','hv']: allnan|=np.isnan(C.L(d,p))
EDGE=binary_dilation(allnan,iterations=2)
def classk(pair,k):
    c=C.classify(pair,kw=k,kc=k,kv=1.0); c[EDGE]=0; return c
base={p:classk(p,3.0) for p in C.PAIRS}; lo={p:classk(p,4.0) for p in C.PAIRS}; hi={p:classk(p,2.0) for p in C.PAIRS}
def shares(c):
    n=(c>0).sum(); return dict(n=int(n),water=100*(c==2).sum()/n,crops=100*(c==3).sum()/n,none=100*(c==1).sum()/n)
summ={}
for p in C.PAIRS:
    summ[p]={'base':shares(base[p]),'k4':shares(lo[p]),'k2':shares(hi[p])}
json.dump(summ,open('class_shares_summary.json','w'),indent=1)
print(json.dumps(summ,indent=1))
# PNGs on WGS84 grid
dtr,w,h=calculate_default_transform('EPSG:32644','EPSG:4326',SH[1],SH[0],*rasterio.transform.array_bounds(SH[0],SH[1],TR)[:0] or (563830,1891320-2003*50,563830+2144*50,1891320),resolution=0.00045)
S,W_,N,E=None,None,None,None
bounds={}
for pair in ['20261109','20261028']:
    out=np.zeros((h,w),np.uint8)
    reproject(base[pair],out,src_transform=TR,src_crs='EPSG:32644',dst_transform=dtr,dst_crs='EPSG:4326',resampling=Resampling.nearest,src_nodata=0,dst_nodata=0)
    L_,B_,R_,T_=array_bounds(h,w,dtr)
    bounds[pair]=[[round(B_,5),round(L_,5)],[round(T_,5),round(R_,5)]]
    for name,idx,col,alpha in [('new_water',2,(0x2A,0x6F,0xB0),255),('wet_crops',3,(0xE0,0x9A,0x2B),255),('no_change',1,(200,205,210),40)]:
        im=Image.fromarray((out==idx).astype(np.uint8),'P'); pal=[0]*768; pal[3:6]=col; im.putpalette(pal)
        im.info['transparency']=bytes([0,alpha]); f=f'class_{pair}_{name}.png'
        im.save(f,optimize=True,transparency=bytes([0,alpha]))
        print(f,os.path.getsize(f)//1024,'KB',im.size)
json.dump({'crs':'EPSG:4326','format':'[[S,W],[N,E]]','bounds':bounds,'size_px':[w,h],'note':'nearest-neighbour warp of the 50 m UTM44N class grid to a 0.00045 deg grid; bounds are exact for these PNGs'},open('class_png_bounds.json','w'),indent=1)
# mandals
gj=json.load(open(R+'data/processed/mandals.geojson'))
rows=list(csv.DictReader(open(R+'data/interim/C/mandal_district_2022_complete.csv')))
dist={r['shapeID']:r for r in rows}
tf=Transformer.from_crs(4326,32644,always_xy=True).transform
feats=[]
for ft in gj['features']:
    g=stransform(tf,shape(ft['geometry'])); feats.append((ft['properties'],g))
ids=rasterize([(g,i+1) for i,(p,g) in enumerate(feats)],out_shape=SH,transform=TR,fill=0,dtype='int32')
pwm=np.load('/tmp/F/jrc_mask.npy')
out=[]
for i,(pr,g) in enumerate(feats):
    m=ids==i+1; tot=int(m.sum()); land=int((m&~pwm).sum())
    d=dist.get(pr['shapeID'],{})
    rec={'mandal':pr['name'],'shapeID':pr['shapeID'],'district':d.get('district_2022') or None,'frac_in_box':float(d.get('frac_inside_delta_box') or 0),'poly_px':tot,'land_px':land}
    def sh(c):
        v=int((m&(c>0)).sum()); 
        if v==0: return None
        return v,100*int((m&(c==2)).sum())/v,100*int((m&(c==3)).sum())/v
    b=sh(base['20261109']); rec['valid_px']=b[0] if b else 0
    rec['coverage_pct']=round(100*rec['valid_px']/land,1) if land else 0.0
    for pair in ['20261109','20261028']:
        b=sh(base[pair]); l=sh(lo[pair]); h_=sh(hi[pair])
        if b:
            rec[f'water_{pair}']=b[1]; rec[f'crops_{pair}']=b[2]
            rec[f'water_err_{pair}']=max(abs(l[1]-b[1]),abs(h_[1]-b[1])); rec[f'crops_err_{pair}']=max(abs(l[2]-b[2]),abs(h_[2]-b[2]))
            rec[f'none_{pair}']=100-b[1]-b[2]
        c=sh(hi[pair]); 
    nb=sh(base['normal']); 
    if nb: rec['normal_water']=nb[1]; rec['normal_crops']=nb[2]; rec['normal_pct']=nb[1]+nb[2]
    out.append(rec)
# eligible
for r in out:
    fl=[]
    if not r['district']: fl.append('no district')
    if r['valid_px']<200: fl.append('<200 valid px')
    if r['coverage_pct']<50: fl.append('valid coverage <50%')
    if r['frac_in_box']<0.5: fl.append('<50% of mandal inside delta box')
    r['flag']='; '.join(fl)
for pair in ['20261109','20261028']:
    el=sorted([r for r in out if not r['flag'] and f'water_{pair}' in r],key=lambda r:-r[f'water_{pair}'])
    for k,r in enumerate(el): r[f'rank_{pair}']=k+1
rf=lambda x:round(x,2)
json_rows=[]
for r in sorted([r for r in out if r['district'] and r['valid_px']>0 and 'water_20261109' in r],key=lambda r:(r.get('rank_20261109') is None,r.get('rank_20261109') or 0,-r['water_20261109'])):
    json_rows.append({'mandal':r['mandal'],'district':r['district'],'water_pct':rf(r['water_20261109']),'water_err':rf(r['water_err_20261109']),'crops_pct':rf(r['crops_20261109']),'crops_err':rf(r['crops_err_20261109']),'normal_pct':rf(r.get('normal_pct',0)),'rank':r.get('rank_20261109'),'coverage_pct':r['coverage_pct'],'flag':r['flag'] or None})
J={'analysis_id':'ap_delta_oct_nov_2026','period':['2026-10-16','2026-11-09'],'normal_period':['2026-10-04','2026-10-16'],
 'note':'Shares of valid (non-masked) 50 m pixels in percent: likely new open water (water_pct), likely wet or flooded crops (crops_pct). normal_pct = water+crops share for the normal pair 4-16 Oct with the same thresholds. *_err = largest shift when thresholds move by +/-1 sigma. rank = by water_pct among mandals with >=50% valid coverage; null = flagged, not ranked. 9 Nov combines Arnab and Murasu (1-3 Nov).',
 'rows':json_rows}
json.dump(J,open('mandal_rank.json','w'),indent=1)
cols=list(out[0].keys())
allk=sorted({k for r in out for k in r}, key=lambda k:(k not in ('mandal','shapeID','district'),k))
with open('mandal_rank.csv','w',newline='') as f:
    wr=csv.DictWriter(f,fieldnames=allk); wr.writeheader()
    for r in out: wr.writerow({k:(rf(v) if isinstance(v,float) else v) for k,v in r.items()})
print(len(out),len(json_rows),sum(1 for r in json_rows if r['rank']))
for r in json_rows[:8]: print(r)
print([ (r['mandal'],r['flag']) for r in json_rows if r['flag']][:20])
