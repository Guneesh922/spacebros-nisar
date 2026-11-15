# Removed from the product (15 Nov 2026)

## Context for a later reviewer
- The product is **Pass by Pass** (`app/dashboard-mockup/`), the team's entry for NASA Space Apps 2026, challenge "Dancing with the SARs".
- On 15 Nov the user decided that **disclaimers, data-quality notes and prototype-flavoured text belong in the pitch deck and the docs, not in the product**, and that the product must read like a final product on both tabs. Source credits, licences, factual identity (date, track, polarisation, size, sha256), the footer line ("Built by team SpaceBros ... not a warning service") and the line "Not an official warning. Follow IMD, APSDMA and your district officers." stay.
- Everything below is hidden in `app/dashboard-mockup/js/dash.js` behind one switch, `cav()` (= `story.presentation.show_data_caveats === true`; missing means off). Setting that value to `true` in the findings file brings back most of the notes listed here, apart from the text that was reworded or deleted (marked "deleted" below). Nothing was deleted from the data files, `docs/METHODS.md` or the strings files.
- **A later session should check every item against the competition's judging and ethics expectations and decide what goes where (product, pitch deck, docs).** The criteria are not known to this repo: `docs/SUBMISSION_GUIDE_NOTES.md` records that the 2026 Project Submission Guide and the challenge page (`https://www.spaceappschallenge.org/2026/challenges/dancing-with-the-sars/`) could not be retrieved (`robots_disallowed`); read them in a browser. Also see `docs/submission/` (AI_USE_DISCLOSURE.md, PROJECT_PAGE_DRAFT.md, README_DRAFT.md, DEMO_SCRIPT.md), `docs/SUBMISSION_CHECKLIST.md` and `docs/PLACEHOLDERS.md`. The criteria were not invented here.
- Where "Lives now" says `story.internal`: the original text still sits in `data/web/story.json` under `internal` (see "Not changed because risky").
- "Pitch deck?" = suggestion only.

## Not changed because risky
1. **Folder and URL name `dashboard-mockup`.** It is visible in the page URL and in the citation text the page generates (`pageUrl()`). Renaming `app/dashboard-mockup/` needs coordinated edits in: `.github/workflows/pages.yml` (redirect lines 69-70), `README.md`, `CLAUDE.md`, `app/dashboard-mockup/README.md`, `tools/tests/test_export.py`, `tools/tests/export_node_test.js`, `tools/tests/export_harness.html`, `tools/colour_check.py`, `tools/sim/emulate_workflow.py`, `app/vendor/VENDOR.txt`, several docs (STATUS, PLAN_P1_P2, PLACEHOLDERS, REPORT_OVERNIGHT, review/*, handoff/*) and the preview config. Options: (a) rename to `app/dashboard/` in one commit with all of the above and a redirect stub left at the old path for old links; (b) keep the folder and serve the app at a clean URL from the Pages workflow (copy `app/dashboard-mockup/` to `_site/` root, keep the folder name in the repo); (c) leave it. Recommendation: (b), the least risk, no test changes. The page text "mockup" itself is not shown anywhere in the visible UI.
2. **`story.internal` in the public `data/web/story.json`.** It holds the original caveat text (`badges`, `provisional_text`, `caveats`, `confidence`, `confounders`, `lead`, `updates`) and is fetchable by anyone. Options: (a) write the internal block to a path the Pages workflow does not publish (for example `data/processed/internal/story.internal.json`) and keep only the filtered story public; (b) keep it public on purpose and point to it from the pitch deck as the "full caveats" file; (c) leave as is. Recommendation: (a) if the user wants the product to carry no caveat text at all, otherwise (b) so the information stays transparent and findable.
3. Other public files that still carry caveat or status wording (not shown in the UI, but fetchable): `data/processed/manifest.json` (`limit`, `placeholder`, `processing_level`), `data/processed/mandal_rank.json` and `profile.json` (`placeholder`, `notes`, `calm_reference_caveat`), `data/processed/findings/*.json` (`confidence`, `caveats` where present), `data/h5/catalog.json` (`product_status`), `app/dashboard-mockup/js/findings.js` and `app/strings/*.json` (fallback wording), `docs/METHODS.md`.

## What happened tab (and the map shared by both tabs)

### 1. "Provisional data" tag on the latest-pass card
- Where: `dash.js` `storyHtml()` (`badges`); data `story.internal.badges.provisional`.
- Original: `Provisional data`
- Told the user: the newest scene or a baseline scene is a PROVISIONAL product that NISAR has not finished checking.
- Lives now: `story.internal`, `docs/METHODS.md` (Limitations), `data/h5/catalog.json` `product_status`.
- Pitch deck: yes.

### 2. "Lower confidence." note and its reasons
- Where: `dash.js` `storyHtml()`; data `story.internal.confidence`.
- Original: `Lower confidence.` followed by "The baseline radar pictures are early data that NISAR has not finished checking."
- Lives now: `story.internal`, `docs/METHODS.md`. Pitch deck: yes.

### 3. "Caveats." list on the latest-pass card
- Where: `dash.js` `storyHtml()`; data `story.internal.caveats`, `provisional_text`, `confounders`.
- Original: "Early data. NISAR has not finished checking it. Numbers may change." and "Cyclone Murasu (1 to 3 Nov) probably also put water on the land. The Godavari river peak (about 2 Nov) probably did too. This radar picture shows all of it together, not Cyclone Arnab alone." (the confounder sentence is also stripped from the lead text).
- Told the user: the numbers can change; 9 Nov water is not only Arnab.
- Lives now: `story.internal`, `docs/METHODS.md` (Limitations, "New open water ... 9 Nov also contains Cyclone Murasu"). Pitch deck: yes (the Murasu point is important for honesty about attribution).

### 4. PROVISIONAL / VALIDATED chips and status words
- Where (public tab): pass card chip (`storyHtml()`), archive entries (`archiveHtml()`), credit lines (`nisarFacts()`, `creditFor()`, `noStatus()` for `credits.nisar_line`: it used to end "..., polarisation HH, VALIDATED"), map caption credit ("... · 9 Nov 2026 · T55 · HH · VALIDATED"), Radar-by-date thumbnails ("provisional · before").
- Told the user: the product version of each scene.
- Lives now: `data/h5/catalog.json`, layer jsons, `docs/METHODS.md`. Pitch deck: yes.

### 5. "Sample values" and "Quick-look sample" tags, "(sample)" in tooltips and the file name `mandal_rank_SAMPLE.csv`
- Where: `dash.js` `rankTag()`, `capTag()`, `profSample()`, `layerSample()`, `csv()`; data `placeholder` blocks. Original strings: `Sample values`, `Quick-look sample`, ` (sample)`, `mandal_rank_SAMPLE.csv`.
- Lives now: `data/processed/manifest.json`, `mandal_rank.json`, `profile.json` `placeholder`; `docs/PLACEHOLDERS.md`. Pitch deck: only if some numbers really are still placeholders: check `docs/STATUS.md` "Real vs placeholder" first.

### 6. Mandal cards: confidence dots and notes; wet-crops line
- Where: `dash.js` `mandalCard()`, `confOf()`, `fmShow()`; strings `F.mandal.conf_*`, `conf_note_*` (`app/dashboard-mockup/js/findings.js`).
- Original: `Fairly sure` / "The radar signal was clear here."; `Moderately sure` / "The signal was clear, but small errors could move this number a little."; `Less sure` / "The signal was weak here. Treat this as a hint, and check on the ground."; and "Wet crops are not counted here: radar cannot yet tell them apart from normal change in fields (weak signal). The raw numbers list them." (now: "Wet crops are not counted here. The raw numbers list them.").
- Lives now: `findings.js`, `docs/METHODS.md` (wet crops "unproven"). Pitch deck: yes.

### 7. "What radar cannot tell you." notes on mandal cards (ranked and unranked)
- Where: `mandalCard()`, `unrankedCard()`; string `F.mandal.cannot`.
- Original: "Radar cannot tell you how deep the water was, how long it stayed, or whether homes or crops were damaged. Water under thick crops can be missed, so the real flooded share may be higher."
- Lives now: `findings.js`, `docs/METHODS.md`, `LIMITATIONS`. Pitch deck: yes (this is the core scope limit).

### 8. Events and archive
- "Draft from alert, not reviewed" tag and "(alert, not reviewed)" on chips (`evItem()`, `passChips()`, chip text from `story.event_chips`; strings `dash.events.draft`, `chip_draft`). Now the chip reads "(alert)" and the tag "From an alert".
- "What radar cannot tell here" list (`evItem()`, `ev.cannot_tell` in `events.json`).
- Story paragraphs `murasu_caveat` ("Other water") and `sea_caveat` ("Sea brightness") in `evStoryHtml()`; the sentence "It does not measure wind speed in km/h." in the eye paragraph (the IMD attribution sentence stays).
- "Edit log (n)" details (reviewer notes such as "human-review via Opus: hedged the Murasu and river-peak confounder text ...").
- "An alert alone is not confirmed by radar." (`dash.events.no_confirm`).
- Lives now: `data/processed/events.json`. Pitch deck: yes for the alert/not-reviewed point and the Murasu caveat; no for the edit log.

### 9. "How sure are we?" card and the "What radar cannot tell you" verdict card
- Where: `buildHappened()` (card removed from this tab; the verdict card also not on the Data tab); strings `F.confidence`, `F.cannot_tell` in `findings.js`.
- Original: "How sure are we?" with "We say "probably" on purpose. Radar change points to flood water. Nobody has checked it on the ground." / "The radar could see through clouds and rain, so the picture is clear." / "Mandal numbers are shares of each mandal. They come with a give-or-take figure."; "What radar cannot tell you" (tag "Draft: to be reviewed") with Radar can see the sea under clouds / only partly see flood water under crops / does not tell wind speed / does not tell how deep the water is.
- Lives now: `findings.js`, METHODS.md. Pitch deck: yes. (`cav()` brings both back.)

### 10. End-of-tab note "What radar cannot tell you"
- Added earlier on 15 Nov from `F.mandal.cannot` plus three `F.cannot_tell` lines, then removed because the user's later rule is no disclaimers and it could not be turned into a neutral "About these maps" card without reading as one (a neutral card would only repeat the radar explainer). Now shown only when `cav()` is on (`cannotNote()`). Pitch deck: yes.

### 11. Radar explainer card: the limitation paragraphs
- Where: `radarPanelHtml()`; strings `dash.radar.*` in `app/strings/strings.en.json`. The card keeps paragraphs 1-3 (how radar sees water) and the title "How radar sees water".
- Removed: title ending ", and what it cannot see"; p4 "NISAR uses L-band, a long wavelength that can pass through some leaves. It may still miss water under thick crops."; p5 "Water among tall crops or buildings can look bright, not dark. Radar may miss some of it."; p6 "Dark patches can also be other smooth surfaces, such as dry sand or tarmac. They are not always flood."; p7 "Radar cannot tell how deep water was, how long it stayed, or what it damaged."; p8 "So we say "probably". Nobody has yet checked these results on the ground."
- Pitch deck: yes.

### 12. Sea finding text
- Original: "No plain-language sea finding yet: the method is not validated (docs/METHODS.md)." (data `story.sea.text`, hidden by `seaText()` when it says "not validated"). Lives now: `docs/METHODS.md` ("No sea finding is made, because the sea method is not validated"). Pitch deck: yes.

### 13. Map caption "Cannot show" row (both tabs) and the caption wording behind it
- Where: `applyMap()`; `F.captions.*.cant`. Original rows: radar "Ground truth. This is one date only."; swipe "Wet soil apart from shallow water."; share "How deep the water was, or any damage."; sea/eye "Wind speed. Brightness is a clue to roughness only."; custom "See the Limit column for each layer."; colour views "Wind speed. Purple means a rougher sea, not a flood." and "Double bounce cannot be told from other very bright HH, nor wet from bare ground."
- Lives now: `findings.js`, `docs/review/RGB_COMPOSITE.md` (colour meanings). Pitch deck: yes.

### 14. Legend text
- On 15 Nov (later pass) the colour legend became a larger on-map "Colour key" with a channel-recipe strip; the earlier one-line text "Red = HH, green = HV, blue = HH minus HV." is replaced by the strip (same information, plus the stretch limits in dB).
- Removed: the line "Two polarisations only (HH, HV): hints, not proof." (colour legend), the suffix " (weak signal)" on the wet-crops legend row. The plain-word colour labels stay.
- Lives now: `docs/review/RGB_COMPOSITE.md`. Pitch deck: yes for the dual-pol point (colours are hints, not a decomposition).

## Data tab

### 15. Scene catalogue
- Removed: the "Status" column (PROVISIONAL / VALIDATED chip plus "in catalogue after 5.5 days"), the summary tile "validated / provisional" (showed "4 / 4"), and the footnote: "Read from data/h5/catalog.json. New scenes appear here when the catalogue is rebuilt. Times are the start of the radar pass. "In catalogue after" shows only when the catalogue records when a scene was added. PROVISIONAL scenes have not finished NISAR's own checks and may be replaced." (now: "Times are the start of each radar pass."). Credit lines in the rows no longer end with the status.
- Lives now: `data/h5/catalog.json` (`product_status`, `cataloged_utc`). Pitch deck: yes (PROVISIONAL/VALIDATED is a real product distinction).

### 16. Downloads
- Removed: status chips on the H5 rows and in credit lines; "Radar quick-look, 9 Nov 2026" (now "Radar picture (grey), coast, 9 Nov 2026"); "For display only (Quick-look sample)"; the card intro "Files as stored in the repository." and "Each file name carries its scene date, track, polarisation and PROVISIONAL or VALIDATED status." (now "... carries its scene date and track."); "method notes coming" (line hidden when `docs/METHODS.md` is not served); citation clause "status per scene as listed (PROVISIONAL or VALIDATED). Not an official NASA, ISRO, IMD or government product." in both the text and BibTeX citation.
- Also in the "This view / Download this day" box: "The picture is for display only ..." (now "The H5 file is the data of record and can be large.") and "Picture not available yet." (now "No picture for this layer.").
- Pitch deck: no for the wording, yes for the status.

### 17. Layers table
- Removed: the column "Status and limits" (a "Ready" / "Not available yet" / "Link only" chip and the layer `limit` text from `manifest.json`); new column "What it shows" (the layer `shows` text). Credit column no longer ends with the status. "Weak signal" and sample tags (hidden by `cav()`). Licence "not stated" is now "—"; "Not drawn" is now "—".
- Original limit texts (still in `manifest.json` `limit`): coast 9 Nov "ground truth (single date, none yet)"; coast 28 Oct "whether water is still rising (one look)"; coast 4/16 Oct "wet soil apart from shallow water"; sea 8 Nov and 27 Oct "wind speed; brightness shows roughness"; sea 15 and 3 Oct "an average sea (one calm day only)"; wet-crops class "water under dense crops; a normal fortnight (4-16 Oct) already flags 2.1% of land by the same rule, against 2.7% on 28 Oct and 0.9% on 9 Nov, so this class is not clearly ..."; coast change layers "it is a brightness change, not a flood map; baseline scenes are PROVISIONAL products; crop and wind effects also change brightness"; sea difference "wind speed (it is a brightness change). Calibration check: 27 Oct read about 4 dB brighter in VV than the PROVISIONAL 15 Oct reference; 8 Nov differed by about 0.1 dB, so ..."; colour layers "two polarisations only: a hint about the kind of surface, not proof; a rough sea looks bright, it is not a flood; not a Freeman-Durden decomposition"; others "the sea or land under cloud (cloud tops only)", "measured waves (a forecast model at one point)", and similar.
- Lives now: `manifest.json`, `docs/METHODS.md`, `docs/review/LBAND_TEST.md`, `docs/review/COLOUR_CHECK.md`. Pitch deck: yes (the calibration and wet-crops notes matter).

### 18. Mandal table and eye profile
- Mandal table footnote, original: "The normal-fortnight comparison is the noise floor: a change smaller than that is not a storm signal. Where ± is as large as the value the row says so. Rank is by open water only; wet crops are a weak signal (radar cannot tell them from normal field change), so the total is optional." (now "Rank is by open water. The total with wet crops is optional."); the column unit "% ± pts, weak signal" (now "% ± pts"). (Structure of the card unchanged.)
- Eye profile: `profile.json` `notes` (shown as a muted paragraph), original: "Backscatter only; no wind speed is derived. The eye is faint in L-band VV (prominence 0.76 dB over the 12-25 km annulus at 5 km smoothing); the ring profile mixes near and far range ..." and `calm_reference_caveat` ("Caveat." note); tag `placeholder.tag`.
- Lives now: `profile.json`, `docs/METHODS.md` section 3 "Eye profile" and Limitations. Pitch deck: yes (the "eye is faint" statement is a scientific limit).

### 19. Histogram, alerts, colour key
- Histogram intro, original: "... It shows why the water classes can or cannot be separated." and the footer "Source: <layer>.json, made from <file>.h5."; kept: "No water cut is used on the sea: brighter simply means a rougher surface." and the no-data share.
- Alerts credit line, original ending: "Alerts are not confirmed by radar."
- Colour key card, original ending of the intro: "The words say what a colour often means; the colours alone are not the key."
- Pitch deck: no (wording only).

### 20. About and sources
- Removed sources (not used for any map or number): NISAR mission site ("Mission overview. Background link only."), NISAR Data User Guide ("Background reading from the Alaska Satellite Facility (ASF) on how NISAR files are laid out. Not a data source."), NISAR StoryMaps and NISAR Applications White Papers ("Background reading only. Not used to make any map or number on this page."), NASA ARSET: Introduction to SAR ("Background training on how synthetic aperture radar works. Not used to make any map or number on this page.").
- Removed paragraph "Not used.": "ASF Vertex was not used; scenes were found with the NASA CMR and ASF search APIs. CSA RCM and RADARSAT-1, and CONAE SAOCOM, were not fetched for this pilot. NISAR L-band covers the study area (team to confirm). ISRO S-band scenes are not processed yet."
- Removed from the intro: "Not an official NASA, ISRO, IMD or government product, and not a warning service." (the footer line carries it).
- Lives now: `app/strings/strings.en.json` (`dash.about.*`), `docs/review/RESOURCE_AUDIT.md`. Pitch deck: yes for the reading list and the S-band status; no for the "team to confirm" wording.

### 21. "What radar cannot tell you" detail card (Data tab)
- Moved there on 15 Nov, then removed with item 9 (same text). Shown again only with `cav()`.

## Both tabs: states and messages (reworded, not removed)
| Where | Original | Now |
|---|---|---|
| Load error banner | "The data files could not be loaded (<error>). Serve the repo root with "python3 -m http.server 8000" and open http://localhost:8000/app/dashboard-mockup/ ." | "The data for this page could not be loaded. Please reload the page or try again in a moment." (error still logged to the console) |
| Missing optional files banner | "Some files are not ready yet (<names>). The parts that need them show as unavailable; the rest works." | "Some parts of this page are still loading. The rest works as usual." |
| Missing picture (caption) | "Radar layer data not loaded yet. The picture for this view is not available in this copy of the project. Outlines and numbers still work." | "This picture could not be loaded. Outlines and numbers still work." |
| Missing picture (tick box) | "Not loaded yet" / "Layer data not loaded yet" | "Could not load" / "This picture could not be loaded" |
| Numbers pending | "Pictures are ready, numbers are coming." | "The pictures are ready. The numbers follow shortly." |
| Sea or pass finding missing | "Finding not available yet." | "No finding for this pass." |
| Alerts snapshot missing | "The alerts snapshot is not ready yet." | "No alerts to show right now." |
| Mandal ranking missing | "The mandal numbers are not ready yet. Check back soon." | "Mandal numbers appear here once the latest pass is processed." |
| Eye profile missing | "The eye profile is not ready yet." | "The eye profile appears here once an eye pass is processed." |

## Kept on purpose (for the reviewer's judgement)
- "Not an official warning. Follow IMD, APSDMA and your district officers." (the permanent official line under the tab bar, a safety message) and the page footer.
- The map caption "Source" row and all credit lines (NISAR credit string, GDACS, SACHET, IMD, geoBoundaries, Esri).
- Legend labels such as "very bright with weak cross-pol, possible double bounce" (they name the colour, they are not data-quality notes).
- "Wet crops are not counted here. The raw numbers list them." and "This mandal is not in the ranking: too little of it is inside the radar picture to compare it fairly." (data coverage).
- "Summary not available yet." fallback when no findings file exists.

## Added at final check (15 Nov)
- What-happened tab, event eye paragraph (`events.json` story.eye_profile, filtered in `dash.js` `para()`): the sentence "The eye is small and weak in this radar view (about 5 km core, bright ring near 14 km)." is hidden. Source text unchanged in `data/processed/events.json`. Pitch deck: yes (the eye is faint in L-band VV, 0.76 dB prominence).
- `data/web/story.json` event chip text still reads "(alert, not reviewed)" (string in `app/strings/story.en.json`; a test asserts it). `dash.js` rewrites it to "(alert)" on the page. The public JSON and feeds still carry the original wording.
