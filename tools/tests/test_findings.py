#!/usr/bin/env python3
"""Tests for the per-pass findings files (tools/build_story.py, schema findings-v1). Plain asserts:  python tools/tests/test_findings.py
Covers: every template state renders and validates; event name absent outside the event window; every displayed number equals the value at its
source path; write-once + revision bump; quiet rule; season / baseline rules. Synthetic worlds live in a temp dir; the real repo is only read."""
import copy
import json
import os
import shutil
import sys
import tempfile
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
import build_story as B  # noqa: E402
import test_story as T  # noqa: E402

NOW = B.parse_utc("2026-11-14T12:00:00Z")
EVENT_NAME = "Cyclone Test"


def kcls(nw_pct, km2=None, land_km2=5000.0):
    km2 = nw_pct / 100.0 * land_km2 if km2 is None else km2
    return {"new_water_km2": km2, "new_water_pct_of_land": nw_pct, "wet_crops_km2": 1.0, "wet_crops_pct_of_land": 0.02}


def make_root(tmp, passes, baseline_status="PROVISIONAL", extra_catalog=(), events=True, areas=True, normal_pct=0.04):
    """passes = [(date, rows, nw_pct, status)] with numbers. Returns the root. Baseline: 4 + 16 Oct track 55 (post-monsoon)."""
    def w(rel, obj):
        p = os.path.join(tmp, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as fh:
            json.dump(obj, fh)
    for rel in ("data/story_rules.json", "data/seasons.json", "app/strings/story.en.json"):
        w(rel, B.jload(os.path.join(ROOT, rel)))
    scenes = [T.scene("2026-10-04", status=baseline_status), T.scene("2026-10-16", status=baseline_status)]
    scenes += [T.scene(d, status=st) for d, _, _, st in passes] + list(extra_catalog)
    for s in scenes:
        s["file"] = "data/h5/%s.h5" % s["scene_id"]
    w("data/h5/catalog.json", {"schema": "x", "scenes": scenes})
    blocks = {d: T.block(d, copy.deepcopy(rows), status=st) for d, rows, _, st in passes}
    for d, b in blocks.items():
        b["scene_id"] = "L_COAST_" + d
    ds = sorted(blocks)
    w("data/processed/mandal_rank.json", {"by_date": blocks, "dates": ds, "latest_date": ds[-1] if ds else None, "provenance": {"tool": "test"}})
    classes = {"normal|k=3.0": kcls(normal_pct), "normal|k=2.0": kcls(normal_pct), "normal|k=4.0": kcls(normal_pct)}
    for d, _, pct, _ in passes:
        k = d.replace("-", "")
        classes[k + "|k=3.0"], classes[k + "|k=2.0"], classes[k + "|k=4.0"] = kcls(pct), kcls(pct * 1.3), kcls(pct * 0.7)
    w("data/web/class_stats.json", {"baseline_dates": ["20261004", "20261016"], "classes": classes, "h5_sources": {},
                                    "scenes": {s["date"]: {"scene_id": s["scene_id"], "product_status": s["product_status"]} for s in scenes if s["role"] == "COAST"}})
    if events:
        shutil.copy(os.path.join(HERE, "fixtures", "events_min.json"), os.path.join(tmp, "data", "processed", "events.json"))
    if areas:
        w("config/areas.json", B.jload(os.path.join(ROOT, "config", "areas.json")) or {"schema": "areas-v1", "default_area": "godavari", "areas": [{"id": "godavari", "baselines": {
            "COAST": {"55": {"season": "post_monsoon", "dates": ["2026-10-04", "2026-10-16"]}}}}]})
    return tmp


def flooded(n=3):
    return T.flooded_rows(n)


def calm():
    return [T.row("A%d" % i, 0.2) for i in range(4)]


def all_findings(root, now=NOW):
    inp = B.load_inputs(root)
    out = {}
    for sc in B.coast_passes(inp):
        out[sc["date"]] = B.finding(inp, sc, now, True)
    inp_latest = None
    if B.coast_passes(inp):
        out["latest"] = B.finding(inp, B.coast_passes(inp)[-1], now, False)
    return inp, out


# ---------------------------------------------------------------- states
def test_every_state_renders_and_validates():
    seen = {}
    with tempfile.TemporaryDirectory() as tmp:
        # big_change (9 Nov, 8 flooded) and quiet (same rows twice, new water at the control level)
        make_root(tmp, [("2026-10-28", calm(), 0.05, "VALIDATED"), ("2026-11-09", flooded(3), 1.6, "VALIDATED")])
        inp, fs = all_findings(tmp)
        seen["big_change"] = fs["2026-11-09"]
        assert fs["2026-11-09"]["event_chip"]["text"] == "After " + EVENT_NAME
        assert fs["2026-10-28"]["template_state"] == "quiet", fs["2026-10-28"]["template_state"]
        assert fs["2026-10-28"]["headline"] == B.fill(inp["strings"]["headline"]["quiet"], prev_date="16 Oct")
        seen["quiet"] = fs["2026-10-28"]
        # no_new_pass: latest, 30 days after the pass
        _, late = all_findings(tmp, B.parse_utc("2026-12-09T12:00:00Z"))
        assert late["latest"]["template_state"] == "no_new_pass", late["latest"]["template_state"]
        assert "No new radar pass in 30 days" in late["latest"]["headline"] or "No new radar" in late["latest"]["headline"]
        assert late["latest"]["age"]["days_since_pass"] == 30
        assert late["latest"]["three_numbers"], "no_new_pass keeps the last numbers"
        assert fs["latest"]["age"]["text"] == "Last radar pass 5 days ago."
        seen["no_new_pass"] = late["latest"]
    with tempfile.TemporaryDirectory() as tmp:
        # numbers_coming: a pass is in the catalogue, analysis has no numbers for it
        make_root(tmp, [("2026-10-28", flooded(3), 1.6, "VALIDATED")], extra_catalog=[T.scene("2026-11-09")])
        inp, fs = all_findings(tmp)
        f = fs["2026-11-09"]
        seen["numbers_coming"] = f
        assert f["template_state"] == "numbers_coming" and f["numbers_ready"] is False
        assert f["headline"] == B.fill(inp["strings"]["numbers_coming"], date="9 Nov")
        assert f["three_numbers"] == [] and f["big_numbers"] == [] and f["comparison_line"] is None and f["since_last"] is None
        assert all(u["date"] != "2026-11-09" for u in f["updates"]), "no older numbers presented as the new pass"
    with tempfile.TemporaryDirectory() as tmp:
        # no_baseline: another track, and a season two steps away from the baseline season
        make_root(tmp, [("2026-10-28", flooded(3), 1.6, "VALIDATED")],
                  extra_catalog=[T.scene("2026-11-09", track=128), T.scene("2027-04-20")])
        inp, fs = all_findings(tmp)
        for d in ("2026-11-09", "2027-04-20"):
            f = fs[d]
            assert f["template_state"] == "no_baseline", (d, f["template_state"])
            assert f["headline"] == inp["strings"]["headline"]["no_baseline"] and f["three_numbers"] == [] and f["numbers_ready"] is False
            assert f["confidence"]["level"] == "lower"
        seen["no_baseline"] = fs["2026-11-09"]
    assert set(seen) == set(inp["rules"]["template_states"]), set(seen)
    for st, f in seen.items():
        assert f["template_state"] == st and f["schema"] == "findings-v1"
        B.validate(f, inp["rules"])
        for k in ("pass", "confidence", "event_chip", "sea", "evidence_layers", "sources", "caveats", "comparison_line", "three_numbers", "age", "area_id", "revision"):
            assert k in f, (st, k)
        assert f["sea"]["finding"] is None and "No plain-language sea finding" in f["sea"]["text"]


def test_real_data_every_pass_validates():
    inp = B.load_inputs(ROOT)
    passes = B.coast_passes(inp)
    assert [p["date"] for p in passes][:2] == ["2026-10-28", "2026-11-09"], [p["date"] for p in passes]
    for sc in passes:
        for archive in (True, False):
            f = B.finding(inp, sc, NOW, archive)
            B.validate(f, inp["rules"])
            assert f["template_state"] in inp["rules"]["template_states"]
    newest = passes[-1]
    latest = B.finding(inp, newest, NOW, False)
    key = "%s|k=3.0" % newest["date"].replace("-", "")
    stats = inp["class_stats"]["classes"].get(key)
    # numbers_coming / no_baseline passes carry no change numbers; only compare when both sides exist
    if latest["template_state"] in ("big_change", "quiet") and latest.get("three_numbers") and stats:
        assert latest["three_numbers"][0]["value"] == int(round(stats["new_water_km2"]))
    else:
        assert latest["template_state"] in ("numbers_coming", "no_baseline", "no_new_pass") or not latest.get("three_numbers")


# ---------------------------------------------------------------- event window
def test_event_name_only_inside_window():
    with tempfile.TemporaryDirectory() as tmp:
        make_root(tmp, [("2026-10-28", flooded(2), 1.0, "VALIDATED"), ("2026-11-09", flooded(3), 1.6, "VALIDATED"), ("2027-01-20", flooded(3), 1.6, "VALIDATED")])
        inp, fs = all_findings(tmp)
        inside = {"2026-10-28": "During " + EVENT_NAME, "2026-11-09": "After " + EVENT_NAME}
        for d, chip in inside.items():
            assert fs[d]["event_chip"]["text"] == chip, (d, fs[d]["event_chip"])
        f = fs["2027-01-20"]                                  # 84 days after the end: outside end + 30 days
        assert f["event_chip"] is None
        assert EVENT_NAME not in json.dumps(f, ensure_ascii=False), "event name leaked into a pass outside the window"
        assert "Other" not in json.dumps(f["caveats"]) and f["event_id"] is None
        assert fs["2026-11-09"]["caveats"][-1].startswith("Cyclone Other"), "confounder text is for passes inside the window only"
        # window edges
        ev = inp["events"][0]
        r = lambda d: B.chip_relation(ev, d, inp["rules"])
        assert r("2026-10-23") is None and r("2026-10-24") == "during" and r("2026-10-28") == "during"
        assert r("2026-10-29") == "after" and r("2026-11-27") == "after" and r("2026-11-28") is None


# ---------------------------------------------------------------- numbers equal their sources
def test_numbers_equal_source_values():
    n = 0
    for root, tag in ((ROOT, "real"),):
        inp, fs = all_findings(root)
        for name, f in fs.items():
            n += check_numbers(f, root, inp["rules"], tag + ":" + name)
    with tempfile.TemporaryDirectory() as tmp:
        make_root(tmp, [("2026-10-28", flooded(2), 1.0, "VALIDATED"), ("2026-11-09", flooded(3), 1.6, "VALIDATED")])
        inp, fs = all_findings(tmp)
        for name, f in fs.items():
            n += check_numbers(f, tmp, inp["rules"], "synthetic:" + name)
    assert n > 30, n


def check_numbers(f, root, rules, tag):
    cache = {}
    count = 0
    assert f["sources"] == {x["key"]: x["source"] for x in f["shown_numbers"]}, tag
    for x in f["shown_numbers"]:
        got = B.resolve_source(x["source"], root, rules, cache)
        assert abs(got - x["raw"]) < 0.011, (tag, x["key"], got, x["raw"])
        assert B.FMT[x["fmt"]](x["raw"]) == x["text"], (tag, x["key"], x["text"], x["raw"])
        count += 1
    # three_numbers shown values come from their registered raw values
    for i, t in enumerate(f["three_numbers"]):
        x = next(s for s in f["shown_numbers"] if s["key"] == "three_numbers[%d].value" % i)
        assert float(x["text"]) == float(t["value"]), (tag, i, x["text"], t["value"])
        if "err" in t:
            e = next(s for s in f["shown_numbers"] if s["key"] == "three_numbers[%d].err" % i)
            assert float(e["text"]) == float(t["err"])
            assert "give or take %s" % e["text"] in t["label"]
    # every number written in comparison_line is registered
    if f["comparison_line"]:
        for key in ("km2", "err", "normal_km2"):
            x = next(s for s in f["shown_numbers"] if s["key"] == "comparison_line." + key)
            assert x["text"] in f["comparison_line"], (tag, key, x["text"], f["comparison_line"])
        if "prev_km2" in [s["key"].split(".")[-1] for s in f["shown_numbers"]]:
            x = next(s for s in f["shown_numbers"] if s["key"] == "comparison_line.prev_km2")
            assert x["text"] in f["comparison_line"]
    # every big number has a registered source (runtime clock numbers are the only exception, marked 'runtime:')
    for i, b in enumerate(f.get("big_numbers") or []):
        src = b.get("source")
        assert src is not None, (tag, "big_numbers", i, b["id"])
        if isinstance(src, str) and src.startswith("runtime:"):
            continue
        assert "big_numbers[%d].value" % i in f["sources"], (tag, i)
    return count


def test_walk_handles_dotted_keys():
    d = {"classes": {"20261109|k=3.0": {"new_water_km2": 83.7}}, "rows": [{"a": 1}, {"a": 2}]}
    assert B.walk(d, "classes.20261109|k=3.0.new_water_km2") == 83.7
    assert B.walk(d, "rows.1.a") == 2


# ---------------------------------------------------------------- write-once
def test_write_once_and_revision():
    with tempfile.TemporaryDirectory() as tmp:
        make_root(tmp, [("2026-10-28", flooded(2), 1.0, "VALIDATED"), ("2026-11-09", flooded(3), 1.6, "PROVISIONAL")])
        inp = B.load_inputs(tmp)
        _, rep1 = B.build_findings(inp, tmp, NOW)
        assert rep1["written"] == ["2026-10-28", "2026-11-09"] and not rep1["unchanged"]
        fdir = os.path.join(tmp, "data", "processed", "findings")
        raw1 = {n: open(os.path.join(fdir, n), "rb").read() for n in os.listdir(fdir)}
        stamp = {n: os.stat(os.path.join(fdir, n)).st_mtime_ns for n in ("2026-10-28.json", "2026-11-09.json")}
        # second run, later clock: date files are NOT rewritten (not even touched); latest.json is rebuilt with the new age
        latest2, rep2 = B.build_findings(B.load_inputs(tmp), tmp, B.parse_utc("2026-11-16T12:00:00Z"))
        assert rep2["unchanged"] == ["2026-10-28", "2026-11-09"] and not rep2["written"] and not rep2["revised"]
        for n in stamp:
            assert os.stat(os.path.join(fdir, n)).st_mtime_ns == stamp[n], n + " was rewritten"
            assert open(os.path.join(fdir, n), "rb").read() == raw1[n]
        assert latest2["age"]["days_since_pass"] == 7 and json.loads(raw1["latest.json"])["age"]["days_since_pass"] == 5
        # an input changes (the 9 Nov scene is upgraded PROVISIONAL -> VALIDATED): only that date is revised
        cat = B.jload(os.path.join(tmp, "data", "h5", "catalog.json"))
        for s in cat["scenes"]:
            if s["date"] == "2026-11-09":
                s["product_status"] = "VALIDATED"
        with open(os.path.join(tmp, "data", "h5", "catalog.json"), "w") as fh:
            json.dump(cat, fh)
        _, rep3 = B.build_findings(B.load_inputs(tmp), tmp, B.parse_utc("2026-11-17T08:00:00Z"))
        assert rep3["revised"] == ["2026-11-09"] and rep3["unchanged"] == ["2026-10-28"], rep3
        f = B.jload(os.path.join(fdir, "2026-11-09.json"))
        assert f["revision"] == 2 and len(f["revision_log"]) == 1 and f["revision_log"][0]["revision"] == 2
        assert "catalog" in f["revision_log"][0]["changed"] and f["pass"]["product_status"] == "VALIDATED"
        assert open(os.path.join(fdir, "2026-10-28.json"), "rb").read() == raw1["2026-10-28.json"]
        assert B.jload(os.path.join(fdir, "latest.json"))["revision"] == 2


# ---------------------------------------------------------------- rules
def test_quiet_rule():
    rules = B.jload(os.path.join(ROOT, "data", "story_rules.json"))
    info = lambda pct: {"new_water_pct_of_land": pct, "normal_new_water_pct_of_land": 0.04}
    rows = calm()
    c0 = B.compare(rows, rows, rules)
    assert B.is_quiet(rows, rows, c0, info(0.05), rules) is True
    assert B.is_quiet(rows, rows, c0, info(0.09), rules) is False, "new water above 2 x control"
    assert B.is_quiet(rows, rows, c0, None, rules) is False, "no control number: cannot call it quiet"
    fl = flooded(1)
    assert B.is_quiet(fl, None, B.compare(fl, None, rules), info(0.05), rules) is False, "a mandal crosses the flooded rule"
    up = copy_rows(rows)
    up[0]["water_pct"] = 2.5                                     # +2.3 points, error 0.5: went up, still below the flooded rule
    assert B.is_quiet(up, rows, B.compare(up, rows, rules), info(0.05), rules) is False, "a mandal went up"
    assert "rule_text" in rules["quiet"]


def test_radar_finding_matches_public_basis():
    """No mandal flooded and none went up -> no_clear_change, even when the new-water total is above a normal fortnight."""
    with tempfile.TemporaryDirectory() as tmp:
        make_root(tmp, [("2026-10-28", calm(), 0.15, "VALIDATED")])
        _, out = all_findings(tmp)
        f = out["2026-10-28"]
        assert f["headline_key"] == "no_flood" and f["template_state"] == "big_change"
        assert f["radar_finding"] == "no_clear_change", f["radar_finding"]
    with tempfile.TemporaryDirectory() as tmp:
        make_root(tmp, [("2026-10-28", flooded(2), 0.15, "VALIDATED")])
        _, out = all_findings(tmp)
        assert out["2026-10-28"]["radar_finding"] == "change_seen"
    assert B.radar_change_seen({"A": {"flooded": False, "trend": "up"}}) is True
    assert B.radar_change_seen({"A": {"flooded": False, "trend": "flat"}, "B": {"flooded": False, "trend": "new"}}) is False


def copy_rows(rows):
    return [dict(r) for r in rows]


def test_season_and_confidence():
    with tempfile.TemporaryDirectory() as tmp:
        make_root(tmp, [("2026-10-28", flooded(3), 1.6, "VALIDATED")], baseline_status="VALIDATED",
                  extra_catalog=[T.scene("2027-01-20"), T.scene("2027-07-10")])
        # extra passes have no numbers -> numbers_coming; confidence still follows the season rule
        inp, fs = all_findings(tmp)
        same = fs["2026-10-28"]
        assert same["confidence"] == {"level": "normal", "reasons": []} and same["template_state"] == "big_change"
        assert B.fill(inp["strings"]["caveat"]["season"]) not in same["sub"]
        dry = fs["2027-01-20"]                               # dry season is next to post-monsoon: lower
        assert dry["confidence"]["level"] == "lower" and any("post-monsoon" in r and "dry season" in r for r in dry["confidence"]["reasons"]), dry["confidence"]
        assert dry["template_state"] == "numbers_coming"
        mon = fs["2027-07-10"]                               # monsoon is next to post-monsoon: lower, not no_baseline
        assert mon["template_state"] == "numbers_coming" and mon["confidence"]["level"] == "lower"
    with tempfile.TemporaryDirectory() as tmp:
        make_root(tmp, [("2026-10-28", flooded(3), 1.6, "VALIDATED"), ("2027-01-20", flooded(3), 1.6, "VALIDATED")], baseline_status="VALIDATED")
        inp, fs = all_findings(tmp)
        f = fs["2027-01-20"]
        assert f["template_state"] in ("big_change", "quiet") and f["confidence"]["level"] == "lower"
        assert inp["strings"]["caveat"]["season"] in f["caveats"] and inp["strings"]["caveat"]["season"] in f["sub"]
        B.validate(f, inp["rules"])
    with tempfile.TemporaryDirectory() as tmp:                # provisional baseline alone lowers confidence
        make_root(tmp, [("2026-10-28", flooded(3), 1.6, "VALIDATED")], baseline_status="PROVISIONAL")
        inp, fs = all_findings(tmp)
        assert fs["2026-10-28"]["confidence"]["level"] == "lower" and "early data" in fs["2026-10-28"]["confidence"]["reasons"][0]
    # baselines are never shared between tracks, and without config/areas.json only the default track has one
    inp = B.load_inputs(ROOT)
    assert B.baseline_for(inp, 55) and B.baseline_for(inp, 128) is None
    inp["areas"] = None
    assert B.baseline_for(inp, 55)["season"] == "post_monsoon" and B.baseline_for(inp, 128) is None


def test_presentation_switch_never_changes_findings():
    """Findings keep every caveat (write-once, no revision); the switch only filters the public story/feed copy, in both states."""
    with tempfile.TemporaryDirectory() as tmp:
        make_root(tmp, [("2026-10-28", flooded(3), 1.6, "VALIDATED"), ("2027-01-20", flooded(3), 1.6, "VALIDATED")], baseline_status="PROVISIONAL")
        inp, fs = all_findings(tmp)
        f = fs["2027-01-20"]
        assert f["confidence"]["level"] == "lower" and f["caveats"], "findings data keeps the caveats"
        before = json.dumps(f, sort_keys=True)
        hidden = B.apply_presentation(f, B.presentation_cfg({"presentation": {"show_data_caveats": False}}), inp["strings"])
        shown = B.apply_presentation(f, B.presentation_cfg({"presentation": {"show_data_caveats": True}}), inp["strings"])
        assert json.dumps(f, sort_keys=True) == before, "the findings dict is not edited"
        season = inp["strings"]["caveat"]["season"]
        assert hidden["caveats"] == [] and hidden["confidence"] == {"level": "normal", "reasons": []} and season not in hidden["sub"]
        assert hidden["internal"]["caveats"] == f["caveats"] and hidden["internal"]["confidence"] == f["confidence"]
        assert season in hidden["internal"]["sub"]
        assert shown["caveats"] == f["caveats"] and season in shown["sub"] and shown["confidence"] == f["confidence"]
        for k in ("three_numbers", "comparison_line", "shown_numbers", "sources", "revision", "inputs_sha256"):
            assert hidden[k] == f[k] == shown[k], k
        B.validate(hidden, inp["rules"])
        B.validate(shown, inp["rules"])


def test_events_fallback_to_event_files():
    """No data/processed/events.json: the reader falls back to data/events/*.json and takes the window from the IMD bulletin dates."""
    with tempfile.TemporaryDirectory() as tmp:
        make_root(tmp, [("2026-10-28", flooded(2), 1.0, "VALIDATED")], events=False)
        os.makedirs(os.path.join(tmp, "data", "events"))
        os.makedirs(os.path.join(tmp, "docs", "imd_bulletins"))
        for n in ("20261027_1200UTC_x.pdf", "20261028_0300UTC_y.pdf"):
            open(os.path.join(tmp, "docs", "imd_bulletins", n), "w").close()
        ev = {"schema": "event-v1", "id": "arnab_2026", "name": EVENT_NAME, "status": "active", "dates": {"landfall_day": "2026-10-28"}, "landfall": {"date": "2026-10-28"},
              "imd": {"bulletin_dir": "docs/imd_bulletins"}, "confounders": [], "official_links": []}
        with open(os.path.join(tmp, "data", "events", "arnab-2026.json"), "w") as fh:
            json.dump(ev, fh)
        inp = B.load_inputs(tmp)
        assert inp["events"][0]["start"] == "2026-10-27" and inp["events"][0]["end"] == "2026-10-28"
        inp, fs = all_findings(tmp)
        assert fs["2026-10-28"]["event_chip"]["text"] == "During " + EVENT_NAME


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
