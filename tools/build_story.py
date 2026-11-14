#!/usr/bin/env python3
"""Build the live "What happened" story: data/web/story.json, feed.json (JSON Feed 1.1) and atom.xml (stdlib only).

Reads (all relative to the repo root):
  data/h5/catalog.json                  scenes (start time, status, track)
  data/events/*.json                    event files; only status "active" is published (stubs with "needs_review" never are)
  data/processed/mandal_rank.json       per-mandal shares; ``by_date`` = one block per coast date
  data/processed/profile.json           eye radius (sea eye pass)
  data/web/class_stats.json             new-water areas (water class only)
  data/story_rules.json, data/seasons.json, app/strings/story.en.json
No LLM and no typed numbers: every number in every sentence comes from those files, every sentence from a template.
Rules (docs/review/LIVE_STORY_SPEC.md): only the WATER class backs headline claims; every flood claim is hedged; banned
words and leftover {placeholders} fail the build (exit 1).

State: event (active event, first radar picture) | recovery (active event, later pictures) | watch (no active event inside
the monitor window) | stale (active event but the newest radar scene is older than stale_after_days: the page says so).

Usage: python3 tools/build_story.py [--root DIR] [--now 2026-11-14T12:00:00Z] [--out DIR]
"""
import argparse
import datetime as dt
import glob
import json
import math
import os
import re
import sys
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
IST = dt.timedelta(hours=5, minutes=30)


class StoryError(Exception):
    pass


# ------------------------------------------------------------------ small helpers
def jload(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def parse_utc(s):
    return dt.datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=dt.timezone.utc)


def iso_utc(t):
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def dmon(iso):
    """'2026-11-09' -> '9 Nov'"""
    d = dt.date.fromisoformat(iso[:10])
    return "%d %s" % (d.day, MONTHS[d.month - 1])


def ist_text(t, year=True):
    t = t + IST
    return "%d %s%s, %02d:%02d" % (t.day, MONTHS[t.month - 1], " %d" % t.year if year else "", t.hour, t.minute)


def fill(tpl, **kw):
    """Fill {placeholders}; a placeholder with no value is an error (never silently left in the text)."""
    def rep(m):
        k = m.group(1)
        if k not in kw or kw[k] is None:
            raise StoryError("template %r needs value for {%s}" % (tpl[:60], k))
        return str(kw[k])
    return re.sub(r"\{([a-z_0-9]+)\}", rep, tpl)


def num(v):
    """share in 100 acres: integer from 1 up, one decimal below 1"""
    v = float(v)
    return str(int(round(v))) if v >= 1 else ("0" if v < 0.05 else "%.1f" % v)


def err_text(e):
    """give-or-take: rounded, never below 1 (a smaller error is not claimed)"""
    return str(max(1, int(round(float(e or 0)))))


def signed(v):
    v = float(v)
    s = num(abs(v)) if abs(v) >= 0.05 else "0"
    return ("+" if v > 0.04 else "-" if v < -0.04 else "") + s


def times_words(ratio, tw):
    if ratio < tw["less_than"]:
        return "less than"
    if ratio < tw["same_below"]:
        return "about the same as"
    if ratio < tw["one_and_a_half_below"]:
        return "about one and a half times"
    if ratio < tw["twice_below"]:
        return "about twice"
    if ratio > tw["cap_above"]:
        return tw["cap_words"]
    return "about %d times" % int(round(ratio))


# ------------------------------------------------------------------ analysis of mandal rows
def is_flooded(row, rules):
    """Water class only (rules.flooded_mandal.class_basis == 'water')."""
    f = rules["flooded_mandal"]
    if row.get("flag") or (row.get("coverage_pct") or 0) < f["min_radar_coverage_pct"]:
        return False
    normal = row.get("normal_water_pct")
    if normal is None:
        normal = row.get("normal_pct") or 0.0
    w = row.get("water_pct") or 0.0
    return w >= f["min_likely_water_pct"] and w >= f["min_times_normal"] * normal


def trend(now, prev, rules):
    c = rules["change_vs_previous_pass"]
    margin = max(c["min_points"], c["report_change_only_if_abs_change_exceeds_error_multiple"] * max(now.get("err") or 0, prev.get("err") or 0))
    d = (now.get("water_pct") or 0) - (prev.get("water_pct") or 0)
    return "down" if -d >= margin else "up" if d >= margin else "flat"


def compare(rows_now, rows_prev, rules):
    """Counts of mandals flooded now / before and how they moved. rows_prev None = no earlier pass."""
    now_by = {r["mandal"]: r for r in rows_now}
    n_now = sum(1 for r in rows_now if is_flooded(r, rules))
    out = {"flooded_now": n_now, "flooded_prev": None, "receded": 0, "still": 0, "worse": 0, "prev_flooded_receded_share": None}
    if rows_prev is None:
        return out
    prev_by = {r["mandal"]: r for r in rows_prev}
    n_prev = sum(1 for r in rows_prev if is_flooded(r, rules))
    out["flooded_prev"] = n_prev
    pf = 0
    prf = 0
    for m, p in prev_by.items():
        n = now_by.get(m)
        if n is None or n.get("flag") or p.get("flag"):
            continue
        if not (is_flooded(p, rules) or is_flooded(n, rules)):
            continue
        t = trend(n, p, rules)
        out["receded" if t == "down" else "worse" if t == "up" else "still"] += 1
        if is_flooded(p, rules):
            pf += 1
            prf += (t == "down")
    out["prev_flooded_receded_share"] = (prf / pf) if pf else None
    return out


def headline_key(cmp_, rules, has_prev):
    if cmp_["flooded_now"] == 0 and not (cmp_["flooded_prev"] or 0):
        return "no_flood"
    if not has_prev:
        return "first_pass"
    if cmp_["flooded_now"] > (cmp_["flooded_prev"] or 0):
        return "worse"
    share = cmp_["prev_flooded_receded_share"] or 0.0
    h = rules["headline_keys"]
    if share >= h["recovery.most"]["receded_share_of_previously_flooded_min"]:
        return "recovery.most"
    if share >= h["recovery.partial"]["receded_share_of_previously_flooded_min"]:
        return "recovery.partial"
    return "recovery.little"


def headline_text(key, S, event_name, date_txt, practice):
    h = S["headline"]
    if key.startswith("recovery."):
        t = fill(h["recovery"][key.split(".")[1]], event=event_name)
    elif key == "first_pass":
        t = fill(h["first_pass"], event=event_name)
    else:
        t = h[key] if "{" not in h[key] else fill(h[key], date=date_txt)
    return (h["practice_prefix"] + t) if practice else t


# ------------------------------------------------------------------ the build
def scene_status(by_date_block, catalog_scene):
    return (by_date_block or {}).get("product_status") or (catalog_scene or {}).get("product_status")


def build(inp, now):
    """Pure function: inputs dict -> story dict. ``now`` = aware datetime (UTC)."""
    rules, S, seasons = inp["rules"], inp["strings"], inp.get("seasons") or {}
    catalog = (inp.get("catalog") or {}).get("scenes", [])
    rank, profile, cstats = inp.get("rank"), inp.get("profile"), inp.get("class_stats")
    event = pick_event(inp.get("events") or [], now, rules)
    story = {"schema": "story-v1", "built_utc": iso_utc(now), "built_text": ist_text(now) + " IST", "event_id": event["id"] if event else None,
             "official_banner": S["official_banner"], "official_links": (event or {}).get("official_links") or []}
    # --- latest radar scene (any role) and staleness
    scenes = [s for s in catalog if s.get("start_utc")]
    newest = max(scenes, key=lambda s: s["start_utc"]) if scenes else None
    data_as_of = parse_utc(newest["start_utc"]) if newest else None
    story["data_as_of"] = iso_utc(data_as_of) if data_as_of else None
    story["data_as_of_text"] = fill(S["timestamps"]["picture"], date=ist_text(data_as_of)) if data_as_of else None
    story["timestamps"] = {"picture": story["data_as_of_text"], "built": fill(S["timestamps"]["built"], built=story["built_text"])}
    stale_days = (now - data_as_of).total_seconds() / 86400.0 if data_as_of else None
    stale = bool(data_as_of and stale_days > rules["stale_after_days"])
    story["stale"] = stale
    # --- passes with numbers
    by_date = (rank or {}).get("by_date") or {}
    dates = sorted(by_date)
    sample = (not rank) or (not rank.get("provenance")) or bool(rank.get("placeholder"))
    nobl = not dates
    # --- next pass: last pass of the same track + 12 days (coast track of the newest analysed scene)
    coast = [s for s in scenes if s["role"] == "COAST"]
    sea = [s for s in scenes if s["role"] == "SEA"]
    nxt = []
    for role, group in (("COAST", coast), ("SEA", sea)):
        if group:
            last = max(group, key=lambda s: s["start_utc"])
            same = [s for s in group if s["track"] == last["track"]]
            lastp = max(same, key=lambda s: s["start_utc"])
            nd = parse_utc(lastp["start_utc"]) + dt.timedelta(days=rules["next_pass_basis_days"])
            nxt.append({"role": role, "track": lastp["track"], "last_pass": lastp["date"], "date": nd.strftime("%Y-%m-%d"), "expected_utc": iso_utc(nd)})
    main_next = next((n for n in nxt if n["role"] == "COAST"), nxt[0] if nxt else None)
    if main_next:
        nd = dt.date.fromisoformat(main_next["date"])
        days_until = (nd - now.date()).days
        tpl = S["next_pass"] if days_until >= 0 else S["next_pass_overdue"]
        main_next = dict(main_next, days_until=days_until, overdue=days_until < 0, basis="last pass of the same track + %d days (NISAR repeat)" % rules["next_pass_basis_days"],
                         text=fill(tpl, next_date=dmon(main_next["date"])))
    story["next_pass"] = main_next
    story["next_passes"] = nxt
    # --- no numbers at all
    if nobl:
        story.update(state="watch" if not event else "event", base_state="watch" if not event else "event", numbers_ready=False,
                     headline=S["missing_numbers"], sub=(fill(S["lead"]["watch"], date=dmon(newest["date"])) if newest else ""),
                     big_numbers=[], map_layer_id="nisar_class_new_water", mandal_sentences={}, mandals={}, updates=[], since_last=None, confounders=[],
                     badges={"provisional": False, "sample": True}, headline_key="missing_numbers")
        story["feed"] = {"json": "feed.json", "atom": "atom.xml"}
        return story
    # --- event geometry
    landfall = (event or {}).get("dates", {}).get("landfall_day") or (event or {}).get("landfall", {}).get("date")
    newest_d = dates[-1]
    prev_d = dates[-2] if len(dates) > 1 else None
    event_name = (event or {}).get("name") or "the storm"
    days_after = (dt.date.fromisoformat(newest_d) - dt.date.fromisoformat(landfall)).days if landfall else None
    in_window = bool(event and landfall and 0 <= (now.date() - dt.date.fromisoformat(landfall)).days <= (event.get("monitor_days") or rules["monitor_window_days"]))
    passes_since = [d for d in dates if landfall and d >= landfall]
    base_state = "watch" if not in_window else ("event" if len(passes_since) <= 1 else "recovery")
    state = "stale" if (stale and base_state in ("event", "recovery")) else base_state
    story["state"], story["base_state"] = state, base_state
    story["numbers_ready"] = True
    story["event"] = {"id": event["id"], "name": event_name, "landfall_day": landfall, "status": event.get("status")} if event else None

    cls_info = class_summary(cstats, newest_d, S, rules)
    cards = {}
    for i, d in enumerate(dates):
        cards[d] = card_for(d, by_date, dates[i - 1] if i else None, event, landfall, rules, S, sample, inp, profile, cls_info_for(cstats, d, S, rules), now)
    cur = cards[newest_d]
    # --- provisional badge: newest scene or any baseline scene provisional
    base_status = []
    for bd in (cstats or {}).get("baseline_dates", []):
        sc = ((cstats or {}).get("scenes") or {}).get("%s-%s-%s" % (bd[:4], bd[4:6], bd[6:]))
        if sc:
            base_status.append(sc.get("product_status"))
    provisional = (cur["status"] == "PROVISIONAL") or any(x == "PROVISIONAL" for x in base_status)
    story["badges"] = {"provisional": bool(provisional), "sample": bool(sample)}
    story["provisional_text"] = S["provisional"] if provisional else None
    practice = sample
    # --- headline / sub
    key = cur["headline_key"]
    sub_parts = [cur["lead"]]
    if provisional:
        sub_parts.append(S["provisional"])
    if state == "stale":
        story_headline = fill(S["headline"]["no_new_pass"], date=dmon(data_as_of.strftime("%Y-%m-%d")))
        key = "no_new_pass"
        sub_parts.insert(0, fill(S["stale"], days=int(stale_days), date=dmon(data_as_of.strftime("%Y-%m-%d"))))
        story_headline = (S["headline"]["practice_prefix"] if practice else "") + story_headline
    elif state == "watch":
        story_headline = (S["headline"]["practice_prefix"] if practice else "") + S["headline"]["watch"]
        key = "watch"
        sub_parts = [fill(S["lead"]["watch"], date=dmon(newest_d))]
        month = now.month
        line = next((x["line"] for x in seasons.get("seasons", []) if month in x["months"]), None)
        sub_parts.append(S["watch"]["normal_check"] if cur["flooded_now"] == 0 else S["watch"]["flood_signal"])
        if line:
            sub_parts.append(line)
        sub_parts.append(S["watch"]["link"])
        if provisional:
            sub_parts.append(S["provisional"])
    else:
        story_headline = cur["headline"]
    story["headline"], story["headline_key"] = story_headline, key
    story["sub"] = " ".join(sub_parts)
    story["lead"] = cur["lead"]
    story["since_last"] = cur["since_last"]
    story["confounders"] = cur["confounders"]
    story["class_summary"] = cur["class_text"]
    # --- three big numbers
    story["big_numbers"] = big_numbers(cur, state, story["next_pass"], newest, now, S, days_after)
    story["map_layer_id"] = "nisar_class_new_water"
    story["map"] = {"layer_id": "nisar_class_new_water", "mode": "share", "date": newest_d, "caption_key": "share"}
    story["mandal_sentences"] = cur["mandal_sentences"]
    story["mandals"] = cur["mandals"]
    story["scene"] = {"date": newest_d, "scene_id": cur["scene_id"], "status": cur["status"], "start_utc": cur["start_utc"], "days_after_landfall": days_after}
    # --- archive
    ups = [cards[d]["update"] for d in dates]
    ups += sea_updates(catalog, event, landfall, profile, S, rules, dates)
    ups.sort(key=lambda u: (u["date"], u["kind"]), reverse=True)
    seen = {}
    for u in ups:                               # ids are the scene date; a second scene on the same date gets a suffix
        if u["id"] in seen:
            u["id"] = "%s-%s" % (u["id"], u["kind"])
        seen[u["id"]] = 1
    story["updates"] = ups
    story["feed"] = {"json": "feed.json", "atom": "atom.xml"}
    return story


def pick_event(events, now, rules):
    act = [e for e in events if e.get("status") == "active"]
    if not act:
        return None
    def lf(e):
        return (e.get("dates") or {}).get("landfall_day") or (e.get("landfall") or {}).get("date") or "0000-00-00"
    return sorted(act, key=lf)[-1]


def cls_info_for(cstats, d, S, rules):
    return class_summary(cstats, d, S, rules)


def class_summary(cstats, iso, S, rules):
    """New open water (water class only) for one date from class_stats.json: km2, share, range over k, normal fortnight share."""
    if not cstats:
        return None
    key = iso.replace("-", "")
    c = cstats.get("classes", {})
    mid = c.get("%s|k=3.0" % key)
    nrm = c.get("normal|k=3.0")
    if not mid or not nrm:
        return None
    lo = c.get("%s|k=4.0" % key, mid)["new_water_km2"]
    hi = c.get("%s|k=2.0" % key, mid)["new_water_km2"]
    ratio = (mid["new_water_pct_of_land"] / nrm["new_water_pct_of_land"]) if nrm["new_water_pct_of_land"] > 0 else float("inf")
    tw = times_words(ratio if ratio != float("inf") else 1e9, rules["times_normal_words"])
    return {"new_water_km2": mid["new_water_km2"], "new_water_pct_of_land": mid["new_water_pct_of_land"], "range_km2": [lo, hi],
            "normal_new_water_pct_of_land": nrm["new_water_pct_of_land"], "times_normal": tw,
            "text": fill(S["update"]["coast_summary"], km2=int(round(mid["new_water_km2"])), lo=int(round(lo)), hi=int(round(hi)), times=tw),
            "source_file": "data/web/class_stats.json"}


def confounders_for(event, iso):
    out = []
    for c in (event or {}).get("confounders") or []:
        if iso in (c.get("affects_dates") or []):
            out.append(c.get("text") or c.get("name"))
    return out


def card_for(d, by_date, prev_d, event, landfall, rules, S, sample, inp, profile, cls_info, now):
    blk = by_date[d]
    rows = blk["rows"]
    prev_rows = by_date[prev_d]["rows"] if prev_d else None
    cmp_ = compare(rows, prev_rows, rules)
    key = headline_key(cmp_, rules, prev_d is not None)
    event_name = (event or {}).get("name") or "the storm"
    days_after = (dt.date.fromisoformat(d) - dt.date.fromisoformat(landfall)).days if landfall else None
    headline = headline_text(key, S, event_name, dmon(d), sample)
    conf = confounders_for(event, d)
    if days_after == 0:
        lead = fill(S["lead"]["landfall_day"], date=dmon(d), event=event_name)
    elif days_after is not None and days_after > 0 and prev_d:
        lead = fill(S["lead"]["recovery"], date=dmon(d), days_after=days_after)
    else:
        lead = fill(S["lead"]["first_pass"], date=dmon(d))
    if conf:
        lead = lead + " " + " ".join(conf)
    # top mandal by new water (rank_water) among ranked rows
    ranked = [r for r in rows if not r.get("flag") and r.get("rank_water")]
    top = min(ranked, key=lambda r: r["rank_water"]) if ranked else None
    prev_by = {r["mandal"]: r for r in (prev_rows or [])}
    since = None
    if prev_rows is not None:
        since = {"prev_date": prev_d, "this_date": d, "prev_scene": by_date[prev_d].get("scene_id"), "this_scene": blk.get("scene_id"),
                 "days_apart": (dt.date.fromisoformat(d) - dt.date.fromisoformat(prev_d)).days,
                 "flooded_mandals_prev": cmp_["flooded_prev"], "flooded_mandals_now": cmp_["flooded_now"],
                 "receded": cmp_["receded"], "still": cmp_["still"], "worse": cmp_["worse"],
                 "chips": {"down": S["since_last"]["chip_down"], "same": S["since_last"]["chip_same"], "up": S["since_last"]["chip_up"]},
                 "title": S["since_last"]["title"]}
        since["text"] = fill(S["since_last"]["text"], prev_date=dmon(prev_d), date=dmon(d), n_prev=cmp_["flooded_prev"], n_now=cmp_["flooded_now"],
                             receded=cmp_["receded"], still=cmp_["still"], worse=cmp_["worse"])
        if top and top["mandal"] in prev_by:
            p = prev_by[top["mandal"]]
            since["water_pct_change"] = {"mandal": top["mandal"], "prev": p["water_pct"], "now": top["water_pct"],
                                         "change_pts": round(top["water_pct"] - p["water_pct"], 2), "source_file": "data/processed/mandal_rank.json"}
            if landfall and prev_d != landfall and landfall in by_date:
                lf_row = next((r for r in by_date[landfall]["rows"] if r["mandal"] == top["mandal"]), None)
                if lf_row:
                    since["since_landfall"] = fill(S["since_last"]["since_landfall"], top_mandal=top["mandal"], lik_then=num(lf_row["water_pct"]), lik=num(top["water_pct"]))
    sentences, detail = {}, {}
    for r in rows:
        t = trend(r, prev_by[r["mandal"]], rules) if r["mandal"] in prev_by else "new"
        sentences[r["mandal"]] = mandal_sentence(r, t, d, prev_d, S, rules)
        detail[r["mandal"]] = {"water_pct": r["water_pct"], "err": r.get("err"), "normal_water_pct": r.get("normal_water_pct"), "trend": t,
                               "flooded": is_flooded(r, rules), "rank_water": r.get("rank_water"), "area_km2": r.get("area_km2"),
                               "water_km2": r.get("water_km2"), "coverage_pct": r.get("coverage_pct"),
                               "confidence": "low" if r.get("flag") else ("high" if (r.get("err") or 0) <= max(1.0, 0.25 * r["water_pct"]) else "medium")}
    cur_status = blk.get("product_status")
    link = permalink_coast(d, d == max(by_date))
    update = {"id": d, "kind": "coast", "date": d, "scene_ids": [blk.get("scene_id")] if blk.get("scene_id") else [], "days_after_landfall": days_after,
              "status": cur_status, "headline_key": key, "headline": headline, "text": " ".join([lead] + ([cls_info["text"]] if cls_info else [])),
              "since_last": since, "confounders": conf, "permalink": link, "hash": link.lstrip("#"),
              "map_layer_id": "nisar_class_new_water", "start_utc": blk.get("start_utc"),
              "cataloged_utc": ((inp.get("class_stats") or {}).get("scenes") or {}).get(d, {}).get("cataloged_utc"),
              "class_summary": cls_info}
    card = {"headline": headline, "headline_key": key, "lead": lead, "since_last": since, "confounders": conf, "top": top, "prev_top": prev_by.get(top["mandal"]) if top else None,
            "flooded_now": cmp_["flooded_now"], "status": cur_status, "scene_id": blk.get("scene_id"), "start_utc": blk.get("start_utc"),
            "mandal_sentences": sentences, "mandals": detail, "update": update, "class_text": cls_info, "has_prev": prev_d is not None, "date": d}
    update["big_numbers"] = card_numbers(card, S, days_after)
    return card


def mandal_sentence(r, t, d, prev_d, S, rules):
    m = S["mandal"]
    name = r["mandal"]
    if r.get("flag") or (r.get("coverage_pct") or 0) < rules["flooded_mandal"]["min_radar_coverage_pct"]:
        return m["not_enough_view"]
    err = err_text(r.get("err"))
    if is_flooded(r, rules):
        normal = r.get("normal_water_pct")
        parts = [fill(m["main"], lik=num(r["water_pct"]), mandal=name, date=dmon(d), err=err)]
        if normal is not None:
            ratio = (r["water_pct"] / normal) if normal > 0 else 1e9
            parts.append(fill(m["times"], times=times_words(ratio, rules["times_normal_words"])))
    else:
        parts = [fill(m["low"], mandal=name, date=dmon(d), lik=num(r["water_pct"]), err=err)]
    if t == "new" or not prev_d:
        parts.append(m["trend_new"])
    else:
        parts.append(fill(m["trend_" + {"down": "down", "up": "up", "flat": "flat"}[t]], prev_date=dmon(prev_d)))
    parts.append(m["ask_officials"])
    return " ".join(parts)


def card_numbers(card, S, days_after):
    """The 3 big numbers of one coast card (top mandal share, change vs last pass or flooded count, days after landfall)."""
    top = card["top"]
    out = []
    if top:
        b = S["bignums"]["top_mandal"]
        out.append({"id": "top_mandal", "value": fill(b["value"], lik=num(top["water_pct"])), "unit": b["unit"],
                    "label": fill(b["label"], top_mandal=top["mandal"], err=err_text(top.get("err"))),
                    "mandal": top["mandal"], "raw": top["water_pct"], "err": top.get("err"), "source_file": "data/processed/mandal_rank.json"})
    prev_top = card["prev_top"]
    if top and card["has_prev"] and prev_top:
        b = S["bignums"]["change"]
        out.append({"id": "change", "value": fill(b["value"], change_pts=signed(top["water_pct"] - prev_top["water_pct"])), "unit": b["unit"],
                    "label": fill(b["label"], top_mandal=top["mandal"]), "raw": round(top["water_pct"] - prev_top["water_pct"], 2),
                    "source_file": "data/processed/mandal_rank.json"})
    else:
        b = S["bignums"]["flooded_count"]
        out.append({"id": "flooded_count", "value": fill(b["value"], n_now=card["flooded_now"]), "unit": b["unit"], "label": b["label"], "raw": card["flooded_now"],
                    "source_file": "data/processed/mandal_rank.json"})
    if days_after is not None and days_after >= 0:
        b = S["bignums"]["days_after"]
        out.append({"id": "days_after", "value": fill(b["value"], days_after=days_after), "unit": b["unit"], "label": b["label"], "raw": days_after,
                    "source_file": "data/events/ (landfall_day) and data/h5/catalog.json"})
    return out


def big_numbers(cur, state, nxt, newest, now, S, days_after):
    nums = card_numbers(cur, S, days_after)
    if state == "watch":
        b = S["bignums"]["flooded_count"]
        w = [{"id": "flooded_count", "value": fill(b["value"], n_now=cur["flooded_now"]), "unit": b["unit"], "label": b["label"], "raw": cur["flooded_now"],
              "source_file": "data/processed/mandal_rank.json"}]
        if nxt:
            b = S["bignums"]["days_to_next"]
            w.append({"id": "days_to_next", "value": fill(b["value"], days=max(0, nxt["days_until"])), "unit": b["unit"], "label": b["label"], "raw": nxt["days_until"],
                      "source_file": "data/h5/catalog.json"})
        if newest:
            b = S["bignums"]["days_since_pass"]
            d = (now.date() - dt.date.fromisoformat(newest["date"])).days
            w.append({"id": "days_since_pass", "value": fill(b["value"], days=d), "unit": b["unit"], "label": b["label"], "raw": d, "source_file": "data/h5/catalog.json"})
        return w[:3]
    return nums[:3]


def permalink_coast(d, is_newest):
    """Same key=value format as the dashboard's own hash (dash.js toHash): the newest class date is the 'share' map, older dates are radar views."""
    return "#tab=happened&mode=share&d=%s" % d if is_newest else "#tab=happened&mode=radar&role=coast&d=%s" % d


def sea_updates(catalog, event, landfall, profile, S, rules, coast_dates):
    out = []
    if not landfall:
        return out
    cut = (dt.date.fromisoformat(landfall) - dt.timedelta(days=rules.get("archive", {}).get("sea_scenes_from_days_before_landfall", 1))).isoformat()
    eye_date = None
    if profile and profile.get("layer_id"):
        m = re.search(r"_(\d{8})_", profile["layer_id"])
        eye_date = "%s-%s-%s" % (m.group(1)[:4], m.group(1)[4:6], m.group(1)[6:]) if m else None
    name = (event or {}).get("name") or "the storm"
    for s in catalog:
        if s["role"] != "SEA" or s["date"] < cut:
            continue
        d = s["date"]
        eye = (d == eye_date)
        if eye:
            text = fill(S["update"]["sea_eye"], date=dmon(d), event=name)
            link = "#tab=happened&mode=eye&d=%s" % d
        else:
            text = fill(S["update"]["sea_after"], date=dmon(d))
            link = "#tab=happened&mode=radar&role=sea&d=%s" % d
        nums = []
        if eye and profile and profile.get("eye_radius_km") is not None:
            b = S["bignums"]["eye_radius"]
            nums.append({"id": "eye_radius", "value": fill(b["value"], radius=num(profile["eye_radius_km"])), "unit": b["unit"],
                         "label": fill(b["label"], err=err_text(profile.get("eye_radius_err"))), "raw": profile["eye_radius_km"], "source_file": "data/processed/profile.json"})
        out.append({"id": d, "kind": "sea", "date": d, "scene_ids": [s["scene_id"]], "days_after_landfall": (dt.date.fromisoformat(d) - dt.date.fromisoformat(landfall)).days,
                    "status": s["product_status"], "headline_key": "sea_eye" if eye else "sea_after", "headline": text, "text": text, "since_last": None,
                    "confounders": [], "permalink": link, "hash": link.lstrip("#"), "map_layer_id": s.get("layer_id") or ("nisar_l_sea_%s_t%d_vv" % (d.replace("-", ""), s["track"])),
                    "start_utc": s["start_utc"], "cataloged_utc": s.get("cataloged_utc"), "big_numbers": nums, "class_summary": None})
    return out


# ------------------------------------------------------------------ guards
def all_strings(o, path=""):
    if isinstance(o, str):
        yield path, o
    elif isinstance(o, dict):
        for k, v in o.items():
            if k in ("official_banner", "official_links", "provisional_text"):
                continue
            yield from all_strings(v, path + "/" + str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from all_strings(v, path + "/%d" % i)


def validate(story, rules):
    """Raise StoryError on a banned word, a leftover {placeholder}, a flood claim without a hedge, or a sentence over the length limit."""
    errs = []
    banned = [re.compile(r"(?<![A-Za-z])%s(?![A-Za-z])" % re.escape(w), re.I) for w in rules["banned_words"]]
    ph = re.compile(rules["guard"]["placeholder_pattern"])
    hedge = [h.lower() for h in rules["hedge_words"]]
    need = [n.lower() for n in rules["require_hedge_for"]]
    maxw = rules.get("reading_level", {}).get("max_words_per_sentence", 20)
    skip = ("/permalink", "/hash", "/id", "/scene", "/source_file", "/start_utc", "/cataloged_utc", "/map_layer_id", "/headline_key", "/event_id", "/schema",
            "/built_utc", "/data_as_of", "/expected_utc", "/date", "/prev_date", "/this_date", "/mandal", "/basis", "/last_pass", "/role", "/kind", "/status", "/state",
            "/base_state", "/chips", "/caption_key", "/layer_id", "/mode", "/name", "/landfall_day", "/feed", "/unit", "/value", "/raw", "/start", "/title")
    for path, s in all_strings(story):
        if any(path.endswith(x) for x in skip) and "/mandal_sentences" not in path:
            continue
        if path.startswith("/mandals/") or path.startswith("/next_passes"):
            continue
        if ph.search(s):
            errs.append("leftover placeholder in %s: %r" % (path, s[:80]))
        for rx in banned:
            if rx.search(s):
                errs.append("banned word %r in %s: %r" % (rx.pattern, path, s[:80]))
        for sent in re.split(r"(?<=[.!?])\s+", s):
            low = sent.lower()
            if any(n in low for n in need) and not any(h in low for h in hedge):
                errs.append("flood claim without a hedge in %s: %r" % (path, sent[:100]))
            if len(sent.split()) > maxw and ("/sub" in path or "/text" in path or "/headline" in path or "/mandal_sentences" in path):
                errs.append("sentence over %d words in %s: %r" % (maxw, path, sent[:100]))
    if errs:
        raise StoryError("story guard failed:\n  " + "\n  ".join(errs))


# ------------------------------------------------------------------ feeds
def feeds(story, strings, rules, event):
    site = rules.get("site_url", "").rstrip("/") + "/"
    title = fill(strings["feed"]["title"], event=(event or {}).get("name") or "NISAR coast")
    items = []
    for u in story.get("updates", []):
        stat = (u.get("status") or "").lower() or "unknown"
        when = u.get("cataloged_utc") or u.get("start_utc") or story["built_utc"]
        items.append({"id": "spacebros-nisar:%s:%s:%s" % ((event or {}).get("id") or "none", u["kind"], u["id"]), "url": site + u["permalink"],
                      "title": fill(strings["feed"]["item"], headline=u["headline"], status=stat), "content_text": u["text"],
                      "summary": u["headline"], "date_published": when, "tags": [u["kind"], stat]})
    jf = {"version": "https://jsonfeed.org/version/1.1", "title": title, "home_page_url": site, "feed_url": site.rsplit("app/", 1)[0] + "data/web/feed.json",
          "description": strings["official_banner"], "language": "en", "items": items}
    upd = max([i["date_published"] for i in items] + [story["built_utc"]])
    a = ['<?xml version="1.0" encoding="utf-8"?>', '<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="en">', "  <title>%s</title>" % escape(title),
         '  <link href="%s"/>' % escape(site), '  <link rel="self" href="%s"/>' % escape(jf["feed_url"].replace("feed.json", "atom.xml")),
         "  <id>%s</id>" % escape("spacebros-nisar:%s" % ((event or {}).get("id") or "none")), "  <updated>%s</updated>" % escape(upd),
         "  <subtitle>%s</subtitle>" % escape(strings["official_banner"])]
    for i in items:
        a += ["  <entry>", "    <title>%s</title>" % escape(i["title"]), '    <link href="%s"/>' % escape(i["url"]), "    <id>%s</id>" % escape(i["id"]),
              "    <updated>%s</updated>" % escape(i["date_published"]), "    <summary>%s</summary>" % escape(i["content_text"]), "  </entry>"]
    a.append("</feed>")
    return jf, "\n".join(a) + "\n"


def load_inputs(root):
    p = lambda *x: os.path.join(root, *x)
    events = []
    for f in sorted(glob.glob(p("data", "events", "*.json"))):
        try:
            events.append(jload(f))
        except ValueError as e:
            raise StoryError("%s: %s" % (f, e))
    return {"catalog": jload(p("data", "h5", "catalog.json")), "events": events, "rank": jload(p("data", "processed", "mandal_rank.json")),
            "profile": jload(p("data", "processed", "profile.json")), "class_stats": jload(p("data", "web", "class_stats.json")),
            "rules": jload(p("data", "story_rules.json")), "seasons": jload(p("data", "seasons.json")), "strings": jload(p("app", "strings", "story.en.json"))}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--out", default=None, help="output dir (default <root>/data/web)")
    ap.add_argument("--now", default=None, help="override the build time (UTC, 2026-11-14T12:00:00Z) for tests")
    a = ap.parse_args()
    inp = load_inputs(a.root)
    for k in ("rules", "strings"):
        if not inp[k]:
            print("build_story: missing %s" % k, file=sys.stderr)
            return 1
    now = parse_utc(a.now) if a.now else dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    try:
        story = build(inp, now)
        validate(story, inp["rules"])
        ev = next((e for e in inp["events"] if e.get("id") == story.get("event_id")), None)
        jf, atom = feeds(story, inp["strings"], inp["rules"], ev)
        validate({"feed": [{"title": i["title"], "text": i["content_text"]} for i in jf["items"]]}, inp["rules"])
    except StoryError as e:
        print("build_story FAILED: %s" % e, file=sys.stderr)
        return 1
    out = a.out or os.path.join(a.root, "data", "web")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "story.json"), "w", encoding="utf-8") as fh:
        json.dump(story, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    with open(os.path.join(out, "feed.json"), "w", encoding="utf-8") as fh:
        json.dump(jf, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    with open(os.path.join(out, "atom.xml"), "w", encoding="utf-8") as fh:
        fh.write(atom)
    print("story.json: state=%s headline=%r" % (story["state"], story["headline"]))
    for b in story["big_numbers"]:
        print("  %s %s  %s" % (b["value"], b["unit"], b["label"]))
    print("  %d updates, next pass %s" % (len(story["updates"]), (story["next_pass"] or {}).get("date")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
