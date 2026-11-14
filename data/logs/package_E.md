# Package E log - 2026-11-14
Agent: data-fetch (Package E). Log file also copied to E_context.md.

## Files written
- src/fetch/E_era5.py  2648 bytes  sha256 9adcba052162ed66f5980ca935aa67a9cc42723bd97ab6c0b4c012e67de1936f
- src/fetch/E_mandal_names.py  865 bytes  sha256 6a2bc6dab408daebf0ed80c6798328603e0e5788553fbd2d13b0e085b7c47080
- src/fetch/E_districts.py  2509 bytes  sha256 f7fcf16d61b84421c5148c73c4d678020de66621b74f38cfd2397575adb035e1
- data/reference/era5_wind_summary.csv  5196 bytes  sha256 f4c2cd79dedf8d0dc754bf82d0d2a981ffb6024e7050e67f6de9459564c3eef6
- data/reference/era5_grid_points.csv  699 bytes  sha256 5db366825de066c205cafeae0214b0a6bdd55adc5563c143882d8b53b74fd64e
- data/reference/mandal_district_2022.csv  6063 bytes  sha256 6a8a5ae18757bfbf4c65a306a7522e464b3d2fe7d97764c81070badecd478e6c
- docs/SUBMISSION_GUIDE_NOTES.md  4675 bytes  sha256 f12e0322125bfeda4b1455cdceb28860da1b79bf3824daed36fcaf6532bdc4da
- docs/CROP_CALENDAR_NOTES.md  3368 bytes  sha256 3c1a9a20affb903148d1e021c8118c649e76c8ce314e041ee15f6ae2459c899c
- data/raw/districts2022/wiki_Dr._B._R._Ambedkar_Konaseema_district.wikitext  79 bytes  sha256 6e69b61851084dfe4961b8c82519f26228911a8ae7ef09509e7f3c3e21f64983
- data/raw/districts2022/wiki_East_Godavari_district.wikitext  49356 bytes  sha256 1973c131e70a2f80bd491890b24b1ff4aec00233adfd0e60f9e0d6ebe9770ab3
- data/raw/districts2022/wiki_Eluru_district.wikitext  21589 bytes  sha256 745a0d2c4ffa524adc3c710ea262db8cca471c6485a9783b72bc99ed45935546
- data/raw/districts2022/wiki_Kakinada_district.wikitext  14214 bytes  sha256 cba934e3d2877af4b606ae0fe3a986de59f33a99627d62fa5e5e36ba1880e8d8
- data/raw/districts2022/wiki_Konaseema_district.wikitext  28446 bytes  sha256 4c98180656df1f87bac160ae9dd82532736a4843b44016b40042e81cfe55c43d
- data/raw/districts2022/wiki_West_Godavari_district.wikitext  30917 bytes  sha256 e1d0c88933a57017da7d044f717fa96764b16d12bb8ada7cd94c60b9971abb73
- data/raw/era5/openmeteo_era5_<date>_<lat>_<lon>.json : 50 raw files (25 points x 2 dates), sha256 list: data/raw/era5/SHA256SUMS
- data/raw/districts2022/wiki_Konaseema.wikitext and wiki_Dr._B._R._Ambedkar_Konaseema_district.wikitext: 79-byte redirect stubs from a wrong first title; cannot be deleted on this mount (ignore; real file is wiki_Konaseema_district.wikitext).

## ERA5 (ERA5_WIND)
- URL pattern: https://archive-api.open-meteo.com/v1/archive?latitude=<lat>&longitude=<lon>&start_date=<d>&end_date=<d>&hourly=wind_speed_10m,wind_direction_10m&models=era5&wind_speed_unit=ms ; dates 2026-10-15 and 2026-10-27; lat 15.0,15.75,16.5,17.25,18.0; lon 81..85; fetched 2026-11-14; 0 failures (HTTP 200 for all 50).
- CSV: 150 rows (25 pts x 3 hours 12-14 UTC x 2 dates); every point has numbers.
- Land points flagged in data/reference/era5_grid_points.csv (elevation_m > 0): 7 of 25 -> (16.5,81.0) (16.5,82.0) (17.25,81.0) (17.25,82.0) (18.0,81.0) (18.0,82.0) (18.0,83.0). 18 points have elevation 0 (sea).
- 15 Oct 2026, 13 UTC, sea box: all 25 pts median 2.87 m/s, range 0.36-4.57; sea-only (18 pts) median 3.41 m/s, range 2.26-4.57.
- 27 Oct 2026, 13 UTC (reference, not a Arnab-intensity claim; ERA5 resolves storms poorly): all 25 median 13.32, range 3.81-18.62; sea-only median 14.52, range 7.33-18.62.
- Caveat: values for recent days may be ERA5T (preliminary, replaced after ~2-3 months). Open-Meteo does not label this per response; treat as preliminary. Open-Meteo grid cells may snap (e.g. 82.0 -> 81.75 lon at lat 16.5), see era5_grid_points.csv.
- Suggested caption: "Reference day 15 Oct 2026: sea-box wind ~3 m/s (ERA5 via Open-Meteo, preliminary)."

## Submission guide (DOCS_SUBMISSION)
- NOT retrievable: the 2026 Project Submission Guide text. project-submission-guide page returned no content to WebFetch; challenge page failed robots_disallowed. Fields/character limits/deadline time/video rules unknown. See docs/SUBMISSION_GUIDE_NOTES.md.
- Found: 2026 FAQ (https://www.spaceappschallenge.org/resources/participant-faqs/) "Teams are not allowed to begin working on the challenges prior to the hackathon." -> flagged to caller.

## Crop calendar (DOCS_CROP): done, 6 sources, see docs/CROP_CALENDAR_NOTES.md. Stage for 2026 is uncertain; sources disagree on damage numbers.

## Mandal -> 2022 district (DOCS_DISTRICTS)
- Package C had not produced mandals_delta_list.csv. I listed geoBoundaries ADM3 (data/raw/boundaries/geoBoundaries-IND-ADM3.geojson) features whose bounding box intersects the delta box 81.6,16.2,82.6,17.1 via src/fetch/E_mandal_names.py: 66 names (bbox test, so boundary-touching mandals included; package C's clip may differ -> re-run src/fetch/E_districts.py after its list exists, names taken from /tmp/E_names.txt).
- Mapping source: Wikipedia wikitext district pages (secondary; they cite the AP 2022 notification) saved in data/raw/districts2022/: https://en.wikipedia.org/wiki/Konaseema_district, Kakinada_district, East_Godavari_district, West_Godavari_district, Eluru_district. Retrieved 2026-11-14. Not verified against the AP gazette/official district sites (Kakinada list carries a "citation needed" tag on Wikipedia).
- Result: 65/66 filled: Konaseema 19, East Godavari 20, Kakinada 12, West Godavari 14, Eluru 0 (no delta-box mandals). Empty: "Yanam Taluk" (Yanam is a Puducherry UT enclave, not an AP district).
- Spelling bridges used (geoBoundaries->Wikipedia): Anaparthy/Anaparthi, Palacole/Palakollu, Palacoderu/Palakoderu, Nidadavole/Nidadavolu, Rajahmundry/Rajamahendravaram, Alamuru/Alumuru, Kakinada (Rural/Urban). Judgement call: geoBoundaries "Kothapalle" mapped to Kakinada's "U. Kothapalli" by name and bbox (82.23-82.40E, 17.02-17.16N, east of Kakinada) - please spot-check. Pre-2022 mandal geometry (2018) kept; note Ganapavaram moved Eluru->West Godavari on 16 Feb 2023 (not in box list).

## sources.yaml statuses set
ERA5_WIND: done; DOCS_SUBMISSION: partial (guide not retrievable); DOCS_CROP: done; DOCS_DISTRICTS: done (secondary source).
