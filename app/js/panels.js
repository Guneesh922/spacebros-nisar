/* panels.js: header controls (region, date), alerts strip, ranking card, selected-mandal card.
   Classic script. Defines App.panels = { init(root) }. Reads state + manifest only through App.
   Listens: manifest, region, event, mandal, lang, layers (date/range changes).
   Emits (via App.setState): region (picker), date (date control), mandal (row click).
   Containers expected: #region-picker #date-control #alerts #left-panel. */
(function () {
  'use strict';
  var App = window.App;
  if (!App) { console.error('[panels] App missing (load core.js first)'); return; }

  App.addStrings('en', {
    'panels.region_aria': 'Region',
    'panels.date_latest': 'Latest · {date} · {age}',
    'panels.date_latest_none': 'Latest',
    'panels.event_range': 'Selected period {from} → {to}',
    'panels.subtitle': 'Selected period {from} → {to} vs normal period {a} → {b}',
    'panels.subtitle_nodates': 'Selected period vs normal period',
    'panels.loading_rank': 'Loading the ranking',
    'panels.rank_unavailable': 'Ranking unavailable',
    'panels.no_rows': 'No mandals for this region in this analysis',
    'panels.sachet_unavailable': 'SACHET · unavailable',
    'panels.sachet_headline_none': 'no alerts in the saved snapshot',
    'panels.sachet_prefix': 'SACHET',
    'panels.gdacs_prefix': 'GDACS · live',
    'panels.gdacs_checking': 'GDACS · live · checking',
    'panels.gdacs_none': 'GDACS · live · no current events',
    'panels.gdacs_unavail_last': 'GDACS · unavailable · last known {time}',
    'panels.gdacs_unavail_never': 'GDACS · unavailable · never loaded',
    'panels.gdacs_type_TC': 'tropical cyclone',
    'panels.gdacs_type_FL': 'flood',
    'panels.gdacs_type_EQ': 'earthquake',
    'panels.gdacs_type_DR': 'drought',
    'panels.gdacs_type_VO': 'volcano',
    'panels.gdacs_type_WF': 'wildfire',
    'panels.why_title': 'Why a snapshot?',
    'panels.why_body': 'SACHET, the national alert list, does not allow browsers to read it directly. So the data pipeline saves a dated snapshot of it. The time shown in the strip is when it was saved, and it may be out of date. Check the official source for current alerts.',
    'panels.why_gdacs': 'GDACS is read live from your browser. If it cannot be reached, the strip says so and shows when it last worked.',
    'panels.why_close': 'Close',
    'panels.mandal_card': 'Selected mandal',
    'panels.water_big': 'likely water',
    'panels.tag_sample': 'Sample values',
    'panels.tag_sample_short': 'Sample',
    'panels.why_gdacs_now': 'GDACS now: {status}',
    'panels.expand_list': 'Show fewer',
    'panels.err_pm': '±{n}'
  });

  var T = function (k, v) { return App.t(k, v); };
  var MAX_PCT = 40;           // track scale, per mockup
  var TOP_N = 5;
  var GDACS_DEFAULT = 'https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH?eventlist=TC;FL&fromdate={from}&todate={to}&alertlevel=Green;Orange;Red';   // the bare .../MAP endpoint answers HTTP 400 (event type required)
  var GDACS_RADIUS_KM = 1500;
  var GDACS_REFRESH_MS = 10 * 60 * 1000;

  var P = {};
  App.panels = P;

  /* ---------------- tiny DOM helpers ---------------- */
  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }
  function clear(n) { while (n.firstChild) n.removeChild(n.firstChild); }
  function $(id) { return document.getElementById(id); }
  function isIso(s) { return typeof s === 'string' && /^\d{4}-\d{2}-\d{2}/.test(s); }
  function num(x) { x = Number(x); return isFinite(x) ? x : 0; }
  function pct(x) { return Math.max(0, Math.min(100, x / MAX_PCT * 100)) + '%'; }

  var ctx = { inited: false, expanded: false };
  var els = {};

  /* ======================================================================
     1. Region picker
     ====================================================================== */
  function regionOrder() {
    var regs = (App.manifest && App.manifest.regions) || [];
    var byId = {}, out = [], seen = {};
    regs.forEach(function (r) { byId[r.id] = r; });
    function add(r, depth) {
      if (!r || seen[r.id]) return;
      seen[r.id] = 1; out.push({ r: r, depth: depth });
      var kids = regs.filter(function (c) { return c.parent === r.id; });
      (r.children || []).forEach(function (id) {
        if (byId[id] && kids.indexOf(byId[id]) < 0) kids.push(byId[id]);
      });
      kids.forEach(function (c) { add(c, depth + 1); });
    }
    regs.forEach(function (r) { if (!r.parent || !byId[r.parent]) add(r, 0); });
    regs.forEach(function (r) { add(r, 0); });
    return out;
  }

  function buildRegion() {
    var host = $('region-picker'); if (!host) return;
    clear(host);
    var wrap = el('div', 'ctl');
    var lab = el('label', 'ctl__label', T('header.region.label'));
    lab.setAttribute('for', 'region-select');
    var sel = el('select', 'ctl__select'); sel.id = 'region-select';
    regionOrder().forEach(function (o) {
      var op = el('option', null, new Array(o.depth + 1).join('   ') + (o.depth ? '└ ' : '') + o.r.name);
      op.value = o.r.id;
      sel.appendChild(op);
    });
    sel.value = App.state.region || '';
    sel.addEventListener('change', function () { App.setState({ region: sel.value }); });
    wrap.appendChild(lab); wrap.appendChild(sel);
    host.appendChild(wrap);
    els.regionSel = sel;
  }
  function syncRegion() {
    if (els.regionSel && App.state.region != null) els.regionSel.value = App.state.region;
  }

  /* ======================================================================
     2. Date control
     ====================================================================== */
  function seriesDates() {
    var s = App.state, seen = {}, list = [];
    App.layersFor({ region: s.region, eventId: s.eventId }).forEach(function (l) {
      if (l.latest_of && l.status === 'ready' && isIso(l.date) && !seen[l.date]) { seen[l.date] = 1; list.push(l.date); }
    });
    list.sort(function (a, b) { return b < a ? -1 : b > a ? 1 : 0; });
    return list;
  }

  function buildDate() {
    var host = $('date-control'); if (!host) return;
    clear(host);
    var wrap = el('div', 'ctl');
    var lab = el('label', 'ctl__label', T('header.date.label'));
    lab.setAttribute('for', 'date-select');
    var sel = el('select', 'ctl__select'); sel.id = 'date-select';
    sel.addEventListener('change', function () { App.setState({ date: sel.value || null }); });
    var rng = el('span', 'ctl__range mono');
    wrap.appendChild(lab); wrap.appendChild(sel); wrap.appendChild(rng);
    host.appendChild(wrap);
    els.dateSel = sel; els.dateRange = rng;
  }
  function syncDate() {
    var sel = els.dateSel; if (!sel) return;
    var dates = seriesDates(), cur = App.state.date;
    clear(sel);
    var latest = el('option', null, dates.length
      ? T('panels.date_latest', { date: App.fmt.date(dates[0]), age: App.fmt.age(dates[0]) })
      : T('panels.date_latest_none'));
    latest.value = '';
    sel.appendChild(latest);
    var list = dates.slice();
    if (isIso(cur) && list.indexOf(cur) < 0) { list.push(cur); list.sort(function (a, b) { return b < a ? -1 : b > a ? 1 : 0; }); }
    list.forEach(function (d) {
      var o = el('option', null, App.fmt.date(d)); o.value = d; sel.appendChild(o);
    });
    sel.value = cur || '';
    var r = App.state.range;
    if (App.state.eventId && r && r[0] && r[1]) {
      els.dateRange.textContent = T('panels.event_range', { from: App.fmt.date(r[0]), to: App.fmt.date(r[1]) });
      els.dateRange.hidden = false;
    } else { els.dateRange.textContent = ''; els.dateRange.hidden = true; }
  }

  /* ======================================================================
     3. Alerts strip
     ====================================================================== */
  var sachet = { status: 'idle', data: null, lastKnown: null };
  var gdacs = { status: 'idle', features: [], lastKnown: null, timer: null };

  function buildAlerts() {
    var host = $('alerts'); if (!host) return;
    clear(host);
    var strip = el('div', 'alerts-strip');
    strip.setAttribute('role', 'region');
    strip.setAttribute('aria-label', T('alerts.title'));
    strip.appendChild(el('span', 'alerts-strip__label', T('alerts.title')));
    var s = el('span', 'alerts-strip__item alerts-strip__item--sachet');
    var sep = el('span', 'alerts-strip__sep', '|'); sep.setAttribute('aria-hidden', 'true');
    var g = el('span', 'alerts-strip__item alerts-strip__item--gdacs');
    g.setAttribute('aria-live', 'polite');
    var sp = el('span', 'alerts-strip__spacer');
    var why = el('button', 'alerts-strip__why', T('alerts.why')); why.type = 'button';
    why.addEventListener('click', openWhy);
    [s, sep, g, sp, why].forEach(function (n) { strip.appendChild(n); });
    host.appendChild(strip);
    els.sachet = s; els.gdacs = g; els.why = why;

    var dlg = el('dialog', 'why-dialog');
    dlg.setAttribute('aria-labelledby', 'why-title');
    var h = el('h2', 'why-dialog__title', T('panels.why_title')); h.id = 'why-title';
    dlg.appendChild(h);
    dlg.appendChild(el('p', 'why-dialog__body', T('panels.why_body')));
    dlg.appendChild(el('p', 'why-dialog__body', T('panels.why_gdacs')));
    els.whyGdacs = el('p', 'why-dialog__body why-dialog__now');
    dlg.appendChild(els.whyGdacs);
    var close = el('button', 'btn btn--primary why-dialog__close', T('panels.why_close')); close.type = 'button';
    close.addEventListener('click', function () { if (dlg.close) dlg.close(); else dlg.removeAttribute('open'); });
    dlg.appendChild(close);
    dlg.addEventListener('click', function (e) { if (e.target === dlg && dlg.close) dlg.close(); });
    host.appendChild(dlg);
    els.dialog = dlg;
  }
  function openWhy() {
    var d = els.dialog; if (!d) return;
    if (d.showModal) { try { d.showModal(); } catch (e) { d.setAttribute('open', ''); } } else d.setAttribute('open', '');
  }

  function dot(kind) { var d = el('span', 'alerts-strip__dot alerts-strip__dot--' + kind); d.setAttribute('aria-hidden', 'true'); return d; }

  function renderSachet() {
    var n = els.sachet; if (!n) return;
    clear(n);
    n.appendChild(dot('ring'));
    if (sachet.status === 'idle' || sachet.status === 'loading') {
      n.appendChild(document.createTextNode(T('panels.sachet_prefix') + ' · ' + T('state.loading')));
      return;
    }
    if (sachet.status === 'fail') {
      var lk = sachet.lastKnown ? ' · ' + T('state.last_known', { time: App.fmt.dateTime(sachet.lastKnown, 'IST') }) : '';
      n.appendChild(document.createTextNode(T('panels.sachet_unavailable') + lk));
      return;
    }
    var d = sachet.data || {};
    n.appendChild(document.createTextNode(T('panels.sachet_prefix') + ' · '));
    // short form (no year): '27 Oct, 17:30 IST' so the strip stays on one line
    var when = d.saved_at_ist ? App.fmt.dateTime(d.saved_at_ist, 'IST').replace(/ \d{4},/, ',') : T('state.unavailable');
    var snap = el('span', 'mono alerts-strip__snap', T('alerts.snapshot', { time: when }));
    n.appendChild(snap);
    var first = Array.isArray(d.sachet) && d.sachet[0];
    var head = first && (first.headline || first.title);
    n.appendChild(el('span', 'alerts-strip__headline', '· ' + (head || T('panels.sachet_headline_none'))));
    if (d.placeholder && d.placeholder.is) {
      var tag = el('span', 'tag-sample');
      tag.appendChild(el('span', 'tag-long', (d.placeholder.tag) || T('panels.tag_sample')));
      tag.appendChild(el('span', 'tag-short', T('panels.tag_sample_short')));
      n.appendChild(tag);
    }
  }

  /* --- GDACS --- */
  function toRad(x) { return x * Math.PI / 180; }
  function hav(lat1, lon1, lat2, lon2) {
    var a = Math.sin(toRad(lat2 - lat1) / 2), b = Math.sin(toRad(lon2 - lon1) / 2);
    var h = a * a + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * b * b;
    return 12742 * Math.asin(Math.min(1, Math.sqrt(h)));
  }
  function flatten(c, out) {
    if (!Array.isArray(c)) return out;
    if (typeof c[0] === 'number' && typeof c[1] === 'number') { out.push([c[0], c[1]]); return out; }
    for (var i = 0; i < c.length && out.length < 400; i++) flatten(c[i], out);
    return out;
  }
  function featurePoints(f) {
    var g = f && f.geometry, pts = [];
    if (!g) return pts;
    if (g.type === 'GeometryCollection' && Array.isArray(g.geometries)) {
      g.geometries.forEach(function (x) { flatten(x && x.coordinates, pts); });
    } else flatten(g.coordinates, pts);
    return pts;
  }
  function distToBounds(pts, b) {
    if (!b) return 0;
    var best = Infinity;
    pts.forEach(function (p) {
      var lon = p[0], lat = p[1];
      var cl = Math.max(b[0][0], Math.min(b[1][0], lat)), co = Math.max(b[0][1], Math.min(b[1][1], lon));
      var d = hav(lat, lon, cl, co);
      if (d < best) best = d;
    });
    return best;
  }
  var LEVEL = { red: 3, orange: 2, green: 1 };
  function pickGdacs() {
    var reg = App.regionById(App.state.region);
    var b = (reg && reg.bounds) || null;
    var best = null;
    (gdacs.features || []).forEach(function (f) {
      var p = (f && f.properties) || {};
      if (String(p.iscurrent).toLowerCase() === 'false') return;
      var pts = featurePoints(f);
      if (!pts.length) return;
      var d = distToBounds(pts, b);
      if (!(d <= GDACS_RADIUS_KM)) return;
      var lv = LEVEL[String(p.alertlevel || '').toLowerCase()] || 0;
      if (!best || d < best.d - 1 || (Math.abs(d - best.d) <= 1 && lv > best.lv)) best = { f: f, d: d, lv: lv };
    });
    return best;
  }
  function gdacsTitle(f) {
    var p = f.properties || {};
    var name = p.name || p.eventname || p.title || '';
    var type = p.eventtype ? (App.hasString('panels.gdacs_type_' + p.eventtype) ? T('panels.gdacs_type_' + p.eventtype) : String(p.eventtype)) : '';
    var meta = [type, p.alertlevel, p.country].filter(Boolean).join(', ');
    return (name || type || '') + (meta && name ? ' (' + meta + ')' : '');
  }
  function renderGdacs() {
    var n = els.gdacs; if (!n) return;
    clear(n);
    n.appendChild(dot('teal'));
    var txt;
    if (gdacs.status === 'idle' || gdacs.status === 'loading') txt = T('panels.gdacs_checking');
    else if (gdacs.status === 'fail') {
      txt = gdacs.lastKnown
        ? T('panels.gdacs_unavail_last', { time: App.fmt.dateTime(gdacs.lastKnown, 'IST') })
        : T('panels.gdacs_unavail_never');
    } else {
      var hit = pickGdacs();
      txt = hit ? T('panels.gdacs_prefix') + ' · ' + gdacsTitle(hit.f) : T('panels.gdacs_none');
    }
    n.appendChild(el('span', 'alerts-strip__text', txt));
    if (els.whyGdacs) els.whyGdacs.textContent = T('panels.why_gdacs_now', { status: txt });
  }

  function gdacsUrls() {
    var urls = [], lay = App.layerById && App.layerById('alerts_gdacs_live');
    if (!lay) {
      var all = (App.manifest && App.manifest.layers) || [];
      lay = all.filter(function (l) { return /gdacs/i.test(l.source_id || '') && l.type === 'alerts'; })[0];
    }
    var to = new Date(), from = new Date(to.getTime() - 14 * 86400000);
    var iso = function (d) { return d.toISOString().slice(0, 10); };
    if (lay) {
      var cfg = lay.config || {};
      if (cfg.endpoint) urls.push(cfg.endpoint);
      else if (lay.url_template) urls.push(lay.url_template.replace('{from}', iso(from)).replace('{to}', iso(to)));
    }
    var dflt = GDACS_DEFAULT.replace('{from}', iso(from)).replace('{to}', iso(to));
    if (urls.indexOf(dflt) < 0) urls.push(dflt);
    return urls;
  }
  function loadGdacs() {
    if (!App.manifest) return;
    var urls = gdacsUrls(), i = 0;
    if (gdacs.status === 'idle') { gdacs.status = 'loading'; renderGdacs(); }
    function next() {
      var url = urls[i++];
      App.fetchJSON(url, { fallbackLabel: 'GDACS' }).then(function (r) {
        var feats = r.ok && r.data && (Array.isArray(r.data.features) ? r.data.features : (Array.isArray(r.data) ? r.data : null));
        if (r.ok && feats) {
          gdacs.status = 'ok'; gdacs.features = feats; gdacs.lastKnown = r.fetchedAt;
          renderGdacs();
        } else if (i < urls.length) next();
        else {
          gdacs.status = 'fail'; gdacs.lastKnown = r.lastKnown || App.lastKnown(urls[0]) || null;
          renderGdacs();
        }
      });
    }
    next();
  }
  function loadSachet() {
    var f = App.manifest && App.manifest.files && App.manifest.files.alerts;
    if (!f) { sachet.status = 'fail'; renderSachet(); return; }
    var url = App.assetUrl(f);
    sachet.status = 'loading'; renderSachet();
    App.fetchJSON(url, { fallbackLabel: 'SACHET snapshot' }).then(function (r) {
      if (r.ok && r.data) { sachet.status = 'ok'; sachet.data = r.data; }
      else { sachet.status = 'fail'; sachet.lastKnown = r.lastKnown; }
      renderSachet();
    });
  }

  /* ======================================================================
     4. Ranking card + selected-mandal card
     ====================================================================== */
  var rankCache = {};     // url -> {status, rows, data}

  function pickAnalysis() {
    var m = App.manifest, s = App.state;
    if (!m || !m.analyses || !m.analyses.length) return null;
    if (s.eventId) {
      var ev = App.eventById(s.eventId);
      if (ev && ev.analysis_id) { var a = App.analysisById(ev.analysis_id); if (a) return a; }
    }
    var chain = App.regionChain(s.region), best = null, bs = Infinity;
    m.analyses.forEach(function (a) {
      var sc;
      if (!a.region) sc = 90;
      else {
        var i = chain.indexOf(a.region);
        if (i >= 0) sc = i;
        else {
          var up = App.regionChain(a.region).indexOf(s.region);
          sc = up >= 0 ? 50 + up : Infinity;
        }
      }
      if (sc < bs || (sc === bs && best && String(a.period && a.period[1] || '') > String(best.period && best.period[1] || ''))) { best = a; bs = sc; }
    });
    return bs === Infinity ? null : best;
  }

  function normRows(data) {
    var rows = Array.isArray(data) ? data : (data && Array.isArray(data.rows) ? data.rows : []);
    return rows.map(function (r, i) {
      return {
        mandal: String(r.mandal != null ? r.mandal : (r.name || '')),
        district: r.district == null ? null : String(r.district),
        water: num(r.water_pct), we: num(r.water_err),
        crops: num(r.crops_pct), ce: num(r.crops_err),
        normal: num(r.normal_pct),
        rank0: r.rank != null ? num(r.rank) : i + 1
      };
    }).filter(function (r) { return r.mandal; });
  }

  function loadRank(url, cb) {
    var c = rankCache[url];
    if (c) { if (c.status !== 'loading') return; c.waiters.push(cb); return; }
    c = rankCache[url] = { status: 'loading', rows: [], data: null, waiters: [cb] };
    App.fetchJSON(url, { fallbackLabel: 'ranking' }).then(function (r) {
      if (r.ok && r.data) { c.status = 'ok'; c.data = r.data; c.rows = normRows(r.data); }
      else { c.status = 'fail'; c.lastKnown = r.lastKnown; }
      var w = c.waiters; c.waiters = [];
      w.forEach(function (f) { f(); });
    });
  }

  /* Current model: {analysis, status, rows (filtered, ordered, with .rank), placeholder, data} */
  function model() {
    var a = pickAnalysis();
    var mo = { analysis: a, status: 'none', rows: [], placeholder: false, data: null };
    if (!a) return mo;
    var file = a.rank_file;
    if (!file) return mo;
    var url = App.assetUrl(file), c = rankCache[url];
    if (!c) { loadRank(url, renderLeft); mo.status = 'loading'; }
    else if (c.status === 'loading') mo.status = 'loading';
    else if (c.status === 'fail') mo.status = 'fail';
    else {
      mo.status = 'ok'; mo.data = c.data;
      var reg = App.regionById(App.state.region), ds = reg && reg.districts && reg.districts.length ? reg.districts : null;
      var rows = c.rows.filter(function (r) { return !ds || (r.district && ds.indexOf(r.district) >= 0); });
      rows = rows.slice().sort(function (x, y) { return x.rank0 - y.rank0; });
      rows.forEach(function (r, i) {
        r.rank = i + 1;
        r.total = r.water + r.crops;
        r.err = Math.round(Math.sqrt(r.we * r.we + r.ce * r.ce));
      });
      mo.rows = rows;
    }
    mo.placeholder = !!((a.placeholder && a.placeholder.is) || (mo.data && !Array.isArray(mo.data) && mo.data.placeholder && mo.data.placeholder.is));
    return mo;
  }

  function findRow(rows, name) {
    if (!name) return null;
    for (var i = 0; i < rows.length; i++) if (rows[i].mandal === name) return rows[i];
    var l = String(name).toLowerCase();
    for (var j = 0; j < rows.length; j++) if (rows[j].mandal.toLowerCase() === l) return rows[j];
    return null;
  }

  function openBrief(name) {
    if (App.brief && typeof App.brief.open === 'function') App.brief.open(name);
  }

  function skeleton(lines) {
    var d = el('div', 'skel-list'); d.setAttribute('aria-hidden', 'true');
    for (var i = 0; i < lines; i++) d.appendChild(el('span', 'skel'));
    return d;
  }

  function rowButton(r) {
    var b = el('button', 'rank-row'); b.type = 'button';
    b.setAttribute('data-mandal', r.mandal);
    b.setAttribute('aria-label', T('ranking.row_aria', { mandal: r.mandal, rank: r.rank, total: Math.round(r.total) + '%', err: r.err }));
    b.appendChild(el('span', 'rank-row__rank mono', String(r.rank)));
    b.appendChild(el('span', 'rank-row__name', r.mandal));
    var track = el('span', 'rank-row__track'); track.setAttribute('aria-hidden', 'true');
    var w = el('span', 'rank-row__water'); w.style.width = pct(r.water);
    var c = el('span', 'rank-row__crops'); c.style.left = pct(r.water); c.style.width = pct(Math.min(r.crops, MAX_PCT - Math.min(r.water, MAX_PCT)));
    var lo = Math.max(0, r.total - r.err), hi = Math.min(MAX_PCT, r.total + r.err);
    var wh = el('span', 'rank-row__whisker'); wh.style.left = pct(lo); wh.style.width = (parseFloat(pct(hi)) - parseFloat(pct(lo))) + '%';
    var cl = el('span', 'rank-row__cap'); cl.style.left = pct(lo);
    var cr = el('span', 'rank-row__cap rank-row__cap--r'); cr.style.left = pct(hi);
    var tk = el('span', 'rank-row__tick'); tk.style.left = pct(r.normal);
    [w, c, wh, cl, cr, tk].forEach(function (n) { track.appendChild(n); });
    b.appendChild(track);
    var tot = el('span', 'rank-row__total');
    tot.appendChild(el('span', 'rank-row__pct mono', Math.round(r.total) + '%'));
    tot.appendChild(document.createTextNode(' '));
    tot.appendChild(el('span', 'rank-row__err', T('panels.err_pm', { n: r.err })));
    b.appendChild(tot);
    b.addEventListener('click', function () { App.setState({ mandal: r.mandal }); });
    return b;
  }

  function legend() {
    var l = el('div', 'rank-legend');
    function item(swatch, label) {
      var s = el('span', 'rank-legend__item');
      s.appendChild(swatch); s.appendChild(document.createTextNode(label)); return s;
    }
    l.appendChild(item(el('span', 'rank-legend__sq rank-legend__sq--water'), App.likely(T('ranking.legend.water').replace(/^likely\s+/i, ''))));
    l.appendChild(item(el('span', 'rank-legend__sq rank-legend__sq--crops'), App.likely(T('ranking.legend.crops').replace(/^likely\s+/i, ''))));
    l.appendChild(item(el('span', 'rank-legend__tick'), T('ranking.legend.normal')));
    var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('width', '20'); svg.setAttribute('height', '10'); svg.setAttribute('viewBox', '0 0 20 10');
    svg.setAttribute('aria-hidden', 'true'); svg.setAttribute('class', 'rank-legend__err');
    var path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', 'M1.5 1v8M18.5 1v8M1.5 5h17'); path.setAttribute('fill', 'none');
    path.setAttribute('stroke', 'currentColor'); path.setAttribute('stroke-width', '1.5');
    svg.appendChild(path);
    l.appendChild(item(svg, T('ranking.legend.err')));
    return l;
  }

  function renderLeft() {
    var host = $('left-panel'); if (!host || !App.manifest) return;
    var scroll = host.scrollTop;
    var mo = model();
    var rootNode = els.leftRoot;
    if (!rootNode) { rootNode = els.leftRoot = el('div', 'panels-left'); host.appendChild(rootNode); }
    clear(rootNode);
    rootNode.appendChild(rankingCard(mo));
    var card = mandalCard(mo);
    if (card) rootNode.appendChild(card);
    host.scrollTop = scroll;
    els.mo = mo;
  }

  function rankingCard(mo) {
    var card = el('section', 'card rank-card');
    card.setAttribute('aria-labelledby', 'rank-title');
    var head = el('div', 'rank-card__head');
    var h = el('h2', 'rank-card__title', T('ranking.title')); h.id = 'rank-title';
    head.appendChild(h);
    if (mo.placeholder) head.appendChild(el('span', 'tag-sample', (mo.analysis && mo.analysis.placeholder && mo.analysis.placeholder.tag) || T('ranking.sample')));
    card.appendChild(head);

    var a = mo.analysis;
    if (!a || mo.status === 'none') {
      card.appendChild(el('p', 'rank-card__msg', T('state.no_analysis')));
      return card;
    }
    var p = a.period || (mo.data && mo.data.period), np = a.normal_period || (mo.data && mo.data.normal_period);
    card.appendChild(el('p', 'rank-card__sub', (p && p[0] && p[1] && np && np[0] && np[1])
      ? T('panels.subtitle', { from: App.fmt.date(p[0]), to: App.fmt.date(p[1]), a: App.fmt.date(np[0]), b: App.fmt.date(np[1]) })
      : T('panels.subtitle_nodates')));

    if (mo.status === 'loading') {
      var ld = el('div', 'rank-card__loading');
      ld.setAttribute('role', 'status');
      ld.appendChild(el('span', 'visually-hidden', T('panels.loading_rank')));
      ld.appendChild(skeleton(5));
      card.appendChild(ld);
      return card;
    }
    if (mo.status === 'fail') {
      var f = el('div', 'rank-card__msg rank-card__msg--fail'); f.setAttribute('role', 'status');
      f.appendChild(el('span', null, T('panels.rank_unavailable') + ' · ' + T('state.unavailable')));
      var rb = el('button', 'btn', T('state.retry')); rb.type = 'button';
      rb.addEventListener('click', function () { var u = App.assetUrl(a.rank_file); delete rankCache[u]; renderLeft(); });
      f.appendChild(rb);
      card.appendChild(f);
      return card;
    }
    if (!mo.rows.length) { card.appendChild(el('p', 'rank-card__msg', T('panels.no_rows'))); return card; }

    card.appendChild(legend());

    var list = el('div', 'rank-list' + (ctx.expanded ? ' rank-list--all' : ''));
    list.setAttribute('role', 'group'); list.setAttribute('aria-label', T('ranking.title'));
    var selName = selectedRow(mo) && selectedRow(mo).mandal;
    var shown = ctx.expanded ? mo.rows : mo.rows.slice(0, TOP_N);
    shown.forEach(function (r) {
      var b = rowButton(r);
      var on = r.mandal === App.state.mandal || (App.state.mandal && findRow(mo.rows, App.state.mandal) === r);
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
      list.appendChild(b);
    });
    card.appendChild(list);
    els.list = list;

    card.appendChild(el('p', 'rank-card__disclaimer', T('ranking.disclaimer')));

    var actions = el('div', 'rank-card__actions');
    var dl = el('button', 'btn btn--primary', T('ranking.download')); dl.type = 'button';
    dl.addEventListener('click', function () {
      var r = selectedRow(mo) || mo.rows[0]; openBrief(App.state.mandal || (r && r.mandal));
    });
    actions.appendChild(dl);
    if (mo.rows.length > TOP_N) {
      var all = el('button', 'btn', ctx.expanded ? T('panels.expand_list') : T('ranking.all', { n: mo.rows.length })); all.type = 'button';
      all.setAttribute('aria-expanded', ctx.expanded ? 'true' : 'false');
      all.addEventListener('click', function () { ctx.expanded = !ctx.expanded; renderLeft(); });
      actions.appendChild(all);
    }
    actions.appendChild(el('span', 'rank-card__pdf', T('ranking.pdf')));
    card.appendChild(actions);
    void selName;
    return card;
  }

  function selectedRow(mo) {
    if (!mo || !mo.rows || !mo.rows.length) return null;
    return findRow(mo.rows, App.state.mandal) || mo.rows[0];
  }

  function mandalCard(mo) {
    if (!mo || mo.status !== 'ok' || !mo.rows.length) return null;
    var r = selectedRow(mo);
    var card = el('section', 'card mandal-card');
    card.setAttribute('aria-label', T('panels.mandal_card'));
    var head = el('div', 'mandal-card__head');
    head.appendChild(el('h3', 'mandal-card__name', r.mandal));
    head.appendChild(el('span', 'mandal-card__rank', T('mandal.rank', { district: r.district || '', rank: r.rank, n: mo.rows.length }).replace(/^\s*·\s*/, '')));
    card.appendChild(head);
    var grid = el('div', 'mandal-card__grid');
    function stat(cls, big, small) {
      var d = el('div', 'stat stat--' + cls);
      d.appendChild(el('div', 'stat__big mono', big));
      d.appendChild(el('div', 'stat__small', small));
      return d;
    }
    grid.appendChild(stat('water', Math.round(r.water) + '%', T('mandal.water_detail', { err: Math.round(r.we) })));
    grid.appendChild(stat('crops', Math.round(r.crops) + '%', T('mandal.crops_detail', { err: Math.round(r.ce) })));
    var nrm = stat('normal', Math.round(r.normal) + '%', T('mandal.normal'));
    grid.appendChild(nrm);
    card.appendChild(grid);
    card.appendChild(el('p', 'mandal-card__disclaimer', T('ranking.disclaimer')));
    var act = el('div', 'mandal-card__actions');
    var b = el('button', 'btn btn--primary', T('mandal.brief', { mandal: r.mandal })); b.type = 'button';
    b.addEventListener('click', function () { openBrief(r.mandal); });
    act.appendChild(b);
    card.appendChild(act);
    return card;
  }

  /* map click or other mandal change: update highlight + card, scroll row into view */
  function onMandal() {
    var mo = els.mo || model();
    var name = App.state.mandal;
    var row = findRow(mo.rows || [], name);
    if (row && !ctx.expanded && mo.rows.indexOf(row) >= TOP_N) ctx.expanded = true;
    renderLeft();
    if (!name) return;
    var list = els.list; if (!list) return;
    var btns = list.querySelectorAll('.rank-row');
    for (var i = 0; i < btns.length; i++) {
      if (row && btns[i].getAttribute('data-mandal') === row.mandal) {
        try { btns[i].scrollIntoView({ block: 'nearest', behavior: 'smooth' }); } catch (e) { btns[i].scrollIntoView(); }
        break;
      }
    }
  }

  /* ======================================================================
     wiring
     ====================================================================== */
  function renderAll() {
    if (!App.manifest) return;
    buildRegion(); buildDate(); syncDate();
    if (!els.sachet) buildAlerts();
    renderSachet(); renderGdacs();
    renderLeft();
  }

  P.init = function (root) {
    if (ctx.inited) return; ctx.inited = true;
    App.on('manifest', function () {
      rankCache = {}; sachet = { status: 'idle', data: null, lastKnown: null };
      gdacs.status = 'idle'; gdacs.features = [];
      renderAll(); loadSachet(); loadGdacs();
    });
    App.on('region', function () { syncRegion(); syncDate(); renderGdacs(); ctx.expanded = false; renderLeft(); });
    App.on('event', function () { syncDate(); renderLeft(); });
    App.on('layers', function () { syncDate(); });
    App.on('mandal', onMandal);
    App.on('lang', function () { els.sachet = null; renderAll(); });
    gdacs.timer = setInterval(loadGdacs, GDACS_REFRESH_MS);
    if (App.manifest) { renderAll(); loadSachet(); loadGdacs(); }
  };
})();
