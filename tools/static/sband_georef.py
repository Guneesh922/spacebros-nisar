"""One-off: put the two S-band colour pictures of Cyclone Arnab on the map grid.

NOT part of the pipeline (tools/pipeline/run_all.py never calls this). The pictures are static event
material: there is no H5 behind them. Input: the two pictures as received from the team (pseudo-colour
HH / HV / HH-HV of the NISAR S-band GCOV frame 10, track 55), which are the full product grid in
UTM 44N. The grid extent and the swath corners come from the Bhoonidhi catalogue rows in
data/reference/nisar_s_candidates.csv (ProdLatLon, ImgLatLon). Output: one WebP per date with a
transparent background, rows linear in Web Mercator y so Leaflet's imageOverlay places every pixel
correctly, plus sband.json with the bounds.

Run:  python tools/static/sband_georef.py     (needs numpy, pillow, pyproj)
"""
import csv, json, math, os
import numpy as np
from PIL import Image, ImageDraw
from pyproj import Transformer

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, 'data', 'static', 'sband')
OUT = os.path.join(ROOT, 'app', 'dashboard-mockup', 'img', 'sband')
DATES = ['2026-10-16', '2026-10-28']
STEP = 0.002   # output posting in degrees of longitude (source is about 213 m)

def rows():
    csv.field_size_limit(10 ** 9)
    out = {}
    with open(os.path.join(ROOT, 'data', 'reference', 'nisar_s_candidates.csv')) as f:
        for r in csv.DictReader(f):
            p = json.loads(r['properties'])
            if r['collection'] == 'NISAR_SSAR_GCOV' and p.get('Frame') == 10 and p.get('Track') == 55:
                out[r['datetime'][:10]] = (r, p)
    return out

def merc(lat):
    return np.log(np.tan(np.pi / 4 + np.radians(lat) / 2))

def main():
    cat = rows()
    to_utm = Transformer.from_crs(4326, 32644, always_xy=True)
    polys = {d: [(float(a), float(b)) for a, b in cat[d][1]['ImgLatLon'][:4]] for d in DATES}
    lons = [p[0] for d in DATES for p in polys[d]]; lats = [p[1] for d in DATES for p in polys[d]]
    w, e, s, n = min(lons), max(lons), min(lats), max(lats)
    W = int(round((e - w) / STEP)); H = int(round(W * (math.degrees(float(merc(n) - merc(s)))) / (e - w)))
    lon = w + (np.arange(W) + 0.5) * (e - w) / W
    my = merc(n) - (np.arange(H) + 0.5) * (merc(n) - merc(s)) / H
    lat = np.degrees(2 * np.arctan(np.exp(my)) - np.pi / 2)
    LON, LAT = np.meshgrid(lon, lat)
    X, Y = to_utm.transform(LON, LAT)
    meta = {'note': 'Static event pictures, not pipeline output. Built by tools/static/sband_georef.py.', 'bounds': [[round(s, 5), round(w, 5)], [round(n, 5), round(e, 5)]], 'scenes': []}
    for d in DATES:
        r, p = cat[d]
        prod = [to_utm.transform(float(a), float(b)) for a, b in p['ProdLatLon'][:4]]
        x0, x1 = min(q[0] for q in prod), max(q[0] for q in prod); y0, y1 = min(q[1] for q in prod), max(q[1] for q in prod)
        im = Image.open(os.path.join(SRC, 'sband_coast_rgb_%s_src.webp' % d.replace('-', ''))).convert('RGB')
        a = np.asarray(im).astype(np.float32); sh, sw = a.shape[:2]
        px = (X - x0) / (x1 - x0) * sw - 0.5; py = (y1 - Y) / (y1 - y0) * sh - 0.5
        ok = (px >= 0) & (px <= sw - 1) & (py >= 0) & (py <= sh - 1)
        pxc = np.clip(px, 0, sw - 1.001); pyc = np.clip(py, 0, sh - 1.001)
        ix = pxc.astype(int); iy = pyc.astype(int); fx = (pxc - ix)[..., None]; fy = (pyc - iy)[..., None]
        v = (a[iy, ix] * (1 - fx) + a[iy, ix + 1] * fx) * (1 - fy) + (a[iy + 1, ix] * (1 - fx) + a[iy + 1, ix + 1] * fx) * fy
        # alpha: inside the swath polygon of this date (drawn in output pixels, pulled in by 2 px to hide the edge fringe)
        def to_px(lo, la):
            return ((lo - w) / (e - w) * W, float((merc(n) - merc(la)) / (merc(n) - merc(s)) * H))
        cx = sum(q[0] for q in polys[d]) / 4; cy = sum(q[1] for q in polys[d]) / 4
        pts = []
        for lo, la in polys[d]:
            ax, ay = to_px(lo, la); bx, by = to_px(cx, cy); L = math.hypot(ax - bx, ay - by)
            pts.append((ax + (bx - ax) * 3 / L, ay + (by - ay) * 3 / L))
        m = Image.new('L', (W, H), 0); ImageDraw.Draw(m).polygon(pts, fill=255)
        alpha = np.asarray(m) * ok
        out = np.dstack([np.clip(v, 0, 255).astype(np.uint8), alpha.astype(np.uint8)])
        name = 'sband_coast_rgb_%s.webp' % d.replace('-', '')
        Image.fromarray(out, 'RGBA').save(os.path.join(OUT, name), 'WEBP', quality=88, method=6)
        meta['scenes'].append({'date': d, 'time_utc': r['datetime'], 'file': name, 'granule': r['id'], 'track': p['Track'], 'frame': p['Frame'],
                               'direction': p['Node'].lower(), 'polarisation': 'HH+HV', 'size_px': [W, H], 'swath': polys[d]})
        print(name, W, H, os.path.getsize(os.path.join(OUT, name)) // 1024, 'KB')
    json.dump(meta, open(os.path.join(OUT, 'sband.json'), 'w'), indent=1)
    print(meta['bounds'])

if __name__ == '__main__':
    main()
