# Demo script - SpaceBros "Pass by Pass"

Rules from the guide as retrieved (verify live): video up to 30 seconds with English subtitles, or up to 7 slides including the title slide, in English; hosted on an external public link, no login; over-limit projects are ineligible for Global Judging. Do not use NASA logos. Do not use AI-generated Earth imagery. Record the real app (screen capture). Do not voice any number that is still marked [TBD].

## A. 30-second video (about 75 words of voiceover, English subtitles burned in)
| Time | Shot (screen / layer) | Page section | Voiceover |
|---|---|---|---|
| 0-4 s | Title card on app load: Workspace tab, Andhra coast, 27 Oct, `nisar_l_sea_20261027_t48_vv` on | Workspace | "Cyclone Arnab, October 2026. Clouds hid the sea for days." |
| 4-9 s | Layer drawer: switch on `gibs_viirs_truecolor` then `imd_track_arnab`; point at the eye fix | Case study ch. 1 "What a normal camera saw" / Workspace layers | "A normal satellite sees a swirl of cloud." |
| 9-15 s | Compare swipe, calm 15 Oct (`nisar_l_sea_20261015_t48_vv`) vs storm 27 Oct | Case study ch. 2 "Radar sees under the clouds" / compare view | "NASA and ISRO's NISAR radar sees through it, day and night." |
| 15-20 s | Sea difference chart, radial profile, hover moves ring. Say the eye radius: 6.4 km (plus or minus 0.5 km). **[TBD from real product: dB figure, only if shown]** | Case study ch. 3 "How much rougher the sea got" | "It shows how the storm roughened the sea, and where its eye was." |
| 20-26 s | Events tab: coast swipe 16 Oct vs 9 Nov, class toggle "likely new water", hover a mandal, click "Download brief" | Events / case ch. 4 "The shore" | "A week on, it shows where water may have stayed, mandal by mandal. Always 'likely', never a promise." |
| 26-30 s | Layer caption with its credit line, then repo URL end card | About and data | "Open source. Every layer shows its source, and the limits are in our deck." |
Subtitles: English text of the voiceover. If speech is not used, still burn in captions.

## B. 7-slide alternative (title slide counts; export as PDF or PPTX to a public link)
1. **Title**: Pass by Pass, team SpaceBros, challenge name, one hero image (NISAR eye quick-look, credit line).
2. **Problem**: Cyclone Arnab, cloud-covered; who decides where to send teams (district disaster cells, agri/fisheries officers). Screen: Case study chapter 1.
3. **What NISAR adds**: L-band, 24 cm, day and night, through cloud. Screen: swipe calm vs storm (chapter 2).
4. **The workspace**: layer drawer with date and source credit. Screen: Workspace with drawer open.
5. **Measurements**: eye radius 6.4 km (plus or minus 0.5 km). Likely new open water: about 84 km2 on 9 Nov (range 61 to 108), 8 km2 on 28 Oct, 2 km2 in a normal fortnight. Screen: chapters 3 and 4. **[TBD from real product: sea roughness dB, if used]**
6. **Honest limits and what radar cannot tell you**: chapter 5 verdicts, no wind speed, no forecast. Full limits in `docs/METHODS.md`. **[Team: the "what radar cannot tell you" card still shows "Draft: to be reviewed" until a domain expert reviews it.]**
7. **Open and reusable**: repo, manifest-only extension, data credits, AI-use note, team. Screen: About and data panel.
Each slide: one visual, at most 25 words.

## Recording checklist
- Screen-record at 1080p from the deployed Pages URL, not localhost. Hide bookmarks and personal tabs.
- Use `app/` English only. Audio: own voice or none. Music, if any, must be licence-free and credited.
- Burn in English subtitles; upload as Unlisted/Public on a video host; test the link in a private window.
- Length check: file under 30.0 s.
