# Eye of the Storm: UI direction and risks

Sat 14 Nov 2026, 10:30 IST, revised 10:50 (v2) · frontend decisions for the SpaceBros NISAR build.
Mockup (Design canvas): https://claude.ai/artifact/AhKDZ8HmCuVyTeWSxy4zuE

## 1. Decisions taken

| Question | Decision |
|---|---|
| Page shape | **Direction A, a two-column split.** The story scrolls on the left (38%, min 420 px) and one Leaflet map stays fixed on the right. Scrollama steps change the map's layers. |
| First 5 seconds | Radar eye image (hero) on the map, plus a **"Where to send teams first"** strip: the top 5 mandals by likely-flooded share, a normal-fortnight tick, and a **Download brief** button, all above the fold. |
| Layer panel | A **drawer over the right edge of the map** (400 px) that opens from a "Layers" button. It is closed while the story plays. On phones it becomes a bottom sheet. |
| Mood | Light, cool paper (#F1F4F3) for text and tools; **dark map stage** (#0F1B1F) with **greyscale radar**. Teal = NISAR only, blue and amber = the two "likely" classes only. No stock imagery: the radar images are the only pictures. |
| Phone | Text stacks above the map (≈40 / 60). Same components, fewer words. |

Rejected options: floating cards over a full-width map (they cover the west of the delta, where Narsapur is, during chapter 4), and a three-column layout with an officer rail (the map shrinks to about 45% on a 13-inch laptop, so the radar becomes secondary).

## 2. What the mockup shows (8 artboards)

1. Desktop main screen: header (EN / తెలుగు toggle, Download brief), alerts strip, hero text, top-5 mandal bars, chapter list, radar eye with the IMD track and the landfall marker, layer caption.
2. Desktop with the layer drawer open: Before / During / After / Coming next groups. Each row shows date, source, credit and a one-line limit, with a NISAR chip or a grey "context" chip.
3. Desktop chapter 4, The shore (**interactive**): a swipe slider from 23 Oct to 4 Nov, the "likely" classes, mandal outlines, the L/S-band toggle, and the selected mandal's card with a brief button.
4. Desktop chapter 3, How rough (**interactive**): stat tiles with ± values. Hovering the radial profile chart moves a ring on the map to the same distance from the eye.
5–7. Phone versions of the main screen, the layers sheet and chapter 4 (**interactive**).
8. Mandal brief, one A4 page (new in v2).

In the mockup, every number is a **sample value** and is labelled as one. Alert headlines are `[placeholders]`. Radar images are real NISAR quick-looks: the T48 eye pass, and T55 delta passes standing in for the T156 23 Oct / 4 Nov pair.

## 3. Risks and how we handle them

These items are in the mockup now. Each has a condition it must meet to stay in the build, and a fallback.

| # | Item | Risk | Keep it if… | Fallback | Gate |
|---|---|---|---|---|---|
| R1 | **Live alerts strip** (SACHET + GDACS) | The SACHET feed blocks browser requests (CORS), and GitHub Pages has no server to relay it. GDACS may also fail from some networks. | GDACS live fetch works from github.io in Chrome and Safari. | **The default is a dated snapshot** (`alerts_snapshot.json`, written by the pipeline). Live only replaces it when the fetch succeeds, and the strip always shows "snapshot, <date time IST>" or "live". | Sat 23:00 |
| R2 | **L/S-band toggle** (ch 4) | NISAR's S-band (ISRO) may have **no scene** over the delta for 23 Oct / 4 Nov. A toggle with no data behind it costs us credibility. | An S-band GCOV/RSLC scene exists for both dates **and** is processed by Sun 11:30. | Drop the toggle. Show "L-band only" with one line: "S-band (9 cm) would mostly bounce off crops; see chapter 5". The 24 cm vs 9 cm comparison stays in chapter 5. | Sun 11:30 |
| R3 | **Chart hover moves a ring on the map** (ch 3) | Linking Chart.js to Leaflet takes time, and the scale (px per km) must be right. | `profile.json` = `[{r_km, db, err}]` plus eye centre lat/lon exist. The ring is an `L.circle(centre, r_km*1000)`, so Leaflet handles the scale. | Static chart, with fixed rings drawn at 25 / 50 / 100 km on the map. | **First cut** if behind at Sat 23:00 |
| R4 | **Mandal ranking** (hero strip + brief) | The hero strip and the PDF brief both depend on it. It needs mandal polygons, zonal stats of the class rasters, and a normal-fortnight baseline. | Person A owns `mandal_rank.json` by **Sun 09:00**. | Hero strip shows the delta-wide figures only. The brief becomes one page for the whole district. | Sun 11:30 |
| R5 | **Telugu later** | Telugu text runs about 30% longer, and fixed-width buttons break. | All UI strings are kept in `strings.en.json`. Buttons and cards use padding, never fixed widths. Font stack includes Noto Sans Telugu. | The toggle stays and shows "soon". | Design rule, no gate |
| R6 | **NISAR must stay the core** | Optical, IMD and model layers can visually take over. | Every radar layer carries a **teal "NISAR L-band" chip**. Other sources get a grey chip and are off by default, except the IMD track. The hero is the radar eye, not an optical image. | — | Check at the freeze |
| R7 | **Page weight under 15 MB** | Full-size browse PNGs are 1.6–4.7 MB each. | Each map PNG ≤ 600 KB (crop to the AOI, ≤ 1400 px, 8-bit palette for class maps). Budget: ~10 images ≈ 6 MB plus libraries. | Lazy-load chapters 5 and 6. | Sun 16:00 |

**Cut order if behind:** R3 ring link → R2 toggle → live part of R1 → per-mandal brief pages (R4 fallback). Never cut the hero, chapter 4, the layer captions or the "likely" wording.

## 4. Data the UI expects (contract for Person A)

- `manifest.json` layer entry: `id, group (before|during|after|next), name, chip (nisar|context|model|reference), date, shows, source, credit, limit, png, bounds, default_on`.
- `mandal_rank.json`: `[{mandal, district, water_pct, water_err, crops_pct, crops_err, normal_pct, rank}]`.
- `profile.json`: `{eye: [lat, lon], eye_radius_km, eye_radius_err, imd_offset_km, points: [{r_km, db, err}]}`.
- `alerts_snapshot.json`: `{saved_at_ist, sachet: [{headline, area, issued}], gdacs: [...]}`.

## 5. Visual rules (v2)

- **Colours:** ink #131E22 · ink 2 #3F4D53 · muted #586469 · paper #F1F4F3 · quiet fill #E6EBEA · line #D3DAD8 · map stage #0F1B1F · NISAR teal #17635F (tint #D8EAE7, on the map #5FD0C3) · likely new open water #2A6FB0 · likely wet or flooded crops #E09A2B · likely no change = outline only.
- **One colour, one meaning.** Teal = NISAR and the brand. Blue and amber = the two classes and nothing else. Limits, "sample" tags and alerts are neutral.
- **Type:** Anek Latin (UI and headings; headings at 88% width, weight 600) with Anek Telugu as its matching Telugu face, so the switch to Telugu keeps the same look. IBM Plex Mono only for numbers, dates and scene ids. Body 16 px desktop / 15 px phone; nothing under 13 px except mono metadata and chips (12 px).
- **Radar is greyscale** (VV for sea, HH for land, in dB), never the magenta quick-look colours, so the class colours and rings stand out.
- Every class label starts with "likely". Every number shows ±. Touch targets ≥ 44 px. Text contrast ≥ 4.5:1.

## 6. Review of v1 and what changed in v2 (14 Nov, 10:50 IST)

| # | Problem in v1 | Change in v2 |
|---|---|---|
| 1 | The magenta quick-look images fought the teal and amber palette, and the amber class was hard to see on pink land. | Radar shown in greyscale on a dark map stage. The pipeline should export greyscale dB PNGs. |
| 2 | Amber meant three things: a flood class, every "Limit" line, and the "Sample" tags and alert dot. | Amber and blue are class colours only. Limits are neutral text with a bold "Can't show:" label. |
| 3 | Warm cream paper looked editorial and unrelated to the radar. | Cool neutral paper (#F1F4F3) with white cards. |
| 4 | IBM Plex Sans + Noto Sans Telugu were two unrelated families; lots of 11–12 px text. | Anek Latin + Anek Telugu (one family). Minimum 13 px. |
| 5 | Ranking bars showed one total; ± was only text. | Stacked bar (water + crops), a ± whisker, the normal-fortnight tick, a legend. Rows are tappable. |
| 6 | Map captions were free text. | Fixed three rows: **Shows** (measure, unit, date) / **Can't show** / **Source**. This matches the plan rule "measure, unit, dates, one limitation". |
| 7 | Layer drawer: 14 rows × 3 lines. | "On now" section with full detail; other layers are one-line rows that expand; "Coming next" is one row. |
| 8 | Chapter navigation differed per screen. | One chapter rail at the top of the story column on every screen. |
| 9 | Chapter 4 showed two classes and text percentages. | Three classes (adds "likely no change"); cyclone fortnight vs normal fortnight as paired bars; legend doubles as class toggles. |
| 10 | The brief, the main product for district officers, had no design. | New A4 artboard: map crop, three numbers, neighbour ranking, "What this is / is not", data lineage. |
| 11 | Hero said "~6 h before landfall" and "28 Oct". | Both are placeholders until the IMD landfall bulletin settles the time (plan §3 open item; IBTrACS suggests 27 Oct 20:30 IST). |

New build tasks from v2: (a) pipeline exports greyscale PNGs; (b) `mandal_rank.json` already carries water and crops separately, as the stacked bars need; (c) `manifest.json` layer entries gain `shows` (measure + unit) next to `limit`; (d) the brief is an HTML print page (`@media print`, A4), not a generated PDF, which fits the no-server rule.
