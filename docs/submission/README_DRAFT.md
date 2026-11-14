# Eye of the Storm - NISAR coastal-hazard workspace (SpaceBros)

Team **SpaceBros** (Arkadeep Ray, Guneesh Gupta) - NASA Space Apps Challenge 2026, Delhi local event (virtual), challenge [Dancing with the SARs](https://www.spaceappschallenge.org/2026/challenges/dancing-with-the-sars/).

When Cyclone Arnab reached the Andhra Pradesh coast in October 2026, cloud hid the sea and the Godavari delta from ordinary cameras. NISAR, the NASA-ISRO L-band radar satellite, imaged through it. This project is an open-source, static web app that puts NISAR passes next to the IMD track, satellite cloud and rain layers, waves and official alerts, with the date, source, credit and one plain line on what each layer cannot show. Every layer comes from one file, `data/processed/manifest.json`, so a new storm, region or hazard is a manifest edit, not a rebuild.

> **Status honesty:** NISAR layers show display-only quick-look browse images, and the eye profile, mandal ranking and alerts files hold sample values, until real GCOV subsets are processed. Each is tagged on screen ("Quick-look sample", "Sample values") and listed in [docs/PLACEHOLDERS.md](docs/PLACEHOLDERS.md). **[TBD from real product: update this box when real products land.]**

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
# open http://localhost:8000/app/
```
It needs internet: Leaflet, Chart.js, Scrollama, Google Fonts, Esri/OSM basemaps and the live GIBS, Open-Meteo and GDACS feeds load from the web (live feeds fail soft with an "unavailable" message). Do not open `app/index.html` by double-click; the manifest is fetched over HTTP.

## Run it on GitHub Pages
1. Repo Settings -> Pages -> Deploy from branch `main`, folder `/ (root)`. (The app reads `../data/processed/`, so serve from the root, not from `/app`.)
2. Open `https://<user>.github.io/spacebros-nisar/app/` (for this repo: **[confirm URL once enabled]** https://guneesh922.github.io/spacebros-nisar/app/).
3. Check in a private window that the live feeds (GDACS, Open-Meteo, GIBS) load from the github.io origin. If one is blocked, the strip shows the snapshot only.

## Repository layout
| Path | What |
|---|---|
| `app/` | Static web app (`index.html`, `js/`, `css/`, `strings/`). `app/legacy/` is the earlier Delhi viewer. |
| `data/processed/` | Everything the page loads: `manifest.json`, `mandals.geojson`, `mandal_rank.json`, `profile.json`, `alerts.json`, `imd_track_arnab.geojson`, `img/*`. Tracked, web-ready, page budget under 15 MB. |
| `data/sources.yaml` | Machine-readable source list with ids, access, status. |
| `data/reference/`, `data/logs/` | Reference tables (IMD track CSV, boundaries, GIBS layer list) and fetch logs. |
| `data/raw/` | Git-ignored downloads and GeoTIFF subsets. Not served. |
| `src/fetch/` | Event-pipeline fetch scripts (`subset_arnab.py` for NISAR, GIBS, IMD, ASF manifest, boundaries, ERA5). |
| `src/*.py`, `notebooks/` | Pre-event starter tools (search, quick-look download, GCOV subset, change map). |
| `tools/` | `make_web_assets.py`, `check_manifest.py`, `audit_page.sh`. |
| `docs/` | `MANIFEST_SCHEMA.md`, `PLACEHOLDERS.md`, `BACKEND_GAPS.md`, `ADDING_CONTENT.md`, `docs/handoff/` (plan), `docs/submission/` (submission drafts). |

## Regenerating the data
You need a free **NASA Earthdata login** (https://urs.earthdata.nasa.gov/users/new) in `~/.netrc` (`machine urs.earthdata.nasa.gov login USER password PASS`) or the env vars the script documents. Never commit credentials (`.netrc` and `.env` are git-ignored).
```bash
pip install -r requirements.txt
# 1. stream only the study boxes of NISAR GCOV from ASF into data/raw/nisar_l/*.tif
python src/fetch/subset_arnab.py --probe L_SEA_EYE_1027   # login check, list layers
python src/fetch/subset_arnab.py --ids P0                  # core scenes (see data/sources.yaml)
# 2. export web-ready PNGs, mandal boundaries, IMD track into data/processed/
python tools/make_web_assets.py
# 3. validate the manifest
python tools/check_manifest.py          # add --files to list files still missing
```
After real GeoTIFFs exist, replace each placeholder file named in `docs/PLACEHOLDERS.md` and set its `placeholder` to `null` in the manifest. No code change is needed. Adding a layer, event or region: `docs/ADDING_CONTENT.md`, schema in `docs/MANIFEST_SCHEMA.md`.

## Data credits
| Data | Provider | Use here | Licence / credit |
|---|---|---|---|
| NISAR L-band L2 GCOV | NASA/JPL-Caltech and ISRO, via ASF DAAC | Core radar layers | NASA open data; credit "NASA/JPL-Caltech and ISRO via ASF DAAC" **[confirm wording against ASF terms]** |
| GIBS / Worldview (VIIRS, IMERG, Himawari B13) | NASA | Live context | CC0 per project notes; credit NASA GIBS |
| IMD / RSMC New Delhi bulletins | India Meteorological Department | Track fixes, landfall position | Public PDFs, linked; credit IMD |
| SACHET alerts | NDMA | Dated snapshot | Credit NDMA **[licence to confirm]** |
| GDACS | EC JRC / UN | Live alerts | Credit GDACS |
| Open-Meteo Marine and Flood | Open-Meteo.com | Live waves, river discharge | CC BY 4.0, non-commercial |
| MOSDAC / INSAT-3DS | ISRO SAC | Link only, not hosted | Redistribution forbidden; **[credit line to confirm]** |
| geoBoundaries ADM3 (2018) | geoBoundaries | Mandal outlines | ODbL |
| OpenStreetMap, Esri World Imagery | OSM contributors, Esri | Basemaps, coastline | ODbL; Esri terms; **[OSM credit line to confirm]** |

## Limitations
- Pending real products, NISAR layers are quick-look images (not calibrated dB) and statistics are samples.
- Provisional-orbit (PR) scenes are used up to 16 Oct; validated GCOV_V1 from 22 Oct. Provisional scenes lack KML footprints, so their bounds are inferred from the same track and frame (`bounds_inferred`).
- Delta coverage by track 55 frame 10 is about 79 to 83 percent; the rest is empty by design.
- Class names say "likely". No flooded area in km2, no wind speed, no forecast.
- Landfall time is unresolved in IMD's own texts; the app says "time being confirmed (IMD)".
- Mandal boundaries are 2018 vintage; the 2022 district mapping was compiled from Wikipedia and not fully verified.
- The 24 cm vs 9 cm wave slider is an illustration. The "what radar can't show" verdicts are marked as drafts until expert-reviewed.
- NISAR S-band (Bhoonidhi) not used unless a scene is confirmed. No Telugu strings yet.
- No automated refresh: nothing re-runs the pipeline for new storms by itself.

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
Arkadeep Ray (team owner), Guneesh Gupta. Delhi local event: https://www.spaceappschallenge.org/2026/local-events/delhi/ . NISAR data: https://search.asf.alaska.edu/ .
