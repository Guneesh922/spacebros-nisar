"""Download the public NISAR quick-look images for one track and crop them to the
study area. No Earthdata login needed. Good for a first time-lapse and for the demo.

Writes data/browse/<aoi>_T<track>/<date>.jpg and a timelapse.gif in the same folder.

Usage:
  python src/nisar_search.py              # run first, makes app/scenes.json
  python src/fetch_browse.py --track 106  # descending pass, ~28 dates over Delhi
"""
import argparse
import io
import json
from concurrent.futures import ThreadPoolExecutor

import requests
from PIL import Image, ImageDraw

import config


def crop(scene, bbox, scale):
    img = Image.open(io.BytesIO(requests.get(scene["browse_png"], timeout=120).content)).convert("RGB")
    (s, w), (n, e) = scene["bounds"]
    W, H = img.size
    aw, as_, ae, an = bbox

    def px(lon, lat):
        return round((lon - w) / (e - w) * W), round((n - lat) / (n - s) * H)

    x0, y0 = px(aw, an)
    x1, y1 = px(ae, as_)
    out = img.crop((x0, y0, x1, y1))
    return out.resize((out.width * scale, out.height * scale), Image.NEAREST)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--track", type=int, required=True)
    ap.add_argument("--scale", type=int, default=1, help="upscale factor for the crops")
    args = ap.parse_args()

    meta = json.loads((config.APP / "scenes.json").read_text())
    scenes = [s for s in meta["scenes"] if s["track"] == args.track]
    if not scenes:
        raise SystemExit(f"No scenes for track {args.track}. Tracks: {sorted({s['track'] for s in meta['scenes']})}")
    bbox = meta["bbox"]
    out_dir = config.BROWSE / f"{meta['aoi']}_T{args.track}"
    out_dir.mkdir(parents=True, exist_ok=True)

    with ThreadPoolExecutor(6) as pool:
        crops = list(pool.map(lambda s: crop(s, bbox, args.scale), scenes))

    frames = []
    for s, im in zip(scenes, crops):
        im.save(out_dir / f"{s['date']}.jpg", quality=88)
        f = im.copy()
        ImageDraw.Draw(f).text((8, 8), f"NISAR L-band  {s['date']}  track {s['track']}", fill=(255, 255, 0))
        frames.append(f)
    frames[0].save(out_dir / "timelapse.gif", save_all=True, append_images=frames[1:], duration=400, loop=0)
    print(f"saved {len(frames)} crops + timelapse.gif to {out_dir}")


if __name__ == "__main__":
    main()
