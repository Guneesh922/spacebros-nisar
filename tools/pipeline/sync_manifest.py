#!/usr/bin/env python3
"""Create / update the NISAR image layers in a manifest from data/h5/catalog.json (stdlib only).

For every catalog scene with band L and role COAST (HH) or SEA (VV) the layer id is
  nisar_l_coast_YYYYMMDD_t55_hh   /   nisar_l_sea_YYYYMMDD_t48_vv
- Layer already in the manifest: ONLY `h5`, `png`, `bounds`, `status`, `processing_level` (and `bounds_inferred` when bounds change)
  are touched, and only when they differ. Everything hand-written (name, group, shows, limit, notes...) is kept.
  `bounds` come from data/web/{id}.json (written by tools/build_web.py) when present, else from the catalog.
- Layer missing: a new one is added (status ready, placeholder null, default_on false) from a sibling layer of the
  same role as template (regions, credit, source_id, shows, opacity...), group before/during/after by date,
  name "<role>, <date> (T<track>)". New layers can be renamed by hand later; sync never renames them again.
Tracks other than the existing series (55 coast, 48 sea) get their own `latest_of` series, e.g. nisar_l_sea_t120_vv.
Layers whose h5 is not in the catalog (S-band, derived) are never touched or removed.

Usage: python tools/pipeline/sync_manifest.py [--manifest data/processed/manifest.json] [--catalog ...] [--dry-run]
Writes with the manifest's own formatting (indent 2, UTF-8, trailing newline). Prints a one-line change list;
exit 0 always (no change = prints "manifest already in sync").
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CATALOG, MANIFEST, ROOT, load_json  # noqa: E402

POL = {"COAST": "HH", "SEA": "VV"}
DIRECTION = {"A": "ascending", "D": "descending"}
EXISTING_SERIES = {("COAST", 55): "nisar_l_coast_hh", ("SEA", 48): "nisar_l_sea_vv"}
EYE_START, EYE_END = "2026-10-27", "2026-10-28"   # passes on these days = "during" (sea eye pass, coast after landfall)
KEEP_BOUNDS_DIFF = 2e-5                              # degrees; smaller differences are rounding, not changes


def layer_id(e):
    return f"nisar_l_{e['role'].lower()}_{e['date'].replace('-', '')}_t{e['track']}_{POL[e['role']].lower()}"


def series_of(e):
    return EXISTING_SERIES.get((e["role"], e["track"])) or f"nisar_l_{e['role'].lower()}_t{e['track']}_{POL[e['role']].lower()}"


def group_of(date):
    return "before" if date < EYE_START else "during" if date <= EYE_END else "after"


def bounds_for(lid, e, web_dir):
    j = load_json(web_dir / f"{lid}.json")
    if j and j.get("bounds"):
        return j["bounds"], False
    return [[round(v, 5) for v in row] for row in e["bounds_latlon"]], False


def same_bounds(a, b):
    try:
        return all(abs(x - y) <= KEEP_BOUNDS_DIFF for ra, rb in zip(a, b) for x, y in zip(ra, rb))
    except TypeError:
        return False


def new_layer(e, lid, bounds, template):
    role = e["role"]
    st = "validated" if e["product_status"] == "VALIDATED" else "provisional"
    layer = {k: v for k, v in (template or {}).items() if k in (
        "type", "chip", "kind", "shows", "source_id", "credit", "url_template", "band", "regions", "event_id",
        "classes", "opacity")}
    layer.update({
        "group": group_of(e["date"]), "type": "nisar", "chip": "nisar", "kind": "image", "date": e["date"],
        "time_utc": e["start_utc"], "latest_of": series_of(e),
        "limit": "single look; compare with other dates of the same track",
        "source": f"T{e['track']} F{e['frame']} · NASA/ISRO via ASF",
        "png": f"data/web/{lid}.png", "bounds": bounds, "bounds_inferred": False,
        "band": "L", "pol": POL[role], "track": e["track"], "frame": e["frame"],
        "direction": DIRECTION.get(e["direction"], e["direction"]),
        "default_on": False, "status": "ready", "placeholder": None, "id": lid,
        "name": f"{'Coast' if role == 'COAST' else 'Sea surface'}, {e['date']} (T{e['track']})",
        "processing_level": st, "h5": e["file"],
    })
    layer.setdefault("opacity", 0.85)
    layer.setdefault("url_template", None)
    layer.setdefault("event_id", None)
    layer.setdefault("classes", None)
    return layer


def sync(manifest, catalog, web_dir):
    layers = manifest["layers"]
    by_id = {l["id"]: l for l in layers}
    changes = []
    for e in catalog.get("scenes", []):
        if e["band"] != "L" or e["role"] not in POL or POL[e["role"]] not in e["pols"]:
            continue
        lid = layer_id(e)
        bounds, _ = bounds_for(lid, e, web_dir)
        want = {"h5": e["file"], "png": f"data/web/{lid}.png", "status": "ready"}
        l = by_id.get(lid)
        if l is not None:
            # a provisional scene replaced by a validated one: refresh the quality fields (never downgrade by accident:
            # the catalog is the source of truth, so a re-ingested PROVISIONAL scene does show as provisional again)
            want["processing_level"] = "validated" if e["product_status"] == "VALIDATED" else "provisional"
            if "product_status" in l:
                want["product_status"] = e["product_status"]
        if l is None:
            tmpl = next((x for x in reversed(layers) if x.get("type") == "nisar" and x.get("band") == "L"
                         and x.get("pol") == POL[e["role"]] and x.get("id", "").startswith(f"nisar_l_{e['role'].lower()}_")), None)
            nl = new_layer(e, lid, bounds, tmpl)
            last = max((i for i, x in enumerate(layers) if x.get("id", "").startswith(f"nisar_l_{e['role'].lower()}_")),
                       default=len(layers) - 1)
            layers.insert(last + 1, nl)
            by_id[lid] = nl
            changes.append(f"ADD {lid}")
            continue
        for k, v in want.items():
            if l.get(k) != v:
                changes.append(f"SET {lid}.{k}: {l.get(k)!r} -> {v!r}")
                l[k] = v
        if not same_bounds(l.get("bounds"), bounds):
            changes.append(f"SET {lid}.bounds: {l.get('bounds')} -> {bounds}")
            l["bounds"] = bounds
    return changes


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", default=str(MANIFEST))
    ap.add_argument("--catalog", default=str(CATALOG))
    ap.add_argument("--web-dir", default=str(ROOT / "data" / "web"))
    ap.add_argument("--dry-run", action="store_true", help="print changes, write nothing")
    a = ap.parse_args()
    with open(a.manifest, encoding="utf-8") as f:
        manifest = json.load(f)
    cat = load_json(a.catalog)
    if not cat:
        print(f"no catalog at {a.catalog}", file=sys.stderr)
        return 1
    changes = sync(manifest, cat, Path(a.web_dir))
    if not changes:
        print("manifest already in sync")
        return 0
    print("\n".join(changes))
    if not a.dry_run:
        with open(a.manifest, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"wrote {a.manifest} ({len(changes)} changes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
