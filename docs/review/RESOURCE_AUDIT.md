# Resource audit: challenge resources, polarisations, sea calibration note

Read-only audit, 14 Nov 2026. Method: grep (case-insensitive, several spellings) over src/, tools/, app/, data/*.json,
data/sources.yaml, data/reference/, docs/, docs/submission/, README.md, app/dashboard-mockup/ and app/strings/.
Line numbers are from the files as they stood at audit time. Nothing outside this file was edited.

## Where the About text lives

| surface | file + element | what it says today |
|---|---|---|
| Main app About dialog | `app/index.html` `#about-btn` (line 37), `#about-dialog` (lines 87-92), `renderAbout()` (lines 245-284) | `shell.about.*` text (`app/strings/shell.en.json:13-21`) plus one row per entry in `data/processed/manifest.json` `sources` (credit, licence, link) |
| Case story "About this story" | `app/js/case.js` lines 364-393; strings `app/strings/case.en.json` lines 98-116 (`case.about.*`) | Data, Methods, Limits, Credits, "What is placeholder" |
| Dashboard (approved UI, do not redesign) | `app/dashboard-mockup/js/dash.js`: Layers card `#d-layers` (line 865, source/credit column line 565), Downloads `#d-files` (line 878), cite block `citeText()` (line 761) | No separate About dialog. Credits sit in the layer table and the cite text |
| Repo readme | `README.md` "Data credits" (lines 80-83) | "NISAR data: NASA/JPL-Caltech and ISRO, distributed by the Alaska Satellite Facility DAAC." |

## Task 1: challenge-resource table

| resource | used in code/data (file:line) | cited on page (About or app) | cited in submission docs | status | reason or gap |
|---|---|---|---|---|---|
| Earthdata (CMR search, Earthdata login) and ASF DAAC (NISAR L2 GCOV) | `src/fetch/subset_h5.py:44` (BASE), `:188-202` (token only to earthdata hosts); `src/fetch/download_l_band_h5.py:8`; `src/fetch/D_asf_manifest.py:23,183`; `tools/pipeline/discover.py:36` (CMR); `tools/pipeline/ingest.py:10`; `data/sources.yaml:14-63` (asf_nisar_l); 8 L-band H5 in `data/h5/` | Yes: `case.en.json:101` "through ASF DAAC"; manifest source `asf_nisar_l` credit shown in About dialog; `dash.js:761` cite text | `PROJECT_PAGE_DRAFT.md` §6 and §10 ref 1; `README.md` data credits | **used** | Fully supported. Earthdata Search (web tool) is not used; only the CMR API is. |
| ASF Vertex | Not used. Code calls the ASF search API (`data/sources.yaml:231` ASF_MANIFEST, `api.daac.asf.alaska.edu`), not the Vertex web tool | No | `PROJECT_PAGE_DRAFT.md:52` ("used to find scenes"); `README.md:77` | **cited only** | Submission text says Vertex was used to find scenes. The record shows the API and CMR were used. Fix the wording, or record a Vertex search before naming it. |
| NISAR Data User Guide (ASF) | Convention only, no citation: `src/fetch/subset_h5.py:467` ("gamma0 (RTC)"); `docs/DATA_STORAGE.md:43-44`; UR fallback URLs `data/sources.yaml:24,52,63` | No | `PROJECT_PAGE_DRAFT.md:52, 72`, §10 ref 2; `README.md:77` | **cited only** (convention used, not attributed) | Guide not read in this audit. Attribute the gamma0 label and the UR fallback to it in About Methods once the team has checked the guide text. |
| Intro to Remote Sensing / Intro to SAR / ARSET | Not used. No speckle, Bragg or double-bounce text in `app/`, `src/` or `tools/` (grep empty) | No | `PROJECT_PAGE_DRAFT.md:74` (§10 ref 4, "NASA ARSET SAR trainings"); plan `docs/handoff/06_PLAN_Eye_of_the_Storm.md:79` | **cited only** (draft) | No page text written yet that needs it. Remove from references unless a sentence is added that uses it. |
| NISAR StoryMaps | Not used. `app/dashboard-mockup/js/dash.js:435,488` "storymap" is an unrelated "Show on the map" button | No | `PROJECT_PAGE_DRAFT.md:52, 74`; plan `06_PLAN...md:80` | **cited only** (draft) | Draft says StoryMaps were used for plain-language notes on L-band, flooded vegetation and sea roughness. No such note exists in `app/` (grep for "flooded vegetation" empty). |
| NISAR Applications White Papers | Not used | No | `PROJECT_PAGE_DRAFT.md:52, 74` (§10 ref 4); plan `06_PLAN...md:80` | **cited only** (draft) | Same as StoryMaps. |
| UAVSAR Postcards | Not used | No | Plan only (`06_PLAN...md:80`); not in the submission draft | **not used** | No UAVSAR data in the repo and no note written that would cite it. |
| CSA RCM / RADARSAT-1 / CSA SAR tutorial | Not used. Grep finds RADARSAT/SAOCOM only in exclusion lists | No | `PROJECT_PAGE_DRAFT.md:55` says "not used"; `docs/DATA_ACQUISITION_PLAN.md:114` "Never fetch (master plan)" | **not used** | Reason recorded only as a plan exclusion. No written technical reason found (no C-band scene search in the repo). Team to confirm wording before the form says why. |
| CONAE SAOCOM | Not used (same exclusions as above) | No | `PROJECT_PAGE_DRAFT.md:55` "not used"; `DATA_ACQUISITION_PLAN.md:114`; plan `06_PLAN...md:82` | **not used** | Same as CSA: plan exclusion only. Team to confirm the reason. |
| ISRO S-band / Bhoonidhi / NRSC | Code only: `src/fetch/bhoonidhi_s_band.py:2-26` (search and download, API `bhoonidhi-api.nrsc.gov.in`); `src/fetch/subset_h5.py:16-19,405` (S-band schema, download URL); `data/reference/nisar_s_candidates.csv` (151 candidate rows, NISAR_SSAR_GCOV); `data/sources.yaml:297-304` (S_GCOV_DELTA, `blocked_credentials`). No S-band H5 in `data/h5/` (catalog: 8 scenes, all band L) | ISRO credit on page as joint mission (`case.en.json:27,101`; `shell.en.json:13`; manifest credit). Bhoonidhi and NRSC not named | `PROJECT_PAGE_DRAFT.md:55` ("not used unless a scene is confirmed [TBD]") | **not used** (S-band data); ISRO credit cited | No S-band product in any layer. Bhoonidhi download is blocked on credentials per `sources.yaml`. |

### Gaps

Each used resource needs a citation on the About surfaces and in the submission text. Each not-used resource needs one honest line.

**Must add or fix (About, `app/strings/case.en.json` `case.about.data_body` / `methods_body` and `app/strings/shell.en.json`):**
1. Earthdata (CMR) and ASF DAAC: already cited. Add "found with NASA CMR and the ASF search API" (what the code does).
2. ASF Vertex: do not name it as used unless a Vertex search is run and recorded. Either drop it or say the ASF search API was used.
3. NISAR Data User Guide: add a line in `case.about.methods_body` naming the gamma0 convention, after checking the guide text.
4. ISRO S-band / Bhoonidhi: add "S-band (ISRO, Bhoonidhi) searched but not used in any product" to `case.about.data_body`. Name Bhoonidhi.
5. Not used (CSA RCM, RADARSAT-1, CONAE SAOCOM, UAVSAR): one line in `case.about.limits_h` or Credits: "No RADARSAT/RCM, SAOCOM or UAVSAR data used." Confirm the reason first.

**Must fix in submission docs (`docs/submission/PROJECT_PAGE_DRAFT.md`, `README.md`):**
6. §6 line 52 and `README.md:77`: remove "ASF Vertex" from "used to find scenes" (see row 2). Remove "used to write the plain-language notes" for StoryMaps and white papers unless those notes exist.
7. §10 ref 4: keep "NASA ARSET SAR trainings" only if a sentence uses it. Otherwise remove.
8. §7 line 55: already says CSA and CONAE "not used". Keep, and add the reason once the team confirms it.
9. §10 ref 2 and ref 3: fine as references. Add a note that the guide was consulted only if it was.

**Not used, one honest line each (for the form):**
- CSA RCM / RADARSAT-1 / SAR tutorial: not used. Reason to confirm: plan exclusion (`DATA_ACQUISITION_PLAN.md:114`).
- CONAE SAOCOM: not used. Reason to confirm: plan exclusion (`DATA_ACQUISITION_PLAN.md:114`).
- UAVSAR Postcards: not used.
- ISRO S-band: searched and listed (151 candidates) but no S-band product was built; download blocked on credentials (`data/sources.yaml:297-304`).

## Task 2: polarisations per product

Only L-band data is in `data/h5/`. Polarisations in the H5 files: coast HH and HV; sea 3 Oct HV and VV; sea 15, 27 Oct and 8 Nov VH and VV (checked with h5py, read only).

| product | pol read | where (`tools/build_web.py`) |
|---|---|---|
| Coast radar pictures (`nisar_l_coast_*_t55_hh`) | HH (layer `pol` from manifest) | `build_layer` lines 173-206 |
| Coast and sea histograms (`hist.counts`) | every pol in the file: HH and HV on coast; VV plus VH or HV on sea. 3x3 smoothed HH and HV on coast only | `_pols_in` 167-170; `build_layer` 218-224 |
| Coast class maps (new water, wet crops, no change) and `class_stats.json` | HH and HV. HH for the water threshold (Otsu, lines 610-615) and HH change; HV for the change test (lines 630-637) and the crops rule (`HV_CROPS_SIGMA`, line 421) | `compute_coast_classes` 562 (HH, HV loaded at 577-578; medians removed at 631-632); `build_class_maps` 717 |
| Mandal ranking (`mandal_rank.json`, `by_date`) | Indirect: shares of the class rasters above, so HH and HV | `build_mandal_rank` 916 |
| Sea radar pictures (`nisar_l_sea_*_t48_vv`) | VV (manifest pol) | `build_layer` 173 |
| Sea difference map (`nisar_sea_diff_*`) | VV minus VV only. Default pol VV; scenes filtered to VV | `build_sea_difference` 343, pol at 357, filter at 362; `_sea_diff_one` 259, `diff = da - db_` at 293 |
| Eye profile (`profile.json`) | VV only, 27 Oct, track 48 | `build_profile` 1238, VV read at 1250; `find_eye` 1190 |
| Story numbers (`story.json`, findings) | No H5 read and no pol name. Use class_stats (HH+HV), mandal_rank (HH+HV) and profile (VV) | `build_story.py`: `class_summary` 330-347, `card_for` 358 (mandal_rank at 393), `sea_updates` 492-520 (profile at 498-520) |

Answer: the coast products use HH and HV. The sea products use VV (and the profile uses VV). VH is never read for any product, only present in the sea histograms. `build_story.py` reads no polarisation directly; it inherits from the JSON files above.

## Task 3: calibration note on the sea difference map

- Sources: `docs/STATUS.md:37` (open item, unchecked: "check 15 Oct (PROVISIONAL) vs 3 Oct calibration offset before quoting numbers (median diff is +3.7 dB)") and `:56`. `docs/METHODS.md:55` says a calibration offset between the 4/16 Oct baseline and the event scenes "cannot be excluded", with HV numbers, but does **not** state the +3.7 dB sea figure.
- Code search for offset, calib, 3.7, median, provisional in `tools/build_web.py` and `tools/build_story.py`: no offset or correction is applied to the sea difference. `diff = da - db_` (line 293) is a raw subtraction. The sea median is stored in `data/web/nisar_sea_diff_20261027_vs_20261015.json:56` (`p50: 3.74`). The only medians removed in code are the coast normal-fortnight medians (lines 618-632), which are not applied to the sea map.

**Applied in code? No** (`tools/build_web.py:293`, `_sea_diff_one`). No correction, no note, and no provisional flag is written into the sea difference json. The json only carries `before.product_status: PROVISIONAL` (`data/web/nisar_sea_diff_20261027_vs_20261015.json`).

**Shown to the user? Partly, yes, through hand-written manifest text.** The sea difference layer in `data/processed/manifest.json:837` has `limit`: "wind speed (it is a brightness change); the 15 Oct calm reference is provisional and patchy, so the level may be overstated". It appears in the map caption "Limit" (`app/js/map.js:467`) and the Layers card (`app/dashboard-mockup/js/dash.js:560`). The median +3.7 dB itself is not shown anywhere (no `p50` use in `dash.js`, `map.js` or `case.js`). The layer `shows` text (`build_web.py:392`) does not mention the provisional reference. The sea story text does not use the difference numbers.

Open point: the calibration check in `STATUS.md:37` is not done. The 3 Oct scene has VV, so the check is possible.

## Summary for the caller

- Not-used rows: UAVSAR Postcards; CSA RCM / RADARSAT-1 / tutorial; CONAE SAOCOM; ISRO S-band (code and candidate list only, no product). Also cited-only in drafts: ASF Vertex, StoryMaps, white papers, ARSET, Data User Guide.
- Used and cited: Earthdata/ASF DAAC (L-band), ISRO credit (joint mission).
- Polarisations: coast = HH and HV; sea and sea difference and eye profile = VV; VH only in sea histograms; `build_story.py` reads no pol directly.
- Calibration: **not applied in code** (`build_web.py:293`). **Shown to the user partly**: the manifest `limit` text on the sea layer (`manifest.json:837`) says the 15 Oct reference is provisional and the level may be overstated. The +3.7 dB figure is not shown. The check in `STATUS.md:37` is still open.
