# data/ layout (Eye of the Storm – Cyclone Arnab)

Source list: `sources.yaml` (machine-readable) and `../docs/DATA_ACQUISITION_PLAN.md` (human-readable).
Every fetch writes a report in `logs/<package>.md` (what, size, sha256, failures). Nothing in here is ever invented:
if a source fails, the file is missing and the log says why.

| Folder | What goes in it | In git? |
|---|---|---|
| `raw/` | Straight-from-source downloads and NISAR box subsets. Sub-folders: `gibs/` (GIBS snapshots), `imd/` (non-PDF IMD material), `insat/`, `scat3/`, `era5/`, `boundaries/` (full geoBoundaries files), `water/` (JRC GSW tile), `coast/` (OSM / Natural Earth zips), `nisar_l/sea/` + `nisar_l/coast/` (L-band GCOV subsets, GeoTIFF dB), `nisar_s/` (S-band from Bhoonidhi) | **No** – `data/raw/` is ignored wholesale (existing rule). The `.gitkeep` files here are therefore local only; recreate with the fetch scripts / `sources.yaml`. |
| `reference/` | Small, clipped or typed inputs the pipeline and the page rely on: `imd_track_arnab.csv`, `scene_manifest.csv`, `asf_probe_*.csv`, `mandals_delta.geojson`, `districts_delta_gb2021.geojson`, `mandal_district_2022.csv`, coastline clips, `gibs_layers.json`, `era5_wind_summary.csv` | Yes (keep each file < 5 MB) |
| `interim/` | Working rasters/arrays between raw and processed (e.g. `gsw_occurrence_delta.tif`, co-registered stacks, class maps before colouring) | Rasters/arrays ignored; small CSV/JSON tracked |
| `processed/` | Web-ready outputs read by `app/` via `manifest.json`: PNG overlays with bounds, JSON numbers (`eye.json`, mandal stats) | Yes (page budget: 15 MB total) |
| `logs/` | One markdown report per fetch package / processing run | Yes |
| `events/`, `catalogue/`, `browse/` | Pre-event catalogues and quick-looks (unchanged) | as before |
| `subsets/` | Old Delhi default output of `src/gcov_subset.py` (ignored) | No |

IMD bulletin PDFs live in `../docs/imd_bulletins/` (tracked). Fetch scripts written during the weekend live in `../src/fetch/` (tracked);
`src/fetch/subset_arnab.py` streams the NISAR boxes (needs Earthdata login, never downloads whole files).

Naming: `<YYYY-MM-DD>_T<track>_<layer>.tif` for NISAR subsets; `<source>_<product>_<date or time>_<box>.<ext>` otherwise.
Boxes (W,S,E,N): delta 81.6,16.2,82.6,17.1 · sea 81,15,85,18 · context 78,12,88,20 · clip_vectors 81,15.8,83,17.6.
Credentials: `~/.netrc` or env vars only – never in this folder.
