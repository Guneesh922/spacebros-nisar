# PROJECT PAGE DRAFT - SpaceBros, "Dancing with the SARs"

Paste each block into the matching field of the form on the team page (Project tab -> Edit). Arkadeep (team owner) submits.

## Field status (read first)
The 2026 Project Submission Guide could not be opened in a browser by this worker. A WebFetch of
https://www.spaceappschallenge.org/resources/project-submission-guide/ returned a field list, but the page text quoted a
"4 October / 5 October" submission window, which is NOT the 2026 schedule, so it may be an older edition. Field names below
match it. **Arkadeep must compare this list against the live form before pasting.** No character or word limits were published
in what was retrieved; the form itself may enforce them. The counts at the bottom are for checking against whatever the form shows.

The NISAR data is real: 8 L-band scenes, built from H5 study-box subsets. The only markers left are items a human must fill
(in square brackets). Delete or fill every marker before submitting; do not submit text that states a result the data has not produced.

---

## 1. Project Name  (field: "Project Name")
Pass by Pass: seeing Cyclone Arnab through the clouds with NISAR

## 2. High-Level Project Summary  (field: "High-Level Project Summary")
When Cyclone Arnab hit the Andhra Pradesh coast in October 2026, clouds hid the sea and the Godavari delta from ordinary cameras for days. NISAR, the NASA-ISRO radar satellite, kept seeing: it imaged the storm over the Bay of Bengal on 27 October and the coast before, during and after. Pass by Pass is a free, open-source web workspace that puts those radar images next to the cyclone track, satellite cloud pictures, rain, waves and official alerts, each with its date and source credit. Pick a date, swipe before against after, and open a one-page brief of which coastal mandals may have held water. Classes are labelled "likely". New storms or regions are added by editing one manifest file, not by rebuilding the page. It helps disaster officers, students and journalists see what radar can tell them about a cyclone. Headline results: the storm's eye has a radius of 6.4 km (plus or minus 0.5 km). About 84 km2 of likely new open water was mapped on 9 November (range 61 to 108 km2), against about 8 km2 on 28 October and about 2 km2 in a normal fortnight. **[TBD from real product: share of mandals "likely flooded", if used]**

## 3. Link to Project Demo  (field: "Link to Project Demo")
**[TO FILL after upload]** public link, no login: 30-second video (English subtitles) or <=7 slides. Script: `DEMO_SCRIPT.md`.

## 4. Link to Final Project  (field: "Link to Final Project")
Repository: https://github.com/Guneesh922/spacebros-nisar (must be Public)
Live app: https://guneesh922.github.io/spacebros-nisar/ (opens the dashboard at app/dashboard-mockup/)

## 5. Detailed Project Description  (field: "Detailed Project Description")
**The problem.** Cyclones are cloudy by definition. After Cyclone Arnab (late October 2026) the people who decide where survey and relief teams go first, such as district disaster cells and agriculture and fisheries officers on the Konaseema, West Godavari and Kakinada coast, could not see the surface under the cloud, and the data that could help sits in many portals behind different logins.

**What it does.** Pass by Pass is a static web workspace (plain HTML, CSS and JavaScript, no server) built around NISAR L-band radar. L-band radar sends its own 24 cm waves, so it images day and night through cloud. The page has three tabs.
- *Workspace*: a map with a layer drawer. Layers are grouped by NISAR, derived products, optical, weather and reference, and by phase (before, during, after the storm). Each layer shows its date, source and credit. A compare view swipes one date against another. The Andhra Pradesh coast region can be narrowed to delta districts.
- *Events*: the saved Cyclone Arnab event with its IMD track, NISAR passes before, during and after, a live alerts strip (GDACS live, NDMA SACHET as a dated snapshot) and, for delta mandals, a ranking card and a downloadable one-page brief.
- *Case study*: a scroll story in chapters: what a normal camera saw, radar under the clouds, how much rougher the sea got, where water may have stayed on the shore, what the colours mean, and what radar cannot show.

**How it works.** The page reads only `data/processed/manifest.json` (regions, sources, layers, events, analyses). The 8 NISAR L-band scenes are stored as small study-box subsets in H5 files (`data/h5/`), which are the data of record. `tools/build_web.py` builds the display images, class maps and statistics from those files, and `tools/check_manifest.py` validates the manifest. Scenes are found with the NASA CMR search API and the ASF search API. Derived measures: storm-minus-calm backscatter in dB with eye centre and radius; per-mandal share of "likely new open water" and "likely wet crops" next to a normal fortnight. Wind speed and forecasting are not claimed, and the area is reported as likely new open water, not as flooded area.

**Honest status.** The 8 L-band scenes are real. The images, class maps, mandal ranking and eye profile are built from them. Baselines (3, 4, 15 and 16 Oct) are PROVISIONAL products; event scenes (27 and 28 Oct, 8 and 9 Nov) are VALIDATED. Landfall time is not stated as one exact time, because IMD gives a window; the position 16.45 N, 81.90 E is consistent.

**Benefits and goals.** One place for NISAR plus context; plain-language limits set out in the pitch deck and `docs/METHODS.md`; reusable for the next storm or hazard (earthquake, landslide, oil spill and wildfire appear as greyed "coming next" layers, not built).

**Tools.** HTML/CSS/JavaScript, Leaflet, Chart.js, Scrollama; Python (earthaccess, h5py, rasterio, numpy, pyproj, Pillow, shapely, asf_search, pandas, matplotlib); GitHub Pages; Claude (Anthropic) as an AI assistant, see section 8. No special hardware.

**Pre-event work.** Reusable starter tools (catalogue search, quick-look downloader, GCOV subset and change-map scripts, Delhi catalogue) were committed on 13 Nov 2026, before the 14 Nov 09:30 IST start, and are tagged `v0.1-pre-event` **[tag to be created; see SUBMISSION_CHECKLIST_NEXT.md]**. The Cyclone Arnab app, manifest, assets, analysis and this page were built during the hackathon.

## 6. NASA Data  (field: "NASA Data")
- **NISAR L-band Level-2 GCOV** (geocoded backscatter, HH/HV over land, VV/VH over sea). Credit: "NISAR L2 GCOV, NASA/JPL-Caltech and ISRO, via ASF DAAC (NASA Earthdata)". Eight scenes are used: sea track 48 VV/VH on 3, 15, 27 Oct and 8 Nov 2026; coast track 55 HH/HV on 4, 16, 28 Oct and 9 Nov 2026. We catalogue 154 NISAR acquisitions over the Bay of Bengal (12 Oct to 6 Nov) and keep only the study-box subsets. Used to measure sea-surface roughening, locate the storm's surface eye, and map likely new open water and likely wet crops.
- **NASA GIBS / Worldview** imagery (VIIRS true colour, IMERG rain, Himawari band 13 via GIBS) as live context layers.
- **Background reading only, not sources used:** ASF Vertex, the NISAR Data User Guide, NISAR white papers and StoryMaps, and NASA ARSET (from the challenge Resources tab). They were read to write the plain-language notes on L-band, flooded vegetation and sea roughness.
  Background links: NISAR Data User Guide https://nisar-docs.asf.alaska.edu/ ; NISAR StoryMaps https://science.nasa.gov/mission/nisar/arcgis-storymaps ; NISAR white papers https://science.nasa.gov/mission/nisar/documents/ ; NASA ARSET https://appliedsciences.nasa.gov/arset . Data access: ASF DAAC / NASA Earthdata; alerts: GDACS and NDMA SACHET; bulletins: IMD. Audit: `docs/review/RESOURCE_AUDIT.md`.

## 7. Space Agency Partner & Other Data  (field: "Space Agency Partner & Other Data")
- **ISRO**: NISAR is a NASA-ISRO mission, and the L-band data above is the joint mission's. **S-band (ISRO) is not used in this submission.** RADARSAT-1 / RCM (CSA), SAOCOM (CONAE) and UAVSAR Postcards: not used **[reason to confirm by the team]**.
- **IMD / RSMC New Delhi** cyclone bulletins: track fixes and landfall position (public PDFs in `docs/imd_bulletins/`, linked, 15 fixes with source page). Credit: IMD.
- **NDMA SACHET** official alerts, credit "NDMA SACHET" (dated snapshot; the live feed blocks browser access). **GDACS** alerts (live), credit "GDACS (EC JRC / UN OCHA)" **[GDACS wording being confirmed]**. **INCOIS**: link only.
- **MOSDAC / INSAT-3DS**: credit "Data Source MOSDAC/SAC/ISRO. https://mosdac.gov.in". Credited link only; its rules forbid redistribution.
- **Open-Meteo** Marine and Flood APIs (CC BY 4.0, non-commercial use).
- **geoBoundaries ADM3** (2018 mandal boundaries; licence **ODbL 1.0**) and a mandal-to-district table compiled from Wikipedia, completeness not verified. **OpenStreetMap** credit "© OpenStreetMap contributors" (ODbL). Basemap: Esri World Dark Gray Canvas.
- Software: Leaflet, Chart.js, Scrollama, Google Fonts (open-source/web libraries loaded from CDNs).
Open credit items for the team: the GDACS wording and the geoBoundaries licence (both marked above).

## 8. Use of Artificial Intelligence  (field: "Use of Artificial Intelligence")
Yes. We used Claude (Anthropic) as an AI assistant for planning the scope, writing and reviewing code (the web app, the fetch and asset scripts, the manifest checker), drafting documentation and this submission text, and structuring the data-source registry. Claude also wrote draft wording for the "what radar can't show" claims, which are tagged "Draft: to be reviewed" on the page until a human expert reviews them. The 24 cm vs 9 cm wave diagram is an illustration drawn in code, not data. We did not use AI to generate imagery of the Earth, any NISAR-derived map, or any number: maps come from NISAR files and listed public sources. No NASA logos or branding were generated or modified. The humans chose the challenge, the Cyclone Arnab scope, the data sources and credit lines, ran the Earthdata logins, checked outputs against sources, and are responsible for the claims. Full statement: `docs/submission/AI_USE_DISCLOSURE.md` in the repository.

## 9. Project Submission Verification  (checkboxes)
Arkadeep ticks: agree to Terms and Conditions; confirm the work is original/our own with all sources cited. Do this only after reading the live wording.

## 10. References (use if the form has a References field; the 2026 Judging guide refers to one)
1. NASA/JPL-Caltech and ISRO. NISAR L2 GCOV products, ASF DAAC. https://search.asf.alaska.edu/
2. ASF. NISAR Data User Guide (background reading; not a source used).
3. NASA CMR search API and ASF search API (scene search); NASA GIBS / Worldview. https://worldview.earthdata.nasa.gov/
4. NISAR Applications White Papers, NISAR StoryMaps, NASA ARSET SAR trainings (background reading; not sources used).
5. India Meteorological Department, RSMC New Delhi cyclone bulletins, Oct 2026 (PDFs in `docs/imd_bulletins/`).
6. NDMA SACHET; GDACS; Open-Meteo Marine and Flood APIs (CC BY 4.0).
7. geoBoundaries ADM3 (**ODbL 1.0**); OpenStreetMap contributors (ODbL); Esri World Dark Gray Canvas basemap.
8. ISRO NISAR S-band products release note, https://www.isro.gov.in/ISRO_EN/NISARS_Band_SAR_Data_Products_Release.html (background only; S-band not used in this submission).
9. Leaflet, Chart.js, Scrollama (open-source libraries).
10. Anthropic Claude (AI assistant), see section 8.

---
## Length check (recounted 15 Nov after the update, including markdown symbols; the guide gave no limits)
| Field | Words | Characters |
|---|---|---|
| Project Name | 11 | 64 |
| High-Level Summary | 200 | 1,134 |
| Detailed Description | 544 | 3,443 |
| NASA Data | 195 | 1,331 |
| Partner & Other Data | 186 | 1,334 |
| AI Use | 153 | 952 |
No limit found, so none is exceeded on the evidence we have. If the live form shows a limit (older Space Apps forms capped the summary at roughly 1,000-2,000 characters), trim the summary first. Recount in the form's own counter.
