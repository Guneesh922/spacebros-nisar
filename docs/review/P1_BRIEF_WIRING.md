# P1 brief and data bundle: wiring for dash.js, index.html, dash.css

Module: `app/dashboard-mockup/js/export.js` (`window.SpacebrosExport`), zip library `app/vendor/fflate-0.8.2.min.js` (global `fflate`).
Both are finished and tested (`tools/tests/export_node_test.js`, `tools/tests/test_export.py`). The edits below are the only things left. They were NOT applied (another agent owns dash.js, dash.css, index.html).

API (all return Promises except `download`):
- `SpacebrosExport.build(ctx, opts)` -> `{ briefHtml, briefName, files:{name->string}, rows, mode }` (async because the map crop loads an image).
- `SpacebrosExport.zip(ctx, opts)` -> `Blob` (`blob.zipName` holds the file name). `SpacebrosExport.download(blob, name)` saves it.
- `SpacebrosExport.openBrief(ctx, opts)` -> `{ opened, url, name, blob }`. **Call it directly inside the click handler**: it opens the new tab before any async work so the popup blocker allows it. If `opened` is false the tab was blocked: show a download link for `url` / `name`.
- `ctx` is read only: `{ rank, mandals, manifest, catalog, cfg, story, findings, events, date, mandalName, classImageUrl, pageUrl }`.

Zip holds 5 files: brief HTML, `mandals_<date>.csv`, `mandals_<date>.geojson`, `findings_<date>.json` (only when the findings file for that date is loaded), `README.txt`.

## 1. index.html: two script tags before dash.js

```html
<script src="../vendor/fflate-0.8.2.min.js"></script>
<script src="js/export.js"></script>
<script src="js/dash.js"></script>
```
Keep `findings.js` where it is. No other change.

## 2. dash.js

### 2a. Findings of the selected pass
`exportCtx` needs the findings of the date the brief is for, not only `X.latest`. Add a small cache next to the other loaders (the `FD` constant already points at `../../data/processed/findings/`):

```js
  /* ---------- brief and data bundle (js/export.js) ---------- */
  var findingsBy = {};
  function findingsFor(date) {
    if (!date) return Promise.resolve(null);
    if (findingsBy[date] !== undefined) return Promise.resolve(findingsBy[date]);
    return soft(FD + date + '.json').then(function (j) { findingsBy[date] = j; return j; });
  }
```
(`soft()` already exists and returns null on a 404.)

### 2b. exportCtx (inside the existing `window.__spacebros = {...}` object, line ~171)
`exportCtx` is synchronous and returns the current data. The findings are filled in by the button handler (2c) before the call.

```js
    window.__spacebros = {
      story: function () { return X.story; },
      setStory: function (s) { X.story = s; buildHappened(); if (S.sel) selectMandal(S.sel, {}); },
      exportCtx: function (date, mandal, findings) {
        var d = date || shareDate();
        var id = classId(d);                       // class PNG layer of that date (same file naming as the map)
        return {
          rank: X.rank, mandals: X.mandals, manifest: X.manifest, catalog: X.catalog, cfg: X.cfg, story: X.story,
          findings: findings || null, events: X.events, date: d,
          mandalName: mandal === undefined ? S.sel : mandal,   // pass null for the area summary
          classImageUrl: id && X.layers[id] ? '../../' + X.layers[id].png : null,
          pageUrl: pageUrl()
        };
      }
    };
```
(Keep whatever else the object already has. `pageUrl()` exists, line ~1078. The class PNG path is `data/web/class_YYYYMMDD_new_water.png`, relative to `app/dashboard-mockup/`, hence the `../../`. Use the same prefix the map layer code uses if it differs.)

Which date: `shareDate()` is the coast day shown in the flood-share view. On a sea pass or in the eye mode there is no ranking for that date, so use `shareDate()` (newest coast day with numbers) and say so in the message (2c does).

### 2c. Button handler with busy state and popup fallback

```js
  var exportBusy = false;
  function exportMsg(html) { var m = $('#bx-msg'); if (m) m.innerHTML = html; }
  function exportRun(kind) {                       // kind: 'zip' | 'open'
    if (exportBusy) return;
    if (!window.SpacebrosExport) { exportMsg('The download tool did not load. Reload the page and try again.'); return; }
    var date = shareDate(), mandal = S.sel || null;
    exportBusy = true;
    var btns = document.querySelectorAll('[data-bx]');
    btns.forEach(function (b) { b.disabled = true; b.setAttribute('aria-busy', 'true'); });
    exportMsg('Preparing the ' + (kind === 'zip' ? 'bundle' : 'brief') + ' for ' + esc(mandal || 'the area') + ', ' + esc(dshort(date)) + '...');
    // openBrief opens its tab synchronously, so call it before any await
    var p;
    if (kind === 'open') {
      // start the tab now; findings are optional for the brief itself, so use the copy already cached (or none)
      p = SpacebrosExport.openBrief(window.__spacebros.exportCtx(date, mandal, findingsBy[date] || null)).then(function (r) {
        if (r.opened) exportMsg('The brief is open in a new tab. Use Print there to save it as PDF.');
        else exportMsg('Your browser blocked the new tab. <a href="' + r.url + '" download="' + esc(r.name) + '">Download the brief</a> instead.');
      });
    } else {
      p = findingsFor(date).then(function (f) {
        return SpacebrosExport.zip(window.__spacebros.exportCtx(date, mandal, f));
      }).then(function (blob) {
        SpacebrosExport.download(blob, blob.zipName);
        exportMsg('Downloaded ' + esc(blob.zipName) + ' (brief, table, map file, findings, README).');
      });
    }
    p.catch(function (e) { console.warn(e); exportMsg('The file could not be made. Try again, or use the CSV in the table above.'); })
      .then(function () { exportBusy = false; btns.forEach(function (b) { b.disabled = false; b.removeAttribute('aria-busy'); }); });
  }
```
Note: if you want findings in the "open" brief too, call `findingsFor(date)` once when the Data tab is built (warm the cache) so `findingsBy[date]` is filled by the time of the click; that keeps `openBrief` synchronous inside the click.

Warm the cache: in the Data-tab build function add `findingsFor(shareDate());`.

### 2d. Markup: Data tab, mandals card and the "This view" card
Place in the mandals card (Data tab, where the existing CSV button lives, near line ~1212) and, if wanted, in `buildDayCard()` / `dlBlock()` (Downloads card):

```js
'<div class="bx">' +
  '<button type="button" class="btn" data-bx="zip">Download brief and data (zip)</button>' +
  '<button type="button" class="btn btn--ghost" data-bx="open">Open brief (print)</button>' +
  '<p class="small muted" id="bx-msg" role="status" aria-live="polite"></p>' +
'</div>'
```
Use the button classes the page already uses (replace `btn` / `btn--ghost` with the existing names; check the CSV button next to it).

Bind once after the card is in the DOM (or with the existing delegated click handler):

```js
document.addEventListener('click', function (e) {
  var b = e.target.closest && e.target.closest('[data-bx]');
  if (b) exportRun(b.getAttribute('data-bx'));
});
```
The handler runs `exportRun` synchronously in the click, so `window.open` inside `openBrief` counts as user initiated.

Behaviour to keep: the brief is for the selected mandal (`S.sel`) on `shareDate()`. With no mandal selected, pass `null` for `mandal` to get the area summary (a third link "Area summary" is optional).

## 3. dash.css (about 12 lines, use existing tokens)

```css
.bx { display: flex; flex-wrap: wrap; gap: var(--s-2); align-items: center; margin-top: var(--s-3); }
.bx .btn { min-height: var(--touch); }
.bx .btn[disabled] { opacity: .6; cursor: progress; }
.bx .btn[aria-busy="true"]::after { content: ""; display: inline-block; width: 12px; height: 12px; margin-left: 8px; border: 2px solid currentColor; border-right-color: transparent; border-radius: 50%; animation: bxspin .8s linear infinite; vertical-align: -2px; }
.bx p { flex: 1 0 100%; margin: 0; }
@keyframes bxspin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .bx .btn[aria-busy="true"]::after { animation: none; } }
@media (max-width: 480px) { .bx .btn { flex: 1 0 100%; } }   /* 375 px: full-width stacked buttons, 44 px tap targets */
```

## 4. Mobile (375 px)
- Buttons stack full width (CSS above), tap target 44 px, message under them in `#bx-msg` (aria-live).
- The generated brief has `<meta name="viewport" content="width=794">`, so a phone shows the whole A4 page scaled to fit; pinch to zoom. Print preview is one A4 page on desktop.
- Download on iOS Safari may open the zip in a preview; that is normal.

## 5. Check after wiring
1. `#tab=data&mode=share&d=2026-11-09`, select Nidadavole, press both buttons; unzip: 5 files, CSV rows 66 (54 ranked).
2. `d=2026-10-28`: headline "No mandal looks probably flooded in this radar picture."
3. Block pop-ups: the message shows the download link.
4. Chrome print preview of the brief: 1 page, background colours kept. (Not yet checked in a browser, see report.)
5. Run `.venv/bin/python tools/tests/test_export.py` and the other tests.

## Notes for the team
- Licence label conflict: `dash.js` `DL` list and `mandal_rank.json` `boundaries_credit` still say ODbL-1.0; the brief and README use CC BY 4.0 (geoboundaries.org). Change the `dash.js` label in the same edit.
- The SpaceBros derived products have no licence in the manifest; the README only says "Derived by SpaceBros from NISAR data". The team must pick one.
- `findings_<date>.json` is copied unchanged, so it still holds the findings file's own caveat fields; the brief and README do not use them.
