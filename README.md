# Pass by Pass · team SpaceBros

Team **SpaceBros** (Arkadeep Ray, Guneesh Gupta), NASA Space Apps Challenge 2026, Delhi local event.
Challenge: [Dancing with the SARs](https://www.spaceappschallenge.org/2026/challenges/dancing-with-the-sars/).

Pass by Pass shows what the **NISAR** L-band radar saw on the Andhra Pradesh coast (Godavari delta and the sea off it) around Cyclone Arnab (landfall 28 October 2026), one satellite pass at a time: a plain-language page for the public and a data page for officials and researchers.

- **Live site:** <https://guneesh922.github.io/spacebros-nisar/>
- **Pitch deck (PDF):** [docs/submission/Pass by Pass — SpaceBros — Dancing with the SARs_pitchdeck.pdf](docs/submission/Pass%20by%20Pass%20%E2%80%94%20SpaceBros%20%E2%80%94%20Dancing%20with%20the%20SARs_pitchdeck.pdf)
- **AI use disclosure:** [docs/submission/AI_USE_DISCLOSURE.md](docs/submission/AI_USE_DISCLOSURE.md)
- **Methods and limits:** [docs/METHODS.md](docs/METHODS.md)
- **Licence:** Apache-2.0 ([LICENSE](LICENSE))

## What is in this repository

| Path | What it is |
|---|---|
| `app/dashboard-mockup/` | The dashboard (plain HTML, CSS and JS, no build step); `app/strings/`, `app/css/tokens.css` and `app/vendor/` are its shared files |
| `data/h5/` | Data of record: 8 NISAR L-band study-box subsets (HDF5) and `catalog.json` |
| `data/processed/`, `data/reference/`, `config/areas.json` | What the page reads, the small reference inputs, and the area configuration |
| `tools/build_web.py`, `tools/build_story.py` | Build the display layers, numbers and plain-language findings from the H5 files |
| `tools/pipeline/` | Daily update: discover new scenes, subset, catalogue, alerts, events (`run_all.py` holds the order) |
| `tools/tests/`, `tools/check_manifest.py`, `tools/sim/` | Tests that gate every deploy, and local simulations of a new pass |
| `src/fetch/` | Scripts that fetched and subset the source data |
| `.github/workflows/` | `pages.yml` (build, test, deploy) and `update.yml` (daily data update) |
| `docs/` | Methods, pipeline, data storage, manifest schema, colour and L-band checks, IMD bulletins used, submission files |

## Web app: "Pass by Pass"

A static page (plain HTML, CSS and JS, no build step): the dashboard in `app/dashboard-mockup/` (tabs "What happened" and "Data for officials and researchers", one Leaflet map) for the Andhra Pradesh coast (Godavari delta and the sea off it), showing what NISAR L-band radar saw around Cyclone Arnab (landfall 28 Oct 2026) and the Murasu aftermath. English only.

- **Run it:** from the repo root run `python3 -m http.server 8000`, then open <http://localhost:8000/app/dashboard-mockup/>. The GitHub Pages root redirects there. Needs internet for Leaflet, fonts, the Esri dark basemap and the live GIBS, Open-Meteo and GDACS feeds (live feeds fail soft).
- **What it reads:** `data/processed/manifest.json` (schema: `docs/MANIFEST_SCHEMA.md`), `data/processed/*.json` and the display files in `data/web/` (git-ignored, built by `tools/build_web.py`). The data of record is the 8 L-band H5 subsets in `data/h5/` (4 coast scenes of track 55, 4 sea scenes of track 48).
- **Colour coding:** radar pictures are greyscale with a per-role stretch (coast HH, sea VV); change layers use one change ramp (grey band for "no clear change", darker and brighter ends); class maps use fixed colours (new open water blue, wet or flooded crops amber, no change as a faint grey outline); a dual-pol colour composite (RGB) is available beside the grey view. Checks: `docs/review/COLOUR_CHECK.md`, `docs/review/RGB_COMPOSITE.md`.
- **Presentation switch:** `config/areas.json` `presentation.show_data_caveats` is `false`: the product shows no data-quality disclaimers, only source credits and one "not an official product, not a warning service" line. The caveats live in the pitch deck and in `docs/METHODS.md`.
- **Alerts and events:** GDACS and SACHET (Andhra Pradesh only) feed draft events. A GDACS flood alert is linked to radar passes only if its footprint is within `defaults.flood_link_km` (50 km) of the coast box; otherwise it is shown as "alert only".
- **Brief and zip download:** a one-page brief and a zip of the chosen day can be downloaded from the page (`app/dashboard-mockup/js/export.js`).
- **Experimental, outside the pipeline:** `tools/experimental/mangrove_change.py` (mangrove HV-minus-HH change at Coringa; about 2 minutes and about 3 GB RAM; run `.venv/bin/python -I tools/experimental/mangrove_change.py`). Result: no detectable change; see `docs/review/MANGROVE_EXPERIMENT.md`. Not shown in the UI.

### Pipeline and tests

```bash
.venv/bin/python tools/pipeline/run_all.py --offline --skip-ingest   # catalogue, alerts, events, build_web, tests, story/findings
.venv/bin/python tools/build_web.py                                  # only the display assets from data/h5/
# the five checks run by run_all.py and pages.yml (each exits non-zero on failure):
.venv/bin/python tools/tests/test_story.py
.venv/bin/python tools/tests/test_findings.py
.venv/bin/python tools/tests/test_events.py
.venv/bin/python tools/tests/test_english_only.py
.venv/bin/python tools/check_manifest.py
```

Adding a daily scene needs `EARTHDATA_TOKEN` (ingest step only). The daily workflow is `.github/workflows/update.yml`; `tools/sim/` emulates it locally.

### Where the docs are

`docs/METHODS.md` (methods and caveats), `docs/PIPELINE.md`, `docs/DATA_STORAGE.md`, `docs/MANIFEST_SCHEMA.md`, `docs/ADDING_CONTENT.md`, `docs/PLACEHOLDERS.md` (what is still open), `docs/review/` (colour check, RGB composite, L-band test, mangrove experiment, resource audit), `docs/submission/` (pitch deck, AI use disclosure).

### Pre-event work

A starter repository (NISAR scene search and quick-look tools for Delhi) was committed on 13 November 2026, before the hackathon opened on 14 November 09:30 IST (commit `c4f110c`). It is not part of the product and was removed from the main branch; it remains in the git history. Everything else was built during the event.

## Data credits

Built by team SpaceBros for the NASA Space Apps Challenge 2026. Not an official NASA, ISRO, IMD or government product, and not a warning service. The dashboard is called "Pass by Pass" (earlier name: "Coast Radar Watch").

Exact credit strings (use them wherever the data is shown, copied or downloaded):

- NISAR: `NISAR L2 GCOV, NASA/JPL-Caltech and ISRO, via ASF DAAC (NASA Earthdata)`, followed by scene date, track, polarisation and PROVISIONAL or VALIDATED status. Maps and numbers made by us: `SpaceBros, derived from NISAR data`.
- Alerts and storm facts: IMD / RSMC New Delhi bulletins; NDMA SACHET; GDACS (EC JRC and UN OCHA).
- Mandal outlines: geoBoundaries gbOpen India ADM3, boundary year 2018, ODbL 1.0 (attribution and share-alike; licence as reported by the geoBoundaries API, source Pathways Data Pvt. Ltd. / lgdirectory.gov.in). District names for the mandals: the 2022 Andhra Pradesh district lists (see `data/interim/C/mandal_district_2022_complete.csv`).
- Basemap: `Map data: Esri, HERE, Garmin, OpenStreetMap contributors` (Esri World Dark Gray Canvas; the line is shown in the map corner).
- Other live layers: NASA GIBS (VIIRS, IMERG, Himawari), Open-Meteo.com (CC BY 4.0), MOSDAC/SAC/ISRO link.
- Images: no NASA, ISRO or Space Apps logos or insignia, and no AI-generated images, are used. All pictures on the site are radar or map products built from the H5 files.
