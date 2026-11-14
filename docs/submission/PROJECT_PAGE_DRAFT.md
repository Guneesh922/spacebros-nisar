# PROJECT PAGE DRAFT - SpaceBros, "Dancing with the SARs"

Paste each block into the matching field of the form on the team page (Project tab -> Edit). Arkadeep (team owner) submits.

## Field status (read first)
The 2026 Project Submission Guide could not be opened in a browser by this worker. A WebFetch of
https://www.spaceappschallenge.org/resources/project-submission-guide/ returned a field list, but the page text quoted a
"4 October / 5 October" submission window, which is NOT the 2026 schedule, so it may be an older edition. Field names below
match it. **Arkadeep must compare this list against the live form before pasting.** No character or word limits were published
in what was retrieved; the form itself may enforce them. The counts at the bottom are for checking against whatever the form shows.

Every number that depends on the real NISAR analysis is marked **[TBD from real product]**. As of this draft the repo holds NISAR
quick-look browse images (display only) and placeholder statistics; the GCOV subsets have not been streamed yet (needs Earthdata login).
Delete or fill every marker before submitting; do not submit text that states a result the data has not produced.

---

## 1. Project Name  (field: "Project Name")
Eye of the Storm: seeing Cyclone Arnab through the clouds with NISAR

## 2. High-Level Project Summary  (field: "High-Level Project Summary")
When Cyclone Arnab hit the Andhra Pradesh coast in October 2026, clouds hid the sea and the Godavari delta from ordinary cameras for days. NISAR, the NASA-ISRO radar satellite, kept seeing: it imaged the storm over the Bay of Bengal on 27 October and the coast before, during and after. Eye of the Storm is a free, open-source web workspace that puts those radar images next to the cyclone track, satellite cloud pictures, rain, waves and official alerts, each with its date, source, credit and one plain line on what it cannot show. Pick a date, swipe before against after, and open a one-page brief of which coastal mandals may have held water. Every map says "likely" and carries its limit; sample values are tagged on screen until real NISAR numbers replace them. New storms or regions are added by editing one manifest file, not by rebuilding the page. It helps disaster officers, students and journalists understand what radar can honestly tell them about a cyclone. Headline result: **[TBD from real product: eye radius, extra sea roughness in dB, share of mandals "likely flooded"]**.

## 3. Link to Project Demo  (field: "Link to Project Demo")
**[TO FILL after upload]** public link, no login: 30-second video (English subtitles) or <=7 slides. Script: `DEMO_SCRIPT.md`.

## 4. Link to Final Project  (field: "Link to Final Project")
Repository: https://github.com/Guneesh922/spacebros-nisar (must be Public)
Live app: **[TO CONFIRM after GitHub Pages is enabled]** likely https://guneesh922.github.io/spacebros-nisar/app/

## 5. Detailed Project Description  (field: "Detailed Project Description")
**The problem.** Cyclones are cloudy by definition. After Cyclone Arnab (late October 2026) the people who decide where survey and relief teams go first, such as district disaster cells and agriculture and fisheries officers on the Konaseema, West Godavari and Kakinada coast, could not see the surface under the cloud, and the data that could help sits in many portals behind different logins.

**What it does.** Eye of the Storm is a static web workspace (plain HTML, CSS and JavaScript, no server) built around NISAR L-band radar. L-band radar sends its own 24 cm waves, so it images day and night through cloud. The page has three tabs.
- *Workspace*: a map with a layer drawer. Layers are grouped by NISAR, derived products, optical, weather and reference, and by phase (before, during, after the storm). Each layer shows its date, source, credit and a one-line "can't show" limit. A compare view swipes one date against another. The Andhra Pradesh coast region can be narrowed to delta districts.
- *Events*: the saved Cyclone Arnab event with its IMD track, NISAR passes before, during and after, a live alerts strip (GDACS live, NDMA SACHET as a dated snapshot) and, for delta mandals, a ranking card and a downloadable one-page brief.
- *Case study*: a scroll story in chapters: what a normal camera saw, radar under the clouds, how much rougher the sea got, where water may have stayed on the shore, what the colours mean, and what radar cannot show.

**How it works.** The page reads only `data/processed/manifest.json` (regions, sources, layers, events, analyses). A pipeline regenerates the files it points to: `src/fetch/subset_arnab.py` streams only the study boxes from NISAR GCOV files hosted by ASF (never whole files) and writes GeoTIFFs; `tools/make_web_assets.py` turns them into web PNGs, mandal boundaries and the IMD track; `tools/check_manifest.py` validates the manifest. Derived measures planned: storm-minus-calm backscatter in dB with eye centre and radius; per-mandal share of "likely new open water" and "likely wet or flooded crops" next to a normal fortnight. Wind speed, flooded area in km2 and forecasting are deliberately not claimed.

**Honest status.** **[TBD from real product]** Until the GCOV subsets are processed, NISAR layers on the page are display-only quick-look browse images and the profile, mandal ranking and alerts files hold sample values; each is tagged "Quick-look sample" or "Sample values" on screen and listed in `docs/PLACEHOLDERS.md`. Landfall time is shown as "being confirmed (IMD)" because IMD's own texts disagree; the position 16.45 N, 81.90 E is consistent.

**Benefits and goals.** One place for NISAR plus context; plain-language limits on every layer; reusable for the next storm or hazard (earthquake, landslide, oil spill and wildfire appear as greyed "coming next" layers, not built).

**Tools.** HTML/CSS/JavaScript, Leaflet, Chart.js, Scrollama; Python (earthaccess, h5py, rasterio, numpy, pyproj, Pillow, shapely, asf_search, pandas, matplotlib); GitHub Pages; Claude (Anthropic) as an AI assistant, see section 8. No special hardware.

**Pre-event work.** Reusable starter tools (catalogue search, quick-look downloader, GCOV subset and change-map scripts, Delhi catalogue) were committed on 13 Nov 2026, before the 14 Nov 09:30 IST start, and are tagged `v0.1-pre-event` **[tag to be created; see SUBMISSION_CHECKLIST_NEXT.md]**. The Cyclone Arnab app, manifest, assets, analysis and this page were built during the hackathon.

## 6. NASA Data  (field: "NASA Data")
- **NISAR L-band Level-2 GCOV** (geocoded backscatter, HH/HV over land, VV/VH over sea), NASA/JPL-Caltech and ISRO, distributed by the Alaska Satellite Facility DAAC (provisional and validated GCOV_V1 products). Scenes: sea T48 F80 on 15 Oct (calm) and 27 Oct (storm eye) 2026, optionally 3 Oct and 8 Nov; coast T55 F10 on 4 Oct, 16 Oct, 28 Oct, 9 Nov 2026. We catalogue 154 NISAR acquisitions over the Bay of Bengal (12 Oct to 6 Nov) and stream only our study boxes. Used to measure sea-surface roughening, locate the storm's surface eye, and map likely new water and wet crops. **[TBD from real product: which scenes were successfully processed]**
- **NASA GIBS / Worldview** imagery (VIIRS true colour, IMERG rain, Himawari band 13 via GIBS) as live context layers.
- **NASA Earthdata Search, ASF Vertex, NISAR Data User Guide, NISAR white papers and StoryMaps** from the challenge Resources tab, used to find scenes and to write the plain-language notes on L-band, flooded vegetation and sea roughness.

## 7. Space Agency Partner & Other Data  (field: "Space Agency Partner & Other Data")
- **ISRO**: NISAR is a NASA-ISRO mission; the L-band data above is the joint mission's. ISRO NISAR S-band products on Bhoonidhi were considered for an L-versus-S toggle; **not used unless a scene is confirmed [TBD]**. RADARSAT (CSA) and SAOCOM (CONAE) data: not used.
- **IMD / RSMC New Delhi** cyclone bulletins: track fixes and landfall position (public PDFs in `docs/imd_bulletins/`, linked, 15 fixes with source page).
- **NDMA SACHET** official alerts (dated snapshot; the live feed blocks browser access). **GDACS** alerts (live). **INCOIS**: link only.
- **MOSDAC / INSAT-3DS**: credited link only; its rules forbid redistribution.
- **Open-Meteo** Marine and Flood APIs (CC BY 4.0, non-commercial use).
- **geoBoundaries ADM3** (ODbL; 2018 mandal boundaries) and a mandal-to-district table compiled from Wikipedia, completeness not verified. **OpenStreetMap** (ODbL) and **Esri World Imagery** basemaps.
- Software: Leaflet, Chart.js, Scrollama, Google Fonts (open-source/web libraries loaded from CDNs).
Credit lines for MOSDAC and OSM are still marked "[credit line to confirm]" in the manifest; confirm before submitting.

## 8. Use of Artificial Intelligence  (field: "Use of Artificial Intelligence")
Yes. We used Claude (Anthropic) as an AI assistant for planning the scope, writing and reviewing code (the web app, the fetch and asset scripts, the manifest checker), drafting documentation and this submission text, and structuring the data-source registry. Claude also wrote draft wording for the "what radar can't show" claims, which are tagged "Draft: to be reviewed" on the page until a human expert reviews them. The 24 cm vs 9 cm wave diagram is an illustration drawn in code, not data. We did not use AI to generate imagery of the Earth, any NISAR-derived map, or any number: maps come from NISAR files and listed public sources. No NASA logos or branding were generated or modified. The humans chose the challenge, the Cyclone Arnab scope, the data sources and credit lines, ran the Earthdata logins, checked outputs against sources, and are responsible for the claims. Full statement: `docs/submission/AI_USE_DISCLOSURE.md` in the repository.

## 9. Project Submission Verification  (checkboxes)
Arkadeep ticks: agree to Terms and Conditions; confirm the work is original/our own with all sources cited. Do this only after reading the live wording.

## 10. References (use if the form has a References field; the 2026 Judging guide refers to one)
1. NASA/JPL-Caltech and ISRO. NISAR L2 GCOV products, ASF DAAC. https://search.asf.alaska.edu/
2. ASF. NISAR Data User Guide (via challenge Resources tab).
3. NASA Earthdata Search; NASA GIBS / Worldview. https://worldview.earthdata.nasa.gov/
4. NISAR Applications White Papers, NISAR StoryMaps, NASA ARSET SAR trainings (challenge Resources tab).
5. India Meteorological Department, RSMC New Delhi cyclone bulletins, Oct 2026 (PDFs in `docs/imd_bulletins/`).
6. NDMA SACHET; GDACS; Open-Meteo Marine and Flood APIs (CC BY 4.0).
7. geoBoundaries ADM3 (ODbL); OpenStreetMap contributors (ODbL); Esri World Imagery.
8. ISRO NISAR S-band products release note, https://www.isro.gov.in/ISRO_EN/NISARS_Band_SAR_Data_Products_Release.html (context; S-band not used unless confirmed).
9. Leaflet, Chart.js, Scrollama (open-source libraries).
10. Anthropic Claude (AI assistant), see section 8.

---
## Length check (measured with wc on this draft; the guide gave no limits)
| Field | Words | Characters |
|---|---|---|
| Project Name | 10 | 70 |
| High-Level Summary | 184 | 1,094 |
| Detailed Description | 533 | 3,505 |
| NASA Data | 166 | 1,008 |
| Partner & Other Data | 162 | 1,134 |
| AI Use | 153 | 954 |
No limit found, so none is exceeded on the evidence we have. If the live form shows a limit (older Space Apps forms capped the summary at roughly 1,000-2,000 characters), trim the summary first. Recount in the form's own counter.
