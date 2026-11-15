#!/usr/bin/env python3
"""Fixture tests for tools/pipeline/{alerts,events}.py. Plain asserts, no pytest:  python tools/tests/test_events.py
Cases: AP cyclone alert -> draft alert_only; pass inside window -> linked; pass outside -> not linked; Jammu & Kashmir
alert filtered out; idempotency; human event never rewritten / alert attached instead of duplicated; failed fetch keeps
previous items; set_radar_finding. No network, no real files touched (everything built in memory / a temp dir)."""
import copy
import json
import os
import sys
import tempfile
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools", "pipeline"))
import alerts as A  # noqa: E402
import events as E  # noqa: E402
import common  # noqa: E402

AR = common.area("godavari")
NOW = E.parse_now("2026-11-14T10:00Z")

AP_CYCLONE = {"id": "9001", "type": "TC", "name": "Tropical Cyclone TESTAP-26", "alert_level": "Orange",
              "from": "2026-11-12T00:00:00Z", "to": "2026-11-14T18:00:00Z", "link": "https://example.invalid/9001",
              "countries": "India", "lon": 82.0, "lat": 16.6}
JK_ALERT = {"id": "j1", "headline": "Heavy snow and cyclone-like winds likely over Srinagar, Baramulla.",
            "area": "Srinagar, Baramulla districts of Jammu and Kashmir", "issued": "2026-11-14T10:00:00+05:30",
            "source": "Jammu and Kashmir SDMA", "link": "https://example.invalid/j1", "category": "Met"}
AP_SACHET = {"id": "a1", "headline": "Heavy rain very likely over Konaseema and Kakinada.",
             "area": "Konaseema, Kakinada districts of Andhra Pradesh", "issued": "2026-11-14T10:00:00+05:30",
             "source": "IMD Amaravati", "link": "https://example.invalid/a1", "category": "Met"}
OUT_OF_BBOX_TC = {"id": "9002", "type": "TC", "name": "Tropical Cyclone FAR-26", "alert_level": "Red",
                  "from": "2026-11-12T00:00:00Z", "to": "2026-11-13T00:00:00Z", "link": None, "countries": "Japan",
                  "lon": 141.5, "lat": 29.4}


def scene(date, role="COAST", sid=None):
    return {"scene_id": sid or f"L_{role}_{date.replace('-', '')}", "role": role, "date": date, "track": 55}


def build_alerts(fixture, prev=None):
    return A.build("godavari", NOW, fixture, prev)


def run(doc, alerts, scenes, now=NOW):
    return E.update(doc, alerts, {"scenes": scenes}, AR, now)


def test_alerts_filter_by_area():
    d = build_alerts({"gdacs": [AP_CYCLONE, OUT_OF_BBOX_TC], "sachet": [JK_ALERT, AP_SACHET]})
    assert d["schema"] == "alerts-v2" and d["area_id"] == "godavari"
    assert [i["id"] for i in d["gdacs"]["items"]] == ["9001"], "Japan cyclone must be dropped, AP one kept"
    assert [i["id"] for i in d["sachet"]["items"]] == ["a1"], "Jammu & Kashmir alert must be filtered out"
    assert d["gdacs"]["ok"] and d["sachet"]["ok"] and d["gdacs"]["error"] is None
    assert d["gdacs"]["items"][0]["current"] is True


def test_sachet_keyword_is_whole_word():
    krishnagiri = dict(AP_SACHET, id="k1", headline="Rain over Krishnagiri.", area="Krishnagiri district of Tamil Nadu",
                       source="IMD Chennai")
    krishna = dict(AP_SACHET, id="k2", headline="Rain over Krishna.", area="Krishna district", source="IMD Chennai")
    d = build_alerts({"gdacs": [], "sachet": [krishnagiri, krishna]})
    assert [i["id"] for i in d["sachet"]["items"]] == ["k2"]


def test_failed_fetch_keeps_previous_items_with_real_timestamp():
    first = build_alerts({"gdacs": [AP_CYCLONE], "sachet": [AP_SACHET]})
    later = E.parse_now("2026-11-15T10:00Z")
    second = A.build("godavari", later, {"gdacs": {"fail": "HTTP 503"}, "sachet": {"fail": "timed out"}}, first)
    for src, stamp in (("gdacs", "fetched_utc"), ("sachet", "snapshot_utc")):
        assert second[src]["ok"] is False and second[src]["error"]
        assert second[src]["items"] == first[src]["items"], "previous items must survive a failed fetch"
        assert second[src][stamp] == first[src][stamp] == "2026-11-14T10:00:00Z", "timestamp must stay the real old one"
    assert second["built_utc"] == "2026-11-15T10:00:00Z"
    third = A.build("godavari", later, {"gdacs": {"fail": "x"}, "sachet": {"fail": "y"}}, None)
    assert third["gdacs"]["items"] == [] and third["gdacs"]["fetched_utc"] is None and third["gdacs"]["ok"] is False


def test_ap_cyclone_alert_makes_draft_alert_only():
    al = build_alerts({"gdacs": [AP_CYCLONE], "sachet": []})
    doc, ch = run(None, al, [])
    assert len(doc["events"]) == 1 and ch
    ev = doc["events"][0]
    assert ev["id"] == "auto_GDACS_9001" and ev["type"] == "cyclone" and ev["area_id"] == "godavari"
    assert ev["status"] == "alert_only" and ev["status_text"] == "Alert only, not yet seen by radar"
    assert ev["reviewed_by_human"] is False and ev["linked_passes"] == []
    assert ev["start"] == "2026-11-12" and ev["end"] == "2026-11-14" and ev["aftermath_days"] == 30
    assert ev["severity"] == {"as_given": "Orange alert", "by": "GDACS"}
    assert ev["alert_refs"][0]["source"] == "GDACS" and ev["edit_log"][0]["by"] == "pipeline"
    assert "confirm" not in json.dumps(ev).lower() or "not" in ev["status_text"].lower()


def test_jk_alert_makes_no_event():
    al = build_alerts({"gdacs": [], "sachet": [JK_ALERT]})
    doc, ch = run(None, al, [])
    assert doc["events"] == [] and ch == []


def test_pass_inside_window_links_and_outside_does_not():
    al = build_alerts({"gdacs": [AP_CYCLONE], "sachet": []})
    inside = scene("2026-11-20")            # end 14 Nov + 6 days
    during = scene("2026-11-13", "SEA")
    last_day = scene("2026-12-14")          # end + 30 days exactly: still inside
    too_late = scene("2026-12-15")          # end + 31 days
    before = scene("2026-11-11")            # before start (12 Nov)
    doc, _ = run(None, al, [inside, during, last_day, too_late, before])
    ev = doc["events"][0]
    got = {lp["scene_id"]: lp for lp in ev["linked_passes"]}
    assert set(got) == {inside["scene_id"], during["scene_id"], last_day["scene_id"]}, sorted(got)
    assert got[inside["scene_id"]]["relation"] == "after" and got[during["scene_id"]]["relation"] == "during"
    assert got[inside["scene_id"]]["radar_finding"] == "numbers_coming"
    assert got[during["scene_id"]]["radar_finding"] == "sea_no_public_finding"
    assert ev["status"] == "radar_linked" and ev["status_text"] == "Radar passes linked"


def test_pass_outside_window_leaves_alert_only():
    al = build_alerts({"gdacs": [AP_CYCLONE], "sachet": []})
    doc, _ = run(None, al, [scene("2026-10-04"), scene("2027-01-30")])
    ev = doc["events"][0]
    assert ev["linked_passes"] == [] and ev["status"] == "alert_only"


def test_idempotent():
    al = build_alerts({"gdacs": [AP_CYCLONE], "sachet": [AP_SACHET]})
    sc = [scene("2026-11-20")]
    d1, _ = run(None, al, sc)
    d2, ch2 = run(d1, al, sc, E.parse_now("2026-11-14T10:00Z"))
    assert ch2 == [], ch2
    assert d2 == d1, "same inputs + same --now must give an identical file"
    d3, ch3 = run(d1, al, sc, E.parse_now("2026-11-14T18:00Z"))
    assert ch3 == [] and E.strip_stamp(d3) == E.strip_stamp(d1), "a later run changes only updated_utc"
    assert d3["updated_utc"] != d1["updated_utc"]


def test_human_event_never_rewritten_or_duplicated():
    human = {"id": "arnab_like", "name": "Cyclone X", "type": "cyclone", "area_id": "godavari", "start": "2026-11-11",
             "end": "2026-11-14", "aftermath_days": 30, "window_source": "test", "status": "radar_linked",
             "status_text": "Radar passes linked", "reviewed_by_human": True, "linked_passes": [], "alert_refs": [],
             "edit_log": [], "description": "keep me", "severity": {"as_given": "VSCS", "by": "IMD"}}
    doc = {"schema": "events-v1", "updated_utc": None, "events": [copy.deepcopy(human)]}
    al = build_alerts({"gdacs": [AP_CYCLONE], "sachet": []})
    out, _ = run(doc, al, [scene("2026-11-20")])
    assert [e["id"] for e in out["events"]] == ["arnab_like"], "the alert must attach to the human event, no duplicate"
    ev = out["events"][0]
    assert ev["description"] == "keep me" and ev["severity"] == human["severity"] and ev["start"] == "2026-11-11"
    assert ev["alert_refs"][0]["id"] == "9001" and len(ev["linked_passes"]) == 1
    gone, _ = run(out, build_alerts({"gdacs": [], "sachet": []}), [], NOW)
    assert [e["id"] for e in gone["events"]] == ["arnab_like"], "events are never deleted when the alert disappears"


def test_other_area_events_untouched():
    other = {"id": "elsewhere", "name": "E", "type": "cyclone", "area_id": "odisha_test", "start": "2026-11-11",
             "end": "2026-11-14", "aftermath_days": 30, "status": "alert_only", "status_text": "x",
             "reviewed_by_human": False, "linked_passes": [], "alert_refs": [], "edit_log": []}
    doc = {"schema": "events-v1", "updated_utc": None, "events": [other]}
    out, _ = run(doc, build_alerts({"gdacs": [], "sachet": []}), [scene("2026-11-12")])
    assert out["events"][0] == other


def test_set_radar_finding():
    al = build_alerts({"gdacs": [AP_CYCLONE], "sachet": []})
    sc = scene("2026-11-20")
    doc, _ = run(None, al, [sc])
    assert E.set_radar_finding(doc, "auto_GDACS_9001", sc["scene_id"], "no_clear_change", NOW, by="findings") is True
    lp = doc["events"][0]["linked_passes"][0]
    assert lp["radar_finding"] == "no_clear_change" and doc["events"][0]["edit_log"][-1]["by"] == "findings"
    assert E.set_radar_finding(doc, "auto_GDACS_9001", sc["scene_id"], "no_clear_change", NOW) is False
    assert E.set_radar_finding(doc, "nope", sc["scene_id"], "change_seen") is False
    try:
        E.set_radar_finding(doc, "auto_GDACS_9001", sc["scene_id"], "radar confirms the alert")
        raise AssertionError("bad finding value accepted")
    except ValueError:
        pass
    again, ch = run(doc, al, [sc])
    assert again["events"][0]["linked_passes"][0]["radar_finding"] == "no_clear_change", "a run must keep the finding"


def test_old_alert_does_not_create_draft():
    old = dict(AP_CYCLONE, id="9003", **{"from": "2026-09-22T18:00:00Z", "to": "2026-09-24T00:00:00Z"})
    doc, ch = run(None, build_alerts({"gdacs": [old], "sachet": []}), [])
    assert doc["events"] == []


# ---------- P2-A: floods (GDACS FL) ----------
def fx(name):
    with open(os.path.join(HERE, "fixtures", name)) as f:
        return json.load(f)


FL_SCENES = [scene("2026-10-27", "SEA"), scene("2026-10-28"), scene("2026-11-09")]


def test_fl_inside_box_makes_draft_and_links():
    al = build_alerts(fx("gdacs_fl_inside.json"))
    item = al["gdacs"]["items"][0]
    assert item["type"] == "FL" and item["source"] == "GLOFAS" and item["affected_bbox"] == [82.0, 16.6, 82.2, 16.8]
    doc, _ = run(None, al, FL_SCENES)
    ev = doc["events"][0]
    assert ev["id"] == "auto_GDACS_7001" and ev["type"] == "flood" and ev["reviewed_by_human"] is False
    assert ev["footprint"]["distance_km"] == 0 and ev["footprint"]["basis"] == "affected_area"
    assert len(ev["linked_passes"]) == 3 and ev["status"] == "radar_linked"
    txt = " ".join(ev["cannot_tell"])
    assert "river-flow model (GloFAS)" in txt and "not a flood map" in txt and "overlaps the radar area" in txt, txt


def test_fl_like_1104248_outside_makes_draft_without_links():
    al = build_alerts(fx("gdacs_fl_outside.json"))
    assert [i["id"] for i in al["gdacs"]["items"]] == ["1104248"]
    doc, _ = run(None, al, FL_SCENES)
    ev = doc["events"][0]
    assert ev["id"] == "auto_GDACS_1104248"
    assert ev["linked_passes"] == [] and ev["status"] == "alert_only"
    assert ev["status_text"] == "Alert only, outside the radar area"
    assert ev["footprint"]["distance_km"] > 100, ev["footprint"]
    txt = " ".join(ev["cannot_tell"])
    assert "km from the radar area" in txt and "model" in txt and "not confirmed by radar" in txt, txt
    assert ar_default_km() == 50
    # an old draft that was linked before this rule loses its links on the next run (drafts only, logged)
    old = copy.deepcopy(doc)
    old["events"][0].pop("footprint")
    old["events"][0]["linked_passes"] = [{"scene_id": "L_COAST_20261028", "date": "2026-10-28", "role": "COAST",
                                          "relation": "during", "radar_finding": "no_clear_change"}]
    old["events"][0]["status"], old["events"][0]["status_text"] = "radar_linked", "Radar passes linked"
    fixed, ch = run(old, al, FL_SCENES)
    ev2 = fixed["events"][0]
    assert ev2["linked_passes"] == [] and ev2["status"] == "alert_only" and ch
    assert any("removed 1 linked pass" in x["what"] for x in ev2["edit_log"])


def ar_default_km():
    return AR["_defaults"]["flood_link_km"]


def test_fl_failed_footprint_fetch_uses_centroid_rule():
    real = A.http_get
    try:
        def boom(url, timeout=40):
            raise OSError("geometry request failed")
        A.http_get = boom
        assert A.fetch_affected_bbox("https://example.invalid/geometry") is None
        assert A.fetch_affected_bbox(None) is None
    finally:
        A.http_get = real
    al = build_alerts(fx("gdacs_fl_centroid_only.json"))
    assert all(i["affected_bbox"] is None for i in al["gdacs"]["items"])
    doc, _ = run(None, al, FL_SCENES)
    by = {e["id"]: e for e in doc["events"]}
    far, near = by["auto_GDACS_7003"], by["auto_GDACS_7004"]
    assert far["footprint"]["basis"] == "point" and 50 < far["footprint"]["distance_km"] < 100
    assert far["linked_passes"] == [] and far["status_text"] == "Alert only, outside the radar area"
    assert near["footprint"]["basis"] == "point" and 0 < near["footprint"]["distance_km"] <= 50
    assert len(near["linked_passes"]) == 3 and near["status"] == "radar_linked"


def test_human_flood_event_absorbs_fl_alert():
    human = {"id": "flood_review", "name": "Flood X", "type": "flood", "area_id": "godavari", "start": "2026-10-19",
             "end": "2026-11-03", "aftermath_days": 30, "window_source": "test", "status": "radar_linked",
             "status_text": "Radar passes linked", "reviewed_by_human": True, "linked_passes": [], "alert_refs": [],
             "edit_log": [], "description": "keep me", "severity": {"as_given": "x", "by": "y"}}
    doc = {"schema": "events-v1", "updated_utc": None, "events": [copy.deepcopy(human)]}
    out, _ = run(doc, build_alerts(fx("gdacs_fl_outside.json")), FL_SCENES)
    assert [e["id"] for e in out["events"]] == ["flood_review"], "FL alert must attach to the human event"
    ev = out["events"][0]
    assert ev["alert_refs"][0]["id"] == "1104248" and ev["description"] == "keep me"
    assert "footprint" not in ev and len(ev["linked_passes"]) == 3, "a reviewed event is linked by its own window, never guarded"


def test_fl_idempotent_second_run():
    for name in ("gdacs_fl_inside.json", "gdacs_fl_outside.json", "gdacs_fl_centroid_only.json"):
        al = build_alerts(fx(name))
        d1, _ = run(None, al, FL_SCENES)
        d2, ch2 = run(d1, al, FL_SCENES)
        assert ch2 == [] and d2 == d1, (name, ch2)
        d3, ch3 = run(d1, al, FL_SCENES, E.parse_now("2026-11-14T18:00Z"))
        assert ch3 == [] and E.strip_stamp(d3) == E.strip_stamp(d1), name


def test_real_files_validate():
    import importlib.util
    spec = importlib.util.spec_from_file_location("cm", os.path.join(ROOT, "tools", "check_manifest.py"))
    cm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cm)
    al = build_alerts({"gdacs": [AP_CYCLONE], "sachet": [AP_SACHET]})
    assert cm.alerts_v2_errors(al) == [], cm.alerts_v2_errors(al)
    doc, _ = run(None, al, [scene("2026-11-20")])
    assert cm.events_v1_errors(doc) == [], cm.events_v1_errors(doc)
    p = os.path.join(ROOT, "data", "processed", "events.json")
    if os.path.exists(p):
        assert cm.events_v1_errors(json.load(open(p))) == []


def test_discover_only_ingests_configured_tracks():
    import discover as D
    def sc(role, track, date):
        return {"role": role, "track": track, "date": date, "scene_key": common.scene_key(role, date, track), "status": "VALIDATED"}
    scenes = [sc("SEA", 48, "2026-12-01"), sc("SEA", 120, "2026-12-02"), sc("SEA", 127, "2026-12-02"), sc("COAST", 55, "2026-12-03"), sc("COAST", 62, "2026-12-03")]
    with tempfile.TemporaryDirectory() as tmp:
        cat = os.path.join(tmp, "catalog.json")
        json.dump({"scenes": []}, open(cat, "w"))
        new, up, known, other = D.compare(scenes, cat, None, AR)
    assert sorted((x["role"], x["track"]) for x in new) == [("COAST", 55), ("SEA", 48)], new
    assert sorted((x["role"], x["track"]) for x in other) == [("COAST", 62), ("SEA", 120), ("SEA", 127)], other


def main():
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for n, f in tests:
        try:
            f()
            print("PASS", n)
        except Exception:  # noqa: BLE001
            failed += 1
            print("FAIL", n)
            traceback.print_exc()
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
