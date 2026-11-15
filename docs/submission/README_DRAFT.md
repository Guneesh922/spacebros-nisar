# Pass by Pass - NISAR coastal-hazard workspace (SpaceBros)

Team **SpaceBros** (Arkadeep Ray, Guneesh Gupta) - NASA Space Apps Challenge 2026, Delhi local event (virtual), challenge [Dancing with the SARs](https://www.spaceappschallenge.org/2026/challenges/dancing-with-the-sars/).

Built by team SpaceBros for the NASA Space Apps Challenge 2026. Not an official NASA, ISRO, IMD or government product, and not a warning service.

When Cyclone Arnab reached the Andhra Pradesh coast in October 2026, cloud hid the sea and the Godavari delta from ordinary cameras. NISAR, the NASA-ISRO L-band radar satellite, imaged through it. This project is an open-source, static web app that puts NISAR passes next to the IMD track, satellite cloud and rain layers, waves and official alerts, with the date and source credit of each layer. Every layer comes from one file, `data/processed/manifest.json`, so a new storm, region or hazard is a manifest edit, not a rebuild.

> **Status:** The 8 L-band NISAR scenes are real. They are H5 study-box subsets in `data/h5/`, and the images, class maps, mandal ranking and eye profile are built from them. Baselines (3, 4, 15 and 16 Oct) are PROVISIONAL products; event scenes (27 and 28 Oct, 8 and 9 Nov) are VALIDATED. S-band (ISRO) is not used in this submission. **[Team: confirm this status wording before submitting.]**

## What you can do in the app
- **Workspace**: map with a layer drawer (NISAR, derived, optical, weather, reference), a date control, region picker, and a compare/swipe view.
- **Events**: the saved Cyclone Arnab event (IMD track, before/during/after passes), alerts strip (GDACS live, NDMA SACHET snapshot), mandal ranking card and a downloadable one-page brief.
- **Case study**: a scroll story, from "what a normal camera saw" to "what radar can't show".

## Run it locally
No build step. Needs Python 3 only to serve files.
```bash
git clone https://github.com/Guneesh922/spacebros-nisar.git
cd spacebros-nisar
python3 -m http.server 8000
# open http://localhost:8000/app/dashboard-mockup/
```
It needs internet: Leaflet, Chart.js, Scrollama, Google Fonts, the Esri World Dark Gray Canvas and OSM basemaps, and the live GIBS, Open-Meteo and GDACS feeds load from the web (live feeds fail soft with an "unavailable" message). Do not open the app page by double-click; the manifest is fetched over HTTP.

## Run it on GitHub Pages
1. GitHub Pages is set up for this repo and deploys from the workflow `.github/workflows/pages.yml`. (The app reads `../data/processed/`, so it is served from the repo root, not from `/app`.)
2. Open https://guneesh922.github.io/spacebros-nisar/ , which redirects to `app/dashboard-mockup/`.
3. Check in a private window that the live feeds (GDACS, Open-Meteo, GIBS) load from the github.io origin. If one is blocked, the strip shows the snapshot only.

## Repository layout
| Path | What |
|---|---|
| `app/` | Static web app (`index.html`, `js/`, `css/`, `strings/`). `app/legacy/` is the earlier Delhi viewer. |
| `data/processed/` | Everything the page loads: `manifest.json`, `mandals.geojson`, `mandal_rank.json`, `profile.json`, `alerts.json`, `imd_track_arnab.geojson`, `img/*`. Tracked, web-ready, page budget under 15 MB. |
| `data/sources.yaml` | Machine-readable source list with ids, access, status. |
| `data/reference/`, `data/logs/` | Reference tables (IMD track CSV, boundaries, GIBS layer list) and fetch logs. |
| `data/h5/` | The 8 L-band NISAR study-box subsets (H5), the data of record. Committed to git. |
| `data/web/` | Build output: display PNGs and class maps. Not in git; rebuilt by the Pages workflow. |
| `data/raw/` | Git-ignored full granules and temporary downloads. Not served. |
| `config/areas.json` | Study area definition and presentation settings. |
| `src/fetch/` | Fetch and subset scripts, including `subset_h5.py` (cuts full NISAR granules to study-box H5 subsets), plus GIBS, IMD, boundaries and ERA5 fetchers. |
| `src/*.py`, `notebooks/` | Pre-event starter tools (search, quick-look download, GCOV subset, change map). |
| `tools/build_web.py` | Builds the display PNGs, class maps, `mandal_rank.json` and `profile.json` from `data/h5/`. |
| `tools/build_story.py` | Writes the findings and feeds. |
| `tools/pipeline/` | Daily update steps. `run_all.py` runs the whole order. |
| `tools/check_manifest.py` | Validates the manifest. |
| `app/dashboard-mockup/` | The dashboard: the live app that GitHub Pages opens. |
| `docs/` | `MANIFEST_SCHEMA.md`, `PLACEHOLDERS.md`, `BACKEND_GAPS.md`, `ADDING_CONTENT.md`, `docs/handoff/` (plan), `docs/submission/` (submission drafts). |

## Regenerating the data
You need a free **NASA Earthdata login** (https://urs.earthdata.nasa.gov/users/new) in `~/.netrc` (`machine urs.earthdata.nasa.gov login USER password PASS`) or the env vars the script documents. Never commit credentials (`.netrc` and `.env` are git-ignored).
Create a virtual environment and install the Python dependencies in `requirements.txt`:
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```
The data flow:
1. Full NISAR granules (0.85 to 7.5 GB each) are streamed or downloaded temporarily, then cut to the study boxes by `src/fetch/subset_h5.py`. The subsets are written to `data/h5/` and committed to git. Full granules are not kept once their subset is verified.
2. `python tools/build_web.py` builds the display PNGs and class maps into `data/web/` (not in git; the Pages workflow rebuilds it), and writes `mandal_rank.json` and `profile.json` to `data/processed/`.
3. `python tools/build_story.py` writes the findings and feeds.
4. `python tools/pipeline/run_all.py` runs the whole order above.
5. `python tools/check_manifest.py` validates the manifest (add `--files` to list files still missing).

Adding a layer, event or region: `docs/ADDING_CONTENT.md`, schema in `docs/MANIFEST_SCHEMA.md`.

## Data credits
| Data | Provider | Use here | Licence / credit |
|---|---|---|---|
| NISAR L-band L2 GCOV | NASA/JPL-Caltech and ISRO, via ASF DAAC | Core radar layers | Credit "NISAR L2 GCOV, NASA/JPL-Caltech and ISRO, via ASF DAAC (NASA Earthdata)" |
| GIBS / Worldview (VIIRS, IMERG, Himawari B13) | NASA | Live context | CC0 per project notes; credit NASA GIBS |
| IMD / RSMC New Delhi bulletins | India Meteorological Department | Track fixes, landfall position | Public PDFs, linked; credit IMD |
| SACHET alerts | NDMA | Dated snapshot | Credit "NDMA SACHET". Licence **[licence to confirm]** |
| GDACS | EC JRC / UN OCHA | Live alerts | Credit "GDACS (EC JRC / UN OCHA)" **[GDACS wording being confirmed]** |
| Open-Meteo Marine and Flood | Open-Meteo.com | Live waves, river discharge | CC BY 4.0, non-commercial |
| MOSDAC / INSAT-3DS | ISRO SAC | Link only, not hosted | Redistribution forbidden. Credit "Data Source MOSDAC/SAC/ISRO. https://mosdac.gov.in" |
| geoBoundaries ADM3 (2018) | geoBoundaries | Mandal outlines | Licence **ODbL 1.0** |
| OpenStreetMap, Esri World Dark Gray Canvas | OSM contributors, Esri | Basemaps, coastline | Credit "© OpenStreetMap contributors" (ODbL); Esri terms |

## Limitations
- Only 8 L-band scenes are used (H5 study-box subsets). S-band (ISRO) is not used in this submission.
- Baselines (3, 4, 15, 16 Oct) are PROVISIONAL products; event scenes (27, 28 Oct, 8, 9 Nov) are VALIDATED. Bounds come from the H5 files.
- Delta coverage by track 55 frame 10 is about 79 to 83 percent; the rest is empty by design.
- Class names say "likely". No flooded area in km2, no wind speed, no forecast. Area is reported only as likely new open water.
- Landfall time is not stated as one exact time: IMD's own texts give a window.
- Mandal boundaries are 2018 vintage; the 2022 district mapping was compiled from Wikipedia and not fully verified.
- The 24 cm vs 9 cm wave slider is an illustration. The "what radar can't show" verdicts are marked as drafts until expert-reviewed.
- No Telugu strings yet.
- Automated refresh: a daily GitHub Action (`.github/workflows/update.yml`, 05:23 UTC) searches for new NISAR scenes, ingests them, rebuilds and redeploys. It needs the repo secret `EARTHDATA_TOKEN` on days with a new scene.

## Pre-event work versus hackathon work
Space Apps rules say teams may not begin working on the challenge before the event. To keep this honest, the repository is split by tag:
- **`v0.1-pre-event`** marks the starter commits made on 13 Nov 2026, before the 14 Nov 09:30 IST start: NISAR catalogue and quick-look tools for Delhi (`src/*.py`, `data/catalogue/`, `data/browse/delhi_T106/`, `app/legacy/`, notebook) and the Apache-2.0 licence. **[Tag not yet created: `git tag v0.1-pre-event f603307 && git push origin v0.1-pre-event`.]**
- Everything after that tag (commit `ccc76ff` onward) was built during the hackathon: the Cyclone Arnab plan, `data/sources.yaml`, fetch scripts in `src/fetch/`, the manifest-driven app, `tools/`, and the docs. See `git log v0.1-pre-event..HEAD`.
- Delhi catalogues are not part of the submitted story. Compare: https://github.com/Guneesh922/spacebros-nisar/compare/v0.1-pre-event...main

## AI assistance
Claude (Anthropic) assisted with planning, code and drafting. See [docs/submission/AI_USE_DISCLOSURE.md](docs/submission/AI_USE_DISCLOSURE.md).

## Licence
Apache License 2.0 (see `LICENSE`). Data remain under their providers' terms (table above).

## Team and links
Arkadeep Ray (team owner), Guneesh Gupta. Delhi local event: https://www.spaceappschallenge.org/2026/local-events/delhi/ . NISAR data: https://search.asf.alaska.edu/ . Live app: https://guneesh922.github.io/spacebros-nisar/ . Repository: https://github.com/Guneesh922/spacebros-nisar
