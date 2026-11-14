# LIVE_STORY_SPEC: "What happened" as a self-updating newsletter

Status: design only. Nothing implemented. Written 14 Nov 2026.

## 0. Findings: what is hard-coded today
- Big numbers are NOT typed. `buildHappened()` in `app/dashboard-mockup/js/dash.js` computes them: "8%" = round(top.lik) with top = rank-1 row of `mandal_rank.json` (water_pct + crops_pct); "5x" = round(lik / normal_pct); "4.7 km" = `profile.json.eye_radius_km`. They are already data-driven but currently read invented placeholder files.
- Hard-coded: `app/dashboard-mockup/js/findings.js` (title "Cyclone Arnab and the Godavari delta", the intro lead with dates, `cyclone.category/wind/where`, landfall text); `dash.js` constants `AFTER/BEFORE/EYE` layer ids and `DELTA/SEA` bounds; `manifest.events[0]` (single event; `X.event = m.events[0]`); `strings/case.en.json` (the separate case-study page, leave as is).
- Result: a new scene changes the numbers, but the headline, dates, "9 Nov" layer choice and wording never change.

## 1. Content model

Two layers, kept apart.

**Event context (hand-written, rarely edited): `data/events/<id>.json`** (also listed in manifest.events)
```
{ "id":"arnab_2026","name":"Cyclone Arnab","hazard":"cyclone","status":"active|recovering|closed",
  "imd":{"category":"VSCS","wind_kmh":[125,135],"gust_kmh":150,"bulletin_urls":[...],"source":"IMD"},
  "landfall":{"lat":16.45,"lon":81.9,"time_utc":null,"note":"time being confirmed (IMD)"},
  "dates":{"formed":"...","landfall_day":"2026-10-28","closed":null},
  "baseline":{"scene_ids":["L_COAST_1004","L_COAST_1016"]}, "region":"konaseema",
  "monitor_days":45, "official_links":[IMD, APSDMA, SACHET] }
```
`landfall.time_utc` stays null while disputed; text must then say "on 28 Oct", never an hour.

**Update cards (generated): `data/web/story.json`**, emitted by new `tools/build_story.py` after `build_web.py`. One card per NISAR scene in `data/h5/catalog.json` that has a new analysis, newest first.
```
{ "schema":"story-v1","built_utc":"...","state":"event|recovery|watch",
  "event_id":"arnab_2026|null",
  "data_as_of_utc":"<latest scene start_utc>", "data_status":"PROVISIONAL|VALIDATED|SAMPLE",
  "headline":{"text":"...","key":"recovery.partial"},
  "next_pass":{"expected_utc":"~2026-11-21","basis":"last pass + 12 days (NISAR repeat)","text":"..."},
  "since_last":{"prev_scene":"L_COAST_1028","this_scene":"L_COAST_1109","days_apart":12,
                "flooded_mandals_prev":N1,"flooded_mandals_now":N2,"receded":R,"still":S,"worse":W,
                "water_pct_change":{...}, "text":"..."},
  "bignums":[{"id":"top_mandal","value":"7%","label":"...","source":"mandal_rank.json rows[rank=1]","err":"±0.1"} x3],
  "map":{"layer_id":"nisar_class_new_water","mode":"share","caption_key":"share"},
  "mandals":{"Nidadavole":{"lik":..,"err":..,"normal":..,"trend":"down|flat|up|new","sentence":"...","confidence":"high|medium|low"}},
  "updates":[{"id":"2026-11-09_L_COAST","permalink":"#update=2026-11-09","date":"2026-11-09","scene_ids":[...],"days_after_landfall":12,"status":"PROVISIONAL","headline":"...","bignums":[...],"since_last":{...}}],
  "feed":{"json":"feed.json","atom":"atom.xml"} }
```
Number sources: scene date/status/track: `catalog.json` (start_utc, product_status). Mandal shares, errors, normals, ranks, coverage flags: `mandal_rank.json` (per scene: extend to `mandal_rank_<scene>.json` so "previous" is comparable; current file is the latest only). Eye radius, core contrast, IMD offset: `profile.json` (only for SEA scenes with an eye; otherwise bignum omitted). Class-map shares: `class_stats.json`. Event facts: event.json. No number is typed into a template.

## 2. Text generation rules (no LLM at runtime, build-time templates only)
Templates live in `app/strings/story.en.json` (keys + `{placeholders}`), selected by `build_story.py`; a Telugu file can be added later with identical keys.

- Reading level about age 12: sentences under 20 words, no "backscatter", "SAR", "polarisation". Use "radar picture", "probably under water". Units always shown (%, km, "days"). Percent phrased as "about 7 in every 100 acres".
- Hedging is mandatory: "probably", "likely", "about", "give or take {err}". Never "flooded" without "probably"; never "damage", "depth", "people affected", "wind speed from radar".
- Thresholds (all in one `story_rules.json`, reviewable):
  - mandal counts as "flooded" if lik >= 3% AND lik >= 2x normal AND coverage >= 50%; coverage < 50% = "not enough radar view", never ranked.
  - trend vs previous pass: down if lik falls by >= max(1 pt, 2x err); up if rises by same margin; else "about the same". Differences inside the error band are reported as "no clear change".
  - times-normal wording reuses `timesWords()` (less / same / about N times; cap "more than ten times").
  - headline keys: `recovery.most` (receded >= 75% of previously flooded), `recovery.partial` (25-75%), `recovery.little` (< 25%), `worse`, `first_pass`, `no_new_pass`.
- Provisional: every card with `product_status=PROVISIONAL` gets text "Early data. NISAR has not finished checking it. Numbers may change." and the existing yellow badge. Sample/placeholder inputs force a "Sample values" badge and the headline prefix "Practice numbers:".
- Missing: if mandal_rank for the new scene is absent, show only the scene date and "Pictures are ready, numbers are coming" (no stale numbers). Missing eye profile: drop that bignum.
- Stale: if `built_utc - data_as_of > 16 days` (12-day repeat + 4 days grace) show "No new radar pass in {n} days. This page shows the last one, from {date}." Never write "now" or "today" for old data; always "on 9 Nov".
- Quiet period (state `watch`): no event within `monitor_days` of landfall and no new flood signal -> headline "Calm on the coast. No active storm." Cards: last pass date, "normal conditions" check (all mandals within normal band), seasonal line from a fixed `seasons.json` (e.g. cyclone season Oct-Dec, monsoon Jun-Sep), next pass date, link to IMD. Archive keeps the old event.
- New storm: a new `data/events/<id>.json` (hand-created, or auto-stub from GDACS/IMD with status "needs review") flips state to `event`; its baseline scenes are those before landfall; the old event moves to the archive section. Auto-stubs never publish text without a human setting `status:"active"`.
- A guard test fails the build if any output string matches a banned-word list or contains a "{" leftover.

## 3. Newsletter layout (inside the approved design; reuse `.card`, `.bignums`, `.tag-sample`, existing classes only)
1. Masthead card: eyebrow "What happened" + date of data, headline, one-line lead, badges (Provisional / Sample), "Data from {date}, page built {time}".
2. "Since the last pass" card (only if a previous scene exists): three chips "went down / about the same / went up" with mandal counts, one sentence.
3. Three big numbers (existing `.bignums`): (a) biggest mandal share now, or in watch state "0 mandals flooded" = count of flooded mandals; (b) change since last pass, "-X points in {top mandal}"; (c) days since landfall, or days to next pass in watch state. Eye radius remains in the cyclone card, shown only for the event's eye scene.
4. One map moment: button "Show on the map" sets `setMapMode(story.map.mode)` and picks `AFTER` from `story.map.layer_id`, replacing the hard-coded constants.
5. "What this means for you": search box (reuse mandal search) -> mandal sentence from `story.mandals`, with trend, error, confidence dots and "ask your local officials, this is not a count of damage".
6. Archive: list of `updates[]`, each a card with permalink `#update=<id>` (deep link restores that card and map layers; stable ids = scene date, so "save this day" can store the id). Keep ranking/cyclone/confidence cards below unchanged.
7. Subscribe line: links to `feed.json` (JSON Feed 1.1) and `atom.xml`, generated from `updates[]`; items carry the plain headline, link `#update=<id>`, date, badge text. No email server; a third-party mail-from-RSS service can sit on top later.

## 4. Honesty and safety
- Fixed banner on the page: "This is not an official warning. For alerts, follow IMD, APSDMA and your district officers." with links from event.json `official_links` (always shown, in every state).
- Two timestamps: "Radar picture taken {data_as_of, IST}" and "Page updated {built_utc, IST}". Provisional/validated badge per card.
- Never forecast; "next pass expected about {date}" is a schedule estimate, labelled so. Pass times can shift; say "about".
- Radar limits sentence is on every card (existing `mandal.cannot`).
- Domain-expert review of `story.en.json` before real numbers go live (see PLACEHOLDERS.md section 7).

## 5. Implementation plan (ordered)
| # | Task | Files | Effort | Delegate |
|---|------|-------|--------|----------|
| 1 | Decide thresholds, banned words, state machine | `data/story_rules.json`, `data/seasons.json` | 1 h | Opus/user |
| 2 | Event files and schema doc, manifest link, validator | `data/events/arnab_2026.json`, `tools/check_manifest.py`, `docs/MANIFEST_SCHEMA.md` | 1.5 h | Sonnet |
| 3 | Per-scene mandal_rank + class_stats (prerequisite: real class maps from STATUS Phase 2 item 3-4) | `tools/build_web.py` | 4-6 h | Opus plan, Sonnet implement |
| 4 | Text templates (EN) | `app/strings/story.en.json` | 1.5 h | Sonnet, review by human |
| 5 | `build_story.py`: read catalog, ranks, profile, event; state, deltas, bignums, next_pass, cards, banned-word test; emit story.json | `tools/build_story.py`, `tools/test_story.py` | 5-6 h | Sonnet (core), Haiku (tests with fixtures: first pass, recovery, worse, stale, missing, watch, new storm) |
| 6 | Feeds | `tools/build_story.py` (feed.json, atom.xml) | 1.5 h | Haiku |
| 7 | Hook into Action after build_web | `.github/workflows/pages.yml` | 0.5 h | Haiku |
| 8 | Front end: `renderStory()` replaces intro card and bignums in `buildHappened()`; load story.json; drop typed layer ids; permalink routing in `setSection`/hash; archive; mandal search sentence; fall back to current FINDINGS if story.json missing | `dash.js`, `findings.js` (keep as fallback), `index.html` untouched | 5-6 h | Sonnet; coordinate with the "save this day" agent on the `#update=<id>` hash format first |
| 9 | Browser check desktop + mobile, 3 states via fixture story.json | docs | 1 h | Haiku |
| 10 | Telugu strings | `story.te.json` | later | human translator |

Critical path: 3 -> 5 -> 8. Tasks 1, 2, 4 can run in parallel now. Total about 20-25 h. Until task 3 is done, build_story.py must label everything "Sample values".

Open questions for the user: (a) per-scene ranking files vs one multi-scene file; (b) who writes event.json for a new storm; (c) is a recovery "since last pass" compared against the previous pass or the landfall pass (spec assumes previous pass, plus total change since landfall as a second sentence).
