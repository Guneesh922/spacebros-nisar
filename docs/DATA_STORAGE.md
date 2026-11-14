# Where the data lives (decided 14 Nov 2026)

## Decision
1. **Full granules** (L-band 0.85–7.5 GB, S-band similar) are *inputs only*. They are streamed (HTTP range reads)
   or downloaded temporarily to `data/raw/` (git-ignored), subset, verified, then deleted. They are always
   re-fetchable from ASF / Bhoonidhi by the `source_granule` attribute in each subset.
2. **Study-box H5 subsets** in `data/h5/` are the data of record and are **committed to plain git**.
   Target ≤ 50 MB per file (GitHub warns at 50 MB, rejects at 100 MB) and ≤ 600 MB for the whole folder.
   - If a coast file at native posting exceeds 50 MB: 2×2 multilook (all coast scenes the same posting).
   - If the folder still exceeds ~600 MB: Git LFS for `data/h5/*.h5`. Current free tier (checked 14 Nov 2026):
     10 GiB storage + 10 GiB/month bandwidth, 2 GB per file. Note: GitHub Pages does not serve LFS content,
     so the Pages build must check out with `lfs: true` (it does).
   - Zenodo / Hugging Face only if the subsets ever pass ~5 GB (not expected).
3. **Browser assets** (display PNG per layer, stats JSON, class maps, mandal_rank.json, profile.json) are
   derived by `tools/build_web.py` into `data/web/` (git-ignored) and published by the GitHub Actions
   Pages workflow. The dashboard reads `layer.png` as before; the manifest points it at `data/web/...`
   and gives the source in `layer.h5`.

## Measured and decided (14 Nov 2026)
L-band coast native 10 m = 232 MB/file (too big). 2×2 → 20 m = 56–57 MB/file: **chosen**. Under GitHub's 100 MB
hard limit (it prints a >50 MB warning on push; acceptable). Sea at 100 m = 7–14 MB/file. Expected L-band total
≈ 270 MB, plain git, no LFS. Revisit only if S-band subsets push `data/h5/` past ~600 MB.
Note: 2×2 medians read ~1 dB higher than native; expected (mean of speckled linear power vs median), not a bug.

## Subset file naming
`data/h5/{band}_{role}_{YYYYMMDD}_T{track:03d}.h5`, e.g. `data/h5/L_COAST_20261004_T055.h5`,
`data/h5/S_COAST_20261016_T055.h5`. Role ∈ COAST (delta box) | SEA (sea box).

## Boxes (WGS84 W,S,E,N; from data/sources.yaml)
- delta (coast): 81.6, 16.2, 82.6, 17.1 — **20 m posting (2×2 multilook of the native 10 m L-band grid; always pass `--multilook 2`)**, pols HH+HV (L) / DH pair (S)
- sea: 81.0, 15.0, 85.0, 18.0 — 100 m posting (block mean in linear power), pols VV+VH (L; HV if quad file)

## H5 subset schema (v1)
Root attributes:
`schema="spacebros-subset-v1"`, `scene_id` (role id from scene_manifest_full.csv, e.g. L_COAST_1004),
`band` (L|S), `role` (COAST|SEA), `source_granule` (full product id), `source_url`, `source_collection`,
`product_status` (PROVISIONAL|VALIDATED), `track`, `frame`, `direction` (A|D), `start_utc`, `end_utc`,
`box_name`, `bbox_wgs84` [W,S,E,N], `epsg`, `posting_m`, `multilook` (int k for k×k), `created_utc`,
`software` (script name + git short sha), `bounds_latlon` [[S,W],[N,E]] true footprint of the data written.

Datasets:
- `/grid/x` float64 (ncol), `/grid/y` float64 (nrow): projected pixel-centre coordinates, `y` descending (north-up). attr `epsg`.
- `/backscatter/{POL}` int16, value = round(gamma0_dB × 100); attrs `scale_factor=0.01`, `units="dB"`,
  `quantity="gamma0 (RTC), from GCOV {POL}{POL} linear power"`, `_FillValue=-32768`.
  POL names: `HH`, `HV`, `VV`, `VH` (S-band: whatever the product holds, same rule).
  Storage: chunks 256×256, gzip level 6, shuffle.
- `/aux/mask` uint8 (copied, nearest), `/aux/numberOfLooks` float16 (optional).
- `/metadata/orbit_pass` etc.: optional copies of small identification fields.

Readers must apply `scale_factor` and fill. 0.01 dB quantisation is far below speckle (~1 dB), so int16 is
lossless for every product we derive.

## Build step
`python tools/build_web.py` reads `data/processed/manifest.json` and every `data/h5/*.h5`, writes to
`data/web/`: `{layer_id}.png` (greyscale, fixed dB stretch per role, transparent fill, EPSG:4326 warp for
Leaflet `imageOverlay`), `{layer_id}.json` (bounds, percentiles, nan fraction), and the derived products.
`.github/workflows/pages.yml` runs it on push to main and deploys the site to GitHub Pages
(user must set Settings → Pages → Source: GitHub Actions once).

## Areas, events and alerts (Wave 4, 14 Nov 2026)
Adding an area is one config entry; numbers start once that area has two calm baseline passes.

### `config/areas.json` (schema `areas-v1`)
Read through `tools/pipeline/common.py`: `load_areas(root=None, path=None)` (whole document) and `area(id=None)` (one area, default
`default_area`; adds `_defaults`). Env `SPACEBROS_AREAS=<file>` (or `--config` on discover/ingest/alerts/events) selects a scratch config.
Keys: `site` {title, tagline, name_options}; `default_area`; `defaults` {aftermath_days 30, search_since}; per area `id`, `name`,
`state`, `country`, `boxes` {COAST, SEA} (W,S,E,N), `roles` {pols, posting_m, multilook, min_cover, analysis}, `tracks`
{role: [{track, direction, frame}]}, `baselines` (COAST: per track `season` (an id in data/seasons.json) + two calm `dates`;
SEA: per track `reference_date`), `boundaries.mandals`, `alert_match` {bbox, states, keywords}.
Used by: `discover.py` (search box = union of boxes, per-role pols and min_cover), `ingest.py` (posting per role),
`build_web.py` (COAST baseline dates, mandal boundary file; falls back to the manifest if the config cannot be read).
`data/sources.yaml` boxes stay as history only. A second area with no data does not change anything for the first one.
Open limit: `data/h5/catalog.json` is not yet split per area; `discover.py` compares against the whole catalogue.

### `data/processed/alerts.json` (schema `alerts-v2`) — written by `tools/pipeline/alerts.py`
`{schema, area_id, built_utc, gdacs{fetched_utc, ok, error, url, credit, items[]}, sachet{snapshot_utc, ok, error, url, credit,
items[], feed_item_count, feed_pubdate, feed_newest_item}, none_text}`. GDACS item: id, type (TC|FL), name, alert_level
(Green|Orange|Red), from, to (UTC), link, countries, current (bool), point [lon,lat], severity_text. SACHET item: id, headline,
area (CAP areaDesc), issued (IST), source (issuing office), link, category.
GDACS: public API `gdacsapi/api/events/geteventlist/SEARCH` (TC + FL, last 60 days, 100 per page); kept when the event point
touches `alert_match.bbox`. SACHET: `rss_india.xml` + each item's CAP areaDesc; kept when headline + areaDesc + office mention
a state or a whole-word keyword. A failed fetch keeps the previous items with their old real timestamp and sets `ok:false` plus
`error`. `--fixture <json>` replaces the network (simulations); `--now` fakes the clock. `tools/check_manifest.py` validates v2
(the old snapshot shape is still accepted). Nothing in this file says radar confirms an alert.

### `data/processed/events.json` (schema `events-v1`) — seeded by hand (Arnab), maintained by `tools/pipeline/events.py`
One entry per event: `id, name, type (cyclone|flood), area_id, start, end, aftermath_days, window_source, source, credit,
severity {as_given, by}, status (alert_only|radar_linked|closed|dismissed), status_text, reviewed_by_human, linked_passes
[{scene_id, date, role, relation (during|after), radar_finding (change_seen|no_clear_change|numbers_coming|sea_no_public_finding)}],
description, cannot_tell[], confounders[], story{landfall_caption, eye_profile, before_after, murasu_caveat, ...} (+ `story_from`
saying which app file each sentence was copied from), landfall, imd, baseline, official_links, alert_refs[], edit_log[]`.
Rules: a pass is linked when its date lies in [start, end + aftermath_days] of an event in the same area ("during" up to `end`,
"after" beyond); auto drafts are `auto_<SOURCE>_<id>`, `alert_only`, `reviewed_by_human:false`, created only from cyclone/flood
alerts still inside their window; an alert that overlaps a human-reviewed event of the same type is added to its `alert_refs`
instead of creating a duplicate; human events are never deleted or rewritten (only `alert_refs` and `linked_passes` grow).
Idempotent (a second run changes only `updated_utc`). The findings step sets `radar_finding` with
`events.set_radar_finding(events, event_id, scene_id, finding)`.
Arnab window: 24 Oct to 28 Oct 2026, from the IMD press releases in `docs/imd_bulletins/` (see `window_source`); the end is the
date of the last bulletin, not an IMD-stated end. `data/events/arnab-2026.json` stays in place until the readers are switched.
Tests: `python tools/tests/test_events.py`.
