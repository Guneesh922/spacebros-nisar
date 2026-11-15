# Overnight report (15 Nov 2026, run started ~00:15 IST)

## Done
- **1A English only (P0-A)**: language switch/Telugu removed; SACHET English-first with "Original alert (not in English)" fallback; `test_english_only.py` (11 tests) added to run_all and pages.yml.
- **1B Colours (P0-B)**: see `docs/review/COLOUR_CHECK.md/.png`. CIEDE2000 under deuteranopia/protanopia: water vs crops 51-58; ramp blue end vs grey end min 21.3 (protanopia); class vs dark basemap 4.8:1 and 5.3:1; legend text 17:1 / 11:1 (AA). New coast change layers for 28 Oct and 9 Nov. Honest notes: coast change is brightness change against PROVISIONAL baselines, not a flood map; the 27 Oct sea difference is almost fully saturated orange (+4.6 dB median, mostly storm per METHODS.md, some provisional/validated offset possible); sea sigma for 27 Oct (3.11 dB) is the map's own spread, not a calm-fortnight value.
- **1C Name**: candidates Pass by Pass / Coast Radar View / Delta Radar Notes; applied **Pass by Pass** (old: Coast Radar Watch; "Watch" dropped, it can read as an official flood watch). Revert steps in STATUS.md.
- **1D Labelling (P0-C)**: no logos or AI images present; credits added; footer/About disclaimer; RESOURCE_AUDIT corrected (CMR + ASF search API named; ASF Vertex, StoryMaps, white papers not used).
- **Pipeline + tests**: `run_all.py --offline --skip-ingest` exit 0; story 19, findings 10, events 14, english_only 11, manifest 17 checks, all pass. JS syntax checked (`node --check`).
- **Part 2**: `docs/PLAN_P1_P2.md`. P1 go (fflate 0.8.2 MIT, crop of class PNG + SVG outlines, ~3 h wall + QA), P2-A go small, P2-B analysis only, no UI. GMW CC BY 4.0 test tiles (1.4 MB) in `data/external/gmw/`. Its clock assumption (06:00 IST) is wrong; this run started ~00:15 IST, so there is more time than the plan says.

## NOT done / dropped
- Browser check (done after the preview was allowed, 1440 and 375 px wide): console clean, no horizontal overflow, no non-Latin text on the page, title "Pass by Pass", footer text present (it sits at the end of the side panel, so scroll down), change legend with grey band and darker / no clear change / brighter words, caption credit line with date, track, polarisation and status. Small leftover: on a phone the legend now includes the credit and sits over the Esri attribution at the bottom of the map. Layers table still prints ODbL for mandal boundaries (data file text).
- P1/P2 not built (as instructed; you confirm first). docs/submission/ not edited. PLACEHOLDERS.md not changed (nothing newly real; README credits updated by the 1D agent).
- No separate "coast change" map mode or timeline control (sea diff has none either); both are in the Data-tab layer list and `l=` permalinks only.

## Numbers that changed
- Sea difference colour range +-15 dB -> +-6 dB (display only). Nothing else: new water 9 Nov 83.8 km2 (61-108), eye 16.226 N 82.539 E, radius 6.4 km are unchanged.
- Manifest class-layer opacity 0.75 -> 1.0; map colours changed (water #3FA7F5, crops #F2A93B).

## Stale statements / things for the team (not edited)
- docs/submission/: PROJECT_PAGE_DRAFT.md lines 52-53, 72, 74-75 (ASF Vertex, white papers, StoryMaps claims; short credit); README_DRAFT.md lines 59, 63, 67 (old credit, "Esri World Imagery" but basemap is Esri dark grey, no geoBoundaries credit); README_DRAFT/DEMO_SCRIPT call the product "Eye of the Storm"; no file carries the "Not an official..." disclaimer; AI_USE_DISCLOSURE.md line 19 and SUBMISSION_CHECKLIST_NEXT.md line 14 "[credit line to confirm]".
- `.github/workflows/pages.yml` root redirect page title still "SpaceBros NISAR".
- Licence conflict: geoBoundaries is CC BY 4.0 on geoboundaries.org, but manifest/sources.yaml/story credits say ODbL; district names from Wikipedia (CC BY-SA) are uncredited; no licence stated for SpaceBros derived products.
- The P2-A problem: live draft "Flood in India" (GDACS, ~150 km from the COAST box) is linked to the delta passes.

## What to push (I pushed nothing)
Review `git status` in 05_Code/spacebros-nisar (31 modified + new files; `src/fetch/bhoonidhi_s_band.py` was already modified before this run and is a teammate's). Then:
```
cd ~/Documents/nsa/05_Code/spacebros-nisar
git add -A -- . ':!data/external'
git commit -m "English only, colour coding, name, credits"
git push origin main
```
(Exclude or include `data/external/gmw/` as you wish; it is 1.4 MB, CC BY 4.0.) Then re-run `build_web.py` is not needed: `data/web` is git-ignored and Pages rebuilds it.

## Will the daily workflow run? (`update.yml`, not run on GitHub yet)
Needs, by you on GitHub: (1) Settings > Pages > Source = GitHub Actions; (2) Settings > Actions > General > Workflow permissions = Read and write (the job commits and pushes); (3) repo secret `EARTHDATA_TOKEN` (only needed on days with new scenes; without it ingest cannot run); (4) push first, since main is ahead of origin. The cron is 05:23 UTC daily; also runnable by "Run workflow" (try dry_run first). SACHET/GDACS fetch is untested from a GitHub runner (fails soft).

## Stale statements in docs/submission (to fix by the team)

Checked 15 Nov 2026 against the current product (name "Pass by Pass", basemap Esri `World_Dark_Gray_Base`, `docs/review/RESOURCE_AUDIT.md`, `config/areas.json` `presentation.show_data_caveats=false`, manifest with no placeholders). Nothing in `docs/submission/` was edited. Line numbers are as of this check.

| file:line | Current text (short) | What is true now |
|---|---|---|
| PROJECT_PAGE_DRAFT.md:52 | "NASA Earthdata Search, ASF Vertex, ... white papers and StoryMaps ... used to find scenes and to write the plain-language notes" | Not used. The code calls the NASA CMR API and the ASF search API. Vertex, StoryMaps, white papers, ARSET and the Data User Guide are background reading only (RESOURCE_AUDIT.md rows and lines 99-100). |
| PROJECT_PAGE_DRAFT.md:53, 74 | resource list "used"; ref 4 "White Papers, StoryMaps, ARSET" | Same: list them as background reading, not as sources used. |
| PROJECT_PAGE_DRAFT.md:13, 41 | NISAR layers are quick-look browse images, statistics are placeholders, GCOV subsets "not streamed yet" | 8 L-band scenes are H5 subsets in `data/h5/`; images, class maps, mandal rank and eye profile are built from them. No placeholders in the manifest (PLACEHOLDERS.md). |
| PROJECT_PAGE_DRAFT.md:19, 34 | name "Eye of the Storm" | Product name is "Pass by Pass" (`config/areas.json`, page title). |
| PROJECT_PAGE_DRAFT.md:29 | live app link "[TO CONFIRM]", `.../app/` | Pages root redirects to `app/dashboard-mockup/` (`pages.yml`). Not confirmed to be live: the workflow has not run on GitHub. |
| PROJECT_PAGE_DRAFT.md:56 | S-band "considered ... not used unless a scene is confirmed" | Still true: no S-band files exist. |
| PROJECT_PAGE_DRAFT.md:61, 78 | "Esri World Imagery" basemap; geoBoundaries "ODbL" | Basemap is Esri World Dark Gray Canvas (`World_Dark_Gray_Base`, `dash.js:187`). geoBoundaries licence is unresolved (site says CC BY 4.0; manifest says to check). |
| PROJECT_PAGE_DRAFT.md:63 | MOSDAC and OSM credit lines "to confirm" | Both are now set with `credit_confirmed: true` in the manifest (MOSDAC: "Data Source MOSDAC/SAC/ISRO. https://mosdac.gov.in"; OSM: "© OpenStreetMap contributors"). GDACS is the one still unconfirmed. |
| README_DRAFT.md:1 | "Eye of the Storm" | "Pass by Pass". |
| README_DRAFT.md:7, 54, 70 | status honesty: quick-look images, sample values, replace placeholders | Not true now; see PLACEHOLDERS.md. Also the product shows no data-quality disclaimers (caveats live in the deck and `docs/METHODS.md`). |
| README_DRAFT.md:22, 67 | "Esri/OSM basemaps", "Esri World Imagery" | Esri World Dark Gray Canvas. |
| README_DRAFT.md:59 | credit "NASA/JPL-Caltech and ISRO via ASF DAAC" with "[confirm wording]" | Current string: "NISAR L2 GCOV, NASA/JPL-Caltech and ISRO, via ASF DAAC (NASA Earthdata)" (`credit_confirmed: true`). |
| README_DRAFT.md:62, 65, 67 | "[licence to confirm]" / "[credit line to confirm]" | MOSDAC and OSM lines are set (see above); SACHET credit is "NDMA SACHET", confirmed in the manifest. |
| README_DRAFT.md:71 | PR scenes used up to 16 Oct, validated from 22 Oct; bounds inferred | Baselines (3, 4, 15, 16 Oct) are PROVISIONAL, events (27 Oct, 28 Oct, 8 Nov, 9 Nov) VALIDATED; bounds come from the H5 (`bounds_inferred: false` everywhere). |
| README_DRAFT.md (whole file) | no "Not an official ... product" disclaimer | The product footer says it; the repo README.md has it; add it to the draft. |
| DEMO_SCRIPT.md:1, 17 | "Eye of the Storm" | "Pass by Pass". |
| DEMO_SCRIPT.md:21 | "Keep 'Sample values' tag visible until replaced" | No sample tags appear any more. |
| DEMO_SCRIPT.md:13, 22 | "Can't show:" line on layers, "placeholders, no km2" | The product shows no caveat disclaimers (`show_data_caveats=false`); put the honest limits in the deck. The "what radar cannot tell you" card still has the "Draft: to be reviewed" tag. |
| AI_USE_DISCLOSURE.md:6 | plan called "Eye of the Storm" | Name of the plan document only; the product is "Pass by Pass". |
| AI_USE_DISCLOSURE.md:12 | "page shows sample values and says so on screen ... [Update this line]" | No sample values remain; update as the line asks. |
| AI_USE_DISCLOSURE.md:19 | "two credit lines still marked 'to confirm'" | Zero are marked "[credit line to confirm]" in the manifest; the open item is GDACS `credit_confirmed:false` and the geoBoundaries licence. |
| SUBMISSION_CHECKLIST_NEXT.md:13 | replace placeholders; fill `[TBD from real product]` | Placeholders are gone; the `[TBD]` markers in the drafts are what is left. |
| SUBMISSION_CHECKLIST_NEXT.md:14 | confirm two credit lines (MOSDAC, OSM) | Both set; confirm GDACS wording and the geoBoundaries licence instead. Landfall wording is still open (`time_utc: null`). |
| any file | any "Pratham" or "Netlify" mention | None found in `docs/submission/` (grep). |

Also not in submission/: `README.md:77` previously described ASF Vertex as a listed resource (now labelled "not used").


## Update (15 Nov, ~07:30 IST): everything in the plan is now built
- P1 brief + zip: built and wired (Data tab, mandal card: 'Download brief and data (zip)', 'Open brief (print)'); node tests 14; A4 fit checked for 8 combinations; real zip unzipped (5 files). Not verified: Chrome print preview, new-tab open (pane blocks pop-ups), Safari/iOS.
- P2-A: done (flood footprint + 50 km link rule; 'Flood in India' is now alert only; findings 28 Oct and 9 Nov at revision 5).
- P2-B: analysis only, result 'not separable from calibration' (HH rose +1.9 dB in the mangrove on 28 Oct, unexplained); not in the UI, ~3 GB RAM, not for CI. docs/review/MANGROVE_EXPERIMENT.md.
- Colour: all 8 H5 scenes have an RGB composite; on-map Colour key in every mode. Coast composites are 502 px wide because of the 600 KB cap.
- Product rule from the user: no data-quality disclaimers in the UI. Removed text is logged in docs/REMOVED_FROM_PRODUCT.md. Kept: footer line, 'Not an official warning. Follow IMD, APSDMA...' line (safety; remove if you decide so). The public story.json still has a story.internal block and feeds still carry the 'not reviewed' chip wording (see REMOVED_FROM_PRODUCT.md).
- Pratham/Netlify steps in earlier text were wrong for this project and are removed.
- Latest live run: GDACS timed out once, then refreshed OK; SACHET has 1 current Andhra Pradesh alert.
