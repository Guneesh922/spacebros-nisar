# Remaining submission steps (as of Sat 14 Nov 2026, evening)

Deadline: Sun 15 Nov 2026, 23:59 IST (Delhi local event time; confirm on the live guide). Target: submit by **20:00 IST** on Sun.
**Only Arkadeep Ray (team owner, @mindlab8912) can press Submit.** Guneesh prepares everything so Arkadeep only pastes and clicks. Arkadeep is not a repo-owner by default (repo is under Guneesh922): decide who owns the public repo and make sure both can push.

| # | Step | Owner | Deadline (IST) | Done |
|---|---|---|---|---|
| 1 | Open the live 2026 Project Submission Guide in a browser; compare field list and limits with `PROJECT_PAGE_DRAFT.md`; note the exact deadline and video rules | Arkadeep | Sat 14 Nov 22:00 | [ ] |
| 2 | Ask local lead (Astha G) or Contact Us whether pre-event starter tools are allowed; record the answer. The FAQ says teams may not start before the hackathon | Arkadeep | Sat 14 Nov 22:00 | [ ] |
| 3 | Create the tag: `git tag v0.1-pre-event f603307 && git push origin v0.1-pre-event` (none exists yet) | Guneesh | Sat 14 Nov 22:00 | [ ] |
| 4 | Both confirmed the Delhi Participation Confirmation Form (needed for certificates) | Arkadeep + Guneesh | Sat 14 Nov | [ ] |
| 5 | Data is built: 8 L-band scenes are H5 subsets in `data/h5/`; display assets are built by `tools/build_web.py`; check the manifest with `tools/check_manifest.py` (no placeholders in the manifest) | Guneesh / Worker backend | Sun 15 Nov 09:00 | [ ] |
| 6 | No placeholders remain in the product. Fill only the `[TBD from real product]` items that are still open in the drafts (for example the dB figure and the share of mandals, if used) | Guneesh + Arkadeep | Sun 15 Nov 14:00 | [ ] |
| 7 | Human decides landfall wording (IMD gives a window; `time_utc` stays null) and reviews the "what radar can't show" claims. MOSDAC and OSM credit lines are set. Open: GDACS wording and the geoBoundaries licence | Arkadeep | Sun 15 Nov 14:00 | [ ] |
| 8 | Freeze code Sun 16:00; make repo **Public**; swap in `README_DRAFT.md` as `README.md` (resolve its bracketed notes); keep `docs/submission/` | Guneesh | Sun 15 Nov 16:00 | [ ] |
| 9 | Pages is live at https://guneesh922.github.io/spacebros-nisar/ (redirects to `app/dashboard-mockup/`). Test it in a private window incl. GDACS, Open-Meteo, GIBS; no login needed | Guneesh | Sun 15 Nov 16:00 | [ ] |
| 10 | Record 30 s video (or build 7 slides) from `DEMO_SCRIPT.md`; English subtitles; upload to a public link; test in a private window | Guneesh | Sun 15 Nov 18:00 | [ ] |
| 11 | Finalise `PROJECT_PAGE_DRAFT.md` and `AI_USE_DISCLOSURE.md` (fill the bracketed lines truthfully, including who verified what) | Guneesh + Arkadeep | Sun 15 Nov 18:30 | [ ] |
| 12 | Arkadeep pastes each field into team page -> Project -> Edit; ticks the verification boxes; clicks Save, then **Submit** | **Arkadeep only** | Sun 15 Nov 20:00 | [ ] |
| 13 | Verify the project shows as submitted/complete; screenshot it; open the demo and repo links from a logged-out browser | Arkadeep + Guneesh | Sun 15 Nov 20:30 | [ ] |
| 14 | Buffer for failures; anything not submitted by 23:00 is at risk | both | Sun 15 Nov 23:00 | [ ] |

Known risks: no `v0.1-pre-event` tag yet; guide fields not confirmed from the live 2026 page; CORS for live feeds from the Pages origin untested; Arkadeep must be logged in on the platform with team-owner rights.
