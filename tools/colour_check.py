#!/usr/bin/env python3
"""colour_check.py: numeric colour checks and the before/after contact sheet for the map layers.

  python tools/colour_check.py              print the numeric checks (contrast, colour-vision simulation, ramp)
  python tools/colour_check.py --md         same, and write the tables between the markers in docs/review/COLOUR_CHECK.md
  python tools/colour_check.py --sheet OUT.png [--before DIR]
                                            contact sheet of every layer over the dark basemap colour (AFTER = data/web,
                                            BEFORE = DIR, a copy of the old data/web PNGs); stacks BEFORE above AFTER when given

What is computed (all from the palette constants in tools/build_web.py and the CSS variables in app/css/tokens.css and
app/dashboard-mockup/css/dash.css, so a palette change in build_web.py is checked automatically):
  1. WCAG 2.x contrast ratio of every map colour against the basemap and against the UI (card, stage, legend background and text).
  2. Colour-vision simulation, Machado, Oliveira and Fernandes 2009, severity 1.0, applied in LINEAR RGB (protanopia and
     deuteranopia), then CIEDE2000 between every pair of class colours (and with the 'no change' tint left out: it is meant
     to be near transparent) and along the diverging ramp.
  3. The diverging ramp: lightness (CIELAB L*) must rise or fall monotonically away from the centre on each side.
No third-party colour library: sRGB -> linear -> XYZ (D65) -> CIELAB, CIEDE2000 written out below.
"""
import argparse
import itertools
import json
import math
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

# Esri "Dark Gray Canvas" land colour is close to this; there is no way to read the tile colour exactly from here, so this
# value is an approximation chosen once and used for every number in this file. State it wherever a result is quoted.
BASEMAP_HEX = "#2B2B2B"
MD = os.path.join(ROOT, "docs", "review", "COLOUR_CHECK.md")
MARK_A, MARK_B = "<!-- colour_check:begin -->", "<!-- colour_check:end -->"


# ----------------------------------------------------------------------------- colour maths
def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def to_hex(rgb):
    return "#%02X%02X%02X" % tuple(int(round(max(0, min(255, c)))) for c in rgb)


def lin(c8):
    c = c8 / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def unlin(c):
    c = max(0.0, min(1.0, c))
    return 255.0 * (12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055)


def luminance(rgb):
    r, g, b = (lin(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def blend(fg, alpha, bg):
    """fg over bg with alpha 0..1 -> rgb floats"""
    return tuple(alpha * f + (1 - alpha) * b for f, b in zip(fg, bg))


# Machado et al. 2009, severity 1.0, to be applied to LINEAR rgb
MACHADO = {
    "protanopia": ((0.152286, 1.052583, -0.204868), (0.114503, 0.786281, 0.099216), (-0.003882, -0.048116, 1.051998)),
    "deuteranopia": ((0.367322, 0.860646, -0.227968), (0.280085, 0.672501, 0.047413), (-0.011820, 0.042940, 0.968881)),
}


def simulate(rgb, kind):
    if kind == "normal":
        return tuple(float(c) for c in rgb)
    m = MACHADO[kind]
    v = [lin(c) for c in rgb]
    return tuple(unlin(sum(m[i][j] * v[j] for j in range(3))) for i in range(3))


def lab(rgb):
    r, g, b = (lin(c) for c in rgb)
    x = (0.4124564 * r + 0.3575761 * g + 0.1804375 * b) / 0.95047
    y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    z = (0.0193339 * r + 0.1191920 * g + 0.9503041 * b) / 1.08883

    def f(t):
        return t ** (1 / 3) if t > 216 / 24389 else (24389 / 27 * t + 16) / 116
    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def de2000(l1, l2):
    L1, a1, b1 = l1
    L2, a2, b2 = l2
    C1, C2 = math.hypot(a1, b1), math.hypot(a2, b2)
    Cm = (C1 + C2) / 2
    G = 0.5 * (1 - math.sqrt(Cm ** 7 / (Cm ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360 if C1p else 0.0
    h2p = math.degrees(math.atan2(b2, a2p)) % 360 if C2p else 0.0
    dLp, dCp = L2 - L1, C2p - C1p
    if C1p * C2p == 0:
        dhp = 0.0
    else:
        dhp = h2p - h1p
        dhp = dhp - 360 if dhp > 180 else dhp + 360 if dhp < -180 else dhp
    dHp = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dhp / 2))
    Lpm, Cpm = (L1 + L2) / 2, (C1p + C2p) / 2
    if C1p * C2p == 0:
        hpm = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        hpm = (h1p + h2p) / 2
    else:
        hpm = (h1p + h2p + 360) / 2 if h1p + h2p < 360 else (h1p + h2p - 360) / 2
    T = (1 - 0.17 * math.cos(math.radians(hpm - 30)) + 0.24 * math.cos(math.radians(2 * hpm))
         + 0.32 * math.cos(math.radians(3 * hpm + 6)) - 0.20 * math.cos(math.radians(4 * hpm - 63)))
    dth = 30 * math.exp(-(((hpm - 275) / 25) ** 2))
    Rc = 2 * math.sqrt(Cpm ** 7 / (Cpm ** 7 + 25 ** 7))
    Sl = 1 + 0.015 * (Lpm - 50) ** 2 / math.sqrt(20 + (Lpm - 50) ** 2)
    Sc, Sh = 1 + 0.045 * Cpm, 1 + 0.015 * Cpm * T
    Rt = -math.sin(math.radians(2 * dth)) * Rc
    return math.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2 + Rt * (dCp / Sc) * (dHp / Sh))


def de(rgb1, rgb2):
    return de2000(lab(rgb1), lab(rgb2))


# ----------------------------------------------------------------------------- inputs read from the repo
def css_vars():
    """--name: #hex from tokens.css (the only file with hex values)."""
    out = {}
    with open(os.path.join(ROOT, "app", "css", "tokens.css"), encoding="utf-8") as fh:
        for m in re.finditer(r"(--[a-z0-9-]+):\s*(#[0-9A-Fa-f]{6})", fh.read()):
            out[m.group(1)] = m.group(2).upper()
    return out


def legend_colours(v):
    """The map legend (.legend in dash.css): background = var(--stage-glass) = 92 % --stage over the map, text --white,
    muted text --on-stage-muted. Returns (background rgb as seen over the basemap, text white, muted text)."""
    bg = blend(hex_rgb(v["--stage"]), 0.92, hex_rgb(BASEMAP_HEX))
    return bg, hex_rgb(v["--white"]), hex_rgb(v["--on-stage-muted"])


def load_palette():
    import build_web as bw
    return bw


def class_colours(bw):
    out = {}
    for k, rgba in bw.CLASS_RGBA.items():
        out[k] = rgba
    return out


# ----------------------------------------------------------------------------- numeric checks
def run_checks():
    bw = load_palette()
    v = css_vars()
    base = hex_rgb(BASEMAP_HEX)
    lines, results = [], {}

    def P(s=""):
        lines.append(s)
        print(s)

    P("Basemap assumed: %s (approximation of Esri Dark Gray Canvas)" % BASEMAP_HEX)
    P("Distance measure: CIEDE2000 (dE00). Colour-vision model: Machado et al. 2009, severity 1.0, in linear RGB.")
    P()

    # ---- classes
    cls = class_colours(bw)
    with open(os.path.join(ROOT, "data", "processed", "manifest.json"), encoding="utf-8") as fh:
        man = {l["id"]: l for l in json.load(fh)["layers"]}
    opac_of = {k: man.get("nisar_class_" + k, {}).get("opacity", 0.75) for k in cls}   # layer opacity in the manifest
    P("### Class colours")
    P("| class | colour | alpha | layer opacity | contrast vs basemap (raw colour) | contrast vs basemap (as drawn: alpha x layer opacity) |")
    P("|---|---|---|---|---|---|")
    eff = {}
    for k, (r, g, b, a) in cls.items():
        raw = contrast((r, g, b), base)
        e = blend((r, g, b), opac_of[k] * a / 255.0, base)
        eff[k] = e
        P("| %s | %s | %d | %.2f | %.2f:1 | %.2f:1 (drawn as %s) |" % (k, to_hex((r, g, b)), a, opac_of[k], raw, contrast(e, base), to_hex(e)))
    results["class_contrast"] = {k: round(contrast(cls[k][:3], base), 2) for k in cls}
    P()
    shown = [k for k in cls if k != "no_change"]
    P("Pairwise dE00 between the classes that carry meaning (no_change is a near-transparent tint, listed apart):")
    P("| pair | normal vision | protanopia | deuteranopia |")
    P("|---|---|---|---|")
    mins = {"normal": 99.0, "protanopia": 99.0, "deuteranopia": 99.0}
    for a, b in itertools.combinations(shown, 2):
        row = []
        for kind in ("normal", "protanopia", "deuteranopia"):
            d = de(simulate(cls[a][:3], kind), simulate(cls[b][:3], kind))
            mins[kind] = min(mins[kind], d)
            row.append("%.1f" % d)
        P("| %s vs %s | %s |" % (a, b, " | ".join(row)))
    results["class_pair_min_de00"] = {k: round(x, 1) for k, x in mins.items()}
    P("Minimum over the pairs: normal %.1f, protanopia %.1f, deuteranopia %.1f (criterion >= 20)" % (mins["normal"], mins["protanopia"], mins["deuteranopia"]))
    P()
    P("Each class colour against the basemap as drawn (dE00, alpha x layer opacity), so a class does not vanish into the map:")
    P("| class | normal | protanopia | deuteranopia |")
    P("|---|---|---|---|")
    vb = {}
    for k in shown:
        row = []
        for kind in ("normal", "protanopia", "deuteranopia"):
            d = de(simulate(eff[k], kind), simulate(base, kind))
            row.append("%.1f" % d)
            vb[(k, kind)] = d
        P("| %s | %s |" % (k, " | ".join(row)))
    results["class_vs_basemap_min_de00"] = round(min(vb.values()), 1)
    P()
    nc = cls["no_change"]
    nce = blend(nc[:3], nc[3] / 255.0 * opac_of["no_change"], base)
    P("no_change tint: %s alpha %d; effective over the basemap %s (dE00 to basemap %.1f); intentionally faint." % (to_hex(nc[:3]), nc[3], to_hex(nce), de(nce, base)))
    P()

    P("Hue family check: each map colour against the UI token it is derived from (HLS hue in degrees; same family = within 10 degrees):")
    P("| class | token | token hue | map hue | token L* | map L* |")
    P("|---|---|---|---|---|---|")
    import colorsys
    for k, tok in (("new_water", "--water"), ("wet_crops", "--crops")):
        th = colorsys.rgb_to_hls(*[q / 255 for q in hex_rgb(v[tok])])[0] * 360
        mh = colorsys.rgb_to_hls(*[q / 255 for q in cls[k][:3]])[0] * 360
        P("| %s | %s %s | %.0f | %.0f | %.0f | %.0f |" % (k, tok, v[tok], th, mh, lab(hex_rgb(v[tok]))[0], lab(cls[k][:3])[0]))
    results["hue_delta"] = {}
    P()

    # ---- UI contrast
    bg, wh, mu = legend_colours(v)
    P("### UI contrast (WCAG 2.x, AA needs >= 4.5:1 for text)")
    P("Legend (dash.css .legend): background = --stage-glass = 92 %% of --stage %s over the basemap = %s; text --white %s; muted text --on-stage-muted %s." % (v["--stage"], to_hex(bg), v["--white"], v["--on-stage-muted"]))
    P("| pair | ratio | AA text (4.5) |")
    P("|---|---|---|")
    ui = {}
    for name, fg, bgc in (("legend text (--white) on legend background", wh, bg), ("legend muted text (--on-stage-muted) on legend background", mu, bg),
                          ("card text (--ink) on --card", hex_rgb(v["--ink"]), hex_rgb(v["--card"])),
                          ("card secondary text (--ink-2) on --card", hex_rgb(v["--ink-2"]), hex_rgb(v["--card"])),
                          ("muted text (--muted) on --card", hex_rgb(v["--muted"]), hex_rgb(v["--card"])),
                          ("muted text (--muted) on --paper", hex_rgb(v["--muted"]), hex_rgb(v["--paper"]))):
        c = contrast(fg, bgc)
        ui[name] = round(c, 2)
        P("| %s | %.2f:1 | %s |" % (name, c, "pass" if c >= 4.5 else "FAIL"))
    results["ui_contrast"] = ui
    P()
    P("Map colours against the legend background and the card (non-text graphics need >= 3:1, WCAG 1.4.11):")
    P("| colour | vs legend bg | vs --card |")
    P("|---|---|---|")
    for k in shown:
        P("| %s %s | %.2f:1 | %.2f:1 |" % (k, to_hex(cls[k][:3]), contrast(cls[k][:3], bg), contrast(cls[k][:3], hex_rgb(v["--card"]))))
    P()

    # ---- diverging ramp
    P("### Diverging ramp (blue = darker, white = no change, orange-red = brighter)")
    stops = [(s[0], s[1]) for s in bw.DIFF_STOPS_UNIT]
    rows = []
    for t, hx in stops:
        rows.append((t, hx, hex_rgb(hx)))
    P("Stops at fractions of the saturation limit: " + ", ".join("%+.2f %s" % (t, hx) for t, hx, _ in rows))
    P("| stop | L* | contrast vs basemap | contrast vs legend bg |")
    P("|---|---|---|---|")
    for t, hx, rgb in rows:
        P("| %+.2f %s | %.1f | %.2f:1 | %.2f:1 |" % (t, hx, lab(rgb)[0], contrast(rgb, base), contrast(rgb, bg)))
    # monotone distance from the centre
    cen = next(r for r in rows if r[0] == 0.0)
    mono = {}
    for kind in ("normal", "protanopia", "deuteranopia"):
        ok = True
        detail = []
        for side in (-1, 1):
            seq = sorted((r for r in rows if r[0] * side > 0), key=lambda r: abs(r[0]))
            prev = 0.0
            for r in seq:
                d = de(simulate(r[2], kind), simulate(cen[2], kind))
                detail.append("%+.2f:%.1f" % (r[0], d))
                if d < prev - 1e-9:
                    ok = False
                prev = d
        mono[kind] = (ok, detail)
    P()
    P("dE00 from the centre (white) outwards, per colour vision; must grow with |value| on each side:")
    for kind, (ok, detail) in mono.items():
        P("- %s: %s -> %s" % (kind, ", ".join(detail), "monotone" if ok else "NOT monotone"))
    results["ramp_monotone_from_centre"] = {k: x[0] for k, x in mono.items()}
    # L* monotone (normal vision)
    lneg = [lab(r[2])[0] for r in sorted((r for r in rows if r[0] <= 0), key=lambda r: r[0])]
    lpos = [lab(r[2])[0] for r in sorted((r for r in rows if r[0] >= 0), key=lambda r: r[0])]
    lmono = all(a <= b + 1e-9 for a, b in zip(lneg, lneg[1:])) and all(a >= b - 1e-9 for a, b in zip(lpos, lpos[1:]))
    P("L* rises from the blue end to the centre and falls to the orange end (monotone): %s (neg side %s; pos side %s)" % (
        "yes" if lmono else "NO", ", ".join("%.0f" % x for x in lneg), ", ".join("%.0f" % x for x in lpos)))
    results["ramp_lightness_monotone"] = lmono
    ends = [rows[0], rows[-1]]
    gre = hex_rgb(bw.CHANGE_GREY_HEX)
    P()
    P("Blue end, orange end, white centre and the 'no clear change' grey, pairwise dE00:")
    P("| pair | normal | protanopia | deuteranopia |")
    P("|---|---|---|---|")
    items = [("blue end %s" % ends[0][1], ends[0][2]), ("orange end %s" % ends[1][1], ends[1][2]), ("white centre %s" % cen[1], cen[2]),
             ("grey (|change| < 1 sigma) %s" % bw.CHANGE_GREY_HEX, gre)]
    pm = {"normal": 99.0, "protanopia": 99.0, "deuteranopia": 99.0}
    for (na, ca), (nb, cb) in itertools.combinations(items, 2):
        row = []
        for kind in ("normal", "protanopia", "deuteranopia"):
            d = de(simulate(ca, kind), simulate(cb, kind))
            pm[kind] = min(pm[kind], d)
            row.append("%.1f" % d)
        P("| %s vs %s | %s |" % (na, nb, " | ".join(row)))
    results["ramp_end_pair_min_de00"] = {k: round(x, 1) for k, x in pm.items()}
    P("Minimum over these pairs: normal %.1f, protanopia %.1f, deuteranopia %.1f (criterion >= 20)" % (pm["normal"], pm["protanopia"], pm["deuteranopia"]))
    P("(the white centre and the grey are meant to be close: they both say 'no clear change'; that pair is the minimum if it is low)")
    P()
    return lines, results


def write_md(lines):
    block = MARK_A + "\n\n" + "\n".join(lines) + "\n\n" + MARK_B
    txt = open(MD, encoding="utf-8").read() if os.path.exists(MD) else "# Colour check\n\n" + MARK_A + "\n" + MARK_B + "\n"
    if MARK_A in txt and MARK_B in txt:
        txt = txt[:txt.index(MARK_A)] + block + txt[txt.index(MARK_B) + len(MARK_B):]
    else:
        txt += "\n" + block + "\n"
    with open(MD, "w", encoding="utf-8") as fh:
        fh.write(txt)


# ----------------------------------------------------------------------------- contact sheet
def _tiles(web_dir, manifest):
    """[(group, title, [(png, opacity)])] for every display layer present in web_dir."""
    op = {l["id"]: l.get("opacity", 0.85) for l in manifest["layers"]}
    tiles = []

    def f(n):
        return os.path.join(web_dir, n)
    names = sorted(os.listdir(web_dir))
    for n in names:
        if re.match(r"nisar_l_coast_\d{8}_t55_hh\.png$", n):
            tiles.append(("backscatter", "coast HH " + n.split("_")[3], [(f(n), op.get(n[:-4], 0.85))]))
    for n in names:
        if re.match(r"nisar_l_sea_\d{8}_t48_vv\.png$", n):
            tiles.append(("backscatter", "sea VV " + n.split("_")[3], [(f(n), op.get(n[:-4], 0.85))]))
    for n in names:
        if n.startswith("nisar_l_coast_change_") and n.endswith(".png"):
            tiles.append(("change", "coast change " + n.split("_")[4], [(f(n), 0.85)]))
    for n in names:
        if n.startswith("nisar_sea_diff_") and n.endswith(".png"):
            tiles.append(("change", "sea diff " + n.split("_")[3], [(f(n), 0.85)]))
    dates = sorted({n.split("_")[1] for n in names if re.match(r"class_\d{8}_new_water\.png$", n)})
    for d in dates:
        lay = [(f("class_%s_%s.png" % (d, w)), op.get("nisar_class_" + w, 0.75)) for w in ("no_change", "wet_crops", "new_water")]
        tiles.append(("classes", "classes " + d, [x for x in lay if os.path.exists(x[0])]))
    return tiles


def contact_sheet(web_dir, out_path, label="", base_hex=BASEMAP_HEX, tile_w=380, cols=5):
    """One image: every layer composited over the basemap colour with its manifest opacity."""
    from PIL import Image, ImageDraw, ImageFont
    with open(os.path.join(ROOT, "data", "processed", "manifest.json"), encoding="utf-8") as fh:
        manifest = json.load(fh)
    font = ImageFont.load_default(size=14)
    big = ImageFont.load_default(size=18)
    base = hex_rgb(base_hex)
    tiles = _tiles(web_dir, manifest)
    cells = []
    for grp, title, lays in tiles:
        im0 = Image.open(lays[0][0])
        h = int(round(tile_w * im0.height / im0.width))
        canvas = Image.new("RGBA", (tile_w, h), base + (255,))
        for p, o in lays:
            im = Image.open(p).convert("RGBA").resize((tile_w, h), Image.NEAREST if "class_" in p else Image.BILINEAR)
            if o < 1:
                a = im.getchannel("A").point(lambda x, o=o: int(x * o))
                im.putalpha(a)
            canvas.alpha_composite(im)
        cells.append((grp, title, canvas.convert("RGB")))
    rows, cur = [], []
    for c in cells:
        cur.append(c)
        if len(cur) == cols:
            rows.append(cur)
            cur = []
    if cur:
        rows.append(cur)
    pad, head = 10, 26
    heights = [max(c[2].height for c in r) + head for r in rows]
    W = cols * (tile_w + pad) + pad
    H = sum(heights) + pad * (len(rows) + 1) + 34
    sheet = Image.new("RGB", (W, H), tuple(int(c * 0.6) for c in base))
    d = ImageDraw.Draw(sheet)
    d.text((pad, 8), "%s  | basemap %s | layers at manifest opacity" % (label, base_hex), fill=(235, 235, 235), font=big)
    y = 34 + pad
    for r, hh in zip(rows, heights):
        x = pad
        for grp, title, im in r:
            d.text((x, y), "%s: %s" % (grp, title), fill=(235, 235, 235), font=font)
            sheet.paste(im, (x, y + head))
            x += tile_w + pad
        y += hh + pad
    sheet.save(out_path)
    return out_path


def stacked(before_dir, after_dir, out_path):
    from PIL import Image
    p1 = os.path.splitext(out_path)[0] + ".__b.png"
    p2 = os.path.splitext(out_path)[0] + ".__a.png"
    contact_sheet(before_dir, p1, "BEFORE")
    contact_sheet(after_dir, p2, "AFTER")
    a, b = Image.open(p1), Image.open(p2)
    s = Image.new("RGB", (max(a.width, b.width), a.height + b.height), (20, 20, 20))
    s.paste(a, (0, 0))
    s.paste(b, (0, a.height))
    s.save(out_path, optimize=True)
    os.remove(p1)
    os.remove(p2)


# ----------------------------------------------------------------------------- dual-pol RGB composite (docs/review/RGB_COMPOSITE.md)
def rgb_check(web_dir, out_png):
    """Contact sheet of every dual-pol RGB composite (coast and sea, one row per group, over the dark basemap), the colour-vision
    simulation (protanopia, deuteranopia) of the newest coast picture and of the sea eye pass, the legends with text labels, and the
    colour-vision distances between each group's legend colours. Returns text lines."""
    import glob
    import numpy as np
    from PIL import Image, ImageDraw
    metas = [json.load(open(f, encoding="utf-8")) for f in sorted(glob.glob(os.path.join(web_dir, "nisar_*_rgb_*.json")))]
    groups = {}
    for m in metas:
        groups.setdefault((m.get("band"), m.get("role")), []).append(m)
    for g in groups.values():
        g.sort(key=lambda m: m["acquisition_date"])
    base = np.array(hex_rgb(BASEMAP_HEX), dtype="float32")
    op = 0.9

    def tile(meta, kind="normal", w=420):
        im = Image.open(os.path.join(ROOT, meta["png"])).convert("RGBA")
        im = im.resize((w, int(im.height * w / im.width)), Image.NEAREST)
        a = np.asarray(im).astype("float32")
        al = a[..., 3:4] / 255.0 * op
        rgb = a[..., :3] * al + base * (1 - al)
        if kind != "normal":
            m = np.array(MACHADO[kind], dtype="float32")
            lin_ = np.where(rgb / 255.0 <= 0.04045, rgb / 255.0 / 12.92, ((rgb / 255.0 + 0.055) / 1.055) ** 2.4)
            lin_ = np.clip(lin_ @ m.T, 0, 1)
            rgb = 255.0 * np.where(lin_ <= 0.0031308, 12.92 * lin_, 1.055 * lin_ ** (1 / 2.4) - 0.055)
        return Image.fromarray(np.clip(rgb, 0, 255).astype("uint8"))
    w = 420
    rows = []          # (title, [(caption, image)])
    for (band, role), g in sorted(groups.items(), key=lambda kv: (kv[0][1] != "COAST", kv[0])):
        rows.append(("%s-band %s: R = %s, G = %s, B = ratio" % (band, role, g[-1]["channels"]["R"], g[-1]["channels"]["G"]), [(m["acquisition_date"], tile(m, w=w)) for m in g]))
    sim = []
    coast = next((g for (b, r), g in groups.items() if r == "COAST"), None)
    sea = next((g for (b, r), g in groups.items() if r == "SEA"), None)
    for kind in ("protanopia", "deuteranopia"):
        if coast:
            sim.append(("%s, simulated: coast %s" % (kind, coast[-1]["acquisition_date"]), tile(coast[-1], kind, w)))
        if sea:
            eye = next((m for m in sea if m["acquisition_date"] == "2026-10-27"), sea[-1])
            sim.append(("%s, simulated: sea %s" % (kind, eye["acquisition_date"]), tile(eye, kind, w)))
    rows.append(("Colour-vision simulation (Machado 2009, severity 1.0)", sim))
    head, ncol = 22, 4
    heights = [max(i.height for _, i in r[1]) + head + 22 for r in rows]
    legends = [(k, g[-1].get("legend") or []) for k, g in sorted(groups.items(), key=lambda kv: (kv[0][1] != "COAST", kv[0]))]
    H = sum(heights) + sum(30 + 24 * len(l) for _, l in legends) + 10
    sheet = Image.new("RGB", (w * ncol, H), hex_rgb(BASEMAP_HEX))
    d = ImageDraw.Draw(sheet)
    y = 0
    for (title, items), h in zip(rows, heights):
        d.text((8, y + 5), title, fill=(255, 255, 255))
        for i, (cap, im) in enumerate(items):
            d.text((i * w + 8, y + 22), cap, fill=(220, 220, 220))
            sheet.paste(im, (i * w, y + 22 + 14))
        y += h
    lines = ["Legend colours (median colour of the pixels that follow the dB rule, all dates of the group pooled)"]
    for (band, role), leg in legends:
        d.text((8, y + 4), "Legend %s-band %s (the TEXT is the key, not the colour)" % (band, role), fill=(255, 255, 255))
        for k, g in enumerate(leg):
            yy = y + 26 + k * 24
            d.rectangle([8, yy, 40, yy + 18], fill=hex_rgb(g["hex"]), outline=(220, 220, 220))
            d.text((50, yy + 3), "%s: %s  [%s]  %s" % (g.get("colour_word"), g.get("meaning") or g["label"], g["hex"], g["rule"]), fill=(255, 255, 255))
        y += 30 + 24 * len(leg)
    sheet.save(out_png)
    for (band, role), leg in legends:
        lines += ["", "### %s-band %s" % (band, role), "| id | colour word | hex | rule |", "|---|---|---|---|"]
        for g in leg:
            lines.append("| %s | %s | %s | %s |" % (g["id"], g.get("colour_word"), g["hex"], g["rule"]))
        sw = {g["id"]: hex_rgb(g["hex"]) for g in leg}
        drawn = {k: blend(v, op, hex_rgb(BASEMAP_HEX)) for k, v in sw.items()}
        lines += ["", "Pairwise dE00 between the legend colours (as drawn: colour x opacity %.2f over %s):" % (op, BASEMAP_HEX), "| pair | normal | protanopia | deuteranopia |", "|---|---|---|---|"]
        mins = {"normal": 1e9, "protanopia": 1e9, "deuteranopia": 1e9}
        for a_, b_ in itertools.combinations(sw, 2):
            row = []
            for kind in ("normal", "protanopia", "deuteranopia"):
                v = de(simulate(drawn[a_], kind), simulate(drawn[b_], kind))
                mins[kind] = min(mins[kind], v)
                row.append("%.1f" % v)
            lines.append("| %s vs %s | %s |" % (a_, b_, " | ".join(row)))
        lines.append("Minimum: normal %.1f, protanopia %.1f, deuteranopia %.1f (criterion used for the other layers: >= 20)" % (mins["normal"], mins["protanopia"], mins["deuteranopia"]))
        lines.append("Against the basemap as drawn (dE00 / WCAG contrast): " + "; ".join("%s %s %.1f / %.2f:1" % (g["id"], g["hex"], de(drawn[g["id"]], hex_rgb(BASEMAP_HEX)), contrast(drawn[g["id"]], hex_rgb(BASEMAP_HEX))) for g in leg))
    return lines


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--md", action="store_true", help="write the numeric tables into docs/review/COLOUR_CHECK.md")
    ap.add_argument("--sheet", help="write a contact sheet PNG of data/web (AFTER)")
    ap.add_argument("--before", help="directory with the old PNGs; with --sheet the sheet stacks BEFORE above AFTER")
    ap.add_argument("--rgb-sheet", help="write the dual-pol RGB contact sheet PNG (4 coast dates + colour-vision simulation) and print the legend colour checks")
    ap.add_argument("--web", default=os.path.join(ROOT, "data", "web"))
    a = ap.parse_args()
    if a.rgb_sheet:
        print("\n".join(rgb_check(a.web, a.rgb_sheet)))
        print("wrote", a.rgb_sheet)
        return 0
    if a.sheet:
        if a.before:
            stacked(a.before, a.web, a.sheet)
        else:
            contact_sheet(a.web, a.sheet, "AFTER" if not a.before else "")
        print("wrote", a.sheet)
        return 0
    lines, res = run_checks()
    if a.md:
        write_md(lines)
        print("wrote", MD)
    return 0


if __name__ == "__main__":
    sys.exit(main())
