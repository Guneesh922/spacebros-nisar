/* export.js: one-page A4 brief + data bundle (zip). Classic script, also loadable under node (module.exports).
   window.SpacebrosExport = { build, zip, zipBytes, openBrief, download, prepare, briefHtml, csv, geojson, readme, COLUMNS, ... }
   ctx (read-only, exposed by the dashboard as window.__spacebros.exportCtx()):
     { rank, mandals, manifest, catalog, cfg, story, findings, events, date, mandalName|null, classImageUrl, pageUrl }
   build(ctx, opts) returns a Promise of { briefHtml, briefName, files:{name->string}, rows, mode } because the map crop is async.
   opts: { cropFn(url, frac, o) -> uri | {uri} | Promise  (default: canvas crop in the browser, none under node),
           fflate (default window.fflate), now (Date, default new Date()), classBounds [[S,W],[N,E]] }
   Never invents numbers: a missing input leaves that part out. No external requests: the page is self-contained.
   The file is ASCII only (entities in the HTML, escapes in strings). */
(function (root) {
  'use strict';

  var FOOTER = 'Built by team SpaceBros for the NASA Space Apps Challenge 2026. Not an official NASA, ISRO, IMD or government product, and not a warning service.';
  var NISAR_CREDIT = 'NISAR L2 GCOV, NASA/JPL-Caltech and ISRO, via ASF DAAC (NASA Earthdata)';
  var DERIVED_CREDIT = 'Derived by SpaceBros from NISAR data';
  var BOUNDARY_CREDIT = 'Mandal boundaries: geoBoundaries gbOpen (geoboundaries.org), boundary year 2018, licence ODbL 1.0';
  var BOUNDARY_CITE = 'Runfola et al. 2020, PLoS ONE 15(4): e0231866';
  var DISTRICT_SOURCE = 'District names: 2022 Andhra Pradesh district lists (AP district portals and lgdirectory.gov.in, as recorded in data/sources.yaml, item DOCS_DISTRICTS)';
  var NISAR_LICENCE = 'NASA Earth science data, open by default (CC0 unless marked); follow ASF DAAC terms';
  var BAN = /provisional|early data|weak signal|sample|lower confidence/i;
  var KM_PER_DEG = 111.195;
  var MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

  /* one table: CSV header, GeoJSON properties and the README definitions all come from here.
     src = key in mandal_rank.json rows (defaults to key). A column is used only if the data has it. */
  var COLUMNS = [
    { key: 'mandal', type: 'text', def: 'Mandal name (geoBoundaries name).' },
    { key: 'district', type: 'text', def: 'District, from the 2022 Andhra Pradesh district lists.' },
    { key: 'rank_water', type: 'int', def: 'Rank by water_pct among the ranked mandals of this pass (1 = highest share of open water). Blank = not ranked, the reason is in flag.' },
    { key: 'rank_total', src: 'rank', type: 'int', def: 'Rank by total_pct (open water plus wet crops) among the ranked mandals. Blank = not ranked.' },
    { key: 'water_pct', type: 'num', def: 'Likely new open water: percent of the mandal\'s valid, non-permanent-water land pixels.' },
    { key: 'water_err', type: 'num', def: 'Error on water_pct in percentage points: the largest shift when the change threshold moves by one sigma either way.' },
    { key: 'crops_pct', type: 'num', def: 'Likely wet or flooded crops: percent of the same pixels.' },
    { key: 'crops_err', type: 'num', def: 'Error on crops_pct in percentage points (same rule as water_err).' },
    { key: 'total_pct', type: 'num', def: 'water_pct plus crops_pct, percent.' },
    { key: 'total_err', type: 'num', def: 'Error on total_pct in percentage points.' },
    { key: 'normal_water_pct', type: 'num', def: 'Likely open water in the normal fortnight (see HOW TO READ THE NUMBERS), percent, same thresholds.' },
    { key: 'normal_pct', type: 'num', def: 'Open water plus wet crops in the normal fortnight, percent.' },
    { key: 'change_vs_normal_pp', type: 'num', def: 'total_pct minus normal_pct, in percentage points.' },
    { key: 'water_change_vs_normal_pp', type: 'num', def: 'water_pct minus normal_water_pct, in percentage points.' },
    { key: 'water_km2', type: 'num', def: 'Area of likely new open water, square km (share times area_km2).' },
    { key: 'crops_km2', type: 'num', def: 'Area of likely wet or flooded crops, square km.' },
    { key: 'flooded_km2', type: 'num', def: 'water_km2 plus crops_km2, square km.' },
    { key: 'area_km2', type: 'num', def: 'Valid, non-permanent-water land the radar saw inside the mandal, square km.' },
    { key: 'coverage_pct', type: 'num', def: 'Valid land share of the mandal inside the radar grid, percent.' },
    { key: 'frac_in_footprint', type: 'num', def: 'Fraction (0 to 1) of the mandal inside the radar picture of this pass.' },
    { key: 'flag', type: 'text', def: 'Why the mandal is listed but not ranked (blank for ranked mandals).' }
  ];

  /* ---------------- small helpers ---------------- */
  function esc(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }
  function slug(s) { return String(s || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'x'; }
  function clean(s) { s = s == null ? '' : String(s).trim(); return s && !BAN.test(s) ? s : ''; }
  function isNum(v) { return typeof v === 'number' && isFinite(v); }
  function dshort(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso || '');
    return m ? (+m[3]) + ' ' + MONTHS[+m[2] - 1] + ' ' + m[1] : '';
  }
  /* any ISO UTC time or Date -> "9 Nov 2026, 05:31 IST" (UTC+5:30, no Intl) */
  function istText(t) {
    var d = t instanceof Date ? t : new Date(t);
    if (isNaN(d.getTime())) return '';
    var s = new Date(d.getTime() + 330 * 60000);
    function p(n) { return (n < 10 ? '0' : '') + n; }
    return s.getUTCDate() + ' ' + MONTHS[s.getUTCMonth()] + ' ' + s.getUTCFullYear() + ', ' + p(s.getUTCHours()) + ':' + p(s.getUTCMinutes()) + ' IST';
  }
  function compactDate(c) { return /^\d{8}$/.test(c || '') ? dshort(c.slice(0, 4) + '-' + c.slice(4, 6) + '-' + c.slice(6, 8)) : String(c || ''); }
  function f1(v) { return isNum(v) ? (Math.abs(v) < 1 ? v.toFixed(2) : v.toFixed(1)) : ''; }
  function fkm(v) { return isNum(v) ? (Math.abs(v) < 10 ? v.toFixed(2) : v.toFixed(1)) : ''; }
  function fsigned(v) { return isNum(v) ? (v > 0 ? '+' : '') + f1(v) : ''; }
  function shortDist(d) { return String(d || '').replace(/\s*\(.*$/, '').replace(/^Dr\.\s*B\.R\.\s*Ambedkar\s+/, ''); }

  /* ---------------- data selection ---------------- */
  function rowsFor(rank, date) {
    if (!rank || !date) return [];
    var bd = rank.by_date && rank.by_date[date];
    var rows = bd && bd.rows ? bd.rows : (rank.latest_date === date ? (rank.rows || []).concat(rank.flagged_not_ranked || []) : []);
    return rows.slice().sort(function (a, b) {
      var ra = isNum(a.rank_water), rb = isNum(b.rank_water);
      if (ra && rb) return a.rank_water - b.rank_water;
      if (ra !== rb) return ra ? -1 : 1;
      return String(a.mandal).localeCompare(String(b.mandal));
    });
  }
  function activeColumns(rows) {
    return COLUMNS.filter(function (c) {
      var s = c.src || c.key;
      return c.key === 'mandal' || c.key === 'district' || rows.some(function (r) { return r[s] !== undefined; });
    });
  }
  function cell(r, c) { var v = r[c.src || c.key]; return v === undefined || v === null ? null : v; }

  function featIndex(feats) {
    var by = {};
    (feats || []).forEach(function (f) { var n = (f.properties || {}).name; (by[n] = by[n] || []).push(f); });
    return by;
  }
  /* name AND district; when no district matches, a name that exists once is accepted (Yanam Taluk has no district in the polygons) */
  function findFeat(idx, name, district) {
    var l = idx[name] || [], i;
    for (i = 0; i < l.length; i++) if ((l[i].properties || {}).district === district) return l[i];
    var blank = l.filter(function (f) { return !(f.properties || {}).district; });
    if (blank.length === 1 && l.length === 1) return blank[0];
    return l.length === 1 ? l[0] : null;
  }

  /* ---------------- CSV / GeoJSON / README ---------------- */
  function csvCell(v) {
    if (v === null || v === undefined) return '';
    if (typeof v === 'number') return String(v);
    v = String(v);
    return /[",\r\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v;
  }
  function csv(rows, cols) {
    cols = cols || activeColumns(rows);
    var out = [cols.map(function (c) { return c.key; }).join(',')];
    rows.forEach(function (r) { out.push(cols.map(function (c) { return csvCell(cell(r, c)); }).join(',')); });
    return out.join('\n') + '\n';
  }
  function geojson(rows, feats, cols) {
    cols = cols || activeColumns(rows);
    var idx = featIndex(feats), out = [];
    rows.forEach(function (r) {
      var f = findFeat(idx, r.mandal, r.district);
      if (!f) return;
      var p = {};
      cols.forEach(function (c) { p[c.key] = cell(r, c); });
      out.push({ type: 'Feature', properties: p, geometry: f.geometry });
    });
    return JSON.stringify({ type: 'FeatureCollection', features: out });
  }

  function pickSource(manifest, id) {
    var s = manifest && manifest.sources ? manifest.sources : [];
    for (var i = 0; i < s.length; i++) if (s[i].id === id) return s[i];
    return null;
  }

  function passInfo(ctx) {
    var date = ctx.date, rank = ctx.rank || {}, bd = (rank.by_date || {})[date] || {};
    var sc = ((ctx.catalog && ctx.catalog.scenes) || []).filter(function (s) { return s.date === date && String(s.role || '').toUpperCase() === 'COAST'; })[0] || null;
    var fp = ctx.findings && ctx.findings.pass && ctx.findings.pass.date === date ? ctx.findings.pass : null;
    var lay = ((ctx.manifest && ctx.manifest.layers) || []).filter(function (l) { return l.type === 'nisar' && l.date === date && /coast/.test(l.id || '') && l.pol; })[0] || null;
    var pols = sc && sc.pols && sc.pols.length ? sc.pols.join(' + ') : (lay ? String(lay.pol) : '');
    var track = sc && sc.track != null ? sc.track : (fp && fp.track != null ? fp.track : (lay && lay.track != null ? lay.track : null));
    var time = (fp && clean(fp.time_ist_text)) || (bd.start_utc ? istText(bd.start_utc) : (sc && sc.start_utc ? istText(sc.start_utc) : ''));
    return { date: date, dateText: dshort(date), time: time, track: track, pols: pols };
  }

  function creditLines(ctx, info) {
    var nis = pickSource(ctx.manifest, 'asf_nisar_l');
    var credit = (nis && nis.credit_line) || NISAR_CREDIT;
    var scene = [info.dateText, info.track != null ? 'track ' + info.track : '', info.pols ? 'polarisation ' + info.pols : ''].filter(Boolean).join(', ');
    return { nisar: credit + (scene ? ' (' + scene + ')' : ''), derived: DERIVED_CREDIT, boundaries: BOUNDARY_CREDIT, districts: DISTRICT_SOURCE,
      licence: (nis && nis.licence) || NISAR_LICENCE };
  }

  function readme(m) {
    var L = [], cols = m.cols, nm = m.names, info = m.info, cr = m.credits, rk = m.ctx.rank || {};
    function hr(t) { L.push(''); L.push(t); }
    L.push(m.title + ' - download bundle');
    L.push('Pass: ' + info.dateText + (info.time ? ' (' + info.time + ')' : '') + ', NISAR L-band' + (info.track != null ? ', track ' + info.track : '') + (info.pols ? ', polarisation ' + info.pols : ''));
    L.push('Selected: ' + (m.row ? m.row.mandal + ' (' + m.row.district + ')' : m.mandalName ? m.mandalName : m.areaName + ' (area summary)'));
    L.push('Generated: ' + istText(m.now));
    if (m.pageUrl) L.push('Page: ' + m.pageUrl);
    hr('FILES');
    L.push('  ' + nm.brief + '  One-page A4 brief. Open it in a browser, print it or save it as PDF. Self-contained, no internet needed.');
    L.push('  ' + nm.csv + '  One row per mandal (' + m.rows.length + ' rows, ' + m.rankedN + ' ranked, the rest listed with a flag).');
    L.push('  ' + nm.geojson + '  The same rows as GeoJSON polygons; the columns below are the properties.');
    if (nm.findings) L.push('  ' + nm.findings + '  The findings file the dashboard uses for this pass, unchanged.');
    L.push('  README.txt  This file.');
    hr('HOW TO READ THE NUMBERS');
    L.push('  Shares are percent of the valid, non-permanent-water land pixels (20 m grid) inside each mandal. Errors are percentage points.');
    L.push('  Area is square km (km2). Changes against the normal fortnight are percentage points (pp).');
    if (rk.normal_period) L.push('  Normal fortnight: ' + dshort(rk.normal_period[0]) + ' to ' + dshort(rk.normal_period[1]) + '.');
    var bl = rk.provenance && rk.provenance.baseline_dates;
    if (bl && bl.length) L.push('  Baseline radar dates: ' + bl.map(compactDate).join(' and ') + '.');
    var mt = clean(rk.provenance && rk.provenance.method);
    if (mt) L.push('  Method (from the data file): ' + mt);
    hr('COLUMNS (same order as the header of ' + nm.csv + ')');
    cols.forEach(function (c) { L.push('  ' + c.key + ': ' + c.def); });
    hr('CREDITS AND LICENCES');
    L.push('  Radar data: ' + cr.nisar + '.');
    L.push('  Data licence: ' + cr.licence + '.');
    L.push('  Maps and numbers: ' + cr.derived + '.');
    L.push('  ' + cr.boundaries + '. Please acknowledge geoBoundaries; cite ' + BOUNDARY_CITE + ' in written work.');
    L.push('  ' + cr.districts + '.');
    hr(FOOTER);
    return L.join('\n') + '\n';
  }

  /* ---------------- map geometry (pure) ---------------- */
  function rings(g) {
    var out = [];
    if (!g || !g.coordinates) return out;
    if (g.type === 'Polygon') g.coordinates.forEach(function (r) { out.push(r); });
    else if (g.type === 'MultiPolygon') g.coordinates.forEach(function (p) { p.forEach(function (r) { out.push(r); }); });
    return out;
  }
  function bboxOf(rs) {
    var b = null;
    rs.forEach(function (r) { r.forEach(function (p) {
      if (!b) b = { minLon: p[0], maxLon: p[0], minLat: p[1], maxLat: p[1] };
      else { if (p[0] < b.minLon) b.minLon = p[0]; if (p[0] > b.maxLon) b.maxLon = p[0]; if (p[1] < b.minLat) b.minLat = p[1]; if (p[1] > b.maxLat) b.maxLat = p[1]; }
    }); });
    return b;
  }
  function pathD(rs, c, eps, ox, oy, K) {
    return rs.map(function (r) {
      var pts = [], lx = null, ly = null, i, x, y;
      for (i = 0; i < r.length; i++) {
        x = (r[i][0] * c - ox) * K; y = (-r[i][1] - oy) * K;       // local coordinates (origin at the view corner, scaled): large geographic offsets with tiny sizes do not paint reliably in browsers
        if (lx === null || i === r.length - 1 || Math.abs(x - lx) >= eps * K || Math.abs(y - ly) >= eps * K) { pts.push(x.toFixed(2) + ' ' + y.toFixed(2)); lx = x; ly = y; }
      }
      return 'M' + pts.join('L') + 'Z';
    }).join('');
  }
  function niceKm(maxKm) {
    var c = [0.5, 1, 2, 5, 10, 20, 50, 100], best = c[0];
    c.forEach(function (v) { if (v <= maxKm) best = v; });
    return best;
  }

  /* feats: mandal polygons; target: array of features that frame the map; hi: features drawn thick (own mandal or top mandals) */
  function mapModel(feats, target, hi, bounds, o) {
    var all = [];
    target.forEach(function (f) { all = all.concat(rings(f.geometry)); });
    var b = bboxOf(all);
    if (!b) return null;
    var c = Math.cos(((b.minLat + b.maxLat) / 2) * Math.PI / 180);
    var w = (b.maxLon - b.minLon) * c, h = b.maxLat - b.minLat;
    var pad = o.pad * Math.max(w, h, 0.002);
    var vx = b.minLon * c - pad, vy = -b.maxLat - pad, vw = w + 2 * pad, vh = h + 2 * pad;
    var AR = 1.25;
    if (vw / vh < AR) { var nw = vh * AR; vx -= (nw - vw) / 2; vw = nw; } else { var nh = vw / AR; vy -= (nh - vh) / 2; vh = nh; }
    var win = { minLon: vx / c, maxLon: (vx + vw) / c, maxLat: -vy, minLat: -(vy + vh) };
    var eps = Math.max(vw, vh) / (o.epsDiv || 1000), hiSet = hi.slice(), K = 1000 / vh, ox = vx, oy = vy;
    var nb = [];
    (feats || []).forEach(function (f) {
      if (hiSet.indexOf(f) >= 0) return;
      var bb = bboxOf(rings(f.geometry));
      if (!bb || bb.maxLat < win.minLat || bb.minLat > win.maxLat || bb.maxLon < win.minLon || bb.minLon > win.maxLon) return;
      nb.push(pathD(rings(f.geometry), c, eps, ox, oy, K));
    });
    var hid = hi.map(function (f) { return pathD(rings(f.geometry), c, eps, ox, oy, K); });
    var m = { vb: [0, 0, vw * K, vh * K], K: K, c: c, win: win, nb: nb, hi: hid, widthKm: vw * KM_PER_DEG, raster: null };
    if (bounds && bounds.length === 2) {
      var S = bounds[0][0], W = bounds[0][1], N = bounds[1][0], E = bounds[1][1];
      var lon0 = Math.max(win.minLon, W), lon1 = Math.min(win.maxLon, E), lat0 = Math.max(win.minLat, S), lat1 = Math.min(win.maxLat, N);
      if (lon1 > lon0 && lat1 > lat0) {
        m.raster = { frac: { x0: (lon0 - W) / (E - W), x1: (lon1 - W) / (E - W), y0: (N - lat1) / (N - S), y1: (N - lat0) / (N - S) },
          x: (lon0 * c - ox) * K, y: (-lat1 - oy) * K, w: (lon1 - lon0) * c * K, h: (lat1 - lat0) * K };
      }
    }
    return m;
  }
  function mapSvg(m, uri, label) {
    var v = m.vb, p = [];
    function n(x) { return (+x).toFixed(4); }
    p.push('<svg class="map" xmlns="http://www.w3.org/2000/svg" viewBox="' + v.map(n).join(' ') + '" preserveAspectRatio="xMidYMid meet" role="img" aria-label="' + esc(label) + '">');
    p.push('<rect class="map-bg" x="' + n(v[0]) + '" y="' + n(v[1]) + '" width="' + n(v[2]) + '" height="' + n(v[3]) + '"/>');
    if (uri && m.raster) p.push('<image href="' + uri + '" x="' + n(m.raster.x) + '" y="' + n(m.raster.y) + '" width="' + n(m.raster.w) + '" height="' + n(m.raster.h) + '" preserveAspectRatio="none"/>');
    m.nb.forEach(function (d) { p.push('<path class="nb" fill-rule="evenodd" d="' + d + '"/>'); });
    m.hi.forEach(function (d) { p.push('<path class="halo" fill-rule="evenodd" d="' + d + '"/>'); });
    m.hi.forEach(function (d) { p.push('<path class="sel" fill-rule="evenodd" d="' + d + '"/>'); });
    var km = niceKm(m.widthKm * 0.28), len = km / KM_PER_DEG * m.K, bx = v[0] + v[2] * 0.04, by = v[1] + v[3] * 0.93, fs = v[2] * 0.032;
    p.push('<path class="scale-halo" d="M' + n(bx) + ' ' + n(by) + 'h' + n(len) + 'M' + n(bx) + ' ' + n(by - fs * 0.35) + 'v' + n(fs * 0.7) + 'M' + n(bx + len) + ' ' + n(by - fs * 0.35) + 'v' + n(fs * 0.7) + '"/>');
    p.push('<path class="scale" d="M' + n(bx) + ' ' + n(by) + 'h' + n(len) + 'M' + n(bx) + ' ' + n(by - fs * 0.35) + 'v' + n(fs * 0.7) + 'M' + n(bx + len) + ' ' + n(by - fs * 0.35) + 'v' + n(fs * 0.7) + '"/>');
    p.push('<text class="scale-t" x="' + n(bx) + '" y="' + n(by - fs * 0.6) + '" font-size="' + n(fs) + '">' + km + ' km</text>');
    p.push('</svg>');
    return p.join('');
  }

  /* ---------------- brief html ---------------- */
  var CSS = '@page{size:A4;margin:0}' +
    '*,*::before,*::after{box-sizing:border-box}' +
    'html,body{margin:0;padding:0;-webkit-print-color-adjust:exact;print-color-adjust:exact}' +
    'body{background:#E6EBEA;color:#131E22;font:14px/1.4 "Anek Latin",system-ui,-apple-system,"Segoe UI",sans-serif}' +
    '.bar{width:210mm;margin:10px auto 0;display:flex;justify-content:flex-end}' +
    '.bar button{font:inherit;font-size:13px;padding:8px 14px;border:1px solid #17635F;background:#17635F;color:#fff;border-radius:6px;cursor:pointer}' +
    '.page{width:210mm;height:296mm;margin:10px auto;padding:13mm 14mm 10mm;background:#fff;display:flex;flex-direction:column;gap:9px;overflow:hidden;box-shadow:0 1px 8px rgba(19,30,34,.18)}' +
    '.top{display:flex;justify-content:space-between;align-items:baseline;border-bottom:2px solid #17635F;padding-bottom:6px;gap:12px}' +
    '.brand{font-weight:600;font-stretch:88%;font-size:15px;color:#17635F}.brand b{font-weight:600;color:#131E22}' +
    '.mono{font-family:"IBM Plex Mono",ui-monospace,Menlo,Consolas,monospace;font-size:11.5px;color:#3F4D53}' +
    'h1{margin:2px 0 0;font-size:30px;line-height:1.08;font-weight:600;font-stretch:88%;overflow-wrap:anywhere}' +
    'h1.long{font-size:22px}h1.xlong{font-size:17px}' +
    '.dist{margin:2px 0 0;font-size:15px;color:#3F4D53;overflow-wrap:anywhere}' +
    '.find{background:#D8EAE7;border-left:4px solid #17635F;border-radius:0 8px 8px 0;padding:8px 12px}' +
    '.find .h{font-size:17px;font-weight:600;font-stretch:88%;line-height:1.25}.find .s{margin-top:3px;font-size:13px;color:#3F4D53}' +
    '.cols{display:flex;gap:14px;align-items:flex-start}' +
    '.mapbox{flex:0 0 61%}.map{display:block;width:100%;height:auto;border-radius:8px;border:1px solid #D3DAD8}' +
    '.map-bg{fill:#0F1B1F}.nb{fill:none;stroke:#C4D0D2;stroke-opacity:.7;stroke-width:.8;vector-effect:non-scaling-stroke}' +
    '.halo{fill:none;stroke:#0F1B1F;stroke-width:5;vector-effect:non-scaling-stroke}' +
    '.sel{fill:rgba(95,208,195,.10);stroke:#5FD0C3;stroke-width:2.2;vector-effect:non-scaling-stroke}' +
    '.scale-halo{fill:none;stroke:#0F1B1F;stroke-width:5;vector-effect:non-scaling-stroke}.scale{fill:none;stroke:#fff;stroke-width:2;vector-effect:non-scaling-stroke}' +
    '.scale-t{fill:#fff;font-family:"IBM Plex Mono",ui-monospace,Menlo,monospace;paint-order:stroke;stroke:#0F1B1F;stroke-width:3px;stroke-linejoin:round}' +
    '.cap{margin-top:4px;font-size:11.5px;color:#586469}' +
    '.leg{display:flex;flex-wrap:wrap;gap:3px 12px;margin-top:3px;font-size:11.5px;color:#3F4D53}' +
    '.sw{display:inline-block;width:11px;height:11px;border-radius:2px;margin-right:4px;vertical-align:-1px}' +
    '.stats{flex:1 1 0;min-width:0;display:grid;grid-template-columns:1fr 1fr;gap:7px}' +
    '.st{border:1px solid #D3DAD8;border-radius:8px;padding:6px 8px;min-width:0}.st.w{background:#E3EDF6;border-color:#E3EDF6}.st.x{grid-column:1/-1}' +
    '.st .n{font-size:21px;font-weight:600;font-stretch:88%;line-height:1.15;white-space:nowrap}.st.w .n{color:#1D4E7C}' +
    '.st .n small{font-size:12px;font-weight:400;color:#3F4D53}' +
    '.st .l{font-size:11.5px;color:#3F4D53;line-height:1.3;margin-top:2px}' +
    '.note{border:1px solid #E09A2B;background:#F8EACF;color:#7A4A06;border-radius:8px;padding:6px 10px;font-size:12.5px}' +
    'h2{margin:0 0 4px;font-size:13px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;color:#586469}' +
    'table{width:100%;border-collapse:collapse;font-size:12.5px}' +
    'th{text-align:left;font-weight:600;color:#586469;font-size:11.5px;border-bottom:1px solid #D3DAD8;padding:2px 5px}' +
    'td{padding:3px 5px;border-bottom:1px solid #E6EBEA;overflow-wrap:anywhere}th.r,td.r{text-align:right;white-space:nowrap}' +
    'tr.me td{background:#D8EAE7;font-weight:600}' +
    '.cred{margin-top:auto;border-top:1px solid #D3DAD8;padding-top:6px;font-size:11.5px;color:#3F4D53;line-height:1.35}' +
    '.cred p{margin:0 0 2px}.cred b{color:#131E22}' +
    '.foot{font-size:11.5px;color:#586469;border-top:1px solid #D3DAD8;padding-top:5px}.foot p{margin:0 0 2px}' +
    '@media print{body{background:#fff}.bar{display:none}.page{margin:0;box-shadow:none}}';

  function statCard(cls, num, label) { return '<div class="st ' + cls + '"><div class="n">' + num + '</div><div class="l">' + label + '</div></div>'; }
  function pm(v, e, unit) { return esc(f1(v)) + (isNum(e) ? ' <small>&plusmn; ' + esc(f1(e)) + '</small>' : '') + (unit ? ' <small>' + unit + '</small>' : ''); }

  function rowTr(r, me) {
    return '<tr' + (me ? ' class="me"' : '') + '><td class="r">' + (isNum(r.rank_water) ? r.rank_water : '-') + '</td><td>' + esc(r.mandal) + '</td><td>' + esc(shortDist(r.district)) +
      '</td><td class="r">' + esc(f1(r.water_pct)) + (isNum(r.water_err) ? ' &plusmn; ' + esc(f1(r.water_err)) : '') + ' %</td><td class="r">' + esc(fkm(r.water_km2)) +
      '</td><td class="r">' + esc(fsigned(r.water_change_vs_normal_pp)) + '</td></tr>';
  }
  function tableHtml(title, rows, me) {
    return '<div><h2>' + esc(title) + '</h2><table><thead><tr><th class="r">Rank</th><th>Mandal</th><th>District</th><th class="r">Open water</th><th class="r">km&sup2;</th><th class="r">vs normal, points</th></tr></thead><tbody>' +
      rows.map(function (r) { return rowTr(r, r === me); }).join('') + '</tbody></table></div>';
  }

  /* m = prepare() model; uri = cropped class image (data URI) or null */
  function briefHtml(m, uri) {
    var info = m.info, cr = m.credits, row = m.row, H = [];
    var nameLen = (m.mode === 'mandal' ? (m.mandalName || '') : m.areaName).length;
    var hcls = nameLen > 60 ? 'xlong' : nameLen > 26 ? 'long' : '';
    H.push('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=794">');
    H.push('<title>' + esc(m.title + ' - ' + (m.mode === 'mandal' ? m.mandalName : 'area summary') + ' - ' + info.dateText) + '</title><style>' + CSS + '</style></head><body>');
    H.push('<div class="bar"><button type="button" onclick="window.print()">Print or save as PDF</button></div>');
    H.push('<main class="page">');
    H.push('<div class="top"><div class="brand"><b>' + esc(m.title) + '</b> &middot; ' + (m.mode === 'mandal' ? 'Mandal brief' : 'Area brief') + '</div><div class="mono">NISAR L-band &middot; ' +
      esc(info.time || info.dateText) + (info.track != null ? ' &middot; track ' + esc(info.track) : '') + (info.pols ? ' &middot; ' + esc(info.pols) : '') + '</div></div>');
    H.push('<div><h1 class="' + hcls + '">' + esc(m.mode === 'mandal' ? m.mandalName : m.areaName) + '</h1><p class="dist">' +
      (m.mode === 'mandal' ? esc(row ? row.district : '') : 'Area summary for the radar pass of ' + esc(info.dateText) + '. Mandals with the most likely new open water first.') + '</p></div>');
    if (m.headline) H.push('<div class="find"><div class="h">' + esc(m.headline) + '</div>' + (m.sentence ? '<div class="s">' + esc(m.sentence) + '</div>' : '') + '</div>');
    if (m.mode === 'mandal' && !row) H.push('<div class="note">No numbers for this mandal in this pass.</div>');
    if (!m.rows.length) H.push('<div class="note">Numbers for this pass are not available.</div>');

    var S = [];
    if (m.mode === 'mandal' && row) {
      var ranked = isNum(row.rank_water);
      S.push(statCard('w', pm(row.water_pct, row.water_err, '%'), 'likely new open water, share of the mandal\'s land'));
      S.push(statCard('', ranked ? row.rank_water + ' <small>of ' + m.rankedN + '</small>' : 'Not ranked', ranked ? 'among ranked mandals by open water (1 = highest)' : esc(clean(row.flag) || 'not enough of the mandal is in the radar picture')));
      S.push(statCard('', isNum(row.water_km2) ? esc(fkm(row.water_km2)) + ' <small>km&sup2;</small>' : 'n/a', 'of likely new open water' + (isNum(row.flooded_km2) ? '; with wet crops ' + esc(fkm(row.flooded_km2)) + ' km&sup2;' : '')));
      S.push(statCard('', isNum(row.water_change_vs_normal_pp) ? esc(fsigned(row.water_change_vs_normal_pp)) + ' <small>points</small>' : 'n/a', 'open water compared with a normal fortnight' + (isNum(row.normal_water_pct) ? ' (' + esc(f1(row.normal_water_pct)) + ' %)' : '')));
      S.push(statCard('', isNum(row.coverage_pct) ? esc(f1(row.coverage_pct)) + ' <small>%</small>' : 'n/a', 'of the mandal\'s land seen by the radar'));
      S.push(statCard('', isNum(row.area_km2) ? esc(fkm(row.area_km2)) + ' <small>km&sup2;</small>' : 'n/a', 'of land measured'));
    } else if (m.mode === 'area') {
      m.numbers.forEach(function (t, i) { S.push(statCard(i === 0 ? 'w' : '', t.big, esc(t.label))); });
      S.push(statCard('', m.rows.length + ' <small>mandals</small>', 'measured in this pass, ' + m.rankedN + ' ranked'));
    }
    H.push('<div class="cols"><div class="mapbox">' + (m.map ? mapSvg(m.map, uri, m.mode === 'mandal' ? 'Map of ' + m.mandalName : 'Map of the area') +
      '<div class="leg"><span><i class="sw" style="background:#3FA7F5"></i>Likely new open water</span><span><i class="sw" style="background:#5FD0C3"></i>' +
      (m.mode === 'mandal' ? 'Selected mandal' : 'Ten mandals with most open water') + '</span><span><i class="sw" style="background:#C4D0D2"></i>Other mandals</span></div>' +
      '<div class="cap">' + (uri ? 'NISAR change map, ' + esc(info.dateText) + '. No basemap.' : 'Mandal outlines only. The radar map is not available here.') + '</div>'
      : '<div class="note">The mandal outline is not available, so no map is drawn.</div>') + '</div><div class="stats">' + S.join('') + '</div></div>');
    if (m.table && m.table.rows.length) H.push(tableHtml(m.table.title, m.table.rows, row));
    H.push('<div class="cred"><h2>Credits</h2><p><b>Radar data:</b> ' + esc(cr.nisar) + '.</p><p><b>Maps and numbers:</b> ' + esc(cr.derived) + '.</p><p>' + esc(cr.boundaries) + '. ' + esc(cr.districts) + '.</p></div>');
    H.push('<div class="foot"><p>' + esc(FOOTER) + '</p><p>Generated ' + esc(istText(m.now)) + (m.pageUrl ? ' &middot; ' + esc(m.pageUrl) : '') + '</p></div>');
    H.push('</main></body></html>');
    return H.join('');
  }

  /* ---------------- model ---------------- */
  function prepare(ctx, opts) {
    opts = opts || {};
    var rank = ctx.rank || {}, cfg = ctx.cfg || {}, findings = ctx.findings || null;
    var rows = rowsFor(rank, ctx.date);
    var rankedRows = rows.filter(function (r) { return isNum(r.rank_water); });
    var title = (cfg.site && cfg.site.title) || 'Matsya';
    var mode = ctx.mandalName ? 'mandal' : 'area';
    var row = null;
    if (mode === 'mandal') rows.forEach(function (r) { if (r.mandal === ctx.mandalName) row = r; });
    var fOK = findings && findings.pass && findings.pass.date === ctx.date;
    var areaId = (fOK && findings.area_id) || (ctx.story && ctx.story.area_id) || cfg.default_area;
    var area = ((cfg.areas || []).filter(function (a) { return a.id === areaId; })[0]) || (cfg.areas || [])[0] || null;
    var areaName = (area && area.name) || title;
    var info = passInfo(ctx);
    var feats = (ctx.mandals && ctx.mandals.features) || [];
    var idx = featIndex(feats);
    var bounds = opts.classBounds || ctx.classBounds || null;
    if (!bounds) {
      var ls = (ctx.manifest && ctx.manifest.layers) || [], i;
      for (i = 0; i < ls.length; i++) if (ls[i].bounds && /class_\d{8}_new_water/.test(ls[i].png || '')) { bounds = ls[i].bounds; break; }
    }
    var names = {};
    names.brief = slug(title) + '_' + (mode === 'mandal' ? slug(ctx.mandalName) : 'area') + '_' + ctx.date + '.html';
    names.csv = 'mandals_' + ctx.date + '.csv';
    names.geojson = 'mandals_' + ctx.date + '.geojson';
    names.findings = fOK ? 'findings_' + ctx.date + '.json' : null;

    var headline = fOK ? clean(findings.headline) : '';
    var sentence = '';
    if (mode === 'mandal' && fOK && findings.mandal_sentences) sentence = clean(findings.mandal_sentences[ctx.mandalName]);
    var numbers = [];
    if (mode === 'area' && fOK) (findings.three_numbers || []).forEach(function (t) {
      if (!t || !isNum(t.value) || !clean(t.label)) return;
      var unit = t.unit === 'km\u00b2' ? ' <small>km&sup2;</small>' : '';
      numbers.push({ big: esc(t.value) + unit, label: t.label });
    });

    var map = null;
    if (mode === 'mandal' && row) {
      var f = findFeat(idx, row.mandal, row.district);
      if (f) map = mapModel(feats, [f], [f], bounds, { pad: 0.3 });
    } else if (mode === 'area' && rows.length) {
      var matched = [], top = [];
      rows.forEach(function (r) { var g = findFeat(idx, r.mandal, r.district); if (g) { matched.push(g); if (isNum(r.rank_water) && r.rank_water <= 10) top.push(g); } });
      if (matched.length) map = mapModel(feats, matched, top, bounds, { pad: 0.05, epsDiv: 450 });
    }

    var table = null;
    if (mode === 'mandal' && row) {
      var at = rankedRows.indexOf(row), sel;
      if (at >= 0) { var a = Math.max(0, Math.min(at - 3, rankedRows.length - 7)); sel = rankedRows.slice(a, a + 7); table = { title: 'Mandals next to this one in the ranking', rows: sel }; }
      else if (rankedRows.length) table = { title: 'Top ranked mandals, for comparison', rows: rankedRows.slice(0, 6) };
    } else if (mode === 'area' && rankedRows.length) table = { title: 'Mandals with the most likely new open water', rows: rankedRows.slice(0, 10) };

    var cols = activeColumns(rows);
    return { ctx: ctx, mode: mode, title: title, areaName: areaName, mandalName: ctx.mandalName || null, row: row, rows: rows, rankedN: rankedRows.length,
      info: info, credits: creditLines(ctx, info), headline: headline, sentence: sentence, numbers: numbers, map: map, table: table, cols: cols, names: names,
      now: opts.now || new Date(), pageUrl: ctx.pageUrl || '', feats: feats, hasFindings: !!fOK };
  }

  /* ---------------- browser pieces ---------------- */
  function browserCrop(url, frac, o) {
    return new Promise(function (resolve) {
      if (typeof document === 'undefined' || !url) return resolve(null);
      var img = new Image();
      img.onload = function () {
        try {
          var W = img.naturalWidth, H = img.naturalHeight;
          var sx = Math.max(0, Math.round(frac.x0 * W)), sy = Math.max(0, Math.round(frac.y0 * H));
          var sw = Math.max(1, Math.min(W - sx, Math.round((frac.x1 - frac.x0) * W))), sh = Math.max(1, Math.min(H - sy, Math.round((frac.y1 - frac.y0) * H)));
          var maxW = (o && o.maxW) || 900, k = Math.min(1, maxW / sw, maxW / sh);
          var cv = document.createElement('canvas');
          cv.width = Math.max(1, Math.round(sw * k)); cv.height = Math.max(1, Math.round(sh * k));
          var g = cv.getContext('2d');
          g.imageSmoothingEnabled = true; g.imageSmoothingQuality = 'high';
          g.drawImage(img, sx, sy, sw, sh, 0, 0, cv.width, cv.height);
          resolve(cv.toDataURL('image/png'));
        } catch (e) { resolve(null); }
      };
      img.onerror = function () { resolve(null); };
      img.src = url;
    });
  }
  function download(blob, name) {
    var a = document.createElement('a'), u = URL.createObjectURL(blob);
    a.href = u; a.download = name; a.style.display = 'none';
    document.body.appendChild(a); a.click();
    setTimeout(function () { document.body.removeChild(a); URL.revokeObjectURL(u); }, 1500);
  }

  /* ---------------- build / zip / open ---------------- */
  function build(ctx, opts) {
    opts = opts || {};
    var m;
    try { m = prepare(ctx, opts); } catch (e) { return Promise.reject(e); }
    var cropFn = opts.cropFn || (typeof document !== 'undefined' ? browserCrop : null);
    var p = Promise.resolve(null);
    if (cropFn && m.map && m.map.raster && ctx.classImageUrl) {
      p = Promise.resolve().then(function () { return cropFn(ctx.classImageUrl, m.map.raster.frac, { maxW: opts.maxPx || (m.mode === 'area' ? 600 : 900) }); })
        .then(function (r) { return r && typeof r === 'object' ? r.uri || null : r || null; }).catch(function () { return null; });
    }
    return p.then(function (uri) {
      var files = {};
      files[m.names.brief] = briefHtml(m, uri);
      files[m.names.csv] = csv(m.rows, m.cols);
      files[m.names.geojson] = geojson(m.rows, m.feats, m.cols);
      if (m.names.findings) files[m.names.findings] = ctx.findingsText || JSON.stringify(ctx.findings, null, 2) + '\n';
      files['README.txt'] = readme(m);
      return { briefHtml: files[m.names.brief], briefName: m.names.brief, files: files, rows: m.rows, mode: m.mode, model: m };
    });
  }
  function zipBytes(ctx, opts) {
    opts = opts || {};
    return build(ctx, opts).then(function (b) {
      var ff = opts.fflate || root.fflate;
      if (!ff || !ff.zipSync) throw new Error('The zip library did not load.');
      var entries = {};
      Object.keys(b.files).forEach(function (k) { entries[k] = ff.strToU8(b.files[k]); });
      return { bytes: ff.zipSync(entries, { level: 6 }), name: 'matsya_' + (b.mode === 'mandal' ? slug(ctx.mandalName) : 'area') + '_' + ctx.date + '.zip', build: b };
    });
  }
  function zip(ctx, opts) {
    return zipBytes(ctx, opts).then(function (z) { var bl = new Blob([z.bytes], { type: 'application/zip' }); bl.zipName = z.name; return bl; });
  }
  /* Call this directly inside the click handler (the new tab must be opened before any await).
     Resolves { opened, url, name, blob }. If the browser blocked the tab (opened === false) show a download link for url/name. */
  function openBrief(ctx, opts) {
    var w = null;
    try { w = root.open ? root.open('', '_blank') : null; } catch (e) { w = null; }
    if (w) { try { w.opener = null; w.document.title = 'Preparing the brief'; w.document.body.textContent = 'Preparing the brief...'; } catch (e2) { /* ignore */ } }
    return build(ctx, opts).then(function (b) {
      var blob = new Blob([b.briefHtml], { type: 'text/html' }), url = URL.createObjectURL(blob);
      if (w) { try { w.location.href = url; } catch (e3) { w = null; } }
      return { opened: !!w, url: url, name: b.briefName, blob: blob };
    }, function (err) { if (w) { try { w.close(); } catch (e4) { /* ignore */ } } throw err; });
  }

  var api = { build: build, zip: zip, zipBytes: zipBytes, openBrief: openBrief, download: download, prepare: prepare, briefHtml: briefHtml, csv: csv, geojson: geojson,
    readme: readme, mapModel: mapModel, COLUMNS: COLUMNS, activeColumns: activeColumns, rowsFor: rowsFor, findFeat: findFeat, featIndex: featIndex, FOOTER: FOOTER, BAN: BAN, istText: istText };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root) root.SpacebrosExport = api;
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));
