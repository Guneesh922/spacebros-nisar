# Worker D: licences, credit lines and access paths

Researched Sat 14 Nov 2026 by web search and fetch only. No accounts created, no credentials used. Terms are paraphrased; not legal advice. "UNCONFIRMED" means the page did not state it or could not be read.

## Part 1. Licences and credit lines (public non-commercial hackathon page)

| Source | What the terms say (paraphrase) | Recommended credit line | Host derived images? | URL read |
|---|---|---|---|---|
| NISAR L-band (ASF DAAC) / NASA data policy | NASA-led mission data are CC0 unless marked otherwise; no endorsement implied; NASA asks that users cite datasets and acknowledge NASA. The NISAR docs defer to this NASA guidance. The NISAR release alert states no licence of its own. Per-dataset DOI/citation text: UNCONFIRMED (not read). | "Contains NISAR L-band data, NASA/JPL-Caltech and ISRO, distributed by ASF DAAC. Processed by SpaceBros." (current manifest line is fine; add the dataset DOI once read from the product's Earthdata entry) | Yes (CC0 default). Do not imply NASA endorsement. | https://www.earthdata.nasa.gov/learn/use-data/data-use-policy ; https://nisar-docs.asf.alaska.edu/data-use-citation-guidance/ ; https://www.earthdata.nasa.gov/data/alerts-outages/nisar-l-band-data-now-publicly-available |
| NDMA SACHET | UNCONFIRMED. No public terms or feed licence found. Alerts are government public-safety messages. | "Alert text: NDMA SACHET (sachet.ndma.gov.in), snapshot saved [date/time IST]" | UNCONFIRMED; a dated text snapshot with credit is low risk but ask NDMA if unsure. | none readable |
| MOSDAC (incl. INSAT-3DS) | Free for General users after registration. Products are "as is". No resale or redistribution of downloaded products; value-added products you create may be distributed freely. Browse images (JPG/GIF/PNG) need no login but IPs are logged. Cite DOI where one exists. | "Data Source MOSDAC/SAC/ISRO. https://mosdac.gov.in" (this is MOSDAC's stated line) | Original products: no. A derived/value-added map: yes per the guidelines. Plan keeps MOSDAC as a credited link only, which is safest. | https://www.mosdac.gov.in/look/DOCS/mosdac-data-guidelines_english.pdf |
| IMD bulletins and data | UNCONFIRMED for public bulletins (no reuse statement found). IMD's data-supply procedure (a different channel) says data are for the requester's own use, may not be passed on without IMD written approval, and IMD must be credited. | "Source: India Meteorological Department (IMD), RSMC New Delhi" | Bulletin text/PDF re-hosting: UNCONFIRMED. Safer: link out, quote short facts with credit. | https://mausam.imd.gov.in/shimla/docs/data-procedure.pdf |
| OpenStreetMap | ODbL 1.0; must credit OSM and contributors and make clear the data is ODbL. Derived databases must stay ODbL. | "© OpenStreetMap contributors" linked to https://www.openstreetmap.org/copyright (add "ODbL" in the About dialog) | Yes, as ODbL-licensed derivatives (e.g. clipped coast vectors), with the credit and licence stated. | https://www.openstreetmap.org/copyright |
| Esri World Dark Gray Base (Leaflet) | Esri terms require attribution to Esri and its data providers and forbid harvesting, redistributing or self-hosting tiles. Whether free no-key use on a non-commercial public page is permitted: UNCONFIRMED (the pages read did not say). Esri's current direction favours ArcGIS Location Platform with an API key, so the legacy open tile URL could be restricted. | Current line is reasonable: "Tiles © Esri — Esri, HERE, Garmin, © OpenStreetMap contributors" (verify against the tile service's own copyright text) | Never cache or re-host tiles. | https://www.esri.com/content/dam/arcgisonline/docs/tou_summary.pdf |
| GDACS | UNCONFIRMED. The Terms of Use page and PDF could not be read. Site disclaimer says content is "as is", automatic alerts are not human-reviewed and should not be used for decisions without official confirmation. Copyright link points to European Commission legal notice (reuse with acknowledgement, usually). | "Source: GDACS (Global Disaster Alert and Coordination System), EC JRC / UN OCHA" | Live use in browser: fine. Re-hosting snapshots: UNCONFIRMED. | https://gdacs.org/About/termofuse.aspx ; https://www.gdacs.org/documents/2025/GDACS_Terms_of_use_Mar_25.pdf (second one not read) |
| geoBoundaries | Site states CC BY 4.0 and requires acknowledgement; on a website show the name "geoBoundaries" prominently, linked to www.geoboundaries.org. NOTE: sources.yaml and PLACEHOLDERS say ODbL-1.0; the site says CC BY 4.0. Per-release licence metadata (ADM3 India) may differ: UNCONFIRMED, check the release's meta file. | "Boundaries: geoBoundaries (geoboundaries.org), CC BY 4.0, 2018 vintage" | Yes (clipped GeoJSON), with credit. | https://www.geoboundaries.org/index.html#usage |
| Open-Meteo (free tier) | API data CC BY 4.0. Free API is for non-commercial use, no key, under 10,000 calls/day (5,000/hour, 600/min). A link to open-meteo.com must appear next to displayed data. Upstream national data may carry own licences. | "Weather data by Open-Meteo.com" (link; CC BY 4.0) | Cached values yes with the credit. | https://open-meteo.com/en/licence ; https://open-meteo.com/en/terms |
| Copernicus Sentinel | Free, full and open licence: may reproduce, distribute, adapt, combine, with source notice. | "Copernicus Sentinel data 2026" or, if processed, "Contains modified Copernicus Sentinel data 2026" | Yes, with the notice. | https://ecds.ecmwf.int/licences/ec-sentinel |
| JRC Global Surface Water | Provided free with no restriction on use (Copernicus programme); outputs must acknowledge the dataset and cite Pekel et al. Nature 2016. For a map layer: "Source: EC JRC/Google". The JRC data page itself returned an error, so the licence on the JRC original is only confirmed via the Earth Engine catalogue. | "Source: EC JRC/Google. Pekel et al., Nature 540, 418-422 (2016)" | Yes, with the credit. | https://developers.google.com/earth-engine/datasets/catalog/JRC_GSW1_4_GlobalSurfaceWater |
| NASA GIBS | NASA supports open sharing; requests an acknowledgment. No key mentioned on the page read (works keyless in practice per project notes; not stated by this page). | "We acknowledge the use of imagery provided by services from NASA's Global Imagery Browse Services (GIBS), part of NASA's Earth Science Data and Information System (ESDIS)." | Yes (NASA open data), with the line. | https://www.earthdata.nasa.gov/engage/open-data-services-software/earthdata-developer-portal/gibs-api |
| NRSC / Bhoonidhi (NISAR S-band) | UNCONFIRMED. The ISRO and Bhoonidhi NISAR pages state no licence or citation text. Bhoonidhi FAQ says data is priced per ISRO Remote Sensing Data pricing policy; NISAR S-band price not stated. | Provisional: "NISAR S-band data: ISRO/NRSC (Bhoonidhi)" (UNCONFIRMED wording) | UNCONFIRMED. Ask bhoonidhi@nrsc.gov.in before publishing derived images. | https://bhoonidhi.nrsc.gov.in/NISAR/NisarProducts.html ; https://bhoonidhi.nrsc.gov.in/bhoonidhi/htmls/FAQ.html |

### Free no-key basemap alternatives

| Option | Policy (from pages read) | Attribution | Fit |
|---|---|---|---|
| OpenFreeMap (Dark style) | Free, no registration, no keys, no request limits on the public instance, commercial use allowed. Vector tiles, so needs MapLibre (plugin maplibre-gl-leaflet) rather than plain Leaflet raster. | "OpenFreeMap © OpenMapTiles Data from OpenStreetMap" | Best dark-style swap, but a code change in app/js/map.js. |
| OSM standard tiles (tile.openstreetmap.org) | Allowed for a small public site, best effort, no SLA. Needs visible attribution, a working Referer header, no bulk prefetching, honour cache headers. Light style only. | "© OpenStreetMap contributors" | Easy raster drop-in; light, not dark. Acceptable for a hackathon page. |
| NASA GIBS imagery base (e.g. Blue Marble / VIIRS true colour via WMTS) | Open; acknowledgment requested. Key requirement not stated on the page read. | GIBS line above | Fits the satellite theme, low detail at coast zoom. |
| CARTO basemaps | UNCONFIRMED here. BACKEND_GAPS item 11 says they now need a key; not re-checked. | n/a | Skip. |

## Part 2. Access paths for stretch items

### (a) Bhoonidhi, NISAR S-band

| Question | Finding |
|---|---|
| Register | Register on Bhoonidhi (https://bhoonidhi.nrsc.gov.in), log in, then browse and download. Exact form steps and approval time: UNCONFIRMED (not stated). If login fails after registering, FAQ says wait 15 minutes. Contact: bhoonidhi@nrsc.gov.in. |
| Products | S-band L1-RSLC, L2-GSLC, L2-GCOV, interferometric L1-RIFG, L1-RUNW, L2-GUNW, offsets L1-ROFF, L2-GOFF. Baseline v1.4.0. Typically available about 48 h after acquisition. 12-day repeat. |
| Catalogue without login | The Bhoonidhi FAQ says browsing the products catalogue needs no login; download needs registration. Whether the NISAR S-band holdings appear in that guest catalogue: UNCONFIRMED. Tools: Browse and Order, Vista (daily acquisitions over India), API, HDF-to-GeoTIFF tool. |
| Dates | ISRO release dated 24 Jul 2026. Operational processing from Cycle 25 (started 8 Jul 2026); earlier data being reprocessed in phases. 26 Oct and 27 Oct fall after Cycle 25, so processing should be operational. |
| Evidence of scenes over Godavari delta 16 Oct to 10 Nov | None found publicly. The ISRO release, the Bhoonidhi NISAR page and the Deccan Chronicle article do not mention Godavari, Andhra Pradesh events or Cyclone Arnab. The ROP Visualizer on the NISAR page may show planned S-band acquisitions: UNCONFIRMED, needs a human look (login state unknown). |

### (b) Oceansat-3 SCAT-3 winds

| Question | Finding |
|---|---|
| MOSDAC route | The MOSDAC Oceansat-3 mission page is linked but its product list was not readable; the pages I could fetch cover SCATSAT-1 and Oceansat-2 only. Oceansat-3 SCAT-3 product names and availability on MOSDAC: UNCONFIRMED. |
| Alternate route that is documented | EUMETSAT OSI SAF product OSI-113-a, Oceansat-3 25 km wind vectors. NetCDF4 and BUFR, operational since 31 Oct 2024, licence CC BY 4.0, credit EUMETSAT OSI SAF. Archive via EUMETSAT Data Centre, collection EO:EUM:DAT:0996 (DOI 10.15770/EUM_SAF_OSI_NRT_2027); whether it needs a login: UNCONFIRMED. KNMI FTP keeps only the last 3 days and is password protected. |
| Available for 15 Oct 2026? | Likely, since the product is continuous from 2024 and the KNMI page was updated 28 Oct 2026, but I did not verify files for 15 Oct. Treat as UNCONFIRMED. A 50 km companion product also exists on the KNMI site (not read). Gaps are listed on the KNMI page (e.g. 13 and 14 Apr 2026). |

### (c) MOSDAC and INSAT-3DS IR for 27 Oct 2026 13:00 UTC

| Step | Finding |
|---|---|
| Register | Fill the SignUp form (mosdac.gov.in/internal/registration); approval is by email. Approval time: UNCONFIRMED (not stated). New users default to General. |
| Order | Log in, "Satellite data order", pick dataset, add to cart, submit; get a request ID; email when ready; download over SFTP from ftp.mosdac.gov.in with portal credentials. |
| Latency | General users get Level-2 and higher in near real time; Level-1 has a 3-day latency, so a 27 Oct scene is old enough. Archive ordering is per the order page; the FAQ does not describe archive ordering explicitly. |
| Product | INSAT-3DS L1B IR channel (exact product ID for the 30-minute imager): UNCONFIRMED, check the INSAT-3D catalogue (mosdac.gov.in/internal/catalog-insat3d) after login. 13:00 UTC is a half-hour slot, so expect a file near 1300 or 1330 UTC. |
| Quick path | Browse images (JPG/GIF/PNG) need no registration (IP logged); these can be used as a credited link, not re-hosted as original products. |

### (d) Sentinel-1 over the delta

| Question | Finding |
|---|---|
| Constellation in Oct 2026 | S1A ended June 2026; S1C operational since May 2025; S1D scheduled to be operational from mid-April 2026. So S1C and S1D are the two satellites. |
| Delta coverage on specific dates | UNCONFIRMED. Sentiwiki does not mention India. IW VV+VH is the usual land mode; revisit near the equator is about 3 days for a pair, per the page. The acquisition plans page (sentinels.copernicus.eu/copernicus/sentinel-1/acquisition-plans) was not read, so no confirmed pass on 15 to 28 Oct. |

## What the lead should do next

1. Fix the geoBoundaries licence entry: site says CC BY 4.0, repo says ODbL. Check the ADM3 release meta file.
2. Decide the basemap: either keep Esri with the attribution and accept risk (non-commercial permission UNCONFIRMED), or switch to OSM standard tiles (easiest) or OpenFreeMap Dark (needs MapLibre).
3. Add the Open-Meteo link text and GIBS acknowledgment, and MOSDAC line, to the About dialog now; these are confirmed.
4. Ask Sachin (human) to register on Bhoonidhi with his own account, then check the guest catalogue and ROP Visualizer for S-band scenes over 81.6 to 82.6 E, 16.2 to 17.1 N. If none, keep the L/S toggle disabled and say so.
5. Keep SACHET, IMD and GDACS as credited text or live fetch only; email NDMA or IMD if re-hosting is wanted.
6. Try the EUMETSAT Data Centre collection for 15 and 27 Oct winds only if time remains; otherwise skip.
7. Landfall note for item 15: NASA Earth Observatory says landfall early on 28 Oct 2026 between Bapatla and Visakhapatnam (no exact time), 130 km/h sustained. Check against IMD (https://science.nasa.gov/earth/earth-observatory/arnab-strikes-india/).
