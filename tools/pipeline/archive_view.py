#!/usr/bin/env python3
"""Keep a frozen, browsable copy of the site every time the live data moves on.

The copies live on the git branch `site-archive` (folder `archive/`), and pages.yml publishes that folder at
<site>/archive/. The dashboard lists every copy in "Saved days" by default (a viewer can remove it there).

  archive/index.json   [{id, label, path, ref, saved_utc, latest: {coast, sea}}], newest first
  archive/live.json    {ref, scenes}: the version that is live now (what gets archived when the scenes change)
  archive/<id>/        app/, data/processed, data/web, config, small data/reference, data/h5/catalog.json, docs/METHODS.md

Commands (run from the repo root; ARCHIVE_DIR is a checkout of the site-archive branch):
  archive_view.py rotate  --archive-dir DIR [--ref HEAD]          used by update.yml after a successful run
      if the scene list at REF differs from live.json, archive live.json's ref first; then live.json = REF
  archive_view.py add     --archive-dir DIR --ref REF --id ID [--label TEXT]   archive one version by hand
"""
import argparse, datetime, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BANNER = ('<div id="archive-banner" style="position:fixed;left:12px;bottom:12px;z-index:9999;max-width:min(560px,calc(100vw - 24px));'
          'background:#0f2a33;color:#fff;font:14px/1.4 system-ui,sans-serif;padding:8px 12px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.35)">'
          'Saved copy: {label}. <a href="../../../../app/dashboard-mockup/" style="color:#7fe0d4;font-weight:600">Go to the live site</a></div>')


def git(*a, cwd=ROOT):
    return subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def scenes_at(ref):
    try:
        cat = json.loads(git("show", f"{ref}:data/h5/catalog.json"))
    except subprocess.CalledProcessError:
        return []
    return sorted(s["file"] for s in cat.get("scenes", []))


def latest(files):
    out = {}
    for f in files:                                   # L_COAST_20261109_T055.h5
        p = f.split("_")
        if len(p) >= 3 and p[2].isdigit():
            role, d = p[1].lower(), p[2]
            out[role] = max(out.get(role, ""), d)
    return {k: "%s-%s-%s" % (v[:4], v[4:6], v[6:]) for k, v in out.items()}


def hday(iso):
    d = datetime.date.fromisoformat(iso)
    return "%d %s %d" % (d.day, d.strftime("%b"), d.year)


def build(ref, dest, py):
    """Build the site exactly as pages.yml does, from the code and data at ref, into dest."""
    tmp = Path(tempfile.mkdtemp(prefix="archive_"))
    wt = tmp / "wt"
    git("worktree", "add", "-q", "--detach", str(wt), ref)
    try:
        for step in (["tools/build_web.py"], ["tools/build_story.py"]):
            r = subprocess.run([py, *step], cwd=wt, capture_output=True, text=True)
            if r.returncode != 0:
                sys.exit("archive: %s failed at %s:\n%s" % (step[0], ref, (r.stdout + r.stderr)[-2000:]))
        if dest.exists():
            shutil.rmtree(dest)
        (dest / "data" / "h5").mkdir(parents=True)
        (dest / "docs").mkdir()
        shutil.copytree(wt / "app", dest / "app")
        shutil.copytree(wt / "data" / "processed", dest / "data" / "processed")
        shutil.copytree(wt / "config", dest / "config")
        if (wt / "data" / "web").is_dir():
            shutil.copytree(wt / "data" / "web", dest / "data" / "web")
        for f in (wt / "data" / "reference").rglob("*"):
            if f.is_file() and f.stat().st_size < 1024 * 1024:
                t = dest / f.relative_to(wt)
                t.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, t)
        if (wt / "data" / "h5" / "catalog.json").exists():
            shutil.copy2(wt / "data" / "h5" / "catalog.json", dest / "data" / "h5" / "catalog.json")
        if (wt / "docs" / "METHODS.md").exists():
            shutil.copy2(wt / "docs" / "METHODS.md", dest / "docs" / "METHODS.md")
        if (dest / "data" / "internal").exists():
            shutil.rmtree(dest / "data" / "internal")
    finally:
        git("worktree", "remove", "--force", str(wt))
        shutil.rmtree(tmp, ignore_errors=True)


def add(adir, ref, aid, label, py):
    sha = git("rev-parse", ref)
    lat = latest(scenes_at(sha))
    if not label:
        label = "radar scenes up to %s" % hday(max(lat.values())) if lat else "saved %s" % sha[:7]
    dest = adir / aid
    build(sha, dest, py)
    page = dest / "app" / "dashboard-mockup" / "index.html"
    s = page.read_text(encoding="utf-8")
    if "archive-banner" not in s:
        page.write_text(s.replace("<body>", "<body>\n" + BANNER.format(label=label), 1), encoding="utf-8")
    ip = adir / "index.json"
    idx = json.loads(ip.read_text()) if ip.exists() else []
    idx = [e for e in idx if e.get("id") != aid]
    idx.insert(0, {"id": aid, "label": label, "path": "archive/%s/app/dashboard-mockup/" % aid, "ref": sha,
                   "saved_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "latest": lat})
    ip.write_text(json.dumps(idx, indent=2) + "\n")
    print("archived %s (%s) -> %s" % (sha[:7], label, dest))


def rotate(adir, ref, py):
    sha = git("rev-parse", ref)
    now = scenes_at(sha)
    lp = adir / "live.json"
    live = json.loads(lp.read_text()) if lp.exists() else None
    if live and live.get("scenes") != now:
        lat = latest(live["scenes"])
        aid = "view-%s-%s" % (max(lat.values()).replace("-", "") if lat else "x", live["ref"][:7])
        add(adir, live["ref"], aid, "radar scenes up to %s, before the %s update" % (
            hday(max(lat.values())) if lat else "?", hday(max(latest(now).values())) if now else "next"), py)
    elif not live:
        print("archive: no live.json yet, starting it at %s" % sha[:7])
    else:
        print("archive: scenes unchanged since %s, nothing to archive" % live["ref"][:7])
    lp.write_text(json.dumps({"ref": sha, "scenes": now}, indent=2) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["rotate", "add"])
    ap.add_argument("--archive-dir", required=True, help="checkout of the site-archive branch; copies go in <dir>/archive/")
    ap.add_argument("--ref", default="HEAD")
    ap.add_argument("--id")
    ap.add_argument("--label")
    ap.add_argument("--python", default=sys.executable)
    a = ap.parse_args()
    adir = Path(a.archive_dir).resolve() / "archive"
    adir.mkdir(parents=True, exist_ok=True)
    if a.cmd == "rotate":
        rotate(adir, a.ref, a.python)
    else:
        if not a.id:
            ap.error("add needs --id")
        add(adir, a.ref, a.id, a.label, a.python)


if __name__ == "__main__":
    main()
