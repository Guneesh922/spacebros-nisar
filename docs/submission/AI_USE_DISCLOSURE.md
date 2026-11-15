# AI use disclosure - SpaceBros, NASA Space Apps 2026

**Short answer:** Yes, we used AI. Claude, made by Anthropic, assisted throughout. The humans on the team made the decisions and are responsible for what we submit.

## What Claude (Anthropic) did
- **Planning.** Helped draft the one-page plan (titled "Eye of the Storm"; the product is "Pass by Pass"): scope, data-source registry (access, licence, credit line per source), build workflow, and risk lists.
- **Code.** Wrote and revised code in this repository, including the manifest-driven web app (`app/`), the fetch and asset scripts (`src/fetch/`, `tools/make_web_assets.py`, `tools/check_manifest.py`) and the earlier starter tools (`src/*.py`, notebook). Code written with AI help is not marked line by line; treat all of `app/`, `src/` and `tools/` as AI-assisted.
- **Writing.** Drafted documentation (README, schema, placeholder and gap lists), UI copy including the "what radar can't show" claims and verdicts, the demo script and the project-page text.
- **Research assistance.** Searched public pages and summarised them (for example Space Apps rules and data-source terms). Summaries were produced by tools and may contain errors; they were not treated as authority.

## What Claude did not do
- It did not produce any NISAR image, map, statistic or measurement. Maps and numbers come from the 8 NISAR L-band scenes (H5 study-box subsets in `data/h5/`) and the public sources listed in the README. No sample values remain in the product (see `docs/PLACEHOLDERS.md`).
- It did not generate photographs or videos of the Earth, and did not create or alter any NASA branding or design elements.
- It did not create accounts, hold credentials or log in to Earthdata or other portals. Humans ran every login.
- The 24 cm versus 9 cm wave diagram is an illustration drawn in code, labelled as such.

## What the humans decided and verified
- Chose the challenge, the study area and the Cyclone Arnab scope (agreed Sat 14 Nov), and what is explicitly not claimed (no wind speed, no forecasting; area is reported only as likely new open water in km2).
- Chose data sources and what may be hosted; checked licences and credit lines. Credit lines are set for NISAR, MOSDAC, OSM and SACHET. Open items: the GDACS wording and the geoBoundaries licence (being confirmed).
- Ran the Earthdata streaming and processing and inspected outputs. **[Fill in: who ran it, which scenes, what was checked against which reference, e.g. eye position against the IMD fix.]**
- Decided what to state about landfall time, because IMD's own bulletins disagree (the page does not state one exact time, because IMD gives a window, unless a human settles it).
- Reviewed, or will review, the AI-drafted radar claims; they carry a "Draft: to be reviewed" tag until a human removes it. **[Confirm status at submission.]**
- Read and approved this submission text. Arkadeep Ray (team owner) submits.

## Pre-event work (separate from AI use)
Starter tools were committed on 13 Nov 2026, before the hackathon opened on 14 Nov 09:30 IST, and are tagged `v0.1-pre-event`. These tools were also written with AI assistance. Everything after that tag was built during the event. See README.

## Files and metadata
Per the Space Apps AI guidance as we read it, AI-generated code and data must be acknowledged in descriptive text and metadata: this file, the README and the project page do that. Generated images or video, if any are added to the demo, will carry a visible "AI-generated" watermark. **[Confirm none are used.]**
