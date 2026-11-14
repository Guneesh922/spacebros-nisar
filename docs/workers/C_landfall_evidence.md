# Cyclone Arnab landfall: time and place evidence (Worker C, Sat 14 Nov 2026)

Scope: every statement about landfall time/place found in the 15 IMD PDFs in `docs/imd_bulletins/`, in `data/reference/imd_track_arnab.csv`, and in IBTrACS v04r01 (last-3-years CSV, SID 2026299N16089, 27 rows, saved as `data/interim/C/ibtracs_arnab_rows.csv`). Text read with `pdftotext -layout`; page numbers are PDF pages. I do not decide the time. Conversion: IST = UTC + 5:30. The "ISSUE" times below are the bulletin's own header.

## A. Place (stable across all sources)

| Statement | Source | Page |
|---|---|---|
| Crossing "between Bapatla and Visakhapatnam, close to (south of) Yanam" | every national bulletin, advisory, press release | p1 or p2 |
| "near latitude 16.45N and 81.90E, about 20 km east-northeast of Narsapur, 40 km southwest of Yanam and 60 km southwest of Kakinada" | Press release 28 Oct (issued 1430 IST) | 1 |
| Centre at 0530 IST 28 Oct: 16.4N 82.0E, "about 30 km east of Narsapur", practically stationary for 3 h | National bulletin 24 | 1 |
| IBTrACS (JTWC-derived positions, no IMD columns): 16.4N 81.6E at 18 UTC, 16.4N 81.4E at 21 UTC, 16.4N 81.4E at 00 UTC | IBTrACS rows | n/a |

Place conflict: IBTrACS puts the centre about 0.5 to 0.6 degrees (50-60 km) farther west/inland than IMD during 18 UTC 27 Oct to 00 UTC 28 Oct (IMD: 16.3N 82.1E at 18 UTC; 16.4N 82.0E at 21, 22, 23 and 00 UTC). Treat 16.45N 81.90E (IMD) as the stated landfall point.

## B. Time: every statement, in order of issue

| # | Source file | Page | Issued (header) | Exact words (shortened) | Zone as written | In UTC | In IST |
|---|---|---|---|---|---|---|---|
| 1 | `20261027_0300UTC_press_release_27Oct.pdf` | 1 (and 2, 3, 4) | 1400 IST 27 Oct | cross coast "by forenoon of 28th October"; wind 125-135 "from early morning to forenoon of 28th" | IST (implied) | about 28 Oct 00-06:30 | forenoon 28 Oct |
| 2 | `20261027_1200UTC_national_bulletin_No20.pdf` | 2 | 2130 IST 27 Oct | "likely to make landfall during early hours (2-4 AM) of 28th October" | IST (bulletin uses IST) | 20:30-22:30 UTC 27 Oct | 02:00-04:00 28 Oct |
| 3 | `20261027_1200UTC_tc_advisory_No13.pdf` | 1 | 1500 UTC 27 Oct | "landfall during 2100-2300 hrs IST of 27th October" | **IST as written** | 15:30-17:30 UTC 27 Oct | 21:00-23:00 27 Oct |
| 4 | same | 2 | same | "landfall during 2100-2300 UTC of 27th October" | **UTC as written** | 21:00-23:00 UTC 27 Oct | 02:30-04:30 28 Oct |
| 5 | same | 3 | same | model guidance "Landfall time is varying between 28/06 to 28/12 UTC"; "latest observations indicate ... landfall early during 2100-2300 UTC of 27th October" | UTC | 06-12 UTC 28 Oct (models); 21-23 UTC (IMD) | 11:30-17:30 28 Oct (models) |
| 6 | `20261027_1500UTC_national_bulletin_No21.pdf` | 2 | 2200 IST 27 Oct | "landfall during early hours (0200-0400 Hrs IST) of 28th October" | IST | 20:30-22:30 UTC 27 Oct | 02:00-04:00 28 Oct |
| 7 | `20261027_1500UTC_tc_advisory_No14.pdf` | 1 | 1800 UTC 27 Oct | cross coast "during 2100-2300 UTC of 27th October, 2026"; p3 repeats model range 28/06-28/12 UTC | UTC | 21:00-23:00 UTC 27 Oct | 02:30-04:30 28 Oct |
| 8 | `20261027_1800UTC_national_bulletin_No22.pdf` | 2 | 0130 IST 28 Oct | "landfall process will commence during next 1-2 hours ... landfall during early hours (0200-0400 Hrs IST) of 28th October" | IST | 20:30-22:30 UTC 27 Oct | 02:00-04:00 28 Oct |
| 9 | `20261027_1800UTC_tc_advisory_No15.pdf` | 2, 4 | 2100 UTC 27 Oct | "landfall ... during early hours (2130-2330 UTC) of 27th October"; p4 "landfall process has commenced and it will continue another 3 to 4 hours" | UTC | 21:30-23:30 UTC 27 Oct (+3-4 h) | 03:00-05:00 28 Oct (process to about 08:00) |
| 10 | `20261027_2000UTC_hourly_bulletin_No7.pdf` | 1 | 0220 IST 28 Oct | "Wall cloud region is entering into the land; Landfall process is continuing; Landfall Time: 0200-0400 IST of 28.10.2026" | IST | 20:30-22:30 UTC 27 Oct | 02:00-04:00 28 Oct |
| 11 | `..._2100UTC_hourly_bulletin_No8.pdf` | 1 | 0330 IST | "Landfall process will continue for next 3 hours" | IST | to about 22:00 UTC 27 Oct | to about 06:30 |
| 12 | `..._2200UTC_hourly_bulletin_No9.pdf` | 1 | 0410 IST | "will continue for next 3 hours" | IST | to about 23:40 UTC | to about 07:10 |
| 13 | `..._2300UTC_hourly_bulletin_No10.pdf` | 1 | 0515 IST | "As the system is Practically Stationary, the Landfall process will continue for next 2-3 hours" | IST | to about 00:45-01:45 UTC 28 Oct | to about 07:15-08:15 |
| 14 | `20261028_0000UTC_hourly_bulletin_No11.pdf` | 1 | 0630 IST | "Practically Stationary ... continue for next 2 hours" | IST | to about 03:00 UTC 28 Oct | to about 08:30 |
| 15 | `20261028_0000UTC_national_bulletin_No24.pdf` | 1, 2 | 0845 IST | centre at 0530 IST 16.4N 82.0E, 30 km east of Narsapur; cross coast "during next 2 hours"; "landfall process will continue during next 2 hours" | IST | about 02:00 UTC 28 Oct | about 07:30-08:45 |
| 16 | `20261028_0000UTC_tc_advisory_No17.pdf` | 1, 3 | 0300 UTC 28 Oct | "landfall process will continue during next 2 hours"; p3 "landfall process has commenced and it will continue another 2 hours" | UTC-based | to about 05:00 UTC (issue time 03:00 + 2 h) | about 08:30 |
| 17 | `20261028_0300UTC_press_release_28Oct.pdf` | 1 | 1430 IST 28 Oct | "crossed ... during 0200 - 0800 hours IST today, the 28th October ... landfall process completed with the central region moving completely into land by 0800 hrs IST" | **IST as written** | 20:30 UTC 27 Oct to 02:30 UTC 28 Oct | 02:00-08:00 28 Oct |
| 18 | `data/reference/imd_track_arnab.csv` row PR6 (landfall) | n/a | derived | `time_utc` = "2026-10-27T20:30Z/2026-10-28T02:30Z" (copy of #17) | UTC | same as #17 | same as #17 |
| 19 | IBTrACS, `LANDFALL`/`DIST2LAND` columns | n/a | n/a | DIST2LAND 54 km at 12 UTC, 11 km at 15 UTC, 0 from 18 UTC 27 Oct (positions 16.4N 81.6E); `LANDFALL`=0 first appears on the 15 UTC row (min distance to land in next period) | UTC, 3-hourly | first land contact between 15:00 and 18:00 UTC 27 Oct | between 20:30 and 23:30 IST 27 Oct |

Other time anchors that are not landfall statements but matter for captions:
- IMD says the system was "practically stationary" offshore at 16.4N 82.0E in hourly bulletins 8-11 (21, 22, 23, 00 UTC) and NB24 (0530 IST).
- Hourly bulletin 7 reports Narsapur rain/wind observations "around 0100 hrs IST of 28.10.2026"; Bhimavaram wind 93 km/h at 0200-0300 IST (HB9).
- PR 28 Oct also says the storm "weakened into a severe cyclonic storm" and was at 16.5N 81.9E at 0830 IST (IMD category change after landfall).
- Header/file-name mismatch: files named `..._2000UTC_hourly_...` are dated 28-10-2026 in their headers (issue 0220 IST = 20:50 UTC 27 Oct). File names are UTC of the data time; the header time is the issue time.

## C. Where they conflict

1. **27 Oct evening vs 28 Oct early hours.** Row 3 (TC advisory 13, p1, "2100-2300 hrs IST of 27 Oct") says the crossing was already due that evening. Row 4 (same file, p2, "2100-2300 UTC") and rows 2, 6, 7, 8, 10 say the early hours of 28 Oct IST. The "IST" in row 3 is the odd one out inside its own document; "2100-2300 UTC" equals "0230-0430 IST", which matches the national bulletins. This is a reading of the text, not a correction by IMD.
2. **2-4 AM vs 0200-0800 IST.** The bulletins and hourly bulletin 7 give a two-hour window (0200-0400 IST); the 28 Oct press release gives a six-hour window ending with the centre fully inland by 0800 IST. The press release is a later, summary statement; the hourly bulletins up to 0630 IST still say the process is continuing.
3. **Centre position vs "landfall" wording.** Until at least 0530 IST (NB24) the centre is about 30 km offshore (east of Narsapur). The "wall cloud/outer band entering land" statements describe the eyewall edge and rain bands, not the centre.
4. **Model guidance in TC advisories 13 and 14 (p3): 28/06-28/12 UTC** (11:30-17:30 IST 28 Oct). This is a forecast range from models, later than IMD's own estimate. Do not quote as an observation.
5. **IBTrACS (JTWC-based) puts first land contact at 15-18 UTC 27 Oct (20:30-23:30 IST)**, several hours earlier than IMD's centre position, and 50-60 km west of IMD's centre. IBTrACS is provisional and its DIST2LAND uses its own position.
6. **TC advisory 15 p2 "2130-2330 UTC"** (03:00-05:00 IST) vs NB22 "0200-0400 IST" for the same sentence: one hour offset between the UTC and IST versions of the same bulletin pair.

## D. Ranked reading (for the lead to choose; I have not decided)

1. **Official final IMD statement (row 17): crossing during 0200-0800 IST 28 Oct = 20:30 UTC 27 Oct to 02:30 UTC 28 Oct; centre completely inland by 0800 IST (02:30 UTC).** Latest, post-event, and consistent with the centre positions in rows 15 and 16 (still offshore at 0530 IST). Best single authority; cite page 1 of the 28 Oct press release.
2. **IMD operational window 0200-0400 IST 28 Oct (20:30-22:30 UTC 27 Oct)**: rows 2, 6, 8, 10. Consistent with 2100-2300 UTC (row 4, 7) within one hour. The first half of reading 1.
3. **IBTrACS/JTWC: first land contact 20:30-23:30 IST 27 Oct (15-18 UTC)**. Independent source, provisional, different position. Use only as a footnote or for a "first land contact" claim, not as the landfall time.
4. **TC advisory 13 p1 "2100-2300 IST 27 Oct"**: most likely a unit slip (see C1). Do not use.
5. **Model range 06-12 UTC 28 Oct**: forecast only. Do not use.

Imagery implication (not a decision): a satellite pass at or after about 02:30 UTC 28 Oct (08:00 IST) is post-landfall under all IMD readings. A pass before about 20:30 UTC 27 Oct (02:00 IST 28 Oct) is pre-landfall under all IMD readings.

## E. Recommended caption wording (true under readings 1-3)

Preferred (no clock time):
> "Cyclone Arnab crossed the Andhra Pradesh coast near Narsapur (about 16.45 N, 81.90 E) on the night of 27-28 October 2026. IMD reports the crossing between 02:00 and 08:00 IST on 28 October; the storm's centre was fully inland by 08:00 IST."

Shorter, with both zones:
> "Landfall near Narsapur, night of 27-28 Oct 2026 (IMD: crossing 02:00-08:00 IST on 28 Oct, i.e. 20:30 UTC 27 Oct to 02:30 UTC 28 Oct)."

Avoid: a single clock time; "landfall at 20:00 UTC" (not an IMD statement); "evening of 27 October"; "landfall on 28 October" alone (true in IST only for most of the window, false in UTC for part of it); any use of "IST of 27 October" from TC advisory 13 p1.

Manifest note suggestion (the lead edits manifest.json): keep `time_utc: null`; set note to "IMD: crossing 02:00-08:00 IST 28 Oct (20:30 UTC 27 Oct to 02:30 UTC 28 Oct), near Narsapur; first land contact per IBTrACS earlier".
