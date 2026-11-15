#!/usr/bin/env python3
"""Fixture tests for tools/build_story.py. Plain asserts, no pytest needed:  python3 tools/tests/test_story.py
Cases: first_pass, recovery (most / partial / little), worse, stale, missing numbers, watch, sample badge, confounders,
guards (banned word, leftover placeholder, hedge), next pass, permalinks, feeds."""
import copy
import datetime as dt
import json
import os
import sys
import traceback
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import build_story as B  # noqa: E402

RULES = B.jload(os.path.join(ROOT, "data", "story_rules.json"))
STRINGS = B.jload(os.path.join(ROOT, "app", "strings", "story.en.json"))
SEASONS = B.jload(os.path.join(ROOT, "data", "seasons.json"))


def row(name, water, err=0.5, normal_water=0.05, coverage=99.0, flag=None, rank=None):
    return {"mandal": name, "district": "D", "water_pct": water, "water_err": err, "err": err, "crops_pct": 0.5, "crops_err": 1.0,
            "total_pct": water + 0.5, "normal_pct": 1.0, "normal_water_pct": normal_water, "rank": None, "rank_water": None,
            "coverage_pct": coverage, "flag": flag, "area_km2": 100.0, "water_km2": water, "flooded_km2": water + 0.5}


def block(date, rows, status="VALIDATED", scene="L_COAST_X"):
    ok = sorted([r for r in rows if not r["flag"]], key=lambda r: -r["water_pct"])
    for i, r in enumerate(ok, 1):
        r["rank_water"] = r["rank"] = i
    return {"date": date, "scene_id": scene + date[5:].replace("-", ""), "product_status": status, "start_utc": date + "T00:01:07Z", "rows": rows}


def scene(date, role="COAST", track=55, status="VALIDATED"):
    return {"scene_id": "%s_%s" % (role, date), "role": role, "date": date, "start_utc": date + ("T00:01:07Z" if role == "COAST" else "T13:01:51Z"),
            "track": track, "product_status": status, "file": "data/h5/x.h5"}


def event(landfall="2026-10-28", status="active", confounders=None):
    return {"id": "ev_2026", "name": "Cyclone Test", "status": status, "dates": {"landfall_day": landfall}, "landfall": {"date": landfall},
            "monitor_days": 45, "official_links": [{"name": "IMD", "url": "https://mausam.imd.gov.in/"}], "confounders": confounders or []}


def inputs(blocks, scenes=None, ev=None, profile=None, provenance=True):
    dates = sorted(blocks)
    rank = {"by_date": blocks, "dates": dates, "latest_date": dates[-1]} if blocks else None
    if rank and provenance:
        rank["provenance"] = {"tool": "test"}
    return {"rules": copy.deepcopy(RULES), "strings": copy.deepcopy(STRINGS), "seasons": SEASONS,
            "catalog": {"scenes": scenes if scenes is not None else [scene(d) for d in dates]},
            "events": [ev] if ev else [], "rank": rank, "profile": profile, "class_stats": None}


def now(s="2026-11-14T12:00:00Z"):
    return B.parse_utc(s)


def flooded_rows(n_flooded, n_dry=3, water=9.0):
    return [row("F%d" % i, water) for i in range(n_flooded)] + [row("D%d" % i, 0.2) for i in range(n_dry)]


def run(inp, t=None):
    s = B.build(inp, t or now())
    B.validate(s, inp["rules"])
    return s


# --------------------------------------------------------------------- tests
def test_first_pass():
    s = run(inputs({"2026-11-09": block("2026-11-09", flooded_rows(3))}, ev=event("2026-11-02")))
    assert s["state"] == "event", s["state"]
    assert s["headline_key"] == "first_pass"
    assert s["headline"] == B.fill(STRINGS["headline"]["first_pass"], event="Cyclone Test")
    assert s["since_last"] is None
    assert [b["id"] for b in s["big_numbers"]] == ["top_mandal", "flooded_count", "days_after"], [b["id"] for b in s["big_numbers"]]
    assert s["big_numbers"][1]["value"] == "3"
    assert s["big_numbers"][2]["value"] == "7"
    assert len(s["updates"]) == 1 and s["updates"][0]["id"] == "2026-11-09"
    assert s["updates"][0]["permalink"] == "#tab=happened&mode=share&d=2026-11-09"


def test_recovery_most_partial_little():
    prev = flooded_rows(4)
    cases = [("recovery.most", [row("F0", 1.0), row("F1", 1.0), row("F2", 1.0), row("F3", 8.9)]),     # 3 of 4 receded = 0.75
             ("recovery.partial", [row("F0", 1.0), row("F1", 8.9), row("F2", 8.9), row("F3", 8.9)]),  # 1 of 4 = 0.25
             ("recovery.little", [row("F0", 8.9), row("F1", 8.9), row("F2", 8.9), row("F3", 8.9)])]   # 0 of 4
    for key, now_rows in cases:
        now_rows = now_rows + [row("D%d" % i, 0.2) for i in range(3)]
        s = run(inputs({"2026-10-28": block("2026-10-28", copy.deepcopy(prev)), "2026-11-09": block("2026-11-09", now_rows)}, ev=event()))
        assert s["state"] == "recovery", s["state"]
        assert s["headline_key"] == key, (key, s["headline_key"], s["since_last"])
        assert s["since_last"]["flooded_mandals_prev"] == 4
        sl = s["since_last"]
        assert sl["receded"] + sl["still"] + sl["worse"] == 4 or key == "recovery.most"
        assert "{" not in s["sub"]
    s = run(inputs({"2026-10-28": block("2026-10-28", copy.deepcopy(prev)), "2026-11-09": block("2026-11-09", [row("F0", 1.0), row("F1", 1.0), row("F2", 1.0), row("F3", 8.9)] + [row("D%d" % i, 0.2) for i in range(3)])}, ev=event()))
    assert s["since_last"]["receded"] == 3 and s["since_last"]["still"] == 1
    assert s["big_numbers"][1]["id"] == "change"
    assert s["badges"]["provisional"] is False


def test_worse():
    s = run(inputs({"2026-10-28": block("2026-10-28", [row("F0", 9.0), row("F1", 0.2), row("F2", 0.2), row("D0", 0.2)]), "2026-11-09": block("2026-11-09", flooded_rows(3, n_dry=1))}, ev=event()))
    assert s["headline_key"] == "worse"
    assert s["headline"] == STRINGS["headline"]["worse"]
    assert s["since_last"]["flooded_mandals_prev"] == 1 and s["since_last"]["flooded_mandals_now"] == 3
    assert s["since_last"]["worse"] == 2 and s["since_last"]["still"] == 1


def test_change_inside_error_is_flat():
    a = [row("A", 5.0, err=3.0), row("B", 0.1)]
    b = [row("A", 8.0, err=3.0), row("B", 0.1)]          # +3 is below 2 x err (6): no clear change
    s = run(inputs({"2026-10-28": block("2026-10-28", a), "2026-11-09": block("2026-11-09", b)}, ev=event()))
    assert s["mandals"]["A"]["trend"] == "flat"
    assert "no clear change" in s["mandal_sentences"]["A"].lower()


def test_stale():
    inp = inputs({"2026-11-09": block("2026-11-09", flooded_rows(3))}, ev=event("2026-10-28"))
    s = run(inp, now("2026-11-29T12:00:00Z"))           # 20 days after the pass
    assert s["state"] == "stale" and s["base_state"] in ("event", "recovery"), (s["state"], s["base_state"])
    assert s["headline"] == B.fill(STRINGS["headline"]["no_new_pass"], days=20)
    assert s["sub"].startswith(B.fill(STRINGS["stale_sub"], date="9 Nov")), s["sub"]
    assert s["stale"] is True
    assert s["next_pass"]["overdue"] is True and "was expected" in s["next_pass"]["text"] and "not in the catalogue" in s["next_pass"]["text"]
    assert s["next_pass"]["date"] >= "2026-11-29" and s["next_pass"]["days_until"] >= 0 and s["next_pass"]["first_expected"] == "2026-11-21"
    assert "today" not in s["headline"].lower() and " now" not in s["headline"].lower()
    fresh = run(inp, now("2026-11-14T12:00:00Z"))
    assert fresh["state"] != "stale" and fresh["stale"] is False


def test_missing_numbers():
    s = run(inputs({}, scenes=[scene("2026-11-09")], ev=event()))
    assert s["numbers_ready"] is False
    assert s["headline"] == B.fill(STRINGS["numbers_coming"], date="9 Nov")      # a coast pass is in the catalogue, no numbers yet
    assert s["big_numbers"] == [] and s["mandal_sentences"] == {} and s["updates"] == []
    assert s["badges"]["sample"] is True
    only_sea = run(inputs({}, scenes=[scene("2026-11-08", "SEA", 48)], ev=event()))
    assert only_sea["headline"] == STRINGS["missing_numbers"]                     # no coast pass at all: the old generic line


def test_sample_badge_prefix():
    s = run(inputs({"2026-11-09": block("2026-11-09", flooded_rows(3))}, ev=event("2026-11-02"), provenance=False))
    assert s["badges"]["sample"] is True
    assert s["headline"].startswith(STRINGS["headline"]["practice_prefix"])


def test_watch():
    s = run(inputs({"2026-03-02": block("2026-03-02", [row("A", 0.2), row("B", 0.1)])}, ev=event("2025-10-28"), scenes=[scene("2026-03-02")]), now("2026-03-10T12:00:00Z"))
    assert s["state"] == "watch", s["state"]
    assert s["headline"] == STRINGS["headline"]["watch"]
    assert STRINGS["watch"]["normal_check"] in s["sub"]
    assert "January to March" in s["sub"], s["sub"]            # season line from data/seasons.json
    assert [b["id"] for b in s["big_numbers"]] == ["flooded_count", "days_to_next", "days_since_pass"]
    assert s["big_numbers"][0]["value"] == "0"
    nothing = run(inputs({"2026-03-02": block("2026-03-02", [row("A", 0.2)])}, ev=None, scenes=[scene("2026-03-02")]), now("2026-03-10T12:00:00Z"))
    assert nothing["state"] == "watch" and nothing["event_id"] is None
    stub = event("2026-03-01", status="needs_review")
    assert run(inputs({"2026-03-02": block("2026-03-02", flooded_rows(3))}, ev=stub, scenes=[scene("2026-03-02")]), now("2026-03-10T12:00:00Z"))["state"] == "watch"


def test_next_pass_and_timestamps():
    s = run(inputs({"2026-11-09": block("2026-11-09", flooded_rows(3))}, ev=event("2026-11-02")))
    assert s["next_pass"]["date"] == "2026-11-21" and s["next_pass"]["track"] == 55
    assert s["next_pass"]["days_until"] == 7 and s["next_pass"]["overdue"] is False
    assert s["data_as_of"] == "2026-11-09T00:01:07Z"
    assert "05:31" in s["data_as_of_text"] and s["built_utc"] == "2026-11-14T12:00:00Z"


def test_confounders_and_permalinks():
    conf = [{"id": "m", "name": "Cyclone Murasu", "affects_dates": ["2026-11-09"], "text": "Cyclone Murasu also put water on the land.", "limit_text": "Murasu"}]
    inp = inputs({"2026-10-28": block("2026-10-28", flooded_rows(0)), "2026-11-09": block("2026-11-09", flooded_rows(3))},
                 scenes=[scene("2026-10-28"), scene("2026-11-09"), scene("2026-10-27", "SEA", 48), scene("2026-11-08", "SEA", 48)], ev=event(confounders=conf),
                 profile={"layer_id": "nisar_l_sea_20261027_t48_vv", "eye_radius_km": 6.4, "eye_radius_err": 0.5})
    s = run(inp)
    assert s["confounders"] == ["Cyclone Murasu also put water on the land."]
    assert "Cyclone Murasu also put water on the land." in s["sub"]
    ids = [u["id"] for u in s["updates"]]
    assert ids == ["2026-11-09", "2026-11-08", "2026-10-28", "2026-10-27"], ids
    pl = {u["id"]: u["permalink"] for u in s["updates"]}
    assert pl["2026-11-09"] == "#tab=happened&mode=share&d=2026-11-09"
    assert pl["2026-10-28"] == "#tab=happened&mode=radar&role=coast&d=2026-10-28"
    assert pl["2026-11-08"] == "#tab=happened&mode=radar&role=sea&d=2026-11-08"
    assert pl["2026-10-27"] == "#tab=happened&mode=eye&d=2026-10-27"
    eye = [u for u in s["updates"] if u["id"] == "2026-10-27"][0]
    assert eye["big_numbers"][0]["value"] == "6" and eye["big_numbers"][0]["unit"] == "km"
    other = run(inputs({"2026-11-09": block("2026-11-09", flooded_rows(3))}, ev=event("2026-10-28", confounders=conf)), now("2026-11-14T12:00:00Z"))
    assert other["confounders"] == ["Cyclone Murasu also put water on the land."]
    none = run(inputs({"2026-11-09": block("2026-11-09", flooded_rows(3))}, ev=event("2026-10-28")))
    assert none["confounders"] == []


def test_provisional_badge():
    inp = inputs({"2026-11-09": block("2026-11-09", flooded_rows(3), status="PROVISIONAL")}, ev=event("2026-11-02"))
    s = run(inp)
    assert s["badges"]["provisional"] is True and STRINGS["provisional"] in s["sub"]


def test_water_class_only():
    rows = [row("W", 9.0), row("C", 0.5)]
    rows[1]["crops_pct"] = 30.0                               # lots of "wet crops" must not make a flooded mandal
    rows[1]["total_pct"] = 30.5
    s = run(inputs({"2026-11-09": block("2026-11-09", rows)}, ev=event("2026-11-02")))
    assert s["mandals"]["C"]["flooded"] is False and s["mandals"]["W"]["flooded"] is True
    assert s["big_numbers"][1]["value"] == "1"


def test_low_coverage_not_ranked():
    rows = [row("W", 9.0), row("L", 20.0, coverage=30.0, flag="valid coverage <50%")]
    s = run(inputs({"2026-11-09": block("2026-11-09", rows)}, ev=event("2026-11-02")))
    assert s["mandal_sentences"]["L"] == STRINGS["mandal"]["not_enough_view"]
    assert s["big_numbers"][0]["mandal"] == "W"


def test_guards():
    inp = inputs({"2026-11-09": block("2026-11-09", flooded_rows(3))}, ev=event("2026-11-02"))
    s = B.build(inp, now())
    bad = copy.deepcopy(s)
    bad["sub"] = "The storm did damage to the coast."
    try:
        B.validate(bad, inp["rules"])
        raise AssertionError("banned word not caught")
    except B.StoryError as e:
        assert "banned" in str(e)
    bad = copy.deepcopy(s)
    bad["headline"] = "Land is {top_mandal} probably under water."
    try:
        B.validate(bad, inp["rules"])
        raise AssertionError("placeholder not caught")
    except B.StoryError as e:
        assert "placeholder" in str(e)
    bad = copy.deepcopy(s)
    bad["headline"] = "The coast is flooded."
    try:
        B.validate(bad, inp["rules"])
        raise AssertionError("missing hedge not caught")
    except B.StoryError as e:
        assert "hedge" in str(e)
    broken = copy.deepcopy(inp)
    broken["strings"]["headline"]["first_pass"] = "First picture after {storm_name}: some land was probably under water."
    try:
        B.build(broken, now())
        raise AssertionError("unfilled template not caught")
    except B.StoryError:
        pass
    B.validate(s, inp["rules"])


CONF = [{"id": "m", "name": "Cyclone Murasu", "affects_dates": ["2026-11-09"], "text": "Cyclone Murasu also put water on the land.", "limit_text": "Murasu"}]


def caveat_story():
    """A story with every caveat source on: provisional pass, confounder, practice (sample) numbers."""
    inp = inputs({"2026-10-28": block("2026-10-28", flooded_rows(0)), "2026-11-09": block("2026-11-09", flooded_rows(3), status="PROVISIONAL")},
                 ev=event(confounders=CONF))
    s = run(inp)
    s["caveats"] = [STRINGS["provisional"]] + s["confounders"]
    s["confidence"] = {"level": "lower", "reasons": [STRINGS["confidence"]["provisional_pass"]]}
    return inp, s


def numbers_of(s):
    return json.dumps({k: s[k] for k in ("big_numbers", "mandals", "mandal_sentences", "scene", "next_pass")}, sort_keys=True)


def test_presentation_default_is_caveats_hidden():
    assert B.presentation_cfg(None) == {"show_data_caveats": False, "cannot_tell_position": "end"}
    assert B.presentation_cfg({"presentation": {"show_data_caveats": True}})["show_data_caveats"] is True
    cfg = B.jload(os.path.join(ROOT, "config", "areas.json"))["presentation"]
    assert cfg == {"show_data_caveats": False, "cannot_tell_position": "end"}, cfg
    for bad in ({"show_data_caveats": "no"}, {"cannot_tell_position": "top"}):
        try:
            B.presentation_cfg({"presentation": bad})
            raise AssertionError("bad presentation accepted")
        except B.StoryError:
            pass


def test_presentation_caveats_hidden():
    inp, s = caveat_story()
    assert s["badges"]["provisional"] is True and STRINGS["provisional"] in s["sub"]
    pub = B.apply_presentation(s, B.presentation_cfg(None), inp["strings"])
    B.validate(pub, inp["rules"])
    assert pub["presentation"] == {"show_data_caveats": False, "cannot_tell_position": "end"}
    assert pub["badges"] == {"provisional": False, "sample": False}
    assert pub["provisional_text"] is None and pub["caveats"] == [] and pub["confounders"] == []
    assert pub["confidence"] == {"level": "normal", "reasons": []}
    public = json.dumps({k: v for k, v in pub.items() if k != "internal"})
    for banned in (STRINGS["provisional"], "Early data", "Murasu", "Practice numbers", "likely to change", "Lower confidence"):
        assert banned not in public, banned
    assert all(u["confounders"] == [] and "Murasu" not in u["text"] for u in pub["updates"])
    assert numbers_of(pub) == numbers_of(s), "numbers must not change"
    assert "looked" in pub["updates"][0]["text"], "the finding itself stays"
    # the originals are kept for docs, tests and the deck
    i = pub["internal"]
    assert i["badges"]["provisional"] is True and i["provisional_text"] == STRINGS["provisional"]
    assert i["confounders"] == ["Cyclone Murasu also put water on the land."] and i["confidence"]["level"] == "lower"
    assert STRINGS["provisional"] in i["sub"] and "Murasu" in i["lead"]
    assert i["updates"]["2026-11-09"]["confounders"] and "Murasu" in i["updates"]["2026-11-09"]["text"]
    assert s["badges"]["provisional"] is True, "the input story is not edited in place"


def test_presentation_caveats_shown():
    inp, s = caveat_story()
    pub = B.apply_presentation(s, {"show_data_caveats": True, "cannot_tell_position": "inline"}, inp["strings"])
    assert pub["presentation"] == {"show_data_caveats": True, "cannot_tell_position": "inline"}
    assert pub["badges"]["provisional"] is True and pub["provisional_text"] == STRINGS["provisional"]
    assert pub["sub"] == s["sub"] and pub["caveats"] == s["caveats"] and pub["confidence"]["level"] == "lower"
    assert pub["confounders"] == s["confounders"] and pub["updates"] == s["updates"]
    assert pub["internal"]["badges"]["provisional"] is True


def test_feeds_respect_presentation():
    inp, s = caveat_story()
    for show in (True, False):
        pub = B.apply_presentation(s, {"show_data_caveats": show, "cannot_tell_position": "end"}, inp["strings"])
        jf, atom = B.feeds(pub, inp["strings"], inp["rules"], inp["events"][0], None, show)
        root = ET.fromstring(atom)
        ns = {"a": "http://www.w3.org/2005/Atom"}
        assert len(root.findall("a:entry", ns)) == len(jf["items"]) == 2
        blob = json.dumps(jf) + atom
        if show:
            assert "(provisional)" in blob and "Murasu" in blob and any("provisional" in i["tags"] for i in jf["items"])
        else:
            assert "provisional" not in blob.lower() and "Murasu" not in blob and "Early data" not in blob, blob
            assert all("(" not in i["title"] and i["tags"] == ["coast"] for i in jf["items"])
            assert all("looked" in i["content_text"] for i in jf["items"])


def test_draft_chip_needs_a_linked_pass():
    d = "2026-10-28"
    ev = {"id": "auto_GDACS_1", "name": "Flood in India", "type": "flood", "area_id": "godavari", "start": "2026-10-20", "end": "2026-11-04",
          "aftermath_days": 30, "status": "alert_only", "reviewed_by_human": False, "linked_passes": []}
    assert B.chips_for([ev], d, "godavari", STRINGS, RULES) == [], "no linked pass, no chip"
    ev["linked_passes"] = [{"scene_id": "L_COAST_1028", "date": d, "role": "COAST", "relation": "during", "radar_finding": "numbers_coming"}]
    ch = B.chips_for([ev], d, "godavari", STRINGS, RULES)
    assert len(ch) == 1 and "not reviewed" in ch[0]["text"]
    assert B.norm_event(ev, RULES, d)["linked_to_this_pass"] is True
    assert B.norm_event(dict(ev, linked_passes=[]), RULES, d)["linked_to_this_pass"] is False
    assert "linked_to_this_pass" not in B.norm_event(dict(ev, reviewed_by_human=True), RULES, d)


def test_feeds():
    inp = inputs({"2026-10-28": block("2026-10-28", flooded_rows(0)), "2026-11-09": block("2026-11-09", flooded_rows(3))}, ev=event())
    s = run(inp)
    jf, atom = B.feeds(s, inp["strings"], inp["rules"], inp["events"][0])
    assert jf["version"] == "https://jsonfeed.org/version/1.1" and len(jf["items"]) == 2
    for it in jf["items"]:
        assert it["id"] and it["url"].startswith("https://") and "#tab=happened" in it["url"] and it["title"] and it["date_published"].endswith("Z")
    root = ET.fromstring(atom)
    ns = {"a": "http://www.w3.org/2005/Atom"}
    assert len(root.findall("a:entry", ns)) == 2 and root.find("a:updated", ns).text
    assert json.loads(json.dumps(jf))["title"] == "Cyclone Test: radar updates"


def test_real_data_if_present():
    root = ROOT
    if not os.path.exists(os.path.join(root, "data", "processed", "mandal_rank.json")):
        return
    inp = B.load_inputs(root)
    if not inp["rank"] or "by_date" not in inp["rank"]:
        return
    s = B.build(inp, now("2026-11-14T12:00:00Z"))
    B.validate(s, inp["rules"])
    assert s["state"] in ("event", "recovery", "watch", "stale") and len(s["big_numbers"]) <= 3


def test_long_mandal_name_and_filled_text_guard():
    """Filled text is checked, not only templates: a long two/three-word mandal name must not push any sentence over 20 words,
    and a 21-word sentence on a since_last path must be caught by validate()."""
    long_name = "Kakinada Rural Urban"
    lf = [row(long_name, 0.3), row("D0", 0.2)]
    nw = [row(long_name, 0.1), row("D0", 0.2)]
    inp = inputs({"2026-10-28": block("2026-10-28", lf), "2026-11-09": block("2026-11-09", copy.deepcopy(nw)), "2026-11-21": block("2026-11-21", copy.deepcopy(nw))}, ev=event())
    s = run(inp, now("2026-11-22T12:00:00Z"))
    txt = s["since_last"].get("since_landfall")
    assert txt, "since_landfall sentence expected"
    for sent in txt.replace("\n", " ").split(". "):
        assert len(sent.split()) <= 20, sent
    bad = copy.deepcopy(s)
    bad["since_last"]["since_landfall"] = " ".join(["word"] * 21) + "."
    try:
        B.validate(bad, inp["rules"])
        raise AssertionError("21-word filled sentence not caught")
    except B.StoryError as e:
        assert "over 20 words" in str(e)


def test_top_mandal_number_respects_flood_rule():
    calm_rows = [row("Katrenikona", 0.8, err=1.0), row("D0", 0.2)]
    s = run(inputs({"2026-10-28": block("2026-10-28", calm_rows)}, ev=event("2026-10-28")))
    top = s["big_numbers"][0]
    assert top["id"] == "top_mandal" and "under water" not in top["label"] and "flooded" not in top["label"], top["label"]
    s = run(inputs({"2026-10-28": block("2026-10-28", flooded_rows(2))}, ev=event("2026-10-28")))
    assert "under water" in s["big_numbers"][0]["label"]


def test_analysis_failed_sub_fits_state():
    inp = inputs({"2026-10-28": block("2026-10-28", flooded_rows(2))}, scenes=[scene("2026-10-28"), scene("2026-11-21")], ev=event())
    inp["_override"] = "numbers_coming"
    inp["_pass_date"] = "2026-11-21"
    s = B.build(inp, now("2026-11-22T12:00:00Z"))
    assert s["state"] == "event" and "No storm is being tracked" not in s["sub"], s["sub"]


def main():
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    bad = 0
    for name, fn in tests:
        try:
            fn()
            print("PASS  %s" % name)
        except Exception:      # noqa: BLE001
            bad += 1
            print("FAIL  %s" % name)
            traceback.print_exc()
    print("%d tests, %d failed" % (len(tests), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
