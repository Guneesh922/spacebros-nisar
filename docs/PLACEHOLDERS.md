# Placeholders: what is still open

Checked on 15 Nov 2026 against `data/processed/manifest.json`, `data/processed/*.json`, `data/h5/catalog.json`, `data/web/` and `app/dashboard-mockup/js/dash.js`.

**No layer or data file is a sample any more.** All 33 layers in the manifest have `placeholder: null` and `bounds_inferred: false`; `mandal_rank.json`, `profile.json`, `alerts.json` and `events.json` carry no `placeholder` key. The "Sample values" and "Quick-look sample" tags in `dash.js` only appear when a layer or file sets `placeholder.is`, so none shows today. What is left is below. "Who" is the role that owes the item.

## 1. What is real now

| Item | Where | Notes |
|---|---|---|
| 8 L-band scenes (COAST T55 HH/HV 4, 16, 28 Oct and 9 Nov; SEA T48 VV/VH 3, 15, 27 Oct and 8 Nov) | `data/h5/*.h5`, `data/h5/catalog.json` | Bounds come from the H5 files. 4 are PROVISIONAL (baselines 3 Oct, 4 Oct, 15 Oct, 16 Oct), 4 are VALIDATED products; the status is shown in the credit line. |
| Greyscale display PNGs for those 8 scenes | `data/web/nisar_l_{coast,sea}_*.png` | Built by `tools/build_web.py` from the H5 files (per-role stretch). `data/web` is git-ignored and rebuilt by Pages. |
| Colour composites (dual-pol RGB) for the 8 scenes | `data/web/nisar_l_{coast,sea}_rgb_*.png` | Recipe and checks: `docs/review/RGB_COMPOSITE.md`. |
| Class maps for 28 Oct and 9 Nov (new water, wet crops, no change) | `data/web/class_*.png`, `class_stats.json` | Method: `docs/METHODS.md`. |
| Coast change layers for 28 Oct and 9 Nov | `data/web/nisar_l_coast_change_*.png` | Brightness change against the PROVISIONAL baselines. |
| Sea difference 27 Oct vs 15 Oct, and 8 Nov vs 15 Oct | `data/web/nisar_sea_diff_*.png` | The 27 Oct signal is mostly storm (`docs/review/LBAND_TEST.md`). |
| Mandal rank | `data/processed/mandal_rank.json` | 54 ranked rows plus the flagged ones, real zonal statistics from the class maps. |
| Eye profile | `data/processed/profile.json` | From the 27 Oct VV subset: eye radius 6.4 km (+/-0.5), IMD offset 10.4 km. |
| Alerts | `data/processed/alerts.json` (alerts-v2) | GDACS and SACHET, Andhra Pradesh only. |
| Open-Meteo marine and flood points | manifest layers `open_meteo_*` | `coordinates_confirmed: true` (16.0 N 82.0 E; 16.925 N 81.725 E). |
| Credit lines | manifest `sources[]` | 10 of 11 have `credit_confirmed: true`; the exception is in section 2. |

## 2. Values to confirm

| Item | Where | Needed | Who |
|---|---|---|---|
| GDACS credit line is `GDACS` with `credit_confirmed: false` (alerts.json uses "GDACS (EC JRC / UN OCHA)") | manifest `sources[gdacs]` | pick one wording and set `credit_confirmed` | owner |
| geoBoundaries licence: manifest says to check geoboundaries.org (project site states CC BY 4.0; earlier notes said ODbL-1.0) | manifest `sources[geoboundaries]` | confirm the licence and fix every credit string that says ODbL | owner |
| VIIRS satellite for saved events (NOAA-21 used; SNPP stops 2 Nov in `gibs_layers.json`) | layer `gibs_viirs_truecolor` | a human picks the satellite | owner |
| Landfall time (`time_utc: null`, note "time being confirmed (IMD)") | event `arnab_2026` | a human decides what to state (IMD texts disagree) | owner |
| Two auto drafts, Murasu (`auto_GDACS_1001346`, radar_linked) and Flood in India (`auto_GDACS_1104248`, alert_only) | `data/processed/events.json` | not reviewed by a person | owner |
| GDACS and SACHET fetch from a GitHub runner | `update.yml` | untested; fails soft and keeps the snapshot with its real date | backend |

## 3. Open analysis and content items

| Item | Where | Status | Who |
|---|---|---|---|
| S-band | `data/h5/S_*`, `data/raw/nisar_s` | no files exist, nothing built | backend |
| Optical and INSIGHT links | `docs/BACKEND_GAPS.md` (optical image row), layer `gibs_viirs_truecolor` | VIIRS true colour is a live GIBS layer; no optical image is exported or linked. No INSIGHT link was found in the manifest, config, docs or the dashboard code, so its state is not verified. | backend / owner |
| Domain review of the English templates (findings text, "what radar cannot tell you") | `data/processed/findings/*.json`, `app/dashboard-mockup/js/findings.js` | not reviewed by a domain expert; the dashboard shows the tag "Draft: to be reviewed" on the "cannot tell" verdicts (`dash.js`, `F.cannot_tell.draft_tag`) | domain expert |
| Wet-crops class | `docs/METHODS.md`, `docs/review/LBAND_TEST.md` | unproven: not separable from normal field change (a normal fortnight gives 112 km2 against 140 km2 on 28 Oct), no ground truth. Headlines use new open water only. | owner |
| Mangrove HV-minus-HH change at Coringa | `tools/experimental/mangrove_change.py`, `data/processed/experimental/mangrove_change.json`, `docs/review/MANGROVE_EXPERIMENT.md` | experimental, outside the pipeline and the UI; no detectable change (the ratio did not move; the corrected values depend on the reference used). No wording about damage or loss is allowed. | owner |
| A real run of the daily workflow on GitHub | `.github/workflows/update.yml`, `pages.yml` | emulated locally only (`tools/sim/`); not run on GitHub | owner |
