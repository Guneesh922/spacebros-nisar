# Pro tab review (14 Nov 2026)

Top 10 (value/effort), files in app/dashboard-mockup/js/dash.js unless noted:
1. Scene catalogue from data/h5/catalog.json (not manifest): add start_utc (IST+UTC), band, role, pass A/D, pols, posting_m, product_status, size, sha256, latency; sceneBlock().
2. Layers table too wide: Licence/Status/On-map cut off at 1400 and 800 px. Collapse to 3 columns (Layer, Source+licence, Status) with On-map checkbox first; layerRows(), dash.css .dt.
3. Mandal table: flooded km2 (area x %) and change vs normal in pts; fix rank semantic (rank follows open water, not Total column; Kovvur 3.7 ranks below 2.1); mandalTable().
4. Sparkline column per mandal (water % across all dates) once archive grows; mandalTable() + mandal_rank.json per-date arrays.
5. Honest uncertainty: show +-, flag rows where error > value (e.g. Peddapuram 4.2+-9.4) as "not distinguishable from zero"; legend that normal-fortnight comparison is the noise floor; keep SAMPLE badge until real.
6. Eye profile: annotate eye edge, peak, IMD-fix offset; shade +-err band; add calm-reference curve (15 Oct) for contrast; profileChart().
7. Downloads: add per-scene H5 links with size + sha256 from catalog.json, copy-citation button (BibTeX/plain), catalog.json + manifest.json "API" row, method link; dlBlock().
8. Small multiples: same coast box x 4 dates (and sea x 4) as tiny thumbnails with dB colour bar; click sets map layer. New card between Eye profile and Scenes.
9. Per-date backscatter histogram (HH, HV dB) with water threshold marked, from build_web stats JSON; shows why change classes are/aren't separable. Also coverage % and NaN share columns in scene table.
10. A11y/colour: viridis/cividis-like ramps with dB legend on map; do not rely on chip colour alone (add text/icon); machine-readable licence (SPDX/CC0 id per layer in manifest); check contrast of .muted/.small text on cards.
Also: placeholder badges must stay; layer 'limits' text is honest but long, put in expandable row; mandal Yanam row is labelled UT - good, keep.
