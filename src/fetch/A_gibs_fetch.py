"""Package A: NASA GIBS WMS GetMap snapshots. Usage: A_gibs_fetch.py <stage>  (himawari|viirs|imerg|p2)"""
import sys, io, json, hashlib, datetime, urllib.request, urllib.parse, os
import numpy as np
from PIL import Image
OUT = "data/raw/gibs"
BASE = "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi"
BOXES = {  # W,S,E,N and pixel size
    "context": ((78, 12, 88, 20), 2000, 1600),
    "sea": ((81, 15, 85, 18), 1600, 1200),
    "delta": ((81.6, 16.2, 82.6, 17.1), 1000, 900),
}
results = []
def fetch(layer, time, box, short, tstr, ext):
    (w, s, e, n), W, H = BOXES[box]
    fmt = "image/jpeg" if ext == "jpg" else "image/png"
    q = {"SERVICE": "WMS", "REQUEST": "GetMap", "VERSION": "1.3.0", "LAYERS": layer, "CRS": "EPSG:4326",
         "BBOX": f"{s},{w},{n},{e}", "WIDTH": W, "HEIGHT": H, "FORMAT": fmt}
    if time: q["TIME"] = time
    url = BASE + "?" + urllib.parse.urlencode(q, safe=":,")
    name = f"{short}_{tstr}_{box}.{ext}" if tstr else f"{short}_{box}.{ext}"
    path = f"{OUT}/{name}"
    rec = {"file": path, "url": url, "layer": layer, "time": time}
    try:
        with urllib.request.urlopen(url, timeout=90) as r:
            data = r.read(); ctype = r.headers.get("Content-Type")
        if not ctype.startswith("image/"):
            raise RuntimeError(f"non-image response {ctype}: {data[:300]!r}")
        im = Image.open(io.BytesIO(data)); im.load()
        arr = np.asarray(im)
        std = float(arr[..., :3].std()) if arr.ndim == 3 else float(arr.std())
        alpha_nonzero = int((arr[..., 3] > 0).sum()) if arr.ndim == 3 and arr.shape[2] == 4 else None
        tmp = path + ".part"
        open(tmp, "wb").write(data); os.replace(tmp, path)
        side = {"layer": layer, "time": time, "bbox_wsen": [w, s, e, n], "crs": "EPSG:4326", "width": W, "height": H,
                "url": url, "fetched_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
        json.dump(side, open(path.rsplit(".", 1)[0] + ".json", "w"), indent=1)
        rec.update(ok=True, bytes=len(data), size=im.size, mode=im.mode, std=round(std, 2), alpha_nonzero=alpha_nonzero,
                   sha256=hashlib.sha256(data).hexdigest())
    except Exception as ex:
        rec.update(ok=False, error=repr(ex)[:400])
    print(json.dumps({k: v for k, v in rec.items() if k != "url"}), flush=True)
    results.append(rec)

def stage(st):
    if st == "himawari":
        for t in ["2026-10-27T13:00:00Z", "2026-10-27T12:50:00Z", "2026-10-27T13:10:00Z", "2026-10-28T00:00:00Z"]:
            for b in ["sea", "context"]:
                fetch("Himawari_AHI_Band13_Clean_Infrared", t, b, "himawari_b13", t.replace("-", "").replace(":", "")[:13] + "Z", "png")
    elif st == "viirs":
        sats = {"snpp": "VIIRS_SNPP", "noaa20": "VIIRS_NOAA20", "noaa21": "VIIRS_NOAA21"}
        for d in ["2026-10-27", "2026-10-26", "2026-10-28", "2026-10-29"]:
            for sk, sl in sats.items():
                for b in ["sea", "context", "delta"]:
                    fetch(f"{sl}_CorrectedReflectance_TrueColor", d, b, f"viirs_{sk}_truecolor", d, "jpg")
    elif st == "imerg":
        for d in ["2026-10-26", "2026-10-27", "2026-10-28", "2026-10-29"]:
            for b in ["sea", "context"]:
                fetch("IMERG_Precipitation_Rate", d, b, "imerg_daily", d, "png")
        for t in ["2026-10-27T12:30:00Z", "2026-10-27T13:00:00Z", "2026-10-27T13:30:00Z", "2026-10-28T00:00:00Z"]:
            for b in ["sea", "context"]:
                fetch("IMERG_Precipitation_Rate_30min", t, b, "imerg_30min", t.replace("-", "").replace(":", "")[:13] + "Z", "png")
    elif st == "p2":
        for sk, sl in {"snpp": "VIIRS_SNPP", "noaa20": "VIIRS_NOAA20"}.items():
            fetch(f"{sl}_Brightness_Temp_BandI5_Night", "2026-10-27", "context", f"viirs_i5night_{sk}", "2026-10-27", "png")
        for lay, sh in [("Coastlines_15m", "ref_Coastlines_15m"), ("Reference_Labels_15m", "ref_Reference_Labels_15m")]:
            for b in ["context", "sea", "delta"]:
                fetch(lay, None, b, sh, None, "png")
    json.dump(results, open(f"data/logs/A_results_{st}.json", "w"), indent=1)

for s in sys.argv[1:]:
    stage(s)
