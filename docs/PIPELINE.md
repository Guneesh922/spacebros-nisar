# Automatic update pipeline (W3-B)

Goal: new NISAR L-band passes over the study area appear on the dashboard without anyone downloading anything.

## What runs when
`.github/workflows/update.yml` runs **daily at 05:23 UTC** (10:53 IST) and on demand (Actions -> "Update NISAR data" -> Run workflow; inputs *dry_run* = only report, *offline* = skip discovery/ingest and keep the old alerts). Runs never overlap (concurrency group `nisar-update`). The workflow only calls **`tools/pipeline/run_all.py`**, the one file that holds the step order; the local simulations (`tools/sim/`) call the same file.

| # | step | tool | what it does |
|---|---|---|---|
| 1 | discover | `discover.py` | NASA CMR (public): NISAR L2 GCOV granules touching the area's boxes (`config/areas.json`). **Only tracks configured for the role in `config/areas.json` (`tracks`) are NEW and ingested; other qualifying tracks are listed as "other tracks seen, not ingested (add to config/areas.json to include)".** COAST = covers >= 50 % of the delta box with HH; SEA = >= 20 % of the sea box with VV. Duplicates of one pass collapse (validated > PR > coverage > smaller). Compares with `data/h5/catalog.json`: NEW scenes and UPGRADES (provisional -> validated). CMR unreachable = warning, the run goes on. |
| 2 | ingest | `ingest.py` | Only if step 1 found something. Stream-subsets each scene over HTTPS range requests (box window only), 90 MB guard, max 6 scenes per run. **Needs `EARTHDATA_TOKEN`; if scenes are new and the token is missing the run fails here with a clear message** (no new scenes = no token needed). |
| 3 | verify_h5 | run_all | Every `data/h5/*.h5` must open. One that does not is left out of the catalogue and listed in the summary (`unreadable_h5`) and as a warning; the workflow never commits it. |
| 4 | catalog | `catalog.py` | `data/h5/catalog.json` from the H5 attributes. |
| 5 | sync_manifest | `sync_manifest.py` | Manifest layers for new scenes. |
| 6 | alerts | `alerts.py` | GDACS + SACHET -> `alerts.json` (alerts-v2), filtered by `alert_match`. A failed source keeps its old items with the real old timestamp. |
| 7 | events | `events.py` | Draft events from cyclone/flood alerts (`auto_<SOURCE>_<id>`, `alert_only`, not reviewed); links catalogue passes to every event whose window holds their date. |
| 8 | build_web | `tools/build_web.py` | PNGs, class maps, `mandal_rank.json` (by_date), `profile.json`. A failure here (e.g. a pass whose data cannot be read) is a WARNING: that pass has no numbers, so step 10 gives it **numbers_coming**; the numbers of an older pass are never shown as new. |
| 9 | tests | `test_story.py`, `test_findings.py`, `test_events.py`, `check_manifest.py` | ALL must pass. Any failure = **exit 2**: step 10 and 11 do not run, the old findings stay, nothing is deployable. |
| 10 | build_story | `tools/build_story.py` | `findings/<pass-date>.json` (write-once), `findings/latest.json` (rebuilt every run, so "age of the last pass" stays true), `data/web/story.json`, `feed.json`, `atom.xml`. States: big_change, quiet, no_new_pass, numbers_coming, no_baseline. |
| 11 | persist | run_all + `events.persist_radar_findings` | Each event's linked pass gets its `radar_finding` (change_seen / no_clear_change / numbers_coming) in `events.json`. |
| 12 | events again | `events.py` | Must change nothing but the stamp (reported as `events_idempotent`). |

**Exit codes**: `0` all good (deployable) | `2` tests failed | `1` any other error. A JSON summary (steps, seconds, result, changed files, warnings) goes to stdout and to `--summary <file>`. Flags: `--root --now --offline --skip-ingest --dry-run --area --summary --alerts-fixture`. `--now 2026-11-21T10:00Z` sets the clock of alerts, events, discovery and the story (the catalogue stamp `cataloged_utc` still uses the real clock).

### Gating in update.yml (decision 5 of the Wave 4 plan)
| what | when it is committed |
|---|---|
| `data/h5/*.h5`, `data/h5/catalog.json`, `data/processed/manifest.json` | **always**, when changed (data of record). An unreadable H5 is never staged. |
| `data/processed/findings/`, `events.json`, `alerts.json`, `mandal_rank.json`, `profile.json` | **only if run_all exited 0** |
| Pages redeploy (`gh workflow run pages.yml`) | only if exit 0 **and** something was committed |
| the job | green on exit 0; **red** on exit 1 or 2, after the data of record was committed |
A day without a new pass still refreshes `alerts.json`, `events.json` and `latest.json` (age), so the daily run normally commits and deploys a small change. `EARTHDATA_TOKEN` is in the environment of the "Run the pipeline" step only and `run_all.py` removes it from every sub-process except ingest; it is never printed (output is masked).

`pages.yml` (on every push to main and on dispatch): build_web (a failure is a warning, same rule as above), **all four test commands (any failure = no deploy)**, build_story, then the site: `app/`, `data/processed/` (includes `findings/`), **`config/`** (the page reads `config/areas.json`), `data/reference/` small files, `data/web/`, `data/h5/`.

SACHET from the runner: not known yet whether the NDMA server answers GitHub's IP ranges. If it does not, `alerts.py` fails soft: the previous SACHET items stay with their real snapshot time, `ok:false` and the error are in `alerts.json`, the run only prints a warning. GDACS is public and worked from the Mac. Look at the first scheduled run's summary (`warnings`).

Known limits: **only configured tracks are ingested** (COAST T055, SEA T048 today). Discovery still lists other qualifying tracks (e.g. SEA T120 F080 and T127 F010, 6 scenes, 8 Oct to 1 Nov 2026) under "other tracks seen, not ingested (add to config/areas.json to include)", so nothing is hidden. This reverses the earlier W3-B note that every new SEA track is ingested automatically. Why: a track needs a baseline entry to give honest numbers, and silently adding sea layers (each 0.9 to 1.3 GB, sea box only 21 to 32 % covered) would be surprise data. Adding a track = adding it to the config (`tracks` and, for numbers, `baselines`); the next run ingests it. Coast passes of an unconfigured track are likewise not ingested; a coast scene already in the catalogue without a baseline gets `no_baseline` until the track is configured.

New layers get a generic name ("Sea surface, 2026-11-01 (T120)"), `default_on: false`, group before/during/after by date (27-28 Oct = during). Rename or re-group by hand in the manifest; sync never overwrites those fields again.

### Notes from building the simulations (14 Nov 2026)
1. (Fixed) `test_findings.py::test_real_data_every_pass_validates` used to hard-code the 9 Nov pass as the newest; it now uses `passes[-1]`. The simulations no longer patch any test.
2. **Local `data/web/` is a git-ignored build product and may be older than `build_web.py`**: the first run after a code change can revise a findings file once (revision +1, `changed: ["class_stats"]`). Harmless but visible; the simulations first do one "settle" run for that reason.
3. The `quiet` template needs a pass with NO flooded mandal and no mandal change since the previous pass, so it cannot follow a flooded pass (scenario `copy_of_last_pass` therefore gives big_change; use `quiet_pass_calm` for quiet).

## One-time setup (user)
1. **Earthdata token**: log in at https://urs.earthdata.nasa.gov -> *Generate Token* (user token, valid ~60 days). Repo -> Settings -> Secrets and variables -> Actions -> New secret `EARTHDATA_TOKEN`. When it expires the run fails on the first day with a new scene, with the message "no Earthdata login ... set the repo secret EARTHDATA_TOKEN". The ASF DAAC app must be authorised on that account (EULA accepted).
2. **Pages**: Settings -> Pages -> Source: *GitHub Actions*.
3. **Workflow permissions**: Settings -> Actions -> General -> Workflow permissions: *Read and write permissions* (the workflow also asks for `contents: write`, `actions: write`; an organisation policy can override).
4. Push the workflow files and `config/`, `tools/`, `data/processed/events.json`, `data/processed/findings/` (nothing has been pushed from the device shell yet), then run "Update NISAR data" once with *dry_run* ticked and read the job summary.

## Simulations (no network, no real data touched)
Everything runs in a scratch copy (`rsync`, without `.git .venv data/raw`); the report ends with a guard that checks the real repo's `data/h5`, `findings/`, `events.json`, `alerts.json`, `manifest.json` and `config/` by sha256 before and after.
```
.venv/bin/python tools/sim/run_sim.py new_pass_change --out <scratch>/sim/new_pass_change   # report in <scratch>/sim/reports/
# scenarios: new_pass_change copy_of_last_pass quiet_pass_calm missing_pass analysis_failed analysis_truncated no_baseline
#            ap_alert ap_alert_quiet ap_alert_calm
tools/sim/emulate_workflow.sh <scratch>/sim/workflow   # runs the run: blocks of update.yml and pages.yml in order, local bare git remote
```
Each scenario: settle run -> inject a fake pass (`_SIMULATED` granule name) -> `run_all.py --offline --now <date>` -> report (headline, template_state, three numbers, top 5 mandals, pass list, chips, events, files changed, 9 Nov archive sha before/after, number-versus-source check). `tools/sim/emulate_workflow.sh <scratch> --force-test-failure` injects a failing test into the scratch copy and checks the gate: run_all exit 2, no findings/events/alerts commit, no Pages redeploy call, pages.yml builds no site. The emulator needs PyYAML in the venv only (`.venv/bin/pip install pyyaml`). Scenario `copy_of_last_pass` (was `quiet_pass`) = 21 Nov copy of 9 Nov; it is NOT a quiet test.

## Run by hand
```
python tools/pipeline/discover.py --all            # what CMR has vs what we have (stdlib, no login)
python tools/pipeline/ingest.py --dry-run          # show the subset commands, download nothing
export EARTHDATA_TOKEN=...                         # or ~/.netrc
python tools/pipeline/ingest.py                    # fetch + subset + catalog
python tools/pipeline/sync_manifest.py --dry-run   # then without --dry-run
python tools/check_manifest.py && python tools/build_web.py
```
Venv: `/tmp/venv-nisar` (h5py numpy pyproj pillow).

## S-band in one command
Bhoonidhi needs your own login, so this runs in YOUR terminal (the password is typed at a hidden prompt; it stays in memory and is never written anywhere). The full GCOV files are ~10 GB each at ~0.2 MB/s; this command does NOT download them: it asks the server for byte ranges and reads only the chunks of the study box, then writes the small schema-v1 H5 straight to `data/h5/`.

One-time setup (Mac terminal, repo root): `python3 -m venv .venv && .venv/bin/pip install h5py numpy pyproj`, then use `.venv/bin/python` below (or any python with those three packages).

```
cd ~/Documents/nsa/05_Code/spacebros-nisar          # your repo folder
.venv/bin/python src/fetch/bhoonidhi_s_band.py subset --preset arnab --only COAST   # the 3 coast scenes first
.venv/bin/python src/fetch/bhoonidhi_s_band.py subset --preset arnab --only SEA     # the sea scene (big, see below)
```
(without `--only` it does all four: 4 Oct, 16 Oct, 28 Oct T055 F10 DHNA -> delta box; 3 Oct T048 F80 CRNA -> sea box.) Add `--plan` to any call to log in, check that Range works and print the compressed bytes each scene needs, without writing anything. One scene by id: `subset --id <ITEM_ID> --role COAST --scene-id S_COAST_1004`.

What you will see: `logged in`, then per scene `range requests OK, file size 10.0 GB`, the grid line (EPSG, native spacing, multilook, e.g. `multilook 2 -> ... @ 20 m`), a progress line every ~10 s (`fetched 143.2 MB of 10011 MB (1.43 % of the file) in 40 requests, 0.35 MB/s average`), then `wrote data/h5/S_COAST_20261004_T055.h5 ...` with median dB per polarisation and the fetched total. If the % of the file is climbing past ~10 % on a coast scene, press Ctrl-C and tell us.

Expected volume (estimate from the product footprints, not measured): delta box = 10,600 km2 of a ~186,000 km2 F10 frame = 5.7 %, and only HHHH + HVHV (+ mask) are read, so roughly 0.2 to 0.4 GB per coast scene, about 15 to 30 min each at 0.2 to 0.3 MB/s (3 parallel range requests may be faster). The sea box covers about 51 % of the T048 frame, so the sea scene is the expensive one: roughly 1.5 to 3 GB (RHRH + RVRV only), one to three hours at the same speed. The real numbers appear in `--plan`. Output: `S_COAST_{date}_T055.h5` (HH, HV at 20 m) and `S_SEA_{date}_T048.h5` (RH, RV compact-pol at 100 m, root attr `pol_basis="compact-circular-transmit"`; RH/RV are circular-transmit, linear-receive channels, not comparable dB-for-dB with VV/VH). Dataset names for S-band are whatever diagonal terms the file holds (`HHHH`, `HVHV`, `RHRH`, `RVRV`...).

If the server does not honour Range (the script checks first and stops with `STOPPING: ... does not support HTTP Range`; it never falls back to a full download): use the portal's own subset/clip download (delta box 81.6,16.2,82.6,17.1), or accept the full file, and run on the file:
```
.venv/bin/python src/fetch/bhoonidhi_s_band.py subset --local <file.h5> --role COAST --scene-id S_COAST_1004 --granule <item id>
```
(or `tools/pipeline/ingest.py --local ...` as below; both call the same subsetter). Then `python3 tools/pipeline/catalog.py` and commit `data/h5/`.

Notes: the download API allows 2 requests/min and 5 concurrent per the Bhoonidhi spec; on HTTP 429 the script waits and drops to one request at a time. Transient errors are retried with backoff; a 401 renews the token with the password already typed.

## S-band (ISRO, Bhoonidhi), whole-file route
Bhoonidhi needs an interactive login, so S-band cannot run in CI. To add scenes:
1. On your computer: `python src/fetch/bhoonidhi_s_band.py download ...` (resumable; asks for your portal login).
2. `python tools/pipeline/ingest.py --local <S-band.h5> --role COAST --scene-id S_COAST_YYYYMMDD_T055 --status PROVISIONAL --granule <granule id>` (band is detected from the file; posting defaults 20 m COAST / 100 m SEA, override with `--posting`). Same mechanism for any manual L-band file.
3. `python tools/pipeline/sync_manifest.py` adds layers only for L-band HH/VV today; S-band layers are still added by hand until S-band product naming is settled (W3-D).
4. Commit `data/h5/` + catalog + manifest and push; Pages rebuilds.
Delete the full S-band granule afterwards.

## Not tested live
CMR discovery and the dry run were run live (14 Nov 2026). The streaming download with a token was not (no credentials in the dev shell); subset_h5.py was tested on a local synthetic granule only. S-band `subset` was tested only against a local Range-capable test server (login, redirect, auth only to the API host, 206/200 detection) with synthetic SSAR files; never against the real Bhoonidhi server (14 Nov 2026).

## Derived products follow the newest data (W3-H phase 2)
`pages.yml` runs, in this order: `tools/build_web.py` -> `python tools/tests/test_story.py` -> `tools/build_story.py` -> site assembly. Nothing needs to be edited when a new scene arrives:
- **Class maps**: `build_web.py` classifies EVERY coast scene of the baseline track newer than the baseline (4 and 16 Oct) and writes `data/web/class_{YYYYMMDD}_{new_water,wet_crops,no_change}.png` + `class_stats.json` (`latest_date`). Baseline-derived numbers (water threshold, permanent water, noise sigma) use the two baseline scenes only, so old dates never change when a new date is added. Memory peak about 1.7 GB with 3 event dates (one date held at a time).
- **Manifest**: in every normal build (not only with `--write-manifest`; `--no-write-manifest` turns it off) the three `nisar_class_*` layers are pointed at the newest date (`png`, `bounds`, `date`, new `class_date`, `period`, `h5_sources`, `limit`, `processing`) and the `nisar_sea_diff_*` layer at the newest sea scene of its track against the calm 15 Oct reference (`png`, `bounds`, `date`, `time_utc`, `diff_date`, `diff_reference_date`, `diff_dates`, `h5_sources`, `name`, `shows`, `ramp`). Only those layers are touched and the file is rewritten only if something changed. The layer id stays `nisar_sea_diff_20261027_vs_20261015`; the PNGs of every date exist as `data/web/nisar_sea_diff_{date}_vs_20261015.png`.
- **Rank file**: `data/processed/mandal_rank.json` keeps the newest date at top level and adds `by_date` (see METHODS.md section 2).
- **Per-layer json** (`data/web/{layer}.json`): `hist` (dB histogram per polarisation, -35..5 dB, 0.5 dB bins) and, for coast layers, `water_threshold_db`.
- **Story**: `tools/build_story.py` (stdlib only) writes `data/web/story.json`, `feed.json` (JSON Feed 1.1) and `atom.xml`. States: `event` (first picture), `recovery`, `watch` (no active event inside `monitor_days`), `stale` (newest scene older than `stale_after_days` while an event is active). Inputs: catalog, `data/events/*.json` (only `status: "active"` publishes), `mandal_rank.json` `by_date`, `profile.json`, `class_stats.json`, `story_rules.json`, `seasons.json`, `app/strings/story.en.json`. The build FAILS (exit 1, Pages does not deploy) on a banned word, a leftover `{placeholder}`, a flood claim without a hedge word, or a sentence over 20 words. Unit tests with fixtures: `python3 tools/tests/test_story.py`.
- **Event files**: add `confounders` (other events that also put water in a scene, `affects_dates` = scene dates) by hand; they feed the story text and the class-layer `limit` text. A new storm = a new `data/events/<id>.json` with `status: "active"`.
- **Catalog** (`catalog.py`): every scene has `cataloged_utc` (first time seen, kept on every rebuild; scenes that existed before this field got the old catalog's `generated_utc`, a lower bound) and, when known, `produced_utc` / `available_utc` (CMR production and update time, written to `data/h5/granule_times.json` by ingest; H5 attrs of the same name win). `sync_manifest.py` now also refreshes `processing_level` (and `product_status` if present) when a provisional scene has been replaced by a validated one.
