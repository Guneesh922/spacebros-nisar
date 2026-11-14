"""Package E helper: list geoBoundaries ADM3 names whose bbox intersects the delta box (own temp list; package C owns the real clip)."""
import json, sys, os
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
W,S,E,N = 81.6,16.2,82.6,17.1
d = json.load(open(os.path.join(ROOT,"data/raw/boundaries/geoBoundaries-IND-ADM3.geojson")))
def pts(c):
    if isinstance(c[0],(int,float)): yield c
    else:
        for x in c: yield from pts(x)
out=[]
for f in d["features"]:
    p=list(pts(f["geometry"]["coordinates"]))
    xs=[a[0] for a in p]; ys=[a[1] for a in p]
    if min(xs)<=E and max(xs)>=W and min(ys)<=N and max(ys)>=S:
        out.append((f["properties"].get("shapeName"),round(min(xs),3),round(min(ys),3),round(max(xs),3),round(max(ys),3)))
print(len(out), list(d["features"][0]["properties"].keys()))
for o in sorted(out): print(o)
