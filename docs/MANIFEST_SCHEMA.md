# manifest.json schema v2

File: `data/processed/manifest.json`. Validate with `python3 tools/check_manifest.py` (add `--files` to list referenced files that are not on disk yet). The binding definition is section 3 of `docs/FRONTEND_BUILD_PLAN.md`; this page is the field-by-field reference. Adding an event, region, layer or hazard means editing this file only (plus dropping the files it points to). No code change.

Rules the page enforces from the manifest: every caption shows `credit` (or the source `credit_line`); any layer or analysis with `placeholder.is` shows a visible tag; class labels render with a leading "likely"; an unknown `status` is treated as `unavailable`; never put a landfall time, track number or date in code.

## Top level

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | 2 | A v1 file (layers only, v1 fields) still loads; missing v2 fields get defaults. |
| `generated_utc` | ISO time | Shown as "data last updated". |
| `app` | object | `default_region` (region id), `default_lang`, `page_budget_mb`. |
| `regions[]`, `sources[]`, `layers[]`, `events[]`, `analyses[]` | arrays | Below. |
| `files` | object | `mandals`, `alerts`, `profile`: paths of the companion files. |
| `coming_next[]` | `{id, name}` | Greyed "Coming next" entries (earthquake and landslide, oil spill, wildfire). |

## regions[]

| Field | Meaning |
|---|---|
| `id`, `name` | Unique id and display name. |
| `default` | `true` on exactly one region (the landing view). |
| `bounds` | `[[S,W],[N,E]]`, the order Leaflet wants. |
| `bounds_source` | Optional note on where the box came from. |
| `districts` | `null` = all, or a list of district names exactly as in the `district` property of `data/processed/mandals.geojson` (that file is built from `data/reference/mandal_district_2022.csv` by `tools/make_web_assets.py`). For Konaseema that is `Dr. B.R. Ambedkar Konaseema`. 81 of the 146 mandal polygons have `district: null`, so they appear only in regions with `districts: null` (for example `ap_coast`). |
| `parent`, `children` | Region ids; the picker nests children under the parent. |

## sources[]

One entry per provider. Layers point to it with `source_id`.

| Field | Meaning |
|---|---|
| `id`, `provider` | Registry id and full provider name. |
| `access` | `live` (browser fetches it), `snapshot` (saved file), `pipeline` (backend produces files), `link` (link out only). |
| `licence` | Plain licence line. |
| `credit_line` | What every caption shows. `[credit line to confirm]` marks an unknown one (listed in `docs/PLACEHOLDERS.md` section 6). |
| `credit_confirmed` | `false` when the credit line is unknown. |
| `can_host` | May we re-host the data (false for MOSDAC and live model feeds). |
| `delay_hint`, `url`, `note` | Free text shown in About and data. |

## layers[]

v1 fields (always present, same meaning): `id, group, name, chip, date, shows, source, credit, limit, png, bounds, default_on`.

| Field | Values and meaning |
|---|---|
| `id` | Unique. NISAR image ids follow `nisar_l_<sea\|coast>_<YYYYMMDD>_t<track>_<pol>`. |
| `group` | `before`, `during`, `after`, `next`. Only used while an event is loaded. Layers not tied to a date use `during` (or `after`). |
| `type` | `nisar`, `derived`, `optical`, `weather`, `reference`, `alerts`: the drawer groups by this, NISAR first. Keep NISAR and derived layers first in `layers[]`. |
| `chip` | `nisar`, `context`, `model`, `reference`. NISAR and derived layers use `nisar` (teal chip). |
| `name`, `shows`, `limit`, `source`, `credit` | Caption copy. `shows` is "Shows", `limit` is the text after "Can't show:" (one plain line), `source` is the short source label, `credit` overrides the source `credit_line`. |
| `source_id` | Must exist in `sources[]`. |
| `kind` | `image` (PNG overlay with `bounds`), `wmts` (tile layer), `geojson` (vector, needs `file`), `live` (fetched JSON, needs `url_template`), `link` (no overlay; needs `link_url` or `file`). |
| `date`, `time_utc` | ISO date or `"live"` or a year; exact pass time for scenes. |
| `latest_of` | Layers sharing the key form a time series; the newest is "latest". Keys used: `nisar_l_sea_vv`, `nisar_l_coast_hh`. |
| `png` | Path under `data/processed/img/`. `null` for non-image layers. |
| `bounds`, `bounds_inferred` | `[[S,W],[N,E]]` of the full image. `bounds_inferred: true` when no KML exists and the box was copied from the same track/frame of a later pass. `bounds_source` explains. |
| `url_template` | Tile or API URL. WMTS uses `{time}/{z}/{y}/{x}`; live uses `{lat}`/`{lon}` filled from `config`. |
| `latest_available_lag_days` | wmts only. Integer: the newest date the source usually has is today minus this many days. The page tries that date, then one and two days earlier. `time_step` and `time_format` say how to build `{time}`. |
| `config` | Free object. Live layers: `{lat, lon, coordinates_confirmed, timeout_ms}`. WMTS: `layer, tile_matrix_set, format, max_native_zoom`. |
| `band`, `pol`, `track`, `frame`, `direction` | Radar metadata. `band:"S"` enables the L/S toggle (none exists yet). Never use Track 156 (it does not cover the delta). |
| `processing_level` | NISAR layers: `provisional` (PR, up to 16 Oct) or `validated` (GCOV_V1, from 22 Oct). Captions should say which. |
| `regions` | Region ids where the layer is offered. |
| `event_id` | When set, the layer is listed only while that event is loaded. |
| `classes` | Class layers only: `[{id, label, colour, style, default_on}]`. `label` must start with "likely". `style` is `fill` (needs `#RRGGBB`) or `outline` (`colour` null). One class per layer here; layers sharing `class_group` form one legend. |
| `period`, `normal_period` | Derived layers: the before/after pair and the normal period used. |
| `default_on`, `opacity` | Initial visibility and opacity. On the landing view only the latest NISAR coast layer and the mandal boundaries are on; GIBS stays off. |
| `status` | `ready`, `coming_next`, `link_only`, `unavailable` (no file yet: shown as unavailable with last-known time). |
| `placeholder` | `null`, or `{is, tag, replaced_by}`. When `is` is true both strings are required. `tag` is printed on the page; `replaced_by` is the real file. |

## events[]

| Field | Meaning |
|---|---|
| `id`, `name`, `hazard`, `gdacs_id` | Identity. `gdacs_id` is null for a saved event with no GDACS entry. |
| `region` | Region the map flies to. |
| `dates` | `before`, `during`, `after` (ISO) and `normal_period` `[from,to]`. |
| `layers` | `{before:[ids], during:[ids], after:[ids]}`; every id must exist. |
| `default_on` | Layer ids switched on when the event opens; the first must be a NISAR layer and every id must appear in `layers`. |
| `analysis_id` | Analysis the ranking card reads. |
| `track_geojson` | Optional track file. |
| `landfall` | `{lat, lon, time_utc, note}`. Keep `time_utc: null` with the note "time being confirmed (IMD)" until a human decides. |
| `case_study` | `true` adds the Case study tab content for this event. |

## analyses[]

`id`, `region`, `period [from,to]`, `normal_period [from,to]`, `rank_file` (path to `mandal_rank.json`), `class_layers` (layer ids), `placeholder`.

## Companion files

- `mandal_rank.json`: `{analysis_id, period, normal_period, placeholder, rows:[{mandal, district, water_pct, water_err, crops_pct, crops_err, normal_pct, rank}]}`. `mandal` is the geoBoundaries name; rows are sorted by `water_pct + crops_pct` descending and `rank` runs 1..N. A bare v1 array is also accepted by the page.
- `profile.json`: `{eye:[lat,lon], eye_radius_km, eye_radius_err, imd_offset_km, layer_id, points:[{r_km, db, err}], placeholder}`.
- `alerts.json`: `{saved_at_ist, sachet:[{headline, area, issued}], gdacs:[], placeholder}`; the strip always prints `saved_at_ist`.

## How to add content (edit manifest.json only)

**A layer.** Put the PNG at `data/processed/img/<id>.png`. Append an object to `layers[]` with all v1 fields plus `type`, `kind`, `source_id`, `regions`, `status`, `bounds` (images) and `placeholder` if it is a sample. Pick a `latest_of` key shared with the series it belongs to. For a layer inside an event, also add its id to that event's `layers.before|during|after`. Run the checker.

**A region.** Append to `regions[]` with `id`, `name`, `bounds`, `districts` (names as in the `district` property of `mandals.geojson`, or null) and `parent`; add its id to the parent's `children`. Add the id to the `regions` list of every layer that should appear there.

**An event.** Append to `events[]`: `id`, `name`, `hazard`, `region`, `dates`, the three `layers` lists, `default_on` (NISAR first), `analysis_id` (add a matching `analyses[]` entry and a rank file, or set it to null for no ranking), `landfall` (time null if unconfirmed), and optionally `track_geojson` plus a reference layer with `event_id` set to the new id. Set `gdacs_id` when GDACS has one.

**A hazard.** Replace its entry in `coming_next[]` by real layers and an event with a new `hazard` string; the Events tab lists by event, not by hazard.

**A source.** Append to `sources[]` and reference it with `source_id`. Unknown credit: write `[credit line to confirm]`, set `credit_confirmed:false` and add a row to `docs/PLACEHOLDERS.md`.

## Notes on what the code decides

- **Marine URL.** The Open-Meteo marine request URL is built in `app/js/live.js`. The `url_template` of the marine layer is ignored for it.
- **Case study.** The Case study tab uses the first event with `case_study: true`. It finds its layers by id prefix: `nisar_l_sea_` and `nisar_l_coast_`.
- **Class swatch colours.** Only the classes `new_water` and `wet_crops` have their own swatch colour. Any other class gets the teal default.
