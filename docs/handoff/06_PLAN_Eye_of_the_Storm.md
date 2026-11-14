# Eye of the Storm – one-page plan

Nov 13, 2026 · @Sachin

The single reference for the SpaceBros build at NASA Space Apps 2026 (Dancing with the SARs), Sat 14 Nov 09:30 → Sun 15 Nov 20:00 IST. Everything else is retired.

## 0. Scope (agreed Sat 14 Nov, 10:05)

**We are building a NISAR-centred coastal-hazard interface for the Bay of Bengal coast of Andhra Pradesh, with Cyclone Arnab as the event that proves it works.** The data already exists but sits in many portals behind different logins; our job is to put it in one place, with dates, sources and plain notes on what each layer can and cannot say.

- **In scope:** the cyclone chain: cyclone → storm surge and coastal flooding → delta flooding → recovery. Sea and land together, because the decision-makers act on land.

- **Shown, not built:** earthquake and landslide (needs interferogram products, GUNW), oil spill, wildfire. They appear as greyed "coming next" layers.

- **Backbone:** a layer registry inside manifest.json, one entry per source (provider, access, licence, credit line, can we host it, delay after the event, one-line limit). A new region or hazard means new entries, not a rebuilt page. Full registry: the *Backend resource registry* tab.

- **Three access modes:** sources that need no key and allow browser access (GDACS, Open-Meteo, GIBS) load live in the browser; SACHET's feed blocks browser access, so the pipeline saves a dated snapshot of it; sources that need a login (Earthdata, Bhoonidhi) are processed by the pipeline into our own maps; sources that forbid re-hosting (MOSDAC) or need a whitelisted IP address (IMD API) are credited links only.

- **NISAR stays the core.** The challenge asks for an interactive app that uses NISAR to track and visualise surface change; every other layer is context around the radar.

- **Awareness is an output, not a second project:** plain notes on every layer plus the "what radar can't tell you" chapter.

Fit with the challenge statement (read live on 14 Nov): it asks for interactive change maps, time series or dashboards that make NISAR accessible to a broad audience, encourages ancillary data and other frequencies, and asks teams to explain the physical drivers. All of these match this scope.

## Workflow at a glance

<img src="06_PLAN_media/workflow.png" style="width:6in;height:6.75in" alt="build workflow · 5 layers, sources to consumers" />

build workflow · 5 layers, sources to consumers

Read top to bottom. The shaded layers are the two people's work; the middle layer is the hand-off: A writes the assets and the manifest, B builds the page against the manifest from Saturday 10:00 using placeholders, so neither waits for the other. The timeline gates (Sat 23:00 sea chapter live, Sun 11:30 MVP, Sun 16:00 freeze, Sun 20:00 submit) are in the hand-drawn chart in the chat.

## 1. The problem

**"After Cyclone Arnab, what did the storm do to the surface, from the open sea to the Godavari delta, when clouds hid it from every camera for three days?"** NISAR's L-band radar imaged the storm's eye on the sea at 18:31 IST on 27 Oct 2026, hours before landfall near Narsapur, and imaged the coast 4 hours and 7 days after. We turn those passes into three measured answers, each with a baseline and an uncertainty:

| Answer                                                         | Measured as                                                                                                    | Where it lives                 |
|----------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------|--------------------------------|
| How the storm roughened the sea, and where its surface eye was | Storm-minus-calm backscatter (dB), eye centre and radius, distance to IMD's interpolated fix                   | Sea chapter                    |
| What was likely flooded or waterlogged a week later, by mandal | Share of each mandal in "likely new water" and "likely wet or flooded crops", shown next to a normal fortnight | Delta chapter + district brief |
| What radar can and cannot tell you about a cyclone             | Four popular claims, each tested on the image                                                                  | Myth chapter                   |

Not in scope: wind speed in m/s, forecasting, intensification, flooded area in km².

## 2. Backend: resources and what each is for

### 2a. What is already in the folder (nsa/)

| Item                                                                                          | Where                                          | Use                                                                          |
|-----------------------------------------------------------------------------------------------|------------------------------------------------|------------------------------------------------------------------------------|
| Cyclone scene catalogue: 154 NISAR L-band GCOV acquisitions, 12 Oct–6 Nov, with download URLs | 03_Data/cyclones_bay_of_bengal_2026/scenes.csv | Pick scenes; 28 of them are UR (Urgent Response) products from 25 Oct onward |
| The eye quick-look and 14 full browse PNGs (T26, T48, T55, T120)                              | 03_Data/cyclones_bay_of_bengal_2026/           | Hero images; fallback if real files fail                                     |
| Delhi catalogue (139 GCOV + 106 GUNW) and 28-date time-lapse                                  | 03_Data/delhi/                                 | Not used this weekend; mention as future work only                           |
| Scene search, quick-look downloader, GCOV subset-to-GeoTIFF, change map, Leaflet viewer       | 05_Code/spacebros-nisar/src, app/              | Reusable pre-event tools; tag v0.1-pre-event and cite                        |
| Review, implementation plan, this plan                                                        | 04_Project_Idea/                               | Science rules and processing steps already decided                           |

### 2b. NISAR L-band from NASA (ASF) – the core

| Scene              | Track / frame / pols | Date (UTC)                           | Size    | For                     |
|--------------------|----------------------|--------------------------------------|---------|-------------------------|
| Calm sea reference | T48 F80 VV+VH        | 15 Oct 13:01                         | 0.89 GB | Sea baseline            |
| **Eye**            | T48 F80 VV+VH (UR)   | 27 Oct 13:01                         | 0.85 GB | Sea chapter             |
| Coast before       | T55 F10 HH+HV        | 16 Oct 00:01                         | 4.3 GB  | Storm footprint pair    |
| Coast +4 h         | T55 F10 HH+HV (UR)   | 28 Oct 00:01                         | 4.1 GB  | Storm footprint pair    |
| Coast before       | T156 F10 HH+HV       | 23 Oct 00:09                         | 6.8 GB  | Flood pair              |
| Coast +7 d         | T156 F10 HH+HV       | 4 Nov 00:09                          | 6.8 GB  | Flood pair, brief       |
| Normal fortnight   | T55 F10 HH+HV        | 4 Oct → 16 Oct (verify 4 Oct exists) | ~4 GB   | Baseline for thresholds |

Stream only the study box with earthaccess + h5py; never download whole files. Free Earthdata login needed.

### 2c. What NASA Space Apps provides for this challenge

Confirmed against the live [challenge Resources tab](https://www.spaceappschallenge.org/2026/challenges/dancing-with-the-sars/?tab=resources) on 14 Nov. NASA GIBS/Worldview is **not** on it, so it moved to 2e.

| Resource (challenge Resources tab)                            | Use                                                                                                                        |
|---------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------|
| NASA Earthdata Search, ASF Vertex                             | Find and download the scenes above; Vertex has an "Urgent Response" filter                                                 |
| NISAR Data User Guide (ASF)                                   | Layer names, gamma-nought convention, naming, UR caveats                                                                   |
| Intro to Remote Sensing, Intro to SAR, ARSET trainings        | Bragg, double bounce, speckle, in your own words for the myth chapter                                                      |
| NISAR StoryMaps, Applications White Papers, UAVSAR Postcards  | Citations for "L-band and flooded vegetation"; StoryMaps also cover oil slicks and subsidence for the "coming next" layers |
| CSA: RCM data, RADARSAT-1 (open licence), SAR Python tutorial | **Not used.** Say so in the form                                                                                           |
| CONAE: SAOCOM catalogue and registration                      | **Not used.** Say so in the form                                                                                           |

The page also says that for non-US-government sites we must follow that site's own data-use terms. That is why the registry carries a licence and credit line per source.

### 2d. NISAR S-band and other free Indian data (Bhoonidhi, MOSDAC, IMD)

| Source                               | What it is                                                                                                                                                                                                                          | Status and access                                                                                                                                                                                                                                                                                                                        | Use for us                                                                                                                                                                                                                          |
|--------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **NISAR S-band (ISRO)**              | Daily processed S-band products on Bhoonidhi since cycle 25 (8 Jul 2026): RSLC, GSLC, GCOV, plus interferometric and offset products ([ISRO release](https://www.isro.gov.in/ISRO%5FEN/NISARS_Band_SAR_Data_Products_Release.html)) | Free registration at [Bhoonidhi](https://bhoonidhi.nrsc.gov.in/NISAR/NisarProducts.html); coverage is the Indian landmass plus global science sites per ISRO's plan; ISRO warns of residual banding over low-signal areas such as oceans. Bhoonidhi offers an HDF-to-GeoTIFF tool with spatial subsetting, a QGIS SARPOL tool and an API | **Coast only**: an S-band GCOV over the delta before and after landfall gives the dual-frequency L-vs-S toggle (flooded vegetation vs wet soil). Must verify a scene exists over 81.6–82.6°E, 16.2–17.1°N between 16 Oct and 10 Nov |
| **EOS-04 (RISAT-1A) C-band SAR**     | Indian C-band SAR; MRS mode is collected systematically over India every 17 days ([NRSC UIM 2024](https://www.nrsc.gov.in/sites/default/files/pdf/ebooks/UIM-2024/2_UIM_2024.pdf))                                                  | MRS/CRS are open for all on Bhoonidhi; FRS (fine) is priced ([Bhoonidhi policy note](https://bhoonidhi.nrsc.gov.in/bhoonidhi_resources/help/UIM2024/4-UIM2024-Bhoonidhi_SpacePolicy_Implementation.pdf))                                                                                                                                 | Optional third frequency over the delta if an MRS pass fell in the window; otherwise skip                                                                                                                                           |
| **EOS-06 (Oceansat-3) SCAT-3 winds** | Scatterometer wind vectors on a 12.5 km grid (same NRSC source)                                                                                                                                                                     | Open data on Bhoonidhi as global binned wind-vector products                                                                                                                                                                                                                                                                             | **The missing piece for the sea chapter**: the 15 Oct calm-day wind, so the caption can say "reference day wind ~X m/s" from an Indian source                                                                                       |
| **Resourcesat-2/2A LISS-III, AWiFS** | Optical, 23.5 m / 56 m                                                                                                                                                                                                              | Open data on Bhoonidhi                                                                                                                                                                                                                                                                                                                   | A clear-sky post-storm optical check of the delta if a cloud-free pass exists after 4 Nov                                                                                                                                           |
| **INSAT-3DS / 3DR imagery (MOSDAC)** | Geostationary IR and visible every 10–30 min                                                                                                                                                                                        | MOSDAC account needed for download (search works without one); a Python download API exists ([MOSDAC API manual](https://mosdac.gov.in/node/2070))                                                                                                                                                                                       | The cloud-top eye at 13:00 UTC 27 Oct beside the radar eye                                                                                                                                                                          |
| **IMD / RSMC New Delhi bulletins**   | Track fixes, intensity, landfall statement                                                                                                                                                                                          | Public PDFs                                                                                                                                                                                                                                                                                                                              | Validation of eye position; landfall fix 16.45°N 81.90°E                                                                                                                                                                            |

The honest rule for the Indian data: it widens the backend, it does not change the pipeline. L-band carries the measurements; S-band adds one toggle; SCAT-3 and INSAT add captions and validation. If any of them fails to download by Saturday noon, nothing else moves.

### 2e. Other free sources and the hosting rule

| Source                               | Mode                                           | What it adds                                                             | Credit or limit                                        |
|--------------------------------------|------------------------------------------------|--------------------------------------------------------------------------|--------------------------------------------------------|
| NASA GIBS / Worldview (VIIRS, IMERG) | Live                                           | Cloud picture and rain                                                   | NASA data is CC0                                       |
| NDMA SACHET alerts (RSS, no key)     | Pipeline snapshot (feed blocks browser access) | Every official warning (IMD, CWC, INCOIS, state authorities) in one feed | Credit NDMA                                            |
| GDACS (public API, no key)           | Live                                           | Cyclone, flood, earthquake alerts                                        | Credit GDACS                                           |
| Open-Meteo marine and flood          | Live                                           | Waves, swell, river discharge (GloFAS)                                   | Non-commercial, under 10,000 calls a day, CC BY 4.0    |
| Copernicus Sentinel-1/2              | Pipeline                                       | Backup radar and optical                                                 | "Contains modified Copernicus Sentinel data \[Year\]"  |
| INCOIS surge and wave services       | Link, or pipeline if the key arrives           | Ocean hazard warnings                                                    | API key on request                                     |
| MOSDAC (INSAT-3DS)                   | **Link out only**                              | Cloud-top eye                                                            | Its rules forbid redistribution                        |
| IMD API                              | **Not used**                                   | –                                                                        | Needs one whitelisted IP; use the public bulletin PDFs |

**Hosting rule:** NASA data we may host freely. NRSC/Bhoonidhi data: our own derived maps only, credited "Source: NRSC, ISRO/DOS", never the raw files. MOSDAC: link only. Every caption carries its credit line.

## 3. Loose ends on backend resources

Tick these before the step that needs them. The first three decide the shape of the weekend.

- [ ] **Earthdata streaming works** on the 27 Oct eye file from your laptop (else Google Colab) – tonight

- [ ] **Bhoonidhi accounts** for both, and a search for NISAR S-band GCOV over the delta box, 16 Oct–10 Nov; note scene ids, dates, polarisations – tonight. No scene = no L/S toggle, nothing else changes

- [ ] **PR versions** of the 27 Oct T48 F80 and 28 Oct T55 F10 acquisitions: ASF says UR products may use less precise orbits; prefer PR if it now exists – Sat morning

- [ ] 4 Oct T55 F10 and 8–9 Nov scenes exist (re-run event_scenes.py for 1 Oct–14 Nov) – tonight

- [ ] EOS-06 SCAT-3 wind for 15 Oct over 15–18°N, 81–85°E downloaded from Bhoonidhi – Sat morning

- [ ] IMD bulletins for 27 Oct (fixes nearest 12 and 15 UTC) and the 28 Oct landfall statement saved as PDFs in docs/; track points typed into a CSV – tonight

- [ ] INSAT-3DS IR image nearest 13:00 UTC 27 Oct from MOSDAC (account approval can take time; apply tonight, fall back to NASA GIBS VIIRS if it is slow)

- [ ] Open mandal boundaries for Andhra Pradesh (geoBoundaries ADM3 or OSM admin level); check the licence and that the 2022 district split does not matter for mandal names

- [ ] JRC Global Surface Water occurrence tile for the delta, and an OSM coastline

- [ ] GCOV layer names in the files you open (mask, numberOfLooks, rtcGammaToSigmaFactor) match the ASF GCOV page

- [ ] Exact GIBS layer ids for VIIRS true colour and IMERG

- [ ] The 2026 Project Submission Guide fields and the FAQ wording on pre-event work (both released 13 Nov)

- [ ] Local crop calendar: is late October harvest or standing kharif paddy in the Godavari delta? (changes the caption, not the method)

Added after the scope decision (14 Nov):

- [ ] **Live feeds load in the browser:** confirm GDACS, Open-Meteo and GIBS load from the deployed GitHub Pages URL (server-side test passed 14 Nov; SACHET failed and moved to the pipeline) – Sat 12:00

- [ ] manifest.json registry written with every layer entry, including the greyed "coming next" ones – Sat 14:00

- [ ] Credit line present in every caption; MOSDAC only as a link – before Sun 16:00 freeze

<!-- -->

- [ ] **Landfall time:** IBTrACS (provisional) puts Arnab at the coast from 27 Oct 15:00 UTC (20:30 IST); this plan says 28 Oct near Narsapur. Settle it from the IMD landfall bulletin before any caption ships – Sat 14:00

## 4. Frontend: where things go

One static scroll page on GitHub Pages (Leaflet, a swipe plugin, Scrollama, Chart.js). The page reads only manifest.json; every map is a PNG with bounds, every number is JSON. No server.

| Section                      | Left column (text)                                 | Right column (map or chart)                                                        | One interaction                               |
|------------------------------|----------------------------------------------------|------------------------------------------------------------------------------------|-----------------------------------------------|
| Hero                         | Title, tagline, one sentence on NISAR              | Full-bleed eye image                                                               | Scroll cue                                    |
| 1 From above                 | What a camera saw on 27 Oct                        | NASA GIBS VIIRS, IMD track with times, landfall point                              | Hover track points                            |
| 2 Under the clouds           | What radar saw, same hour                          | NISAR VV, eye and eyewall labelled                                                 | Swipe calm (15 Oct) vs storm (27 Oct)         |
| 3 How rough                  | Three numbers with ±; the IMD comparison           | Storm-minus-calm map (dB, "relative"), radial profile chart                        | Hover chart moves a ring on the map           |
| 4 The shore                  | Likely flooded vs normal fortnight; caveats        | Delta swipe 23 Oct → 4 Nov; three classes; mandal outlines; L/S toggle if S exists | Class toggles, mandal hover, "Download brief" |
| 5 What radar cannot tell you | Four claims, four verdicts                         | One picture per claim; Bragg slider                                                | Slider: 24 cm vs 9 cm                         |
| 6 About                      | Data table, methods, limits, team, licence, AI use | Notebook link                                                                      | –                                             |

Rules: every layer carries measure, unit, dates and one limitation in its caption; "likely" before every class name; mobile stacks text above map; total page under 15 MB.

**Added after the scope decision (14 Nov):** the page gains two things around the six sections. (1) A **layer panel**, built from the registry: layers grouped by phase (before / during / after), each with date, source, credit and its one-line limit, plus greyed "coming next" hazards. (2) A **live alerts strip** fed by GDACS live plus a dated pipeline snapshot of SACHET, whose feed blocks browser access. The story chapters stay as the guided tour of the Arnab event. Exact layout is being worked out in the UI-mockup session.

## 5. Consumers and how the data helps them

| Who (exact)                                                                                                                                     | What they open                                                                                                                          | Decision it changes                                                                                                                         | What NISAR can honestly give them                                                                       |
|-------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------|
| **Primary: district disaster cell (Collector's office / APSDMA) and fisheries + agriculture officers of Konaseema, West Godavari and Kakinada** | The one-page generated brief: map, top mandals by likely-flooded share with the normal-fortnight share beside it, caveats, data lineage | Where to send survey and relief teams first in the week after landfall; which mandals to shortlist for crop and aquaculture loss assessment | A cloud-free surface map 1–3 days after each pass, labelled "likely". Not a warning, not an area in km² |
| **Secondary: cyclone researchers and IMD post-season review**                                                                                   | Sea chapter and eye.json                                                                                                                | Whether the surface eye, eyewall radius and asymmetry agree with the cloud-top picture and the operational fix                              | One rare, time-stamped snapshot with real numbers and uncertainties                                     |
| **Tertiary: teachers and journalists**                                                                                                          | Chapters 1, 2 and 5                                                                                                                     | How to explain "radar sees through clouds" without overclaiming                                                                             | Correct captions, public-domain images, the four verdicts                                               |
| **Anyone repeating this for the next storm**                                                                                                    | The notebook and manifest.json schema                                                                                                   | Whether to trust and reuse the method                                                                                                       | A pipeline that regenerates every asset from ASF and Bhoonidhi with two logins                          |

## 6. If time permits (in this order, only after the MVP is live and checked)

1.  **L/S dual-frequency toggle** on the delta (needs the S-band scene found tonight). The single most distinctive addition; no other team will show both NISAR bands.

2.  **SCAT-3 wind caption** for the calm reference day, and an **IMERG rain mask** on the sea anomaly map.

3.  **Aquaculture ponds**: if pond bunds resolve in the T55/T156 subsets, a second toggle "ponds that breached or overflowed" and a paragraph in the brief (the delta is India's shrimp belt; verify extent in frame).

4.  **8 Nov sea scene** ("the sea after the storm") and **9 Nov coast scene** (recovery).

5.  **INSAT-3DS IR eye** beside the radar eye at the same hour.

6.  **Mangrove canopy change** over Coringa (HV drop) as a map or, if short of time, one future-work paragraph.

7.  **StormCard**: a script that exports a shareable 1080×1350 card (before/after, three numbers, credit) for WhatsApp and Instagram.

Never add, whatever the time: wind speed maps, Murasu, Delhi, GUNW, RADARSAT/SAOCOM data, a live server.
