/* case.js: the Case study tab (a guided story). Classic script.
   Defines window.App.case = { init(rootEl) }.
   Left: a 7-chapter story with a chapter rail. Right: a sticky figure with its own Leaflet map (not the
   workspace map). The map is created once; chapters swap the image overlays, the vectors and the caption.
   Dates, layers, the track and the eye come from App.manifest and fetched JSON only. Text: strings/case.en.json.
   Scroll: Scrollama (lazy, jsDelivr) -> IntersectionObserver -> rail buttons only.
   Chart: Chart.js (window.Chart, else loaded from cdnjs). Without it, static rings at 25/50/100 km.
   Listens: view (builds lazily when view === 'case'), resize.
   Uses: App.t, App.fmt, App.likely, App.layerById, App.applyEvent, App.setState, App.fetchJSON, App.assetUrl. */
(function () {
  'use strict';
  var App = window.App;
  if (!App) { console.error('[case] App missing (load core.js first)'); return; }

  var SCROLLAMA_URL = 'https://cdn.jsdelivr.net/npm/scrollama@3.2.0/build/scrollama.min.js';
  var CHART_URL = 'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js';
  var KEYS = ['start', 'above', 'clouds', 'rough', 'shore', 'radar', 'about'];
  var STATIC_KM = [25, 50, 100];
  var SVGNS = 'http://www.w3.org/2000/svg';
  // wave diagram geometry (SVG user units, viewBox 0 0 360 210)
  var GEO = { top: 10, canopy: 80, water: 150, bottom: 210, endWater: 188 };

  var T = function (k, v) { return App.t(k, v); };

  var root = null, built = false, ev = null;
  var lay = {};                                   // resolved layers: calm, eye, coastBefore, coastAfter
  var data = { profile: null, track: null, viirs: null, viirsBounds: null, viirsDate: null };
  var dom = {}, map = null, baseOv = null, topOv = null, vec = null, ring = null, classOvs = {};
  var classOn = {}, chart = null, chartOk = false, scrollMode = 'rail', current = -1;
  var swipeOn = false, swipePct = 50, peak = null, wave = null;
  var lockIndex = null, lockTimer = null;          // a rail click wins over scroll-triggered steps for a moment
  var activeRaf = 0;                               // pending animation frame for the active-chapter check

  /* ---------------- small helpers ---------------- */
  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }
  function cssVar(name) {
    try { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
    catch (e) { return ''; }
  }
  function colour(name) { return cssVar(name) || 'currentColor'; }
  function pm(n) { return '±' + (Math.round(Number(n) * 10) / 10); }
  function signed(n) { var v = Number(n); return (v > 0 ? '+' : '') + v.toFixed(1); }
  function fmtDate(iso) { return iso ? App.fmt.date(iso) : ''; }
  function ready(layer) { return !!layer && layer.status === 'ready'; }
  function layerUrl(layer) { return App.assetUrl(layer.png); }
  function profilePoints() { return (data.profile && data.profile.points) || []; }
  function eyeLatLng() {
    var e = data.profile && data.profile.eye;
    return e && e.length === 2 ? [Number(e[0]), Number(e[1])] : null;
  }
  function polyCss(points) {
    return 'polygon(' + points.map(function (p) {
      return p[0].toFixed(1) + 'px ' + p[1].toFixed(1) + 'px';
    }).join(', ') + ')';
  }
  function debounce(fn, ms) {
    var t = null;
    return function () { clearTimeout(t); t = setTimeout(fn, ms); };
  }
  function loadScript(src) {
    return new Promise(function (resolve) {
      var s = document.createElement('script');
      s.src = src;
      s.async = true;
      s.onload = function () { resolve(true); };
      s.onerror = function () { resolve(false); };
      document.head.appendChild(s);
    });
  }
  function svgEl(name, attrs) {
    var n = document.createElementNS(SVGNS, name);
    Object.keys(attrs || {}).forEach(function (k) { n.setAttribute(k, attrs[k]); });
    return n;
  }

  /* ---------------- data ---------------- */
  // Chooses the first case_study event and its chapter layers by id pattern (see plan, section 3).
  function pickLayers() {
    var list = (App.manifest && App.manifest.events) || [];
    ev = list.filter(function (e) { return e.case_study; })[0] || null;
    if (!ev) return false;
    function get(ids) { return (ids || []).map(function (id) { return App.layerById(id); }).filter(Boolean); }
    function sorted(a) {
      return a.slice().sort(function (x, y) { return String(x.date || '').localeCompare(String(y.date || '')); });
    }
    var before = sorted(get(ev.layers && ev.layers.before));
    var during = sorted(get(ev.layers && ev.layers.during));
    var after = sorted(get(ev.layers && ev.layers.after));
    function sea(l) { return /^nisar_l_sea_/.test(l.id); }
    function coast(l) { return /^nisar_l_coast_/.test(l.id); }
    lay.eye = during.filter(sea)[0] || null;                 // sea layer of the during list (the eye pass)
    // calm reference: the sea layer of the before list closest in time BEFORE the eye pass (not the earliest:
    // the earliest frame has partial coverage and is an average sea)
    var seaBefore = before.filter(sea);
    var calmPool = lay.eye ? seaBefore.filter(function (l) { return String(l.date || '') < String(lay.eye.date || ''); }) : seaBefore;
    lay.calm = calmPool[calmPool.length - 1] || seaBefore[seaBefore.length - 1] || null;
    lay.coastBefore = before.filter(coast)[0] || null;       // earliest coast layer of the before list
    var lateCoast = sorted(during.concat(after).filter(coast));
    lay.coastAfter = lateCoast[lateCoast.length - 1] || null; // latest coast layer of the during/after lists
    return true;
  }

  function loadData() {
    var files = (App.manifest && App.manifest.files) || {};
    return Promise.all([
      App.fetchJSON(App.assetUrl(files.profile || 'data/processed/profile.json')).then(function (r) {
        data.profile = r.ok ? r.data : null;
      }),
      ev.track_geojson ? App.fetchJSON(App.assetUrl(ev.track_geojson)).then(function (r) {
        data.track = r.ok ? r.data : null;
      }) : Promise.resolve(),
      App.fetchJSON(App.assetUrl('data/processed/img/_index.json')).then(function (r) {
        if (!r.ok || !r.data || !r.data.images) return;
        var hit = r.data.images.filter(function (i) { return /gibs_viirs/.test(i.file || ''); })[0];
        if (!hit) return;
        data.viirs = App.assetUrl('data/processed/' + hit.file);
        data.viirsBounds = hit.bounds;
        data.viirsDate = hit.time || null;
      })
    ]);
  }

  function ensureChart() {
    if (window.Chart) return Promise.resolve(true);
    return loadScript(CHART_URL).then(function () { return !!window.Chart; });
  }

  function computePeak() {
    var p = profilePoints(), best = null;
    p.forEach(function (q) { if (best == null || q.db > best.db) best = q; });
    return best;
  }

  /* ---------------- DOM: story and figure ---------------- */
  function sectionFor(i) {
    var s = el('section', 'case-step');
    s.setAttribute('data-step', String(i));
    s.setAttribute('aria-labelledby', 'case-h-' + KEYS[i]);
    return s;
  }
  function heading(i, text) {
    var h = el('h2', null, text);
    h.id = 'case-h-' + KEYS[i];
    return h;
  }
  function button(text, cls, fn) {
    var b = el('button', cls || 'case-btn', text);
    b.type = 'button';
    b.addEventListener('click', fn);
    return b;
  }
  function tagSample() { return el('span', 'tag-sample', T('case.tag.numbers')); }

  function stepStart(i) {
    var s = sectionFor(i);
    s.appendChild(heading(i, T('case.start.title', { name: ev.name })));
    s.appendChild(el('p', null, T('case.start.body', { date: fmtDate(lay.eye && lay.eye.date), name: ev.name })));
    if (lay.eye && lay.eye.time_utc) {
      s.appendChild(el('p', 'case-meta', T('case.start.time', { time: App.fmt.dateTime(lay.eye.time_utc, 'IST') })));
    }
    s.appendChild(button(T('case.start.cta'), 'case-btn', function () { App.setState({ view: 'workspace' }); }));
    s.appendChild(el('p', 'muted', T('case.start.hint')));
    return s;
  }

  function stepAbove(i) {
    var s = sectionFor(i);
    s.appendChild(heading(i, T('case.above.title')));
    dom.aboveBody = el('p', null, T('case.above.body', { date: '' }));
    s.appendChild(dom.aboveBody);
    var key = el('ul', 'case-key');
    var li1 = el('li'); li1.appendChild(el('span', 'case-key__line')); li1.appendChild(el('span', null, T('case.above.key_track')));
    var li2 = el('li'); li2.appendChild(el('span', 'case-key__ring')); li2.appendChild(el('span', null, T('case.above.key_land', {
      time: ev.landfall && ev.landfall.time_utc ? App.fmt.dateTime(ev.landfall.time_utc, 'IST') : T('state.landfall_pending')
    })));
    key.appendChild(li1); key.appendChild(li2);
    s.appendChild(key);
    return s;
  }

  function stepClouds(i) {
    var s = sectionFor(i);
    s.appendChild(heading(i, T('case.clouds.title')));
    s.appendChild(el('p', null, T('case.clouds.body', { before: fmtDate(lay.calm && lay.calm.date), during: fmtDate(lay.eye && lay.eye.date) })));
    s.appendChild(el('p', 'case-note', T('case.swipe.hint')));
    return s;
  }

  function stepRough(i) {
    var s = sectionFor(i);
    s.appendChild(heading(i, T('case.rough.title')));
    s.appendChild(el('p', null, T('case.rough.body')));
    dom.stats = el('div', 'case-stats');
    s.appendChild(dom.stats);
    dom.tagRow = el('div', 'case-tags');
    s.appendChild(dom.tagRow);

    var card = el('div', 'case-card');
    card.appendChild(el('h4', null, T('case.rough.chart_title')));
    card.appendChild(el('p', 'muted', T('case.rough.chart_unit')));
    dom.readout = el('p', 'case-readout');
    dom.readout.setAttribute('aria-live', 'polite');
    card.appendChild(dom.readout);
    var box = el('div', 'case-chart');
    dom.canvas = el('canvas');
    dom.canvas.setAttribute('role', 'img');
    dom.canvas.setAttribute('aria-label', T('case.rough.chart_aria'));
    box.appendChild(dom.canvas);
    card.appendChild(box);
    dom.chartBox = box;
    dom.chartNotes = [el('p', 'case-note', T('case.rough.note')), el('p', 'case-note', T('case.rough.hint'))];
    dom.chartNotes.forEach(function (n) { card.appendChild(n); });
    dom.chartFallback = el('p', 'case-note', T('case.rough.fallback'));
    dom.chartFallback.hidden = true;
    card.appendChild(dom.chartFallback);
    s.appendChild(card);
    return s;
  }

  function stepShore(i) {
    var s = sectionFor(i);
    s.appendChild(heading(i, T('case.shore.title')));
    s.appendChild(el('p', null, T('case.shore.body', {
      before: fmtDate(lay.coastBefore && lay.coastBefore.date),
      after: fmtDate(lay.coastAfter && lay.coastAfter.date)
    })));
    var card = el('div', 'case-card');
    card.appendChild(el('h4', null, T('case.classes.title')));
    dom.classList = el('ul', 'case-classes');
    card.appendChild(dom.classList);
    card.appendChild(el('p', 'case-note', T('case.classes.explain')));
    card.appendChild(el('p', null, T('case.classes.note')));
    s.appendChild(card);
    s.appendChild(button(T('case.shore.open'), 'case-btn', openInWorkspace));
    s.appendChild(el('p', 'case-note', T('case.shore.open_hint')));
    return s;
  }

  function classRows() {
    var defs = [
      { id: 'nisar_class_new_water', label: T('case.classes.water'), sw: 'case-sw--water' },
      { id: 'nisar_class_wet_crops', label: T('case.classes.crops'), sw: 'case-sw--crops' },
      { id: 'nisar_class_no_change', label: T('case.classes.none'), sw: 'case-sw--none' }
    ];
    dom.classList.textContent = '';
    defs.forEach(function (d) {
      var layer = App.layerById(d.id);
      var named = App.likely(d.label);
      var li = el('li', 'case-class');
      var cb = el('input', 'case-class__cb');
      cb.type = 'checkbox';
      cb.setAttribute('aria-label', T('case.classes.toggle', { label: named }));
      var on = ready(layer) && !!layer.png;
      cb.disabled = !on;
      cb.checked = on && !!classOn[d.id];
      cb.addEventListener('change', function () {
        classOn[d.id] = cb.checked;
        syncClassOverlay(d.id, layer);
      });
      li.appendChild(cb);
      li.appendChild(el('span', 'case-sw ' + d.sw));
      li.appendChild(el('span', null, named));
      li.appendChild(el('span', 'case-class__pending', on ? '' : T('case.classes.pending')));
      dom.classList.appendChild(li);
    });
  }

  function stepRadar(i) {
    var s = sectionFor(i);
    s.appendChild(heading(i, T('case.radar.title')));
    s.appendChild(el('p', null, T('case.radar.body')));
    var list = el('ul', 'case-claims');
    [
      { c: 'c1', v: 'yes' },
      { c: 'c2', v: 'no' },
      { c: 'c3', v: 'partly' },
      { c: 'c4', v: 'no' }
    ].forEach(function (item) {
      var li = el('li', 'case-claim');
      li.appendChild(el('h3', null, T('case.radar.' + item.c + '.claim')));
      var verdictText = T('case.verdict.' + (item.v === 'yes' ? 'yes' : item.v === 'partly' ? 'partly' : 'no'));
      li.appendChild(el('span', 'case-verdict case-verdict--' + item.v, verdictText));
      li.appendChild(el('span', 'tag-sample case-draft', T('case.tag.draft')));
      li.appendChild(el('p', null, T('case.radar.' + item.c + '.why', { date: fmtDate(lay.eye && lay.eye.date) })));
      list.appendChild(li);
    });
    s.appendChild(list);

    var box = el('div', 'case-slider-box');
    var label = el('label', 'case-swipe__label', T('case.radar.slider'));
    label.htmlFor = 'case-wave-range';
    box.appendChild(label);
    box.appendChild(el('p', 'case-note', T('case.radar.slider_hint')));
    var range = el('input', 'case-range');
    range.type = 'range';
    range.id = 'case-wave-range';
    range.min = '0'; range.max = '100'; range.step = '1'; range.value = '0';
    range.setAttribute('aria-label', T('case.radar.slider_aria'));
    range.addEventListener('input', function () { morphWave(Number(range.value) / 100); });
    box.appendChild(range);
    var ends = el('div', 'case-slider-ends');
    ends.appendChild(el('span', null, T('case.radar.end_l')));
    ends.appendChild(el('span', null, T('case.radar.end_s')));
    box.appendChild(ends);
    box.appendChild(buildDiagram());
    dom.waveNote = el('p', 'case-note');
    box.appendChild(dom.waveNote);
    box.appendChild(el('p', 'case-note', T('case.radar.diagram_note')));
    s.appendChild(box);
    morphWave(0);
    return s;
  }

  function buildDiagram() {
    var svg = svgEl('svg', { viewBox: '0 0 360 210', role: 'img', 'aria-label': T('case.radar.diagram_alt'), class: 'case-diagram' });
    svg.appendChild(svgEl('rect', { x: 0, y: GEO.water, width: 360, height: GEO.bottom - GEO.water, fill: colour('--quiet') }));
    svg.appendChild(svgEl('rect', { x: 0, y: GEO.canopy, width: 360, height: GEO.water - GEO.canopy, fill: colour('--teal-tint') }));
    for (var x = 16; x < 360; x += 18) {
      svg.appendChild(svgEl('line', { x1: x, y1: GEO.canopy, x2: x + 4, y2: GEO.water, stroke: colour('--ink-2'), 'stroke-width': 1.5, opacity: '0.5' }));
    }
    svg.appendChild(svgEl('line', { x1: 0, y1: GEO.water, x2: 360, y2: GEO.water, stroke: colour('--ink-2'), 'stroke-width': 1 }));
    var t1 = svgEl('text', { x: 8, y: GEO.canopy - 8, 'font-size': 12, fill: colour('--ink-2') });
    t1.textContent = T('case.radar.canopy');
    var t2 = svgEl('text', { x: 8, y: GEO.bottom - 10, 'font-size': 12, fill: colour('--ink-2') });
    t2.textContent = T('case.radar.water');
    var t3 = svgEl('text', { x: 8, y: 20, 'font-size': 13, 'font-weight': 600, fill: colour('--ink') });
    svg.appendChild(t1); svg.appendChild(t2); svg.appendChild(t3);
    wave = {
      path: svgEl('path', { fill: 'none', stroke: colour('--teal'), 'stroke-width': 3, 'stroke-linecap': 'round' }),
      dot: svgEl('circle', { r: 5, fill: colour('--card'), stroke: colour('--ink'), 'stroke-width': 2 }),
      label: t3
    };
    svg.appendChild(wave.path);
    svg.appendChild(wave.dot);
    return svg;
  }

  // t = 0 is the 24 cm L-band wave (passes the canopy); t = 1 is the 9 cm S-band wave (stops at the canopy)
  function morphWave(t) {
    if (!wave) return;
    var cm = 24 + (9 - 24) * t;
    var period = 120 * cm / 24;                              // a shorter wave has a shorter crest spacing
    var yEnd = GEO.endWater - (GEO.endWater - GEO.canopy) * t;
    var d = '';
    for (var y = GEO.top; y <= yEnd + 0.01; y += 2) {
      var x = 180 + 18 * Math.sin(2 * Math.PI * (y - GEO.top) / period);
      d += (d ? ' L ' : 'M ') + x.toFixed(1) + ' ' + y.toFixed(1);
    }
    var lastX = 180 + 18 * Math.sin(2 * Math.PI * (yEnd - GEO.top) / period);
    wave.path.setAttribute('d', d);
    wave.dot.setAttribute('cx', lastX.toFixed(1));
    wave.dot.setAttribute('cy', yEnd.toFixed(1));
    wave.label.textContent = T('case.radar.wl', { cm: Math.round(cm) });
    if (dom.waveNote) dom.waveNote.textContent = t < 0.5 ? T('case.radar.note_l') : T('case.radar.note_s');
  }

  function stepAbout(i) {
    var s = sectionFor(i);
    s.appendChild(heading(i, T('case.about.title')));
    s.appendChild(el('p', null, T('case.about.intro')));
    s.appendChild(el('h3', null, T('case.about.data_h')));
    s.appendChild(el('p', null, T('case.about.data_body')));
    s.appendChild(el('h3', null, T('case.about.methods_h')));
    s.appendChild(el('p', null, T('case.about.methods_body')));
    s.appendChild(el('h3', null, T('case.about.limits_h')));
    var lim = el('ul', 'case-key');
    for (var n = 1; n <= 7; n++) {
      var li = el('li', null, T('case.about.limit' + n));
      li.style.alignItems = 'flex-start';
      lim.appendChild(li);
    }
    s.appendChild(lim);
    s.appendChild(el('h3', null, T('case.about.credits_h')));
    var sources = (App.manifest && App.manifest.sources) || [];
    var credits = el('ul', 'case-key');
    sources.forEach(function (src) {
      var li = el('li', null, T('case.about.credit_row', {
        provider: src.provider || src.id || '',
        credit: src.credit_line || '',
        licence: src.licence || ''
      }));
      li.style.alignItems = 'flex-start';
      credits.appendChild(li);
    });
    s.appendChild(credits);
    s.appendChild(el('h3', null, T('case.about.placeholder_h')));
    s.appendChild(el('p', null, T('case.about.placeholder_body')));
    s.appendChild(el('p', 'case-note', T('case.about.docs')));
    return s;
  }

  function buildDom() {
    root.textContent = '';
    var layout = el('div', 'case-layout');

    dom.story = el('div', 'case-story');
    dom.story.id = 'case-story';
    var backRow = el('div', 'case-back-row');
    backRow.appendChild(button(T('case.back'), 'case-btn case-btn--ghost', function () { App.setState({ view: 'workspace' }); }));
    dom.story.appendChild(backRow);

    dom.rail = el('nav', 'case-rail');
    dom.rail.setAttribute('aria-label', T('case.nav.label'));
    var ol = el('ol', 'case-rail__list');
    dom.railBtns = [];
    KEYS.forEach(function (k, i) {
      var li = el('li', 'case-rail__item');
      var b = el('button', 'case-rail__btn');
      b.type = 'button';
      b.setAttribute('aria-label', T('case.nav.item', { n: i, name: T('case.step.' + k) }));
      b.appendChild(el('span', 'case-rail__num', String(i)));
      b.appendChild(el('span', null, T('case.step.' + k)));
      b.addEventListener('click', function () { goStep(i); });
      li.appendChild(b);
      ol.appendChild(li);
      dom.railBtns.push(b);
    });
    dom.rail.appendChild(ol);
    dom.story.appendChild(dom.rail);

    dom.steps = [stepStart(0), stepAbove(1), stepClouds(2), stepRough(3), stepShore(4), stepRadar(5), stepAbout(6)];
    dom.steps.forEach(function (s) { dom.story.appendChild(s); });
    classRows();

    dom.figure = el('section', 'case-figure');
    dom.stage = el('div', 'case-stage');
    dom.mapEl = el('div', 'case-map');
    dom.mapEl.setAttribute('role', 'img');
    dom.divider = el('div', 'case-divider');
    dom.divider.hidden = true;
    dom.chipL = el('span', 'case-chip');
    dom.chipR = el('span', 'case-chip case-chip--right');
    dom.chipL.hidden = true;
    dom.chipR.hidden = true;
    dom.stage.appendChild(dom.mapEl);
    dom.stage.appendChild(dom.divider);
    dom.stage.appendChild(dom.chipL);
    dom.stage.appendChild(dom.chipR);

    dom.swipe = el('div', 'case-swipe');
    dom.swipe.hidden = true;
    var label = el('span', 'case-swipe__label', T('case.swipe.label'));
    dom.range = el('input', 'case-range');
    dom.range.type = 'range';
    dom.range.min = '0'; dom.range.max = '100'; dom.range.step = '1';
    dom.range.value = String(swipePct);
    dom.range.setAttribute('aria-label', T('case.swipe.label'));
    dom.range.addEventListener('input', function () { swipePct = Number(dom.range.value); clipTop(); });
    dom.swipe.appendChild(label);
    dom.swipe.appendChild(dom.range);
    dom.swipe.appendChild(el('span', 'case-swipe__hint', T('case.swipe.hint')));

    dom.figcap = el('div', 'case-figcap');
    dom.figcap.setAttribute('aria-live', 'polite');

    dom.figure.appendChild(dom.stage);
    dom.figure.appendChild(dom.swipe);
    dom.figure.appendChild(dom.figcap);

    layout.appendChild(dom.story);
    layout.appendChild(dom.figure);
    root.appendChild(layout);
  }

  /* ---------------- map ---------------- */
  function buildMap() {
    // Leaflet sets position:relative inline when the container is static; pin it so the map fills the stage.
    dom.mapEl.style.position = 'absolute';
    map = L.map(dom.mapEl, { attributionControl: false, zoomControl: false, scrollWheelZoom: false, zoomSnap: 0.1 });
    L.control.zoom({ position: 'topright' }).addTo(map);
    [['caseBase', 400], ['caseTop', 410], ['caseClass', 420], ['caseVec', 450]].forEach(function (p) {
      map.createPane(p[0]).style.zIndex = String(p[1]);
    });
    vec = L.layerGroup().addTo(map);
    var region = ev && App.regionById(ev.region);
    if (region && region.bounds) map.fitBounds(region.bounds, { animate: false });
    else map.setView([0, 0], 2);
    map.on('move zoom resize viewreset', clipTop);
  }

  function showBase(url, bounds) {
    if (!map || !url || !bounds) return false;
    if (!baseOv) {
      baseOv = L.imageOverlay(url, bounds, { pane: 'caseBase', interactive: false }).addTo(map);
    } else {
      baseOv.setUrl(url);
      baseOv.setBounds(bounds);
      if (!map.hasLayer(baseOv)) baseOv.addTo(map);
    }
    map.fitBounds(bounds, { padding: [12, 12], animate: false });
    return true;
  }

  function showLayer(layer) {
    if (!layer) return false;
    return showBase(layerUrl(layer), layer.bounds);
  }

  function setTopLayer(layer) {
    var url = layerUrl(layer);
    if (!topOv) {
      topOv = L.imageOverlay(url, layer.bounds, { pane: 'caseTop', interactive: false }).addTo(map);
    } else {
      topOv.setUrl(url);
      topOv.setBounds(layer.bounds);
      if (!map.hasLayer(topOv)) topOv.addTo(map);
    }
  }

  // Two pictures: the base (right side) and the top (left side, clipped at the divider).
  function swipeTo(leftLayer, rightLayer, leftText, rightText) {
    if (!map || !leftLayer || !rightLayer) return false;
    if (!showLayer(rightLayer)) return false;
    setTopLayer(leftLayer);
    dom.chipL.textContent = leftText;
    dom.chipR.textContent = rightText;
    setSwipe(true);
    return true;
  }

  function setSwipe(on) {
    swipeOn = on;
    if (!on && topOv && map && map.hasLayer(topOv)) map.removeLayer(topOv);
    dom.swipe.hidden = !on;
    dom.divider.hidden = !on;
    dom.chipL.hidden = !on;
    dom.chipR.hidden = !on;
    if (!on && map && map.getPane('caseTop')) map.getPane('caseTop').style.clipPath = '';
    if (on) clipTop();
  }

  // Clip the top picture to the left of the divider. Coordinates in layer points, as compare.js does.
  function clipTop() {
    if (!swipeOn || !map || !topOv || !map.hasLayer(topOv)) return;
    var pane = map.getPane('caseTop');
    if (!pane) return;
    var size = map.getSize();
    var x = size.x * swipePct / 100;
    var nw = map.containerPointToLayerPoint([0, 0]);
    var se = map.containerPointToLayerPoint(size);
    var cx = nw.x + x;
    pane.style.clipPath = polyCss([[nw.x, nw.y], [cx, nw.y], [cx, se.y], [nw.x, se.y]]);
    dom.divider.style.left = swipePct + '%';
  }

  function clearVectorsAndRings() {
    if (vec) vec.clearLayers();
    ring = null;
  }

  function setClassOverlay(id, layer, on) {
    if (!map) return;
    if (on && !classOvs[id] && layer && layer.png) {
      classOvs[id] = L.imageOverlay(layerUrl(layer), layer.bounds, { pane: 'caseClass', opacity: 0.85, interactive: false }).addTo(map);
    } else if (!on && classOvs[id]) {
      map.removeLayer(classOvs[id]);
      delete classOvs[id];
    }
  }
  function syncClassOverlay(id, layer) { setClassOverlay(id, layer, !!classOn[id]); }
  function removeClassOverlays() {
    Object.keys(classOvs).forEach(function (id) { setClassOverlay(id, null, false); });
  }

  /* ---------------- figure per chapter ---------------- */
  function caption(c) {
    if (!dom.figcap) return;
    dom.figcap.textContent = '';
    if (!c) { dom.figcap.appendChild(el('p', 'case-cap__note', T('case.missing'))); return; }
    var head = el('div', 'case-cap__head');
    head.appendChild(el('span', 'chip ' + (c.nisar ? 'chip--nisar' : 'chip--context'), c.nisar ? T('case.chip.nisar') : T('case.chip.context')));
    head.appendChild(el('span', 'case-cap__name', c.name || ''));
    if (c.date) head.appendChild(el('span', 'case-cap__date', c.date));
    dom.figcap.appendChild(head);
    if (c.meta) dom.figcap.appendChild(el('p', 'case-cap__meta', c.meta));
    [[T('case.cap.shows'), c.shows], [T('case.cap.cant'), c.limit], [T('case.cap.source'), c.credit]].forEach(function (r) {
      if (!r[1]) return;
      var row = el('dl', 'case-cap__row');
      row.appendChild(el('dt', null, r[0]));
      row.appendChild(el('dd', null, r[1]));
      dom.figcap.appendChild(row);
    });
    if (c.sample) dom.figcap.appendChild(el('span', 'tag-sample', T('case.cap.tag_image')));
    if (c.note) dom.figcap.appendChild(el('p', 'case-cap__note', c.note));
  }

  function layerCaption(layer, note) {
    if (!layer) return null;
    return {
      nisar: layer.type === 'nisar' || layer.chip === 'nisar',
      name: layer.name,
      date: fmtDate(layer.date),
      meta: layer.track != null ? T('case.cap.track', { track: layer.track, frame: layer.frame }) : '',
      shows: layer.shows,
      limit: layer.limit,
      credit: layer.credit,
      sample: !!(layer.placeholder && layer.placeholder.is),
      note: note || ''
    };
  }

  function figStart() {
    if (!showLayer(lay.eye)) return caption(null);
    var c = eyeLatLng();
    if (c) vec.addLayer(L.circleMarker(c, { pane: 'caseVec', radius: 16, color: colour('--teal-onmap'), weight: 2.5, fill: false, interactive: false }));
    caption(layerCaption(lay.eye));
  }

  function figAbove() {
    var viirs = App.layerById('gibs_viirs_truecolor');
    if (!data.viirs || !showBase(data.viirs, data.viirsBounds)) return caption(null);
    var track = (data.track && data.track.features) || [];
    track.forEach(function (f, i) {
      var g = f.geometry || {}, p = f.properties || {};
      if (g.type === 'LineString') {
        vec.addLayer(L.polyline(g.coordinates.map(function (c) { return [c[1], c[0]]; }), {
          pane: 'caseVec', color: colour('--teal-onmap'), weight: 3, interactive: false
        }));
      } else if (g.type === 'Point') {
        var c = g.coordinates;
        var time = (p.time_utc && !/\//.test(p.time_utc)) ? App.fmt.dateTime(p.time_utc, 'IST') : '';
        var label = time ? T('case.above.fix', { n: i, time: time }) : T('case.above.fix_none', { n: i });
        var m = L.circleMarker([c[1], c[0]], {
          pane: 'caseVec', radius: 5, color: colour('--teal-onmap'), weight: 1.5,
          fillColor: colour('--stage'), fillOpacity: 1
        });
        m.bindTooltip(label, { direction: 'top' });
        vec.addLayer(m);
      }
    });
    if (ev.landfall && ev.landfall.lat != null) {
      var lf = L.circleMarker([ev.landfall.lat, ev.landfall.lon], {
        pane: 'caseVec', radius: 9, color: colour('--card'), weight: 2.5, fill: false
      });
      lf.bindTooltip(T('case.above.landfall') + ': ' + (ev.landfall.time_utc
        ? App.fmt.dateTime(ev.landfall.time_utc, 'IST') : T('state.landfall_pending')), { direction: 'top' });
      vec.addLayer(lf);
    }
    caption(viirs ? {
      nisar: false, name: viirs.name, date: fmtDate(data.viirsDate), shows: viirs.shows,
      limit: viirs.limit, credit: viirs.credit, sample: false, note: ''
    } : null);
  }

  function figClouds() {
    var ok = swipeTo(lay.calm, lay.eye, T('case.clouds.left', { date: fmtDate(lay.calm && lay.calm.date) }),
                     T('case.clouds.right', { date: fmtDate(lay.eye && lay.eye.date) }));
    caption(ok ? layerCaption(lay.eye) : null);
  }

  function figRough() {
    if (!showLayer(lay.eye)) return caption(null);
    var c = eyeLatLng();
    if (c && peak) {
      ring = L.circle(c, { pane: 'caseVec', radius: peak.r_km * 1000, color: colour('--teal-onmap'), weight: 2.5, fill: false, interactive: false });
      vec.addLayer(ring);
      if (!chartOk) {
        STATIC_KM.forEach(function (km) {
          vec.addLayer(L.circle(c, {
            pane: 'caseVec', radius: km * 1000, color: colour('--on-stage-muted'), weight: 1.5,
            dashArray: '6 6', fill: false, interactive: false
          }));
        });
      }
      selectIndex(profilePoints().indexOf(peak));
    }
    caption(layerCaption(lay.eye));
  }

  function figShore() {
    var ok = swipeTo(lay.coastBefore, lay.coastAfter, T('case.shore.left', { date: fmtDate(lay.coastBefore && lay.coastBefore.date) }),
                     T('case.shore.right', { date: fmtDate(lay.coastAfter && lay.coastAfter.date) }));
    if (!ok) return caption(null);
    Object.keys(classOn).forEach(function (id) {
      if (classOn[id]) syncClassOverlay(id, App.layerById(id));
    });
    caption(layerCaption(lay.coastAfter));
  }

  function figRadar() {
    if (!showLayer(lay.eye)) return caption(null);
    caption(layerCaption(lay.eye, T('case.radar.fig_note')));
  }

  function figAbout() {
    if (!showLayer(lay.coastAfter)) return caption(null);
    caption(layerCaption(lay.coastAfter));
  }

  var FIGURES = {
    start: figStart, above: figAbove, clouds: figClouds, rough: figRough,
    shore: figShore, radar: figRadar, about: figAbout
  };

  function setFigure(key) {
    if (!map) return;
    clearVectorsAndRings();
    removeClassOverlays();
    setSwipe(false);
    (FIGURES[key] || FIGURES.start)();
  }

  /* ---------------- rough chart and ring ---------------- */
  function buildChart() {
    var p = profilePoints();
    if (!p.length || !window.Chart || !dom.canvas) return false;
    var teal = colour('--teal'), tint = colour('--teal-tint'), ink2 = colour('--ink-2'), muted = colour('--muted'), line = colour('--line');
    chart = new window.Chart(dom.canvas, {
      type: 'line',
      data: {
        labels: p.map(function (q) { return q.r_km; }),
        datasets: [
          { label: 'lower', data: p.map(function (q) { return q.db - q.err; }), borderWidth: 0, pointRadius: 0, fill: false },
          { label: 'upper', data: p.map(function (q) { return q.db + q.err; }), borderWidth: 0, pointRadius: 0, fill: '-1', backgroundColor: tint },
          { label: 'rise', data: p.map(function (q) { return q.db; }), borderColor: teal, backgroundColor: teal,
            borderWidth: 2.5, pointRadius: 0, pointHoverRadius: 5, tension: 0.3, fill: false }
        ]
      },
      options: {
        animation: false,
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        events: ['mousemove', 'mouseout', 'click', 'touchstart', 'touchmove'],
        plugins: { legend: { display: false }, tooltip: { enabled: false } },
        scales: {
          x: { title: { display: true, text: T('case.rough.axis_x'), color: ink2 }, ticks: { color: muted, maxTicksLimit: 8 }, grid: { color: line } },
          y: { title: { display: true, text: T('case.rough.axis_y'), color: ink2 }, ticks: { color: muted }, grid: { color: line } }
        },
        onHover: function (e, els) { if (els && els.length) selectIndex(els[0].index); },
        onClick: function (e, els) { if (els && els.length) selectIndex(els[0].index); }
      }
    });
    return true;
  }

  function selectIndex(i) {
    var p = profilePoints()[i];
    if (!p) return;
    if (dom.readout) {
      dom.readout.textContent = T('case.rough.readout', {
        km: p.r_km, db: signed(p.db), err: (Math.round(p.err * 10) / 10).toFixed(1)
      });
    }
    if (ring) ring.setRadius(p.r_km * 1000);
  }

  function fillStats() {
    if (!dom.stats) return;
    dom.stats.textContent = '';
    dom.tagRow.textContent = '';
    var p = data.profile;
    if (!p) { dom.stats.appendChild(el('p', 'case-note', T('case.missing'))); return; }
    function tile(value, sub, teal) {
      var t = el('div', 'case-stat');
      t.appendChild(el('span', 'case-stat__value' + (teal ? ' case-stat__value--teal' : ''), value));
      t.appendChild(el('span', 'case-stat__sub', sub));
      dom.stats.appendChild(t);
    }
    var radiusErr = p.eye_radius_err;
    tile(T('case.value.km', { n: p.eye_radius_km }), pm(radiusErr) + ' · ' + T('case.rough.stat.radius'), false);
    if (peak) {
      tile(T('case.value.db', { n: signed(peak.db) }), pm(peak.err) + ' · ' + T('case.rough.stat.peak', { km: peak.r_km }), true);
    }
    tile(T('case.value.km', { n: p.imd_offset_km }), T('case.stat.no_err') + ' · ' + T('case.rough.stat.offset'), false);
    if (p.placeholder && p.placeholder.is) dom.tagRow.appendChild(tagSample());
  }

  /* ---------------- open the workspace with the coast pair ---------------- */
  function openInWorkspace() {
    if (!ev || !lay.coastBefore || !lay.coastAfter) return;
    App.applyEvent(ev.id);
    App.setState({ view: 'workspace' });
    App.setState({ compare: { on: true, a: lay.coastBefore.id, b: lay.coastAfter.id } });
  }

  /* ---------------- chapter steps ---------------- */
  function goIndex(i) {
    if (isNaN(i) || i < 0 || i >= KEYS.length || i === current) return;
    current = i;
    dom.railBtns.forEach(function (b, j) {
      var on = j === i;
      b.classList.toggle('is-current', on);
      if (on) b.setAttribute('aria-current', 'step'); else b.removeAttribute('aria-current');
    });
    setFigure(KEYS[i]);
  }

  // The active chapter is the last step whose top is at or above 30% of the story column's visible
  // height. It is measured with getBoundingClientRect, once per frame at most. Scrollama, the
  // IntersectionObserver fallback, scroll and resize only ask for a check; they never pick a chapter.
  function nearestStep() {
    var story = dom.story;
    if (!story || !dom.steps || !dom.steps.length) return -1;
    var line = story.getBoundingClientRect().top + story.clientHeight * 0.3;
    var pick = 0;
    dom.steps.forEach(function (s, i) {
      if (s.getBoundingClientRect().top <= line) pick = i;
    });
    return pick;
  }
  function syncActive() {
    activeRaf = 0;
    if (lockIndex != null) return;          // a rail click is still scrolling to its chapter
    goIndex(nearestStep());
  }
  function requestActive() {
    if (!activeRaf) activeRaf = requestAnimationFrame(syncActive);
  }

  function goStep(i) {
    var s = dom.steps && dom.steps[i];
    if (s && dom.story) {
      // place the chapter a fifth of the way down the column, but never under the sticky rail, and
      // always above the 30% line that decides the active chapter, so the clicked button stays active
      var railH = dom.rail ? dom.rail.offsetHeight : 0;
      var top = s.offsetTop - Math.max(railH + 8, Math.round(dom.story.clientHeight * 0.2));
      if (typeof dom.story.scrollTo === 'function') dom.story.scrollTo({ top: Math.max(0, top), behavior: 'smooth' });
      else dom.story.scrollTop = Math.max(0, top);
    }
    lockIndex = i;
    clearTimeout(lockTimer);
    lockTimer = setTimeout(function () { lockIndex = null; requestActive(); }, 1200);
    goIndex(i);
  }

  function refreshFigure() {
    var c = current < 0 ? 0 : current;
    current = -1;
    goIndex(c);
  }

  function setupIO() {
    if (typeof window.IntersectionObserver !== 'function') return false;
    // only a trigger: the chapter itself is always picked by nearestStep()
    var io = new IntersectionObserver(requestActive, { root: dom.story, rootMargin: '-20% 0px -60% 0px', threshold: 0 });
    dom.steps.forEach(function (s) { io.observe(s); });
    return true;
  }

  function setupScroll() {
    var haveIO = typeof window.IntersectionObserver === 'function';
    dom.story.addEventListener('scroll', requestActive, { passive: true });
    window.addEventListener('resize', requestActive);
    loadScript(SCROLLAMA_URL).then(function (ok) {
      if (ok && haveIO && typeof window.scrollama === 'function') {
        try {
          var sc = window.scrollama();
          sc.setup({ step: '#case-story .case-step', offset: 0.3, root: dom.story, container: dom.story })
            .onStepEnter(requestActive);
          window.addEventListener('resize', debounce(function () { sc.resize(); }, 150));
          scrollMode = 'scrollama';
          requestActive();
          return;
        } catch (e) {
          console.warn('[case] Scrollama setup failed, using IntersectionObserver', e);
        }
      }
      scrollMode = setupIO() ? 'io' : 'rail';
      requestActive();
    });
  }

  /* ---------------- build and open ---------------- */
  function build() {
    built = true;
    if (typeof L === 'undefined') { root.textContent = ''; root.appendChild(el('p', 'case-msg', T('case.no_map'))); return; }
    if (!pickLayers()) { root.textContent = ''; root.appendChild(el('p', 'case-msg', T('case.no_event'))); return; }
    buildDom();
    buildMap();
    goIndex(0);
    setupScroll();
    Promise.all([loadData(), ensureChart()]).then(function (res) {
      peak = computePeak();
      if (dom.aboveBody) dom.aboveBody.textContent = T('case.above.body', { date: fmtDate(data.viirsDate) });
      chartOk = res[1] ? buildChart() : false;
      if (dom.chartFallback) dom.chartFallback.hidden = chartOk;
      // no chart: hide the empty canvas, the readout and the notes that talk about moving along it
      if (dom.chartBox) dom.chartBox.hidden = !chartOk;
      if (dom.readout) dom.readout.hidden = !chartOk;
      (dom.chartNotes || []).forEach(function (n) { n.hidden = !chartOk; });
      fillStats();
      if (chartOk && peak) selectIndex(profilePoints().indexOf(peak));
      else if (dom.readout && peak) dom.readout.textContent = '';
      refreshFigure();
    });
    requestAnimationFrame(function () { if (map) map.invalidateSize(); });
  }

  function openView() {
    if (!built) { build(); return; }
    requestAnimationFrame(function () {
      if (!map) return;
      map.invalidateSize();
      refreshFigure();
    });
  }

  var onResize = debounce(function () {
    if (!map || !root || root.offsetWidth === 0) return;
    map.invalidateSize();
    refreshFigure();
  }, 200);

  function init(rootEl) {
    root = rootEl || document.getElementById('case-root');
    if (!root) return;
    App.on('view', function (v) { if (v === 'case') openView(); });
    window.addEventListener('resize', onResize);
    if (App.state.view === 'case') openView();
  }

  App.case = { init: init };
})();
