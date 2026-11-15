#!/usr/bin/env python3
"""run_all.py: the ONE place that holds the order of the update pipeline. The daily Action (update.yml) and the local
simulations (tools/sim/) both call this file; nothing else knows the order.

Steps, in order (each is logged with duration and result):
   1 discover      CMR search for new NISAR scenes (public)            [skipped with --offline]
   2 ingest        stream-subset the new scenes into data/h5/           [only if discover found some; needs EARTHDATA_TOKEN; skipped with --offline / --skip-ingest]
   3 verify_h5     every data/h5/*.h5 must open; an unopenable file is left out of the catalogue and reported (warning)
   4 catalog       data/h5/catalog.json from the H5 attributes
   5 sync_manifest manifest layers for new scenes
   6 alerts        GDACS + SACHET -> data/processed/alerts.json         [--offline: from --alerts-fixture, else the old file is kept]
   7 events        draft events from alerts + radar links               -> data/processed/events.json
   8 build_web     display PNGs, class maps, mandal_rank.json, profile.json (a failure here is a WARNING: the pass that could not be
                   analysed gets "numbers_coming" in step 10; numbers of an older pass are never shown as new)
   9 tests         tools/tests/test_story.py, test_findings.py, test_events.py, tools/check_manifest.py. ANY failure -> exit 2:
                   findings are NOT written (the old ones stay), nothing is deployable.
  10 build_story   findings/<date>.json (write-once) + latest.json + data/web/story.json, feed.json, atom.xml
  11 persist       radar findings (change_seen / no_clear_change / numbers_coming) into data/processed/events.json
  12 events        run again; must change nothing but the stamp (idempotent check, reported)

Exit codes: 0 ok (deployable) | 2 tests failed (findings kept old, NOT deployable) | 1 any other error.
Flags: --root DIR  --now 2026-11-21T10:00Z  --offline  --skip-ingest  --dry-run  --area ID  --summary FILE  --alerts-fixture FILE
Secrets: EARTHDATA_TOKEN is handed to the ingest step ONLY (removed from the environment of every other step). Never printed.
--dry-run: discover runs (read-only); ingest/catalog/sync/alerts/events run in their own dry-run or check mode; build_web, build_story
and persist are skipped; tests run (read-only).
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parents[2]
TEST_CMDS = [["tools/tests/test_story.py"], ["tools/tests/test_findings.py"], ["tools/tests/test_events.py"], ["tools/tests/test_english_only.py"], ["tools/tests/test_export.py"], ["tools/check_manifest.py"]]
WATCH = ["data/h5", "data/processed", "data/web/story.json", "data/web/feed.json", "data/web/atom.xml", "config"]
SECRET = "EARTHDATA_TOKEN"


def iso_now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def norm_now(s):
    """'2026-11-21T10:00Z' or '...T10:00:00Z' -> (HH:MMZ form for alerts/events, seconds form for build_story / CMR)"""
    for f in ("%Y-%m-%dT%H:%MZ", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            d = dt.datetime.strptime(s, f)
            return d.strftime("%Y-%m-%dT%H:%MZ"), d.strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            pass
    raise SystemExit("--now must look like 2026-11-21T10:00Z, got %r" % s)


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def snapshot(root):
    out = {}
    for w in WATCH:
        base = root / w
        files = [base] if base.is_file() else sorted(p for p in base.rglob("*") if p.is_file()) if base.exists() else []
        for p in files:
            if "/img/" in p.as_posix():
                continue
            out[p.relative_to(root).as_posix()] = sha_file(p)
    return out


class Run:
    def __init__(self, a):
        self.a = a
        self.root = Path(a.root).resolve()
        self.steps = []
        self.warnings = []
        self.errors = []
        self.exit_code = 0
        self.extra = {}
        self.tmp = Path(tempfile.mkdtemp(prefix="run_all_"))
        self.now_hm, self.now_s = norm_now(a.now) if a.now else (None, None)

    # ---- logging
    def log(self, step, result, secs, detail=""):
        self.steps.append({"step": step, "seconds": round(secs, 1), "result": result, "detail": detail})
        print("[%-13s] %-12s %6.1fs  %s" % (step, result, secs, detail), flush=True)

    def env(self, with_token=False):
        e = dict(os.environ)
        if not with_token:
            e.pop(SECRET, None)
        e["PYTHONUNBUFFERED"] = "1"
        return e

    def sh(self, cmd, with_token=False, tail=25):
        """Run a command in the root, return (returncode, output). Output tail is echoed (indented); the token is masked."""
        r = subprocess.run([str(c) for c in cmd], cwd=self.root, env=self.env(with_token), text=True, capture_output=True)
        out = (r.stdout or "") + (r.stderr or "")
        tok = os.environ.get(SECRET)
        if tok:
            out = out.replace(tok, "***")
        lines = out.strip().splitlines()
        for ln in lines[-tail:]:
            print("      | " + ln[:220])
        return r.returncode, out

    def py(self, script, *args, with_token=False, tail=25):
        return self.sh([sys.executable, self.root / script, *args], with_token, tail)

    def area_args(self):
        return ["--area", self.a.area] if self.a.area else []

    def step(self, name, fn, critical=False):
        t = time.time()
        try:
            result, detail = fn()
        except Exception as e:  # noqa: BLE001 - a step may never crash the run
            result, detail = "error", "%s: %s" % (type(e).__name__, str(e)[:300])
        dur = time.time() - t
        self.log(name, result, dur, detail)
        if result == "error":
            self.errors.append("%s: %s" % (name, detail))
            self.exit_code = max(self.exit_code, 1) if self.exit_code != 2 else 2
            if critical:
                return False
        return True

    # ---- steps
    def discover(self):
        a = self.a
        if a.offline:
            return "skipped", "--offline"
        out = self.tmp / "new_scenes.json"
        args = ["--json", out, *self.area_args()]
        if self.now_s:
            args += ["--until", self.now_s]
        rc, _ = self.py("tools/pipeline/discover.py", *args)
        if rc == 2:
            self.warnings.append("CMR unreachable: no discovery today; the rest of the run continues")
            return "failed_soft", "CMR unreachable (exit 2)"
        if rc != 0:
            return "error", "discover.py exit %d" % rc
        d = json.loads(out.read_text())
        self.extra["new_scenes"] = [{"scene_key": s["scene_key"], "status": s["status"], "granule": s["granule"], "role": s["role"]}
                                    for s in d["new"] + d["upgrades"]]
        self.extra["_new_json"] = str(out)
        return "ok", "%d new, %d upgrade(s)" % (len(d["new"]), len(d["upgrades"]))

    def ingest(self):
        a = self.a
        n = len(self.extra.get("new_scenes") or [])
        if a.offline:
            return "skipped", "--offline"
        if a.skip_ingest:
            return "skipped", "--skip-ingest"
        if not n:
            return "skipped", "no new scenes"
        have = bool(os.environ.get(SECRET)) or (Path.home() / ".netrc").exists()
        if not a.dry_run and not have:
            msg = "%d new scene(s) need ingesting but no Earthdata login: set the repo secret %s (docs/PIPELINE.md)" % (n, SECRET)
            print(("::error::" if os.environ.get("GITHUB_ACTIONS") else "ERROR ") + msg, flush=True)
            return "error", msg
        args = ["--from", self.extra["_new_json"], *self.area_args()]
        if a.dry_run:
            args.append("--dry-run")
        rc, _ = self.py("tools/pipeline/ingest.py", *args, with_token=True, tail=12)
        if rc != 0:
            return "error", "ingest.py exit %d (scenes already installed are kept)" % rc
        return "ok", "ingested %d scene(s)%s" % (n, " (dry-run)" if a.dry_run else "")

    def verify_h5(self):
        try:
            import h5py
        except ImportError:
            return "error", "h5py is not installed"
        bad = []
        for p in sorted((self.root / "data" / "h5").glob("*.h5")):
            try:
                with h5py.File(p, "r") as h:
                    h.attrs["scene_id"], list(h["backscatter"].keys())
            except Exception as e:  # noqa: BLE001
                bad.append(p.name)
                self.warnings.append("unreadable H5 left out of the catalogue: %s (%s)" % (p.name, str(e)[:80]))
        self.extra["unreadable_h5"] = bad
        return ("warning", "unreadable: %s" % ", ".join(bad)) if bad else ("ok", "all H5 files open")

    def catalog(self):
        args = []
        bad = self.extra.get("unreadable_h5") or []
        if bad:   # catalogue only the readable files (symlinked into a temp dir; the catalogue still says data/h5/<name>)
            d = self.tmp / "h5_ok"
            d.mkdir(exist_ok=True)
            for p in (self.root / "data" / "h5").glob("*.h5"):
                if p.name not in bad and not (d / p.name).exists():
                    (d / p.name).symlink_to(p)
            args = ["--h5-dir", d, "--out", self.root / "data" / "h5" / "catalog.json"]
        if self.a.dry_run:
            args.append("--check")
        rc, out = self.py("tools/pipeline/catalog.py", *args)
        if self.a.dry_run:
            return "ok", "catalogue current" if rc == 0 else "catalogue WOULD change"
        return ("ok", out.strip().splitlines()[-1][:120]) if rc == 0 else ("error", "catalog.py exit %d" % rc)

    def sync_manifest(self):
        rc, out = self.py("tools/pipeline/sync_manifest.py", *(["--dry-run"] if self.a.dry_run else []))
        return ("ok", out.strip().splitlines()[-1][:120]) if rc == 0 else ("error", "sync_manifest.py exit %d" % rc)

    def alerts(self):
        a = self.a
        if a.offline and not a.alerts_fixture:
            return "skipped", "--offline without fixture: existing alerts.json kept"
        args = [*self.area_args()]
        if self.now_hm:
            args += ["--now", self.now_hm]
        if a.alerts_fixture:
            args += ["--fixture", a.alerts_fixture]
        if a.dry_run:
            args.append("--dry-run")
        rc, out = self.py("tools/pipeline/alerts.py", *args)
        if rc != 0:
            return "error", "alerts.py exit %d" % rc
        bad = [ln.split()[0] for ln in out.splitlines() if " ok=False" in ln]
        if bad:
            self.warnings.append("alert source(s) failed, previous items kept with their old timestamp: " + ", ".join(bad))
            return "warning", "failed: %s (old items kept)" % ", ".join(bad)
        return "ok", "fixture" if a.alerts_fixture else "fetched"

    def events(self, second=False):
        args = [*self.area_args()]
        if self.now_hm:
            args += ["--now", self.now_hm]
        if self.a.dry_run:
            args.append("--dry-run")
        ev = self.root / "data" / "processed" / "events.json"
        before = self.events_hash(ev) if second else None
        rc, out = self.py("tools/pipeline/events.py", *args)
        if rc != 0:
            return "error", "events.py exit %d" % rc
        if second:
            idem = self.events_hash(ev) == before
            self.extra["events_idempotent"] = idem
            if not idem:
                self.warnings.append("events.py second run changed events.json (not idempotent)")
            return ("ok" if idem else "warning"), "second run changed nothing but the stamp" if idem else "second run CHANGED events.json"
        changes = [ln.strip(" -") for ln in out.splitlines() if ln.startswith(" - ") and "no content changes" not in ln]
        return "ok", "; ".join(changes)[:200] or "no content changes"

    @staticmethod
    def events_hash(p):
        try:
            d = json.loads(Path(p).read_text())
        except (OSError, ValueError):
            return None
        d.pop("updated_utc", None)
        return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()

    def build_web(self):
        if self.a.dry_run:
            return "skipped", "--dry-run"
        rc, out = self.py("tools/build_web.py", tail=40)
        fails = [ln.strip()[:160] for ln in out.splitlines() if ln.startswith("FAIL")]
        self.extra["analysis_failures"] = fails
        if rc != 0:
            self.warnings.append("build_web reported failures; a pass that could not be analysed shows 'numbers_coming': " + " | ".join(fails or ["exit %d" % rc]))
            return "warning", "exit %d: %s" % (rc, " | ".join(fails)[:200])
        return "ok", "built"

    def tests(self):
        ok, bad = True, []
        for cmd in TEST_CMDS:
            t = time.time()
            rc, out = self.py(*cmd, tail=3)
            last = out.strip().splitlines()[-1] if out.strip() else ""
            print("      test %-26s %s (%.1fs) %s" % (cmd[0].split("/")[-1], "ok" if rc == 0 else "FAILED", time.time() - t, last[:60]))
            if rc != 0:
                ok = False
                bad.append(cmd[0])
        self.extra["tests"] = {"ok": ok, "failed": bad}
        if ok:
            return "ok", "%d test commands passed" % len(TEST_CMDS)
        self.exit_code = 2
        return "failed", "FAILED: %s" % ", ".join(bad)

    def build_story(self):
        if self.a.dry_run:
            return "skipped", "--dry-run"
        args = []
        if self.now_s:
            args += ["--now", self.now_s]
        rc, out = self.py("tools/build_story.py", *args, tail=14)
        if rc != 0:
            return "error", "build_story.py exit %d (old findings kept)" % rc
        line = next((ln for ln in out.splitlines() if ln.startswith("findings:")), "")
        self.extra["findings_report"] = line
        return "ok", line[:160]

    def persist(self):
        if self.a.dry_run:
            return "skipped", "--dry-run"
        sys.path.insert(0, str(self.root / "tools"))
        sys.path.insert(0, str(self.root / "tools" / "pipeline"))
        import build_story as B  # noqa: E402
        import events as E  # noqa: E402
        triples = B.radar_findings(str(self.root / "data" / "processed" / "findings"))
        now = E.parse_now(self.now_hm)
        changed = E.persist_radar_findings(self.root / "data" / "processed" / "events.json", triples, now)
        self.extra["radar_findings"] = [list(t) for t in triples]
        return "ok", ("%d finding(s) written to events.json: %s" % (len(changed), ", ".join("%s/%s=%s" % t for t in changed))) if changed \
            else "events.json already holds every radar finding"


def run(a):
    r = Run(a)
    t0 = time.time()
    before = snapshot(r.root)
    print("run_all: root=%s now=%s offline=%s skip_ingest=%s dry_run=%s" % (r.root, a.now or "(clock)", a.offline, a.skip_ingest, a.dry_run), flush=True)
    stop = False

    def go(name, fn, critical=False):
        nonlocal stop
        if stop:
            r.log(name, "not_run", 0, "an earlier critical step failed")
            return
        if not r.step(name, fn, critical):
            stop = True

    go("discover", r.discover)
    go("ingest", r.ingest)
    go("verify_h5", r.verify_h5)
    go("catalog", r.catalog, critical=True)
    go("sync_manifest", r.sync_manifest, critical=True)
    go("alerts", r.alerts)
    go("events", r.events, critical=True)
    go("build_web", r.build_web)
    if not stop:
        go("tests", r.tests)
    if r.exit_code == 2:
        for n in ("build_story", "persist", "events_again"):
            r.log(n, "not_run", 0, "tests failed: findings not written, old ones kept")
    elif not stop:
        go("build_story", r.build_story, critical=True)
        go("persist", r.persist)
        go("events_again", lambda: r.events(second=True))
    after = snapshot(r.root)
    changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    rec = [k for k in changed if k.startswith("data/h5/") or k == "data/processed/manifest.json"]
    groups = {"data_of_record": rec, "derived": [k for k in changed if k not in rec]}
    code = r.exit_code
    summary = {"schema": "run-all-v1", "started_utc": iso_now(), "now": a.now, "root": str(r.root), "flags": {
        "offline": a.offline, "skip_ingest": a.skip_ingest, "dry_run": a.dry_run, "area": a.area},
        "exit_code": code, "tests_ok": (r.extra.get("tests") or {}).get("ok"), "deployable": code == 0 and not a.dry_run,
        "changed": changed, "changed_groups": groups, "something_changed": bool(changed), "warnings": r.warnings, "errors": r.errors,
        "steps": r.steps, "seconds": round(time.time() - t0, 1),
        **{k: v for k, v in r.extra.items() if not k.startswith("_")}}
    if a.summary:
        Path(a.summary).parent.mkdir(parents=True, exist_ok=True)
        Path(a.summary).write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n")
    print("\nrun_all: exit %d (%s); %d file(s) changed; %d warning(s)%s" % (
        code, {0: "ok, deployable" if not a.dry_run else "ok (dry run)", 1: "error", 2: "TESTS FAILED, not deployable"}[code],
        len(changed), len(r.warnings), "; summary -> %s" % a.summary if a.summary else ""), flush=True)
    for w in r.warnings:
        print("  warning: " + w)
    for e in r.errors:
        print("  error: " + e)
    return code


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(DEFAULT_ROOT), help="repo root whose tools/ are run (default: this repo)")
    ap.add_argument("--now", default=None, help="pretend it is this UTC time, e.g. 2026-11-21T10:00Z")
    ap.add_argument("--offline", action="store_true", help="no network: skip discover/ingest; alerts from --alerts-fixture or keep the old file")
    ap.add_argument("--skip-ingest", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="read-only: list what would change, write nothing")
    ap.add_argument("--area", default=None, help="area id in config/areas.json (default: default_area)")
    ap.add_argument("--summary", default=None, help="write a JSON summary (steps, exit code, changed files) to this path")
    ap.add_argument("--alerts-fixture", default=None, help="fake alerts JSON (see tools/pipeline/alerts.py) used instead of the network")
    a = ap.parse_args()
    try:
        return run(a)
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print("run_all: unexpected error: %s: %s" % (type(e).__name__, e), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
