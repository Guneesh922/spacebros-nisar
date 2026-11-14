# SpaceBros · Dancing with the SARs

Team **SpaceBros** (Arkadeep Ray, Guneesh Gupta) – NASA Space Apps Challenge 2026, Delhi local event.
Challenge: [Dancing with the SARs](https://www.spaceappschallenge.org/2026/challenges/dancing-with-the-sars/) –
build an interactive app that uses **NISAR** radar data to track and visualise surface change.

![Delhi through NISAR, Nov 2025 – Nov 2026](data/browse/delhi_T106/timelapse.gif)

## What's already here

| Path | What it is |
|---|---|
| `data/catalogue/delhi_scenes.csv` | Every NISAR GCOV (139) and GUNW (106) product over Delhi NCR, Nov 2025 → Nov 2026, with download URLs |
| `data/browse/delhi_T106/` | 28 quick-look crops of Delhi from descending track 106 (every 12 days) + `timelapse.gif` |
| `app/index.html` | Starter web viewer: map + date slider + play over 105 NISAR acquisitions on 4 tracks |
| `src/nisar_search.py` | Finds scenes for any area (no login) → CSV + `app/scenes.js` |
| `src/fetch_browse.py` | Downloads public quick-looks for one track and crops them (no login) |
| `src/gcov_subset.py` | Streams **real backscatter** (HH, HV in dB) for the study area → GeoTIFF (needs Earthdata login) |
| `src/event_scenes.py` | Catalogue + public quick-looks for any region/date window (e.g. a cyclone) – no login |
| `data/events/cyclones_bay_of_bengal_2026/` | 154 NISAR acquisitions over the Bay of Bengal, 12 Oct–6 Nov 2026 (Cyclones Arnab & Murasu) |
| `src/change_map.py` | Before/after difference map from two GeoTIFFs |
| `notebooks/01_quickstart.ipynb` | All of the above step by step (works in Google Colab) |
| `docs/SUBMISSION_CHECKLIST.md` | What we must hand in and when |

## Quick start

```bash
git clone <this repo> && cd spacebros-nisar
pip install -r requirements.txt

# 1. no login needed
python src/nisar_search.py                 # refresh catalogue (edit AOI in src/config.py)
python src/fetch_browse.py --track 106     # quick-look time-lapse

# 2. real data (free NASA Earthdata account)
python src/gcov_subset.py --track 106 --start 2026-06-01 --end 2026-10-31
python src/change_map.py data/subsets/delhi/2026-06-09_T106_HHHH.tif data/subsets/delhi/2026-09-13_T106_HHHH.tif

# 3. viewer
open app/index.html                        # or: cd app && python -m http.server
```

**Earthdata login:** register at <https://urs.earthdata.nasa.gov/users/new>. Then either let the script prompt you,
or put `machine urs.earthdata.nasa.gov login USER password PASS` in `~/.netrc`.
**Never commit credentials** (`.gitignore` already blocks `.netrc` and `.env`).

## The data, in short

- **NISAR** = NASA–ISRO L-band SAR (24 cm wavelength). Sees through clouds, day and night.
- **GCOV** (Level 2) = geocoded backscatter, ~2–9 GB per scene. Bands: `HHHH` (HH power), `HVHV` (HV power).
  HV is high over vegetation, HH is high over buildings, both are low over calm water.
- **GUNW** = geocoded interferograms → centimetre-scale ground motion (subsidence, earthquakes).
- Delhi is covered by tracks **106 & 34 (descending, frame 74)** and **55 & 156 (ascending, frame 16)**,
  each revisiting every 12 days. Compare dates **within one track** only.
- Quick-look PNGs are public and fine for visuals; for numbers, use GCOV via `gcov_subset.py`.

## Story ideas for Delhi NCR (pick one on day 1)

1. **Yamuna monsoon floodplain**: water spreads in Jul–Sep (dark in HH) then retreats. Clear, visual "dance".
2. **Crop cycle around Delhi**: kharif → harvest → rabi wheat, seen in HV. Ties to stubble burning in Oct–Nov.
3. **Urban growth / construction**: new bright HH returns (Dwarka Expressway, Noida, Jewar airport).
4. **Land subsidence** (GUNW): parts of Delhi-NCR are documented as sinking from groundwater extraction.

## Web app (app/)

A static page (plain HTML, CSS and JS, no build step): a daily NISAR-centred coastal-hazard workspace for the Andhra Pradesh coast, with a saved Cyclone Arnab event and a Case study tab.

- **Run it:** from the repo root run `python3 -m http.server 8000`, then open <http://localhost:8000/app/>.
- **What it reads:** everything comes from `data/processed/manifest.json` (regions, layers, events, sources, analyses) and the files it points to (`mandals.geojson`, `mandal_rank.json`, `profile.json`, `alerts.json`, `img/*`). Adding a layer, event or region means editing the manifest only. Schema: `docs/MANIFEST_SCHEMA.md`.
- **Sample values:** anything that is not real data yet is tagged on screen ("Sample values", "Quick-look sample", "Draft: to be reviewed"). The list is in `docs/PLACEHOLDERS.md`; what the backend still owes is in `docs/BACKEND_GAPS.md` (section 13 was added during the frontend review).
- **Needs internet:** Leaflet, Chart.js, Scrollama, Google Fonts, Esri basemap tiles and the live GIBS, Open-Meteo and GDACS feeds are loaded from the web; live feeds fail soft with an "unavailable" message.

## Community & links

- Delhi WhatsApp community: <https://chat.whatsapp.com/G51kBazKRdnHrRxi5VPRoS>
- Instagram: <https://www.instagram.com/nasaspaceappsbyuwr/> · Website: <https://www.spaceappsindia.com>
- ASF Vertex (browse NISAR by map): <https://search.asf.alaska.edu/> · NISAR data user guide: via the challenge Resources tab
- Schedule: hackathon starts Sat 14 Nov 09:30 IST, ends **Sun 15 Nov 23:59 IST**

## Data credits

NISAR data: NASA/JPL-Caltech and ISRO, distributed by the Alaska Satellite Facility DAAC.
Basemaps: © OpenStreetMap contributors; Esri World Imagery.
