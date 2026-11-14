#!/usr/bin/env python3
"""Emulate .github/workflows/update.yml and pages.yml on this Mac, in a scratch copy, without GitHub, docker or a push.

How: the workflow files themselves are read (PyYAML) and every `run:` block of the named steps is executed with bash, in order,
in a scratch copy of the repo, with the GitHub variables the blocks use ($GITHUB_OUTPUT, $RUNNER_TEMP, $GITHUB_STEP_SUMMARY,
$GITHUB_REF_NAME...). `if:` conditions are evaluated against the step outputs collected so far. `uses:` steps (checkout, setup-python,
upload-artifact, Pages upload/deploy) are not run: the copy replaces checkout. `git push` goes to a local bare repository, and `gh` is a
shim that only logs "gh workflow run pages.yml". Nothing leaves this computer; the real repo is only read.

  python tools/sim/emulate_workflow.py --scratch <dir> [--log <file>] [--force-test-failure]

--force-test-failure: after the baseline commit, a failing test is injected into the SCRATCH copy of tools/tests/test_findings.py.
  Then only phases A and C run and the emulator checks the gate: run_all exit 2, no findings/events/alerts commit (only data of record,
  if any), no Pages redeploy call, pages.yml stops at the tests (no _site). Exit 0 = the gate held, 1 = it did not.

Phases (all with --offline, as requested, except discover):
  A  update.yml, scheduled-run style, OFFLINE=true  (run_all --offline; commit step; deploy step; fail step)
  B  update.yml, DRY_RUN=true, OFFLINE=false        (live public CMR discovery, ingest --dry-run if anything is new, nothing written)
  C  pages.yml build job (build_web, all tests, build_story, assemble site), then checks of _site/
Not emulated: GitHub's runner image, actions/*, secrets, LFS, the real git remote, Pages hosting.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is needed for this emulator only: .venv/bin/pip install pyyaml")

REAL = Path(__file__).resolve().parents[2]
SKIP_RUN = {"Install deps", "Install pipeline deps"}   # dependencies are already in the venv


class Emu:
    def inject_failing_test(self):
        t = self.repo / "tools" / "tests" / "test_findings.py"
        txt = t.read_text()
        marker = "\ndef main():"
        add = "\ndef test_zz_forced_failure():\n    raise AssertionError('forced failure injected by emulate_workflow --force-test-failure (scratch copy only)')\n\n"
        assert marker in txt, "cannot find main() in the scratch test_findings.py"
        t.write_text(txt.replace(marker, add + marker, 1))
        self.say("FORCED FAILURE: injected test_zz_forced_failure into the scratch copy of tools/tests/test_findings.py (the real repo is not touched)")

    def __init__(self, scratch, logf):
        self.s = Path(scratch)
        self.repo = self.s / "repo"
        self.log = open(logf, "w")
        self.rt = self.s / "runner_temp"
        self.results = []

    def say(self, msg=""):
        print(msg, flush=True)
        self.log.write(msg + "\n")
        self.log.flush()

    def sh(self, cmd, **kw):
        r = subprocess.run(cmd, shell=isinstance(cmd, str), text=True, capture_output=True, **kw)
        return r.returncode, (r.stdout or "") + (r.stderr or "")

    def setup(self):
        if self.s.exists():
            shutil.rmtree(self.s)
        self.repo.mkdir(parents=True)
        self.rt.mkdir()
        subprocess.run(["rsync", "-a", "--exclude", ".git", "--exclude", ".venv", "--exclude", "data/raw", "--exclude", "node_modules",
                        str(REAL) + "/", str(self.repo) + "/"], check=True)
        # local bare "origin" so that the commit/push step really runs (pull --rebase, push)
        env = dict(os.environ, GIT_AUTHOR_NAME="emu", GIT_AUTHOR_EMAIL="emu@example.invalid", GIT_COMMITTER_NAME="emu", GIT_COMMITTER_EMAIL="emu@example.invalid")
        for c in (["git", "init", "-q", "-b", "main", str(self.repo)], ["git", "init", "-q", "--bare", str(self.s / "origin.git")]):
            subprocess.run(c, check=True, env=env)
        for c in (["add", "-A"], ["commit", "-q", "-m", "baseline = the working tree as it is now"],
                  ["remote", "add", "origin", str(self.s / "origin.git")], ["push", "-q", "origin", "main"]):
            subprocess.run(["git", "-C", str(self.repo), *c], check=True, env=env)
        shim = self.s / "bin"
        shim.mkdir()
        (shim / "gh").write_text('#!/bin/sh\necho "[gh shim] gh $*  (nothing is started)" | tee -a "%s"\n' % (self.s / "gh_calls.log"))
        (shim / "gh").chmod(0o755)
        self.shim = shim
        self.say("scratch copy: %s  (baseline commit made, local bare origin)" % self.repo)

    # ---- expressions
    def ev(self, expr, ctx):
        e = expr.strip()
        e = re.sub(r"^\$\{\{\s*|\s*\}\}$", "", e)
        e = e.replace("always()", "True")
        e = re.sub(r"steps\.(\w+)\.outputs\.(\w+)", lambda m: repr(ctx["outputs"].get("%s.%s" % (m.group(1), m.group(2)), "")), e)
        e = re.sub(r"inputs\.(\w+)", lambda m: repr(ctx["inputs"].get(m.group(1), "")), e)
        e = e.replace("&&", " and ").replace("||", " or ")
        e = re.sub(r"!(?!=)", " not ", e)
        return bool(eval(e, {"__builtins__": {}}, {"True": True}))   # noqa: S307 - own workflow files only

    def sub(self, text, ctx):
        def rep(m):
            x = m.group(1).strip()
            if x.startswith("inputs."):
                return str(ctx["inputs"].get(x[7:], "")).lower() if isinstance(ctx["inputs"].get(x[7:]), bool) else str(ctx["inputs"].get(x[7:], ""))
            if x.startswith("steps."):
                a = x.split(".")
                return ctx["outputs"].get("%s.%s" % (a[1], a[3]), "")
            if x.startswith("secrets."):
                return ""
            if x == "github.token":
                return "emulated-token"
            return ""
        return re.sub(r"\$\{\{(.*?)\}\}", rep, str(text))

    def run_workflow(self, wf, job, inputs, only=None, label=""):
        d = yaml.safe_load(open(REAL / ".github" / "workflows" / wf))
        steps = d["jobs"][job]["steps"]
        out_file = self.s / ("gh_output_%s.txt" % label)
        out_file.write_text("")
        ctx = {"outputs": {}, "inputs": inputs}
        self.say("\n" + "=" * 100 + "\nWORKFLOW %s job %s  (%s)  inputs=%s\n" % (wf, job, label, inputs) + "=" * 100)
        for st in steps:
            name = st.get("name") or st.get("uses")
            sid = st.get("id")
            if "run" not in st:
                self.say("--- [uses] %s: not emulated" % name)
                continue
            if name in SKIP_RUN:
                self.say("--- [run ] %s: skipped (venv already has the dependencies)" % name)
                continue
            if "if" in st and not self.ev(str(st["if"]), ctx):
                self.say("--- [run ] %s: SKIPPED by condition  if: %s" % (name, str(st["if"]).strip()))
                self.results.append((label, name, "skipped"))
                continue
            env = dict(os.environ)
            env.pop("EARTHDATA_TOKEN", None)
            env.update({"GITHUB_OUTPUT": str(out_file), "RUNNER_TEMP": str(self.rt), "GITHUB_STEP_SUMMARY": str(self.s / "step_summary.md"),
                        "GITHUB_REF_NAME": "main", "GITHUB_ACTIONS_EMU": "1",
                        "PATH": "%s:%s:%s" % (self.shim, REAL / ".venv" / "bin", env["PATH"]), "SPACEBROS_AREAS": str(self.repo / "config" / "areas.json")})
            for k, v in (st.get("env") or {}).items():
                env[k] = self.sub(v, ctx)
            if st.get("name") == "Run the pipeline (run_all.py)":
                env["EARTHDATA_TOKEN"] = ""   # the real secret is never used here
            self.say("--- [run ] %s" % name)
            t = time.time()
            p = subprocess.run(["bash", "-e", "-c", st["run"]], cwd=self.repo, env=env, text=True, capture_output=True)
            txt = (p.stdout or "") + (p.stderr or "")
            lines = txt.rstrip().splitlines()
            for ln in (lines if len(lines) <= 60 else lines[:25] + ["      ... (%d lines hidden) ..." % (len(lines) - 50)] + lines[-25:]):
                self.say("      | " + ln[:200])
            for ln in out_file.read_text().splitlines():
                if "=" in ln and sid:
                    k, v = ln.split("=", 1)
                    ctx["outputs"]["%s.%s" % (sid, k)] = v
            self.say("    -> exit %d in %.1fs; outputs so far: %s" % (p.returncode, time.time() - t, {k: v for k, v in ctx["outputs"].items() if k.startswith(sid or "?")}))
            self.results.append((label, name, "ok" if p.returncode == 0 else "exit %d" % p.returncode))
            if p.returncode != 0:
                self.say("    STEP FAILED -> job stops here (as GitHub would, later steps with always() excepted)")
                # GitHub keeps running only steps whose `if` is always()/failure(); evaluate the remaining ones the same way
                for later in steps[steps.index(st) + 1:]:
                    cond = str(later.get("if", ""))
                    if "always()" in cond and "run" in later and later.get("name") not in SKIP_RUN:
                        self.say("--- [run ] %s (always())" % later.get("name"))
                        q = subprocess.run(["bash", "-e", "-c", later["run"]], cwd=self.repo, env=env, text=True, capture_output=True)
                        for ln in ((q.stdout or "") + (q.stderr or "")).rstrip().splitlines()[-15:]:
                            self.say("      | " + ln[:200])
                break
        return ctx


def forced(e):
    e.inject_failing_test()
    base = e.sh("git -C %s rev-parse HEAD" % e.repo)[1].strip()
    ctx = e.run_workflow("update.yml", "update", {"dry_run": False, "offline": True}, label="A update.yml offline, forced test failure")
    code = ctx["outputs"].get("run.code")
    rc, files = e.sh("git -C %s diff --name-only %s HEAD" % (e.repo, base))
    committed = [f for f in files.split() if f]
    _, gh = e.sh("cat %s 2>/dev/null" % (e.s / "gh_calls.log"))
    findings_committed = [f for f in committed if f.startswith("data/processed/findings/") or f.endswith(("events.json", "alerts.json", "mandal_rank.json", "profile.json"))]
    e.say("\nrun_all exit code: %s (expected 2)" % code)
    e.say("files committed after the baseline: %s" % (committed or "none"))
    e.say("gh calls (Pages redeploy): %s" % (gh.strip() or "none"))
    ctx_c = e.run_workflow("pages.yml", "build", {}, label="C pages.yml build, forced test failure")
    site_built = (e.repo / "_site" / "data" / "web" / "story.json").exists()
    e.say("pages.yml: _site assembled: %s (expected False)" % site_built)
    checks = {"run_all exit code is 2": code == "2", "no findings/events/alerts commit": not findings_committed,
              "no Pages redeploy call": not gh.strip(), "pages.yml built no site": not site_built}
    for k, v in checks.items():
        e.say("  %-36s %s" % (k, "OK" if v else "FAILED"))
    ok = all(checks.values())
    e.say("\nFORCED FAILURE OVERALL: %s" % ("the gate held: exit 2, nothing committed, nothing deployed" if ok else "GATE DID NOT HOLD"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scratch", required=True)
    ap.add_argument("--log", default=None)
    ap.add_argument("--force-test-failure", action="store_true", help="inject a failing test in the scratch copy and check that nothing is committed or deployed (exit 2 expected)")
    a = ap.parse_args()
    scratch = Path(a.scratch).resolve()
    if REAL in scratch.parents or scratch == REAL:
        sys.exit("refusing: --scratch must be outside the real repo")
    scratch.parent.mkdir(parents=True, exist_ok=True)
    logf = a.log or str(scratch.parent / "reports" / "workflow_emulation.log")
    Path(logf).parent.mkdir(parents=True, exist_ok=True)
    e = Emu(scratch, logf)
    e.setup()
    if a.force_test_failure:
        return forced(e)
    # phase A: the daily job, offline (no network, no real push)
    ctx = e.run_workflow("update.yml", "update", {"dry_run": False, "offline": True}, label="A update.yml offline")
    code = ctx["outputs"].get("run.code")
    e.say("\nPHASE A result: run_all exit code %s; pushed=%s" % (code, ctx["outputs"].get("commit.pushed")))
    rc, out = e.sh("git -C %s log --stat --format='%%h %%s' -3 | head -30" % e.repo)
    e.say("last commits in the scratch repo (pushed to the local bare origin):\n" + out)
    rc, out = e.sh("cat %s 2>/dev/null" % (e.s / "gh_calls.log"))
    e.say("gh calls: " + (out.strip() or "none (no deploy)"))
    # phase B: workflow_dispatch with dry_run, live CMR (public)
    ctx = e.run_workflow("update.yml", "update", {"dry_run": True, "offline": False}, label="B update.yml dry-run, live CMR")
    e.say("\nPHASE B result: run_all exit code %s; pushed=%s (a dry run never commits)" % (ctx["outputs"].get("run.code"), ctx["outputs"].get("commit.pushed")))
    # phase C: pages.yml build job
    ctx = e.run_workflow("pages.yml", "build", {}, label="C pages.yml build")
    site = e.repo / "_site"
    checks = {"_site/config/areas.json": (site / "config" / "areas.json").exists(),
              "_site/data/processed/findings/latest.json": (site / "data" / "processed" / "findings" / "latest.json").exists(),
              "_site/data/web/story.json": (site / "data" / "web" / "story.json").exists(),
              "_site/app/dashboard-mockup/index.html": (site / "app" / "dashboard-mockup" / "index.html").exists(),
              "_site/data/h5/catalog.json": (site / "data" / "h5" / "catalog.json").exists()}
    e.say("\nPHASE C checks of the assembled site:")
    for k, v in checks.items():
        e.say("  %-48s %s" % (k, "present" if v else "MISSING"))
    e.say("\nSUMMARY of steps:")
    for lab, name, res in e.results:
        e.say("  %-34s %-44s %s" % (lab, name, res))
    bad = [r for r in e.results if r[2] not in ("ok", "skipped")] + [k for k, v in checks.items() if not v]
    e.say("\nOVERALL: %s" % ("every emulated step passed" if not bad else "PROBLEMS: %s" % bad))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
