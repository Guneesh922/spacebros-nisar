#!/usr/bin/env python3
"""Validate data/processed/manifest.json against schema v2 (stdlib only).

Usage:
    python3 tools/check_manifest.py [--manifest PATH] [--files]

Prints one PASS/FAIL line per check. Exit code 0 when every check passes, 1 otherwise.
--files additionally lists referenced files that do not exist yet (informational; the exit code is
unchanged, except that a layer's `h5` file must exist, a missing one fails). Missing `png` files under
data/web/ are build outputs of tools/build_web.py and only produce a WARN line.
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

V1_FIELDS = ["id", "group", "name", "chip", "date", "shows", "source", "credit", "limit", "png", "bounds", "default_on"]
GROUPS = {"before", "during", "after", "next"}
TYPES = {"nisar", "derived", "optical", "weather", "reference", "alerts"}
CHIPS = {"nisar", "context", "model", "reference"}
KINDS = {"image", "wmts", "geojson", "live", "link"}
STATUSES = {"ready", "coming_next", "link_only", "unavailable"}
ACCESS = {"live", "snapshot", "pipeline", "link"}
HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PNG_PREFIXES = ("data/processed/img/", "data/web/")   # data/web/ = built by tools/build_web.py (git-ignored)
H5_PREFIX = "data/h5/"

results = []   # (ok, name, detail)
warnings = []  # non-failing notes, printed as WARN lines


def check(name, errors):
    results.append((not errors, name, errors))


def bounds_ok(b):
    try:
        (s, w), (n, e) = b
        return all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in (s, w, n, e)) \
            and -90 <= s < n <= 90 and -180 <= w < e <= 180
    except Exception:
        return False


def placeholder_errors(where, ph):
    errs = []
    if ph is None:
        return errs
    if not isinstance(ph, dict) or "is" not in ph:
        return ["%s: placeholder must be an object with 'is'" % where]
    if ph.get("is"):
        for k in ("tag", "replaced_by"):
            if not isinstance(ph.get(k), str) or not ph.get(k).strip():
                errs.append("%s: placeholder.%s missing or empty" % (where, k))
    return errs


def all_paths(m):
    """Every file path the manifest references (for --files)."""
    paths = set()
    for l in m.get("layers", []):
        for k in ("png", "file", "h5"):
            if l.get(k):
                paths.add(l[k])
        for c in l.get("classes") or []:
            if c.get("png"):
                paths.add(c["png"])
    for ev in m.get("events", []):
        if ev.get("track_geojson"):
            paths.add(ev["track_geojson"])
    for a in m.get("analyses", []):
        if a.get("rank_file"):
            paths.add(a["rank_file"])
    for v in (m.get("files") or {}).values():
        paths.add(v)
    return sorted(paths)


ALERT_LEVELS = {"Green", "Orange", "Red", None}
EVENT_STATUS = {"alert_only", "radar_linked", "closed", "dismissed"}
EVENT_FINDINGS = {"change_seen", "no_clear_change", "numbers_coming", "sea_no_public_finding"}


def alerts_v2_errors(d):
    """alerts-v2 (tools/pipeline/alerts.py): area_id, built_utc, gdacs{fetched_utc,ok,error,url,credit,items}, sachet{snapshot_utc,...}."""
    errs = []
    for k in ("area_id", "built_utc", "none_text"):
        if not d.get(k):
            errs.append("alerts.json: %s missing" % k)
    for src, stamp, ikeys in (("gdacs", "fetched_utc", ("id", "type", "name", "alert_level", "from", "to", "link", "countries")),
                              ("sachet", "snapshot_utc", ("id", "headline", "area", "issued", "source", "link", "category"))):
        b = d.get(src)
        if not isinstance(b, dict):
            errs.append("alerts.json: %s must be an object (alerts-v2)" % src)
            continue
        for k in (stamp, "ok", "error", "url", "credit", "items"):
            if k not in b:
                errs.append("alerts.json: %s.%s missing" % (src, k))
        if not isinstance(b.get("ok"), bool):
            errs.append("alerts.json: %s.ok must be true/false" % src)
        if b.get("ok") is False and not b.get("error"):
            errs.append("alerts.json: %s.ok is false but error is empty" % src)
        if b.get("ok") is True and not b.get(stamp):
            errs.append("alerts.json: %s.%s missing although ok" % (src, stamp))
        for it in b.get("items") or []:
            for k in ikeys:
                if k not in it:
                    errs.append("alerts.json: %s item %s missing '%s'" % (src, it.get("id"), k))
                    break
            if src == "gdacs" and it.get("alert_level") not in ALERT_LEVELS:
                errs.append("alerts.json: gdacs item %s alert_level %r not Green/Orange/Red" % (it.get("id"), it.get("alert_level")))
    return errs


def events_v1_errors(d):
    """events-v1 (data/processed/events.json): ids unique, windows valid, statuses and radar findings from the contract."""
    errs, seen = [], set()
    if d.get("schema") != "events-v1":
        errs.append("events.json: schema must be events-v1")
    if not d.get("updated_utc"):
        errs.append("events.json: updated_utc missing")
    for ev in d.get("events", []):
        i = ev.get("id")
        if not i or i in seen:
            errs.append("events.json: id missing or duplicate (%r)" % i)
        seen.add(i)
        for k in ("name", "type", "area_id", "start", "end", "aftermath_days", "window_source", "status", "status_text",
                  "reviewed_by_human", "linked_passes", "alert_refs", "edit_log"):
            if k not in ev:
                errs.append("events.json: %s missing '%s'" % (i, k))
        if ev.get("start") and ev.get("end") and ev["start"] > ev["end"]:
            errs.append("events.json: %s start after end" % i)
        if ev.get("status") not in EVENT_STATUS:
            errs.append("events.json: %s status %r" % (i, ev.get("status")))
        if ev.get("status") == "alert_only" and ev.get("linked_passes"):
            errs.append("events.json: %s is alert_only but has linked passes" % i)
        if str(i).startswith("auto_") and ev.get("reviewed_by_human"):
            errs.append("events.json: %s is auto_ but reviewed_by_human is true (rename it)" % i)
        for lp in ev.get("linked_passes", []):
            if lp.get("radar_finding") not in EVENT_FINDINGS or lp.get("relation") not in ("during", "after"):
                errs.append("events.json: %s linked pass %s has bad relation/radar_finding" % (i, lp.get("scene_id")))
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=os.path.join(ROOT, "data", "processed", "manifest.json"))
    ap.add_argument("--files", action="store_true", help="report referenced files that do not exist yet")
    args = ap.parse_args()

    try:
        with open(args.manifest, encoding="utf-8") as f:
            m = json.load(f)
    except Exception as exc:
        print("FAIL  manifest parses as JSON: %s" % exc)
        return 1
    print("PASS  manifest parses as JSON")

    top = ["schema_version", "generated_utc", "app", "regions", "sources", "layers", "events", "analyses", "files", "coming_next"]
    errs = ["missing top-level key '%s'" % k for k in top if k not in m]
    if m.get("schema_version") != 2:
        errs.append("schema_version must be 2")
    check("top-level keys and schema_version 2", errs)

    regions = m.get("regions", [])
    sources = m.get("sources", [])
    layers = m.get("layers", [])
    events = m.get("events", [])
    analyses = m.get("analyses", [])

    # ids unique
    errs = []
    for label, coll in (("regions", regions), ("sources", sources), ("layers", layers), ("events", events), ("analyses", analyses)):
        seen = set()
        for x in coll:
            i = x.get("id")
            if not i:
                errs.append("%s: entry without id" % label)
            elif i in seen:
                errs.append("%s: duplicate id '%s'" % (label, i))
            seen.add(i)
    check("ids present and unique in regions, sources, layers, events, analyses", errs)

    rid = {r["id"] for r in regions if "id" in r}
    sid = {s["id"] for s in sources if "id" in s}
    lid = {l["id"] for l in layers if "id" in l}
    eid = {e["id"] for e in events if "id" in e}
    aid = {a["id"] for a in analyses if "id" in a}

    # regions
    errs = []
    defaults = [r["id"] for r in regions if r.get("default")]
    if len(defaults) != 1:
        errs.append("exactly one region needs default:true (found %d)" % len(defaults))
    if m.get("app", {}).get("default_region") not in rid:
        errs.append("app.default_region does not resolve")
    for r in regions:
        if not r.get("name"):
            errs.append("region %s: name missing" % r.get("id"))
        if not bounds_ok(r.get("bounds")):
            errs.append("region %s: bounds must be [[S,W],[N,E]]" % r.get("id"))
        if r.get("parent") and r["parent"] not in rid:
            errs.append("region %s: parent '%s' unknown" % (r["id"], r["parent"]))
        for c in r.get("children") or []:
            if c not in rid:
                errs.append("region %s: child '%s' unknown" % (r["id"], c))
        d = r.get("districts")
        if d is not None and not (isinstance(d, list) and all(isinstance(x, str) for x in d)):
            errs.append("region %s: districts must be null or a list of names" % r["id"])
    check("regions: one default, bounds shape, parent/children resolve", errs)

    # sources
    errs = []
    for s in sources:
        for k in ("provider", "access", "licence", "credit_line"):
            if not s.get(k):
                errs.append("source %s: %s missing" % (s.get("id"), k))
        if s.get("access") not in ACCESS:
            errs.append("source %s: access must be one of %s" % (s.get("id"), sorted(ACCESS)))
        if not isinstance(s.get("can_host"), bool):
            errs.append("source %s: can_host must be true/false" % s.get("id"))
    check("sources: provider, access, licence, credit_line, can_host", errs)

    # layers: v1 fields
    errs = []
    for l in layers:
        for k in V1_FIELDS:
            if k not in l:
                errs.append("layer %s: v1 field '%s' missing" % (l.get("id"), k))
    check("layers: all v1 fields present", errs)

    # layers: v2 fields and enums
    errs = []
    for l in layers:
        i = l.get("id")
        if l.get("group") not in GROUPS:
            errs.append("layer %s: group '%s' invalid" % (i, l.get("group")))
        if l.get("type") not in TYPES:
            errs.append("layer %s: type '%s' invalid" % (i, l.get("type")))
        if l.get("chip") not in CHIPS:
            errs.append("layer %s: chip '%s' invalid" % (i, l.get("chip")))
        if l.get("kind") not in KINDS:
            errs.append("layer %s: kind '%s' invalid" % (i, l.get("kind")))
        if l.get("status") not in STATUSES:
            errs.append("layer %s: status '%s' invalid" % (i, l.get("status")))
        if not isinstance(l.get("default_on"), bool):
            errs.append("layer %s: default_on must be true/false" % i)
        for k in ("name", "shows", "limit", "source", "credit"):
            if not isinstance(l.get(k), str) or not l.get(k).strip():
                errs.append("layer %s: %s must be a non-empty string" % (i, k))
        if l.get("source_id") not in sid:
            errs.append("layer %s: source_id '%s' not in sources" % (i, l.get("source_id")))
        regs = l.get("regions")
        if not isinstance(regs, list) or not regs:
            errs.append("layer %s: regions must be a non-empty list" % i)
        else:
            for r in regs:
                if r not in rid:
                    errs.append("layer %s: region '%s' unknown" % (i, r))
        if l.get("event_id") is not None and l["event_id"] not in eid:
            errs.append("layer %s: event_id '%s' unknown" % (i, l["event_id"]))
        d = l.get("date")
        if d is not None and not (ISO_DATE.match(d) or d == "live" or re.match(r"^\d{4}$", d)):
            errs.append("layer %s: date '%s' must be ISO date, 'live', a year or null" % (i, d))
        if l.get("kind") == "image":
            if not bounds_ok(l.get("bounds")):
                errs.append("layer %s: image layer needs bounds [[S,W],[N,E]]" % i)
            if not l.get("png"):
                errs.append("layer %s: image layer needs png" % i)
            if not isinstance(l.get("bounds_inferred"), bool):
                errs.append("layer %s: bounds_inferred must be true/false on image layers" % i)
            if not l.get("time_utc") and l.get("type") == "nisar":
                errs.append("layer %s: nisar image layer needs time_utc" % i)
        elif l.get("bounds") is not None and not bounds_ok(l.get("bounds")):
            errs.append("layer %s: bounds shape invalid" % i)
        if l.get("png") and not str(l["png"]).startswith(PNG_PREFIXES):
            errs.append("layer %s: png must live under data/processed/img/ or data/web/ (build output)" % i)
        if l.get("h5") is not None:
            h = str(l["h5"])
            if not h.startswith(H5_PREFIX) or not h.endswith(".h5") or ".." in h or h.count("/") != 2:
                errs.append("layer %s: h5 must be data/h5/<name>.h5" % i)
        if l.get("kind") == "wmts":
            u = l.get("url_template") or ""
            if "{time}" not in u or "{z}" not in u:
                errs.append("layer %s: wmts url_template needs {time} and {z}" % i)
            if not isinstance(l.get("latest_available_lag_days"), int):
                errs.append("layer %s: wmts layer needs integer latest_available_lag_days" % i)
        if l.get("kind") == "live":
            u = l.get("url_template")
            if not u:
                errs.append("layer %s: live layer needs url_template" % i)
            cfg = l.get("config")
            if "{lat}" in (u or "") and not (isinstance(cfg, dict) and "lat" in cfg and "lon" in cfg):
                errs.append("layer %s: url uses {lat}/{lon} so config needs lat and lon" % i)
        if l.get("kind") == "geojson" and not l.get("file"):
            errs.append("layer %s: geojson layer needs file" % i)
        if l.get("kind") == "link" and not (l.get("link_url") or l.get("file")):
            errs.append("layer %s: link layer needs link_url or file" % i)
        if l.get("latest_of") is not None and not isinstance(l["latest_of"], str):
            errs.append("layer %s: latest_of must be a string or null" % i)
    check("layers: enums, references, kind-specific fields, bounds, dates", errs)

    # layer ordering and counts
    errs = []
    if len(layers) < 16:
        errs.append("need at least 16 layers, found %d" % len(layers))
    seen_types = {l.get("type") for l in layers}
    for t in sorted(TYPES - seen_types):
        errs.append("no layer of type '%s'" % t)
    first_non_nisar = next((i for i, l in enumerate(layers) if l.get("type") != "nisar"), len(layers))
    if any(l.get("type") == "nisar" for l in layers[first_non_nisar:]):
        errs.append("NISAR layers must come first in layers[]")
    for l in layers:
        if l.get("type") in ("nisar", "derived") and l.get("chip") != "nisar":
            errs.append("layer %s: nisar/derived layers must carry chip 'nisar'" % l.get("id"))
    check("layers: at least 16, all six types present, NISAR first, chip 'nisar'", errs)

    # required png names and series keys
    errs = []
    need = ["nisar_l_sea_20261003_t48_vv", "nisar_l_sea_20261015_t48_vv", "nisar_l_sea_20261027_t48_vv", "nisar_l_sea_20261108_t48_vv",
            "nisar_l_coast_20261004_t55_hh", "nisar_l_coast_20261016_t55_hh", "nisar_l_coast_20261028_t55_hh", "nisar_l_coast_20261109_t55_hh"]
    byid = {l["id"]: l for l in layers if "id" in l}
    for n in need:
        l = byid.get(n)
        if not l:
            errs.append("missing NISAR layer %s" % n)
            continue
        if l.get("png") not in tuple(p + "%s.png" % n for p in PNG_PREFIXES):
            errs.append("layer %s: png must be data/processed/img/%s.png or data/web/%s.png" % (n, n, n))
        want_key = "nisar_l_sea_vv" if "_sea_" in n else "nisar_l_coast_hh"
        if l.get("latest_of") != want_key:
            errs.append("layer %s: latest_of must be %s" % (n, want_key))
        if l.get("track") != (48 if "_sea_" in n else 55):
            errs.append("layer %s: wrong track (sea=48, coast=55)" % n)
        if l.get("track") == 156 or l.get("track") == "156":
            errs.append("layer %s: Track 156 must never be used" % n)
    check("eight required NISAR layers with exact png names, latest_of keys and tracks", errs)

    errs = []
    if any(l.get("track") in (156, "156") for l in layers):
        errs.append("a layer uses Track 156")
    mf = json.dumps(m)
    if re.search(r"T156|Track 156", mf) and "does not cover" not in mf and "never" not in mf:
        errs.append("Track 156 mentioned without a warning")
    check("no Track 156 layer", errs)

    # landing defaults
    errs = []
    on_layers = [l for l in layers if l.get("default_on")]
    if not any(l.get("type") == "nisar" and l.get("status") == "ready" for l in on_layers):
        errs.append("landing default_on needs at least one ready nisar layer")
    if not any(l.get("type") == "reference" for l in on_layers):
        errs.append("landing default_on needs the mandal boundaries layer (type reference)")
    for l in layers:
        if l.get("type") == "optical" and l.get("default_on"):
            errs.append("layer %s: live optical layers must be off by default" % l["id"])
    check("landing view: default_on has a ready NISAR layer and a reference layer, optical off", errs)

    # classes
    errs = []
    for l in layers:
        cl = l.get("classes")
        if cl is None:
            continue
        if not isinstance(cl, list) or not cl:
            errs.append("layer %s: classes must be a non-empty list or null" % l["id"])
            continue
        for c in cl:
            if not str(c.get("label", "")).startswith("likely"):
                errs.append("layer %s: class '%s' label must start with 'likely'" % (l["id"], c.get("id")))
            if not c.get("id"):
                errs.append("layer %s: class without id" % l["id"])
            if c.get("style") == "outline":
                if c.get("colour") is not None and not HEX.match(str(c["colour"])):
                    errs.append("layer %s: outline class colour must be hex or null" % l["id"])
            elif not HEX.match(str(c.get("colour", ""))):
                errs.append("layer %s: class '%s' needs a #RRGGBB colour" % (l["id"], c.get("id")))
            if not isinstance(c.get("default_on"), bool):
                errs.append("layer %s: class '%s' default_on must be true/false" % (l["id"], c.get("id")))
    for l in layers:
        if l.get("type") == "derived" and l.get("kind") == "image" and l.get("classes") is not None:
            pass
    check("class layers: labels start with 'likely', colours valid", errs)

    # placeholders
    errs = []
    for l in layers:
        errs += placeholder_errors("layer %s" % l.get("id"), l.get("placeholder"))
    for a in analyses:
        errs += placeholder_errors("analysis %s" % a.get("id"), a.get("placeholder"))
    for l in layers:
        if l.get("status") == "unavailable" and not (l.get("placeholder") or {}).get("is"):
            errs.append("layer %s: unavailable image layers must be flagged as placeholder" % l.get("id"))
    check("placeholders: every placeholder with is:true has tag and replaced_by", errs)

    # events
    errs = []
    for e in events:
        i = e.get("id")
        for k in ("name", "hazard", "region", "dates", "layers", "default_on", "analysis_id", "landfall"):
            if k not in e:
                errs.append("event %s: '%s' missing" % (i, k))
        if e.get("region") not in rid:
            errs.append("event %s: region '%s' unknown" % (i, e.get("region")))
        if e.get("analysis_id") is not None and e["analysis_id"] not in aid:
            errs.append("event %s: analysis_id '%s' unknown" % (i, e.get("analysis_id")))
        d = e.get("dates", {})
        for k in ("before", "during", "after"):
            if not ISO_DATE.match(str(d.get(k, ""))):
                errs.append("event %s: dates.%s must be ISO date" % (i, k))
        npd = d.get("normal_period")
        if not (isinstance(npd, list) and len(npd) == 2 and all(ISO_DATE.match(str(x)) for x in npd)):
            errs.append("event %s: dates.normal_period must be [from,to]" % i)
        for grp in ("before", "during", "after"):
            for x in (e.get("layers") or {}).get(grp, []):
                if x not in lid:
                    errs.append("event %s: layers.%s refers to unknown layer '%s'" % (i, grp, x))
        listed = {x for g in (e.get("layers") or {}).values() for x in g}
        for x in e.get("default_on", []):
            if x not in lid:
                errs.append("event %s: default_on layer '%s' unknown" % (i, x))
            elif x not in listed:
                errs.append("event %s: default_on layer '%s' not in layers.before/during/after" % (i, x))
        don = [x for x in e.get("default_on", []) if x in byid]
        if don and byid[don[0]].get("type") != "nisar":
            errs.append("event %s: first default_on layer must be a NISAR layer" % i)
        lf = e.get("landfall") or {}
        if "time_utc" not in lf:
            errs.append("event %s: landfall.time_utc key required (null when unconfirmed)" % i)
        if lf.get("time_utc") is None and not lf.get("note"):
            errs.append("event %s: landfall.note required when time_utc is null" % i)
        if not (isinstance(lf.get("lat"), (int, float)) and isinstance(lf.get("lon"), (int, float))):
            errs.append("event %s: landfall lat/lon must be numbers" % i)
        if e.get("track_geojson") and not str(e["track_geojson"]).endswith(".geojson"):
            errs.append("event %s: track_geojson must be a .geojson path" % i)
    for l in layers:
        pass
    check("events: region, dates, layer references, NISAR-first default_on, landfall time null with note", errs)

    # analyses
    errs = []
    for a in analyses:
        i = a.get("id")
        if a.get("region") not in rid:
            errs.append("analysis %s: region unknown" % i)
        for k in ("period", "normal_period"):
            v = a.get(k)
            if not (isinstance(v, list) and len(v) == 2 and all(ISO_DATE.match(str(x)) for x in v)):
                errs.append("analysis %s: %s must be [from,to]" % (i, k))
        if not a.get("rank_file"):
            errs.append("analysis %s: rank_file missing" % i)
        for c in a.get("class_layers") or []:
            if c not in lid:
                errs.append("analysis %s: class layer '%s' unknown" % (i, c))
    check("analyses: region, periods, rank_file, class layers resolve", errs)

    # coming_next
    errs = []
    cn = m.get("coming_next", [])
    if len(cn) < 1:
        warnings.append("coming_next is empty (allowed; the page shows no Coming next entries)")
    for c in cn:
        if not c.get("id") or not c.get("name"):
            errs.append("coming_next entry needs id and name")
    check("coming_next entries", errs)

    # companion files (if present)
    errs = []
    base = os.path.join(ROOT, "data", "processed")
    for fn in ("mandal_rank.json", "profile.json", "alerts.json"):
        p = os.path.join(base, fn)
        if not os.path.exists(p):
            errs.append("%s missing" % fn)
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception as exc:
            errs.append("%s: invalid JSON (%s)" % (fn, exc))
            continue
        if isinstance(d, dict) and "placeholder" in d:
            errs += placeholder_errors(fn, d["placeholder"])
        if fn == "mandal_rank.json":
            rows = d.get("rows", [])
            need_k = ["mandal", "district", "water_pct", "water_err", "crops_pct", "crops_err", "normal_pct", "rank"]
            if not rows:
                errs.append("mandal_rank.json: no rows")
            if d.get("analysis_id") not in aid:
                errs.append("mandal_rank.json: analysis_id does not resolve")
            names = [r.get("mandal") for r in rows]
            if len(names) != len(set(names)):
                errs.append("mandal_rank.json: duplicate mandal names")
            for r in rows:
                for k in need_k:
                    if k not in r:
                        errs.append("mandal_rank.json: %s missing '%s'" % (r.get("mandal"), k))
            ranks = [r.get("rank") for r in rows]
            if ranks != list(range(1, len(rows) + 1)):
                errs.append("mandal_rank.json: ranks must run 1..N in row order")
            basis = d.get("rank_basis") or "water_pct"   # W3-H: rank follows total likely flooded (water + crops); rank_water follows water only
            tot = [r[basis] for r in rows if basis in r]
            if tot != sorted(tot, reverse=True):
                errs.append("mandal_rank.json: rows not sorted by %s descending" % basis)
            for iso, blk in (d.get("by_date") or {}).items():
                brs = blk.get("rows") or []
                for r in brs:
                    for k in ("mandal", "water_pct", "crops_pct", "err", "coverage_pct", "area_km2", "flooded_km2"):
                        if k not in r:
                            errs.append("mandal_rank.json by_date %s: %s missing '%s'" % (iso, r.get("mandal"), k))
                            break
                rw = sorted(r["rank_water"] for r in brs if r.get("rank_water"))
                if rw != list(range(1, len(rw) + 1)):
                    errs.append("mandal_rank.json by_date %s: rank_water must run 1..N" % iso)
        if fn == "profile.json":
            pts = d.get("points", [])
            if len(pts) < 20:
                errs.append("profile.json: need 20+ points")
            if d.get("layer_id") not in lid:
                errs.append("profile.json: layer_id does not resolve")
            if not all(k in p_ for p_ in pts for k in ("r_km", "db", "err")):
                errs.append("profile.json: points need r_km, db, err")
        if fn == "alerts.json":
            if d.get("schema") == "alerts-v2":
                errs += alerts_v2_errors(d)
            else:   # legacy v1 snapshot (src/fetch/sachet_snapshot.py --out): still readable
                if not d.get("saved_at_ist"):
                    errs.append("alerts.json: saved_at_ist missing")
                if "gdacs" not in d or not isinstance(d.get("sachet"), list):
                    errs.append("alerts.json: needs sachet[] and gdacs[]")
    check("companion files: mandal_rank.json, profile.json, alerts.json", errs)

    # events.json (events-v1), written by tools/pipeline/events.py; optional until the first run
    errs = []
    p = os.path.join(base, "events.json")
    if os.path.exists(p):
        try:
            errs += events_v1_errors(json.load(open(p, encoding="utf-8")))
        except Exception as exc:
            errs.append("events.json: invalid JSON (%s)" % exc)
    else:
        warnings.append("data/processed/events.json missing (optional; tools/pipeline/events.py writes it)")
    check("events.json (events-v1)", errs)

    ok_all = all(r[0] for r in results)
    for ok, name, errs in results:
        print("%s  %s" % ("PASS" if ok else "FAIL", name))
        for e in errs:
            print("        - %s" % e)
    for w in warnings:
        print("WARN  %s" % w)

    if args.files:
        print("\nReferenced files that do not exist yet (informational):")
        missing = [p for p in all_paths(m) if not os.path.exists(os.path.join(ROOT, p))]
        h5_missing = []
        for p in missing:
            if p.startswith("data/web/"):
                print("  WARN     %s (build output: run python tools/build_web.py)" % p)
            elif p.startswith(H5_PREFIX) and p.endswith(".h5"):
                h5_missing.append(p)
                print("  FAIL     %s (layer h5 file missing)" % p)
            else:
                print("  missing  %s" % p)
        print("  %d of %d referenced files missing" % (len(missing), len(all_paths(m))))
        if h5_missing:
            ok_all = False

    wtxt = ", %d warning%s" % (len(warnings), "" if len(warnings) == 1 else "s") if warnings else ""
    print("\n%s (%d checks, %d failed%s)" % ("PASS" if ok_all else "FAIL", len(results), sum(1 for r in results if not r[0]), wtxt))
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
