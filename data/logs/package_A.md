# Package A log - NASA GIBS imagery

Run: 2026-11-14 03:48 UTC (planner date 14 Nov 2026). Script: `src/fetch/A_gibs_fetch.py` (stages himawari, viirs, imerg, p2). Endpoint: `https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi` (WMS 1.3.0, EPSG:4326, BBOX=S,W,N,E). Exact per-image URL is in each `.json` sidecar. No credentials used.

Fetch order followed: Himawari B13, VIIRS true colour, IMERG, P2.

Images fetched: 68 (each with .json sidecar). All opened with PIL.

## Failures / flags

- **Reference_Labels_15m (context, sea, delta): FETCHED BUT EMPTY.** WMS 200 image/png, alpha fully 0 (every pixel transparent). Retried once with TRANSPARENT=TRUE&STYLES= for delta box and with layer `Reference_Labels` (250 m) for context: still alpha=0. WMTS stitching retry not done (time box; layer is Level13 tiles). Files kept on disk but are NOT usable; treat as failed. sources.yaml `GIBS_REF` set to `failed` (Coastlines_15m part is fine).
- **VIIRS true colour 2026-10-27 `_delta` (snpp, noaa20, noaa21): pixel std 3.2-3.4, below the std>5 rule.** No pure-black (nodata) pixels at all, so this looks like a near-uniform scene (cloud deck) not a missing swath. Kept; flagged for a human to eyeball. Other 27 Oct boxes pass (std 16-56).
- No ServiceException responses, no HTTP errors, no out-of-range times. Himawari 13:00Z std 82.9 (sea) / 90.3 (context), above the >20 rule (planner probe 94 was a different box).
- Reference_Labels aside, Coastlines_15m PNGs are mostly transparent by design (2.3k-3.3k opaque pixels), alpha not all 0.

## Best VIIRS for 27 Oct

Nodata-stripe test (pure black pixel fraction): 0.000 for SNPP, NOAA-20 and NOAA-21 in all boxes, so the test does not discriminate and no stripes were detected for any satellite. No satellite chosen from pixels; all three are on disk for 27 Oct. Human should pick visually (mean std on sea box: SNPP 16.2, NOAA-20 17.8, NOAA-21 24.2, not a quality measure).

## Layer table

`data/reference/gibs_layers.json` written from WMTS capabilities (epsg3857): formats, tile matrix sets, time ranges and Leaflet template for the 10 layers. All 10 layers found. Time ranges end: SNPP true colour 2026-11-02 (fetched dates 26-29 Oct: 26-29 Oct returned images; 29 Oct SNPP is within range only if listed range covers it - range ends 2026-11-02, OK); NOAA-20 2026-11-13; NOAA-21 2026-11-14; IMERG daily 2026-11-12; IMERG 30 min 2026-11-13; Himawari B13 rolling, last seen window up to 2026-11-14T03:10Z (earliest ~3 Oct per planner).

## Files (path, bytes, size, pixel std, opaque px (RGBA), sha256, flags)

|file|bytes|px|std|alpha>0|sha256|flags|
|-|-|-|-|-|-|-|
|data/raw/gibs/himawari_b13_20261027T1250Z_context.png|361982|2000x1600|90.5|3200000|e95b81123c224a0979f2d29006b10b7b3d08dc736e691b8a5b3816387c265fdc||
|data/raw/gibs/himawari_b13_20261027T1250Z_sea.png|92743|1600x1200|82.9|1920000|cb1d5ec96f0219d5c18ffda17acf7be9208d58f56335ddc39b820dd5076715c6||
|data/raw/gibs/himawari_b13_20261027T1300Z_context.png|362063|2000x1600|90.3|3200000|e369a9ea6b694fc56d1196e16a4da424f15addd1ec43316602e16212fce034ee||
|data/raw/gibs/himawari_b13_20261027T1300Z_sea.png|92693|1600x1200|82.9|1920000|ac11b7cebd93f0c4866b0e663d28949a5254dd5b2d8f45f029ab1c60abc5bd2c||
|data/raw/gibs/himawari_b13_20261027T1310Z_context.png|363831|2000x1600|90.5|3200000|6506a3d7b4eb759f127348fbd913a55578bbbc7fcd0951b9c8f140cf509c6109||
|data/raw/gibs/himawari_b13_20261027T1310Z_sea.png|91970|1600x1200|82.8|1920000|dafac9778add3aae6d6642d64139b0707c6accac874a7087e7ea8ecbbd5b810c||
|data/raw/gibs/himawari_b13_20261028T0000Z_context.png|359141|2000x1600|96.4|3200000|da25a7fc64b12e884939627a294c23daa655366f5b21fb45e17010f113f1f44b||
|data/raw/gibs/himawari_b13_20261028T0000Z_sea.png|94034|1600x1200|96.9|1920000|44eeaa41f2bb6aa4d010d9d89fe061227d37a9e8f6d95086bc8b0e73eddeac7b||
|data/raw/gibs/imerg_30min_20261027T1230Z_context.png|76521|2000x1600|93.5|1779214|644a5633f8230a9501da42fd5f59a15a04fe20aa22e554cd8a866235de41a698||
|data/raw/gibs/imerg_30min_20261027T1230Z_sea.png|66587|1600x1200|102.2|1731002|4fea04be9b8e574299fa7503b8f15e5b007b7b2069a103f0c9b9140c1b112d60||
|data/raw/gibs/imerg_30min_20261027T1300Z_context.png|74587|2000x1600|93.5|1755762|85cbc801c1dd98df7faab6080470690286d95cb416057e99e1d51bcd76728233||
|data/raw/gibs/imerg_30min_20261027T1300Z_sea.png|64293|1600x1200|102.0|1705909|4febab11a82565067ae30b28b67fc2e5aab46d5e3babd93f20adc2b94b047de5||
|data/raw/gibs/imerg_30min_20261027T1330Z_context.png|75842|2000x1600|93.6|1766202|22d25b1e64f0c1604a3192fef04ad83a6e3694f0670ff06119c10a8cb597b4a5||
|data/raw/gibs/imerg_30min_20261027T1330Z_sea.png|64920|1600x1200|102.5|1690892|f0130e6b83b3f677466ff522380add1599e13a381537893e58c268631a700c3a||
|data/raw/gibs/imerg_30min_20261028T0000Z_context.png|72862|2000x1600|93.5|1779584|e69af9f39bdc02df17d89e3c6c9e0ed9586f3782b6a8f37c3090d96281997074||
|data/raw/gibs/imerg_30min_20261028T0000Z_sea.png|63941|1600x1200|98.2|1687220|35dd9e32ae67a92b12683094cce680593a5ff962b522e406a30695a88f3a8188||
|data/raw/gibs/imerg_daily_2026-10-26_context.png|71604|2000x1600|86.7|1638050|ab0c60dc834ab88875d93ac32c0cb8703dda4ab8f88b7e95faa4a252b2b1955c||
|data/raw/gibs/imerg_daily_2026-10-26_sea.png|49352|1600x1200|84.1|1080393|7628a59dfdff891794260f48793d8f10f198521e36bcc9f36c288c89a5d47114||
|data/raw/gibs/imerg_daily_2026-10-27_context.png|94653|2000x1600|100.7|2313020|f1f9fc84610ca78b519f0ba1cb85cc9050d71872ebc845d0fe3df4df6822df0f||
|data/raw/gibs/imerg_daily_2026-10-27_sea.png|77306|1600x1200|98.1|1920000|652739472f65cc3867a7551cec2435d58daaf42f80a3d4842fe065b60b16ede1||
|data/raw/gibs/imerg_daily_2026-10-28_context.png|81312|2000x1600|92.2|2000729|c5339e611a14b07d8019d75bff674252d08ceb531ef103ed3f1d4539466ae862||
|data/raw/gibs/imerg_daily_2026-10-28_sea.png|66099|1600x1200|93.3|1761818|8224f98d8a3227c8c7568a2ec37525a5e2f7a63f2ba960b010252eca8eb45ec5||
|data/raw/gibs/imerg_daily_2026-10-29_context.png|35844|2000x1600|47.9|534692|1b36ae0cae8d16d5250f19187d3892dcf05fe30cf447459d77762034bc2501d3||
|data/raw/gibs/imerg_daily_2026-10-29_sea.png|39369|1600x1200|64.2|708502|55f670309c9d6bfb04fd3b90c0d37c6fbb267fd34d26e27e9b9dad9ac9d7d6c1||
|data/raw/gibs/ref_Coastlines_15m_context.png|31012|2000x1600|4.3|3320|9e10cdfea0cc68687f9a4d11336b597513a2a1658720045df8fa05f791f05d83||
|data/raw/gibs/ref_Coastlines_15m_delta.png|18142|1000x900|7.5|2815|2eb3ae66373d70ec9294ca310185710ba630661a556ef050e653f76ef263c269||
|data/raw/gibs/ref_Coastlines_15m_sea.png|20210|1600x1200|4.6|2303|c7ad5635ddd51638d21531b1b71e67f1d9d97a1c34998e4adbd6e616ea71e4cf||
|data/raw/gibs/ref_Reference_Labels_15m_context.png|12534|2000x1600|0.0|0|c097f5955c3c20f0893030bbf3be6108007aad8d170a5ddce7cbae3ce810dd52|alpha all 0|
|data/raw/gibs/ref_Reference_Labels_15m_delta.png|3568|1000x900|0.0|0|311053905e1184f76a7cef29b0faa5598a31e411ebedde713958fcd32d1b27c5|alpha all 0|
|data/raw/gibs/ref_Reference_Labels_15m_sea.png|7535|1600x1200|0.0|0|5a88381e93548c2d5adabdc2a87324ea05987c37f820306e5763d1a14650d43e|alpha all 0|
|data/raw/gibs/viirs_i5night_noaa20_2026-10-27_context.png|2158763|2000x1600|44.4|3199999|e05273ee57acca4c407e2f0524feb67f448439a862c840504356c0621a2f8622||
|data/raw/gibs/viirs_i5night_snpp_2026-10-27_context.png|2001382|2000x1600|43.7|3200000|42e7948ef025bf1f63daa8266538177bfefc261df2935e4696b8bf6bd63ed2a3||
|data/raw/gibs/viirs_noaa20_truecolor_2026-10-26_context.jpg|346526|2000x1600|65.0|None|30f522ccf9c9e9367723318ac4646c0c57a9eb2dd780f7844fdd9b7ac894d937||
|data/raw/gibs/viirs_noaa20_truecolor_2026-10-26_delta.jpg|26547|1000x900|14.5|None|2fc09caeef6a121a64777b42b412ae3f8f4e3864d3af7c9472cc2e7619bca5ea||
|data/raw/gibs/viirs_noaa20_truecolor_2026-10-26_sea.jpg|138126|1600x1200|49.1|None|7f159d543041fc5ca9c87d95b5bdba624f13edeb254af4965db6553624737a06||
|data/raw/gibs/viirs_noaa20_truecolor_2026-10-27_context.jpg|234196|2000x1600|45.8|None|c69bc16d9b5875faae7fc7821928c66c6625f206f6719704ba547e2c5486cc1a||
|data/raw/gibs/viirs_noaa20_truecolor_2026-10-27_delta.jpg|7509|1000x900|3.2|None|865537baa8892d1e7d85232a608e7f0f7ea0c2c54b0d932c367bf6fb8cffb6cf|std<=5 (uniform scene; no black nodata px)|
|data/raw/gibs/viirs_noaa20_truecolor_2026-10-27_sea.jpg|41965|1600x1200|17.8|None|18b45e64504148696841189c8746dcae8de185e44cf46d6d9974c1539037979b||
|data/raw/gibs/viirs_noaa20_truecolor_2026-10-28_context.jpg|199151|2000x1600|48.2|None|fe4c34214d3f614b7100eac2be438ae0f8e181499c4348c42e4707c908392254||
|data/raw/gibs/viirs_noaa20_truecolor_2026-10-28_delta.jpg|15463|1000x900|6.4|None|182abb9032df63fa67119f6d41886cd1102b6eddcf68314d7edc5b8af8503eeb||
|data/raw/gibs/viirs_noaa20_truecolor_2026-10-28_sea.jpg|64689|1600x1200|23.8|None|14426cebd0fa435f93189ebd3b174aee3566400d7b71a4a9eb13fb58e4a240ac||
|data/raw/gibs/viirs_noaa20_truecolor_2026-10-29_context.jpg|445636|2000x1600|61.6|None|708f7f368d06342f1dda340f847e7159d82ba6c43d04a43f9ee594483f24fede||
|data/raw/gibs/viirs_noaa20_truecolor_2026-10-29_delta.jpg|66907|1000x900|39.7|None|c62f7a77bafd4335a82b1aa2e2b3f196bb4f575fa81d8806f8e36b8bfc7c4895||
|data/raw/gibs/viirs_noaa20_truecolor_2026-10-29_sea.jpg|165650|1600x1200|45.2|None|e27dea92fcd57d15339a45a21011971493c4df56434a5755395be08c8baadb67||
|data/raw/gibs/viirs_noaa21_truecolor_2026-10-26_context.jpg|297545|2000x1600|59.0|None|4ca86ac275e6e6a6f4975b15f8e692de41e7e7f38cf36eeb8f34d2acce53e138||
|data/raw/gibs/viirs_noaa21_truecolor_2026-10-26_delta.jpg|21736|1000x900|11.7|None|cc0fde2db93d71d95415cfb47011102750c12fa730503f8b831e1e1387b6ec43||
|data/raw/gibs/viirs_noaa21_truecolor_2026-10-26_sea.jpg|94835|1600x1200|40.6|None|a48faefa42173ce146ce4e00fdc663598187af011261ca6de3e37b22eb8eb176||
|data/raw/gibs/viirs_noaa21_truecolor_2026-10-27_context.jpg|263035|2000x1600|56.4|None|43e8da953b58e117f8e217f37343937a1500479ea11fbb94df6819022dfad171||
|data/raw/gibs/viirs_noaa21_truecolor_2026-10-27_delta.jpg|8319|1000x900|3.4|None|cff410c962cf2e8c8efb5c9a1adcb7b3d024e0ca206079fa99dc48f218aeb1b9|std<=5 (uniform scene; no black nodata px)|
|data/raw/gibs/viirs_noaa21_truecolor_2026-10-27_sea.jpg|43746|1600x1200|24.2|None|6559e3329db3071db1b4e79d94640aa6485b772fec66381edf7676fd62572201||
|data/raw/gibs/viirs_noaa21_truecolor_2026-10-28_context.jpg|306767|2000x1600|58.2|None|5e042d89a9408e146e4ec6d02d9accea754f791287af1197a3a70a660a863ac5||
|data/raw/gibs/viirs_noaa21_truecolor_2026-10-28_delta.jpg|28511|1000x900|12.6|None|fcf8dd1cf44fc314bad914f9d2d6841bcd7e4794e0238158b2f597d78ad231c3||
|data/raw/gibs/viirs_noaa21_truecolor_2026-10-28_sea.jpg|144804|1600x1200|36.9|None|28b45137270f9818264a3a0268462860b53fd7dffa6dd96950f5cf2a36dd5bd2||
|data/raw/gibs/viirs_noaa21_truecolor_2026-10-29_context.jpg|531111|2000x1600|67.9|None|1e6dc9f8c54509051facb346dd9dd87c191b1ab0adc1dc3c6cb2ff18efdea1d3||
|data/raw/gibs/viirs_noaa21_truecolor_2026-10-29_delta.jpg|78638|1000x900|46.9|None|f81a20f1beafc854b80371229f8637c4ebf9d56a668880678165fc182c3055e9||
|data/raw/gibs/viirs_noaa21_truecolor_2026-10-29_sea.jpg|209011|1600x1200|48.1|None|3989d5059805b6e9d9a1ba509ee017dead766f9f84350562695a610bb372f327||
|data/raw/gibs/viirs_snpp_truecolor_2026-10-26_context.jpg|241492|2000x1600|53.2|None|0ff6de1773df78da0c731c04e5096c3bdd08349060fb3cacc98be2787bf03a74||
|data/raw/gibs/viirs_snpp_truecolor_2026-10-26_delta.jpg|17909|1000x900|13.8|None|bad0c4fa1dab7f17d84ea8ae3c3c7593cba684bc5fa1a136fe98d58fcedf83bb||
|data/raw/gibs/viirs_snpp_truecolor_2026-10-26_sea.jpg|89249|1600x1200|39.2|None|d94d0a47b832dde6a2c1bf62c2483b90bbe75b6979952910c20d708e54197fe6||
|data/raw/gibs/viirs_snpp_truecolor_2026-10-27_context.jpg|210482|2000x1600|47.9|None|e0da1869446f0a7ab7886d30058f646a99f2299aea08712128ecd77f75e7ef52||
|data/raw/gibs/viirs_snpp_truecolor_2026-10-27_delta.jpg|8083|1000x900|3.2|None|93a728fc38b0c3d9d381c95a496519d84e57de875c947ef81cb1945a6372e027|std<=5 (uniform scene; no black nodata px)|
|data/raw/gibs/viirs_snpp_truecolor_2026-10-27_sea.jpg|32932|1600x1200|16.2|None|d866a95190be2fbdb0c0cd4aaebe2e66d4a705150303a862775f3097bd37354d||
|data/raw/gibs/viirs_snpp_truecolor_2026-10-28_context.jpg|268521|2000x1600|55.7|None|f8e641bb8344a5b29e5dc141fa658fbbbc55600cc8da76d4ab613c351bff69e3||
|data/raw/gibs/viirs_snpp_truecolor_2026-10-28_delta.jpg|22664|1000x900|10.0|None|85eb0e736741f5e74e91fb2e5397e63bd49669ab341b342734343bd0453060b3||
|data/raw/gibs/viirs_snpp_truecolor_2026-10-28_sea.jpg|104682|1600x1200|29.6|None|54ec56f6e868db65f130033aac313069a89cb8490da77cf6b795e79c3abbc8cf||
|data/raw/gibs/viirs_snpp_truecolor_2026-10-29_context.jpg|566106|2000x1600|69.8|None|0b3d5215c1eb47dc8b47337bacebd890d683547582a9d9176fdeeb7990e45a99||
|data/raw/gibs/viirs_snpp_truecolor_2026-10-29_delta.jpg|95017|1000x900|53.4|None|f4becd879536200191d91d90a748239c81e81950aade8a8b2f70c97b69502d5f||
|data/raw/gibs/viirs_snpp_truecolor_2026-10-29_sea.jpg|223993|1600x1200|55.1|None|976360e50db7aaab4e96eac1140cd753746097f88c09061c89c95a142518ed7e||

Other files written: `data/reference/gibs_layers.json`, `src/fetch/A_gibs_fetch.py`, `data/logs/A_results_{himawari,viirs,imerg,p2}.json` (raw fetch results with URLs), this log.

## sources.yaml status

GIBS_VIIRS_TC done; GIBS_IMERG done; GIBS_HIMAWARI_IR done; GIBS_VIIRS_I5_NIGHT done; GIBS_REF failed (labels empty). Only `status:` lines edited (diff checked).

## Not done

- WMTS stitched retry for Reference_Labels_15m. - Visual choice of best VIIRS satellite. - Log named `package_A.md` per caller; FETCH_TASKS.md mentions `A_gibs.md`.
