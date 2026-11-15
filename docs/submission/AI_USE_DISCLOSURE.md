# AI use disclosure - SpaceBros, NASA Space Apps 2026

**Short answer:** Yes, we used AI. Claude, made by Anthropic, assisted throughout, mainly by writing code and documentation to our direction. The team chose the problem, the data, the design and the interpretation, and is responsible for what we submit.

## What the team did
- **Chose the challenge, the event and the scope.** Dancing with the SARs, Cyclone Arnab on the Andhra Pradesh coast, cyclones with coastal and ocean effects only, and what is explicitly not claimed (no wind speed, no forecasting; flooding is reported only as likely new open water in km2).
- **Pinpointed the data and the oceanography resources.** We decided which NISAR passes mattered (coast track 55, sea track 48, before, during and after landfall), and picked the ocean and weather sources we wanted beside the radar: IMD / RSMC New Delhi bulletins and track, NASA GIBS (VIIRS, IMERG, Himawari), ERA5 wind, GDACS and NDMA SACHET alerts, and the challenge's NISAR reading list. We decided what may be hosted and checked the licences and credit lines.
- **Proposed the newsletter format.** The idea that the public page should read like a newsletter that updates with every satellite pass (the idea behind the earlier name "Pass by Pass", since renamed Matsya), with earlier updates kept as an archive and a feed, came from the team.
- **Set the exact theme and the visuals.** We chose the name and theme, the two-audience layout ("What happened" for the public, "Data for officials and researchers"), one shared map, and which visuals to show: flood share by mandal, radar before and after, the cyclone eye and its profile, radar by date, the mandal table and the per-scene histograms. The dashboard design was approved by the team before data was wired in.
- **Decided how to interpret the data.** We decided what a change in radar brightness may and may not be read as: dark, smooth surfaces on land as likely new open water; wet or flooded crops treated as a weak signal and kept out of the public ranking; the 9 November water attributed to Cyclone Murasu and the river peak as well as Arnab; the sea brightening on 27 October read as mostly the storm; landfall given as IMD's window, not one time.
- **Decided how to depict the data and which colour codes to use.** Greyscale for radar brightness with a stretch per scene type; one blue-white-orange ramp for change with a grey band for "no clear change"; fixed class colours on the dark basemap (new open water blue, wet or flooded crops amber); a dual-polarisation colour composite beside the grey view; and a colour-blind check on the palette.
- **Did every login and set the rules.** Team members created and used the Earthdata account; Claude never held credentials. We decided that the data of record is the HDF5 subsets, that the product is L-band only, and that data-quality caveats live in the pitch deck and `docs/METHODS.md`.
- **Reviewed the result.** We looked at the built maps and numbers (for example the eye position against the IMD fix), read the plain-language findings, and approved this submission text. Arkadeep Ray (team owner) submits.

## What Claude (Anthropic) did
- **Code.** Wrote and revised the code in this repository to the team's specification: the dashboard (`app/`), the fetch and subset scripts (`src/fetch/`), the build, pipeline and test tools (`tools/`) and the GitHub workflows. Code written with AI help is not marked line by line; treat all of `app/`, `src/` and `tools/` as AI-assisted. Claude also ran these scripts and tests during development.
- **Writing.** Drafted the documentation (README, methods, schema, pipeline notes) and the wording of the page, including the sentence templates behind the plain-language findings. The team edited and approved them.
- **Planning help.** Helped turn the team's idea into a written plan: task lists, a data-source registry (access, licence, credit line per source) and risk lists.
- **Research assistance.** Searched public pages and summarised them (for example Space Apps rules and data-source terms). Summaries may contain errors and were not treated as authority.
- **Implementing our design choices.** Turned the team's choices of visuals, interpretation rules and colours into code, and ran numeric checks on them (`docs/review/COLOUR_CHECK.md`, `docs/review/RGB_COMPOSITE.md`, `docs/review/LBAND_TEST.md`).

## What Claude did not do
- It did not invent any NISAR image, map, statistic or measurement. Every map and number is computed by the code in `tools/` from the 8 NISAR L-band scenes (H5 study-box subsets in `data/h5/`) and the public sources listed in the README. No sample values remain in the product (see `docs/PLACEHOLDERS.md`).
- It did not generate photographs, images or videos, and did not create or alter any NASA, ISRO or Space Apps branding.
- It did not create accounts, hold credentials or log in to Earthdata or other portals.

## Pre-event work
A starter repository (NISAR scene search and quick-look tools for Delhi) was committed on 13 November 2026, before the hackathon opened on 14 November 09:30 IST (commit `c4f110c`). It was also written with AI assistance. It is not part of the product and was removed from the main branch; it remains in the git history. Everything else was built during the event.

## Files and metadata
Per the Space Apps AI guidance as we read it, AI-generated code and data must be acknowledged in descriptive text and metadata: this file, the README and the project page do that. No AI-generated images or video are used in the product.
