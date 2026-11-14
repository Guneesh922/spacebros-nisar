/* live.js: live layers. NASA GIBS WMTS tiles with date fallback, Open-Meteo marine + flood readouts,
   GDACS event list for the Events panel. Classic script, defines window.App.live.

   Public API:
     App.live.init()                         idempotent; waits for App.map, manifest and state
     App.live.getGdacsEvents({bounds,days})  -> Promise {ok, events[], fetchedAt, lastKnown}; never rejects
     App.live.status(layerId)                -> {ok, date, checkedAt, error, pending} | null
   Emits: App.emit('live:status', {id, ok, date, checkedAt, error, lastKnown}) when a layer's status changes.
   Every failure shows "unavailable" plus the last-known time. No numbers are ever invented. */
(function () {
  'use strict';
  if (!window.App) { console.error('[live] App missing'); return; }
  var App = window.App;

  App.addStrings('en', {
    'live.chip_ok': '{name} · {date}',
    'live.chip_checking': '{name} · checking',
    'live.chip_unavail_last': '{name} · unavailable · last known {time}',
    'live.chip_unavail_never': '{name} · unavailable · never loaded',
    'live.chips_label': 'Live data status',
    'live.readout_label': 'Live readouts',
    'live.readout_button': 'Live readouts',
    'live.readout_hide': 'Hide live readouts',
    'live.marine_line': 'Wave height {h} m · period {p} s · from {d}°',
    'live.marine_time': 'Model time {time} UTC',
    'live.flood_line': 'River flow today {q} m³/s',
    'live.flood_time': 'Model day {day}',
    'live.flood_spark_label': 'River flow, past 7 days to next 2 days. Today marked.',
    'live.unavail_last': 'unavailable · last known {time}',
    'live.unavail_never': 'unavailable · never loaded',
    'live.coords_unconfirmed': 'coordinates to be confirmed',
    'live.checking': 'checking',
    'live.credit_om': 'Open-Meteo, CC BY 4.0',
    'live.model_note': 'Model value at one point, not a measurement.',
    'live.marker_label': '{name} point'
  });

  var T = function (k, v) { return App.t(k, v); };
  var CSS_HREF = 'css/live.css?v=3';   // bumped: v=1 was cached with the old phone layout
  var OM_REFRESH_MS = 15 * 60 * 1000;
  var PROBE_TIMEOUT_MS = 6000;
  var GDACS_TTL_MS = 10 * 60 * 1000;
  var GDACS_DEFAULT = 'https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH?eventlist=TC;FL&fromdate={from}&todate={to}&alertlevel=Green;Orange;Red';   // the bare .../MAP endpoint answers HTTP 400 (event type required)

  var inited = false, map = null, mapWrap = null;
  var statusMap = {};            // id -> {ok, date, checkedAt, error, pending}
  var tiles = {};                // id -> {layer, key, date}
  var resolveToken = {};         // id -> int
  var om = {};                   // id -> {layer, marker, state, data, timer, token}
  var chipsEl = null, readoutEl = null, readoutBody = null, readoutBtn = null;
  var stackEl = null, layoutRo = null, watched = [];   // below 1200px the chips + readout share one column (css/live.css)
  var readoutOpen = false;
  var syncTimer = null;

  /* ---------------- tiny helpers ---------------- */
  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }
  function css(name, fb) {
    try { return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fb || ''; }
    catch (e) { return fb || ''; }
  }
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  function isoDay(d) { return d.getUTCFullYear() + '-' + pad(d.getUTCMonth() + 1) + '-' + pad(d.getUTCDate()); }
  function layers() { return (App.manifest && App.manifest.layers) || []; }
  function isOn(id) { var s = App.state.layersOn; return !!(s && s.has && s.has(id)); }
  function lsRead(key) { try { return window.localStorage.getItem(key); } catch (e) { return null; } }
  function lsWrite(key, v) { try { window.localStorage.setItem(key, v); } catch (e) { /* ignore */ } }
  function lastKey(layer) { return 'app.lastok:' + (layer.url_template || layer.id); }
  function lastKnown(layer) { return App.lastKnown(layer.url_template || layer.id) || lsRead(lastKey(layer)) || null; }
  function markOk(layer) { lsWrite(lastKey(layer), new Date().toISOString()); }
  function shortName(layer) {
    var n = String(layer.name || layer.id);
    var i = n.indexOf(' (');
    return (i > 0 ? n.slice(0, i) : n);
  }
  function timeText(iso) { return iso ? App.fmt.dateTime(iso, 'IST') : ''; }
  function safe(fn) { try { return fn(); } catch (e) { console.warn('[live]', e); return undefined; } }

  /* ---------------- css + dom ---------------- */
  function injectCss() {
    try {
      if (document.querySelector('link[data-live-css]')) return;
      var l = document.createElement('link');
      l.rel = 'stylesheet'; l.href = CSS_HREF; l.setAttribute('data-live-css', '1');
      document.head.appendChild(l);
    } catch (e) { /* ignore */ }
  }
  function ensureDom() {
    mapWrap = document.getElementById('map-wrap') || (map && map.getContainer && map.getContainer().parentNode);
    if (!mapWrap) return false;
    if (!stackEl) {
      stackEl = el('div', 'live-stack');
      mapWrap.appendChild(stackEl);
      watchLayout();
    }
    if (!chipsEl) {
      chipsEl = el('div', 'live-chips');
      chipsEl.setAttribute('aria-label', T('live.chips_label'));
      chipsEl.hidden = true;
      stackEl.appendChild(chipsEl);
    }
    if (!readoutEl) {
      readoutEl = el('div', 'live-readout');
      readoutEl.hidden = true;
      readoutBtn = el('button', 'live-readout__toggle', T('live.readout_button'));
      readoutBtn.type = 'button';
      readoutBtn.setAttribute('aria-expanded', 'false');
      readoutBtn.addEventListener('click', function () {
        readoutOpen = !readoutOpen;
        applyReadoutOpen();
      });
      readoutBody = el('div', 'live-readout__body');
      readoutBody.setAttribute('aria-label', T('live.readout_label'));
      readoutEl.appendChild(readoutBtn);
      readoutEl.appendChild(readoutBody);
      stackEl.insertBefore(readoutEl, chipsEl);   // readout sits above the chips, nearest the caption card
    }
    return true;
  }
  /* Below 1200px: the stack's bottom edge sits just above the caption card (or above the scale row
     when there is no card), and the readout's max height is 35% of the map. Both are CSS variables
     on the stack, so the layout follows the caption's real height. */
  function placeStack() {
    if (!stackEl || !mapWrap) return;
    var wr = mapWrap.getBoundingClientRect();
    var cap = mapWrap.querySelector('.mapcap');
    var bar = mapWrap.querySelector('.cmp-bar');
    var bottom = 52;                                   // scale/attribution row (about 44px) + gap
    if (cap) {
      var cr = cap.getBoundingClientRect();
      if (cr.height > 0) bottom = Math.round(wr.bottom - cr.top + 8);
    }
    /* readout may grow up to 35% of the map, but never above the compare bar or past the chips */
    var top = 0;
    if (bar) {
      var br = bar.getBoundingClientRect();
      if (br.height > 0) top = Math.round(br.bottom - wr.top + 8);
    }
    var chipsH = (chipsEl && !chipsEl.hidden) ? chipsEl.getBoundingClientRect().height : 0;
    var room = wr.height - bottom - top - chipsH - 6;
    stackEl.style.setProperty('--live-bottom', bottom + 'px');
    stackEl.style.setProperty('--live-maxh', Math.max(44, Math.floor(Math.min(wr.height * 0.35, room))) + 'px');
  }
  function watchLayout() {
    if (!stackEl || !mapWrap) return;
    if (typeof ResizeObserver === 'undefined') {
      if (!layoutRo) { layoutRo = true; window.addEventListener('resize', placeStack); }
      return;
    }
    if (!layoutRo || layoutRo === true) layoutRo = new ResizeObserver(placeStack);
    [mapWrap, mapWrap.querySelector('.mapcap'), mapWrap.querySelector('.cmp-bar'), chipsEl].forEach(function (n) {
      if (n && watched.indexOf(n) < 0) { watched.push(n); layoutRo.observe(n); }
    });
  }
  function applyReadoutOpen() {
    if (!readoutEl) return;
    readoutEl.classList.toggle('is-open', readoutOpen);
    readoutBtn.setAttribute('aria-expanded', readoutOpen ? 'true' : 'false');
    readoutBtn.textContent = readoutOpen ? T('live.readout_hide') : T('live.readout_button');
  }

  /* ---------------- status + chips ---------------- */
  function setStatus(layer, patch) {
    var prev = statusMap[layer.id] || {};
    var next = Object.assign({}, prev, patch);
    statusMap[layer.id] = next;
    renderChips();
    var out = { id: layer.id, ok: !!next.ok, date: next.date || null, checkedAt: next.checkedAt || null,
                error: next.error || null, lastKnown: lastKnown(layer), pending: !!next.pending };
    App.emit('live:status', out);
  }
  function activeLiveLayers() {
    return layers().filter(function (l) {
      return (l.kind === 'wmts' || isOpenMeteo(l)) && isOn(l.id);
    });
  }
  function dateLabel(layer, s) {
    if (!s || !s.date) return '';
    return /T/.test(s.date) ? App.fmt.dateTime(s.date, 'UTC') : App.fmt.date(s.date);
  }
  function renderChips() {
    if (!ensureDom()) return;
    var act = activeLiveLayers();
    chipsEl.textContent = '';
    chipsEl.hidden = !act.length;
    chipsEl.classList.toggle('has-readout', Object.keys(om).length > 0);
    act.forEach(function (layer) {
      var s = statusMap[layer.id] || { pending: true };
      var name = shortName(layer), txt, cls = 'live-chip';
      if (s.pending && !s.ok) { txt = T('live.chip_checking', { name: name }); cls += ' is-pending'; }
      else if (s.ok) { txt = T('live.chip_ok', { name: name, date: s.date ? dateLabel(layer, s) : T('common.today') }); }
      else {
        cls += ' is-fail';
        var lk = lastKnown(layer);
        txt = lk ? T('live.chip_unavail_last', { name: name, time: timeText(lk) })
                 : T('live.chip_unavail_never', { name: name });
      }
      var chip = el('div', cls);
      chip.setAttribute('role', 'status');
      chip.appendChild(el('span', 'live-chip__text', txt));
      if (layer.credit) chip.appendChild(el('span', 'live-chip__credit', layer.credit));
      chipsEl.appendChild(chip);
    });
  }

  /* ---------------- GIBS: date candidates + probing ---------------- */
  function isSubDaily(layer) {
    return /T/.test(layer.time_format || '') || layer.time_step === 'PT10M';
  }
  function fmtTime(layer, d) {
    if (isSubDaily(layer)) return d.toISOString().slice(0, 16) + ':00Z';
    return isoDay(d);
  }
  function candidates(layer) {
    var out = [], lag = Number(layer.latest_available_lag_days) || 0, now = new Date(), i;
    var sel = App.state.date;
    if (isSubDaily(layer)) {
      var base;
      var step = 10 * 60000;
      if (sel && /^\d{4}-\d{2}-\d{2}$/.test(sel) && sel !== isoDay(now)) base = new Date(sel + 'T12:00:00Z');
      else if (sel && /^\d{4}-\d{2}-\d{2}T/.test(sel)) base = new Date(sel);
      else base = now;
      if (isNaN(base)) base = now;
      base = new Date(Math.floor(base.getTime() / step) * step - lag * 86400000);
      for (i = 0; i <= 6; i++) out.push(fmtTime(layer, new Date(base.getTime() - i * step)));
    } else {
      var day;
      if (sel && /^\d{4}-\d{2}-\d{2}/.test(sel)) day = new Date(sel.slice(0, 10) + 'T00:00:00Z');
      else day = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()) - lag * 86400000);
      for (i = 0; i <= 3; i++) out.push(isoDay(new Date(day.getTime() - i * 86400000)));
    }
    return out;
  }
  function maxNative(layer) {
    var c = layer.config || {};
    return Number(c.max_native_zoom || c.maxNativeZoom) || 6;
  }
  function urlFor(layer, time, z, x, y) {
    return String(layer.url_template).replace('{time}', time)
      .replace('{z}', z).replace('{x}', x).replace('{y}', y);
  }
  function probeUrl(layer, time) {
    var z = Math.min(6, maxNative(layer)), c = null;
    try { if (map._loaded) c = map.getCenter(); } catch (e) { c = null; }    // no view yet: getCenter() would throw NaN
    if (!c || !isFinite(c.lat) || !isFinite(c.lng)) {
      var rg = App.regionById(App.state.region), rb = rg && rg.bounds;
      c = rb ? { lat: (rb[0][0] + rb[1][0]) / 2, lng: (rb[0][1] + rb[1][1]) / 2 } : { lat: 20.6, lng: 79 };
    }
    var lat = Math.max(-85.05, Math.min(85.05, c.lat)), n = Math.pow(2, z);
    var x = Math.floor((c.lng + 180) / 360 * n);
    var r = lat * Math.PI / 180;
    var y = Math.floor((1 - Math.log(Math.tan(r) + 1 / Math.cos(r)) / Math.PI) / 2 * n);
    x = Math.max(0, Math.min(n - 1, x)); y = Math.max(0, Math.min(n - 1, y));
    return urlFor(layer, time, z, x, y);
  }
  function probe(url) {
    return new Promise(function (resolve) {
      var done = false, img;
      function fin(ok, err) { if (done) return; done = true; clearTimeout(t); if (img) { img.onload = img.onerror = null; } resolve({ ok: ok, error: err || null }); }
      var t = setTimeout(function () { fin(false, 'timeout after ' + PROBE_TIMEOUT_MS + ' ms'); }, PROBE_TIMEOUT_MS);
      try {
        img = new Image();
        img.onload = function () { fin(true); };
        img.onerror = function () { fin(false, 'tile not available'); };
        img.src = url;
      } catch (e) { fin(false, e && e.message || 'probe failed'); }
    });
  }
  function opacityFor(layer) {
    var o = App.state.opacity && App.state.opacity[layer.id];
    if (o == null) o = layer.opacity;
    return (o == null || isNaN(o)) ? 0.7 : Number(o);
  }
  function ensurePane() {
    if (!map.getPane('contextPane')) {
      var p = map.createPane('contextPane');
      p.style.zIndex = 405;           /* above basemap (200), below NISAR radar images (410) */
    }
  }
  function removeTiles(id) {
    var t = tiles[id];
    if (t && t.layer && map) safe(function () { map.removeLayer(t.layer); });
    delete tiles[id];
  }
  function addTiles(layer, time, key) {
    removeTiles(layer.id);
    ensurePane();
    var tpl = String(layer.url_template).replace('{time}', time);
    var tl = L.tileLayer(tpl, {
      pane: 'contextPane', tileSize: 256, maxNativeZoom: maxNative(layer),
      maxZoom: Math.max(map.getMaxZoom() || 18, maxNative(layer)),
      opacity: opacityFor(layer), attribution: '', errorTileUrl: '', crossOrigin: false
    });
    tl.addTo(map);
    tiles[layer.id] = { layer: tl, key: key, date: time };
  }
  function resolveGibs(layer, key) {
    var id = layer.id;
    var token = (resolveToken[id] = (resolveToken[id] || 0) + 1);
    var list = candidates(layer), i = 0, lastErr = null;
    setStatus(layer, { pending: true });
    function next() {
      if (resolveToken[id] !== token) return;
      if (i >= list.length) {
        removeTiles(id);
        setStatus(layer, { ok: false, pending: false, date: null, checkedAt: new Date().toISOString(),
                           error: lastErr || 'no tile available' });
        return;
      }
      var time = list[i++];
      probe(probeUrl(layer, time)).then(function (r) {
        if (resolveToken[id] !== token) return;
        if (r.ok) {
          if (!isOn(id)) return;
          addTiles(layer, time, key);
          markOk(layer);
          setStatus(layer, { ok: true, pending: false, date: time, checkedAt: new Date().toISOString(), error: null });
        } else { lastErr = r.error; next(); }
      });
    }
    next();
  }

  function syncGibs() {
    if (!map || typeof L === 'undefined') return;
    var wanted = {};
    layers().forEach(function (layer) {
      if (layer.kind !== 'wmts' || !layer.url_template || !isOn(layer.id)) return;
      wanted[layer.id] = true;
      var key = layer.id + '|' + (App.state.date || '');
      var st = statusMap[layer.id], t = tiles[layer.id];
      if (t && t.key === key) {
        safe(function () { t.layer.setOpacity(opacityFor(layer)); });
        return;
      }
      if (st && st.key === key && (st.pending || (st.ok === false && st.checkedAt))) return;
      setStatus(layer, { key: key });
      resolveGibs(layer, key);
    });
    Object.keys(tiles).forEach(function (id) { if (!wanted[id]) { removeTiles(id); resolveToken[id] = (resolveToken[id] || 0) + 1; } });
    Object.keys(statusMap).forEach(function (id) {
      if (!wanted[id] && !om[id] && statusMap[id] && !isOn(id)) { /* keep status for last-known; chips only show active */ }
    });
  }

  /* ---------------- Open-Meteo ---------------- */
  function isOpenMeteo(l) {
    if (!l || l.kind !== 'live') return false;
    var c = l.config || {};
    if (!isFinite(c.lat) || !isFinite(c.lon) || c.lat == null || c.lon == null) return false;
    return /open-?meteo/i.test([l.source_id, l.provider, l.url_template, l.source].join(' '));
  }
  function omKind(l) {
    var s = [l.id, l.url_template].join(' ');
    if (/flood/i.test(s)) return 'flood';
    if (/marine/i.test(s)) return 'marine';
    return null;
  }
  function omUrl(l, kind) {
    var c = l.config, lat = c.lat, lon = c.lon, u;
    if (kind === 'marine') {
      u = 'https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lon}&current=wave_height,wave_period,wave_direction&timezone=UTC';
    } else {
      u = (l.url_template && /flood-api\.open-meteo/.test(l.url_template))
        ? l.url_template.replace(/forecast_days=\d+/, 'forecast_days=3')
        : 'https://flood-api.open-meteo.com/v1/flood?latitude={lat}&longitude={lon}&daily=river_discharge&past_days=7&forecast_days=3';
      u = u.replace(/\{lat\}/g, '{lat}').replace(/\{lon\}/g, '{lon}');
      if (!/latitude=/.test(u)) u += (u.indexOf('?') < 0 ? '?' : '&') + 'latitude={lat}&longitude={lon}';
    }
    return u.replace(/\{lat\}/g, lat).replace(/\{lon\}/g, lon);
  }
  function num(v) { return (typeof v === 'number' && isFinite(v)) ? v : null; }
  function fmtNum(v, d) {
    var s = Number(v).toFixed(d);
    return s;
  }
  function parseMarine(data) {
    var cur = data && data.current;
    if (!cur) return null;
    var h = num(cur.wave_height), p = num(cur.wave_period), d = num(cur.wave_direction);
    if (h == null || p == null || d == null) return null;
    return { h: h, p: p, d: d, time: cur.time || null };
  }
  function parseFlood(data) {
    var dl = data && data.daily;
    if (!dl || !Array.isArray(dl.time) || !Array.isArray(dl.river_discharge)) return null;
    var days = dl.time, q = dl.river_discharge, todayIso = isoDay(new Date()), idx = days.indexOf(todayIso);
    if (idx < 0 || num(q[idx]) == null) return null;
    return { days: days, q: q.map(num), today: idx };
  }
  function refreshOm(id) {
    var o = om[id];
    if (!o) return;
    var l = o.layer, token = (o.token = (o.token || 0) + 1);
    o.state = o.data ? o.state : 'loading';
    var url = omUrl(l, o.kind);
    setStatus(l, { pending: !o.data });
    renderReadout();
    App.fetchJSON(url, { timeoutMs: (l.config && l.config.timeout_ms) || 8000, fallbackLabel: l.name }).then(function (r) {
      if (!om[id] || o.token !== token) return;
      var parsed = r.ok ? (o.kind === 'marine' ? parseMarine(r.data) : parseFlood(r.data)) : null;
      if (parsed) {
        o.state = 'ok'; o.data = parsed; o.lastKnown = r.fetchedAt;
        lsWrite(lastKey(l), r.fetchedAt);
        setStatus(l, { ok: true, pending: false, date: o.kind === 'marine' ? (parsed.time ? parsed.time + ':00Z' : null) : parsed.days[parsed.today],
                       checkedAt: r.fetchedAt, error: null });
      } else {
        o.state = 'fail'; o.data = null;
        o.lastKnown = r.lastKnown || lastKnown(l);
        setStatus(l, { ok: false, pending: false, date: null, checkedAt: new Date().toISOString(),
                       error: r.ok ? 'unexpected response' : r.error });
      }
      renderReadout();
    });
  }
  function startOm(layer) {
    var kind = omKind(layer);
    if (!kind || om[layer.id]) return;
    var o = { layer: layer, kind: kind, state: 'loading', data: null, token: 0, marker: null, timer: null, lastKnown: null };
    om[layer.id] = o;
    if (map && typeof L !== 'undefined') {
      safe(function () {
        o.marker = L.circleMarker([layer.config.lat, layer.config.lon], {
          pane: 'markerPane', radius: 6, weight: 2, color: css('--teal-onmap'),
          fillColor: css('--stage'), fillOpacity: 0.9, interactive: true
        }).bindTooltip(T('live.marker_label', { name: shortName(layer) }), { className: 'map-tip' }).addTo(map);
      });
    }
    o.timer = setInterval(function () { refreshOm(layer.id); }, OM_REFRESH_MS);
    refreshOm(layer.id);
  }
  function stopOm(id) {
    var o = om[id];
    if (!o) return;
    clearInterval(o.timer);
    if (o.marker && map) safe(function () { map.removeLayer(o.marker); });
    delete om[id];
  }
  function syncOm() {
    layers().forEach(function (l) { if (isOpenMeteo(l) && isOn(l.id)) startOm(l); });
    Object.keys(om).forEach(function (id) { if (!isOn(id)) stopOm(id); });
    renderReadout();
  }

  function sparkline(o) {
    var d = o.data, W = 200, H = 36, P = 4, svgNS = 'http://www.w3.org/2000/svg';
    var vals = d.q.filter(function (v) { return v != null; });
    var lo = Math.min.apply(null, vals), hi = Math.max.apply(null, vals);
    var span = (hi - lo) || 1, n = d.q.length;
    function X(i) { return P + (W - 2 * P) * (n === 1 ? 0 : i / (n - 1)); }
    function Y(v) { return H - P - (H - 2 * P) * ((v - lo) / span); }
    var svg = document.createElementNS(svgNS, 'svg');
    svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
    svg.setAttribute('class', 'live-spark');
    svg.setAttribute('role', 'img');
    svg.setAttribute('aria-label', T('live.flood_spark_label'));
    var pts = [], segs = [];
    d.q.forEach(function (v, i) { if (v != null) pts.push(X(i).toFixed(1) + ',' + Y(v).toFixed(1)); });
    var line = document.createElementNS(svgNS, 'polyline');
    line.setAttribute('points', pts.join(' '));
    line.setAttribute('class', 'live-spark__line');
    svg.appendChild(line);
    var tx = X(d.today), ty = Y(d.q[d.today]);
    var vl = document.createElementNS(svgNS, 'line');
    vl.setAttribute('x1', tx); vl.setAttribute('x2', tx); vl.setAttribute('y1', P); vl.setAttribute('y2', H - P);
    vl.setAttribute('class', 'live-spark__today');
    svg.appendChild(vl);
    var dot = document.createElementNS(svgNS, 'circle');
    dot.setAttribute('cx', tx); dot.setAttribute('cy', ty); dot.setAttribute('r', 3);
    dot.setAttribute('class', 'live-spark__dot');
    svg.appendChild(dot);
    return svg;
  }

  function renderReadout() {
    if (!ensureDom()) return;
    var ids = Object.keys(om);
    readoutBody.textContent = '';
    readoutEl.hidden = !ids.length;
    if (chipsEl) chipsEl.classList.toggle('has-readout', ids.length > 0);
    if (!ids.length) { readoutOpen = false; applyReadoutOpen(); return; }
    ids.forEach(function (id) {
      var o = om[id], l = o.layer, card = el('section', 'live-card');
      card.appendChild(el('h3', 'live-card__title', shortName(l)));
      var line = el('p', 'live-card__line'), meta = null;
      line.setAttribute('role', 'status');
      if (o.state === 'ok' && o.data) {
        if (o.kind === 'marine') {
          line.textContent = T('live.marine_line', { h: fmtNum(o.data.h, 1), p: fmtNum(o.data.p, 1), d: Math.round(o.data.d) });
          if (o.data.time) meta = T('live.marine_time', { time: o.data.time.replace('T', ' ') });
        } else {
          line.textContent = T('live.flood_line', { q: fmtNum(o.data.q[o.data.today], 2) });
          meta = T('live.flood_time', { day: App.fmt.date(o.data.days[o.data.today]) });
        }
      } else if (o.state === 'fail') {
        line.classList.add('is-fail');
        var lk = o.lastKnown || lastKnown(l);
        line.textContent = lk ? T('live.unavail_last', { time: timeText(lk) }) : T('live.unavail_never');
      } else {
        line.textContent = T('live.checking');
      }
      card.appendChild(line);
      if (o.state === 'ok' && o.kind === 'flood' && o.data) card.appendChild(sparkline(o));
      if (meta) card.appendChild(el('p', 'live-card__meta', meta));
      if (l.config && l.config.coordinates_confirmed === false) card.appendChild(el('p', 'live-card__meta live-card__note', T('live.coords_unconfirmed')));
      card.appendChild(el('p', 'live-card__credit', l.credit || T('live.credit_om')));
      readoutBody.appendChild(card);
    });
    applyReadoutOpen();
  }

  /* ---------------- GDACS ---------------- */
  var gdacsCache = {};
  function gdacsUrls(from, to) {
    var urls = [], lay = App.layerById && App.layerById('alerts_gdacs_live');
    if (lay) {
      var cfg = lay.config || {};
      if (cfg.endpoint) urls.push(cfg.endpoint);
      else if (lay.url_template) urls.push(lay.url_template.replace('{from}', from).replace('{to}', to));
    }
    var dflt = GDACS_DEFAULT.replace('{from}', from).replace('{to}', to);
    if (urls.indexOf(dflt) < 0) urls.push(dflt);
    return urls;
  }
  function inBounds(b, lat, lon) {
    if (!b) return true;
    var s, w, n, e;
    if (Array.isArray(b) && b.length === 4) { s = b[0]; w = b[1]; n = b[2]; e = b[3]; }
    else if (b && typeof b.getSouth === 'function') { s = b.getSouth(); w = b.getWest(); n = b.getNorth(); e = b.getEast(); }
    else if (b && b.south != null) { s = b.south; w = b.west; n = b.north; e = b.east; }
    else return true;
    return lat >= s && lat <= n && lon >= w && lon <= e;
  }
  function mapGdacs(f) {
    var p = (f && f.properties) || {}, c = f && f.geometry && f.geometry.coordinates;
    var url = p.url && (typeof p.url === 'object' ? (p.url.report || p.url.details) : p.url) || null;
    return {
      id: String(p.eventtype || '') + ':' + String(p.eventid != null ? p.eventid : '') + (p.episodeid != null ? ':' + p.episodeid : ''),
      title: p.name || p.eventname || p.description || '',
      type: p.eventtype || null,
      alert: p.alertlevel || p.episodealertlevel || null,
      country: p.country || null,
      from: p.fromdate || null,
      to: p.todate || null,
      lat: Array.isArray(c) ? num(c[1]) : null,
      lon: Array.isArray(c) ? num(c[0]) : null,
      url: url
    };
  }
  function getGdacsEvents(opts) {
    try {
      opts = opts || {};
      var days = opts.days != null ? opts.days : 14;
      var nowD = new Date(), to = isoDay(nowD), from = isoDay(new Date(nowD.getTime() - days * 86400000));
      var ckey = from.slice(0, 10) + '|' + to;
      var hit = gdacsCache[ckey];
      var finish = function (res) {
        var events = (res.events || []).filter(function (e) { return e.lat == null || inBounds(opts.bounds, e.lat, e.lon); });
        return { ok: res.ok, events: events, fetchedAt: res.fetchedAt, lastKnown: res.lastKnown, error: res.error || null };
      };
      if (hit && hit.res && Date.now() - hit.at < GDACS_TTL_MS) return Promise.resolve(finish(hit.res));
      if (hit && hit.promise) return hit.promise.then(finish);
      var urls = gdacsUrls(from, to), i = 0;
      var promise = new Promise(function (resolve) {
        function next() {
          var url = urls[i++];
          App.fetchJSON(url, { timeoutMs: 8000, fallbackLabel: 'GDACS' }).then(function (r) {
            var feats = r.ok && r.data && (Array.isArray(r.data.features) ? r.data.features : (Array.isArray(r.data) ? r.data : null));
            if (feats) {
              resolve({ ok: true, events: feats.map(mapGdacs), fetchedAt: r.fetchedAt, lastKnown: r.fetchedAt });
            } else if (i < urls.length) next();
            else resolve({ ok: false, events: [], fetchedAt: null, lastKnown: r.lastKnown || App.lastKnown(urls[0]) || null, error: r.error });
          }).catch(function (e) {
            resolve({ ok: false, events: [], fetchedAt: null, lastKnown: App.lastKnown(urls[0]) || null, error: String(e && e.message || e) });
          });
        }
        next();
      }).then(function (res) {
        if (res.ok) gdacsCache[ckey] = { res: res, at: Date.now() }; else delete gdacsCache[ckey];
        return res;
      });
      gdacsCache[ckey] = { promise: promise, at: Date.now() };
      return promise.then(finish);
    } catch (e) {
      return Promise.resolve({ ok: false, events: [], fetchedAt: null, lastKnown: null, error: String(e && e.message || e) });
    }
  }

  /* ---------------- orchestration ---------------- */
  function sync() {
    if (!map) return;
    ensureDom();
    safe(syncGibs);
    safe(syncOm);
    safe(renderChips);
    watchLayout();
    placeStack();
  }
  function scheduleSync() { clearTimeout(syncTimer); syncTimer = setTimeout(sync, 60); }

  function onRegion() {
    /* the map re-centres after a region change: retry layers that had failed */
    setTimeout(function () {
      layers().forEach(function (l) {
        var s = statusMap[l.id];
        if (l.kind === 'wmts' && isOn(l.id) && s && !s.ok && !s.pending) {
          if (tiles[l.id]) removeTiles(l.id);
          setStatus(l, { key: null });
        }
      });
      sync();
    }, 900);
  }

  function attach() {
    map = App.map && App.map.getMap && App.map.getMap();
    if (!map) return false;
    ensureDom();
    ensurePane();
    sync();
    return true;
  }

  function init() {
    if (inited) return;
    inited = true;
    injectCss();
    App.on('layers', scheduleSync);
    App.on('manifest', scheduleSync);
    App.on('state', function (p) { if (p && p.changed && p.changed.indexOf('date') >= 0) scheduleSync(); });
    App.on('region', onRegion);
    App.on('lang', function () { renderChips(); renderReadout(); });
    if (!attach()) {
      var tries = 0, iv = setInterval(function () {
        tries++;
        if (attach() || tries > 120) clearInterval(iv);
      }, 250);
    }
  }

  App.live = {
    init: init,
    getGdacsEvents: getGdacsEvents,
    status: function (id) { var s = statusMap[id]; return s ? Object.assign({}, s) : null; }
  };
})();
