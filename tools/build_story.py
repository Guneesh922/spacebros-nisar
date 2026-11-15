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

Findings (WP1, schema findings-v1): one file per coast pass after the baseline, data/processed/findings/<pass-date>.json, plus
findings/latest.json. A findings file = every story-v1 key + template_state, comparison_line, three_numbers, sources, confidence,
event_chip, sea, evidence_layers, age. Date files are WRITE-ONCE: rewritten only when the sha256 of their inputs changes (then
revision + 1 and a revision_log line). latest.json is rebuilt every run; data/web/story.json = latest.json content.
Optional inputs: config/areas.json (baselines per track), data/processed/events.json (events-v1; falls back to data/events/*.json).

Presentation switch (config/areas.json "presentation": {"show_data_caveats": false, "cannot_tell_position": "end"}): when show_data_caveats
is false, apply_presentation() removes every user-visible data-quality caveat from the PUBLIC story.json, feed.json and atom.xml (badges.provisional
and badges.sample false, provisional_text null, caveats [], confidence normal, confounders [] and the caveat sentences inside sub / lead / update
text). The original values are kept in story["internal"] in memory and written by main() to data/internal/story.internal.json (NOT published by pages.yml; never in data/web/story.json). Numbers are unchanged. findings/*.json keep all caveats
(no revisions); only data/web/story.json and the feeds are filtered. story["presentation"] carries the switch so dash.js can gate its own strings.

Usage: python3 tools/build_story.py [--root DIR] [--now 2026-11-14T12:00:00Z] [--out DIR] [--no-findings]
"""
import argparse
import copy
import datetime as dt
import glob
import hashlib
import json
import math
import os
import re
import sys
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
IST = dt.timedelta(hours=5, minutes=30)


BUILDER_VERSION = "findings-1"


class StoryError(Exception):
    pass


# ------------------------------------------------------------------ source paths ("<repo file>#<dotted.path>")
def walk(obj, dotted):
    """Walk a dotted path. Dict keys may themselves contain dots ('20261109|k=3.0'): the longest matching key wins. Digits index lists."""
    toks = dotted.split(".")
    i = 0
    while i < len(toks):
        if isinstance(obj, list):
            obj = obj[int(toks[i])]
            i += 1
        elif isinstance(obj, dict):
            for j in range(len(toks), i, -1):
                k = ".".join(toks[i:j])
                if k in obj:
                    obj = obj[k]
                    i = j
                    break
            else:
                raise KeyError("no key at %r in path %r" % (".".join(toks[i:]), dotted))
        else:
            raise KeyError("path %r goes into a scalar" % dotted)
    return obj


def resolve_source(src, root, rules=None, cache=None):
    """src = 'file#dotted.path' or {'derived': op, 'inputs': [paths]} -> number. Ops: difference (a-b), max_abs_diff (max |x-a|), days_between, count_flooded."""
    cache = cache if cache is not None else {}

    def load(path):
        f, _, dotted = path.partition("#")
        if f not in cache:
            cache[f] = jload(os.path.join(root, f))
        return walk(cache[f], dotted)
    if isinstance(src, str):
        return load(src)
    vals = [load(x) for x in src["inputs"]]
    op = src["derived"]
    if op == "difference":
        return vals[0] - vals[1]
    if op == "max_abs_diff":
        return max(abs(v - vals[0]) for v in vals[1:])
    if op == "days_between":
        return (dt.date.fromisoformat(vals[0][:10]) - dt.date.fromisoformat(vals[1][:10])).days
    if op == "count_flooded":
        return sum(1 for r in vals[0] if is_flooded(r, rules))
    raise KeyError("unknown derived op %r" % op)


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


def since_text(T, prev_date, date, n_prev, n_now, receded, still, worse):
    """The 'since the last pass' sentence(s): 'On 28 Oct no mandal looked probably flooded. On 9 Nov, 8 do.' Handles 0, 1 and many (singular/plural),
    so a zero start or end reads naturally. The went down / stayed / went up counts follow as one short sentence, leaving out the zero ones."""
    k = lambda n: "none" if n == 0 else ("one" if n == 1 else "many")
    a = fill(T["prev_" + k(n_prev)], prev_date=prev_date, n_prev=n_prev)
    b = fill(T["now_" + k(n_now)], date=date, n_now=n_now)
    parts = [fill(T[key], receded=receded, still=still, worse=worse) for key, n in (("tail_down", receded), ("tail_same", still), ("tail_up", worse)) if n]
    return " ".join([a, b] + ([", ".join(parts) + "."] if parts else []))


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


def headline_text(key, S, event_name, date_txt, practice, prev_date_txt=None):
    h = S["headline"]
    if key == "quiet":
        t = fill(h["quiet"], prev_date=prev_date_txt)
    elif key.startswith("recovery."):
        t = fill(h["recovery"][key.split(".")[1]], event=event_name)
    elif key == "first_pass":
        t = fill(h["first_pass"], event=event_name)
    else:
        t = h[key] if "{" not in h[key] else fill(h[key], date=date_txt)
    return (h["practice_prefix"] + t) if practice else t


# ------------------------------------------------------------------ the build
def scene_status(by_date_block, catalog_scene):
    return (by_date_block or {}).get("product_status") or (catalog_scene or {}).get("product_status")


CREDIT_NISAR = "NISAR L2 GCOV, NASA/JPL-Caltech and ISRO, via ASF DAAC (NASA Earthdata)"
DISCLAIMER = ("Built by team SpaceBros for the NASA Space Apps Challenge 2026. Not an official NASA, ISRO, IMD or government product, "
              "and not a warning service.")


def credits_block(scene=None, track=None, pol=None):
    """story.json `credits`: exact credit strings. `nisar_line` adds scene date, track, polarisation and PROVISIONAL/VALIDATED status
    when the pass is known (scene = {"date", "status"}). Other sources are credited in full where the page shows their data."""
    nisar = CREDIT_NISAR
    if scene and scene.get("date"):
        bits = ["scene %s" % scene["date"]]
        if track:
            bits.append("track %s" % track)
        if pol:
            bits.append("polarisation %s" % pol)
        if scene.get("status"):
            bits.append(str(scene["status"]).upper())
        nisar = "%s; %s" % (CREDIT_NISAR, ", ".join(bits))
    return {"nisar": CREDIT_NISAR, "nisar_line": nisar, "derived": "Maps and numbers: SpaceBros, derived from NISAR data",
            "imd": "IMD / RSMC New Delhi bulletins", "ndma_sachet": "NDMA SACHET", "gdacs": "GDACS (EC JRC and UN OCHA)",
            "boundaries": "geoBoundaries (ODbL 1.0, boundary year 2018); district names from the 2022 AP district lists",
            "basemap": "Map data: Esri, HERE, Garmin, OpenStreetMap contributors", "disclaimer": DISCLAIMER}


def build(inp, now):
    """Pure function: inputs dict -> story dict. ``now`` = aware datetime (UTC)."""
    rules, S, seasons = inp["rules"], inp["strings"], inp.get("seasons") or {}
    catalog = (inp.get("catalog") or {}).get("scenes", [])
    rank, profile, cstats = inp.get("rank"), inp.get("profile"), inp.get("class_stats")
    by_date = (rank or {}).get("by_date") or {}
    dates = sorted(by_date)
    override = inp.get("_override")                  # "numbers_coming" | "no_baseline" (findings wrapper); None = normal
    coast_dates = sorted({s_["date"] for s_ in catalog if s_.get("role") == "COAST"})
    pass_date = inp.get("_pass_date") or (dates[-1] if dates else (coast_dates[-1] if coast_dates else None))
    event = pick_event(inp.get("events") or [], now, rules, pass_date)
    story = {"schema": "story-v1", "built_utc": iso_utc(now), "built_text": ist_text(now) + " IST", "event_id": event["id"] if event else None,
             "official_banner": S["official_banner"], "official_links": (event or {}).get("official_links") or [],
             "credits": credits_block()}
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
    sample = (not rank) or (not rank.get("provenance")) or bool(rank.get("placeholder"))
    nobl = not dates or bool(override)
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
        step = rules["next_pass_basis_days"]
        first = dt.date.fromisoformat(main_next["date"])           # last pass + 12 days
        nd = first
        while nd < now.date():                                     # roll forward: last pass + n x 12 days >= today (no stale past date)
            nd += dt.timedelta(days=step)
        overdue = first < now.date()
        if overdue:
            text = fill(S["next_pass_overdue"], expected=dmon(first.isoformat()), next_date=dmon(nd.isoformat()))
        else:
            text = fill(S["next_pass"], next_date=dmon(nd.isoformat()))
        main_next = dict(main_next, date=nd.isoformat(), expected_utc=iso_utc(parse_utc(main_next["expected_utc"]) + (nd - first)), first_expected=first.isoformat(),
                         days_until=(nd - now.date()).days, overdue=overdue,
                         basis="last pass of the same track + n x %d days (NISAR repeat), first date on or after today" % step, text=text)
    story["next_pass"] = main_next
    story["next_passes"] = nxt
    # --- no numbers at all
    if nobl:
        pd = pass_date or (newest["date"] if newest else None)
        if override == "no_baseline":
            head, sub, hkey = S["headline"]["no_baseline"], fill(S["lead"]["no_baseline"], date=dmon(pd)), "no_baseline"
        elif pd and (override == "numbers_coming" or coast_dates):
            head, hkey = fill(S["numbers_coming"], date=dmon(pd)), "numbers_coming"
            sub = fill(S["lead"]["numbers_coming_event" if event else "watch"], date=dmon(pd if event else (newest["date"] if newest else pd)))   # sub text must fit the state
        else:
            head, sub, hkey = S["missing_numbers"], (fill(S["lead"]["watch"], date=dmon(newest["date"])) if newest else ""), "missing_numbers"
        landfall0 = event_landfall(event) if event else None
        old = [d for d in dates if not pd or d < pd]
        cards0 = {}
        for i, d in enumerate(old):
            cards0[d] = card_for(d, by_date, old[i - 1] if i else None, event, landfall0, rules, S, sample, inp, profile, cls_info_for(cstats, d, S, rules), now)
        ups0 = [cards0[d]["update"] for d in old] + (sea_updates(catalog, event, landfall0, profile, S, rules, old) if landfall0 else [])
        ups0.sort(key=lambda u: (u["date"], u["kind"]), reverse=True)
        story.update(state="watch" if not event else "event", base_state="watch" if not event else "event", numbers_ready=False,
                     headline=head, sub=sub, big_numbers=[], map_layer_id="nisar_class_new_water", mandal_sentences={}, mandals={}, updates=ups0,
                     since_last=None, confounders=[], badges={"provisional": False, "sample": bool(sample)}, headline_key=hkey)
        story["feed"] = {"json": "feed.json", "atom": "atom.xml"}
        return story
    # --- event geometry
    landfall = event_landfall(event) if event else None
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
        story_headline = fill(S["headline"]["no_new_pass"], days=int(stale_days))
        key = "no_new_pass"
        sub_parts.insert(0, fill(S["stale_sub"], date=dmon(data_as_of.strftime("%Y-%m-%d"))))
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
    story["credits"] = credits_block(story["scene"], (cur.get("track") if isinstance(cur, dict) else None) or ((story.get("next_pass") or {}).get("track")), "HH")
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


def event_landfall(e):
    return (e.get("dates") or {}).get("landfall_day") or (e.get("landfall") or {}).get("date")


def event_window(e, rules):
    """(start, end, aftermath_days) as ISO strings / int. Missing start/end fall back to the landfall day (tests, old event files)."""
    lf = event_landfall(e)
    start = e.get("start") or (e.get("dates") or {}).get("start") or lf
    end = e.get("end") or (e.get("dates") or {}).get("end") or (e.get("dates") or {}).get("closed") or start
    after = e.get("aftermath_days")
    if after is None:
        after = rules.get("default_aftermath_days", 30)
    return start, end, int(after)


def event_publishable(e, rules):
    return e.get("status") in rules.get("event_publishable_status", ["active"]) and e.get("reviewed_by_human") is not False


def chip_relation(e, iso, rules):
    """'during' if iso in [start, end], 'after' if in (end, end + aftermath_days], else None. Window comes from the event, never guessed."""
    start, end, after = event_window(e, rules)
    if not start or not end or not iso:
        return None
    d = dt.date.fromisoformat(iso[:10])
    s_, e_ = dt.date.fromisoformat(start[:10]), dt.date.fromisoformat(end[:10])
    if s_ <= d <= e_:
        return "during"
    if e_ < d <= e_ + dt.timedelta(days=after):
        return "after"
    return None


def display_name(name):
    """GDACS draft names -> plain names: 'Tropical Cyclone MURASU-26' -> 'Cyclone Murasu'. Anything else is kept."""
    m = re.match(r"^Tropical Cyclone ([A-Za-z]+)-\d+$", (name or "").strip())
    return "Cyclone %s" % m.group(1).title() if m else (name or "the storm")


def severity_rank(e):
    """Higher = more severe, from the words the source used (IMD class or GDACS colour). Unknown = 0."""
    t = str((e.get("severity") or {}).get("as_given") or "").lower()
    for rank, words in ((4, ("extremely", "super", "red")), (3, ("very severe", "orange")), (2, ("severe", "yellow")), (1, ("green", "depression", "deep", "cyclonic storm"))):
        if any(w in t for w in words):
            return rank
    return 0


def draft_linked_here(e, iso):
    """True when events.json links a radar pass of this date to the event (written by tools/pipeline/events.py)."""
    return any(str(lp.get("date"))[:10] == str(iso)[:10] for lp in e.get("linked_passes") or [])


def chips_for(events, iso, area_id, S, rules):
    """Every event whose window holds the pass date, reviewed first, then most severe, then newest start. Drafts (auto events nobody has
    reviewed) are included, with chip text that says so. Dismissed / needs_review events never get a chip."""
    out = []
    for e in events or []:
        if e.get("status") in ("dismissed", "needs_review"):
            continue
        if e.get("area_id") and area_id and e["area_id"] != area_id:
            continue
        reviewed = e.get("reviewed_by_human") is not False
        if reviewed and not event_publishable(e, rules):
            continue
        rel = chip_relation(e, iso, rules)
        if not rel:
            continue
        if not reviewed and not draft_linked_here(e, iso):
            continue        # an alert nobody reviewed and radar was never linked to for this pass (e.g. a flood alert far from the box): no chip
        text = fill(S["chip"][rel], event=e.get("name")) if reviewed else fill(S["chip_draft"][rel], event=display_name(e.get("name")))
        start = dt.date.fromisoformat((event_window(e, rules)[0] or "1970-01-01")[:10]).toordinal()
        out.append(((not reviewed, -severity_rank(e), -start), {"event_id": e["id"], "relation": rel, "text": text, "reviewed": reviewed}))
    out.sort(key=lambda x: x[0])
    return [c for _, c in out]


def pick_event(events, now, rules, pass_date=None):
    """Publishable event whose window (start .. end + aftermath_days) holds the pass date; latest landfall if several.
    Without a pass date: the newest publishable event (old behaviour)."""
    act = [e for e in events if event_publishable(e, rules)]
    if pass_date is not None:
        act = [e for e in act if chip_relation(e, pass_date, rules)]
    if not act:
        return None
    return sorted(act, key=lambda e: event_landfall(e) or "0000-00-00")[-1]


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
    """Confounder sentences for a scene date. events.json ``story.murasu_caveat`` (human text) replaces the generic text of a 'murasu' confounder."""
    out = []
    story = (event or {}).get("story") or {}
    for c in (event or {}).get("confounders") or []:
        if iso in (c.get("affects_dates") or []):
            text = c.get("text") or c.get("name")
            if "murasu" in str(c.get("id", "")).lower() and story.get("murasu_caveat"):
                text = story["murasu_caveat"]
            out.append(text)
    return out


def is_quiet(rows, prev_rows, cmp_, cls_info, rules):
    """quiet = no mandal crosses the flooded rule AND none went up/down since the previous pass AND new-water share <= max_times_control x control."""
    q = rules.get("quiet")
    if not q or cls_info is None or cmp_["flooded_now"] > 0:
        return False
    if prev_rows is not None:
        prev_by = {r["mandal"]: r for r in prev_rows}
        for r in rows:
            p = prev_by.get(r["mandal"])
            if p and not r.get("flag") and not p.get("flag") and trend(r, p, rules) != "flat":
                return False
    return cls_info["new_water_pct_of_land"] <= q["max_times_control"] * cls_info["normal_new_water_pct_of_land"]


def radar_change_seen(mandals):
    """True if at least one mandal meets the flooded rule or went up vs the previous pass (story_rules.json radar_finding)."""
    return any(m.get("flooded") or m.get("trend") == "up" for m in (mandals or {}).values())


def row_index(rows, row):
    for i, r in enumerate(rows):
        if r is row:
            return i
    return None


def card_for(d, by_date, prev_d, event, landfall, rules, S, sample, inp, profile, cls_info, now):
    blk = by_date[d]
    rows = blk["rows"]
    prev_rows = by_date[prev_d]["rows"] if prev_d else None
    cmp_ = compare(rows, prev_rows, rules)
    key = headline_key(cmp_, rules, prev_d is not None)
    event_name = (event or {}).get("name") or "the storm"
    days_after = (dt.date.fromisoformat(d) - dt.date.fromisoformat(landfall)).days if landfall else None
    bl = ((inp.get("class_stats") or {}).get("baseline_dates") or [None])[-1]
    baseline_last = ("%s-%s-%s" % (bl[:4], bl[4:6], bl[6:])) if bl else None
    prev_ref = prev_d or baseline_last
    quiet = bool(prev_ref) and is_quiet(rows, prev_rows, cmp_, cls_info, rules)
    if quiet:
        key = "quiet"
    headline = headline_text(key, S, event_name, dmon(d), sample, dmon(prev_ref) if prev_ref else None)
    conf = confounders_for(event, d)
    if quiet:
        lead = fill(S["lead"]["quiet"], date=dmon(d))
    elif key == "no_flood" and not (days_after is not None and days_after > 0 and prev_d):
        # no mandal passes the flood rule: the lead must not say places were "probably under water" (it would contradict the headline)
        lead = fill(S["lead"]["no_flood_landfall_day"], date=dmon(d), event=event_name) if days_after == 0 else fill(S["lead"]["no_flood"], date=dmon(d))
    elif days_after == 0:
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
        since["text"] = since_text(S["since_last"], dmon(prev_d), dmon(d), cmp_["flooded_prev"], cmp_["flooded_now"], cmp_["receded"], cmp_["still"], cmp_["worse"])
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
    rows_path = "data/processed/mandal_rank.json#by_date.%s.rows" % d
    card = {"rows_path": rows_path, "top_idx": row_index(rows, top) if top else None, "prev_rows_path": ("data/processed/mandal_rank.json#by_date.%s.rows" % prev_d) if prev_d else None,
            "prev_top_idx": (row_index(prev_rows, prev_by[top["mandal"]]) if (top and prev_rows is not None and top["mandal"] in prev_by) else None),
            "pass_date_src": "data/processed/mandal_rank.json#by_date.%s.date" % d, "landfall_src": (event or {}).get("_landfall_src"), "quiet": quiet,
            "headline": headline, "headline_key": key, "lead": lead, "since_last": since, "confounders": conf, "top": top, "prev_top": prev_by.get(top["mandal"]) if top else None,
            "flooded_now": cmp_["flooded_now"], "top_flooded": bool(top and is_flooded(top, rules)), "status": cur_status, "scene_id": blk.get("scene_id"), "start_utc": blk.get("start_utc"),
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
        b = S["bignums"]["top_mandal"] if card.get("top_flooded") else S["bignums"]["top_mandal_calm"]   # "under water" only if the flooded rule holds
        base = "%s.%d" % (card["rows_path"], card["top_idx"])
        out.append({"id": "top_mandal", "value": fill(b["value"], lik=num(top["water_pct"])), "unit": b["unit"],
                    "label": fill(b["label"], top_mandal=top["mandal"], err=err_text(top.get("err"))),
                    "mandal": top["mandal"], "raw": top["water_pct"], "err": top.get("err"), "source_file": "data/processed/mandal_rank.json",
                    "fmt": "num", "source": base + ".water_pct", "err_source": base + ".err", "err_fmt": "err_text"})
    prev_top = card["prev_top"]
    if top and card["has_prev"] and prev_top:
        b = S["bignums"]["change"]
        out.append({"id": "change", "value": fill(b["value"], change_pts=signed(top["water_pct"] - prev_top["water_pct"])), "unit": b["unit"],
                    "label": fill(b["label"], top_mandal=top["mandal"]), "raw": round(top["water_pct"] - prev_top["water_pct"], 2),
                    "source_file": "data/processed/mandal_rank.json", "fmt": "signed",
                    "source": {"derived": "difference", "inputs": ["%s.%d.water_pct" % (card["rows_path"], card["top_idx"]), "%s.%d.water_pct" % (card["prev_rows_path"], card["prev_top_idx"])]}})
    else:
        b = S["bignums"]["flooded_count"]
        out.append({"id": "flooded_count", "value": fill(b["value"], n_now=card["flooded_now"]), "unit": b["unit"], "label": b["label"], "raw": card["flooded_now"],
                    "source_file": "data/processed/mandal_rank.json", "fmt": "int", "source": {"derived": "count_flooded", "inputs": [card["rows_path"]]}})
    if days_after is not None and days_after >= 0:
        b = S["bignums"]["days_after"]
        out.append({"id": "days_after", "value": fill(b["value"], days_after=days_after), "unit": b["unit"], "label": b["label"], "raw": days_after,
                    "source_file": "data/events/ (landfall_day) and data/h5/catalog.json", "fmt": "int"}
                   | ({"source": {"derived": "days_between", "inputs": [card["pass_date_src"], card["landfall_src"]]}} if card.get("landfall_src") else {}))
    return out


def big_numbers(cur, state, nxt, newest, now, S, days_after):
    nums = card_numbers(cur, S, days_after)
    if state == "watch":
        b = S["bignums"]["flooded_count"]
        w = [{"id": "flooded_count", "value": fill(b["value"], n_now=cur["flooded_now"]), "unit": b["unit"], "label": b["label"], "raw": cur["flooded_now"],
              "source_file": "data/processed/mandal_rank.json", "fmt": "int", "source": {"derived": "count_flooded", "inputs": [cur["rows_path"]]}}]
        if nxt:
            b = S["bignums"]["days_to_next"]
            w.append({"id": "days_to_next", "value": fill(b["value"], days=max(0, nxt["days_until"])), "unit": b["unit"], "label": b["label"], "raw": nxt["days_until"],
                      "source_file": "data/h5/catalog.json", "fmt": "int", "source": "runtime: last pass date + 12 days - build date"})
        if newest:
            b = S["bignums"]["days_since_pass"]
            d = (now.date() - dt.date.fromisoformat(newest["date"])).days
            w.append({"id": "days_since_pass", "value": fill(b["value"], days=d), "unit": b["unit"], "label": b["label"], "raw": d, "source_file": "data/h5/catalog.json", "fmt": "int", "source": "runtime: build date - last pass date"})
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
            if k in ("official_banner", "official_links", "provisional_text", "sources", "shown_numbers", "revision_log", "inputs_detail", "evidence_layers", "pass",
                     "alerts_ref", "credits", "area_id", "inputs_sha256", "internal", "presentation", "source", "err_source", "fmt", "err_fmt", "crop_stage"):
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
            if len(sent.split()) > maxw:          # every filled prose string, not only known paths (skip list above removes ids, dates, names)
                errs.append("sentence over %d words in %s: %r" % (maxw, path, sent[:100]))
    if errs:
        raise StoryError("story guard failed:\n  " + "\n  ".join(errs))


# ------------------------------------------------------------------ presentation switch
PRESENTATION_DEFAULT = {"show_data_caveats": False, "cannot_tell_position": "end"}
CANNOT_TELL_POSITIONS = ("end", "inline")
_KEEP_KEYS = ("internal", "presentation", "official_banner", "official_links", "credits", "inputs_detail", "inputs_sha256", "revision_log", "sources", "shown_numbers")


def presentation_cfg(areas):
    """config/areas.json "presentation" merged over the defaults (caveats hidden, cannot-tell block at the end)."""
    cfg = dict(PRESENTATION_DEFAULT)
    cfg.update((areas or {}).get("presentation") or {})
    if not isinstance(cfg["show_data_caveats"], bool):
        raise StoryError("presentation.show_data_caveats must be true or false, got %r" % (cfg["show_data_caveats"],))
    if cfg["cannot_tell_position"] not in CANNOT_TELL_POSITIONS:
        raise StoryError("presentation.cannot_tell_position must be one of %s, got %r" % (CANNOT_TELL_POSITIONS, cfg["cannot_tell_position"]))
    return cfg


def caveat_phrases(story, S):
    """Caveat sentences that are woven into public prose (longest first): provisional line, season line, 'numbers likely to change' line,
    the practice-numbers prefix and every confounder note ('Other causes') of the story and of its updates."""
    ph = [S.get("provisional"), (S.get("caveat") or {}).get("season"), (S.get("headline") or {}).get("practice_prefix")]
    for tpl in ((S.get("lead") or {}).get("recovery") or "",):
        ph += [x for x in re.split(r"(?<=[.!?])\s+", tpl) if "likely to change" in x.lower()]
    ph += list(story.get("confounders") or [])
    ph += list(story.get("caveats") or [])
    for u in story.get("updates") or []:
        ph += list(u.get("confounders") or [])
    return sorted({p for p in ph if p and "{" not in p}, key=len, reverse=True)


def _strip_text(o, phrases):
    if isinstance(o, str):
        if not any(p in o for p in phrases):
            return o
        for p in phrases:
            o = o.replace(p, "")
        return re.sub(r"\s{2,}", " ", o).strip()
    if isinstance(o, dict):
        return {k: (v if k in _KEEP_KEYS else _strip_text(v, phrases)) for k, v in o.items()}
    if isinstance(o, list):
        return [_strip_text(v, phrases) for v in o]
    return o


def split_internal(story):
    """(public, internal): the public story WITHOUT the `internal` key, and that key's content (the original caveat text). main() writes the first to
    data/web/story.json and the second to data/internal/story.internal.json, which pages.yml does not publish."""
    public = {k: v for k, v in story.items() if k != "internal"}
    return public, story.get("internal")


def apply_presentation(story, cfg, S):
    """Public copy of a story (or findings) dict. Always adds story["presentation"]. With show_data_caveats false the caveat fields are emptied and
    their originals are kept in story["internal"]; numbers are never touched. With true the story is returned unchanged apart from the two new keys."""
    out = copy.deepcopy(story)
    out["presentation"] = {"show_data_caveats": bool(cfg["show_data_caveats"]), "cannot_tell_position": cfg["cannot_tell_position"]}
    internal = {"badges": copy.deepcopy(story.get("badges")), "provisional_text": story.get("provisional_text"), "caveats": copy.deepcopy(story.get("caveats")),
                "confidence": copy.deepcopy(story.get("confidence")), "confounders": copy.deepcopy(story.get("confounders")),
                "sub": story.get("sub"), "lead": story.get("lead"),
                "updates": {u["id"]: {"text": u.get("text"), "headline": u.get("headline"), "confounders": copy.deepcopy(u.get("confounders"))} for u in story.get("updates") or []}}
    out["internal"] = internal
    if cfg["show_data_caveats"]:
        return out
    phrases = caveat_phrases(story, S)
    out = _strip_text(out, phrases)
    out["badges"] = dict(story.get("badges") or {}, provisional=False, sample=False)
    out["provisional_text"] = None
    out["caveats"] = []
    out["confidence"] = {"level": "normal", "reasons": []}
    out["confounders"] = []
    for u in out.get("updates") or []:
        u["confounders"] = []
    return out


# ------------------------------------------------------------------ feeds
def feeds(story, strings, rules, event, site_title=None, show_data_caveats=True):
    site = rules.get("site_url", "").rstrip("/") + "/"
    title = fill(strings["feed"]["title"], event=(event or {}).get("name") or "NISAR coast")
    if site_title:
        title = "%s: %s" % (site_title, title)
    items = []
    for u in story.get("updates", []):
        stat = (u.get("status") or "").lower() or "unknown"
        when = u.get("cataloged_utc") or u.get("start_utc") or story["built_utc"]
        items.append({"id": "spacebros-nisar:%s:%s:%s" % ((event or {}).get("id") or "none", u["kind"], u["id"]), "url": site + u["permalink"],
                      "title": fill(strings["feed"]["item"], headline=u["headline"], status=stat) if show_data_caveats else u["headline"],   # status = validated / provisional
                      "content_text": u["text"], "summary": u["headline"], "date_published": when,
                      "tags": [u["kind"], stat] if show_data_caveats else [u["kind"]]})
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


# ------------------------------------------------------------------ findings (findings-v1)
FMT = {"num": num, "int": lambda v: str(int(round(float(v)))), "err_text": err_text, "signed": signed}


def season_entry(seasons, name):
    for x in (seasons or {}).get("seasons", []):
        if name == x["id"] or name in (x.get("aliases") or []):
            return x
    return None


def season_for_date(seasons, iso):
    m = int(iso[5:7])
    return next((x for x in (seasons or {}).get("seasons", []) if m in x["months"]), None)


def season_relation(seasons, a, b):
    """'same' | 'adjacent' (next or previous season in the cyclic order of seasons.json) | 'other' | 'unknown'"""
    if not a or not b:
        return "unknown"
    if a["id"] == b["id"]:
        return "same"
    ids = [x["id"] for x in seasons["seasons"]]
    n = len(ids)
    d = (ids.index(a["id"]) - ids.index(b["id"])) % n
    return "adjacent" if d in (1, n - 1) else "other"


def crop_stage_for(seasons, iso):
    m = int(iso[5:7])
    return next((x["id"] for x in ((seasons or {}).get("crop_stages") or {}).get("stages", []) if m in x["months"]), None)


def area_config(inp):
    cfg = inp.get("areas")
    if not cfg:
        return None, None
    aid = cfg.get("default_area")
    return next((a for a in cfg.get("areas", []) if a.get("id") == aid), (cfg.get("areas") or [None])[0]), cfg


def baseline_for(inp, track):
    """{'season','dates'} for a coast track. config/areas.json is the only source; without the file, the rules' default (track 55, post-monsoon 4 + 16 Oct).
    A baseline is NEVER reused for another track."""
    area, cfg = area_config(inp)
    if area is not None:
        b = ((area.get("baselines") or {}).get("COAST") or {}).get(str(track))
        return dict(b) if b else None
    d = inp["rules"].get("default_baseline")
    return dict(d) if d and d.get("track") == track else None


def baseline_dates_all(inp):
    area, cfg = area_config(inp)
    out = set()
    if area is not None:
        for b in ((area.get("baselines") or {}).get("COAST") or {}).values():
            out.update(b.get("dates") or [])
    else:
        out.update((inp["rules"].get("default_baseline") or {}).get("dates") or [])
    return out


def coast_passes(inp):
    """Coast scenes after the baseline(s), oldest first (the baseline scenes themselves have no findings)."""
    bl = baseline_dates_all(inp)
    cat = (inp.get("catalog") or {}).get("scenes", [])
    last_bl = max(bl) if bl else ""
    return sorted([s for s in cat if s.get("role") == "COAST" and s["date"] not in bl and s["date"] > last_bl], key=lambda s: (s["start_utc"], s["scene_id"]))


def norm_event(e, rules, iso=None):
    """The parts of an event that decide a finding (hashed). Lists of linked passes, edit logs and alert refs are left out on purpose:
    the pipeline writes those back, which would change the hash of the file that caused the write."""
    st, en, af = event_window(e, rules)
    status = e.get("status")
    if e.get("reviewed_by_human") is False and status != "dismissed":
        status = "draft"
    out = {"id": e.get("id"), "name": e.get("name"), "status": status, "reviewed_by_human": e.get("reviewed_by_human"), "start": st, "end": en, "aftermath_days": af,
           "landfall": event_landfall(e), "confounders": e.get("confounders"), "story": e.get("story"), "official_links": e.get("official_links"), "monitor_days": e.get("monitor_days")}
    if iso and e.get("reviewed_by_human") is False:
        out["linked_to_this_pass"] = draft_linked_here(e, iso)       # decides whether a draft gets a chip on this pass
    return out


def sha(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def input_groups(inp, d, sc):
    rank, cs = inp.get("rank") or {}, inp.get("class_stats") or {}
    by = {k: v for k, v in (rank.get("by_date") or {}).items() if k <= d}
    key = lambda k: k.split("|")[0]
    classes = {k: v for k, v in (cs.get("classes") or {}).items() if key(k) == "normal" or ("%s-%s-%s" % (key(k)[:4], key(k)[4:6], key(k)[6:])) <= d}
    scenes = {k: v for k, v in (cs.get("scenes") or {}).items() if k <= d}
    cat = [x for x in (inp.get("catalog") or {}).get("scenes", []) if x["date"] <= d]
    area, _ = area_config(inp)
    return {"by_date": by, "class_stats": {"classes": classes, "scenes": scenes, "baseline_dates": cs.get("baseline_dates"), "thresholds": cs.get("thresholds")},
            "catalog": cat, "events": [norm_event(e, inp["rules"], d) for e in (inp.get("events") or []) if chip_relation(e, d, inp["rules"])],   # only events whose window holds this pass: a new alert elsewhere must not revise an old finding
            "templates": inp["strings"], "rules": inp["rules"], "seasons": inp.get("seasons"),
            "baseline": {"area": (area or {}).get("baselines"), "track": sc["track"]}, "builder": BUILDER_VERSION}


def pass_scene_status(inp, d, track):
    for x in (inp.get("catalog") or {}).get("scenes", []):
        if x["date"] == d and x["role"] == "COAST" and x["track"] == track:
            return x.get("product_status")
    return None


def finding(inp, sc, now, archive):
    """One findings-v1 dict for coast pass ``sc``. archive=True: frozen as of the pass itself (no dependence on the clock) = the write-once date file.
    archive=False: the same finding with the live clock (age, next pass, no_new_pass) = latest.json."""
    rules, S, seasons = inp["rules"], inp["strings"], inp.get("seasons") or {}
    d, track = sc["date"], sc["track"]
    cat_all = (inp.get("catalog") or {}).get("scenes", [])
    rank = inp.get("rank")
    cs = inp.get("class_stats")
    as_of = parse_utc(sc["start_utc"])
    bnow = as_of if archive else now
    view = dict(inp)
    view["_pass_date"] = d
    if archive:
        view["catalog"] = {"scenes": [x for x in cat_all if x["date"] <= d]}
    if rank and rank.get("by_date"):
        r2 = dict(rank)
        r2["by_date"] = {k: v for k, v in rank["by_date"].items() if k <= d}
        view["rank"] = r2
    # --- baseline, season, confidence
    bl = baseline_for(inp, track)
    pass_season = season_for_date(seasons, d)
    bl_season = season_entry(seasons, bl["season"]) if bl else None
    rel = season_relation(seasons, pass_season, bl_season) if bl else None
    have_numbers = bool(rank and d in (rank.get("by_date") or {}) and cs and class_summary(cs, d, S, rules))
    ts = "big_change"
    if not bl or rel == "other":
        ts = "no_baseline"
    elif not have_numbers:
        ts = "numbers_coming"
    view["_override"] = ts if ts in ("no_baseline", "numbers_coming") else None
    story = build(view, bnow)
    story["schema"] = "findings-v1"
    sstat = sc.get("product_status")
    reasons, caveats = [], []
    if ts == "no_baseline":
        reasons.append(S["confidence"]["no_baseline"])
    else:
        bl_status = [x.get("product_status") for x in cat_all if x["role"] == "COAST" and x["track"] == track and x["date"] in (bl or {}).get("dates", [])]
        if any(x == "PROVISIONAL" for x in bl_status):
            reasons.append(S["confidence"]["provisional_baseline"])
        if sstat == "PROVISIONAL":
            reasons.append(S["confidence"]["provisional_pass"])
        if rel == "adjacent":
            reasons.append(fill(S["confidence"]["season"], baseline_season=bl_season["label"], season=pass_season["label"]))
            caveats.append(S["caveat"]["season"])
        elif rel == "unknown":
            reasons.append(S["confidence"]["season_unknown"])
            caveats.append(S["caveat"]["season"])
    if story.get("provisional_text"):
        caveats.insert(0, story["provisional_text"])
    story["confidence"] = {"level": "lower" if reasons else "normal", "reasons": reasons}
    story["caveats"] = caveats + [c for c in story.get("confounders") or []]
    if rel in ("adjacent", "unknown") and ts == "big_change":
        story["sub"] = story["sub"] + " " + S["caveat"]["season"]
    story["crop_stage"] = crop_stage_for(seasons, d)
    # --- numbers
    shown, three, cmp_line = [], [], None
    cur_info = class_summary(cs, d, S, rules) if (cs and ts == "big_change") else None
    if cur_info:
        key = d.replace("-", "")
        base = "data/web/class_stats.json#classes.%s|k=3.0" % key
        lo = base.replace("k=3.0", "k=4.0") if (cs["classes"].get("%s|k=4.0" % key)) else base
        hi = base.replace("k=3.0", "k=2.0") if (cs["classes"].get("%s|k=2.0" % key)) else base
        nbase = "data/web/class_stats.json#classes.normal|k=3.0"
        mid = cs["classes"]["%s|k=3.0" % key]
        err_raw = max(abs(cur_info["range_km2"][0] - mid["new_water_km2"]), abs(cur_info["range_km2"][1] - mid["new_water_km2"]))
        err_src = {"derived": "max_abs_diff", "inputs": [base + ".new_water_km2", lo + ".new_water_km2", hi + ".new_water_km2"]}
        nrm = cs["classes"]["normal|k=3.0"]

        def reg(k, text, raw, fmt, src):
            shown.append({"key": k, "text": str(text), "raw": raw, "fmt": fmt, "source": src})
        three.append({"id": "new_water_km2", "value": int(round(mid["new_water_km2"])), "err": int(err_text(err_raw)), "unit": S["three"]["new_water"]["unit"],
                      "label": fill(S["three"]["new_water"]["label"], err=err_text(err_raw)), "raw": mid["new_water_km2"], "fmt": "int", "source": base + ".new_water_km2"})
        reg("three_numbers[0].value", three[0]["value"], mid["new_water_km2"], "int", base + ".new_water_km2")
        reg("three_numbers[0].err", three[0]["err"], err_raw, "err_text", err_src)
        n_flooded = sum(1 for r in rank["by_date"][d]["rows"] if is_flooded(r, rules))
        three.append({"id": "flooded_mandals", "value": n_flooded, "unit": S["three"]["flooded"]["unit"], "label": S["three"]["flooded"]["label"], "raw": n_flooded, "fmt": "int",
                      "source": {"derived": "count_flooded", "inputs": ["data/processed/mandal_rank.json#by_date.%s.rows" % d]}})
        reg("three_numbers[1].value", n_flooded, n_flooded, "int", three[1]["source"])
        nv = num(nrm["new_water_km2"])
        three.append({"id": "normal_new_water_km2", "value": float(nv) if "." in nv else int(nv), "unit": S["three"]["normal"]["unit"],
                      "label": S["three"]["normal"]["label"], "raw": nrm["new_water_km2"], "fmt": "num", "source": nbase + ".new_water_km2"})
        reg("three_numbers[2].value", num(nrm["new_water_km2"]), nrm["new_water_km2"], "num", nbase + ".new_water_km2")
        # comparison line: vs previous pass on the same track (needs numbers) and vs a normal fortnight
        ds = sorted(k for k in rank["by_date"] if k <= d)
        prev_d = ds[ds.index(d) - 1] if ds.index(d) > 0 else None
        prev_info = class_summary(cs, prev_d, S, rules) if prev_d else None
        cm = S["comparison"]
        kw = dict(km2=int(round(mid["new_water_km2"])), err=err_text(err_raw))
        if prev_info:
            pk = prev_d.replace("-", "")
            delta = mid["new_water_km2"] - prev_info["new_water_km2"]
            variant = "prev_up" if delta > err_raw else "prev_down" if delta < -err_raw else "prev_same"
            first = fill(cm["first"], **kw) + " " + fill(cm[variant], prev_km2=num(prev_info["new_water_km2"]), prev_date=dmon(prev_d))
            reg("comparison_line.prev_km2", num(prev_info["new_water_km2"]), prev_info["new_water_km2"], "num", "data/web/class_stats.json#classes.%s|k=3.0.new_water_km2" % pk)
        else:
            first = fill(cm["first"], **kw)
        reg("comparison_line.km2", kw["km2"], mid["new_water_km2"], "int", base + ".new_water_km2")
        reg("comparison_line.err", kw["err"], err_raw, "err_text", err_src)
        cmp_line = first + " " + fill(cm["normal"], times=cur_info["times_normal"], normal_km2=num(nrm["new_water_km2"]))
        reg("comparison_line.normal_km2", num(nrm["new_water_km2"]), nrm["new_water_km2"], "num", nbase + ".new_water_km2")
    for i, b in enumerate(story.get("big_numbers") or []):
        if b.get("source") is not None and "raw" in b:
            shown.append({"key": "big_numbers[%d].value" % i, "text": b["value"], "raw": b["raw"], "fmt": b.get("fmt", "num"), "source": b["source"]})
        if b.get("err_source"):
            shown.append({"key": "big_numbers[%d].err" % i, "text": err_text(b.get("err")), "raw": b.get("err"), "fmt": b["err_fmt"], "source": b["err_source"]})
    story["comparison_line"] = cmp_line
    story["three_numbers"] = three
    story["shown_numbers"] = shown
    story["sources"] = {x["key"]: x["source"] for x in shown}
    # --- template state
    if ts == "big_change" and story.get("headline_key") == "quiet":
        ts = "quiet"
    rf = {"big_change": "change_seen", "quiet": "no_clear_change", "numbers_coming": "numbers_coming"}.get(ts)
    if rf == "change_seen" and not radar_change_seen(story.get("mandals")):
        rf = "no_clear_change"       # same basis as the public headline: no mandal flooded and none went up (story_rules radar_finding)
    stale_days = (now - parse_utc(story["data_as_of"])).total_seconds() / 86400.0 if (story.get("data_as_of") and not archive) else None
    if not archive and ts in ("big_change", "quiet") and stale_days is not None and stale_days > rules["stale_after_days"]:
        ts = "no_new_pass"
        story["stale"] = True
        if story["state"] != "stale":
            story["headline"] = fill(S["headline"]["no_new_pass"], days=int(stale_days))
            story["sub"] = fill(S["stale_sub"], date=dmon(story["data_as_of"][:10])) + " " + story["sub"]
        story["headline_key"] = "no_new_pass"
    story["template_state"] = ts
    story["radar_finding"] = rf
    # --- pass, event chip, sea, layers, age
    story["area_id"] = (area_config(inp)[0] or {}).get("id", "godavari")
    story["pass"] = {"date": d, "time_utc": sc["start_utc"], "time_ist_text": ist_text(as_of) + " IST", "role": "COAST", "track": track, "scene_id": sc["scene_id"], "product_status": sstat}
    story["credits"] = credits_block({"date": d, "status": sstat}, track, "HH")
    chips = chips_for(inp.get("events"), d, story["area_id"], S, rules)
    story["event_chips"] = chips                     # all events whose window holds this pass: reviewed first, then most severe
    story["event_chip"] = chips[0] if chips else None   # the reviewed / most severe one (same keys as before + "reviewed")
    story["sea"] = {"finding": None, "text": S["sea"]["none"]}
    lid = "nisar_l_coast_%s_t%d_hh" % (d.replace("-", ""), track)
    layers = [{"layer_id": lid, "png": "data/web/%s.png" % lid, "h5": sc.get("file")}]
    if have_numbers and ts != "no_baseline":
        layers.append({"layer_id": "nisar_class_new_water", "png": "data/web/class_%s_new_water.png" % d.replace("-", ""), "h5": ((cs or {}).get("h5_sources") or {}).get(d.replace("-", ""))})
    story["evidence_layers"] = layers
    if archive:
        story["age"] = None
        story["archive"] = True
        story["as_of_utc"] = iso_utc(as_of)
    else:
        days = (now.date() - dt.date.fromisoformat(d)).days
        story["age"] = {"days_since_pass": days, "text": S["age"]["today"] if days <= 0 else S["age"]["one"] if days == 1 else fill(S["age"]["days"], days=days)}
        story["archive"] = False
    story["alerts_ref"] = "data/processed/alerts.json"
    story["revision"], story["revision_log"] = 1, []
    groups = input_groups(inp, d, sc)
    story["inputs_detail"] = {k: sha(v) for k, v in groups.items()}
    story["inputs_sha256"] = sha(story["inputs_detail"])
    return story


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, ensure_ascii=False)
        fh.write("\n")


REASONS = {"events": "event record wording changed (landfall caption, names or edit log)", "templates": "English templates changed (since-last sentence)",
           "rank": "mandal numbers changed", "class_stats": "new-water numbers changed", "catalog": "scene catalogue changed", "profile": "eye profile changed"}


def revision_reason(changed):
    """Why a write-once findings file got a new revision, in words: 'inputs changed: <what>'."""
    return "inputs changed: " + "; ".join(REASONS.get(k, k) for k in changed)


def build_findings(inp, root, now, regenerate=False):
    """Write data/processed/findings/<date>.json (write-once) for every coast pass after the baseline + latest.json. Returns (latest, report)."""
    fdir = os.path.join(root, "data", "processed", "findings")
    passes = coast_passes(inp)
    report = {"written": [], "unchanged": [], "revised": []}
    files = {}
    for sc in passes:
        f = finding(inp, sc, now, True)
        validate(f, inp["rules"])
        path = os.path.join(fdir, "%s.json" % sc["date"])
        old = None if regenerate else jload(path)
        if old and old.get("inputs_sha256") == f["inputs_sha256"]:
            report["unchanged"].append(sc["date"])
            files[sc["date"]] = old
            continue
        if old:
            rev = int(old.get("revision", 1)) + 1
            changed = sorted(k for k, v in f["inputs_detail"].items() if (old.get("inputs_detail") or {}).get(k) != v)
            f["revision"], f["revision_log"] = rev, list(old.get("revision_log") or []) + [{"revision": rev, "utc": iso_utc(now), "changed": changed, "reason": revision_reason(changed)}]
            report["revised"].append(sc["date"])
        else:
            f["revision"], f["revision_log"] = 1, []
            report["written"].append(sc["date"])
        write_json(path, f)
        files[sc["date"]] = f
    if passes:
        last = passes[-1]
        latest = finding(inp, last, now, False)
        rec = files[last["date"]]
        latest["revision"], latest["revision_log"] = rec["revision"], rec["revision_log"]
        latest["inputs_sha256"] = rec["inputs_sha256"]
    else:
        latest = build(inp, now)
        latest.update(schema="findings-v1", template_state="no_new_pass", revision=1, revision_log=[], inputs_sha256=None, archive=False, age=None, comparison_line=None,
                      three_numbers=[], shown_numbers=[], sources={}, caveats=[], confidence={"level": "normal", "reasons": []}, event_chip=None, event_chips=[],
                      sea={"finding": None, "text": inp["strings"]["sea"]["none"]}, evidence_layers=[], radar_finding=None, area_id="godavari", **{"pass": None})
    validate(latest, inp["rules"])
    write_json(os.path.join(fdir, "latest.json"), latest)
    return latest, report


def radar_findings(findings_dir):
    """[(event_id, scene_id, radar_finding)] for every findings file linked to an event. tools/pipeline/events.py ``set_radar_finding(events, event_id,
    scene_id, finding)`` edits an in-memory events dict and does not save it, and data/processed/events.json belongs to the events step, so this
    builder does not write events.json: the orchestrator (run_all.py) feeds these tuples to set_radar_finding and saves."""
    out = []
    for f in sorted(glob.glob(os.path.join(findings_dir, "20*.json"))):
        x = jload(f)
        chips = x.get("event_chips") or ([x["event_chip"]] if x.get("event_chip") else [])
        if x.get("radar_finding"):
            for c in chips:
                out.append((c["event_id"], x["pass"]["scene_id"], x["radar_finding"]))
    return out


def bulletin_window(root, bdir):
    """(first, last) bulletin date from file names like 20261027_1200UTC_...pdf in the event's bulletin folder, or (None, None)."""
    ds = sorted({m.group(1) for m in (re.match(r"(\d{8})_", os.path.basename(f)) for f in glob.glob(os.path.join(root, bdir, "*"))) if m})
    fmt = lambda x: "%s-%s-%s" % (x[:4], x[4:6], x[6:])
    return (fmt(ds[0]), fmt(ds[-1])) if ds else (None, None)


def load_events(root):
    """data/processed/events.json (events-v1) when present; else data/events/*.json (event-v1). For the old files, start/end come from the dates of the
    IMD bulletins in the event's bulletin folder (never guessed); aftermath_days from the rules. ``_landfall_src`` records where the landfall date sits."""
    p = os.path.join(root, "data", "processed", "events.json")
    if os.path.exists(p):
        doc = jload(p)
        out = []
        for i, e in enumerate(doc.get("events") or []):
            e = dict(e)
            e["_landfall_src"] = "data/processed/events.json#events.%d.%s" % (i, "dates.landfall_day" if (e.get("dates") or {}).get("landfall_day") else "landfall.date" if (e.get("landfall") or {}).get("date") else "start")
            out.append(e)
        return out
    out = []
    for f in sorted(glob.glob(os.path.join(root, "data", "events", "*.json"))):
        try:
            e = jload(f)
        except ValueError as ex:
            raise StoryError("%s: %s" % (f, ex))
        rel = os.path.relpath(f, root).replace(os.sep, "/")
        e["_landfall_src"] = rel + ("#dates.landfall_day" if (e.get("dates") or {}).get("landfall_day") else "#landfall.date")
        if not e.get("start") or not e.get("end"):
            a, b = bulletin_window(root, (e.get("imd") or {}).get("bulletin_dir") or "")
            e.setdefault("start", a)
            e.setdefault("end", b)
            e.setdefault("window_source", "dates of the IMD bulletins in %s" % ((e.get("imd") or {}).get("bulletin_dir")))
        out.append(e)
    return out


def load_inputs(root):
    p = lambda *x: os.path.join(root, *x)
    return {"catalog": jload(p("data", "h5", "catalog.json")), "events": load_events(root), "rank": jload(p("data", "processed", "mandal_rank.json")),
            "profile": jload(p("data", "processed", "profile.json")), "class_stats": jload(p("data", "web", "class_stats.json")),
            "rules": jload(p("data", "story_rules.json")), "seasons": jload(p("data", "seasons.json")), "strings": jload(p("app", "strings", "story.en.json")),
            "areas": jload(p("config", "areas.json"))}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--out", default=None, help="output dir (default <root>/data/web)")
    ap.add_argument("--now", default=None, help="override the build time (UTC, 2026-11-14T12:00:00Z) for tests")
    ap.add_argument("--regenerate-findings", action="store_true", help="ignore existing findings files (drops revision history; only before anything was published)")
    ap.add_argument("--no-findings", action="store_true", help="do not write data/processed/findings/ (story.json is then the plain story-v1 build)")
    a = ap.parse_args()
    inp = load_inputs(a.root)
    for k in ("rules", "strings"):
        if not inp[k]:
            print("build_story: missing %s" % k, file=sys.stderr)
            return 1
    now = parse_utc(a.now) if a.now else dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    try:
        report = None
        if a.no_findings:
            story = build(inp, now)
        else:
            story, report = build_findings(inp, a.root, now, a.regenerate_findings)
        validate(story, inp["rules"])
        pres = presentation_cfg(inp.get("areas"))
        story = apply_presentation(story, pres, inp["strings"])      # data/processed/findings/ keeps the caveats; only the public story.json is filtered
        validate(story, inp["rules"])
        ev = next((e for e in inp["events"] if e.get("id") == story.get("event_id")), None)
        jf, atom = feeds(story, inp["strings"], inp["rules"], ev, ((inp.get("areas") or {}).get("site") or {}).get("title"), pres["show_data_caveats"])
        validate({"feed": [{"title": i["title"], "text": i["content_text"]} for i in jf["items"]]}, inp["rules"])
    except StoryError as e:
        print("build_story FAILED: %s" % e, file=sys.stderr)
        return 1
    out = a.out or os.path.join(a.root, "data", "web")
    os.makedirs(out, exist_ok=True)
    story, internal = split_internal(story)          # the caveat text never goes into the public build output
    idir = os.path.join(os.path.dirname(os.path.abspath(out)), "internal")     # sibling of the output dir: data/internal for data/web
    os.makedirs(idir, exist_ok=True)
    with open(os.path.join(idir, "story.internal.json"), "w", encoding="utf-8") as fh:
        json.dump(internal, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    with open(os.path.join(out, "story.json"), "w", encoding="utf-8") as fh:
        json.dump(story, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    with open(os.path.join(out, "feed.json"), "w", encoding="utf-8") as fh:
        json.dump(jf, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    with open(os.path.join(out, "atom.xml"), "w", encoding="utf-8") as fh:
        fh.write(atom)
    if report is not None:
        print("findings: new %s, revised %s, unchanged %s" % (report["written"], report["revised"], report["unchanged"]))
        print("radar_finding per linked pass (for events.py set_radar_finding): %s" % radar_findings(os.path.join(a.root, "data", "processed", "findings")))
    print("story.json: state=%s template_state=%s headline=%r" % (story["state"], story.get("template_state"), story["headline"]))
    for b in story["big_numbers"]:
        print("  %s %s  %s" % (b["value"], b["unit"], b["label"]))
    print("  %d updates, next pass %s" % (len(story["updates"]), (story["next_pass"] or {}).get("date")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
