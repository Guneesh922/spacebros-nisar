# STATUS — live task board (update this at the end of every session)

Last updated: 2026-11-14 16:15 IST by Opus planning session.

## Real vs placeholder (14 Nov, end of session)
- REAL: all 8 L-band H5 subsets in data/h5/ (259 MB) and their 8 map layers; sea difference map 27 Oct vs 15 Oct;
  scene catalogues, IMD bulletins, district/mandal vectors, approved dashboard UI.
- PLACEHOLDER: class maps (new water, wet crops, no change), data/processed/mandal_rank.json,
  data/processed/profile.json (numbers invented), all S-band layers. Badges stay on these.
- Full L-band granules were DELETED after subsetting (user approved). Re-fetch with download_l_band_h5.py if ever needed.
- Committed locally on main ("Switch data of record to H5 study-box subsets") (author Guneesh Gupta). NOT PUSHED: the device shell has no GitHub login.

## Phase 1 — in progress
- [x] P1-A subsetter `src/fetch/subset_h5.py` + one-scene size test (agent: Sonnet)
- [x] P1-B HTTP Range resume in `src/fetch/bhoonidhi_s_band.py` (agent: Haiku): `<id>.h5.part` + Range resume, 1 MB chunks, progress every 10 s, 5 retries with backoff, 200 restarts with warning, 416 completes, Content-Disposition names the file
- [x] P1-C `tools/build_web.py` (H5 -> lat/lon PNG + stats JSON, tested on a synthetic schema-v1 H5; derived products are stubs), `.gitignore` exception for `data/h5/` + `data/web/` ignored, `.github/workflows/pages.yml` (not yet run on GitHub), check_manifest `h5`/`data/web` support, `requirements.txt`, `h5` documented in MANIFEST_SCHEMA.md (agent: Sonnet, 14 Nov)

## Measured sizes (P1-A, 14 Nov 2026, schema v1: int16 dB*100, gzip 6 + shuffle, 256x256 chunks, HH/HV or VV/VH + mask)
| file | shape | posting | size | medians | NaN | time |
|---|---|---|---|---|---|---|
| `L_SEA_20261015_T048.h5` (L_SEA_CALM_1015) | 3006x3398 | 100 m (5x5 of 20 m) | 7.5 MB | VV -14.20, VH -25.31 dB | 0.687 (swath edge) | 11 s |
| `L_COAST_20261004_T055.h5` (L_COAST_1004) | 10017x10720 | 10 m native | 232.4 MB | HH -10.62, HV -20.35 dB | 0.191 | 33 s |
| `L_COAST_20261004_T055_ml2.h5` (2x2) | 5008x5360 | 20 m | 56.2 MB | HH -9.52, HV -19.56 dB | 0.190 | 10 s |
Native coast is far over 50 MB; 2x2 is still 56 MB (slightly over the 50 MB target; 8 coast files ~450 MB, folder fits the 600 MB rule). Decision on 2x2 vs 3x3 vs LFS pending. Tool venv: `/tmp/venv-nisar` (home disk was full).

## Phase 2 — L-band done; next session starts here
1. [ ] User: `git push origin main`, then GitHub Settings -> Pages -> Source: GitHub Actions; check the Actions run.
2. [ ] Look at the dashboard (local preview or Pages): overlay placement over delta/sea, badges, console errors; fix only
       what is broken (no redesign). Also the known UI leftovers below.
3. [ ] Class maps from H5 (implement build_class_maps in tools/build_web.py): coast HH/HV, baseline 1004+1016 (pre),
       1028 (landfall) and 1109 (after). Classes: likely new open water (low HH both bands drop vs baseline),
       likely wet/flooded crops (HH rise / double bounce), no change. Thresholds documented; reference
       permanent water from data/interim/F/jrc.py if useful. Older prototype code: data/interim/F/{cls,ml,final}.py.
4. [ ] mandal_rank.json from the class maps x mandal polygons (data/interim/F/mandal_rank.* is the old prototype format);
       profile.json (eye profile) from L_SEA_20261027 VV along a transect through the eye (data/interim/A/profile*.json
       is the old format). Replace the invented numbers; keep the same JSON shape the dashboard reads.
5. [ ] Sea difference: check 15 Oct (PROVISIONAL) vs 3 Oct calibration offset before quoting numbers (median diff is +3.7 dB).
6. [ ] S-band: user downloads the 4 scenes with `python src/fetch/bhoonidhi_s_band.py download ...` (resume now works),
       inspect format with h5py, extend subset_h5.py for S-band (band S, same schema), add layers.
7. [ ] Email Bhoonidhi support about missing S-band: 27 Oct sea eye pass, 15 Oct + 8 Nov sea, 9 Nov delta.
8. [ ] Drop badges only for layers now built from H5; update docs/PLACEHOLDERS.md; tidy docs/BACKEND_GAPS.md and
       docs/handoff/NEXT_SESSION_PROMPT.md (older handoff; CLAUDE.md + this file supersede it).

## Known UI leftovers (do not redesign; fix only)
layer table scrolls sideways; eye-profile chart / Alerts / Scenes / Downloads not visually reviewed;
map overlays crowd at narrow desktop widths; fit-to-bounds off right after a mode switch.

## Needs the user
- Enable GitHub Pages (Settings → Pages → Source: GitHub Actions) once the workflow is pushed.
- Decide who commits: nothing has been committed or pushed by Claude. Teammate branch `origin/bhoonidhi` exists (S-band fetch work).

## Notes from 14 Nov session (Opus)
- Built PNGs checked by eye: coast 16 Oct shows the Godavari delta clearly; sea 27 Oct shows the cyclone eye and spiral bands. Real.
- Stretch changed to SEA -25..0 dB (shared across dates so they compare) and sea-difference ramp to ±15 dB (±6 saturated).
- Sea difference median is +3.7 dB over the whole scene: partly the storm, but the 15 Oct reference is PROVISIONAL, so part may be calibration. Check against 3 Oct (also calm) before claiming numbers.
- Dashboard NOT yet checked in a browser: the built-in browser cannot reach a server started from the Linux shell, and no server was running on port 8765. The user (or a Claude Code session on the Mac) must start the `nisar-static` preview, then check overlay placement, badges and console.
- Pipeline venv lives in /tmp/venv-nisar (made with uv; the device-shell home disk is full). Rebuild with: `UV_CACHE_DIR=/tmp/uvcache uv venv /tmp/venv-nisar && uv pip install --python /tmp/venv-nisar/bin/python h5py numpy pyproj pillow`.
