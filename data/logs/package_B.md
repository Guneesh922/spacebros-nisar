# Package B log: IMD / RSMC New Delhi bulletins, Cyclone Arnab

Run: 2026-11-14T03:54Z (agent run on 14 Nov 2026). Script: src/fetch/B_imd_fetch.py

## Method
The RSMC year links are plain GET (not the POST form): https://rsmcnewdelhi.imd.gov.in/system-archive.php?internal_menu=MzQ=&year=MjAyNg== (same page is returned for internal_menu MjY= and MzM=, i.e. it lists all products per system). System 6 on that page is 'VERY SEVERE CYCLONIC STORM ARNAB ... 24-29 OCTOBER 2026'. Download URL pattern: https://rsmcnewdelhi.imd.gov.in/download.php?path=uploads%2Farchive%2F<id>%2F<file>. No login, no browser needed.

## Files (docs/imd_bulletins/), bytes, sha256, pages (all text PDFs, all contain ARNAB)
```
20261027_0300UTC_press_release_27Oct.pdf  4692154 bytes  pages=19  e0ac9d5bb44bff036a02af091d5084d92c351fb45598644f7b81bd6efd6a77f5
20261027_1200UTC_national_bulletin_No20.pdf  4766142 bytes  pages=20  00482bb1a8432cf0e4fd8085a0a5e6226dc5c1db313fcbea1ee8f60cdba3628f
20261027_1200UTC_tc_advisory_No13.pdf  1812066 bytes  pages=9  5ea6151875bd0447e570b95e66ccb229a8cddd4b6ef0721c2727910d991370c5
20261027_1500UTC_national_bulletin_No21.pdf  4740795 bytes  pages=20  0f56217b6aef2d04c5c171a023e5f4ced7d41899953c0945bf5bac068c8f23cf
20261027_1500UTC_tc_advisory_No14.pdf  2813004 bytes  pages=11  2d9a9ee2aab8be561c278e9044e2c5c83fe989bed7642f3c6de3970c45e15e14
20261027_1800UTC_national_bulletin_No22.pdf  4068271 bytes  pages=18  6c70f365ca6c0fe005fc12eb898c29ea7a18519d9bb683619bb665ea2bdd0314
20261027_1800UTC_tc_advisory_No15.pdf  2554005 bytes  pages=11  8854082c7ecdecc50ecd232fdb063df26006cbe96b7faaf0eb40c1731dba8969
20261027_2000UTC_hourly_bulletin_No7.pdf  2278999 bytes  pages=8  a0294907ccb34deb6af715154703670f1e9e0910a02da37430567a3ca354a2b2
20261027_2100UTC_hourly_bulletin_No8.pdf  2133765 bytes  pages=9  24f0d0772fd1878eaddc29f0baa28de9cbab93d32cd43cb6f6f3d3b9857c194f
20261027_2200UTC_hourly_bulletin_No9.pdf  2255187 bytes  pages=9  af0db5332c7928658d4594ec69dcea9eb6b2cdc81f112999c19be75c0313b2ce
20261027_2300UTC_hourly_bulletin_No10.pdf  2391716 bytes  pages=9  07463dc53da65b955c8e9ccfca209d437b0cc5f3f1197048056835ff121b965c
20261028_0000UTC_hourly_bulletin_No11.pdf  2354041 bytes  pages=8  3eca6b73c611e2fd59a1b6abf061631fcc81d4b23ce8bd80b8f7ad1d2dd19af5
20261028_0000UTC_national_bulletin_No24.pdf  4068740 bytes  pages=17  815b25a421e5e6f09a8db15052af2a9aaaeaeffd36f0af031e18ba67b6ba182f
20261028_0000UTC_tc_advisory_No17.pdf  2332535 bytes  pages=10  7ad06c4c7ed945e866072eab7cebbd2682c5e0bebbba716259ce8e178394eca3
20261028_0300UTC_press_release_28Oct.pdf  4524647 bytes  pages=18  5b92bb4d910336190b9f66b64994a389ceb5b77c14ba968927ec52729e07cf92
```

Source URLs: see src/fetch/B_imd_fetch.py (each file's remote path); all https://rsmcnewdelhi.imd.gov.in/download.php?path=uploads%2Farchive%2F... All 15 returned HTTP 200.

Nearest-fix mapping: 12 UTC 27 Oct = tc_advisory_No13 + national_bulletin_No20; 15 UTC = tc_advisory_No14 + national_bulletin_No21 (also 18 UTC No15/No22 and 00 UTC 28 Oct No17/No24 and hourly bulletins 20-00 UTC). Landfall statement = 20261028_0300UTC_press_release_28Oct.pdf (Press Release-6, issued 1430 IST 28 Oct), page 1.

## Landfall statement (exact, page 1 of press release of 28 Oct 2026)
> "...crossed Andhra Pradesh & Yanam coasts between Bapatla and Visakhapatnam to the Southwest of Yanam near latitude 16.450N and 81.90E, about 20 km east-northeast of Narsapur, 40 km southwest of Yanam and 60 km southwest of Kakinada during 0200 - 0800 hours IST today, the 28th October, 2026 as a very severe cyclonic storm with the maximum sustained wind speed of 125-135 kmph gusting to 150 kmph. Latest observations indicate that the landfall process completed with the central region moving completely into land by 0800 hrs IST."

Converted: 0200-0800 IST 28 Oct = 20:30 UTC 27 Oct to 02:30 UTC 28 Oct. The planner expectation (16.45N 81.90E near Narsapur) matches the IMD text; the ~20:00 UTC single time from news is NOT what IMD says: IMD gives a 6-hour crossing window ending 02:30 UTC 28 Oct, and the centre was still offshore (16.4N 82.0E, 'practically stationary') at 21, 22, 23 and 00 UTC (hourly bulletins 8-11, advisory 17).

Internal inconsistencies in IMD text (not resolved, flagged): TC advisory No13 p1 says landfall 'during 2100-2300 hrs IST of 27th October' and, a few lines later, '2100-2300 UTC of 27th October'; hourly bulletin 7 says landfall 0200-0400 IST 28 Oct; the final statement says 0200-0800 IST. Also the NB22 text says '2330 hrs IST of yesterday, the 27th October' (wording only). Listing page mislabels some hourly bulletins (No5-7 shown as 28-10 18/19/20 UTC; file names say 27 Oct).

## Track CSV
data/reference/imd_track_arnab.csv, 15 rows, sha256 123fc03061fc47d1a2caae3cc81268a807331e75a5c87d48202ec01e46590218. Columns: the 7 requested (bulletin_id,time_utc,lat,lon,intensity,source_pdf,page) followed by the FETCH_TASKS.md columns (category,max_wind_kt,max_wind_kmh,central_pressure_hpa,note) so either spec can be read. page 'a;b' = position on page a, intensity on page b. Values were read from the PDF text layer (pdftotext) and checked against the page text; none estimated. Empty cells: max_wind_kt and pressure for national bulletins and hourly bulletins (not stated there); category for hourly bulletins (not in their table). max_wind_kmh = IMD table row for the analysis time (forecast table first row), or 'current intensity' in hourly bulletins. Checks passed: lat 10-20, lon 80-90, times non-decreasing (landfall row is last, time given as a window), every row has existing source_pdf + page. Unreadable values: none.

## Not obtained / not done
- Preliminary report and Best Track: the RSMC listing for 2026 shows no preliminary report or best-track item for Arnab (same page for those menus), so none saved. Re-check later.
- mausam.imd.gov.in press-release section not checked (RSMC press releases 23-29 Oct were sufficient). Satellite bulletins archive pages not checked.
- Only a subset of the ~200 Arnab PDFs was downloaded (12/15 UTC 27 Oct, 18 UTC, 00 UTC 28 Oct, hourly 20-00 UTC, press releases 27 and 28 Oct). Other items (quadrant wind, storm surge, track PNGs, other bulletins) are listed on the page but not fetched. Bulletin Nos 23 and 25 of the national series, advisory No16 and hourly bulletins No5-6 UTC variants are absent from the listing.
- Bulletin for 12/15 UTC: IMD publishes the National Bulletin and TC Advisory for each; both saved.

## sources.yaml status
IMD_BULLETINS: done. IMD_TRACK_CSV: done.
