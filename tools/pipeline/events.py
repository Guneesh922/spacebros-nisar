#!/usr/bin/env python3
"""Keep data/processed/events.json (schema events-v1) in step with the alerts and the radar catalogue.

What it does, in order (all idempotent: a second run with the same inputs and --now changes nothing but updated_utc):
  1. ALERTS -> DRAFT EVENTS. Every cyclone / flood alert in data/processed/alerts.json (GDACS types TC, FL; SACHET items whose
     headline says cyclone or flood) that touches the area and is still inside its window (alert end + aftermath_days >= now):
       - if an event already holds that alert id in alert_refs: refresh it (drafts only; reviewed events are never edited);
       - elif a human-reviewed event of the same type in the same area overlaps the alert's dates: the alert is only ADDED to
         that event's alert_refs (no duplicate event);
       - else a new draft: id auto_<SOURCE>_<id>, status alert_only, status_text "Alert only, not yet seen by radar",
         reviewed_by_human false, severity exactly as the source gave it, start/end from the alert, aftermath_days from
         config (defaults.aftermath_days, 30), one edit_log line.
  2. RADAR LINKING. Every catalogue scene (data/h5/catalog.json) whose date lies in [start, end + aftermath_days] of an event
     in the same area is added to linked_passes (relation "during" if date <= end, else "after"). A draft with a first
     link moves to status radar_linked. New links start with radar_finding "numbers_coming" (COAST roles analysed for flood
     classes) or "sea_no_public_finding" (roles configured analysis "none_public"). The findings step later calls
     set_radar_finding() to turn "numbers_coming" into "change_seen" or "no_clear_change".
  3. Human-reviewed events are NEVER deleted or rewritten; only alert_refs and linked_passes grow. Dismissed events are skipped.
Wording rule: this file never says radar confirms an alert.

Usage: python tools/pipeline/events.py [--area godavari] [--now 2026-11-14T10:00Z] [--dry-run]
         [--events data/processed/events.json] [--alerts data/processed/alerts.json] [--catalog data/h5/catalog.json]
"""
import argparse
import copy
import datetime as dt
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import AREAS_ENV, CATALOG, ROOT, area as load_area, dump_json, load_json  # noqa: E402

SCHEMA = "events-v1"
EVENTS = ROOT / "data" / "processed" / "events.json"
ALERTS = ROOT / "data" / "processed" / "alerts.json"
STATUS_TEXT = {"alert_only": "Alert only, not yet seen by radar", "radar_linked": "Radar passes linked",
               "closed": "Closed", "dismissed": "Dismissed"}
FINDINGS = ("change_seen", "no_clear_change", "numbers_coming", "sea_no_public_finding")
GDACS_KIND = {"TC": "cyclone", "FL": "flood"}
SACHET_KIND_RX = [("cyclone", re.compile(r"cyclon", re.I)), ("flood", re.compile(r"flood", re.I))]


# ---------- small helpers ----------
def parse_now(s):
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


def day(s):
    """'YYYY-MM-DD...' -> date"""
    return dt.date.fromisoformat(str(s)[:10])


def log(ev, now, what):
    ev.setdefault("edit_log", []).append({"utc": iso(now), "by": "pipeline", "what": what})


def _events(doc_or_list):
    return doc_or_list["events"] if isinstance(doc_or_list, dict) else doc_or_list


def window(ev):
    """(start, end, last_day) as dates; last_day = end + aftermath_days"""
    s, e = day(ev["start"]), day(ev["end"])
    return s, e, e + dt.timedelta(days=int(ev.get("aftermath_days", 30)))


# ---------- public API for the findings step ----------
def set_radar_finding(events, event_id, scene_id, finding, now=None, by="pipeline"):
    """Set linked_passes[scene_id].radar_finding of one event. `events` = the whole events.json dict or its events list.
    finding must be one of FINDINGS. Returns True if something changed (an edit_log line is added), False if the event or
    pass is unknown or the value is already set."""
    if finding not in FINDINGS:
        raise ValueError(f"finding must be one of {FINDINGS}, got {finding!r}")
    now = now or parse_now(None)
    for ev in _events(events):
        if ev["id"] != event_id:
            continue
        for lp in ev.get("linked_passes", []):
            if lp["scene_id"] == scene_id:
                if lp.get("radar_finding") == finding:
                    return False
                old = lp.get("radar_finding")
                lp["radar_finding"] = finding
                ev.setdefault("edit_log", []).append({"utc": iso(now), "by": by,
                                                      "what": f"radar_finding {scene_id}: {old} -> {finding}"})
                return True
    return False


def persist_radar_findings(path, triples, now=None):
    """Apply [(event_id, scene_id, finding)] (from build_story.radar_findings) to the events file and save it. Used by
    tools/pipeline/run_all.py after the findings step. Writes only when something changed. Returns the list of changed
    (event_id, scene_id, finding)."""
    now = now or parse_now(None)
    doc = load_json(path, None)
    if not doc:
        return []
    changed = [t for t in triples if set_radar_finding(doc, t[0], t[1], t[2], now)]
    if changed:
        doc["updated_utc"] = iso(now)
        dump_json(doc, path)
    return changed


# ---------- alerts -> candidates ----------
def alert_candidates(alerts, now):
    """Normalise alerts-v2 items into [{source, id, kind, name, start, end, issued, headline, link, severity, ...}]."""
    out = []
    for g in (alerts.get("gdacs") or {}).get("items", []):
        kind = GDACS_KIND.get(g.get("type"))
        if not kind or not g.get("from"):
            continue
        out.append({"source": "GDACS", "id": str(g["id"]), "kind": kind, "name": g.get("name") or f"GDACS {g['id']}",
                    "start": day(g["from"]), "end": day(g.get("to") or g["from"]), "issued": g["from"],
                    "headline": g.get("name") or "", "link": g.get("link"),
                    "severity": {"as_given": f"{g.get('alert_level')} alert" if g.get("alert_level") else None,
                                 "by": "GDACS"}, "credit": (alerts.get("gdacs") or {}).get("credit") or "GDACS"})
    for s in (alerts.get("sachet") or {}).get("items", []):
        head = s.get("headline") or ""
        kind = next((k for k, rx in SACHET_KIND_RX if rx.search(head)), None)
        if not kind or not s.get("issued"):
            continue
        d = day(s["issued"])
        out.append({"source": "SACHET", "id": str(s["id"]), "kind": kind,
                    "name": ("Cyclone alert" if kind == "cyclone" else "Flood alert") + f" ({s.get('source') or 'SACHET'})",
                    "start": d, "end": d, "issued": s["issued"], "headline": head, "link": s.get("link"),
                    "severity": {"as_given": s.get("category") or None, "by": s.get("source") or "SACHET"},
                    "credit": (alerts.get("sachet") or {}).get("credit") or "NDMA SACHET"})
    return out


def ref_of(c):
    return {"source": c["source"], "id": c["id"], "issued": c["issued"], "headline": c["headline"]}


def has_ref(ev, c):
    return any(r.get("source") == c["source"] and str(r.get("id")) == c["id"] for r in ev.get("alert_refs", []))


def overlaps(ev, c, slack=1):
    s, e, _ = window(ev)
    return c["start"] <= e + dt.timedelta(days=slack) and c["end"] >= s - dt.timedelta(days=slack)


def new_draft(c, ar, now):
    aft = int(ar["_defaults"]["aftermath_days"])
    ev = {
        "id": f"auto_{c['source']}_{c['id']}", "name": c["name"], "type": c["kind"], "area_id": ar["id"],
        "start": c["start"].isoformat(), "end": c["end"].isoformat(), "aftermath_days": aft,
        "window_source": f"{c['source']} alert {c['id']}: from {c['start'].isoformat()} to {c['end'].isoformat()} "
                         f"(as published; not checked by a person)",
        "source": {"name": c["source"], "url": c.get("link"), "ids": [c["id"]]}, "credit": c["credit"],
        "severity": c["severity"], "status": "alert_only", "status_text": STATUS_TEXT["alert_only"],
        "reviewed_by_human": False, "linked_passes": [], "description": c["headline"] or c["name"],
        "cannot_tell": ["This is an alert from an outside source. Radar has not been checked against it yet."],
        "confounders": [], "alert_refs": [ref_of(c)], "edit_log": [],
    }
    log(ev, now, f"draft created from {c['source']} alert {c['id']}")
    return ev


def refresh_draft(ev, c, now):
    """Update an auto draft from its alert (never a reviewed event). Returns True if anything changed."""
    changed = []
    for k, v in (("start", c["start"].isoformat()), ("end", c["end"].isoformat())):
        if ev.get(k) != v:
            ev[k] = v
            changed.append(k)
    if changed:
        ev["window_source"] = (f"{c['source']} alert {c['id']}: from {ev['start']} to {ev['end']} "
                               f"(as published; not checked by a person)")
    if ev.get("severity") != c["severity"]:
        ev["severity"] = c["severity"]
        changed.append("severity")
    if changed:
        log(ev, now, f"updated from {c['source']} alert {c['id']}: {', '.join(changed)}")
    return bool(changed)


# ---------- radar linking ----------
def default_finding(ar, role):
    cfg = (ar.get("roles") or {}).get(role) or {}
    return "sea_no_public_finding" if cfg.get("analysis") == "none_public" else "numbers_coming"


def link_passes(ev, scenes, ar, now):
    """Add catalogue scenes inside [start, end + aftermath_days]. Returns number of new links."""
    s, e, last = window(ev)
    have = {lp["scene_id"] for lp in ev.get("linked_passes", [])}
    added = []
    for sc in sorted(scenes, key=lambda x: (x["date"], x["role"])):
        d = day(sc["date"])
        if sc["scene_id"] in have or not (s <= d <= last):
            continue
        if sc["role"] not in (ar.get("roles") or {}):
            continue
        ev.setdefault("linked_passes", []).append({
            "scene_id": sc["scene_id"], "date": sc["date"], "role": sc["role"],
            "relation": "during" if d <= e else "after", "radar_finding": default_finding(ar, sc["role"])})
        added.append(sc["scene_id"])
    if added:
        log(ev, now, "linked radar pass(es): " + ", ".join(added))
        if ev.get("status") == "alert_only" and not ev.get("reviewed_by_human"):
            ev["status"] = "radar_linked"
            ev["status_text"] = STATUS_TEXT["radar_linked"]
    return len(added)


# ---------- main update ----------
def update(doc, alerts, catalog, ar, now):
    """Return (new_doc, changes: list[str]). Does not touch the inputs."""
    doc = copy.deepcopy(doc) if doc else {"schema": SCHEMA, "updated_utc": None, "events": []}
    doc["schema"] = SCHEMA
    evs = doc["events"]
    changes = []
    aft = int(ar["_defaults"]["aftermath_days"])
    mine = lambda ev: ev.get("area_id") == ar["id"]  # noqa: E731

    for c in alert_candidates(alerts or {}, now):
        if c["end"] + dt.timedelta(days=aft) < now.date():
            continue   # alert (plus its aftermath window) is over: no new draft; existing events keep their refs
        holder = next((ev for ev in evs if mine(ev) and has_ref(ev, c)), None)
        if holder:
            if not holder.get("reviewed_by_human") and holder.get("status") != "dismissed" and refresh_draft(holder, c, now):
                changes.append(f"refreshed {holder['id']}")
            continue
        twin = next((ev for ev in evs if mine(ev) and ev.get("reviewed_by_human") and ev.get("type") == c["kind"]
                     and ev.get("status") != "dismissed" and overlaps(ev, c)), None)
        if twin:
            twin.setdefault("alert_refs", []).append(ref_of(c))
            log(twin, now, f"added alert_ref {c['source']} {c['id']} (same event)")
            changes.append(f"alert_ref {c['source']} {c['id']} -> {twin['id']}")
            continue
        if any(ev["id"] == f"auto_{c['source']}_{c['id']}" for ev in evs):
            continue   # same id in another area: leave it alone
        evs.append(new_draft(c, ar, now))
        changes.append(f"new draft auto_{c['source']}_{c['id']}")

    scenes = (catalog or {}).get("scenes", [])
    for ev in evs:
        if not mine(ev) or ev.get("status") == "dismissed":
            continue
        n = link_passes(ev, scenes, ar, now)
        if n:
            changes.append(f"{ev['id']}: +{n} pass(es)")

    doc["updated_utc"] = iso(now)   # every run stamps itself; everything else stays identical when nothing changed
    return doc, changes


def strip_stamp(doc):
    d = copy.deepcopy(doc)
    d.pop("updated_utc", None)
    return d


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--area", default=None)
    ap.add_argument("--config", default=None, help=f"areas config (default config/areas.json; env {AREAS_ENV})")
    ap.add_argument("--now", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--events", default=str(EVENTS))
    ap.add_argument("--alerts", default=str(ALERTS))
    ap.add_argument("--catalog", default=str(CATALOG))
    a = ap.parse_args()
    if a.config:
        import os
        os.environ[AREAS_ENV] = a.config
    ar = load_area(a.area)
    now = parse_now(a.now)
    doc = load_json(a.events, None)
    alerts = load_json(a.alerts, {})
    if alerts and alerts.get("schema") != "alerts-v2":
        print(f"WARN {a.alerts} is not alerts-v2: no drafts made from it")
        alerts = {}
    new, changes = update(doc, alerts, load_json(a.catalog, {"scenes": []}), ar, now)
    for c in changes or ["no content changes"]:
        print(" -", c)
    if a.dry_run:
        print("[dry-run] nothing written")
        return 0
    dump_json(new, a.events)
    print("wrote", a.events, f"({len(new['events'])} events)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
