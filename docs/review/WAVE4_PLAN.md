# Wave 4 plan: from "Arnab dashboard" to a live coast monitor (Opus, 14 Nov 2026 19:40 IST)

Freeze Sun 15 Nov 16:00 IST. This file is the CONTRACT every agent builds against. If you need to change a
schema here, stop and report; do not improvise a different shape.

## What already exists (do not rebuild)
- `tools/build_story.py` already writes `data/web/story.json` (states event/recovery/watch/stale, `numbers_ready`,
  next pass, since-last comparison, confounders, mandal sentences) from templates in `app/strings/story.en.json`,
  and FAILS the build on banned words, unhedged flood claims, sentences > 20 words, unfilled `{slots}`.
  Tests: `tools/tests/test_story.py`. WP1 EXTENDS this builder; it does not add a second summary engine.
- `tools/build_web.py` already computes class maps for every coast date after the 4+16 Oct baseline and
  `data/processed/mandal_rank.json` `by_date` (share, km2, err, change vs normal).
- Frontend `renderStory()` in `app/dashboard-mockup/js/dash.js` already renders story.json; saved days, permalinks,
  timeline, pro tab tables, histograms exist.
- Python: `.venv/bin/python` (h5py numpy pyproj Pillow). Builders are stdlib + those four only. No PyYAML.

## Review decisions (Opus)
1. `findings/latest.json` is a SUPERSET of today's story.json (same keys + new ones), so renderStory keeps working.
   `build_story.py` keeps writing `data/web/story.json` (= latest.json content) for the feeds.
2. `findings/<date>.json` is write-once: rewritten only when its inputs hash changes (e.g. provisional -> validated
   upgrade); then `revision` +1 and a line in `revision_log`. This is what keeps 9 Nov unchanged in the archive.
3. Event windows come from the source, never guessed. Chip text: "During <name>" if the pass is inside
   [start, end]; "After <name>" if inside (end, end + aftermath_days]; no chip otherwise. Arnab's start/end come
   from the IMD bulletins in `docs/imd_bulletins/`. If 9 Nov is after Arnab's end, the chip reads
   "After Cyclone Arnab" (honest), not "During". This adjusts acceptance #1.
4. Areas live in `config/areas.json` (JSON, not YAML). `data/sources.yaml` boxes stay as history only.
   Honest pitch: "adding an area = one config entry; numbers start once that area has two calm baseline passes".
5. Daily Action: tests gate deploy AND the findings commit. If tests fail, only `data/h5/` + catalog
   (data of record) are committed, nothing is deployed, the job goes red. Alerts/events/latest.json refresh
   every day even without a new pass (so "age of last pass" stays true).
6. One orchestrator, `tools/pipeline/run_all.py`, holds the step order; the workflow and the local simulations
   both call it. Simulations NEVER run in the real repo: they run in a scratch copy.
7. `--now YYYY-MM-DDTHH:MMZ` on every time-dependent step, so missing-pass states can be simulated.

## config/areas.json (schema areas-v1) — owner: WP4 agent
```json
{
  "schema": "areas-v1",
  "site": {"title": "Coast Radar Watch", "tagline": "What the newest NISAR radar passes show on the Andhra Pradesh coast, next to official alerts.",
           "name_options": ["Coast Radar Watch", "Pass by Pass", "Delta Radar Watch"]},
  "default_area": "godavari",
  "areas": [{
    "id": "godavari",
    "name": "Godavari delta and the sea off it",
    "state": "Andhra Pradesh", "country": "India",
    "boxes": {"COAST": [81.6, 16.2, 82.6, 17.1], "SEA": [81.0, 15.0, 85.0, 18.0]},
    "roles": {"COAST": {"pols": ["HH","HV"], "posting_m": 20, "multilook": 2, "min_cover": 0.5, "analysis": "flood_classes"},
              "SEA":   {"pols": ["VV","VH"], "posting_m": 100, "min_cover": 0.2, "analysis": "none_public"}},
    "tracks": {"COAST": [{"track": 55, "direction": "A", "frame": 10}], "SEA": [{"track": 48, "direction": "D", "frame": 80}]},
    "baselines": {"COAST": {"55": {"season": "post_monsoon", "dates": ["2026-10-04", "2026-10-16"]}},
                  "SEA":   {"48": {"reference_date": "2026-10-15"}}},
    "boundaries": {"mandals": "data/processed/mandals.geojson"},
    "alert_match": {"bbox": [80.5, 15.0, 85.0, 18.5], "states": ["Andhra Pradesh"],
                    "keywords": ["andhra","godavari","konaseema","kakinada","yanam","eluru","krishna","bapatla","narsapur","amalapuram","rajamahendravaram"]}
  }]
}
```
(Verify track/frame values against `data/h5/catalog.json`.) Season names must match `data/seasons.json`.

## data/processed/events.json (schema events-v1) — owner: WP2 agent; documented in docs/DATA_STORAGE.md
```json
{"schema": "events-v1", "updated_utc": "...", "events": [{
  "id": "arnab_2026", "name": "Cyclone Arnab", "type": "cyclone", "area_id": "godavari",
  "start": "YYYY-MM-DD", "end": "YYYY-MM-DD", "aftermath_days": 30,
  "window_source": "IMD bulletin <file>: depression formed <date>, weakened <date>",
  "source": {"name": "IMD", "url": "...", "ids": []}, "credit": "India Meteorological Department",
  "severity": {"as_given": "Very Severe Cyclonic Storm", "by": "IMD"},
  "status": "radar_linked",          // alert_only | radar_linked | closed | dismissed
  "status_text": "Radar passes linked",   // alert_only -> "Alert only, not yet seen by radar"
  "reviewed_by_human": true,         // auto-created drafts: false
  "linked_passes": [{"scene_id": "L_COAST_1109", "date": "2026-11-09", "role": "COAST", "relation": "after",
                     "radar_finding": "change_seen" }],   // change_seen | no_clear_change | numbers_coming | sea_no_public_finding
  "description": "...", "cannot_tell": ["..."],
  "confounders": [ ...copied unchanged from data/events/arnab-2026.json... ],
  "story": {"landfall_caption": "...", "eye_profile": "...", "before_after": "...", "murasu_caveat": "..."},
  "landfall": {...from arnab-2026.json...}, "imd": {...}, "baseline": {...}, "official_links": [...],
  "alert_refs": [{"source": "GDACS|SACHET", "id": "...", "issued": "...", "headline": "..."}],
  "edit_log": [{"utc": "...", "by": "pipeline|human", "what": "..."}]
}]}
```
Rules: never claim radar confirms an alert. Radar finding words: "Radar shows likely new open water in N mandals"
or "Radar shows no clear change". Auto events from alerts: id `auto_<source>_<id>`, status `alert_only`,
`reviewed_by_human: false`. Linking: a pass whose date falls in [start, end + aftermath_days] of an event in the same area.

## data/processed/alerts.json (schema alerts-v2) — owner: WP2 agent
```json
{"schema": "alerts-v2", "area_id": "godavari", "built_utc": "...",
 "gdacs":  {"fetched_utc": "...", "ok": true, "error": null, "url": "...", "credit": "GDACS (EC JRC / UN OCHA)", "items": [
            {"id":"...","type":"TC","name":"...","alert_level":"Green|Orange|Red","from":"...","to":"...","link":"...","countries":"..."}]},
 "sachet": {"snapshot_utc": "...", "ok": true, "error": null, "url": "...", "credit": "...", "items": [
            {"id":"...","headline":"...","area":"...","issued":"...","source":"...","link":"...","category":"..."}]},
 "none_text": "No current alerts for this area from GDACS or SACHET."}
```
A failed fetch keeps the previous items with their REAL timestamp and sets ok:false + error. Filter by the area's
`alert_match` (bbox for GDACS geometry, states/keywords for SACHET areaDesc/headline). `--fixture <file>` loads fake
alerts for simulations. `check_manifest.py` alerts check must accept v2.

## data/processed/findings/<YYYY-MM-DD>.json and latest.json (schema findings-v1) — owner: WP1 agent
All story-v1 keys (as today) PLUS:
```json
{"schema": "findings-v1", "revision": 1, "revision_log": [], "inputs_sha256": "...", "area_id": "godavari",
 "pass": {"date": "2026-11-09", "time_utc": "...", "time_ist_text": "9 Nov 2026, 05:31 IST", "role": "COAST",
          "track": 55, "scene_id": "L_COAST_1109", "product_status": "VALIDATED"},
 "template_state": "big_change",   // big_change | quiet | no_new_pass | numbers_coming | no_baseline
 "comparison_line": "...",          // vs previous pass on the same track AND vs normal
 "three_numbers": [{"value": 84, "err": 24, "unit": "km²", "label": "...", "source": "class_stats.json#dates.2026-11-09.new_water_km2"}],
 "caveats": ["..."],
 "confidence": {"level": "normal|lower", "reasons": ["Thresholds tuned on Oct post-monsoon scenes; this pass is in <season>."]},
 "event_chip": {"event_id": "arnab_2026", "relation": "during|after", "text": "After Cyclone Arnab"} ,   // or null
 "sea": {"finding": null, "text": "No plain-language sea finding yet: the method is not validated (docs/METHODS.md)."},
 "evidence_layers": [{"layer_id": "...", "png": "data/web/...", "h5": "data/h5/..."}],
 "sources": {"three_numbers[0].value": "class_stats.json#...", "...": "..."},
 "age": {"days_since_pass": 5, "text": "Last radar pass 5 days ago."},
 "alerts_ref": "data/processed/alerts.json"}
```
Template states (text from `app/strings/story.en.json`, never hard-coded, never built in the browser):
- big_change: today's Arnab format exactly.
- quiet: "This pass shows no clear change since <prev date>." No story invented.
- no_new_pass: latest.json keeps the last pass's numbers, adds the age line; headline says no new pass in N days.
- numbers_coming: a pass arrived but analysis failed -> "Pictures from <date> are in. Numbers are coming." NO numbers
  from an older pass presented as new.
- no_baseline: pass on a track/season with no baseline -> "No baseline yet for this track, so no change numbers."
Arnab-specific sentences move out of story.en.json/findings.js into events.json `story` and are rendered only when
an event chip is present or in the archive.

## Tests to add (tools/tests/)
- event name appears in a findings file only if the pass is inside that event's [start, end + aftermath_days]
- every number in `three_numbers` and `big_numbers` equals the value at its `sources` path in the stats file
- every template state renders with no unfilled slot, <= 20-word sentences, hedge words on flood claims, no banned words
- events: fake AP cyclone alert -> draft event `alert_only`; a pass inside its window -> linked, finding text present

## File ownership (one writer per file at a time)
| agent | owns |
|---|---|
| WP4+WP2 backend (Sonnet) | config/areas.json, tools/pipeline/{common,discover,ingest,alerts,events}.py, src/fetch/sachet_snapshot.py, build_web.py (box/config reads ONLY), data/processed/{events,alerts}.json, check_manifest.py (alerts/events checks), tools/tests/test_events.py, docs/DATA_STORAGE.md (events/alerts/areas sections) |
| WP1 findings (Sonnet) | tools/build_story.py, app/strings/story.en.json, data/story_rules.json, data/seasons.json, tools/tests/test_story.py, tools/tests/test_findings.py, data/processed/findings/ |
| WP6 L-band test (Sonnet) | scratch scripts + docs/review/LBAND_TEST.md only |
| WP5 audit (Haiku) | docs/review/RESOURCE_AUDIT.md only (read-only otherwise) |
| WP3 frontend (Sonnet, wave 2) | app/dashboard-mockup/**, app/strings/{shell,case,strings}.en.json |
| WP1e Action + sims (Sonnet, wave 2) | tools/pipeline/run_all.py, .github/workflows/*.yml, tools/sim/**, docs/PIPELINE.md |

Never touch `src/fetch/bhoonidhi_s_band.py` (teammate's uncommitted edit) or the S-band download logic.
Nobody commits, pushes, stashes, resets or checks out; Opus handles commits at the end.
