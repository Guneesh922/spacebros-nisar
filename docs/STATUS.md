# STATUS — live task board (update this at the end of every session)

Last updated: 2026-11-14 21:20 IST by Opus planning session (Wave 4 commits).

## Wave 4 (14 Nov, evening) — live coast monitor
Plan/contract: `docs/review/WAVE4_PLAN.md`. Tests: story 16, findings 10, events 13, manifest 17, all pass (`docs/review/ACCEPTANCE_DATA.md`).

### Done
- WP1 findings: `data/processed/findings/<date>.json` is write-once with revisions (28 Oct and 9 Nov are at revision 4, logged; nothing published yet) plus `latest.json`. Template states: big_change / quiet / no_new_pass / numbers_coming / no_baseline. Lower-confidence flag (provisional baseline; season rule from `data/seasons.json`). Radar finding: 28 Oct `no_clear_change`, 9 Nov `change_seen`.
- WP2 alerts and events: alerts-v2 = GDACS + SACHET filtered to Andhra Pradesh (the Jammu and Kashmir bug is fixed). `data/processed/events.json` holds Arnab (24-28 Oct from IMD press releases 5-6; end = last bulletin date; aftermath 45 days) plus two auto drafts, Murasu and Flood in India (GDACS, not reviewed). `data/events/arnab-2026.json` is superseded by `events.json` (kept; still the fallback).
- WP3 dashboard: latest pass home, event chips, events archive, alerts for the area, sidebar collapse, About and sources (`app/dashboard-mockup/README.md`, section "WP3").
- WP4 area config: `config/areas.json` drives boxes, tracks, baseline and alert matching. Site title "Coast Radar Watch"; name options Coast Radar Watch / Pass by Pass / Delta Radar Watch (team picks; one config value). Only configured tracks are ingested (T120/T127 SEA are listed, not ingested).
- WP1e pipeline: `tools/pipeline/run_all.py` holds the single step order. `update.yml` and `pages.yml` are gated by tests (actionlint clean; emulated locally including a forced failure with `tools/sim/`; NOT run on GitHub).
- WP5 resource audit: `docs/review/RESOURCE_AUDIT.md`. About card cites the Data User Guide, StoryMaps, white papers, ARSET. CSA RCM/RADARSAT-1, CONAE SAOCOM and UAVSAR Postcards are not used (reason to confirm by the team).
- WP6 L-band tests (`docs/review/LBAND_TEST.md`): wet-crops HH / HV / ratio tested, not adopted. Sea +4 dB on 27 Oct is mostly the storm (8 Nov vs 15 Oct is +0.1 dB); 3 Oct is unusable as a reference.
- WP7 S-band: no files in `data/h5/S_*` or `data/raw/nisar_s`, so NOT done.
- SACHET and GDACS are reachable from the Mac; untested from a GitHub runner (fails soft, keeps the snapshot with its real date).

### Left / placeholder
- S-band (no files). A real run on a GitHub runner. Domain review of the English templates. GDACS gives a centroid only.
- The sea chip names Murasu "Tropical Cyclone MURASU-26" but "Cyclone Murasu" elsewhere.
- `docs/review/ACCEPTANCE_UI.md` bugs, resolved 14 Nov (fix pass + fresh browser re-check, console clean at 1468 and 390 wide): B1 earlier-updates entries now show their own event chips; B5 header "Radar layers built" vs footer "Summary updated"; B6 contradicting km2 line removed; B7 sea-difference limit made date-neutral; B4 was a stale tab (not reproduced). By design, not bugs: B2 (a draft moves alert_only -> radar_linked once a pass falls in its window; still tagged "not reviewed"), B3 (plan phrases were examples; archive shows each pass's own headline). Also fixed from ACCEPTANCE_DATA.md: 28 Oct top-mandal contradiction, 20-word guard on filled text, Murasu caveat hedged, numbers_coming sub per state, no_new_pass day count + rolling next pass, only configured tracks ingested.

### Needs the team
- S-band download (Bhoonidhi login). `EARTHDATA_TOKEN` secret. Pages source = GitHub Actions and workflow read/write permission. Push (main is ahead of origin). Final site name. Submission form. Confirm the CSA/CONAE reason. Fable evaluation, on the user's say-so.

### Older items now done (verified in the docs above)
- Alerts J&K bug (W3 "Open" note at the bottom of this file): fixed, AP only.
- Sea +3.7 dB check against 3 Oct: done (WP6; 3 Oct is unusable, the 27 Oct signal is mostly storm).
- W3-H "PRO review" mandal card follow-up and "mandal card follows the day selector": not verified, left open.

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
5. [x] (done in Wave 4, see WP6) Sea difference: check 15 Oct (PROVISIONAL) vs 3 Oct calibration offset before quoting numbers (median diff is +3.7 dB).
6a. [x] One-command S-band subsetting written (14 Nov 2026): `python src/fetch/bhoonidhi_s_band.py subset --preset arnab` streams only box chunks over HTTP Range (RangeFile), S-band grid/pols in subset_h5.py, `--local` for portal files; see docs/PIPELINE.md "S-band in one command". Tested on synthetic SSAR files + local Range server only.
6. [ ] S-band: user RUNS the subset command (replaces downloading the 4 full files; old `download` still works),
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

## Wave 3 (started 14 Nov 16:20 IST) — user's goals: a living product, not a static doc
User wants: the map keeps updating as new NISAR scenes are released (automatic pipeline); users can save a
particular day to view later; then a full evaluation (by a Fable agent) of whether all L- and S-band data is used
and shown well. Verified 16:18 IST in the browser: radar overlays draw in the right place (coast + sea/eye modes);
8 console 404s still to trace.
- [x] W3-A derived products from H5: class maps, mandal_rank.json, profile.json (agent: Sonnet, 14 Nov). Built by `tools/build_web.py`, method in `docs/METHODS.md`. Still placeholder: all S-band layers; the wet-crops class is not distinguishable from normal field change; no ground truth; baseline scenes PROVISIONAL; dashboard text/badges that say "sample" are hard-coded in app/ (owned by W3-C).
- [x] W3-B automatic update pipeline: discover (CMR) -> ingest -> catalog -> manifest sync -> daily Action `.github/workflows/update.yml`; see docs/PIPELINE.md. Needs the user: secret EARTHDATA_TOKEN, push, Pages on (agent: Sonnet)
- [x] W3-C dashboard: timeline of all scenes, "Save this day" + permalinks, fix 404s (agent: Sonnet, 14 Nov). Done: 404s were size-probe HEADs with a wrong path (fixed); class-map PNGs 404 only if ticked (UI shows "Not loaded yet"); dates come from manifest layers (type nisar, ready); date timeline on the map for Radar/Before-after/Eye; "This view" card with Save this day / Copy link / Download this day / Saved days; view state in the URL hash; layer table no longer scrolls sideways; fit-after-mode-switch fixed. Saved days live in localStorage (per browser). Open: class PNGs still missing in data/processed/img/ (W3-A).
- [ ] W3-D S-band: blocked until the user downloads the 4 scenes (needs their Bhoonidhi login)
- [ ] W3-E final evaluation of data use and presentation (agent: Fable), after A–C
- [ ] W3-F review of the professional tab -> docs/review/PRO_TAB_REVIEW.md (agent: Sonnet, read-only)
- [ ] W3-G spec for a live, newsletter-style public tab driven by the latest scenes -> docs/review/LIVE_STORY_SPEC.md (agent: Sonnet, read-only)
- [ ] W3-H implement F + G after W3-C finishes (avoid two agents editing dash.js at once)
- Order agreed with the user: the Fable evaluation (W3-E) runs LAST, only after A, B, C, H and S-band are done (or the user says to go without S-band).
- W3-F done: docs/review/PRO_TAB_REVIEW.md (top 10). W3-G done: docs/review/LIVE_STORY_SPEC.md (critical path: per-scene stats -> build_story.py -> renderStory).
- Decisions on the spec's open questions (Opus, 14 Nov): (1) ONE mandal_rank.json with a `by_date` section
  (one fetch; also feeds the per-mandal sparkline from PRO review #5) rather than separate files;
  (2) event files are written by a human (or a Claude session on request); the pipeline may create a draft stub that
  never publishes until marked active; (3) "since last pass" compares with the previous pass, plus a second sentence
  for total change since landfall. Permalink format must be shared with W3-C's hash state (read dash.js first).
- W3-B decisions (Opus): ingest the 6 extra SEA scenes (T120 D, T127 A; 8 Oct, 20 Oct, 1 Nov) as layers that are off by default
  (partial sea coverage, not eye passes). The timeline must handle several tracks per role. Small fix pending in
  sync_manifest.py: refresh processing_level/product_status when a provisional scene is replaced by a validated one.
- W3-A done (see docs/METHODS.md). Honest status: new water on 9 Nov = 84 km2 (1.6% of land; 61-108 km2 by threshold) vs 0.04% in a
  normal fortnight -> real signal; wet-crops class NOT separable from normal field change -> keep it labelled weak or drop it from the
  public tab; eye found at 16.226 N 82.539 E, 4.4 km from the old placeholder marker, 10 km from the IMD fix (faint, 0.76 dB).
  9 Nov water also includes Cyclone Murasu + river peak, not Arnab alone; say so.
- Gap for the live product: build_web.py writes class layers into the manifest only with --write-manifest; when a new COAST scene
  arrives, the pipeline must recompute class maps/mandal_rank for the NEWEST coast date and point the class layers at it
  (and add by_date to mandal_rank.json per the W3 decision). -> W3-H phase 2.

## W3-H phase 1 (14 Nov, Sonnet) — done: PRO review #1, #6, eye wording, LIVE_STORY tasks 1/2/4, official-warning line
- Scenes card (Data tab) now built from `data/h5/catalog.json` (falls back to manifest layers if missing): date + start time UTC and IST, band, role, track/frame, A/D, pols, posting m, PROVISIONAL/VALIDATED chip on every row, size, sha256 (12 chars, Copy button copies the full hash). Newest first; any number of tracks per role. New catalogue rows appear with no code change. Latency ("in catalogue after ...") shows only if a scene carries `cataloged_utc`/`ingested_utc`/`added_utc`; catalog.json has no such field today, so it is not shown.
- Downloads card: per-scene H5 link with size + sha256 from catalog.json, "Cite this" (Copy citation text / Copy BibTeX, authors "SpaceBros (NASA Space Apps 2026)", NASA/JPL-Caltech + ISRO via ASF DAAC credit, URL of the page), method-notes link (docs/METHODS.md if present, else "method notes coming"), "For scripts" row (catalog.json, manifest.json). If the clipboard is blocked the citation opens and is selected.
- Eye-profile card text now comes from profile.json (`points_definition`, caveat, notes, eye fields); axis label says "change in brightness" when the definition says minus/difference; y range follows the data. Nothing in profile.json edited.
- Official-warning line ("Not an official warning ...", IMD / APSDMA / SACHET links) under the first card on What happened; links from `data/events/arnab-2026.json` `official_links`, hard-coded fallback.
- New files: `data/story_rules.json`, `data/seasons.json`, `data/events/arnab-2026.json`, `app/strings/story.en.json` (no runtime use yet; findings.js untouched except an added `official` string and still the fallback).
- Still open for W3-H phase 2: renderStory(), build_story.py, per-scene mandal_rank by_date, class-map retargeting, feeds; PRO review #2-#5, #7-#10.

## W3-H phase 2 backend (14 Nov, Sonnet) — DONE
- [x] Class maps for every coast date after the baseline; class + sea-difference manifest layers retargeted at the newest date in every build (`class_date`, `diff_date` added); sea difference for every track-48 scene vs 15 Oct, colour-blind-safe ramp with stops in the json.
- [x] `mandal_rank.json` `by_date`, `area_km2`, `flooded_km2`, `change_vs_normal_pp`, `err`, `total_pct`; `rank` = total (water + crops), `rank_water` = water only; headlines use water only (docs/METHODS.md section 2). `tools/check_manifest.py` now checks `rank_basis` and `by_date`.
- [x] dB histograms + `water_threshold_db` in every layer json (PRO review #9); colour-blind ramp (#10 partly: map ramp done, UI legend/contrast is frontend).
- [x] Catalog `cataloged_utc` (+ `produced_utc` / `available_utc` when known); `sync_manifest.py` refreshes `processing_level` on a provisional -> validated upgrade.
- [x] `tools/build_story.py` -> `data/web/story.json`, `feed.json`, `atom.xml`; `tools/tests/test_story.py` (16 tests, plain asserts); `pages.yml` runs build_web, the tests, then build_story. Event file `data/events/arnab-2026.json` has `confounders` (Murasu + river peak, 9 Nov). `app/strings/story.en.json` got extra keys (update.*, mandal.main/low/times, bignums unit); `data/story_rules.json` got `class_basis`, `site_url`.
- Still frontend (next agent): renderStory(), archive + `#...` permalinks, histogram and sparkline drawing, sea-diff legend from `ramp`, read `rank_water`/`flooded_km2`/`by_date`; PRO review #2, #4, #5 (UI parts), #7 done in phase 1.
- Not tested live: a third coast scene arriving through CI (simulated locally with a copy of the 9 Nov file as a fake 21 Nov scene: class maps, manifest, rank by_date all picked it up; peak memory 1.7 GB). Domain-expert review of the English templates is still open (docs/PLACEHOLDERS.md section 7).
- S-band check (14 Nov 17:15 IST): NOT processed. Only a truncated 21 MB start of the 4 Oct coast file (full ~10 GB per its HDF5
  header) existed, from the old non-resuming script; renamed to .h5.part so the new script resumes it. Other 3 files not downloaded.
  At ~0.2 MB/s each file takes ~14 h; prefer the Bhoonidhi portal's subsetting tool (delta box 81.6,16.2,82.6,17.1) if available.

## W3-H phase 2 frontend (14 Nov, Sonnet) — DONE (app/dashboard-mockup only)
- Public tab renders from `data/web/story.json` (`renderStory`, falls back to findings.js text if the file is missing): masthead (state eyebrow, provisional badge from `badges.provisional`, "Sample values" only if `badges.sample`), headline + the `since_last` box (text + went down / about the same / went up counts) always next to it, lead (confounder sentence shown once as its own "Other causes" note), 84 km2 class summary, 3 big numbers (value, unit, label; first has the +- from `err`), "Show on the map" (opens `map.mode` + the `map.layer_id` class overlay), next-pass line, picture/build timestamps, official-warning line, "Find your mandal" search over `mandal_sentences` (a click on the map shows the same sentence; unranked mandals say "not enough radar view"), the existing ranking/mandal/cyclone cards, "Earlier updates" archive from `updates[]` (each links by its `hash`; "Save" stores it in the existing saved days without moving the view), JSON/Atom feed links. State variants tested by overriding the story in the console (`window.__spacebros.setStory(obj)`): event, recovery, watch (no ranking/cyclone cards), stale (older-picture note), `numbers_ready:false` (only "Pictures are ready, numbers are coming", no lead/numbers/ranking), sample badge.
- Public ranking and mandal card now use OPEN WATER only (`rank_water`, `water_pct`, `normal_water_pct`), as the backend decided; wet crops are not shown there (weak signal).
- Flood share map: day selector (28 Oct / 9 Nov) from `mandal_rank.by_date`; hash `mode=share&d=` now honoured, so archive and saved days restore the right day. Class PNG for the chosen day is derived from the manifest class layer name (`class_YYYYMMDD_*.png`).
- Pro tab: layer table verified (no sideways scroll at 1400 and 800; long limits in an expandable "Limits" row; "Weak signal" tag on the wet-crops layer); mandal table = rank by `rank_water` with toggle to water + crops, water % +- (with "not distinguishable from zero" when err >= value), flooded km2, change vs normal in points, sparkline per mandal from `by_date`, list of unranked mandals; eye profile annotated (eye edge with shaded +- band, eyewall ring, IMD-fix offset marker, peak); "Radar by date" small multiples (all coast and sea dates, click puts it on the map); brightness histogram card per scene with the water cut line (coast) and share below the cut; legends: dB greyscale bar, sea-difference colour ramp from `ramp.stops`, class colours with text labels (wet crops marked weak signal).
- Hard-coded "Sample values" / "Quick-look sample" tags removed wherever the data is real (manifest placeholder null, `badges.sample` false); they still appear automatically if a layer/rank/profile carries `placeholder.is` or the story sets `badges.sample`.
- Bugs fixed on the way: eye-profile hover threw (`L` shadowed Leaflet); an unbroken alert headline made the page 1031 px wide at 800 px.
- Still placeholder / open: S-band (none yet); no English-template domain review; HEAD size probes show `net::ERR_ABORTED` in the browser tool but return 200 (tool artefact, all GET requests 200, no 404s, no console messages); the "Water + crops" table mode scrolls sideways inside its box at 800 px; mandal-card and ranking still read the newest day, not the day chosen in the share-map selector.

- Open (Opus, 14 Nov 17:40; alerts part DONE in Wave 4): data/processed/alerts.json holds Jammu & Kashmir SACHET alerts, not Andhra Pradesh -> wrong region on
  the alerts card; refetch AP alerts (src/fetch/sachet_snapshot.py) or mark it placeholder. Rename the sea-diff layer id to match
  its date when convenient (update dash.js references). Mandal card should follow the share-map day selector.
