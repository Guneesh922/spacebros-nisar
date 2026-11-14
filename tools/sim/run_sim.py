#!/usr/bin/env python3
"""Simulate what the pipeline does when something new (or nothing) happens. NEVER runs in the real repo: it copies the repo to
<out>/repo (rsync, without .git .venv data/raw node_modules), injects fake inputs there, runs tools/pipeline/run_all.py --offline
with a fixed --now, and prints / saves a report.

  python tools/sim/run_sim.py <scenario> --out <dir> [--reports <dir>] [--keep]

Scenarios (all fake passes are labelled: source_granule ends in _SIMULATED):
  new_pass_change     21 Nov = copy of 9 Nov, HH/HV lowered by 8 dB over 4 inland mandals -> new water there
  copy_of_last_pass   21 Nov = copy of 9 Nov, only attributes changed (the quiet rule needs NO flooded mandal: see the report)
  quiet_pass_calm     21 Nov and 3 Dec = copies of the calm 16 Oct baseline scene (two calm passes in a row -> quiet on 3 Dec)
  missing_pass        no new file, --now 2026-12-05 -> no_new_pass with the age
  analysis_failed     21 Nov = copy of 9 Nov with corrupt data chunks (opens, but cannot be read) -> numbers_coming
  analysis_truncated  21 Nov = copy of 9 Nov cut short (does not open at all) -> left out of the catalogue, warning, rest of the run fine
  no_baseline         fake pass on track 62 -> no_baseline
  ap_alert            fake GDACS cyclone alert over the delta, 18-20 Nov + scenario new_pass_change pass
  ap_alert_quiet      same alert + scenario copy_of_last_pass (copy of 9 Nov)
  ap_alert_calm       same alert + scenario quiet_pass_calm
The report lists: headline, template_state, three numbers, top 5 mandals, pass list, chips, events, files changed, the
number-versus-source check and a guard that the real repo was not touched.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REAL = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REAL / "tools"))
sys.path.insert(0, str(REAL / "tools" / "pipeline"))

NOW = {"new_pass_change": "2026-11-21T10:00Z", "copy_of_last_pass": "2026-11-21T10:00Z", "quiet_pass_calm": "2026-12-04T10:00Z",
       "missing_pass": "2026-12-05T10:00Z", "analysis_failed": "2026-11-21T10:00Z", "analysis_truncated": "2026-11-21T10:00Z",
       "no_baseline": "2026-11-21T10:00Z", "ap_alert": "2026-11-22T10:00Z", "ap_alert_quiet": "2026-11-22T10:00Z",
       "ap_alert_calm": "2026-12-04T10:00Z"}
DARK_MANDALS = ["Alamuru", "Ravulapalem", "Kothapeta", "Atreyapuram"]   # inland of Amalapuram, little water on 9 Nov
DROP = -800                                                             # int16 units = -8 dB
ALERT = {"gdacs": [{"id": "9100001", "type": "TC", "name": "Tropical Cyclone SIMCY-26", "alert_level": "Orange",
                    "from": "2026-11-18T00:00:00Z", "to": "2026-11-20T12:00:00Z", "link": "https://example.invalid/sim-alert",
                    "countries": "India", "lon": 82.0, "lat": 16.6}], "sachet": []}


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def snap(root, only=("data/h5", "data/processed", "data/web", "config")):
    out = {}
    for w in only:
        b = Path(root) / w
        for p in sorted(b.rglob("*")) if b.exists() else []:
            if p.is_file() and "/img/" not in p.as_posix():
                out[p.relative_to(root).as_posix()] = sha_file(p)
    return out


def guard_snapshot():
    """what must not change in the real repo while a simulation runs"""
    out = {}
    for w in ("data/h5", "data/processed/findings", "data/processed/events.json", "data/processed/alerts.json",
              "data/processed/manifest.json", "config"):
        b = REAL / w
        files = [b] if b.is_file() else sorted(x for x in b.rglob("*") if x.is_file())
        for p in files:
            out[p.relative_to(REAL).as_posix()] = sha_file(p)
    return out


# ----------------------------------------------------------------------------- injection
def copy_repo(dst):
    dst = Path(dst)
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    subprocess.run(["rsync", "-a", "--exclude", ".git", "--exclude", ".venv", "--exclude", "data/raw", "--exclude", "node_modules",
                    str(REAL) + "/", str(dst) + "/"], check=True)


def clone_scene(root, src_name, dst_name, date, scene_id, start="00:01:07", track=None):
    import h5py
    src, dst = Path(root) / "data" / "h5" / src_name, Path(root) / "data" / "h5" / dst_name
    shutil.copyfile(src, dst)
    with h5py.File(dst, "r+") as h:
        end = (dt.datetime.strptime(start, "%H:%M:%S") + dt.timedelta(seconds=23)).strftime("%H:%M:%S")
        h.attrs["scene_id"] = scene_id
        h.attrs["start_utc"] = "%sT%sZ" % (date, start)
        h.attrs["end_utc"] = "%sT%sZ" % (date, end)
        h.attrs["created_utc"] = date + "T06:00:00Z"
        h.attrs["source_granule"] = str(h.attrs["source_granule"]) + "_SIMULATED"
        if track is not None:
            h.attrs["track"] = track
    return dst


def darken(path, root, names, drop=DROP):
    """Lower HH and HV by `drop` (int16 units, keep the fill value) inside the named mandals' polygons."""
    import h5py
    import numpy as np
    from PIL import Image, ImageDraw
    from pyproj import Transformer
    gj = json.load(open(Path(root) / "data" / "processed" / "mandals.geojson"))
    with h5py.File(path, "r+") as h:
        x, y = h["grid/x"][...], h["grid/y"][...]
        tr = Transformer.from_crs(4326, int(h["grid/x"].attrs["epsg"]), always_xy=True)
        dx, dy = (x[-1] - x[0]) / (len(x) - 1), (y[-1] - y[0]) / (len(y) - 1)
        mask = Image.new("L", (len(x), len(y)), 0)
        dr = ImageDraw.Draw(mask)
        found = []
        for f in gj["features"]:
            if f["properties"]["name"] not in names:
                continue
            found.append(f["properties"]["name"])
            g = f["geometry"]
            polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
            for poly in polys:
                for ring in poly[:1]:
                    px = [tr.transform(lon, lat) for lon, lat in ring]
                    dr.polygon([((u - x[0]) / dx, (v - y[0]) / dy) for u, v in px], fill=1)
        m = np.array(mask, dtype=bool)
        n = 0
        for pol in ("HH", "HV"):
            a = h["backscatter/" + pol][...]
            sel = m & (a != -32768)
            a[sel] = np.maximum(a[sel].astype(np.int32) + drop, -32767).astype(np.int16)
            h["backscatter/" + pol][...] = a
            n = int(sel.sum())
    return found, n


def corrupt_chunks(path, n=24, seed=0):
    import h5py
    import numpy as np
    rng = np.random.RandomState(seed)
    spots = []
    with h5py.File(path, "r") as h:
        for pol in ("HH", "HV"):
            d = h["backscatter/" + pol]
            nc = d.id.get_num_chunks()
            for i in rng.choice(nc, size=min(n, nc), replace=False):
                info = d.id.get_chunk_info(int(i))
                spots.append((info.byte_offset, info.size))
    with open(path, "r+b") as f:
        for off, size in spots:
            f.seek(off)
            f.write(rng.bytes(size))
    return len(spots)


def read_test(path):
    """('ok'|'unreadable data'|'does not open', message)"""
    import h5py
    try:
        with h5py.File(path, "r") as h:
            try:
                h["backscatter/HH"][...]
                return "ok", ""
            except Exception as e:  # noqa: BLE001
                return "attributes open but data unreadable", "%s: %s" % (type(e).__name__, str(e)[:80])
    except Exception as e:  # noqa: BLE001
        return "does not open at all", "%s: %s" % (type(e).__name__, str(e)[:80])


def inject(scn, root):
    notes = []
    h5 = "data/h5/"
    if scn in ("new_pass_change", "ap_alert"):
        p = clone_scene(root, "L_COAST_20261109_T055.h5", "L_COAST_20261121_T055.h5", "2026-11-21", "L_COAST_1121")
        found, n = darken(p, root, DARK_MANDALS)
        notes.append("fake %s = copy of 9 Nov, attrs updated, HH/HV %+d dB over %d px inside mandals %s" % (p.name, DROP / 100, n, found))
    elif scn in ("copy_of_last_pass", "ap_alert_quiet"):
        p = clone_scene(root, "L_COAST_20261109_T055.h5", "L_COAST_20261121_T055.h5", "2026-11-21", "L_COAST_1121")
        notes.append("fake %s = copy of 9 Nov, only attributes changed" % p.name)
    elif scn in ("quiet_pass_calm", "ap_alert_calm"):
        p1 = clone_scene(root, "L_COAST_20261016_T055.h5", "L_COAST_20261121_T055.h5", "2026-11-21", "L_COAST_1121")
        p2 = clone_scene(root, "L_COAST_20261016_T055.h5", "L_COAST_20261203_T055.h5", "2026-12-03", "L_COAST_1203")
        notes.append("fake %s and %s = copies of the calm 16 Oct baseline scene, attributes changed" % (p1.name, p2.name))
    elif scn == "analysis_failed":
        p = clone_scene(root, "L_COAST_20261109_T055.h5", "L_COAST_20261121_T055.h5", "2026-11-21", "L_COAST_1121")
        k = corrupt_chunks(p)
        notes.append("fake %s = copy of 9 Nov with %d data chunks overwritten by random bytes; read test: %s" % (p.name, k, read_test(p)))
    elif scn == "analysis_truncated":
        p = clone_scene(root, "L_COAST_20261109_T055.h5", "L_COAST_20261121_T055.h5", "2026-11-21", "L_COAST_1121")
        size = p.stat().st_size
        with open(p, "r+b") as f:
            f.truncate(int(size * 0.6))
        notes.append("fake %s = copy of 9 Nov cut to 60 %% of its size; read test: %s" % (p.name, read_test(p)))
    elif scn == "no_baseline":
        p = clone_scene(root, "L_COAST_20261109_T055.h5", "L_COAST_20261121_T062.h5", "2026-11-21", "L_COAST_1121_T62", start="11:05:40", track=62)
        notes.append("fake %s = copy of 9 Nov relabelled track 62 (no baseline configured for track 62)" % p.name)
    elif scn == "missing_pass":
        notes.append("no new file; clock set to 5 Dec")
    else:
        raise SystemExit("unknown scenario %r" % scn)
    fx = None
    if scn.startswith("ap_alert"):
        fx = Path(root).parent / ("alerts_fixture_%s.json" % scn)
        fx.write_text(json.dumps(ALERT, indent=1))
        notes.append("alerts fixture: GDACS TC 'SIMCY-26' Orange, 18-20 Nov 2026, point 82.0E 16.6N (inside the delta); not a real alert")
    return notes, fx


# ----------------------------------------------------------------------------- report
def jload(p, d=None):
    try:
        return json.load(open(p))
    except (OSError, ValueError):
        return d


def number_check(root):
    """Every shown number of every findings file must equal the value at its source path in the stats files."""
    import build_story as B
    rules = jload(Path(root) / "data" / "story_rules.json")
    res, bad = [], 0
    for f in sorted((Path(root) / "data" / "processed" / "findings").glob("*.json")):
        d = jload(f)
        cache, n, errs = {}, 0, []
        for x in d.get("shown_numbers") or []:
            try:
                got = B.resolve_source(x["source"], str(root), rules, cache)
                ok = abs(got - x["raw"]) < 0.011 and B.FMT[x["fmt"]](x["raw"]) == x["text"]
            except Exception as e:  # noqa: BLE001
                ok, got = False, "%s" % e
            n += 1
            if not ok:
                errs.append("%s: shown %r raw %r, source says %r" % (x["key"], x["text"], x["raw"], got))
        for t in d.get("three_numbers") or []:
            sv = next((s for s in d["shown_numbers"] if s["key"] == "three_numbers[%d].value" % d["three_numbers"].index(t)), None)
            if sv is None or float(sv["text"]) != float(t["value"]):
                errs.append("three_numbers %s not registered" % t["id"])
        if d.get("template_state") in ("numbers_coming", "no_baseline"):
            if d.get("three_numbers") or d.get("big_numbers") or d.get("comparison_line"):
                errs.append("state %s but numbers are shown" % d["template_state"])
        res.append((f.name, n, errs))
        bad += len(errs)
    return res, bad


def report(scn, root, notes, summary, code, before, guard_ok, guard_diff, sha9_before, now):
    root = Path(root)
    L = []
    P = L.append
    P("SIMULATION %s   (clock set to %s; fake data only, run in a scratch copy; a settle run on the untouched copy came first)" % (scn, now))
    for n in notes:
        P("  inject: " + n)
    P("")
    P("run_all exit code %s | tests_ok %s | deployable %s | seconds %s" % (code, summary.get("tests_ok"), summary.get("deployable"), summary.get("seconds")))
    for s in summary.get("steps", []):
        P("  step %-14s %-11s %6.1fs  %s" % (s["step"], s["result"], s["seconds"], (s["detail"] or "")[:110]))
    for w in summary.get("warnings", []):
        P("  WARNING: " + w[:200])
    for e in summary.get("errors", []):
        P("  ERROR: " + e[:200])
    P("")
    lat = jload(root / "data" / "processed" / "findings" / "latest.json", {})
    P("LATEST (findings/latest.json)")
    P("  template_state : %s   radar_finding: %s   state: %s" % (lat.get("template_state"), lat.get("radar_finding"), lat.get("state")))
    P("  headline       : %s" % lat.get("headline"))
    P("  lead           : %s" % lat.get("lead"))
    P("  comparison     : %s" % lat.get("comparison_line"))
    P("  age            : %s" % (lat.get("age") or {}).get("text"))
    P("  pass           : %s" % json.dumps(lat.get("pass")))
    P("  three_numbers  : %s" % ("; ".join("%s %s%s (+-%s) [%s]" % (t["value"], t["unit"], "", t.get("err", "-"), t["source"]) for t in lat.get("three_numbers") or []) or "none"))
    P("  big_numbers    : %s" % ("; ".join("%s %s - %s" % (b["value"], b["unit"], b["label"]) for b in lat.get("big_numbers") or []) or "none"))
    P("  since_last     : %s" % ((lat.get("since_last") or {}).get("text")))
    P("  confidence     : %s" % json.dumps(lat.get("confidence")))
    P("  next pass      : %s" % ((lat.get("next_pass") or {}).get("text")))
    P("  event_chip     : %s" % json.dumps(lat.get("event_chip")))
    P("  event_chips    : %s" % json.dumps([c["text"] for c in lat.get("event_chips") or []]))
    rank = jload(root / "data" / "processed" / "mandal_rank.json", {})
    by = rank.get("by_date") or {}
    last = sorted(by)[-1] if by else None
    P("")
    P("TOP 5 MANDALS by open water (mandal_rank.json by_date.%s; scene %s)" % (last, by.get(last, {}).get("scene_id")))
    rows = sorted([r for r in (by.get(last, {}).get("rows") or []) if r.get("rank_water")], key=lambda r: r["rank_water"])[:5]
    for r in rows:
        P("  #%-3s %-14s water %5.1f%% (+-%.1f)  normal %.2f%%  flooded km2 %s  coverage %s%%" % (r["rank_water"], r["mandal"], r["water_pct"], r.get("err") or 0, r.get("normal_water_pct") or 0, r.get("flooded_km2"), r.get("coverage_pct")))
    P("")
    P("PASS LIST / TIMELINE")
    for f in sorted((root / "data" / "processed" / "findings").glob("20*.json")):
        d = jload(f)
        P("  findings/%s  rev %s  %-14s %s | chips: %s" % (f.name, d.get("revision"), d.get("template_state"), d.get("headline"), "; ".join(c["text"] for c in d.get("event_chips") or []) or "-"))
    story = jload(root / "data" / "web" / "story.json", {})
    P("  story.json updates (archive): " + ", ".join("%s:%s" % (u["date"], u["kind"]) for u in story.get("updates") or []))
    cat = jload(root / "data" / "h5" / "catalog.json", {})
    P("  catalogue scenes: " + ", ".join("%s%s" % (s["scene_id"], "" if s["product_status"] == "VALIDATED" else "(PROV)") for s in cat.get("scenes") or []))
    P("")
    P("EVENTS (data/processed/events.json)")
    ev = jload(root / "data" / "processed" / "events.json", {})
    for e in ev.get("events") or []:
        P("  %-22s %-12s reviewed=%-5s %s..%s | %s" % (e["id"], e["status"], e.get("reviewed_by_human"), e["start"], e["end"], e.get("status_text")))
        for lp in e.get("linked_passes") or []:
            if lp["role"] == "COAST":
                P("      linked %s (%s) radar_finding=%s" % (lp["scene_id"], lp["relation"], lp["radar_finding"]))
    P("  events idempotent on second run: %s" % summary.get("events_idempotent"))
    P("")
    P("FILES CHANGED by the run (sha256 differs from the copy; the fake injected files show as ADDED)")
    after = snap(root)
    for k in sorted(set(before) | set(after)):
        if before.get(k) != after.get(k) and not k.startswith("data/web/") or (k.startswith("data/web/") and k.endswith((".json", ".xml")) and before.get(k) != after.get(k)):
            P("  %-8s %s" % ("ADDED" if k not in before else "REMOVED" if k not in after else "CHANGED", k))
    pngs = sum(1 for k in set(before) | set(after) if k.endswith(".png") and before.get(k) != after.get(k))
    P("  (+ %d PNG display files under data/web rebuilt)" % pngs)
    sha9_after = after.get("data/processed/findings/2026-11-09.json")
    P("")
    P("ARCHIVE: findings/2026-11-09.json sha256 before %s | after %s | %s" % (sha9_before and sha9_before[:16], sha9_after and sha9_after[:16],
      "BYTE-IDENTICAL" if sha9_before == sha9_after else "CHANGED (see revision_log)"))
    P("")
    res, bad = number_check(root)
    P("NUMBER-VS-SOURCE CHECK (every shown number re-read from its stats file): %s" % ("PASS" if bad == 0 else "FAIL (%d)" % bad))
    for name, n, errs in res:
        P("  %-18s %3d numbers checked%s" % (name, n, "" if not errs else "  ERRORS: " + " | ".join(errs)))
    P("")
    P("REAL REPO GUARD (data/h5, findings, events.json, alerts.json, manifest.json, config in %s): %s" % (REAL, "UNCHANGED" if guard_ok else "CHANGED: %s" % guard_diff))
    return "\n".join(L) + "\n", bad


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scenario", choices=sorted(NOW))
    ap.add_argument("--out", required=True, help="scratch directory for this scenario (the copy goes to <out>/repo)")
    ap.add_argument("--reports", default=None, help="where <scenario>.txt and <scenario>.summary.json go (default <out>/../reports)")
    a = ap.parse_args()
    out = Path(a.out).resolve()
    if REAL in out.parents or out == REAL:
        raise SystemExit("refusing: --out must be OUTSIDE the real repo")
    reports = Path(a.reports) if a.reports else out.parent / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    g0 = guard_snapshot()
    root = out / "repo"
    print("copying repo -> %s" % root, flush=True)
    copy_repo(root)
    env = dict(os.environ)
    env.pop("EARTHDATA_TOKEN", None)
    env["SPACEBROS_AREAS"] = str(root / "config" / "areas.json")
    # settle run: one ordinary offline run on the untouched copy = the state the repo is in after yesterday's daily run. Without it the
    # local data/web build products (git-ignored, may be older than the code) would make the archive look 'revised' in every scenario.
    settle = subprocess.run([sys.executable, str(root / "tools" / "pipeline" / "run_all.py"), "--root", str(root), "--offline",
                             "--now", "2026-11-14T15:00Z", "--summary", str(reports / ("%s.settle.summary.json" % a.scenario))],
                            cwd=root, env=env, text=True, capture_output=True)
    (reports / ("%s.settle.log" % a.scenario)).write_text(settle.stdout + settle.stderr)
    print("settle run (steady state before the scenario): exit %d" % settle.returncode, flush=True)
    sha9_before = sha_file(root / "data" / "processed" / "findings" / "2026-11-09.json")
    before = snap(root)
    notes, fx = inject(a.scenario, root)
    now = NOW[a.scenario]
    summ = reports / ("%s.summary.json" % a.scenario)
    cmd = [sys.executable, str(root / "tools" / "pipeline" / "run_all.py"), "--root", str(root), "--offline", "--now", now, "--summary", str(summ)]
    if fx:
        cmd += ["--alerts-fixture", str(fx)]
    print("running: run_all.py --offline --now %s" % now, flush=True)
    r = subprocess.run(cmd, cwd=root, env=env, text=True, capture_output=True)
    (reports / ("%s.run_all.log" % a.scenario)).write_text(r.stdout + r.stderr)
    summary = jload(summ, {})
    g1 = guard_snapshot()
    diff = sorted(k for k in set(g0) | set(g1) if g0.get(k) != g1.get(k))
    text, bad = report(a.scenario, root, notes, summary, r.returncode, before, not diff, diff, sha9_before, now)
    (reports / ("%s.txt" % a.scenario)).write_text(text)
    print(text)
    return 0 if (not diff and bad == 0) else 3


if __name__ == "__main__":
    sys.exit(main())
