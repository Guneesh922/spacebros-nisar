# Adding content without a developer

This page is for the backend person. You add content by editing one file, `data/processed/manifest.json`, plus dropping the files it points to. You do not change any code.

Every example below uses a real id and value that already exists in the manifest. Copy the shape, then change the values.

Read this first:

- **Back up before you edit.** Copy `data/processed/manifest.json` to a safe place.
- **Keep the JSON valid.** Every object needs a comma between it and the next one. No comma after the last one. Use a plain-text editor, or a JSON-aware editor such as VS Code.
- **Run the checks after every change.** See section (j).
- **Some fields are read by the page, some are not.** Each table says which is which. A field marked *informational* is saved for people, the checker or later work. Changing it does not change the page.
- **Some changes need a developer.** Section 11 lists them. If you hit one, stop and ask.

Related files: `docs/MANIFEST_SCHEMA.md` (field reference), `docs/PLACEHOLDERS.md` (every sample value and its real replacement).

---

## Where things live

| What | Where |
|---|---|
| Everything the page shows (regions, sources, layers, events, analyses, coming next) | `data/processed/manifest.json` |
| Map images (PNG or JPG) | `data/processed/img/` |
| Mandal outlines (one file, with district names) | `data/processed/mandals.geojson` |
| Ranking table (one file per analysis) | `data/processed/mandal_rank.json` (path set in `analyses[].rank_file`) |
| Case study numbers | `data/processed/profile.json` |
| Official alert strip | `data/processed/alerts.json` |
| IMD cyclone track (drawn on the map) | `data/processed/imd_track_arnab.geojson` |

---

## (a) Add a layer

A layer is one thing the map can show: one radar scene, one class map, one satellite image, one live feed.

### a1. Example: a radar image layer (real values)

This is the real 9 Nov coast scene. Paste a new layer in the same shape, then change the values.

```json
{
  "id": "nisar_l_coast_20261109_t55_hh",
  "group": "after",
  "type": "nisar",
  "chip": "nisar",
  "name": "Coast, 12 days after",
  "kind": "image",
  "date": "2026-11-09",
  "time_utc": "2026-11-09T00:01:07Z",
  "latest_of": "nisar_l_coast_hh",
  "shows": "Land backscatter: radar brightness, HH (γ⁰, dB)",
  "limit": "ground truth (single date, none yet)",
  "source": "T55 F10 · NASA/ISRO via ASF",
  "source_id": "asf_nisar_l",
  "credit": "NASA/JPL-Caltech and ISRO via ASF DAAC",
  "png": "data/processed/img/nisar_l_coast_20261109_t55_hh.png",
  "bounds": [[15.289417736208744, 80.53360154529867], [18.337444233134367, 83.76801815174849]],
  "bounds_inferred": false,
  "url_template": null,
  "band": "L",
  "pol": "HH",
  "track": 55,
  "frame": 10,
  "direction": "ascending",
  "regions": ["ap_coast", "konaseema", "west_godavari", "kakinada"],
  "event_id": null,
  "classes": null,
  "default_on": true,
  "opacity": 0.85,
  "status": "ready",
  "placeholder": {
    "is": true,
    "tag": "Quick-look sample",
    "replaced_by": "data/processed/img/nisar_l_coast_20261109_t55_hh.png (same path, real greyscale dB product from the GCOV GeoTIFF)"
  },
  "processing_level": "validated",
  "bounds_source": "KML LatLonQuad of the browse image"
}
```

### a2. What each field does

"Page reads it: yes" means the page uses the value. "Informational" means it is saved but not used by the page.

| Field | What it means | Page reads it? |
|---|---|---|
| `id` | Unique name. NISAR ids follow `nisar_l_<sea or coast>_<YYYYMMDD>_t<track>_<pol>`. | yes |
| `group` | `before`, `during`, `after` or `next`. Puts the layer under that heading when an event is open. The Compare default uses `before`. | yes |
| `type` | `nisar`, `derived`, `optical`, `weather`, `reference` or `alerts`. Sets the drawer section. Keep NISAR layers first in the file. | yes |
| `chip` | `nisar`, `context`, `model` or `reference`. The small label on the caption. NISAR and derived layers use `nisar`. | yes |
| `name` | Short name in the drawer. | yes |
| `kind` | `image` (PNG overlay), `wmts` (satellite tiles), `geojson` (vector file), `live` (fetched JSON), `link` (link only). | yes |
| `date` | ISO date `2026-11-09`, or `live`, or a year such as `2018`, or `null`. Used for "latest" and for the age text. | yes |
| `time_utc` | Exact pass time in UTC, ending in `Z`. Required for NISAR images (the checker enforces it). Shown in the caption. | yes |
| `latest_of` | Series key. Layers with the same key form one time series. The newest `date` is "latest". Also feeds the header date list. | yes |
| `shows` | Caption line "Shows". | yes |
| `limit` | Caption line "Can't show". One plain line. | yes |
| `source` | Short source label in the caption and the drawer. | yes |
| `source_id` | Must match an `id` in `sources[]`. | yes |
| `credit` | Credit line in the caption. If empty, the source's `credit_line` is used. | yes |
| `png` | Image path under `data/processed/img/`. `null` for non-image layers. | yes |
| `bounds` | `[[S, W], [N, E]]`: south-west corner, then north-east corner, as latitude, longitude. Covers the whole image. See a4. | yes |
| `bounds_inferred` | `true` when the box was copied from another pass because no KML exists. The caption then shows a note. | yes |
| `url_template` | Address for `wmts` and `live` layers. `null` for images. See (g). | yes |
| `band` | `L` or `S`. The S option is only enabled when some layer has `S`. | yes |
| `pol`, `track`, `frame` | Radar polarisation and orbit. Shown in the caption. Never use track 156 (it does not cover the delta). | yes |
| `direction` | `ascending` or `descending`. | informational |
| `regions` | Region ids where the layer is offered. A child region also gets its parent's layers. | yes |
| `event_id` | `null`, or an event id. If set, the layer only appears while that event is open. | yes |
| `classes` | Class layers only. A list, see (f). `null` otherwise. | yes (id, label, style) |
| `class_group` | Class layers only. Layers with the same value share one legend. | yes |
| `default_on` | `true` if the layer is on when the page opens. | yes |
| `opacity` | 0 to 1. Starting opacity. `null` for non-image layers. | yes |
| `status` | `ready`, `coming_next`, `link_only` or `unavailable`. Any other value counts as `unavailable`. | yes |
| `placeholder` | `null`, or `{"is": true, "tag": "...", "replaced_by": "..."}`. When `is` is true the page shows the tag. | yes |
| `file` | Path to a vector file (`geojson` layers). | yes |
| `link_url` | Address for a `link` layer. | yes |
| `latest_available_lag_days`, `time_step`, `time_format`, `config` | Settings for `wmts` and `live` layers. See (g). | yes (some keys) |
| `period`, `normal_period` | On class layers. The page uses the analysis's periods instead. | informational |
| `processing_level` | `provisional` or `validated`. The page does not print it yet. | informational |
| `bounds_source` | A note on where the bounds came from. | informational |

### a3. Where to drop the PNG

- Put the file in `data/processed/img/`. Use the same name as the `png` field.
- Size: **600 KB or less** per file. `bash tools/audit_page.sh` fails any file over that.
- Radar images: **greyscale** (no colour). The real replacement should be a greyscale dB product, as `docs/PLACEHOLDERS.md` section 1 says.
- Do not ship the magenta or green colour composites from NISAR's quick-look browse images. Convert them to greyscale first.

### a4. How bounds come from a NISAR browse KML

Each NISAR browse image has a KML file next to it, in `data/browse/nisar_arnab/`. Inside it is a `<LatLonQuad>` with four corners:

```xml
<ns0:LatLonQuad>
  <coordinates>80.53360154529867,15.289417736208744 83.76801815174849,15.289417736208744 83.76801815174849,18.337444233134367 80.53360154529867,18.337444233134367</coordinates>
</ns0:LatLonQuad>
```

Each pair is `longitude,latitude`. The manifest wants latitude first. Take the smallest and largest values:

1. Latitudes: 15.289417736208744 (smallest) and 18.337444233134367 (largest).
2. Longitudes: 80.53360154529867 (smallest) and 83.76801815174849 (largest).
3. Write them as `[[S, W], [N, E]]`: `[[15.289417736208744, 80.53360154529867], [18.337444233134367, 83.76801815174849]]`.

That is exactly the bounds used by the 28 Oct coast layer.

If the KML is missing (the Earthdata link returns HTTP 401, which means a login is needed), copy the bounds from the same track and frame in a later pass. Set `bounds_inferred` to `true`. Add the row to `docs/PLACEHOLDERS.md` section 2.

### a5. Check it

Run the checks (section j). Then open the page and turn the layer on from the drawer.

---

## (b) Replace a placeholder with a real file

A placeholder is a sample value. The page shows a grey tag ("Sample values", "Quick-look sample") until it is replaced.

Steps:

1. Put the real file at the path in `replaced_by` (or the `png` field). Keep the same file name, or update `png` to match.
2. In `manifest.json`, find that layer (or analysis, or companion file). Set its `placeholder` to `null`. (Setting `"is": false` also hides the tag.)
3. If the bounds are now real, set `bounds_inferred` to `false` and fix `bounds`.
4. If the layer was `unavailable`, set `status` to `ready`.
5. Update the matching row in `docs/PLACEHOLDERS.md`. Move it to "done", or delete it. (This is a manual step. The script does not do it.)
6. Run the checks.

**Warning for NISAR layers (`type` is `nisar`).** The checker requires NISAR layers to keep `placeholder.is` set to `true` (`tools/check_manifest.py`, around line 323). If you set it to `false` or `null` on a NISAR layer, the checker fails. Until a developer changes that rule, do not switch off a NISAR placeholder. Ask the developer first. You can still replace the PNG file itself, and it will show up on the page.

For **derived** layers (`type` is `derived`, the class maps and the sea difference map), `null` works. For **companion JSON files**, set the top-level `placeholder` to `null` (in `mandal_rank.json`, `profile.json` or `alerts.json`). For analyses, set `analyses[].placeholder` to `null`.

---

## (c) Add a new date to an existing series

Use this for a new scene in a series such as `nisar_l_coast_hh`.

1. Put the PNG in `data/processed/img/`.
2. Copy an existing layer from the same series (same `latest_of`). Change `id`, `date`, `time_utc`, `png`, `bounds`, `bounds_inferred`, `name` and `placeholder`.
3. Put the new object **at the end of the NISAR block** in `layers[]`. That is right after the last NISAR layer, before the first `derived` layer. The checker fails if a NISAR layer comes after a non-NISAR one. (Right now the last NISAR entry is the 3 Oct sea scene.)
4. Keep `latest_of` the same as the rest of the series. The page sorts by `date`, so "latest" is the newest date, whatever the array order.
5. The header date list picks up the new date automatically.
6. If the new scene should appear on the landing view by default, see the warning below.
7. If it belongs to an event, add its id to that event's `layers.before`, `layers.during` or `layers.after` (see e).

**Warning: the landing view.** The checker expects exactly two layers to be `default_on` on the landing view: `nisar_l_coast_20261109_t55_hh` and `mandal_boundaries` (`tools/check_manifest.py`, around line 280). If you make a newer coast scene the landing default, the checker fails until a developer changes that expected id. Ask first. Do not leave two coast scenes on by default.

---

## (d) Add a region

A region is an area the picker can zoom to. Regions can nest.

Example: the real Konaseema region.

```json
{
  "id": "konaseema",
  "name": "Konaseema",
  "parent": "ap_coast",
  "bounds": [[16.2, 81.6], [17.1, 82.6]],
  "bounds_source": "data/sources.yaml boxes.delta",
  "districts": ["Dr. B.R. Ambedkar Konaseema"]
}
```

| Field | What it means | Page reads it? |
|---|---|---|
| `id` | Unique. Lower case, underscores. | yes |
| `name` | Name in the picker. | yes |
| `default` | `true` on exactly one region (the landing view). Leave it off other regions. | yes |
| `bounds` | `[[S, W], [N, E]]`. The map zooms here. | yes |
| `districts` | `null` for "all", or a list of district names. The names must match the `district` property in `data/processed/mandals.geojson` exactly, including full stops. The page filters mandal outlines and ranking rows on this list. | yes |
| `parent` | The id of the region this one sits under. | yes |
| `children` | On the parent: the list of child ids. The picker nests children under their parent. | yes |
| `bounds_source` | A note on where the box came from. | informational |

Steps:

1. Add the object to `regions[]`.
2. If it has a parent, add its id to the parent's `children`.
3. Add the new id to the `regions` list of each layer that should show there. A child region already gets its parent's layers, so you only need to add it where a layer is specific.
4. Run the checks.

**Known data issue.** In `mandals.geojson`, 81 of the 146 mandal outlines have no `district` value. Those mandals are left out of any region that lists districts, and out of its ranking. Fix the file (or ask the backend) before relying on a district-based region for the full set.

**Note on the docs.** `docs/MANIFEST_SCHEMA.md` says the district names come from `data/reference/mandal_district_2022.csv`. The page does not read that CSV. It reads the `district` property in `mandals.geojson`. Use the names in `mandals.geojson`.

---

## (e) Add an event

An event is a saved episode, such as a cyclone. Opening an event sets the region, the dates, which layers are on, and the ranking.

Example: the real Cyclone Arnab event.

```json
{
  "id": "arnab_2026",
  "name": "Cyclone Arnab",
  "hazard": "cyclone_flood",
  "gdacs_id": null,
  "region": "konaseema",
  "dates": {
    "before": "2026-10-16",
    "during": "2026-10-28",
    "after": "2026-11-09",
    "normal_period": ["2026-10-04", "2026-10-16"]
  },
  "layers": {
    "before": ["nisar_l_sea_20261003_t48_vv", "nisar_l_sea_20261015_t48_vv", "nisar_l_coast_20261004_t55_hh", "nisar_l_coast_20261016_t55_hh"],
    "during": ["nisar_l_sea_20261027_t48_vv", "nisar_l_coast_20261028_t55_hh", "nisar_sea_diff_20261027_vs_20261015", "gibs_viirs_truecolor", "gibs_himawari_b13", "gibs_imerg_daily", "imd_track_arnab", "open_meteo_marine"],
    "after": ["nisar_l_sea_20261108_t48_vv", "nisar_l_coast_20261109_t55_hh", "nisar_class_new_water", "nisar_class_wet_crops", "nisar_class_no_change", "mandal_boundaries", "open_meteo_flood"]
  },
  "default_on": ["nisar_l_sea_20261027_t48_vv", "nisar_l_coast_20261109_t55_hh", "mandal_boundaries", "imd_track_arnab"],
  "analysis_id": "ap_delta_oct_nov_2026",
  "track_geojson": "data/processed/imd_track_arnab.geojson",
  "landfall": {
    "lat": 16.45,
    "lon": 81.9,
    "time_utc": null,
    "note": "time being confirmed (IMD)"
  },
  "case_study": true,
  "summary": "One saved event: eye pass 27 Oct (Track 48), delta before/after pair on Track 55 (16 Oct, 28 Oct, 9 Nov) against a normal period of 4-16 Oct."
}
```

| Field | What it means | Page reads it? |
|---|---|---|
| `id`, `name` | Identity. `name` is shown in the event list and banner. | yes |
| `hazard` | Label key. The page shows it as a short label (see section h). | yes |
| `gdacs_id` | GDACS id, or `null` for a saved event with no GDACS entry. | informational |
| `region` | The region the map flies to. | yes |
| `dates.before`, `dates.during`, `dates.after` | ISO dates. Used for the date line and for the event range. | yes |
| `dates.normal_period` | `[from, to]` of the normal period used for comparison. | yes |
| `layers.before`, `layers.during`, `layers.after` | Layer ids under each heading in the drawer while the event is open. Every id must exist in `layers[]`. The Case study also reads these lists. | yes |
| `default_on` | Layer ids that are on when the event opens. The **first must be a NISAR layer**. Every id must also appear in one of the three `layers` lists. | yes |
| `analysis_id` | The analysis the ranking card reads. `null` for no ranking. | yes |
| `track_geojson` | The track file. The Case study reads it. The map draws the track from its reference layer (`file`). | yes (Case study only) |
| `landfall.lat`, `landfall.lon` | Position of the landfall marker. | yes |
| `landfall.time_utc` | Exact landfall time, or `null`. **Keep it `null` until a person confirms it.** The page then shows "time being confirmed". | yes |
| `landfall.note` | A note for the team. | informational |
| `case_study` | `true` adds this event to the Case study tab. **Only the first event with `true` is used.** | yes |
| `summary` | A plain summary for people reading the file. | informational |

Steps:

1. Add the event to `events[]`.
2. Add the event's layers to `layers[]`. Each reference layer that belongs only to this event gets `event_id` set to the event's id. For example the IMD track layer has `"event_id": "arnab_2026"`.
3. Make sure every id in the three `layers` lists exists in `layers[]`.
4. Set `default_on` with a NISAR layer first.
5. If it has a ranking, add an analysis (section f). Otherwise set `analysis_id` to `null`.
6. Keep `landfall.time_utc` as `null` unless a person has confirmed the time.
7. Run the checks.

**Note on the Case study tab.** It finds its layers by id pattern. Sea scenes must start with `nisar_l_sea_`, and coast scenes with `nisar_l_coast_`. A new event that follows those names works. Other names will leave gaps in the Case study. The tab also reads one fixed set of satellite images. A developer should check it before a second Case study goes in.

---

## (f) Add an analysis with a ranking and class layers

An analysis is a before-and-after comparison for a region and a period. It has a ranking table and optional class maps.

### f1. The analysis entry

```json
{
  "id": "ap_delta_oct_nov_2026",
  "region": "ap_coast",
  "period": ["2026-10-16", "2026-11-09"],
  "normal_period": ["2026-10-04", "2026-10-16"],
  "rank_file": "data/processed/mandal_rank.json",
  "class_layers": ["nisar_class_new_water", "nisar_class_wet_crops", "nisar_class_no_change"],
  "placeholder": {
    "is": true,
    "tag": "Sample values",
    "replaced_by": "data/processed/mandal_rank.json (real zonal stats from the NISAR change analysis)"
  }
}
```

| Field | What it means | Page reads it? |
|---|---|---|
| `id` | Unique. An event points here with `analysis_id`. | yes |
| `region` | The region the analysis covers. The page uses it to pick an analysis when no event is open. | yes |
| `period`, `normal_period` | `[from, to]` ISO dates. Shown as the ranking subtitle. | yes |
| `rank_file` | Path to the ranking file. | yes |
| `class_layers` | Class layer ids that belong to this analysis. | yes |
| `placeholder` | Sample flag. Set to `null` when the numbers are real. | yes |

### f2. The ranking file: `mandal_rank.json`

```json
{
  "analysis_id": "ap_delta_oct_nov_2026",
  "period": ["2026-10-16", "2026-11-09"],
  "normal_period": ["2026-10-04", "2026-10-16"],
  "placeholder": {"is": true, "tag": "Sample values", "replaced_by": "data/processed/mandal_rank.json (real zonal stats)"},
  "rows": [
    {"mandal": "Narasapuram", "district": "West Godavari", "water_pct": 12.0, "water_err": 2.4, "crops_pct": 19.0, "crops_err": 3.2, "normal_pct": 5.0, "rank": 1}
  ]
}
```

| Field | What it means | Page reads it? |
|---|---|---|
| `analysis_id` | Must match an analysis. The checker requires it. | informational |
| `period`, `normal_period` | Used only if the analysis has none. | yes (fallback) |
| `placeholder` | Sample flag. | yes |
| `rows[].mandal` | The mandal name. **Must match the `name` property in `mandals.geojson` exactly.** Clicking a row highlights that outline. | yes |
| `rows[].district` | The district name, as in `mandals.geojson`. Used for district-based regions. | yes |
| `rows[].water_pct`, `water_err` | Share of the mandal that is likely open water now, in percent, and its error. | yes |
| `rows[].crops_pct`, `crops_err` | Share of the mandal that is likely wet or flooded crops, in percent, and its error. | yes |
| `rows[].normal_pct` | The same share in the normal period, in percent. Drawn as a tick. | yes |
| `rows[].rank` | 1 to N. The page renumbers after a district filter. | yes |

Rules the checker enforces:

- Rows are sorted by `water_pct + crops_pct`, highest first.
- `rank` runs 1, 2, 3 ... N in row order.
- Mandal names are not repeated.

The page always shows the note "Not a warning. Not a flooded area in km²." next to these numbers. Keep the numbers as percentages.

### f3. Class layers

A class layer is one class map (for example "likely new open water") as one manifest layer. Each class is its own layer.

```json
{
  "id": "nisar_class_new_water",
  "group": "after",
  "type": "derived",
  "chip": "nisar",
  "name": "Likely new open water",
  "kind": "image",
  "date": "2026-11-09",
  "time_utc": null,
  "latest_of": "nisar_class_new_water",
  "shows": "Where open water likely appeared between the before and after scenes",
  "limit": "water under dense crops (it can be missed)",
  "source": "SpaceBros change map",
  "source_id": "spacebros_derived",
  "credit": "SpaceBros, from NISAR data",
  "png": "data/processed/img/class_20261109_new_water.png",
  "bounds": [[15.289417736208744, 80.53360154529867], [18.337444233134367, 83.76801815174849]],
  "bounds_inferred": true,
  "band": "L", "pol": "HH", "track": 55, "frame": 10, "direction": "ascending",
  "regions": ["ap_coast", "konaseema", "west_godavari", "kakinada"],
  "event_id": null,
  "classes": [
    {"id": "new_water", "label": "likely new open water", "colour": "#2A6FB0", "style": "fill", "default_on": true}
  ],
  "class_group": "ap_delta_oct_nov_2026",
  "default_on": false,
  "opacity": 0.75,
  "status": "unavailable",
  "placeholder": {"is": true, "tag": "Sample values", "replaced_by": "data/processed/img/class_20261109_new_water.png (real class map from the NISAR change analysis)"}
}
```

Rules:

- `classes[].label` must start with `likely`. The checker enforces it. The page adds "likely" itself when it is missing.
- `classes[].style` is `fill` (solid colour, needs `colour` as `#RRGGBB`) or `outline` (`colour` may be `null`).
- `classes[].id` is used by the legend. The page knows the swatch colour for two ids only: `new_water` and `wet_crops` (`app/js/compare.js`, the `CLASS_TOKEN` line). A **new class id gets a default teal swatch**. The map itself shows the colours baked into the PNG. So set the colours in the PNG, and ask a developer to add a swatch for a new id.
- `classes[].colour` and `classes[].default_on` are saved for reference. The page does not read them. Whether a class is on follows the layer's own `default_on`.
- Every class layer in one analysis should share the same `class_group`. That is how the page builds one legend.
- Class layers are one per class. Do not put several classes in one PNG.
- Keep the layer's `status` as `unavailable` and `placeholder` set until the PNG exists. Then set `status` to `ready` and `placeholder` to `null` (section b).

---

## (g) Add a live layer

There are two kinds: satellite tiles (`wmts`) and a fetched number (`live`).

### g1. A satellite tile layer (`wmts`), real example

```json
{
  "id": "gibs_imerg_daily",
  "group": "during",
  "type": "optical",
  "chip": "context",
  "name": "Rain (IMERG, daily)",
  "kind": "wmts",
  "date": "live",
  "time_utc": null,
  "latest_of": null,
  "shows": "Satellite rain estimate, daily mean rate (mm/h)",
  "limit": "rain under a day's average (a daily mean, not a storm total)",
  "source": "NASA GIBS · IMERG",
  "source_id": "nasa_gibs",
  "credit": "NASA GIBS · IMERG",
  "png": null,
  "bounds": null,
  "bounds_inferred": false,
  "url_template": "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/IMERG_Precipitation_Rate/default/{time}/GoogleMapsCompatible_Level6/{z}/{y}/{x}.png",
  "regions": ["ap_coast", "konaseema", "west_godavari", "kakinada"],
  "event_id": null,
  "default_on": false,
  "opacity": 0.7,
  "status": "ready",
  "placeholder": null,
  "id": "gibs_imerg_daily",
  "name": "Rain (IMERG, daily)",
  "latest_available_lag_days": 2,
  "time_step": "P1D",
  "time_format": "YYYY-MM-DD",
  "config": {
    "max_native_zoom": 6
  }
}
```

Notes:

- `url_template` must contain `{time}` and `{z}`. The page fills `{time}` with a date, then tries the newest day that is likely to exist. `latest_available_lag_days` says how many days behind today that is. If the tile is not there, the page tries older days. The candidate logic is in `app/js/live.js` (`candidates`).
- `time_step` `PT10M` (every 10 minutes) or `time_format` with a `T` in it means sub-daily. Anything else is treated as daily.
- `config.max_native_zoom` is the highest zoom the source has. The page uses 6 if it is missing.
- Keep `default_on` as `false`. The checker requires live optical layers to start off.
- If the source fails, the page shows "unavailable" and the last time it worked. It does not crash.
- The other keys in `config` (`layer`, `tile_matrix_set`, `format`, `known_range_end`, `range_from`, `rolling_window`, `alt_layers`) are for people. The page does not read them.

### g2. An Open-Meteo readout (`live`)

The page reads these two Open-Meteo layers: `open_meteo_marine` (waves) and `open_meteo_flood` (river flow). Use the real examples in the manifest, and change only the point:

```json
{
  "config": {
    "lat": 16.0,
    "lon": 82.0,
    "coordinates_confirmed": false,
    "coordinates_note": "sea point to be confirmed by the backend person",
    "readout": "card",
    "timeout_ms": 8000
  }
}
```

- `lat` and `lon` are read. Change them to move the point.
- `coordinates_confirmed: false` shows the note "coordinates to be confirmed" on the card. Set it to `true` when the point is checked.
- `timeout_ms` is how long the page waits before it shows "unavailable".
- The marine readout uses a fixed address in the code. Its `url_template` is not used. The flood readout does use `url_template`.
- A third Open-Meteo layer needs a developer. The page only builds a readout when all of these are true: `lat` and `lon` are set, the source or `url_template` mentions Open-Meteo, and the `id` or `url_template` mentions `marine` or `flood`.

Open-Meteo layers are `kind` `live`, `chip` `model`, `type` `weather`, and `default_on` `false`.

### g3. Other live feeds

GDACS (`alerts_gdacs_live`) is a `live` layer too, but its readout is in the alerts strip. Adding a new feed of that kind needs a developer.

---

## (h) Add a coming-next hazard, or make one real

The grey "Coming next" list in the drawer reads `coming_next[]`:

```json
{
  "coming_next": [
    {"id": "quake", "name": "Earthquake and landslide"},
    {"id": "oil", "name": "Oil spill"},
    {"id": "fire", "name": "Wildfire"}
  ]
}
```

To make a hazard real:

1. Add its layers to `layers[]` (sections a and g).
2. Add an event with the new `hazard` text (section e).
3. Remove its entry from `coming_next[]`.
4. **Keep at least three entries in `coming_next`.** The checker fails with fewer. If you remove one, add another, or ask a developer to change the rule.

The Events tab lists events, not hazards. The `hazard` text is the label. The page turns `earthquake_landslide` into "Earthquake landslide" with no code change. If you want a nicer label, a developer adds a line to the events text in `app/js/events.js` (the `events.hazard_` keys).

---

## (i) Update the official alerts (`alerts.json`)

Real example:

```json
{
  "saved_at_ist": "2026-10-27T17:30:00+05:30",
  "placeholder": {"is": true, "tag": "Sample values", "replaced_by": "data/processed/alerts.json (real SACHET snapshot)"},
  "sachet": [
    {"headline": "[Sample headline: official alert text from the saved SACHET feed]", "area": "Coastal Andhra Pradesh", "issued": "2026-10-27T16:45:00+05:30"}
  ],
  "gdacs": []
}
```

- `saved_at_ist` is **shown on screen** in the alerts strip as "snapshot 27 Oct, 17:30 IST". Use the time the snapshot was saved, with `+05:30` at the end.
- The strip shows the **first** item in `sachet` only, using its `headline`. Put the most important alert first.
- `area` and `issued` are saved for people. The page does not read them.
- `gdacs` must exist, even if it is empty. The live GDACS list comes from the browser, not from this file.
- `placeholder`: set to `null` once the headlines are real (section b).

---

## (j) Checklist before you tell anyone a change is ready

Run these in order from the repo root.

1. **Check the manifest:**
   ```
   python3 tools/check_manifest.py --files
   ```
   It must end with `PASS`. The `--files` list shows files the manifest points to that are not on disk yet. Missing files are fine for `unavailable` layers.

2. **Run the page audit:**
   ```
   bash tools/audit_page.sh
   ```
   It must end with `RESULT: PASS`. Any `FAIL` line says what is wrong and where. Warnings are for a person to read, but they do not stop the audit.

3. **Look at the page.** Start a local server from the repo root:
   ```
   python3 -m http.server 8000
   ```
   Then open <http://localhost:8000/app/>. Check it at two widths in your browser's responsive mode:
   - **Wide (1440 px):** the map fills the screen. The drawer lists NISAR layers first. Your new layer appears in the drawer, and turns on and off.
   - **Narrow (390 px):** there is no sideways scrolling. The drawer opens as a sheet from the bottom. Buttons are easy to tap.

4. **Check the captions.** Each layer you changed should show what it shows, what it cannot show, its source and its credit line. Any sample should show its grey tag.

5. **Check the console.** Open the browser's developer tools. There should be no red errors. A warning that a CDN or font did not load is expected when you are offline.

6. **Commit only when the owner asks.** Do not push to the public site until the owner says so.

If a check fails and the fix is not clear, send the `FAIL` line and the file name to the developer. Do not edit the script to make it pass.

---

## 11. Things that still need a developer

These are limits in the code, not in the data. Ask before you work around them.

| # | Limit | Where | What it blocks |
|---|---|---|---|
| 1 | The checker requires NISAR placeholders to stay on. | `tools/check_manifest.py` (about line 323) | Turning off a NISAR placeholder (section b). |
| 2 | The checker expects two landing defaults: the 9 Nov coast scene and mandal boundaries. | `tools/check_manifest.py` (about line 280) | A newer coast scene as the landing default (section c). |
| 3 | The checker requires at least three `coming_next` entries. | `tools/check_manifest.py` (about line 391) | Removing a hazard without adding another (section h). |
| 4 | Class swatch colours are known for two class ids only. | `app/js/compare.js` (`CLASS_TOKEN`) | A new class id shows a teal swatch (section f3). |
| 5 | The marine readout uses a fixed address. | `app/js/live.js` (`omUrl`) | A new marine point needs only `config.lat` and `config.lon`. A new kind of Open-Meteo layer needs code. |
| 6 | The Case study uses only the first event with `case_study: true`, and finds layers by id prefix. | `app/js/case.js` (`pickLayers`) | A second Case study, or other id names (section e). |
| 7 | 81 of 146 mandal outlines have no `district`. | `data/processed/mandals.geojson` | District-based regions and rankings are incomplete. |
| 8 | The schema doc says districts come from a CSV. The page reads `mandals.geojson`. | `docs/MANIFEST_SCHEMA.md` | Follow the file the page reads (section d). |

