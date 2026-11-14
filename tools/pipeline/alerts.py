#!/usr/bin/env python3
"""Refresh data/processed/alerts.json (schema alerts-v2): official alerts that touch one area.

Sources (both public, no key):
  GDACS  https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH  (GeoJSON, tropical cyclones + floods).
         Kept when the event's point/bbox falls inside the area's alert_match.bbox. GDACS gives a centroid point for
         cyclones and floods; the full footprint is a separate API call we do not make, so an event whose centre is
         just outside the bbox is not kept (documented limit).
  SACHET https://sachet.ndma.gov.in/cap_public_website/rss/rss_india.xml (NDMA CAP feed, via src/fetch/sachet_snapshot.py).
         The CAP areaDesc of every item is fetched (one small request each, 8 in parallel, ~1 s for ~100 items).
         Kept when headline + areaDesc + issuing office mention one of alert_match.states (e.g. "Andhra Pradesh") or one
         of alert_match.keywords (whole words, so "Krishna" does not match "Krishnagiri").

A failed fetch NEVER blanks the file: the previous items of that source are kept with their REAL old timestamp,
ok:false and the error text. With no previous v2 file the items are [] and the timestamp null.
This tool never says that radar confirms an alert; it only lists what the official sources published.

Usage:
  python tools/pipeline/alerts.py [--area godavari] [--out data/processed/alerts.json]
                                  [--now 2026-11-14T10:00Z] [--fixture fake.json] [--no-sachet] [--no-gdacs]
  --fixture  JSON {"gdacs": [ {id,type,name,alert_level,from,to,link,countries,lon,lat[,bbox]} ... ],
                   "sachet": [ {id,headline,area,issued,source,link,category} ... ]}
             used INSTEAD of the network (for simulations); the same area filter is applied. A key may also be
             {"fail": "error text"} to simulate a failed fetch of that source.
  --now      pretend it is this UTC time (built_utc / fetched stamps / "current" flag).
Exit 0 always when the file was written (also when a source failed: see ok/error in the file).
"""
import argparse
import datetime as dt
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import AREAS_ENV, ROOT, area as load_area, dump_json, load_json  # noqa: E402

sys.path.insert(0, str(ROOT / "src" / "fetch"))

SCHEMA = "alerts-v2"
OUT = ROOT / "data" / "processed" / "alerts.json"
GDACS_API = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"
GDACS_CREDIT = "GDACS (EC JRC / UN OCHA)"
SACHET_URL = "https://sachet.ndma.gov.in/cap_public_website/rss/rss_india.xml"
SACHET_CREDIT = "NDMA SACHET (CAP Integrated Alert System); feed states copyright 'public domain'"
NONE_TEXT = "No current alerts for this area from GDACS or SACHET."
GDACS_DAYS = 60          # look-back window for GDACS events (covers a 30-day aftermath plus the event itself)
GDACS_TYPES = ("TC", "FL")
GDACS_TYPE_NAME = {"TC": "Tropical cyclone", "FL": "Flood"}


def utc(s):
    return dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)


def parse_now(s):
    """--now 'YYYY-MM-DDTHH:MMZ' (also with seconds) -> aware datetime."""
    if not s:
        return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    for f in ("%Y-%m-%dT%H:%MZ", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return dt.datetime.strptime(s, f).replace(tzinfo=dt.timezone.utc)
        except ValueError:
            pass
    raise SystemExit(f"--now must look like 2026-11-14T10:00Z, got {s!r}")


def iso(d):
    return d.strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------- area matching ----------
def bbox_touches(b, box):
    """b, box = (W, S, E, N). True when the rectangles overlap or touch."""
    return not (b[2] < box[0] or b[0] > box[2] or b[3] < box[1] or b[1] > box[3])


def gdacs_matches(item, am):
    b = item.get("bbox") or ([item["lon"], item["lat"]] * 2 if item.get("lon") is not None else None)
    return bool(b) and bbox_touches(b, am["bbox"])


def _word_re(words):
    return re.compile(r"(?<![a-z])(" + "|".join(re.escape(w.lower()) for w in words) + r")(?![a-z])", re.I) if words else None


def sachet_matches(item, am):
    text = " ".join([item.get("headline") or "", item.get("area") or "", item.get("source") or ""]).lower()
    for st in am.get("states", []):
        if st.lower() in text:
            return True
    rx = _word_re(am.get("keywords", []))
    return bool(rx and rx.search(text))


# ---------- GDACS ----------
def http_get(url, timeout=40):
    req = urllib.request.Request(url, headers={"User-Agent": "spacebros-nisar-pipeline"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def fetch_gdacs(now):
    """All TC + FL events with a start in the last GDACS_DAYS days (paged, 100 per page). Returns normalised items."""
    frm = (now - dt.timedelta(days=GDACS_DAYS)).strftime("%Y-%m-%d")
    to = (now + dt.timedelta(days=1)).strftime("%Y-%m-%d")
    items, page = [], 1
    while page <= 10:
        q = urllib.parse.urlencode({"eventlist": ";".join(GDACS_TYPES), "fromdate": frm, "todate": to,
                                    "alertlevel": "Green;Orange;Red", "pagenumber": page, "pagesize": 100}, safe=";")
        try:
            d = json.loads(http_get(f"{GDACS_API}?{q}"))
        except (json.JSONDecodeError, ValueError):
            if page == 1:
                raise
            break   # past the last page GDACS answers with an empty body
        feats = d.get("features", [])
        for f in feats:
            items.append(norm_gdacs(f))
        if len(feats) < 100:
            break
        page += 1
    return items


def norm_gdacs(f):
    p = f.get("properties", {})
    g = f.get("geometry") or {}
    coords = g.get("coordinates") if g.get("type") == "Point" else None
    bbox = f.get("bbox")
    et = p.get("eventtype")
    name = (p.get("name") or "").strip()
    return {
        "id": str(p.get("eventid")),
        "type": et,
        "name": name or f"{GDACS_TYPE_NAME.get(et, et)} {p.get('eventid')}",
        "alert_level": p.get("alertlevel") or p.get("episodealertlevel"),
        "from": (p.get("fromdate") or "") + ("Z" if p.get("fromdate") else ""),
        "to": (p.get("todate") or "") + ("Z" if p.get("todate") else ""),
        "link": (p.get("url") or {}).get("report"),
        "countries": p.get("country") or "",
        "lon": coords[0] if coords else None, "lat": coords[1] if coords else None,
        "bbox": list(bbox) if bbox else None,
        "iscurrent": str(p.get("iscurrent")).lower() == "true",
        "severity_text": ((p.get("severitydata") or {}).get("severitytext") or "").strip(),
    }


def out_gdacs_item(g, now):
    to = g.get("to") or ""
    current = bool(g.get("iscurrent")) if "iscurrent" in g else bool(to and utc(to) >= now)
    return {"id": g["id"], "type": g["type"], "name": g["name"], "alert_level": g["alert_level"], "from": g.get("from"),
            "to": g.get("to"), "link": g.get("link"), "countries": g.get("countries", ""),
            "current": current, "point": [g["lon"], g["lat"]] if g.get("lon") is not None else None,
            "severity_text": g.get("severity_text") or None}


# ---------- SACHET ----------
def fetch_sachet():
    import sachet_snapshot
    items, meta = sachet_snapshot.fetch_items(cap=True)
    return items, meta


def out_sachet_item(i):
    return {k: i.get(k) for k in ("id", "headline", "area", "issued", "source", "link", "category")}


# ---------- build ----------
def build(area_id=None, now=None, fixture=None, prev=None, do_gdacs=True, do_sachet=True, out_path=OUT):
    """Return the alerts-v2 dict. prev = previous alerts.json (dict) used for the keep-on-failure rule."""
    ar = load_area(area_id)
    am = ar["alert_match"]
    now = now or parse_now(None)
    prev = prev if (prev and prev.get("schema") == SCHEMA and prev.get("area_id") == ar["id"]) else {}
    res = {}

    # --- GDACS
    pg = prev.get("gdacs") or {}
    if not do_gdacs:
        res["gdacs"] = pg or {"fetched_utc": None, "ok": False, "error": "not fetched (--no-gdacs)", "url": GDACS_API,
                              "credit": GDACS_CREDIT, "items": []}
    else:
        try:
            if fixture is not None:
                fx = fixture.get("gdacs", [])
                if isinstance(fx, dict) and fx.get("fail"):
                    raise ConnectionError(fx["fail"])
                raw = [dict(x) for x in fx]
            else:
                raw = fetch_gdacs(now)
            kept = [out_gdacs_item(g, now) for g in raw if g.get("type") in GDACS_TYPES and gdacs_matches(g, am)]
            kept.sort(key=lambda x: (x.get("from") or ""), reverse=True)
            res["gdacs"] = {"fetched_utc": iso(now), "ok": True, "error": None, "url": GDACS_API,
                            "credit": GDACS_CREDIT, "items": kept}
        except Exception as e:  # noqa: BLE001 - any failure keeps the previous items
            res["gdacs"] = {"fetched_utc": pg.get("fetched_utc"), "ok": False,
                            "error": f"{type(e).__name__}: {e}"[:300], "url": GDACS_API, "credit": GDACS_CREDIT,
                            "items": pg.get("items", [])}

    # --- SACHET
    ps = prev.get("sachet") or {}
    if not do_sachet:
        res["sachet"] = ps or {"snapshot_utc": None, "ok": False, "error": "not fetched (--no-sachet)",
                               "url": SACHET_URL, "credit": SACHET_CREDIT, "items": []}
    else:
        try:
            if fixture is not None:
                fx = fixture.get("sachet", [])
                if isinstance(fx, dict) and fx.get("fail"):
                    raise ConnectionError(fx["fail"])
                raw, meta = [dict(x) for x in fx], {}
            else:
                raw, meta = fetch_sachet()
            kept = [out_sachet_item(i) for i in raw if sachet_matches(i, am)]
            kept.sort(key=lambda x: x.get("issued") or "", reverse=True)
            res["sachet"] = {"snapshot_utc": iso(now), "ok": True, "error": None, "url": SACHET_URL,
                             "credit": SACHET_CREDIT, "items": kept,
                             "feed_item_count": len(raw), "feed_pubdate": meta.get("feed_pubdate"),
                             "feed_newest_item": meta.get("feed_newest_item_ist")}
        except Exception as e:  # noqa: BLE001
            res["sachet"] = {"snapshot_utc": ps.get("snapshot_utc"), "ok": False,
                             "error": f"{type(e).__name__}: {e}"[:300], "url": SACHET_URL, "credit": SACHET_CREDIT,
                             "items": ps.get("items", [])}

    return {"schema": SCHEMA, "area_id": ar["id"], "built_utc": iso(now), "gdacs": res["gdacs"],
            "sachet": res["sachet"], "none_text": NONE_TEXT}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--area", default=None)
    ap.add_argument("--config", default=None, help=f"areas config (default config/areas.json; env {AREAS_ENV})")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--now", default=None)
    ap.add_argument("--fixture", default=None)
    ap.add_argument("--no-sachet", action="store_true")
    ap.add_argument("--no-gdacs", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="print the result, do not write")
    a = ap.parse_args()
    if a.config:
        import os
        os.environ[AREAS_ENV] = a.config
    now = parse_now(a.now)
    fixture = load_json(a.fixture) if a.fixture else None
    if a.fixture and fixture is None:
        raise SystemExit(f"fixture {a.fixture} not found")
    prev = load_json(a.out, None)
    doc = build(a.area, now, fixture, prev, not a.no_gdacs, not a.no_sachet)
    for k in ("gdacs", "sachet"):
        s = doc[k]
        print(f"{k:6s} ok={s['ok']} kept={len(s['items'])} stamp={s.get('fetched_utc') or s.get('snapshot_utc')}"
              + (f" ERROR {s['error']}" if s["error"] else ""))
        for i in s["items"][:8]:
            print("   -", i.get("alert_level") or "", i.get("name") or (i.get("headline") or "")[:70], "|",
                  i.get("from") or i.get("issued"))
    if a.dry_run:
        return 0
    dump_json(doc, a.out)
    print("wrote", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
