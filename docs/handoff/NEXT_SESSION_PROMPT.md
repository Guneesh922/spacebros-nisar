# Prompt for the next session (paste everything below the line)

---

You are continuing work on **SpaceBros NISAR**, a NASA Space Apps 2026 entry: a dashboard showing NISAR radar evidence of coastal flooding and ocean effects from **Cyclone Arnab** (landfall Andhra Pradesh, 28 Oct 2026). Scope is **cyclones, coastal and oceanic only**. Repo: `~/Documents/nsa/05_Code/spacebros-nisar` (remote `origin` = Guneesh922/spacebros-nisar, branch `main`; my last pushed commit is 831c3a4, a teammate has also pushed to main). Plan docs: `~/Documents/nsa/04_Project_Idea/06_PLAN_Eye_of_the_Storm.md`; backend gaps: `docs/BACKEND_GAPS.md`, `docs/PLACEHOLDERS.md` (partly stale, see below).

## Decisions already made by the user
1. **Data format is HDF5 (.h5) only.** No PNG/GeoTIFF as the data of record. All image files under `data/` were deleted (166 files, 4.7 GB). 41 of them were tracked in git and can be restored with `git restore`; 125 were never committed and are gone (they can be re-fetched from ASF / Bhoonidhi).
2. **Both bands:** L-band (NASA, via ASF DAAC) and S-band (ISRO, via Bhoonidhi).
3. **The new dashboard UI is approved and must be kept:** `app/dashboard-mockup/` (tabs "What happened" and "Data for officials and researchers", one Leaflet map). A design agent polished it; do not redesign it. Known leftovers it reported: layer table scrolls sideways, eye-profile chart / Alerts / Scenes / Downloads sections not visually reviewed, map overlays crowd at narrow desktop widths, map fit-to-bounds looks off right after a mode switch. Its map overlays now show "Radar layer data not loaded yet" because the PNGs are gone.
4. **The user does NOT want massive files on their computer, and wants the data kept in GitHub.** They asked ME to figure out how to keep the data. This is the main task.

## Main task: decide and implement where the data lives
Facts to design around (verify current GitHub limits before relying on them; my recollection): normal git rejects files over 100 MB; Git LFS free tier is about 1 GB storage + 1 GB/month bandwidth with about a 2 GB per-file cap; Releases cap assets at about 2 GB. The full scenes are 0.85 to 7.5 GB each (about 27 GB for the 8 L-band scenes), so full granules cannot live in GitHub.

Proposed approach (confirm, then do it):
1. Write a **study-box H5 subsetter** that streams each scene (HTTP range reads, nothing large stored locally) and writes a small `.h5` with only the study area: GCOV backscatter layers (HH/HV for coast, VV or VH+VV for sea, plus S-band DH), coordinates/projection, acquisition metadata, product version (PROVISIONAL vs validated). Compress (gzip, chunked). Existing helper code: `src/fetch/subset_arnab.py` and `src/gcov_subset.py` (find_grid / epsg_of; they wrote GeoTIFFs, switch the output to H5). It used `earthaccess` + fsspec (not installed in the system python; check for a venv or install in a venv).
2. **Test on ONE scene first and measure the real file size**, then choose: under 100 MB each, commit straight to git; otherwise Git LFS, or reduce resolution (multilook), or host the bulk on Zenodo / Hugging Face datasets and keep only a manifest + links in GitHub.
3. Update `data/processed/manifest.json`, `tools/check_manifest.py` and the dashboard data layer so layers come from the H5 (browsers cannot read H5 directly: add a small build step that converts H5 to what the page needs, e.g. JSON stats / tiles, derived at build time, not committed as the source of truth). Keep the "Sample values" / "Quick-look sample" honesty badges until a layer is real.
4. Then produce the real derived products from H5: class maps, sea difference map, `mandal_rank.json`, `profile.json` (the current numbers are invented placeholders).

## Scenes
**L-band (ASF, Earthdata login, needs the user's netrc; I never read or print credentials).** The 8 roles are in `data/reference/scene_manifest_full.csv`: L_SEA_CALM_1003 (T48, 7.5 GB quad-pol), L_COAST_1004 / 1016 / 1028 / 1109 (T55 F10, HH+HV, ~4.2 GB each), L_SEA_CALM_1015, L_SEA_EYE_1027, L_SEA_AFTER_1108 (T48, ~0.85 GB). 15 Oct, 4 Oct and 16 Oct are PROVISIONAL (no KML, bounds inferred); 28 Oct onward validated. Landfall time is disputed in IMD bulletins; keep `time_utc: null`.
`src/fetch/download_l_band_h5.py` downloads full granules to `data/raw/nisar_l_h5/` (git-ignored, resumes). The user may have it running or stopped; check `ls -la data/raw/nisar_l_h5`. Once the subsetter works, delete the full files to free disk.

**S-band (Bhoonidhi STAC API, user's normal portal login, typed by the user in their own terminal; never ask for or store the password).** `src/fetch/bhoonidhi_s_band.py search|download`. Search results are in `data/reference/nisar_s_candidates.csv` (152 items, all `Online: Y`). Findings: S-band covers the delta (about 96-97%) on **4, 16, 28 Oct (T55 F10, dual-pol DH, GCOV)** and 3 Oct (T48 F80, CP, 91%). **Missing from the catalogue:** the 27 Oct sea eye pass (Vista showed it planned, 13:01 UTC, "Coastal_Ocean_isro_NOE"), the 15 Oct and 8 Nov sea scenes, and 9 Nov over the delta (only frame 11, centred 18.8N, does not reach it). Ask Bhoonidhi support about those (API support address is on https://bhoonidhi.nrsc.gov.in/bhoonidhi-api/). The API download endpoint is `/download?id=&collection=`; the delivered format is not documented, so inspect the first file with h5py. The S-band downloader has NO resume (a restart wastes the partial file) and the server throttled to about 0.2 MB/s: add resume (HTTP Range) before using it again, or use the portal's HDF-to-HDF5 subsetting tool instead. S-band scene ids to fetch: `NISAR_S2_PR_GCOV_032_055_A_010_3700_DHNA_A_20261004T000102_...`, `..._033_055_A_010_..._20261016T000103_...`, `..._034_055_A_010_..._20261028T000103_...`, `..._032_048_D_080_2500_CRNA_A_20261003T130133_...` (full ids in the CSV).

## Working rules
- The working tree has other people's uncommitted edits (manifest, class PNGs, dashboard, docs). Do not commit, push, stash, reset or checkout anything unless the user asks; touch only files for your task.
- Never delete files without confirming exactly what and that it is permanent.
- Run the preview server with `mcp__Claude_Browser__preview_start name "nisar-static"` (config in `~/Documents/nsa/.claude/launch.json`, serves the repo on port 8765, open `/app/dashboard-mockup/`); Bash-started background servers get blocked.
- Run `python3 tools/check_manifest.py` after manifest changes (it currently expects PNG paths and will need updating for H5).
- Tell the user plainly what is real and what is still a placeholder.
