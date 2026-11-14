# Acceptance data: Wave 4 pipeline (tester run, 14 Nov 2026)

Tester: acceptance run, read-only on the real repo. Nothing was committed, pushed, deleted or edited in the repo.
All simulations ran in scratch copies (`tools/sim/run_sim.py`, `tools/sim/emulate_workflow.py`). The real repo
was never passed to `run_all.py`, `build_web.py` or `build_story.py`.

Scratch directory (outside the repo): `/private/tmp/claude-501/-Users-guneeshgupta--claude-spares-spare-6MTeDC/2dadeda1-16d1-4850-b8d1-0b82b67c77a9/scratchpad/accept/`
Workflow emulation log: `/private/tmp/claude-501/-Users-guneeshgupta--claude-spares-spare-6MTeDC/2dadeda1-16d1-4850-b8d1-0b82b67c77a9/scratchpad/accept/workflow_emulation.log`

## Summary table

| check | PASS/FAIL | evidence |
|---|---|---|
| A. Tests (story 16, findings 10, events 13, manifest 17) | PASS | all four exit 0 (captured in scratch `test_*.out`). Read-only. |
| B. Real findings (9 Nov, latest, 28 Oct) | PASS | 47 shown/three-number values re-read from source files: all match. 12/12/11 `sources` entries resolve. Chips and radar findings correct. |
| C1. new_pass_change | PASS | latest regenerated, numbers 84 to 323 km2, top mandals change, timeline 3 to 4 passes, 9 Nov byte-identical |
| C2. quiet_pass_calm ("no clear change") | PASS | template `quiet`, headline "This pass shows no clear change since 21 Nov." |
| C3. quiet_pass (9 Nov copy) | NOT A QUIET TEST | template `big_change` (8 flooded mandals). Expected by design (quiet needs no flooded mandal), so this scenario does not exercise `quiet`. |
| C4. missing_pass | PASS (minor wording gap) | `no_new_pass`, age "Last radar pass 26 days ago.", state `stale`. Headline has no day count. |
| C5. analysis_failed | PASS (minor) | `numbers_coming`, no numbers and no comparison shown. `sub` text uses the "No storm is being tracked" line while state is `event` (see problem 4). |
| C6. analysis_truncated | PASS | H5 left out of catalogue, warning, run exit 0, findings unchanged for the other passes. |
| C7. no_baseline | PASS | template `no_baseline`, headline "No baseline yet for this track, so no change numbers.", no numbers. |
| C8. ap_alert (change variant) | PASS | draft event `auto_GDACS_9100001` status `radar_linked`, reviewed false, pass 21 Nov linked as `after`, `change_seen`. Chip "After Cyclone Simcy (alert, not reviewed)". No "confirm" wording. |
| C9. ap_alert_quiet | PASS (scenario limit) | alert linked. Pass is still big_change, so the summary handles "change seen" here, not "no clear change". |
| C10. ap_alert_calm (no-clear-change variant) | PASS | 3 Dec quiet pass linked `no_clear_change` to the alert event. |
| C. Number-vs-source check, every scratch scenario | PASS | `run_sim` report: PASS for all 10 scenarios. My independent re-check: all `findings/*.json` OK. |
| C. 9 Nov archive byte-identical | PASS | sha256 `87e42419401adb7c...` before and after, all 10 scenarios. |
| C. Real-repo guard in every sim report | PASS | UNCHANGED in all 10 reports. My sha check (below) matches. |
| D. Workflow emulator (phases A, B, C) | PASS | `OVERALL: every emulated step passed`. Log: scratch `workflow_emulation.log`. |
| D. update.yml gating (read + forced failure) | PASS | YAML read: findings/events/alerts/rank/profile committed only on exit 0; Pages only on exit 0 and pushed; job red on 1 or 2. Forced test failure in a scratch copy: exit 2, `deployable: false`, `build_story` and `persist` not run, findings kept. |
| E. Text rules, real findings | PASS | 0 violations in 2026-11-09, latest, 2026-10-28 (about 1,650 sentences). |
| E. Text rules, sim findings | FAIL | quiet_pass_calm and ap_alert_calm: a 21-word sentence (`since_landfall`). Other 8 scenarios: 0. |
| F. git status of the real repo | LISTED | see section F below. `src/fetch/bhoonidhi_s_band.py` is modified (M) in the tree. |

## A. Tests (real repo, read-only)

| test | exit | result |
|---|---|---|
| `tools/tests/test_story.py` | 0 | 16 tests, 0 failed |
| `tools/tests/test_findings.py` | 0 | 10 tests, 0 failed (includes `test_real_data_every_pass_validates`, which now uses `passes[-1]`) |
| `tools/tests/test_events.py` | 0 | 13/13 passed |
| `tools/check_manifest.py` | 0 | PASS (17 checks, 0 failed) |

## B. Real findings

Script: `scratchpad/accept/verify_findings.py` (own path walker and own copy of the flood rule from `data/story_rules.json`). Output: `scratchpad/accept/verify_real_findings.txt`.

- **2026-11-09.json**: `template_state` big_change, `event_chip` "After Cyclone Arnab" (relation after, correct: 9 Nov is after the window 24-28 Oct), `radar_finding` change_seen. `three_numbers`: 84 (err 24, from `class_stats.json#classes.20261109|k=3.0.new_water_km2`), 8 flooded mandals (`count_flooded` over `mandal_rank.json` by_date rows), 2 km2 normal. All 12 shown numbers match their source.
- **latest.json**: identical numbers and chip; `age` "Last radar pass 5 days ago." (9 Nov to 14 Nov).
- **2026-10-28.json**: chip "During Cyclone Arnab", `radar_finding` no_clear_change, headline "No mandal looks probably flooded in this radar picture." All 11 shown numbers match. One sub-check is a rounding display note: see problem 1 (the top-mandal card says "probably under water" at 0.8%).
- **Event windows** (`events.json`): Arnab 24-28 Oct +45 days; Murasu 1-3 Nov +30 days; Flood in India 20 Oct-4 Nov +30 days. Event names in the findings files appear only for passes inside those windows (28 Oct and 9 Nov pass; Murasu not on 28 Oct, which is before its start). PASS.

## C. Simulations

Command: `.venv/bin/python tools/sim/run_sim.py <scenario> --out <scratch>/sim/<scenario>`. Reports: `scratchpad/accept/sim/reports/<scenario>.txt`, logs next to them. Each run did a settle run first. All 10 runs exited 0.

| scenario (clock) | template_state | headline | 3 numbers | top mandal | timeline | chips | radar_finding | 9 Nov sha |
|---|---|---|---|---|---|---|---|---|
| new_pass_change (21 Nov) | big_change | More land is probably flooded than on the last radar pass. | 323 km2 +-38; 12 mandals; 2 km2 | Alamuru 85.5% | 3 passes | After Arnab, Murasu, Flood in India | change_seen | identical |
| quiet_pass_calm (3 Dec, calm copies) | quiet (3 Dec) | This pass shows no clear change since 21 Nov. | 1 km2 +-1; 0 mandals; 2 km2 | Kakinada (Rural) 0.1% | 4 passes | After x3 | no_clear_change | identical |
| quiet_pass (21 Nov, copy of 9 Nov) | big_change | Most of the land probably flooded by Cyclone Arnab still looks wet... | 84 km2 +-24; 8 mandals; 2 km2 | Nidadavole 10.9% | 3 passes | After x3 | change_seen | identical |
| missing_pass (5 Dec, no new file) | no_new_pass | No new radar picture yet. This page shows the last one, from 9 Nov. | 84 / 8 / 2 (from 9 Nov) | Nidadavole | 2 passes | After x3 | change_seen (9 Nov) | identical |
| analysis_failed (21 Nov, corrupt chunks) | numbers_coming | Pictures from 21 Nov are in. Numbers are coming. | none | none | 3 entries, 21 Nov numbers_coming | After x3 | numbers_coming | identical |
| analysis_truncated (21 Nov, cut file) | big_change (9 Nov) | More land is probably flooded than on the last radar pass. | 84 / 8 / 2 (9 Nov) | Nidadavole | 2 passes | After x3 | change_seen | identical |
| no_baseline (track 62) | no_baseline | No baseline yet for this track, so no change numbers. | none | none | 3 entries | After Arnab | none | identical |
| ap_alert (21 Nov, SIMCY-26 fixture, 18-20 Nov) | big_change | More land is probably flooded than on the last radar pass. | 323 / 12 / 2 | Alamuru 85.5% | 3 passes | After Arnab, Murasu, Simcy (alert), Flood in India | change_seen | identical |
| ap_alert_quiet (9 Nov copy + alert) | big_change | Most of the land probably flooded... still looks wet | 84 / 8 / 2 | Nidadavole | 3 passes | After x4 | change_seen | identical |
| ap_alert_calm (3 Dec + alert) | quiet | This pass shows no clear change since 21 Nov. | 1 / 0 / 2 | Kakinada (Rural) | 4 passes | After x4 | no_clear_change | identical |

Expectations vs results:

- **(2) new pass**: PASS. Latest regenerates, numbers and mandal list change, timeline grows from 2 to 3 passes, 9 Nov unchanged (`87e42419401adb7c`, byte-identical).
- **(3) quiet**: PASS through `quiet_pass_calm` and `ap_alert_calm`. `quiet_pass` does not produce a quiet state (by design, it has flooded mandals).
- **(3) missing**: PASS. `no_new_pass`, age 26 days, state stale. Headline has no day count (problem 5).
- **(3) failed**: PASS. `numbers_coming`; no numbers from an older pass are presented as new (`three_numbers` and `big_numbers` are empty; `comparison_line`, `since_last`, `lead` are null).
- **(3) no_baseline**: PASS. No numbers.
- **(4) fake AP alert**: PASS. Draft event `auto_GDACS_9100001` (SIMCY-26, Orange, 18-20 Nov, inside the delta). Status `radar_linked` (not `alert_only`, because a pass falls inside its window), `reviewed_by_human` false, pass 21 Nov linked `after` with `change_seen`. Chip reads "After Cyclone Simcy (alert, not reviewed)". Summary handles change seen (ap_alert) and no clear change (ap_alert_calm). No "confirm" wording anywhere.

The alert-only status (no pass yet) was not run as its own scenario; the fixture always carries a pass.

## D. Workflow

- Emulator: `tools/sim/emulate_workflow.sh <scratch>/workflow <scratch>/workflow_emulation.log`. Phase A (update.yml, offline): run_all exit 0, commit to local bare origin, Pages redeploy call, failure step skipped. Phase B (update.yml, dry run, live CMR): exit 0, nothing committed. Phase C (pages.yml build): build_web, all four tests, build_story, site assembled (`_site/config/areas.json`, `latest.json`, `story.json`, the dashboard and `catalog.json` present). `OVERALL: every emulated step passed`.
- Forced failure: the emulator has no failure switch, and `run_sim --no-test-patch` no longer fails (see problem 6). I injected a failing `sys.exit(main() or 1)` into `test_findings.py` in a scratch copy (`scratchpad/accept/gate/`) and ran `run_all.py --offline` there: tests `FAILED`, `run_all exit=2`, `deployable: False`, `build_story` and `persist` `not_run`, findings not written, old findings kept. Gating works as documented.
- YAML read (update.yml): commit step always stages data of record; findings, events, alerts, rank, profile only when `run_all` code is 0; Pages redeploy only when code is 0 and something was pushed; the final step fails the job for any non-zero code.

## E. Text rules

Script: `scratchpad/accept/text_rules.py` (sentences over 20 words, banned words from `data/story_rules.json`, unfilled `{`, `confirm`, unhedged flood claims using the trigger list in `require_hedge_for`).

- Real findings (2026-11-09, latest, 2026-10-28): 0 violations.
- quiet_pass_calm and ap_alert_calm: the same 21-word sentence in `latest.json` and `2026-12-03.json`, 8 rows each: "Since the landfall pass, the share in Kakinada (Rural) has gone from about 0.3 to about 0.1 in every 100 acres." The template is `app/strings/story.en.json` line 65. Two-word mandal names push it over 20.
- Other 8 scenarios: 0 violations.

## F. git status (real repo, list only)

Modified (M): `.github/workflows/pages.yml`, `.github/workflows/update.yml`, `app/dashboard-mockup/README.md`, `app/dashboard-mockup/css/dash.css`, `app/dashboard-mockup/index.html`, `app/dashboard-mockup/js/dash.js`, `app/dashboard-mockup/js/findings.js`, `app/strings/story.en.json`, `app/strings/strings.en.json`, `data/processed/alerts.json`, `data/processed/mandal_rank.json`, `data/processed/manifest.json`, `data/processed/profile.json`, `data/seasons.json`, `data/story_rules.json`, `docs/DATA_STORAGE.md`, `docs/METHODS.md`, `docs/PIPELINE.md`, `src/fetch/bhoonidhi_s_band.py`, `src/fetch/sachet_snapshot.py`, `tools/build_story.py`, `tools/build_web.py`, `tools/check_manifest.py`, `tools/pipeline/common.py`, `tools/pipeline/discover.py`, `tools/pipeline/ingest.py`, `tools/tests/test_story.py`.

Untracked (??): `config/`, `data/processed/events.json`, `data/processed/findings/`, `docs/review/LBAND_TEST.md`, `docs/review/RESOURCE_AUDIT.md`, `docs/review/WAVE4_PLAN.md`, `tools/pipeline/alerts.py`, `tools/pipeline/events.py`, `tools/pipeline/run_all.py`, `tools/sim/`, `tools/tests/fixtures/`, `tools/tests/test_events.py`, `tools/tests/test_findings.py`.

Note for Opus: `src/fetch/bhoonidhi_s_band.py` is the only file the plan says must not be touched, and it is modified in the tree. The plan calls it a teammate's uncommitted edit. `src/fetch/sachet_snapshot.py` is also modified, though the plan assigns it to this wave (WP4). `docs/review/ACCEPTANCE_DATA.md` (this file) is the only file this run created.

## Real-repo hashes

sha256 of `data/h5/*.h5`, `data/h5/catalog.json`, `data/processed/findings/*.json`, `data/processed/events.json`, `data/processed/manifest.json`, recorded before and after the run: **identical (yes)**. Files: scratch `sha_before.txt` and `sha_after.txt`. `latest.json` also unchanged.

## Problems found

1. **Contradiction on the published 28 Oct card (real findings)**. Headline: "No mandal looks probably flooded in this radar picture." Big number: "0.8 in every 100 acres of Katrenikona was probably under water, give or take 1." The flood rule needs at least 3% likely water (`story_rules.json` `flooded_mandal`). The top-mandal card (`build_story.py`, `card_numbers`) uses the "under water" label for the top mandal whether or not it meets the flood rule. The same happens on the quiet sims (Kakinada 0.1%). Fix: use a neutral label ("most water seen in") unless `is_flooded`.
2. **Sentence over 20 words** (`since_landfall` template): 21 words with two-word mandal names. The build guard did not catch it, because it does not check the filled sentence. Fix the template or add a filled-text length check.
3. **Unhedged attribution in the published 9 Nov text.** The `sub` and `lead` lines say "Cyclone Murasu (1 to 3 Nov) and the Godavari river peak (about 2 Nov) also put water on the land." Murasu is an unreviewed GDACS draft event. The claim is not hedged and is not radar-checked. Consider "may have" wording or a reviewed event.
4. **Mixed state text** (`analysis_failed`): state `event` and chip "After Cyclone Arnab", but `sub` says "No storm is being tracked right now." That is the `watch` template. Choose the template from the state.
5. **missing_pass headline** has no day count (plan says "no new pass in N days"). The `next pass` line also still says "was expected about 21 Nov" on 5 Dec.
6. **Stale known-problem note.** `docs/PIPELINE.md` "Known problem 1" (the hard-coded 9 Nov assertion) is fixed in `test_findings.py` (`passes[-1]`). So `run_sim --no-test-patch` no longer makes tests fail, and the documented exit-2 demonstration does not happen. Update the doc. The `--no-test-patch` flag can be removed.
7. **quiet_pass is not a quiet scenario.** It produces big_change by design. Keep it, but rename it, or the report will look like a quiet test failure.
8. **Live CMR dry run (emulator phase B) found 6 new scenes outside the configured tracks**: SEA T120 F080 and T127 F010 (PR products, provisional and validated, 0.9 to 1.3 GB each, dates 8 Oct to 1 Nov). `config/areas.json` lists track 48 (SEA) and 55 (COAST) only. A real daily run would ingest them (max 6 per run) and show them as sea layers, which PIPELINE.md says is intended. Opus should decide whether discovery should stay limited to the configured tracks for now.
9. **Emulator has no forced-failure option**, so the gating test needed a manual scratch edit. Consider adding `--force-test-fail`.
10. **Tests ran in the real repo** as read-only checks. They may have written `__pycache__` under `tools/`. No tracked files changed.
