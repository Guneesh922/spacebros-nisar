# Automatic update pipeline (W3-B)

Goal: new NISAR L-band passes over the study area appear on the dashboard without anyone downloading anything.

## What runs when
`.github/workflows/update.yml` runs **daily at 05:23 UTC** (10:53 IST) and on demand (Actions -> "Update NISAR data" -> Run workflow; tick *dry_run* to only list). Runs never overlap (concurrency group `nisar-update`).

| step | tool | what it does |
|---|---|---|
| 1 discover | `tools/pipeline/discover.py` | Asks NASA CMR (public, no login) for NISAR_L2_GCOV_V1 (validated) and NISAR_L2_GCOV_PROVISIONAL_V1 granules from 2026-10-01 that touch the delta box or the sea box. COAST = covers >= 50 % of the delta box with HH; SEA = covers >= 20 % of the sea box with VV. Duplicates of one pass (validated vs provisional, PR vs UR, several modes) collapse to one: validated > PR > coverage > smaller. Compares with `data/h5/catalog.json`: NEW scenes, and UPGRADES (provisional we hold, validated now available). |
| 2 ingest | `tools/pipeline/ingest.py` | For each new scene runs `src/fetch/subset_h5.py` on the ASF HTTPS URL with range requests (only the box window is read; nothing large on disk). COAST 20 m (2x2 of 10 m), SEA 100 m. Output goes to a temp dir; a subset > 90 MB is refused and discarded. Max 6 scenes per run, the rest next day. |
| 3 catalog | `tools/pipeline/catalog.py` | Rebuilds `data/h5/catalog.json` from the H5 attributes (file, scene_id, band, role, date, track, frame, direction, product_status, source_granule, posting_m, size_bytes, sha256, bounds_latlon...). `--check` tells whether it is current. |
| 4 manifest | `tools/pipeline/sync_manifest.py` | Adds a layer `nisar_l_<coast|sea>_YYYYMMDD_t<track>_<hh|vv>` per new scene; for existing layers only touches `h5`, `png`, `bounds`, `status`. A no-op when nothing changed. Then `tools/check_manifest.py` validates. |
| 5 commit + deploy | workflow | Bot commit of `data/h5/` + manifest to `main`, then `gh workflow run pages.yml` (a push by `GITHUB_TOKEN` does not trigger other workflows, but `workflow_dispatch` is allowed). Pages runs `tools/build_web.py`, which builds the PNGs for the new layers. |

No new scenes: the job ends after step 1 with no commit and no deploy.

New layers get a generic name ("Sea surface, 2026-11-01 (T120)"), `default_on: false`, group before/during/after by date (27-28 Oct = during) and their own `latest_of` series for tracks other than 55 (coast) / 48 (sea), e.g. `nisar_l_sea_t120_vv`. Rename or re-group by hand in the manifest; sync never overwrites those fields again.

Known limits: every new SEA track (T120, T127...) is shown as a sea layer even though the sea box is only 20-30 % covered; classification thresholds are in `discover.py` (`MIN_COVER`). Coast passes of other tracks are picked up automatically if they cover the delta. Class maps, mandal ranking and profile (W3-A) are not run by update.yml; the Pages build re-runs them (next section).

## One-time setup (user)
1. **Earthdata token**: log in at https://urs.earthdata.nasa.gov -> *Generate Token* (user token, valid ~60 days; renew and update the secret when it expires, the run fails with a clear error). Repo -> Settings -> Secrets and variables -> Actions -> New secret `EARTHDATA_TOKEN`. The ASF DAAC app must be authorised on that account (EULA accepted: it already is if downloads worked with `~/.netrc`).
2. **Pages**: Settings -> Pages -> Source: *GitHub Actions* (also needed by `pages.yml`).
3. Settings -> Actions -> General -> Workflow permissions: allow read and write (the workflow also sets `contents: write`, `actions: write` itself; org policies can override).
4. Push the workflow files (nothing has been pushed from the device shell yet).

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
