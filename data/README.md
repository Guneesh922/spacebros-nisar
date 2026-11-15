# data/ layout

| Folder | What is in it | In git? |
|---|---|---|
| `h5/` | Data of record: 8 NISAR L-band GCOV study-box subsets (4 coast scenes, track 55; 4 sea scenes, track 48) and `catalog.json` (sizes, sha256, status). Schema: `../docs/DATA_STORAGE.md` | Yes |
| `processed/` | What the dashboard reads: `manifest.json`, findings per pass, events, alerts, mandal ranking, eye profile, mandal outlines | Yes |
| `reference/` | Small inputs: scene lists, IMD track, mandal and district outlines, coastline clips, licence metadata | Yes |
| `events/` | Event definition for Cyclone Arnab (fallback for `processed/events.json`) | Yes |
| `interim/C/` | District names for the mandals (2022 Andhra Pradesh district lists) | Yes |
| `web/` | Display PNG and JSON built from `h5/` by `tools/build_web.py` | No (build output) |
| `internal/` | Caveat text kept out of the product, written by `tools/build_story.py` | No (build output) |
| `raw/` | Full NISAR granules while they are being subset | No |

`sources.yaml` lists every source with its access route, licence and credit line. `seasons.json` and `story_rules.json` hold the rules for the plain-language findings.
IMD bulletin PDFs are in `../docs/imd_bulletins/`. Credentials go in `~/.netrc` or environment variables, never in this folder.
