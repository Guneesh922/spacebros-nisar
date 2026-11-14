# SpaceBros NISAR — read this first (every Claude Code session)

NASA Space Apps 2026 entry: dashboard of NISAR radar evidence of coastal flooding and ocean effects from
**Cyclone Arnab** (landfall Andhra Pradesh, 28 Oct 2026). Scope: cyclones, coastal and oceanic only.
Remote `origin` = Guneesh922/spacebros-nisar, branch `main`.

**Before doing anything:** read `docs/STATUS.md` (live task board: what is real, what is placeholder, what is next)
and `docs/DATA_STORAGE.md` (where data lives, H5 schema, build step). Build on the current state; do not restart
or redesign. When you finish a task, update `docs/STATUS.md` in the same session.

## Fixed decisions (do not reopen without the user)
- Data of record is **HDF5 (.h5) only**, as small study-box subsets in `data/h5/` (committed to git).
  No PNG/GeoTIFF/JPG as data of record. Display PNGs/JSON are *build outputs* in `data/web/` (git-ignored),
  made by `tools/build_web.py` from the H5. Full NISAR granules (0.85–7.5 GB) never go in git and should
  not stay on disk once their subset is verified.
- Both bands: L-band (NASA, ASF DAAC, Earthdata login) and S-band (ISRO, Bhoonidhi STAC API, user's portal login).
- The dashboard UI in `app/dashboard-mockup/` (tabs "What happened" / "Data for officials and researchers",
  one Leaflet map) is **approved. Do not redesign.** Only wire data into it and fix listed bugs.
- Landfall time is disputed in IMD bulletins: keep `time_utc: null`.
- Keep honesty badges ("Sample values", "Quick-look sample") on any layer until it is built from real H5.
  Always tell the user plainly what is real and what is still a placeholder.

## Working rules
- Other people have uncommitted edits in the tree. **Do not commit, push, stash, reset or checkout unless the
  user asks.** Touch only files for your task.
- Never delete files without telling the user exactly what and that it is permanent.
- Never read, print or store credentials (`~/.netrc`, Bhoonidhi password). The user types logins themselves.
- Preview: `mcp__Claude_Browser__preview_start` name `nisar-static` (config `~/Documents/nsa/.claude/launch.json`,
  port 8765), open `/app/dashboard-mockup/`. Background servers started from Bash get blocked.
- After manifest changes: `python3 tools/check_manifest.py`.
- Python deps for the data pipeline: `requirements.txt` (h5py, numpy, pyproj; earthaccess+fsspec only for
  streaming). Use a venv; system python lacks them.
- Delegation: the user prefers a planning model (Opus) that hands simple, well-specified tasks to
  Sonnet/Haiku agents. Give agents exact file paths, the H5 schema, and the "do not commit / do not delete" rules.

## Map of the repo
- `src/fetch/subset_h5.py` — study-box subsetter, full granule (local path or HTTPS) -> small H5 (schema in DATA_STORAGE.md)
- `src/fetch/download_l_band_h5.py` — full L-band granules to `data/raw/nisar_l_h5/` (git-ignored, resumes)
- `src/fetch/bhoonidhi_s_band.py` — S-band search/download (needs HTTP Range resume, see STATUS)
- `src/fetch/subset_arnab.py`, `src/gcov_subset.py` — old GeoTIFF subsetter (superseded; helpers reused)
- `data/reference/scene_manifest_full.csv` — the 8 L-band scene roles; `data/reference/nisar_s_candidates.csv` — S-band
- `data/processed/manifest.json` — what the dashboard shows (schema `docs/MANIFEST_SCHEMA.md`)
- `tools/build_web.py` — H5 -> `data/web/` display assets + stats; `tools/check_manifest.py` — validator
- Plan: `~/Documents/nsa/04_Project_Idea/06_PLAN_Eye_of_the_Storm.md`
