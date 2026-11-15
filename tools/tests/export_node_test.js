/* Node test for app/dashboard-mockup/js/export.js with the REAL data files. Plain asserts.  node tools/tests/export_node_test.js */
'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const ROOT = path.resolve(__dirname, '..', '..');
const X = require(path.join(ROOT, 'app/dashboard-mockup/js/export.js'));
const fflate = require(path.join(ROOT, 'app/vendor/fflate-0.8.2.min.js'));
const J = (p) => JSON.parse(fs.readFileSync(path.join(ROOT, p), 'utf8'));

const rank = J('data/processed/mandal_rank.json'), mandals = J('data/processed/mandals.geojson'), manifest = J('data/processed/manifest.json');
const catalog = J('data/h5/catalog.json'), cfg = J('config/areas.json'), events = J('data/processed/events.json').events;
// story.json is a build output written AFTER the tests (and absent in a dry run): read it like the page does, with findings/latest.json (committed) as the fallback. export.js only uses story.area_id.
const story = fs.existsSync(path.join(ROOT, 'data/web/story.json')) ? J('data/web/story.json') : J('data/processed/findings/latest.json');
const FOOT = 'Built by team SpaceBros for the NASA Space Apps Challenge 2026. Not an official NASA, ISRO, IMD or government product, and not a warning service.';
const NOW = new Date('2026-11-15T09:00:00Z');
// stub canvas: tiny valid PNG data URI, records the requested crop
const crops = [];
const cropFn = (url, frac) => { crops.push({ url, frac }); return 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=='; };

function ctxFor(date, mandalName) {
  return { rank, mandals, manifest, catalog, cfg, story, events, findings: J('data/processed/findings/' + date + '.json'), date, mandalName,
    classImageUrl: '../../data/web/class_' + date.replace(/-/g, '') + '_new_water.png', pageUrl: 'https://example.invalid/app/dashboard-mockup/#tab=data' };
}
function badLetters(s) { return [...new Set([...s].filter((c) => /\p{L}/u.test(c) && !/\p{Script=Latin}/u.test(c)))]; }
function parseCsv(t) {
  const out = []; let row = [], cur = '', q = false;
  for (let i = 0; i < t.length; i++) {
    const c = t[i];
    if (q) { if (c === '"') { if (t[i + 1] === '"') { cur += '"'; i++; } else q = false; } else cur += c; }
    else if (c === '"') q = true; else if (c === ',') { row.push(cur); cur = ''; } else if (c === '\n') { row.push(cur); out.push(row); row = []; cur = ''; } else cur += c;
  }
  return out;
}
const FORBID = /provisional|early data|weak signal|sample|lower confidence/i;
const longest = (d) => rank.by_date[d].rows.reduce((a, b) => (b.mandal.length > a.mandal.length ? b : a)).mandal;

let n = 0, failed = 0;
async function test(name, fn) {
  try { await fn(); n++; console.log('PASS  ' + name); } catch (e) { n++; failed++; console.log('FAIL  ' + name); console.log(e.stack); }
}

(async () => {
  const cases = [['2026-10-28', 'Nidadavole'], ['2026-11-09', 'Nidadavole'], ['2026-11-09', longest('2026-11-09')], ['2026-11-09', 'Jaggampeta'], ['2026-10-28', null], ['2026-11-09', null], ['2026-11-09', 'Yanam Taluk'], ['2026-11-09', 'Yelamanchili']];
  const built = {};
  for (const [d, m] of cases) built[d + '|' + m] = await X.build(ctxFor(d, m), { cropFn, now: NOW });

  await test('every case builds 5 files with the expected names', () => {
    for (const [d, m] of cases) {
      const b = built[d + '|' + m];
      const want = ['matsya_' + (m ? m.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') : 'area') + '_' + d + '.html', 'mandals_' + d + '.csv', 'mandals_' + d + '.geojson', 'findings_' + d + '.json', 'README.txt'];
      assert.deepStrictEqual(Object.keys(b.files).sort(), want.slice().sort());
      assert.strictEqual(b.briefName, want[0]);
    }
  });

  await test('CSV header equals README column list; all rows present incl. flagged; numbers verbatim', () => {
    for (const d of ['2026-10-28', '2026-11-09']) {
      const b = built[d + '|Nidadavole'];
      const t = parseCsv(b.files['mandals_' + d + '.csv']); const head = t[0];
      const rd = b.files['README.txt'].split('\n');
      const i0 = rd.findIndex((l) => l.startsWith('COLUMNS (same order'));
      const cols = []; for (let i = i0 + 1; i < rd.length && rd[i].startsWith('  '); i++) cols.push(rd[i].trim().split(':')[0]);
      assert.deepStrictEqual(head, cols);
      assert.deepStrictEqual(head, X.activeColumns(rank.by_date[d].rows).map((c) => c.key));
      const rows = rank.by_date[d].rows; assert.strictEqual(t.length - 1, rows.length);
      const byName = {}; t.slice(1).forEach((r) => { byName[r[0]] = r; });
      let ranked = 0;
      rows.forEach((r) => {
        const line = byName[r.mandal]; assert.ok(line, 'missing ' + r.mandal); assert.strictEqual(line.length, head.length);
        assert.strictEqual(line[head.indexOf('district')], r.district);
        const rw = line[head.indexOf('rank_water')];
        if (r.rank_water != null) { ranked++; assert.strictEqual(rw, String(r.rank_water)); assert.ok(!line[head.indexOf('flag')]); } else { assert.strictEqual(rw, ''); assert.ok(line[head.indexOf('flag')].length > 0, r.mandal + ' flag'); }
        ['water_pct', 'water_err', 'normal_water_pct', 'water_km2', 'flooded_km2', 'change_vs_normal_pp', 'coverage_pct', 'area_km2'].forEach((k) => {
          const v = line[head.indexOf(k)]; assert.ok(/^-?\d+(\.\d+)?$/.test(v), k + '=' + v); assert.strictEqual(Number(v), r[k]);
        });
      });
      assert.strictEqual(ranked, rank.by_date[d].n_ranked);
      assert.ok(rows.some((r) => r.rank_water == null), 'a flagged-not-ranked mandal exists');
    }
  });

  await test('number formats in the brief (Nidadavole 9 Nov: 10.9 +/- 1.6 %, rank 1 of 54)', () => {
    const h = built['2026-11-09|Nidadavole'].briefHtml, r = rank.by_date['2026-11-09'].rows.find((x) => x.mandal === 'Nidadavole');
    assert.ok(h.includes('10.9 <small>&plusmn; 1.6</small>'), 'water share');
    assert.ok(h.includes('1 <small>of 54</small>'));
    assert.ok(h.includes(r.water_km2.toFixed(1)) || h.includes(r.water_km2.toFixed(2)));
    assert.ok(/\+\d+\.\d <small>points/.test(h));
    assert.ok(h.includes('Nidadavole') && h.includes('West Godavari'));
    const h28 = built['2026-10-28|Nidadavole'].briefHtml;
    assert.ok(h28.includes('28 Oct 2026') && h28.includes('track 55') && h28.includes('HH + HV'));
  });

  await test('headline comes from the findings file for that date', () => {
    assert.ok(built['2026-10-28|Nidadavole'].briefHtml.includes('No mandal looks probably flooded in this radar picture.'));
    assert.ok(built['2026-11-09|Nidadavole'].briefHtml.includes('More land is probably flooded than on the last radar pass.'));
  });

  await test('brief: English only, footer, NISAR credit, boundaries, no banned words, no external requests', () => {
    for (const k of Object.keys(built)) {
      const b = built[k], h = b.briefHtml;
      assert.deepStrictEqual(badLetters(h), [], k);
      assert.ok(h.includes(FOOT), k); assert.ok(h.includes('NISAR L2 GCOV, NASA/JPL-Caltech and ISRO, via ASF DAAC (NASA Earthdata)'), k);
      assert.ok(h.includes('Derived by SpaceBros from NISAR data') && h.includes('geoBoundaries') && h.includes('ODbL 1.0'));
      assert.ok(!FORBID.test(h), k + ' banned word: ' + (h.match(FORBID) || [])[0]);
      assert.ok(!/(src|href)="https?:/i.test(h) && !/@import|url\(http/i.test(h), 'no external requests');
      assert.ok(h.includes('@page{size:A4;margin:0}') && h.includes('print-color-adjust:exact'));
      assert.ok(h.includes('Generated 15 Nov 2026, 14:30 IST'), 'stamp');
      assert.ok(h.includes('https://example.invalid/app/dashboard-mockup/#tab=data'));
      assert.ok(h.includes('Matsya'));
      assert.ok(Buffer.byteLength(h) < 300 * 1024, 'size ' + Buffer.byteLength(h));
      const rd = b.files['README.txt'];
      assert.deepStrictEqual(badLetters(rd), []); assert.ok(!/[^\x00-\x7F]/.test(rd), 'README ascii'); assert.ok(!FORBID.test(rd), k + ' README banned');
      assert.ok(rd.includes(FOOT) && rd.includes('ODbL 1.0') && rd.includes('NISAR L2 GCOV') && rd.includes('lgdirectory.gov.in'));
      assert.ok(!/Esri/.test(h + rd));
    }
  });

  await test('long mandal name: map + one-page structure present, class set for long names', () => {
    const nm = longest('2026-11-09'); const h = built['2026-11-09|' + nm].briefHtml;
    assert.ok(nm.length >= 15); assert.ok(h.includes(nm.replace(/&/g, '&amp;')));
    assert.ok(h.includes('<svg class="map"') && h.includes('<image href="data:image/png') && h.includes('class="sel"'));
    assert.ok(h.includes('class="scale-t"') && /\d+ km<\/text>/.test(h));
    const syn = JSON.parse(JSON.stringify(rank)); const row = syn.by_date['2026-11-09'].rows[0]; const long = 'Extraordinarily Long Mandal Name '.repeat(3).trim(); row.mandal = long;
    const p = X.prepare(Object.assign(ctxFor('2026-11-09', long), { rank: syn }), { now: NOW });
    assert.ok(X.briefHtml(p, null).includes('class="xlong"'));
  });

  await test('flagged-not-ranked mandal shows Not ranked and the flag text, keeps its numbers', () => {
    const h = built['2026-11-09|Jaggampeta'].briefHtml;
    assert.ok(h.includes('Not ranked') && h.includes('&lt;50% of mandal inside coast footprint'));
    assert.ok(h.includes('Top ranked mandals, for comparison'));
  });

  await test('Yanam Taluk (district not matched in polygons) still gets its outline; Yelamanchili matches the right polygon', () => {
    assert.ok(built['2026-11-09|Yanam Taluk'].briefHtml.includes('class="sel"'));
    const idx = X.featIndex(mandals.features);
    const f = X.findFeat(idx, 'Yelamanchili', 'West Godavari'); assert.strictEqual(f.properties.district, 'West Godavari');
    const g = JSON.parse(built['2026-11-09|Yelamanchili'].files['mandals_2026-11-09.geojson']);
    const hit = g.features.filter((x) => x.properties.mandal === 'Yelamanchili'); assert.strictEqual(hit.length, 1); assert.strictEqual(hit[0].properties.district, 'West Godavari');
    assert.deepStrictEqual(hit[0].geometry, f.geometry);
  });

  await test('area summary: top mandals by open water, no mandal-only parts', () => {
    const h = built['2026-11-09|null'].briefHtml, top = rank.by_date['2026-11-09'].rows.filter((r) => r.rank_water != null).sort((a, b) => a.rank_water - b.rank_water);
    assert.ok(h.includes('Area brief') && h.includes('Godavari delta')); assert.ok(h.includes('Mandals with the most likely new open water'));
    for (const r of top.slice(0, 10)) assert.ok(h.includes('<td>' + r.mandal + '</td>'), r.mandal);
    assert.ok(!h.includes('Mandals next to this one')); assert.ok(h.includes('84 <small>km&sup2;</small>'));
    assert.ok(built['2026-10-28|null'].briefHtml.includes('Area brief'));
    assert.ok(built['2026-11-09|null'].briefName === 'matsya_area_2026-11-09.html');
  });

  await test('geojson: every ranked mandal has a polygon with the CSV columns as properties', () => {
    for (const d of ['2026-10-28', '2026-11-09']) {
      const g = JSON.parse(built[d + '|Nidadavole'].files['mandals_' + d + '.geojson']); assert.strictEqual(g.type, 'FeatureCollection');
      const names = new Set(g.features.map((f) => f.properties.mandal));
      rank.by_date[d].rows.forEach((r) => assert.ok(names.has(r.mandal), 'polygon for ' + r.mandal));
      g.features.forEach((f) => assert.ok(/Polygon/.test(f.geometry.type)));
      assert.deepStrictEqual(Object.keys(g.features[0].properties), X.activeColumns(rank.by_date[d].rows).map((c) => c.key));
    }
  });

  await test('findings file is verbatim; crop request is inside the class PNG', () => {
    const b = built['2026-11-09|Nidadavole'];
    assert.deepStrictEqual(JSON.parse(b.files['findings_2026-11-09.json']), J('data/processed/findings/2026-11-09.json'));
    assert.ok(crops.length >= 8);
    crops.forEach((c) => { const f = c.frac; assert.ok(f.x0 >= 0 && f.y0 >= 0 && f.x1 <= 1 && f.y1 <= 1 && f.x1 > f.x0 && f.y1 > f.y0); });
  });

  await test('zip round-trips with fflate.unzipSync and holds the 5 files', async () => {
    const z = await X.zipBytes(ctxFor('2026-11-09', 'Nidadavole'), { cropFn, now: NOW, fflate });
    const u = fflate.unzipSync(z.bytes); const names = Object.keys(u).sort(); assert.strictEqual(names.length, 5);
    const b = built['2026-11-09|Nidadavole'];
    names.forEach((k) => assert.strictEqual(Buffer.from(u[k]).toString('utf8'), b.files[k]));
    assert.strictEqual(z.name, 'matsya_nidadavole_2026-11-09.zip'); assert.ok(z.bytes.length < 400 * 1024, 'zip ' + z.bytes.length);
    const blob = await X.zip(ctxFor('2026-11-09', null), { cropFn, now: NOW, fflate }); assert.ok(blob.size > 1000);
  });

  await test('missing inputs: no findings, no class image, unknown mandal, date without numbers -> no invented numbers', async () => {
    const c = ctxFor('2026-11-09', 'Nidadavole'); c.findings = null; c.classImageUrl = null;
    const b = await X.build(c, { cropFn, now: NOW });
    assert.ok(!b.files['findings_2026-11-09.json'] && Object.keys(b.files).length === 4); assert.ok(b.briefHtml.includes('Mandal outlines only'));
    const u = await X.build(ctxFor('2026-11-09', 'Nowhere'), { cropFn, now: NOW }); assert.ok(u.briefHtml.includes('No numbers for this mandal in this pass.'));
    const c3 = ctxFor('2026-11-09', 'Nidadavole'); c3.date = '2026-12-01'; c3.findings = null; const e = await X.build(c3, { cropFn, now: NOW }); assert.ok(e.briefHtml.includes('not available')); assert.strictEqual(e.files['mandals_2026-12-01.csv'].trim().split('\n').length, 1);
  });

  await test('area brief with a worst-case 600 px crop (about 110 KB data URI, measured with PIL on the real PNG) stays under 300 KB', async () => {
    const big = await X.build(ctxFor('2026-11-09', null), { cropFn: () => 'data:image/png;base64,' + 'A'.repeat(110000), now: NOW });
    assert.ok(Buffer.byteLength(big.briefHtml) < 300 * 1024, 'size ' + Buffer.byteLength(big.briefHtml));
  });

  console.log(n + ' tests, ' + failed + ' failed');
  process.exit(failed ? 1 : 0);
})();
