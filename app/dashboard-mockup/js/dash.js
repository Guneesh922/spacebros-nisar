/* Dashboard mockup logic. Plain JS, no build. Words live in js/findings.js (FINDINGS). */
(function () {
  'use strict';
  var D = '../../data/processed/';
  var F = window.FINDINGS;
  var SAMPLE = 'Sample values', QUICK = 'Quick-look sample';
  var ROLES = ['coast', 'sea'], STORE_KEY = 'spacebros.nisar.savedDays.v1';
  var DELTA = [[16.2, 81.5], [17.25, 82.7]], SEA = [[15.3, 81.5], [17.7, 84.0]];
  var SHARE_MAX = 15, GRAY = [-25, 0];
  var MODES = [['share', 'Flood share'], ['radar', 'Radar, after'], ['swipe', 'Before and after'], ['eye', 'Cyclone eye']];

  var S = { section: 'happened', mapMode: 'share', shareD: null, rankBy: 'water', histId: null, fm: false, sel: null, swipe: 50, showAll: false, storyD: null, evOpen: {}, sort: { k: 'rank', d: 1 }, q: '', role: 'coast', dates: {}, dEye: null, prevMode: null, saved: [], storeOK: true, notice: '', undo: null };
  var X = {};                                  // loaded data
  var vis = { img: {}, before: null, outlines: true, track: true };
  var ready = false, hashTimer = null, lastHash = '', missing = {}, map, imgs = {}, imgsB = {}, mandLayer, featByName = {}, trackGrp, eyeGrp, hoverRing, built = {};

  function $(s, r) { return (r || document).querySelector(s); }
  function $$(s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function css(n) { return getComputedStyle(document.documentElement).getPropertyValue(n).trim(); }
  function fill(t, v) { return t.replace(/\{(\w+)\}/g, function (m, k) { return v[k] != null ? v[k] : m; }); }
  function n0(x) { return Math.round(x); }
  function n1(x) { return (Math.round(x * 10) / 10).toFixed(1); }
  function tag(t) { return '<span class="tag-sample">' + esc(t) + '</span>'; }
  function info(t) { return '<i class="info" tabindex="0" role="note" data-tip="' + esc(t) + '">?</i>'; }
  function ist(iso) {
    var d = new Date(iso); if (isNaN(d)) return iso;
    return d.toLocaleString('en-GB', { timeZone: 'Asia/Kolkata', day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }) + ' IST';
  }
  function dshort(iso) { var d = new Date(iso + 'T00:00:00Z'); return isNaN(d) ? iso : d.toLocaleDateString('en-GB', { timeZone: 'UTC', day: 'numeric', month: 'short', year: 'numeric' }); }
  function niceName(n) { return F.aliases && F.aliases[n] ? n + ' (' + F.aliases[n] + ')' : n; }
  function shortDist(d) { return /Konaseema/.test(d) ? 'Konaseema' : d; }
  var WORDS = ['', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten'];
  function timesWords(r) {
    if (r < 0.8) return 'less';
    if (r < 1.25) return null;
    if (r < 1.75) return 'about one and a half times';
    if (r < 2.5) return 'about twice';
    var n = Math.round(r); return n > 10 ? 'more than ten times' : 'about ' + WORDS[n] + ' times';
  }
  function mapRow(r) {
    var w = r.water_pct, e = r.water_err, nw = r.normal_water_pct != null ? r.normal_water_pct : r.normal_pct;
    var tot = r.total_pct != null ? r.total_pct : w + (r.crops_pct || 0), te = r.total_err != null ? r.total_err : Math.hypot(e || 0, r.crops_err || 0);
    return { mandal: r.mandal, district: r.district, water: w, we: e, crops: r.crops_pct || 0, ce: r.crops_err || 0, tot: tot, te: te,
             lik: w, err: e, normal: nw, normalT: r.normal_pct, ratio: nw > 0 ? w / nw : Infinity,
             km: r.water_km2, kmT: r.flooded_km2, area: r.area_km2, chg: r.water_change_vs_normal_pp, chgT: r.change_vs_normal_pp, cover: r.coverage_pct,
             rank: r.rank_water != null ? r.rank_water : (r.rank_water === undefined ? r.rank : null), rankT: r.rank };
  }
  function storyOK() { return !!(X.story && (X.story.schema === 'story-v1' || X.story.schema === 'findings-v1') && X.story.headline); }
  /* UI text from app/strings/strings.en.json (flat keys); the second argument is a neutral fallback */
  function T(k, fb) { return (X.ui && X.ui[k]) || fb || ''; }
  function tl(iso) { if (!iso) return 'an unknown time'; var d = new Date(iso); return isNaN(d) ? String(iso) : ist(iso); }
  function areaCfg() {
    var c = X.cfg, as = (c && c.areas) || [], id = (X.latest && X.latest.area_id) || (c && c.default_area);
    return as.filter(function (a) { return a.id === id; })[0] || as[0] || null;
  }
  function areaName() { var a = areaCfg(); return a ? a.name : ''; }
  function latestPassDate() {
    var s = X.latest; if (!s) return null;
    if (s.pass && s.pass.date) return s.pass.date;
    if (s.scene && s.scene.date) return s.scene.date;
    return s.data_as_of ? String(s.data_as_of).slice(0, 10) : null;
  }
  function chipsOf(s) {
    if (!s) return [];
    var a = (s.event_chips && s.event_chips.length) ? s.event_chips : (s.event_chip ? [s.event_chip] : []);
    return a.filter(function (c) { return c && c.text; });
  }
  function eventById(id) { return (X.events || []).filter(function (e) { return e.id === id; })[0] || null; }
  function hasLang(t) { return /[\u0C00-\u0C7F]/.test(t || '') ? ' lang="te"' : ''; }
  function storyHas(nm) { return !!(storyOK() && X.story.mandal_sentences && X.story.mandal_sentences[nm]); }
  function hasM(nm) { return !!(nm && ((X.byName && X.byName[nm]) || storyHas(nm))); }
  function rankSample() { return !!((X.rank && X.rank.placeholder && X.rank.placeholder.is) || (storyOK() && X.story.badges && X.story.badges.sample)); }
  function rankTag() { return rankSample() ? tag((X.rank && X.rank.placeholder && X.rank.placeholder.tag) || SAMPLE) : ''; }
  function profSample() { return !!(X.profile && X.profile.placeholder && X.profile.placeholder.is); }
  function layerSample(l) { return !!(l && l.placeholder && l.placeholder.is); }
  function sampleWord() { return rankSample() ? ' (sample)' : ''; }
  function getJSON(u) { return fetch(u).then(function (r) { if (!r.ok) throw new Error(u + ' ' + r.status); return r.json(); }); }

  /* ---------------- load ---------------- */
  X.warn = [];
  function opt(u, what) { return getJSON(u).catch(function (e) { X.warn.push(what); console.warn(e.message); return null; }); }
  function soft(u) { return getJSON(u).catch(function () { return null; }); }
  /* first URL that loads wins; null if none (the 404 of a missing first file is the only noise) */
  function firstJSON(urls) { var p = Promise.reject(new Error('start')); urls.forEach(function (u) { p = p.catch(function () { return getJSON(u); }); }); return p.catch(function () { return null; }); }
  var FD = '../../data/processed/findings/';
  Promise.all([getJSON(D + 'manifest.json'), getJSON(D + 'mandals.geojson'), opt(D + 'mandal_rank.json', 'mandal_rank.json'),
               opt(D + 'profile.json', 'profile.json'), opt(D + 'alerts.json', 'alerts.json'), opt(D + 'imd_track_arnab.geojson', 'imd_track_arnab.geojson'),
               getJSON('../../data/h5/catalog.json').catch(function (e) { console.warn(e.message); return null; }),
               firstJSON([FD + 'latest.json', '../../data/web/story.json']),
               soft(D + 'events.json'), soft('../../config/areas.json'),
               soft('../strings/story.en.json'), soft('../strings/strings.en.json')])
    .then(function (a) {
      X.manifest = a[0]; X.mandals = a[1]; X.rank = a[2]; X.profile = a[3]; X.alerts = a[4]; X.track = a[5]; X.catalog = a[6];
      X.story = a[7]; X.latest = a[7]; X.events = (a[8] && a[8].events) || []; X.cfg = a[9]; X.str = a[10] || {}; X.ui = a[11] || {};
      if (!X.story) console.warn('No findings file and no story.json: the home tab shows the neutral message.');
      init();
    })
    .catch(function (e) {
      var b = $('#banner'); b.hidden = false;
      b.setAttribute('role', 'alert'); b.textContent = 'The data files could not be loaded (' + e.message + '). Serve the repo root with "python3 -m http.server 8000" and open http://localhost:8000/app/dashboard-mockup/ .';
      console.error(e);
    });

  function init() {
    var m = X.manifest;
    $('#hdr-meta').textContent = 'Radar layers built ' + ist(m.generated_utc);
    $('#hdr-meta').classList.remove('is-loading');
    // title and tagline come from config/areas.json (site.title / site.tagline); the HTML holds neutral defaults
    var site = (X.cfg && X.cfg.site) || {};
    if (site.title) { document.title = site.title; $('.hdr__title').textContent = site.title; }
    if (site.tagline) $('.hdr__sub').textContent = site.tagline;
    if (areaName()) $('#map').setAttribute('aria-label', 'Map of ' + areaName());
    // dates that have a frozen findings file (coast passes listed in the archive) and the newest pass date
    X.fdates = {}; X.fcache = {};
    ((X.latest && X.latest.updates) || []).forEach(function (u) { if (u.kind !== 'sea' && u.date) X.fdates[u.date] = true; });
    if (latestPassDate()) { X.fdates[latestPassDate()] = true; X.fcache[latestPassDate()] = X.latest; }
    X.rowsBy = {}; X.series = {}; X.shareDates = [];
    var rk = X.rank || {}, latest = rk.latest_date;
    function mapRows(list) {
      var rows = (list || []).map(mapRow).filter(function (r) { return r.rank != null; }).sort(function (a, b) { return a.rank - b.rank; }), by = {};
      rows.forEach(function (r) { by[r.mandal] = r; });
      return { rows: rows, byName: by };
    }
    if (rk.by_date) Object.keys(rk.by_date).sort().forEach(function (d) {
      var b = rk.by_date[d]; X.rowsBy[d] = mapRows(b.rows); X.shareDates.push(d);
      (b.rows || []).forEach(function (r) { (X.series[r.mandal] = X.series[r.mandal] || []).push({ d: d, w: r.water_pct, e: r.water_err }); });
    });
    var top = mapRows(rk.rows);
    if (latest) { X.rowsBy[latest] = top; if (X.shareDates.indexOf(latest) < 0) { X.shareDates.push(latest); X.shareDates.sort(); (rk.rows || []).forEach(function (r) { (X.series[r.mandal] = X.series[r.mandal] || []).push({ d: latest, w: r.water_pct, e: r.water_err }); }); } }
    X.rows = top.rows; X.byName = top.byName;
    X.maxLik = Math.max(15, Math.ceil((X.rows.length ? X.rows[0].lik : 0) / 5) * 5);
    X.sparkMax = Math.max(5, X.rows.reduce(function (m, r) { return Math.max(m, r.water); }, 0));
    X.hasProf = !!(X.profile && X.profile.points && X.profile.points.length && X.profile.eye);
    X.peak = null;
    if (X.hasProf) { var pts = X.profile.points, pk = pts[0]; pts.forEach(function (p) { if (p.db > pk.db) pk = p; }); X.peak = pk; }
    X.layers = {}; m.layers.forEach(function (l) { X.layers[l.id] = l; });
    X.event = (m.events && m.events[0]) || { landfall: null, dates: {} };
    S.sel = X.rows.length ? X.rows[0].mandal : null;
    buildScenes(); setDefaults();
    S.saved = loadSaved();

    initMap();
    buildHappened();
    buildData();
    bindUI();
    buildDayCard(); bindDay();
    if (X.warn.length) {
      var b = $('#banner'); b.hidden = false; b.setAttribute('role', 'status');
      b.textContent = 'Some files are not ready yet (' + X.warn.join(', ') + '). The parts that need them show as unavailable; the rest works.';
    }
    applyView(parseHash());
    ready = true; writeHash(true);
    preloadFindings();
    if (window.ResizeObserver) new ResizeObserver(function () {
      if (!mapReady()) return;
      map.invalidateSize({ animate: false });
      if (S.pendingFit) fitFor(S.pendingFit);
      if (S.pendingView) { var pv = S.pendingView; S.pendingView = null; if (validView(pv)) map.setView([pv.c[0], pv.c[1]], pv.z, { animate: false }); }
    }).observe($('#map'));
    // test hook: window.__spacebros.setStory(obj) re-renders the public tab from a modified story object (null = built-in text)
    window.__spacebros = { story: function () { return X.story; }, setStory: function (s) { X.story = s; buildHappened(); if (S.sel) selectMandal(S.sel, {}); } };
    window.addEventListener('hashchange', function () {
      if (location.hash === lastHash) return;
      var h = location.hash.replace(/^#/, '');
      if (h.indexOf('=') < 0 && h !== 'data' && h !== 'happened') { writeHash(); return; }   // an in-page jump link, not a saved view
      applyView(parseHash());
    });
  }

  /* ---------------- map ---------------- */
  function initMap() {
    map = L.map('map', { zoomControl: false, zoomSnap: 0.25, attributionControl: true });
    map.attributionControl.setPrefix(false);
    L.control.zoom({ position: 'bottomright' }).addTo(map);
    L.control.scale({ position: 'bottomright', imperial: false, maxWidth: 110 }).addTo(map);
    try {
      L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',
        { maxNativeZoom: 16, maxZoom: 18, opacity: 0.7, attribution: 'Map data: Esri, HERE, Garmin, OpenStreetMap contributors', errorTileUrl: '' }).addTo(map);
    } catch (e) { console.warn('basemap unavailable', e); }
    map.createPane('radar').style.zIndex = 350;
    map.createPane('radar2').style.zIndex = 351;
    map.fitBounds(DELTA);

    // mandal polygons (name match; for duplicates prefer the one in the ranked district)
    mandLayer = L.geoJSON(X.mandals, {
      style: mStyle,
      onEachFeature: function (f, lyr) {
        var nm = f.properties.name;
        var r = X.byName[nm];
        if (r ? (!featByName[nm] || (f.properties.district && f.properties.district === r.district)) : (storyHas(nm) && !featByName[nm])) featByName[nm] = lyr;
        lyr.on('click', function () { if (hasM(nm)) selectMandal(nm, { fly: false, user: true }); });
        lyr.bindTooltip(function () {
          var rr = shadeRow(nm);
          return '<span>' + esc(nm) + (rr ? ': about ' + n0(rr.lik) + '% probably under water' + sampleWord() : '') + '</span>';
        }, { sticky: true, className: 'map-tip' });
      }
    });

    // track, eye, landfall
    trackGrp = L.layerGroup(); eyeGrp = L.layerGroup();
    var line = X.track && X.track.features ? X.track.features.filter(function (f) { return f.geometry.type === 'LineString'; })[0] : null;
    if (line) L.polyline(line.geometry.coordinates.map(function (c) { return [c[1], c[0]]; }),
      { color: css('--on-stage-muted'), weight: 2.5, dashArray: '6 6', opacity: 0.95 }).bindTooltip('Cyclone path (IMD fixes joined by straight lines)', { sticky: true, className: 'map-tip' }).addTo(trackGrp);
    var lf = X.event.landfall;
    if (lf) L.circleMarker([lf.lat, lf.lon], { radius: 7, color: css('--white'), weight: 2, fillColor: css('--stage'), fillOpacity: 1 })
      .bindTooltip('Landfall area. ' + (lf.time_utc ? ist(lf.time_utc) : 'Time being confirmed (IMD)'), { className: 'map-tip' }).addTo(trackGrp);
    var eye = X.hasProf ? X.profile.eye : null;
    if (eye) L.circle(eye, { radius: X.profile.eye_radius_km * 1000, color: css('--teal-onmap'), weight: 2, fill: false })
      .bindTooltip('Calm eye, about ' + X.profile.eye_radius_km + ' km radius' + (profSample() ? ' (sample)' : ''), { sticky: true, className: 'map-tip' }).addTo(eyeGrp);
    if (eye) L.circle(eye, { radius: X.peak.r_km * 1000, color: css('--teal-onmap'), weight: 1.5, dashArray: '3 5', fill: false })
      .bindTooltip('Roughest sea, about ' + X.peak.r_km + ' km from the centre' + (profSample() ? ' (sample)' : ''), { sticky: true, className: 'map-tip' }).addTo(eyeGrp);
    if (eye) L.circleMarker(eye, { radius: 3, color: css('--teal-onmap'), fillColor: css('--teal-onmap'), fillOpacity: 1, weight: 1 }).addTo(eyeGrp);

    map.on('move zoomend resize', clipBefore);
    map.on('moveend', function () { writeHash(); });
  }

  function shadeRows() { var d = shareDate(); return (X.rowsBy[d] || X.rowsBy[Object.keys(X.rowsBy).sort().pop()] || { byName: X.byName }).byName; }
  function shadeRow(nm) { return shadeRows()[nm]; }
  function mStyle(f) {
    var nm = f.properties.name, r = shadeRow(nm), known = !!(X.byName[nm] || storyHas(nm));
    var sel = known && S.sel === nm && featByName[nm] && featByName[nm].feature === f;
    var share = S.mapMode === 'share' && r;
    var base = { color: css('--on-stage-muted'), weight: known ? 1 : 0.6, opacity: known ? 0.7 : 0.3, fillColor: css('--water'), fillOpacity: share ? 0.1 + 0.6 * Math.min(1, r.lik / SHARE_MAX) : (known ? 0.02 : 0) };
    if (sel) { base.color = css('--white'); base.weight = 3; base.opacity = 1; }
    return base;
  }

  function overlay(id, second) {
    var store = second ? imgsB : imgs, l = X.layers[id];
    if (!isImg(l)) return null;
    if (!store[id]) {
      var o = L.imageOverlay('../../' + l.png, l.bounds, { pane: second ? 'radar2' : 'radar', opacity: 0.9, alt: l.name });
      o.on('add', clipBefore);
      o.on('error', function () {
        missing[id] = true; if (S.mapMode === 'custom') delete vis.img[id];
        [imgs[id], imgsB[id]].forEach(function (x) { if (x && map.hasLayer(x)) map.removeLayer(x); });
        applyMap();
      });
      store[id] = o;
    }
    return store[id];
  }
  function syncOverlays(store, want, second) {
    Object.keys(want).forEach(function (id) {
      if (missing[id]) return;
      var o = overlay(id, second); if (!o) return;
      o.setOpacity(want[id] === true ? 0.9 : want[id]); if (!map.hasLayer(o)) o.addTo(map);
    });
    Object.keys(store).forEach(function (id) { if (!want[id] && map.hasLayer(store[id])) map.removeLayer(store[id]); });
  }

  function clipBefore() {
    var o = S.mapMode === 'swipe' && vis.before ? imgsB[vis.before] : null;
    if (!o || !map.hasLayer(o) || !o.getElement()) return;
    var e = o.getElement();
    var sz = map.getSize(), x = sz.x * S.swipe / 100;
    var nw = map.containerPointToLayerPoint([0, 0]), p = map.containerPointToLayerPoint([x, 0]), se = map.containerPointToLayerPoint(sz);
    var pos = L.DomUtil.getPosition(e) || L.point(0, 0);
    e.style.clip = 'rect(' + (nw.y - pos.y) + 'px,' + (p.x - pos.x) + 'px,' + (se.y - pos.y) + 'px,' + (nw.x - pos.x) + 'px)';
  }

  function computeVis() {
    var m = S.mapMode; if (m === 'custom') return;
    vis.img = {}; vis.before = null; vis.outlines = true; vis.track = true;
    var o = viewIds();
    if (m === 'share') { if (o.after) vis.img[o.after] = 0.35; if (o.cls) vis.img[o.cls] = 0.8; }
    if ((m === 'radar' || m === 'eye') && o.after) vis.img[o.after] = 0.9;
    if (m === 'swipe') { if (o.after) vis.img[o.after] = 0.9; vis.before = o.before; }
  }

  function capVars() {
    var o = viewIds(), la = o.after && X.layers[o.after], lb = o.before && X.layers[o.before];
    return { date: la ? dshort(la.date) : 'the chosen date', after: la ? dshort(la.date) : '?', before: lb ? dshort(lb.date) : '?', what: S.role === 'sea' ? 'sea' : 'land' };
  }

  function applyMap() {
    var want = {}, wantB = {};
    Object.keys(vis.img).forEach(function (id) { if (vis.img[id]) want[id] = vis.img[id]; });
    if (S.mapMode === 'swipe' && vis.before) wantB[vis.before] = 0.9;
    syncOverlays(imgs, want, false); syncOverlays(imgsB, wantB, true);
    toggleLayer(mandLayer, vis.outlines); toggleLayer(trackGrp, vis.track); toggleLayer(eyeGrp, vis.track);
    mandLayer.setStyle(mStyle);
    if (vis.outlines) mandLayer.bringToFront();
    $('#swipe').hidden = $('#swipe-line').hidden = S.mapMode !== 'swipe';
    if (S.mapMode === 'swipe') {
      var o = viewIds(), lb = o.before && X.layers[o.before], la = o.after && X.layers[o.after];
      $('.swipe__l').textContent = (lb ? dd(lb.date) : '?') + ', before'; $('.swipe__r').textContent = (la ? dd(la.date) : '?') + ', after';
    }
    updateSwipeLine(); clipBefore();
    // legend
    $('#legend').innerHTML = legendHtml();
    // caption (dates come from the manifest layers that are on the map)
    var key = S.mapMode === 'radar' && S.role === 'sea' ? 'radar_sea' : S.mapMode;
    var c = F.captions[key] || F.captions.custom, cv = capVars(), cant = c.cant;
    if (S.mapMode === 'swipe') { var vo = viewIds(); [vo.before, vo.after].forEach(function (id) { var l = id && X.layers[id]; if (l && l.bounds_inferred) cant += ' The position of the ' + dshort(l.date) + ' frame is copied from a later pass.'; }); }
    $('#caption').innerHTML = '<div class="cap__row"><span class="cap__k">Shows</span><span>' + esc(fill(c.shows, cv)) + '</span></div><div class="cap__row"><span class="cap__k">Cannot show</span><span>' + esc(fill(cant, cv)) + '</span></div><div class="cap__row"><span class="cap__k">Source</span><span>' + esc(c.src) + '</span></div>' + capTag(key);
    var gone = Object.keys(vis.img).filter(function (id) { return vis.img[id] && missing[id]; });
    if (S.mapMode === 'swipe' && vis.before && missing[vis.before]) gone.push(vis.before);
    if (gone.length) $('#caption').insertAdjacentHTML('beforeend', '<div class="cap__miss" role="status"><b>Radar layer data not loaded yet.</b> The picture for this view is not available in this copy of the project. Outlines and numbers still work.</div>');
    $$('#map-modes button').forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.m === S.mapMode)); });
    $$('input[data-lyr]').forEach(function (cb) {
      var id = cb.dataset.lyr;
      if (missing[id]) { cb.disabled = true; cb.title = 'Layer data not loaded yet'; if (!cb.nextElementSibling) cb.insertAdjacentHTML('afterend', '<span class="sub">Not loaded yet</span>'); }
      cb.checked = id === 'mandal_boundaries' ? vis.outlines : id === 'imd_track_arnab' ? vis.track : !!vis.img[id];
    });
    markThumbs(); renderTimeline(); updateNow(); syncStory();
  }
  function capTag(key) {
    if (key === 'custom') return '';
    if (key === 'share') return rankSample() ? tag(SAMPLE) : '';
    var l = Object.keys(vis.img).filter(function (id) { return vis.img[id] && layerSample(X.layers[id]); })[0] || (S.mapMode === 'swipe' && vis.before && layerSample(X.layers[vis.before]) ? vis.before : null);
    return l ? tag(X.layers[l].placeholder.tag || QUICK) : '';
  }
  function markThumbs() { $$('.sm__i').forEach(function (b) { b.setAttribute('aria-pressed', String(!!vis.img[b.dataset.sm] && S.mapMode === 'custom')); }); }
  function legendHtml() {
    var h = '', ids = Object.keys(vis.img).filter(function (id) { return vis.img[id] && !missing[id] && X.layers[id]; }), radar = false, diff = null, cls = [];
    if (S.mapMode === 'share') h += '<b class="legend__t">Mandals: probably under water</b><div class="ramp"></div><div class="ramp-l"><span>0</span><span>' + SHARE_MAX + '+ in 100</span></div>' + rankTag();
    ids.forEach(function (id) { var l = X.layers[id]; if (l.classes && l.classes.length) cls.push(l); else if (l.ramp && l.ramp.stops) diff = l; else if (l.type === 'nisar' && S.mapMode !== 'share') radar = true; });
    if (cls.length) h += '<b class="legend__t">Map colours</b>' + cls.map(function (l) { return l.classes.map(function (c) { return '<span class="lg"><i class="sw" style="background:' + esc(c.colour) + '"></i>' + esc(c.label) + (isWeak(l) ? ' (weak signal)' : '') + '</span>'; }).join(''); }).join('');
    if (diff) { var st = diff.ramp.stops, lo = st[0].value, hi = st[st.length - 1].value; h += '<b class="legend__t">Sea brightness change (' + esc(diff.ramp.unit || 'dB') + ')</b><div class="ramp ramp--d" role="img" aria-label="Colour scale from ' + lo + ' to +' + hi + ' dB" style="background:linear-gradient(90deg,' + st.map(function (s) { return esc(s.hex) + ' ' + ((s.value - lo) / (hi - lo) * 100).toFixed(0) + '%'; }).join(',') + '"></div><div class="ramp-l"><span>' + lo + '</span><span>0</span><span>+' + hi + '</span></div><div class="ramp-l ramp-l--t"><span>' + esc(st[0].label || 'darker') + '</span><span>' + esc(st[st.length - 1].label || 'brighter') + '</span></div>'; }
    if (radar) h += '<b class="legend__t">Radar brightness (dB)</b><div class="gray" role="img" aria-label="Greyscale from dark, ' + GRAY[0] + ' dB, to bright, ' + GRAY[1] + ' dB"></div><div class="ramp-l"><span>' + GRAY[0] + ' dark</span><span>' + GRAY[1] + ' bright</span></div>';
    return h;
  }
  function toggleLayer(l, on) { if (on && !map.hasLayer(l)) l.addTo(map); if (!on && map.hasLayer(l)) map.removeLayer(l); }
  function updateSwipeLine() { $('#swipe-line').style.left = S.swipe + '%'; }

  function mapReady() { var z = map.getSize(); return z.x >= 100 && z.y >= 100; }
  function fitFor(m) {
    map.invalidateSize({ animate: false });          // size first, so the fit is not computed on a stale container
    if (!mapReady()) { S.pendingFit = m; return; }   // hidden or not laid out yet: fit when the map has a real size
    S.pendingFit = null;
    var sea = m === 'eye' || ((m === 'radar' || m === 'swipe') && S.role === 'sea');
    map.fitBounds(sea ? SEA : DELTA, { animate: false });
  }
  function setMapMode(m, fit) {
    S.mapMode = m; computeVis(); applyMap(); if (fit) fitFor(m); writeHash();
  }

  /* ---------------- selection ---------------- */
  function selectMandal(name, o) {
    o = o || {};
    if (!hasM(name)) return;
    S.sel = name; if (o.user) S.fm = true;
    if (mandLayer) mandLayer.setStyle(mStyle);
    if (featByName[name]) { featByName[name].bringToFront(); if (o.fly) map.fitBounds(featByName[name].getBounds().pad(0.5), { maxZoom: 11 }); }
    $$('.rank__item').forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.m === name)); });
    $$('#mtbody tr').forEach(function (tr) { tr.setAttribute('aria-selected', String(tr.dataset.m === name)); });
    var c = $('#mcard'); if (c) c.innerHTML = X.byName[name] ? mandalCard(X.byName[name]) : unrankedCard(name);
    if (S.fm) fmShow(name);
    writeHash();
  }

  /* ---------------- "What happened" ---------------- */
  function confOf(r) {
    var o = F.mandals && F.mandals[r.mandal];
    if (o && o.confidence) return { lvl: o.confidence, note: o.confidence_note || F.mandal['conf_note_' + o.confidence] };
    var rel = r.err / r.lik, lvl = rel < 0.2 ? 'high' : rel < 0.35 ? 'medium' : 'low';
    return { lvl: lvl, note: F.mandal['conf_note_' + lvl] };
  }
  function dots(lvl) { var n = { high: 3, medium: 2, low: 1 }[lvl]; return '<span class="conf" aria-hidden="true">' + [1, 2, 3].map(function (i) { return '<i class="' + (i <= n ? 'on' : '') + '"></i>'; }).join('') + '</span>'; }

  function waffle(w, c, rest, label, big, bg) {
    var cells = '', nw = n0(w), nc = n0(c), nr = n0(rest || 0);
    for (var i = 0; i < 100; i++) cells += '<i class="' + (i < nw ? 'w' : i < nw + nc ? 'c' : i < nw + nc + nr ? 'n' : '') + '"></i>';
    return '<div class="waffle"><div class="waffle__g" role="img" aria-label="' + esc(label) + '">' + cells + '</div><div class="waffle__cap"><b>' + big + '</b><br>' + esc(label) + '</div></div>';
  }

  function mandalCard(r) {
    var o = (F.mandals && F.mandals[r.mandal]) || {};
    var v = { lik: n0(r.lik), normal: n0(r.normal), err: n0(r.err) };
    var sen = X.story && X.story.mandal_sentences && X.story.mandal_sentences[r.mandal];
    var cf = confOf(r);
    var head = o.headline || sen || niceName(r.mandal);
    return '<div class="row row--between"><span class="eyebrow">Selected mandal \u00B7 ' + esc(shortDist(r.district)) + '</span>' + rankTag() + '</div>' +
      '<h3>' + esc(niceName(r.mandal)) + '</h3>' +
      (sen || o.headline ? '<p class="lead">' + esc(head) + '</p>' : '<p class="small">' + esc(T('dash.no_summary', 'Summary not available yet.')) + '</p>') +
      '<div class="waffles">' +
        waffle(r.water, 0, 0, 'on ' + esc(radarDay()), v.lik + ' in 100') +
        waffle(0, 0, r.normal, 'in a normal fortnight', v.normal + ' in 100') +
      '</div>' +
      '<div class="legendline"><span><i class="sw sw--w"></i>Probably open water</span><span><i class="sw sw--n"></i>Normal fortnight</span><span>Each square is 1 in 100</span></div>' +
      '<p class="small">Give or take <b>' + v.err + '</b> out of 100.' + info(F.tips.err) + '</p>' +
      '<div class="note"><b>' + dots(cf.lvl) + esc(F.mandal['conf_' + cf.lvl]) + '.</b> ' + esc(cf.note) + '</div>' +
      '<div class="note"><b>What radar cannot tell you.</b> ' + esc(o.cannot || F.mandal.cannot) + '</div>' +
      '<p class="small muted">Wet crops are not counted here: radar cannot yet tell them apart from normal change in fields (weak signal). The raw numbers list them.</p>' +
      '<div class="row"><button class="btn btn--sm" data-act="zoom">Show on the map</button>' +
      '<button class="btn btn--sm" data-act="swipe">Before and after here</button>' +
      '<button class="linkbtn small" data-act="raw">See the raw numbers</button></div>';
  }
  function radarDay() { return dshort(shareDate()); }
  function unrankedCard(name) {
    var s = X.story && X.story.mandal_sentences && X.story.mandal_sentences[name];
    return '<div class="row row--between"><span class="eyebrow">Selected mandal</span></div><h3>' + esc(niceName(name)) + '</h3>' +
      (s ? '<p class="lead">' + esc(s) + '</p>' : '') +
      '<p class="small">This mandal is not in the ranking: too little of it is inside the radar picture to compare it fairly.</p>' +
      '<div class="note"><b>What radar cannot tell you.</b> ' + esc(F.mandal.cannot) + '</div>';
  }

  function rankItem(r) {
    var max = X.maxLik || 15, w = Math.min(100, r.water / max * 100);
    var tick = Math.min(100, r.normal / max * 100), e0 = Math.max(0, (r.lik - r.err) / max * 100), e1 = Math.min(100, (r.lik + r.err) / max * 100);
    return '<li><button class="rank__item" data-m="' + esc(r.mandal) + '" aria-pressed="false">' +
      '<span class="rank__n">' + r.rank + '</span>' +
      '<span class="rank__top"><span>' + esc(niceName(r.mandal)) + '</span><span>' + n1(r.lik) + ' in 100 land</span></span>' +
      '<span class="bar" aria-hidden="true"><span class="bar__w" style="width:' + w + '%"></span>' +
      '<span class="bar__tick" style="left:' + tick + '%"></span><span class="bar__err" style="left:' + e0 + '%;width:' + (e1 - e0) + '%"></span></span></button></li>';
  }
  function renderRank() {
    if (!$('#ranklist')) return;
    var list = S.showAll ? X.rows : X.rows.slice(0, 5);
    $('#ranklist').innerHTML = list.map(rankItem).join('');
    $('#rankmore').textContent = S.showAll ? 'Show the top 5 only' : 'Show all ' + X.rows.length + ' mandals';
    selectMandal(S.sel, {});
  }

  function eyeDiagram() {
    var R = X.profile.eye_radius_km, P = X.peak.r_km, k = 70 / P;
    return '<svg class="chart" viewBox="0 0 220 160" role="img" aria-label="Diagram: calm eye in the middle, roughest sea in a wider ring" style="max-width:220px">' +
      '<circle cx="110" cy="80" r="' + P * k + '" fill="none" stroke="' + css('--teal') + '" stroke-dasharray="4 4" stroke-width="2"/>' +
      '<circle cx="110" cy="80" r="' + R * k + '" fill="' + css('--teal-tint') + '" stroke="' + css('--teal') + '" stroke-width="2"/>' +
      '<line x1="110" y1="80" x2="' + (110 + R * k) + '" y2="80" stroke="' + css('--ink') + '"/>' +
      '<text x="' + (110 + R * k / 2 - 12) + '" y="74" style="font-size:11px;fill:' + css('--ink') + '">' + R + ' km</text>' +
      '<text x="110" y="' + (80 - P * k - 5) + '" text-anchor="middle" style="font-size:11px;fill:' + css('--ink-2') + '">roughest sea ' + P + ' km out</text>' +
      '<text x="110" y="' + (80 + 14) + '" text-anchor="middle" style="font-size:11px;fill:' + css('--ink-2') + '">calm eye</text></svg>';
  }

  var OFFICIAL = [{ name: 'IMD', url: 'https://mausam.imd.gov.in/' }, { name: 'APSDMA', url: 'https://apsdma.ap.gov.in/' }, { name: 'SACHET', url: 'https://sachet.ndma.gov.in/' }];
  function officialLine() {
    var o = F.official || {}, s = X.story, ev = s && eventById(s.event_id);
    var ls = (s && s.official_links && s.official_links.length) ? s.official_links : (ev && ev.official_links && ev.official_links.length) ? ev.official_links : OFFICIAL;
    var txt = (s && s.official_banner) || o.text || 'Not an official warning. Follow IMD and APSDMA.';
    return '<p class="small muted official">' + esc(txt) + ' ' + ls.map(function (l) { return '<a href="' + esc(l.url) + '" target="_blank" rel="noopener">' + esc(l.name) + '</a>'; }).join(' · ') + '</p>';
  }
  /* ---------- live story (data/processed/findings/latest.json, or a frozen <date>.json) ---------- */
  var STR = { missing: 'Pictures are ready, numbers are coming.', stale: 'No new radar pass in {days} days. This page shows the last one, from {date}.', overdue: 'The next radar pass was expected about {next_date}. It can shift.' };
  function sstr(k) { return (X.str && X.str[k]) || STR[{ missing_numbers: 'missing', stale: 'stale', next_pass_overdue: 'overdue' }[k] || k]; }
  function dm(iso) { var d = new Date(String(iso).slice(0, 10) + 'T00:00:00Z'); return isNaN(d) ? String(iso) : d.toLocaleDateString('en-GB', { timeZone: 'UTC', day: 'numeric', month: 'short' }); }
  function pmTxt(e) { e = +e; return '±' + (e >= 1.5 ? Math.round(e) : n1(e)); }
  function storyNumbersOK() { var s = X.story; return !!(s && s.numbers_ready !== false); }
  function evChipHtml(c) { return '<a class="chip chip--event" href="#ev-' + esc(c.event_id) + '" data-evchip="' + esc(c.event_id) + '">' + esc(c.text) + '</a>'; }
  function storyHtml() {
    var s = X.story, b = s.badges || {}, ts = s.timestamps || {}, sl = s.since_last, ok = storyNumbersOK(), pass = s.pass || {}, arch = !!s.archive;
    var when = pass.time_ist_text || (s.data_as_of ? ist(s.data_as_of) : '');
    var chips = chipsOf(s), area = areaName();
    var badges = (b.provisional ? tag('Provisional data') : '') + (b.sample ? tag(SAMPLE) : '');
    var conf = (s.confounders || []).filter(Boolean);
    var lead = String(s.lead || '');
    conf.forEach(function (c) { lead = lead.split(c).join(''); });
    lead = lead.replace(/\s{2,}/g, ' ').trim();
    var stale = '';
    if (s.stale) {
      var days = Math.round((Date.parse(s.built_utc) - Date.parse(s.data_as_of)) / 864e5);
      stale = '<div class="note note--warn" role="status"><b>Older picture.</b> ' + esc(fill(sstr('stale'), { days: isFinite(days) ? days : '?', date: dshort(String(s.data_as_of).slice(0, 10)) })) + '</div>';
    }
    var h = '<div class="card" id="story">' +
      '<div class="row row--between"><span class="eyebrow">' + esc(arch ? 'Archived radar pass' : 'Latest radar pass') + (when ? ' · ' + esc(when) : '') + '</span><span class="row" style="gap:6px">' + badges + '</span></div>' +
      '<div class="row" style="gap:6px">' + chips.map(evChipHtml).join('') + (pass.product_status ? statusChip(String(pass.product_status).toUpperCase()) : '') +
        (area ? '<span class="small muted">' + esc(area) + (pass.role ? ' · ' + esc(pass.role.charAt(0) + pass.role.slice(1).toLowerCase()) + ' pass' + (pass.track != null ? ', track ' + esc(pass.track) : '') : '') + '</span>' : '') + '</div>' +
      '<h2 class="story__h">' + esc(s.headline) + '</h2>';
    if (arch) h += '<div class="note" role="status"><b>Frozen record.</b> This is the summary as it was written for this pass. <button type="button" class="linkbtn small" data-act="tolatest">Back to the latest pass</button></div>';
    if (!ok) h += '<div class="note note--warn" role="status">' + esc(s.numbers_text || sstr('missing_numbers')) + '</div>';
    else if (sl) {
      var ch = sl.chips || {};
      h += '<div class="since" role="group" aria-label="' + esc(sl.title || 'Since the last pass') + '"><div class="since__t">' + esc(sl.title || 'Since the last pass') + ' <span class="muted">(' + esc(dm(sl.prev_date)) + ' to ' + esc(dm(sl.this_date)) + ')</span></div>' +
        '<p class="since__p">' + esc(sl.text) + '</p>' +
        '<div class="since__c"><span><b>' + esc(sl.receded) + '</b>' + esc(ch.down || 'went down') + '</span><span><b>' + esc(sl.still) + '</b>' + esc(ch.same || 'about the same') + '</span><span><b>' + esc(sl.worse) + '</b>' + esc(ch.up || 'went up') + '</span></div></div>';
    }
    if (lead && ok) h += '<p class="lead">' + esc(lead) + '</p>';
    if (ok && s.comparison_line) h += '<p class="small">' + esc(s.comparison_line) + '</p>';
    else if (ok && s.class_summary && s.class_summary.text) h += '<p class="small">' + esc(s.class_summary.text) + '</p>';
    h += stale;
    var nums = (s.three_numbers && s.three_numbers.length) ? s.three_numbers : (s.big_numbers || []);
    if (ok && nums.length) h += '<div class="bignums">' + nums.map(function (n, i) {
      return '<div class="bn"><span class="bn__v' + (i === 0 ? ' bn__v--water' : '') + '">' + esc(n.value) + (n.err != null ? '<span class="bn__pm">' + pmTxt(n.err) + '</span>' : '') + '</span>' +
        (n.unit ? '<span class="bn__u">' + esc(n.unit) + '</span>' : '') + '<span class="bn__l">' + esc(n.label) + '</span></div>';
    }).join('') + '</div>';
    if (s.confidence && s.confidence.level === 'lower') {
      h += '<div class="note note--warn" role="status"><b>Lower confidence.</b>' + ((s.confidence.reasons || []).length ? '<ul class="note__l">' + s.confidence.reasons.map(function (r) { return '<li>' + esc(r) + '</li>'; }).join('') + '</ul>' : '') + '</div>';
    }
    var cav = (s.caveats && s.caveats.length) ? s.caveats : conf.concat(b.provisional && s.provisional_text ? [s.provisional_text] : []);
    if (cav.length) h += '<div class="note"><b>Caveats.</b><ul class="note__l">' + cav.map(function (c) { return '<li>' + esc(c) + '</li>'; }).join('') + '</ul></div>';
    if (s.sea && s.sea.text) h += '<p class="small muted"><b>Sea.</b> ' + esc(s.sea.text) + '</p>';
    h += '<div class="row">' + (s.map && s.map.layer_id ? '<button class="btn btn--sm" data-act="storymap">Show on the map</button>' : '') + '</div>';
    var np = s.next_pass;
    if (np && !arch) {
      var ntxt = np.text || '';
      if (ntxt) h += '<p class="small">' + esc(ntxt) + '</p>';
    }
    if (s.age && s.age.text && !arch) h += '<p class="small">' + esc(s.age.text) + '</p>';
    h += '<p class="small muted">' + esc(ts.picture || s.data_as_of_text || '') + (ts.built ? ' · ' + esc(ts.built) : (s.built_text ? ' · Summary updated ' + esc(s.built_text) : '')) + '</p>';
    return h + '</div>';
  }
  function noStoryHtml() {
    return '<div class="card" id="story"><div class="row row--between"><span class="eyebrow">' + esc(F.intro.title) + '</span>' + rankTag() + '</div>' +
      '<h2 class="story__h">' + esc(F.intro.lead) + '</h2><p class="small">' + esc(F.intro.how_to_read) + '</p></div>';
  }

  /* ---------- frozen findings per pass date ---------- */
  function loadFindings(d) {
    if (X.fcache[d]) return Promise.resolve(X.fcache[d]);
    return getJSON(FD + d + '.json').then(function (o) { X.fcache[d] = o; return o; });
  }
  /* which pass date the home card should describe, from the map view (coast views only) */
  function storyDateWanted() {
    if (S.section !== 'happened') return undefined;
    if (S.mapMode === 'share') return shareDate();
    if ((S.mapMode === 'radar' || S.mapMode === 'swipe') && S.role === 'coast') return S.dates.coast.after;
    return undefined;
  }
  function syncStory() {
    if (!X.builtHappened || !X.latest) return;
    var d = storyDateWanted(); if (d === undefined) return;
    var target = (d && d !== latestPassDate() && X.fdates[d]) ? d : null;
    if (target === S.storyD) return;
    S.storyD = target;
    if (!target) { X.story = X.latest; buildHappened(); return; }
    loadFindings(target).then(function (o) { if (S.storyD === target) { X.story = o; buildHappened(); } })
      .catch(function (e) { console.warn(e.message); if (S.storyD === target) { S.storyD = null; X.story = X.latest; buildHappened(); } });
  }
  function preloadFindings() {
    Object.keys(X.fdates).forEach(function (d) { if (!X.fcache[d]) loadFindings(d).then(function () { refreshEvents(); refreshArchive(); }).catch(function (e) { console.warn(e.message); }); });
  }

  /* ---------- alerts (alerts-v2) ---------- */
  function alertsHtml() {
    var a = X.alerts;
    if (!a) return '<p class="small">The alerts snapshot is not ready yet.</p>';
    if (a.schema !== 'alerts-v2') return '<p class="small">The alerts file has an unknown format, so it is not shown.</p>';
    var g = a.gdacs || {}, sa = a.sachet || {}, gi = g.items || [], si = sa.items || [];
    function head(label, o, t) {
      var when = o.ok === false ? 'Could not refresh, showing snapshot from ' + tl(t) + '.' : (label === 'GDACS' ? 'Checked ' : 'Snapshot ') + tl(t) + '.';
      return '<div class="alerts__h"><b>' + esc(label) + '</b><span class="small' + (o.ok === false ? ' alerts__bad' : ' muted') + '">' + esc(when) + '</span></div>';
    }
    var h = '';
    h += head('GDACS', g, g.fetched_utc) + (gi.length ? gi.map(function (x) {
      return '<div class="alert"><b>' + esc(x.name || x.id) + '</b>' + (x.alert_level ? ' <span class="chip chip--partly">' + esc(x.alert_level) + '</span>' : '') +
        '<div class="alert__m">' + esc(x.severity_text || '') + (x.from ? ' · ' + esc(dshort(String(x.from).slice(0, 10))) + (x.to ? ' to ' + esc(dshort(String(x.to).slice(0, 10))) : '') : '') + (x.current === false ? ' · not current' : '') + (x.link ? ' · <a href="' + esc(x.link) + '" target="_blank" rel="noopener">GDACS report</a>' : '') + '</div></div>';
    }).join('') : '<p class="small muted">No items.</p>');
    h += head('SACHET', sa, sa.snapshot_utc) + (si.length ? si.map(function (x) {
      return '<div class="alert"><b' + hasLang(x.headline) + '>' + esc(x.headline) + '</b><div class="alert__m">' + esc(x.area || '') + (x.source ? ' · ' + esc(x.source) : '') + (x.issued ? ' · issued ' + esc(tl(x.issued)) : '') + (x.link ? ' · <a href="' + esc(x.link) + '" target="_blank" rel="noopener">Alert text</a>' : '') + '</div></div>';
    }).join('') : '<p class="small muted">No items.</p>');
    if (!gi.length && !si.length) h += '<p class="small"><b>' + esc(a.none_text || 'No current alerts for this area.') + '</b></p>';
    h += '<p class="small muted">Credit: ' + esc(g.credit || 'GDACS') + '; ' + esc(sa.credit || 'NDMA SACHET') + '. Alerts are not confirmed by radar.</p>';
    return h;
  }
  function alertsCard() {
    var area = areaName();
    return '<div class="card" id="alerts-strip"><div class="row row--between"><h2>Alerts' + (area ? ' <span class="muted small">for ' + esc(area) + '</span>' : '') + '</h2></div>' + alertsHtml() + '</div>';
  }

  /* ---------- general panel and About ---------- */
  function radarPanelHtml() {
    var title = T('dash.radar.title'); if (!title) return '';
    var items = []; for (var i = 1; T('dash.radar.p' + i); i++) items.push(T('dash.radar.p' + i));
    return '<div class="card" id="radar-water"><h2>' + esc(title) + '</h2><ul class="small note__l note__l--card">' + items.map(function (t) { return '<li>' + esc(t) + '</li>'; }).join('') + '</ul></div>';
  }
  function aboutHtml(id) {
    var title = T('dash.about.title'); if (!title) return '';
    var li = []; for (var i = 1; T('dash.about.s' + i + '.name'); i++) {
      var u = T('dash.about.s' + i + '.url');
      li.push('<li><b>' + (u ? '<a href="' + esc(u) + '" target="_blank" rel="noopener">' + esc(T('dash.about.s' + i + '.name')) + '</a>' : esc(T('dash.about.s' + i + '.name'))) + '.</b> ' + esc(T('dash.about.s' + i + '.what')) + '</li>');
    }
    return '<div class="card" id="' + id + '"><h2>' + esc(title) + '</h2><p class="small">' + esc(T('dash.about.intro')) + '</p><ul class="small note__l note__l--card">' + li.join('') + '</ul>' +
      (T('dash.about.notused') ? '<p class="small"><b>Not used.</b> ' + esc(T('dash.about.notused')) + '</p>' : '') + '</div>';
  }

  /* ---------- events (data/processed/events.json) ---------- */
  var BAN = /\{\w+\}/;
  function fillOrDrop(t, v) {      // a sentence with a slot that cannot be filled is left out, never invented
    return String(t || '').split(/(?<=[.!?])\s+/).map(function (x) { return fill(x, v); }).filter(function (x) { return !BAN.test(x); }).join(' ');
  }
  function profBelongsTo(ev) {
    if (!X.hasProf || !ev) return false;
    var l = X.layers[X.profile.layer_id]; if (!l || !l.date) return false;
    return (ev.linked_passes || []).some(function (p) { return p.date === l.date; });
  }
  function storySlots(ev) {
    var v = {}, P = X.profile;
    if (profBelongsTo(ev) && P) { if (P.eye_radius_km != null) v.eye = P.eye_radius_km; if (P.eye_radius_err != null) v.eye_err = P.eye_radius_err; if (X.peak) v.peak = X.peak.r_km; }
    var cs = X.scenes && X.scenes.coast; if (cs && cs.length) { v.before = dshort(X.def.before.coast); v.after = dshort(X.def.after.coast); }
    return v;
  }
  function evStoryHtml(ev, full) {
    var st = ev.story; if (!st) return '';
    var v = storySlots(ev), h = '', sampleT = profSample() ? tag(X.profile.placeholder.tag || SAMPLE) : '';
    function para(k, lab) { var t = fillOrDrop(st[k], v); return t ? '<p class="small">' + (lab ? '<b>' + esc(lab) + '.</b> ' : '') + esc(t) + '</p>' : ''; }
    h += para('landfall_caption', full ? 'Landfall' : '');
    if (profBelongsTo(ev)) h += '<div class="row" style="align-items:flex-start">' + eyeDiagram() + '<div style="flex:1;min-width:180px;display:flex;flex-direction:column;gap:8px">' + (full ? '<b class="small">The eye ' + sampleT + '</b>' : sampleT) + para('eye_profile', '') + para('wind', '') + '</div></div>';
    else h += para('eye_profile', full ? 'The eye' : '') + para('wind', '');
    if (full) h += para('before_after', 'Before and after') + para('murasu_caveat', 'Other water') + para('sea_caveat', 'Sea brightness');
    h += '<div class="row">' + (profBelongsTo(ev) ? '<button type="button" class="btn btn--sm" data-act="eye">Show the eye and path on the map</button>' : '') +
      (full && X.scenes && X.scenes.coast.length > 1 ? '<button type="button" class="btn btn--sm" data-act="evswipe">Before and after on the map</button>' : '') + '</div>';
    return h;
  }
  function evCardHome(s) {          // only when the pass carries an event chip
    var out = '';
    chipsOf(s).forEach(function (c) {
      var ev = eventById(c.event_id); if (!ev || !ev.story) return;
      out += '<div class="card" id="evcard-' + esc(ev.id) + '"><div class="row row--between"><h2>' + esc(ev.name) + '</h2>' + evChipHtml(c) + '</div>' + evStoryHtml(ev, false) +
        '<p class="small"><a href="#ev-' + esc(ev.id) + '" data-evchip="' + esc(ev.id) + '">Open the full event record</a></p></div>';
    });
    return out;
  }
  var REL = { during: 'During the event', after: 'After the event', before: 'Before the event' };
  function passFinding(p) {
    var fd = X.fcache && X.fcache[p.date];
    if (p.role === 'COAST' && fd && fd.headline) return fd.headline;
    if (p.role === 'SEA') return (X.latest && X.latest.sea && X.latest.sea.text) || 'No sea finding yet.';
    if (p.radar_finding === 'numbers_coming') return sstr('missing_numbers');
    if (p.radar_finding === 'no_clear_change') return 'Radar shows no clear change.';
    return 'Finding not available yet.';
  }
  function passLink(p) {
    var u = ((X.latest && X.latest.updates) || []).filter(function (x) { return x.date === p.date && (x.kind === 'sea') === (p.role === 'SEA'); })[0];
    if (u && (u.hash || u.permalink)) return '#' + (u.hash || String(u.permalink).replace(/^#/, ''));
    return p.role === 'SEA' ? '#tab=happened&mode=radar&role=sea&d=' + p.date : '#tab=happened&mode=share&d=' + p.date;
  }
  function evItem(ev, open) {
    var draft = ev.reviewed_by_human === false, sev = ev.severity || {}, src = ev.source || {};
    var until = '';
    if (ev.end && ev.aftermath_days) { var dt = new Date(ev.end + 'T00:00:00Z'); dt.setUTCDate(dt.getUTCDate() + ev.aftermath_days); until = dt.toISOString().slice(0, 10); }
    var lp = (ev.linked_passes || []).slice().sort(function (a, b) { return a.date < b.date ? -1 : 1; });
    function kv(k, v) { return v ? '<div class="evkv"><dt>' + esc(k) + '</dt><dd>' + v + '</dd></div>' : ''; }
    var h = '<details class="evt" id="ev-' + esc(ev.id) + '"' + (open ? ' open' : '') + '><summary><b>' + esc(ev.name) + '</b> <span class="chip chip--no">' + esc(ev.type || 'event') + '</span> ' +
      '<span class="small muted">' + esc(ev.start ? dshort(ev.start) : '') + (ev.end && ev.end !== ev.start ? ' to ' + esc(dshort(ev.end)) : '') + '</span> ' +
      (ev.status_text ? '<span class="chip chip--yes">' + esc(ev.status_text) + '</span> ' : '') +
      (draft ? tag(T('dash.events.draft', 'Draft from alert, not reviewed')) : '') + '</summary><div class="evt__b">';
    if (ev.description) h += '<p class="small">' + esc(ev.description) + '</p>';
    h += '<dl class="evkv__l">' + kv('Type', esc(ev.type || '')) +
      kv('Dates', esc((ev.start ? dshort(ev.start) : '?') + ' to ' + (ev.end ? dshort(ev.end) : '?')) + (until ? '. Radar passes are linked up to ' + esc(dshort(until)) : '')) +
      kv('Source', (src.url ? '<a href="' + esc(src.url) + '" target="_blank" rel="noopener">' + esc(src.name || src.url) + '</a>' : esc(src.name || '')) + (ev.credit ? '. Credit: ' + esc(ev.credit) : '')) +
      kv('Severity' + (sev.by ? ' (as given by ' + sev.by + ')' : ''), esc(sev.as_given || '')) +
      kv('Status', esc(ev.status_text || ev.status || '') + (draft ? '. ' + esc(T('dash.events.draft', 'Draft from alert, not reviewed')) : '')) + '</dl>';
    h += '<h3>Radar passes linked to this event</h3>';
    h += lp.length ? '<ul class="evl">' + lp.map(function (p) {
      return '<li><a class="evl__a" href="' + esc(passLink(p)) + '"><span class="arch__top"><b>' + esc(dshort(p.date)) + '</b><span class="chip chip--no">' + (p.role === 'SEA' ? 'Sea' : 'Coast') + '</span><span class="chip chip--partly">' + esc(REL[p.relation] || p.relation || '') + '</span></span>' +
        '<span class="arch__h">' + esc(passFinding(p)) + '</span><span class="small muted">Opens this day on the map.</span></a></li>';
    }).join('') + '</ul>' : '<p class="small">No radar pass is linked yet. ' + esc(T('dash.events.no_confirm', 'An alert alone is not confirmed by radar.')) + '</p>';
    if (ev.story) h += '<h3>Guided story</h3>' + evStoryHtml(ev, true);
    if ((ev.cannot_tell || []).length) h += '<h3>What radar cannot tell here</h3><ul class="small note__l">' + ev.cannot_tell.map(function (t) { return '<li>' + esc(t) + '</li>'; }).join('') + '</ul>';
    if ((ev.alert_refs || []).length) h += '<h3>Alerts that mention it</h3><ul class="small note__l">' + ev.alert_refs.map(function (a) { return '<li>' + esc(a.source) + ' ' + esc(a.id) + (a.issued ? ' · ' + esc(tl(a.issued)) : '') + ': ' + esc(a.headline || '') + '</li>'; }).join('') + '</ul>';
    if ((ev.official_links || []).length) h += '<p class="small">Official sources: ' + ev.official_links.map(function (l) { return '<a href="' + esc(l.url) + '" target="_blank" rel="noopener">' + esc(l.name) + '</a>'; }).join(' · ') + '</p>';
    if ((ev.edit_log || []).length) h += '<details class="lim lim--card"><summary>Edit log (' + ev.edit_log.length + ')</summary><ul class="small note__l">' + ev.edit_log.map(function (e) { return '<li>' + esc(tl(e.utc)) + ' · ' + esc(e.by) + ': ' + esc(e.what) + '</li>'; }).join('') + '</ul></details>';
    return h + '</div></details>';
  }
  function eventsHtml() {
    var evs = (X.events || []).slice().sort(function (a, b) { return (a.start || '') < (b.start || '') ? 1 : -1; });
    var chipIds = chipsOf(X.story).slice(0, 1).map(function (c) { return c.event_id; });   // the first chip's event opens; the rest stay collapsed
    return '<div class="card" id="events"><h2>' + esc(T('dash.events.title', 'Events archive')) + '</h2><p class="small">' + esc(T('dash.events.intro')) + '</p>' +
      (evs.length ? evs.map(function (e) { return evItem(e, chipIds.indexOf(e.id) >= 0 || S.evOpen[e.id]); }).join('') : '<p class="small">No events are listed yet.</p>') + '</div>';
  }
  function refreshEvents() {
    var el = $('#events'); if (!el) return;
    $$('#events details.evt', el).forEach(function (d) { S.evOpen[d.id.replace(/^ev-/, '')] = d.open; });
    el.outerHTML = eventsHtml();
  }
  function openEvent(id) {
    var d = $('#ev-' + id); if (!d) return;
    d.open = true; S.evOpen[id] = true;
    d.scrollIntoView({ block: 'start' });
    var sm = d.querySelector('summary'); if (sm) sm.focus();
  }

  function findHtml() {
    return '<div class="card" id="find"><h2>Find your mandal</h2><p class="small">Type the name of your mandal, or click it on the map.</p>' +
      '<div class="tools"><input type="search" id="fm-q" placeholder="Start typing a mandal name" aria-label="Find your mandal" autocomplete="off" aria-controls="fm-list"></div>' +
      '<ul class="fm__list" id="fm-list" role="listbox" aria-label="Matching mandals"></ul><div id="fm-out" aria-live="polite"></div></div>';
  }
  function fmNames() { return Object.keys((X.story && X.story.mandal_sentences) || {}).sort(function (a, b) { return a.localeCompare(b); }); }
  function fmList(q) {
    var el = $('#fm-list'); if (!el) return;
    q = (q || '').trim().toLowerCase();
    if (!q) { el.innerHTML = ''; return; }
    var m = fmNames().filter(function (n) { return (n + ' ' + niceName(n)).toLowerCase().indexOf(q) >= 0; });
    el.innerHTML = m.length ? m.slice(0, 8).map(function (n) { return '<li role="option"><button type="button" class="fm__b" data-fm="' + esc(n) + '">' + esc(niceName(n)) + '</button></li>'; }).join('') + (m.length > 8 ? '<li class="small muted">' + (m.length - 8) + ' more. Keep typing.</li>' : '')
      : '<li class="small muted">No mandal called "' + esc(q) + '". Check the spelling, or click it on the map.</li>';
  }
  var TRENDS = { up: 'went up since the last radar pass', down: 'went down since the last radar pass', flat: 'about the same as the last radar pass', new: 'first time in the radar record' };
  function fmShow(name) {
    var out = $('#fm-out'); if (!out || !storyOK()) return;
    var fq = $('#fm-q'), fl = $('#fm-list'); if (fq) fq.value = ''; if (fl) fl.innerHTML = '';
    var s = X.story, sen = s.mandal_sentences && s.mandal_sentences[name], m = (s.mandals && s.mandals[name]) || {};
    if (!sen) { out.innerHTML = ''; return; }
    out.innerHTML = '<div class="note fm__out"><div class="row row--between"><b>' + esc(niceName(name)) + '</b><span class="chip ' + (m.flooded ? 'chip--flag' : 'chip--calm') + '">' + (m.rank_water == null ? 'Not enough radar view' : m.flooded ? 'Probably flooded' : 'No clear flooding') + '</span></div>' +
      '<p class="lead">' + esc(sen) + '</p>' +
      '<p class="small">' + (m.rank_water != null && m.trend && TRENDS[m.trend] ? 'Open water share ' + esc(TRENDS[m.trend]) + '. ' : '') + (m.confidence ? dots(m.confidence) + esc(F.mandal['conf_' + m.confidence] || m.confidence) + '. ' : '') +
      (m.coverage_pct != null && m.coverage_pct < 50 ? 'Less than half of this mandal was in the radar view. ' : '') + (m.rank_water == null ? 'Not ranked.' : 'Rank ' + esc(m.rank_water) + ' of ' + X.rows.length + ' for open water.') + '</p>' +
      '<div class="row"><button type="button" class="btn btn--sm" data-act="zoom">Show on the map</button></div></div>';
  }
  /* the event chip(s) of ONE pass: coast = that date's findings file (event_chips / event_chip); sea = events whose linked_passes hold it */
  function passChips(u) {
    if (u.kind !== 'sea') { var fd = X.fcache && X.fcache[u.date]; return fd ? chipsOf(fd).map(function (c) { return c.text; }) : []; }
    var out = [];
    (X.events || []).forEach(function (ev) {
      (ev.linked_passes || []).forEach(function (p) {
        if (p.date === u.date && p.role === 'SEA' && (p.relation === 'during' || p.relation === 'after')) out.push((p.relation === 'during' ? 'During ' : 'After ') + ev.name + (ev.reviewed_by_human === false ? ' (alert, not reviewed)' : ''));
      });
    });
    return out;
  }
  function refreshArchive() { var el = $('#archive'); if (el) el.outerHTML = archiveHtml(); }
  function archiveHtml() {
    var s = X.latest || X.story, ups = s.updates || [], f = s.feed || {};
    var li = ups.map(function (u, i) {
      var role = u.kind === 'sea' ? 'Sea' : 'Coast';
      var chips = passChips(u), chipH = chips.map(function (t) { return '<span class="chip chip--event">' + esc(t) + '</span>'; }).join('');
      return '<li class="arch__i"><a class="arch__a" href="#' + esc(u.hash || String(u.permalink || '').replace(/^#/, '')) + '"><span class="arch__top"><b>' + esc(dshort(u.date)) + '</b><span class="chip chip--no">' + role + '</span>' + (u.status ? statusChip(String(u.status).toUpperCase()) : '') + (i === 0 ? '<span class="chip chip--yes">Latest</span>' : '') + chipH + '</span>' +
        '<span class="arch__h">' + esc(u.headline || '') + '</span>' + (u.days_after_landfall != null && chips.length ? '<span class="small muted">' + esc(u.days_after_landfall === 0 ? 'Landfall day' : u.days_after_landfall < 0 ? Math.abs(u.days_after_landfall) + (u.days_after_landfall === -1 ? ' day before landfall' : ' days before landfall') : u.days_after_landfall + (u.days_after_landfall === 1 ? ' day after landfall' : ' days after landfall')) + '. Opens this day on the map.</span>' : '<span class="small muted">Opens this day on the map.</span>') + '</a>' +
        '<button type="button" class="linkbtn small arch__s" data-arch-save="' + esc(i) + '" aria-label="Save ' + esc(dshort(u.date)) + ' ' + role + ' to saved days">Save</button></li>';
    }).join('');
    return '<div class="card" id="archive"><h2>Earlier updates</h2><p class="small">Every radar picture we have analysed, newest first. Each opens the map for that day. Save keeps it in your saved days (this browser only).</p>' +
      (li ? '<ul class="arch">' + li + '</ul>' : '<p class="small">No earlier updates yet.</p>') +
      '<p class="small">Follow updates: <a href="../../data/web/' + esc(f.json || 'feed.json') + '" target="_blank" rel="noopener">JSON feed</a> · <a href="../../data/web/' + esc(f.atom || 'atom.xml') + '" target="_blank" rel="noopener">Atom feed</a> (for a feed reader).</p></div>';
  }
  function archiveRec(i) {
    var u = ((X.latest || X.story || {}).updates || [])[i]; if (!u) return null;
    var st = parseHash('#' + (u.hash || String(u.permalink || '').replace(/^#/, '')));
    var role = u.kind === 'sea' ? 'sea' : 'coast', label = dshort(u.date) + ' · ' + (role === 'sea' ? 'sea' : 'coast');
    return { id: uid(), label: label, date: st.d || u.date, mode: st.mode || 'share', view: { tab: 'happened', role: st.role || role, before: st.b || null, mandal: null, c: null, z: null, layers: null }, saved_at: new Date().toISOString() };
  }
  function storyMap() {
    var s = X.story, m = (s.map && s.map.mode) || 'share', d = s.map && s.map.date;
    if (m === 'share' && d && X.rowsBy[d]) S.shareD = d;
    setSection('happened', { keepView: true });
    setMapMode(['share', 'radar', 'swipe', 'eye'].indexOf(m) >= 0 ? m : 'share', true);
  }

  function buildHappened() {
    var story = storyOK(), nums = !story || storyNumbersOK();
    var showRank = X.rows.length && nums && !(story && X.story.state === 'watch' && !X.rows.some(function (r) { return X.story.mandals && X.story.mandals[r.mandal] && X.story.mandals[r.mandal].flooded; }));
    var html = (story ? storyHtml() : noStoryHtml()) +
      officialLine() +
      alertsCard() +
      (story ? evCardHome(X.story) : '') +
      (story && X.story.mandal_sentences && nums ? findHtml() : '') +

      (!X.rows.length && nums ? '<div class="card"><h2>' + esc(F.ranking.title) + '</h2><p class="small">The mandal numbers are not ready yet. Check back soon.</p></div>' : '') +
      (showRank ? '<div class="card" id="ranking">' +
        '<div class="row row--between"><h2>' + esc(F.ranking.title) + '</h2>' + rankTag() + '</div>' +
        '<p class="small">' + esc(F.ranking.sub) + ' ' + esc(F.ranking.reading_help) + '</p>' +
        '<ol class="rank" id="ranklist" style="list-style:none"></ol>' +
        '<div class="legendline"><span><i class="sw sw--w"></i>' + esc(F.ranking.legend_water) + '</span><span><i class="sw sw--t"></i>' + esc(F.ranking.legend_normal) + '</span><span>Thin line: ' + esc(F.ranking.legend_err.toLowerCase()) + '</span></div>' +
        '<button class="linkbtn small" id="rankmore" style="align-self:flex-start"></button>' +
      '</div>' +

      '<div class="card" id="mcard"></div>' : '') +

      radarPanelHtml() +

      '<div class="card">' +
        '<h2>' + esc(F.confidence.title) + '</h2>' +
        '<ul class="small" style="margin:0;padding-left:18px;display:flex;flex-direction:column;gap:6px">' + F.confidence.items.map(function (t) { return '<li>' + esc(t) + '</li>'; }).join('') + '</ul>' +
        '<div class="row row--between" style="margin-top:8px"><h3>' + esc(F.cannot_tell.title) + '</h3>' + tag(F.cannot_tell.draft_tag) + '</div>' +
        F.cannot_tell.items.map(function (i) {
          var lab = { yes: 'Radar can', partly: 'Only partly', no: 'Radar cannot' }[i.verdict];
          return '<div class="verd"><span class="chip chip--' + i.verdict + ' verd__chip">' + lab + '</span><b>' + esc(i.claim) + '</b><span>' + esc(i.why) + '</span></div>';
        }).join('') +
      '</div>' +

      eventsHtml() +
      (X.latest && (X.latest.updates || []).length ? archiveHtml() : '') +
      aboutHtml('about') +
      '<div class="linkcard"><h2>' + esc(F.link_to_data.title) + '</h2><p>' + esc(F.link_to_data.text) + '</p><button class="btn" data-act="todata">' + esc(F.link_to_data.button) + ' \u2192</button></div>';
    $('#sec-happened').innerHTML = html; $('#sec-happened').removeAttribute('aria-busy');
    X.builtHappened = true;
    renderRank();
    if (S.fm && S.sel) fmShow(S.sel);
  }

  /* ---------------- "Data" ---------------- */
  function isWeak(l) { return !!(l && (l.classes || []).some(function (c) { return c.id === 'wet_crops'; })); }
  function layerRows() {
    var src = {}; X.manifest.sources.forEach(function (s) { src[s.id] = s; });
    return X.manifest.layers.map(function (l) {
      var s = src[l.source_id] || {}, drawable = isImg(l) || l.id === 'mandal_boundaries' || l.id === 'imd_track_arnab';
      var st = l.status === 'ready' ? 'ready' : l.status === 'unavailable' ? 'not available yet' : 'link only';
      var lim = l.limit ? String(l.limit) : '';
      return '<tr title="' + esc(l.id) + '"><td><b>' + esc(l.name) + '</b>' + (l.chip === 'nisar' || l.type === 'nisar' ? ' <span class="chip chip--nisar">NISAR L-band</span>' : '') +
        (isWeak(l) ? '<span class="sub">' + tag('Weak signal') + '</span>' : '') +
        (layerSample(l) ? '<span class="sub">' + tag(l.placeholder.tag) + '</span>' : '') + '</td>' +
        '<td class="num">' + esc(l.date ? dshort(l.date) : (l.access === 'live' ? 'Live' : '—')) + '</td>' +
        '<td>' + esc(l.source || '') + '<span class="sub">' + esc(l.credit || '') + '</span></td>' +
        '<td>' + esc(s.licence || 'not stated') + '</td>' +
        '<td><span class="chip chip--st-' + (l.status === 'ready' ? 'ready' : 'other') + '">' + esc(st.charAt(0).toUpperCase() + st.slice(1)) + '</span>' +
          (lim ? (lim.length > 70 ? '<details class="lim"><summary>Limits</summary><span class="sub">' + esc(lim) + '</span></details>' : '<span class="sub">' + esc(lim) + '</span>') : '') + '</td>' +
        '<td>' + (drawable ? '<input type="checkbox" data-lyr="' + esc(l.id) + '" aria-label="Show ' + esc(l.name) + ' on the map">' : '<span class="sub">Not drawn</span>') + '</td></tr>';
    }).join('');
  }

  function pm(v) { return '<span class="pm">\u00B1' + n1(v) + '</span>'; }
  function profDate() { var l = X.profile && X.layers[X.profile.layer_id]; return l && l.date ? dshort(l.date) : 'the eye-pass date'; }
  function spark(name) {
    var s = X.series[name], W = 76, H = 24, P = 3;
    if (!s || !s.length) return '<span class="muted">n/a</span>';
    var n = s.length, mx = X.sparkMax || 5;
    function px(i) { return n === 1 ? W / 2 : P + i * (W - 2 * P) / (n - 1); }
    function py(v) { return H - P - Math.min(1, v / mx) * (H - 2 * P); }
    var pts = s.map(function (p, i) { return px(i).toFixed(1) + ',' + py(p.w).toFixed(1); });
    var lab = s.map(function (p) { return dm(p.d) + ' ' + n1(p.w) + '%'; }).join(', ');
    return '<svg class="spark" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="Open water share by date: ' + esc(lab) + '"><title>' + esc(lab) + '</title>' +
      '<line x1="' + P + '" x2="' + (W - P) + '" y1="' + (H - P) + '" y2="' + (H - P) + '" class="spark__0"/>' + (n > 1 ? '<polyline points="' + pts.join(' ') + '" class="spark__l"/>' : '') +
      s.map(function (p, i) { return '<circle cx="' + px(i).toFixed(1) + '" cy="' + py(p.w).toFixed(1) + '" r="' + (i === n - 1 ? 2.8 : 1.8) + '" class="' + (i === n - 1 ? 'spark__e' : 'spark__d') + '"/>'; }).join('') + '</svg>';
  }
  function mtCols() {
    var tot = S.rankBy === 'total', c = [['rank', 'Rank', tot ? 'water + crops' : 'open water only', 1], ['mandal', 'Mandal', '', 0], ['water', 'Open water', '% of area ± pts', 1]];
    if (tot) c.push(['crops', 'Wet crops', '% ± pts, weak signal', 1], ['tot', 'Total', '% of area ± pts', 1]);
    c.push(['km', tot ? 'Flooded area' : 'Water area', 'km²', 1], ['chg', 'Change vs normal', 'percentage points', 1], ['spark', 'By date', 'open water %', 0]);
    return c;
  }
  function mtVal(r, k) {
    var t = S.rankBy === 'total', v;
    if (k === 'rank') v = t ? r.rankT : r.rank; else if (k === 'km') v = t ? r.kmT : r.km; else if (k === 'chg') v = t ? r.chgT : r.chg; else v = r[k];
    return v;
  }
  function numPm(v, e) {
    var flag = e != null && e >= v && (v > 0 || e > 0);
    return n1(v) + pm(e) + (flag ? '<span class="nz">not distinguishable from zero</span>' : '');
  }
  function kmTxt(v) { return v == null ? '—' : (v < 1 ? v.toFixed(2) : n1(v)); }
  function signed(v) { return v == null ? '—' : (v > 0 ? '+' : v < 0 ? '−' : '') + n1(Math.abs(v)); }
  function mandalTable() {
    if (!$('#mtbody')) return;
    var q = S.q.toLowerCase(), k = S.sort.k, d = S.sort.d, tot = S.rankBy === 'total', cols = mtCols();
    $('#mthead').innerHTML = '<tr>' + cols.map(function (c) {
      return '<th scope="col" data-col="' + c[0] + '" aria-sort="none" class="' + (c[3] ? 'num' : '') + '">' + (c[0] === 'spark' ? '<span class="th-b">' + c[1] + '<span class="th-u">' + c[2] + '</span></span>' : '<button data-sort="' + c[0] + '" title="Sort by ' + c[1].toLowerCase() + '">' + c[1] + '<span class="th-u">' + c[2] + '</span></button>') + '</th>';
    }).join('') + '</tr>';
    var rows = X.rows.filter(function (r) { return !q || (r.mandal + ' ' + r.district).toLowerCase().indexOf(q) >= 0; });
    rows.sort(function (a, b) {
      var x = k === 'mandal' ? a.mandal : mtVal(a, k), y = k === 'mandal' ? b.mandal : mtVal(b, k);
      if (x == null) x = 1e9; if (y == null) y = 1e9;
      return (typeof x === 'string' ? x.localeCompare(y) : x - y) * d;
    });
    $('#mtbody').innerHTML = rows.map(function (r) {
      var rk = tot ? r.rankT : r.rank;
      return '<tr class="clickable" tabindex="0" data-m="' + esc(r.mandal) + '" aria-selected="' + (r.mandal === S.sel) + '"><td class="num">' + (rk == null ? '—' : rk) + '</td>' +
        '<td><b>' + esc(r.mandal) + '</b><span class="sub" title="' + esc(r.district) + '">' + esc(shortDist(r.district)) + '</span></td>' +
        '<td class="num"><b>' + numPm(r.water, r.we) + '</b></td>' +
        (tot ? '<td class="num">' + numPm(r.crops, r.ce) + '</td><td class="num"><b>' + numPm(r.tot, r.te) + '</b></td>' : '') +
        '<td class="num">' + kmTxt(tot ? r.kmT : r.km) + '</td><td class="num">' + signed(tot ? r.chgT : r.chg) + '</td><td>' + spark(r.mandal) + '</td></tr>';
    }).join('') || '<tr class="empty"><td colspan="' + cols.length + '">No mandal matches "' + esc(S.q) + '". Clear the filter to see all ' + X.rows.length + '.</td></tr>';
    $$('#d-mandals th[data-col]').forEach(function (th) { th.setAttribute('aria-sort', th.dataset.col === S.sort.k ? (S.sort.d > 0 ? 'ascending' : 'descending') : 'none'); });
    $$('#d-mandals [data-rankby]').forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.rankby === S.rankBy)); });
    $('#mtcount').textContent = rows.length + ' of ' + X.rows.length + ' ranked mandals';
  }
  function flaggedHtml() {
    var f = (X.rank && X.rank.flagged_not_ranked) || [];
    if (!f.length) return '';
    return '<details class="lim lim--card"><summary>' + f.length + ' mandals are not ranked (too little of them is inside the radar picture)</summary><p class="small">Shown for completeness. Treat these with great care: only a small part of each mandal was seen.</p><ul class="small flg">' +
      f.map(function (r) { return '<li><b>' + esc(r.mandal) + '</b> (' + esc(shortDist(r.district)) + '): open water ' + n1(r.water_pct) + ' ±' + n1(r.water_err) + '%, ' + Math.round((r.frac_in_footprint || 0) * 100) + '% of the mandal in the picture</li>'; }).join('') + '</ul></details>';
  }

  function profDiff() { var P = X.profile; return /minus|difference|change/i.test(String(P.points_definition || '')); }
  function profileText() {
    var P = X.profile, h = '', geo = [];
    var def = P.points_definition ? String(P.points_definition) : 'Radar brightness of the sea (dB) by distance from the eye centre.';
    h += '<p class="small"><b>What the line shows.</b> ' + esc(def.charAt(0).toUpperCase() + def.slice(1)) + (/[.!?]$/.test(def) ? '' : '.') + '</p>';
    if (P.eye && P.eye.length === 2) geo.push('Eye centre ' + esc(P.eye[0]) + ' N, ' + esc(P.eye[1]) + ' E' + (P.eye_centre_err_km != null ? ' (give or take ' + esc(P.eye_centre_err_km) + ' km)' : ''));
    if (P.imd_offset_km != null) geo.push('the IMD position fix is ' + esc(P.imd_offset_km) + ' km away');
    if (P.eyewall_ring_km != null) geo.push('eyewall ring (brightest ring) at ' + esc(P.eyewall_ring_km) + ' km');
    if (P.core_contrast_db != null) geo.push('eye floor to ring contrast ' + esc(P.core_contrast_db) + ' dB');
    if (P.acquisition_utc) geo.push('radar pass ' + esc(P.acquisition_utc));
    if (P.sea_only_land_masked) geo.push('sea only, land masked out');
    h += '<p class="small">' + (profDate() ? 'Eye pass ' + profDate() + '. ' : '') + geo.join('; ') + (geo.length ? '. ' : '') + 'Hover the chart to draw that distance on the map.</p>';
    if (P.calm_reference_caveat) h += '<div class="note"><b>Caveat.</b> ' + esc(P.calm_reference_caveat) + '</div>';
    if (P.notes) h += '<p class="small muted">' + esc(P.notes) + '</p>';
    return h;
  }
  var PX = { L: 44, R: 10, xm: 150, T: 12, B: 36 };
  function profileChart() {
    var Pf = X.profile, P = Pf.points, W = 420, H = 230, L = PX.L, R = PX.R, T = PX.T, B = PX.B;
    var maxr = P.reduce(function (m, p) { return Math.max(m, p.r_km); }, 0), xm = Math.max(50, Math.ceil((maxr + 2) / 25) * 25); PX.xm = xm;
    var lo0 = Math.min.apply(null, P.map(function (p) { return p.db - (p.err || 0); })), hi0 = Math.max.apply(null, P.map(function (p) { return p.db + (p.err || 0); })), ymin = Math.min(-2, Math.floor(lo0 / 2) * 2), ymax = Math.max(6, Math.ceil(hi0 / 2) * 2 + 2), yl = profDiff() ? 'change in brightness (dB)' : 'brightness (dB)';
    function x(r) { return L + r / xm * (W - L - R); } function y(v) { return T + (ymax - v) / (ymax - ymin) * (H - T - B); }
    var up = P.map(function (p) { return x(p.r_km) + ',' + y(p.db + p.err); }), lo = P.slice().reverse().map(function (p) { return x(p.r_km) + ',' + y(p.db - p.err); });
    var line = P.map(function (p) { return x(p.r_km) + ',' + y(p.db); }).join(' ');
    var s = '<svg class="chart" id="pchart" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="' + (profDiff() ? 'Change in radar brightness of the sea' : 'Radar brightness of the sea') + ' against distance from the eye centre, with a shaded band for the uncertainty, the eye edge, the eyewall ring and the distance to the IMD position fix">';
    (function () { var a = []; for (var v = ymin; v <= ymax; v += 2) a.push(v); return a; })().forEach(function (v) { s += '<line x1="' + L + '" x2="' + (W - R) + '" y1="' + y(v) + '" y2="' + y(v) + '" stroke="' + css('--line') + '"/><text x="' + (L - 6) + '" y="' + (y(v) + 3) + '" text-anchor="end">' + v + '</text>'; });
    for (var v2 = 0; v2 <= xm; v2 += 25) s += '<text x="' + x(v2) + '" y="' + (H - B + 13) + '" text-anchor="middle">' + v2 + '</text>';
    s += '<text x="' + (L + (W - L - R) / 2) + '" y="' + (H - 2) + '" text-anchor="middle">distance from eye centre (km)</text>';
    s += '<text x="10" y="' + (T + 60) + '" transform="rotate(-90 10 ' + (T + 60) + ')" text-anchor="middle">' + yl + '</text>';
    s += '<polygon points="' + up.concat(lo).join(' ') + '" fill="' + css('--teal-tint') + '"/>';
    var er = Pf.eye_radius_km, ee = Pf.eye_radius_err || 0, ring = Pf.eyewall_ring_km, imd = Pf.imd_offset_km;
    if (er != null && ee) s += '<rect x="' + x(Math.max(0, er - ee)) + '" y="' + T + '" width="' + (x(er + ee) - x(Math.max(0, er - ee))) + '" height="' + (H - T - B) + '" fill="' + css('--ink-2') + '" opacity=".14"><title>Eye edge, give or take ' + ee + ' km</title></rect>';
    s += '<polyline points="' + line + '" fill="none" stroke="' + css('--teal') + '" stroke-width="2"/>';
    function lbl(xx, yy, t) { return '<text x="' + xx + '" y="' + yy + '" class="plab">' + t + '</text>'; }
    if (er != null) s += '<line x1="' + x(er) + '" x2="' + x(er) + '" y1="' + T + '" y2="' + (H - B) + '" stroke="' + css('--ink-2') + '" stroke-dasharray="3 3"/>' + lbl(x(er) + 4, T + 10, 'eye edge ' + er + ' ±' + ee + ' km');
    if (ring != null) s += '<line x1="' + x(ring) + '" x2="' + x(ring) + '" y1="' + T + '" y2="' + (H - B) + '" stroke="' + css('--teal') + '" stroke-width="1.5"/>' + lbl(x(ring) + 4, T + 23, 'eyewall ring ' + ring + ' km');
    if (imd != null) s += '<path d="M' + (x(imd) - 5) + ',' + (H - B) + ' L' + (x(imd) + 5) + ',' + (H - B) + ' L' + x(imd) + ',' + (H - B - 9) + ' Z" fill="' + css('--ink') + '"><title>The IMD position fix is ' + imd + ' km from the radar eye centre</title></path>' + lbl(x(Math.max(imd, ring == null ? 0 : ring)) + 8, H - B - 3, 'IMD fix is ' + imd + ' km away');
    s += '<circle cx="' + x(X.peak.r_km) + '" cy="' + y(X.peak.db) + '" r="4" fill="' + css('--teal') + '"/>' + lbl(x(X.peak.r_km) + 7, y(X.peak.db) - 7, 'peak ' + X.peak.db + ' dB at ' + X.peak.r_km + ' km');
    s += '<line id="pcur" x1="0" x2="0" y1="' + T + '" y2="' + (H - B) + '" stroke="' + css('--ink') + '" visibility="hidden"/><text id="pcurt" x="0" y="' + (T + 38) + '" visibility="hidden" class="plab"></text>';
    s += '<rect id="phit" x="' + L + '" y="' + T + '" width="' + (W - L - R) + '" height="' + (H - T - B) + '" fill="transparent"/></svg>';
    return s + '<div class="legendline"><span><i class="sw sw--tl"></i>Line: change in brightness, band: give or take</span><span><i class="sw sw--sh"></i>Grey band: eye edge uncertainty</span><span>Triangle: where the IMD fix sits</span></div>';
  }
  function bindProfile() {
    var svg = $('#pchart'); if (!svg) return;
    var P = X.profile.points, vb = svg.viewBox.baseVal, pl = PX.L, pr = PX.R, xm = PX.xm;
    function r(ev) { var b = svg.getBoundingClientRect(); var px = (ev.clientX - b.left) / b.width * vb.width; return Math.max(0, Math.min(xm, (px - pl) / (vb.width - pl - pr) * xm)); }
    $('#phit').addEventListener('mousemove', function (ev) {
      var rk = r(ev), p = P.reduce(function (a, b) { return Math.abs(b.r_km - rk) < Math.abs(a.r_km - rk) ? b : a; });
      var px = pl + p.r_km / xm * (vb.width - pl - pr), c = $('#pcur'), t = $('#pcurt');
      c.setAttribute('x1', px); c.setAttribute('x2', px); c.setAttribute('visibility', 'visible');
      t.setAttribute('x', px + 4); t.setAttribute('visibility', 'visible'); t.textContent = p.r_km + ' km: ' + p.db + ' ±' + p.err + ' dB';
      if (hoverRing) map.removeLayer(hoverRing);
      hoverRing = L.circle(X.profile.eye, { radius: p.r_km * 1000, color: css('--white'), weight: 1.5, dashArray: '2 4', fill: false, interactive: false }).addTo(map);
    });
    $('#phit').addEventListener('mouseleave', function () { $('#pcur').setAttribute('visibility', 'hidden'); $('#pcurt').setAttribute('visibility', 'hidden'); if (hoverRing) { map.removeLayer(hoverRing); hoverRing = null; } });
  }

  /* ---------- scene catalogue (data/h5/catalog.json; falls back to the manifest layers) ---------- */
  var DIRW = { A: 'Ascending', D: 'Descending', ascending: 'Ascending', descending: 'Descending' };
  function fmtSize(n) { n = +n; if (!n) return ''; return n >= 1e6 ? (n / 1e6).toFixed(1) + ' MB' : Math.round(n / 1e3) + ' KB'; }
  function utcStr(iso) { var d = new Date(iso); return isNaN(d) ? '' : d.toISOString().slice(11, 16) + ' UTC'; }
  function istStr(iso) { var d = new Date(iso); return isNaN(d) ? '' : d.toLocaleTimeString('en-GB', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit' }) + ' IST'; }
  function latencyOf(s) {
    var c = s.cataloged_utc || s.ingested_utc || s.added_utc, a = s.end_utc || s.start_utc;
    if (!c || !a) return null;
    var h = (new Date(c) - new Date(a)) / 36e5; if (isNaN(h) || h < 0) return null;
    return h >= 48 ? n1(h / 24) + ' days' : n0(h) + ' h';
  }
  function sceneList() {
    var c = X.catalog && X.catalog.scenes;
    if (c && c.length) return c.map(function (s) {
      return { file: s.file, id: s.scene_id, band: s.band || 'L', role: String(s.role || '').toLowerCase(), start: s.start_utc, date: s.date, track: s.track, frame: s.frame, dir: DIRW[s.direction] || s.direction || '',
        status: String(s.product_status || '').toUpperCase(), pols: s.pols || [], posting: s.posting_m, size: s.size_bytes, sha: s.sha256, latency: latencyOf(s), from: 'catalog' };
    });
    var seen = {};
    return X.manifest.layers.filter(function (l) { return l.type === 'nisar' && (l.h5 || l.png); }).map(function (l) {
      return { file: l.h5 || null, id: l.id, band: l.band || 'L', role: /sea/.test(l.id) ? 'sea' : 'coast', start: l.time_utc || null, date: l.date, track: l.track, frame: l.frame, dir: DIRW[l.direction] || l.direction || '',
        status: String(l.processing_level || '').toUpperCase(), pols: l.pol ? [String(l.pol).toUpperCase()] : [], posting: null, size: null, sha: null, latency: null, from: 'manifest' };
    }).filter(function (r) { var k = r.file || r.id; if (seen[k]) return false; seen[k] = 1; return true; });
  }
  function sortedScenes() { return sceneList().sort(function (a, b) { var x = a.start || a.date || '', y = b.start || b.date || ''; return x < y ? 1 : x > y ? -1 : 0; }); }
  function statusChip(st) { var v = st === 'VALIDATED'; return '<span class="chip ' + (v ? 'chip--yes' : 'chip--partly') + '">' + (st ? esc(st) : 'UNKNOWN') + '</span>'; }
  function shaCell(sha) {
    if (!sha) return '<span class="muted">not in catalogue</span>';
    return '<code class="sha" title="' + esc(sha) + '">' + esc(sha.slice(0, 12)) + '…</code> <button type="button" class="copybtn" data-copy="' + esc(sha) + '" aria-label="Copy the full sha256 checksum">Copy</button>';
  }
  function sceneBlock() {
    var sc = sortedScenes();
    var val = sc.filter(function (l) { return l.status === 'VALIDATED'; }).length;
    var tr = {}; sc.forEach(function (l) { if (l.track != null) tr['T' + l.track] = 1; });
    var tot = sc.reduce(function (a, l) { return a + (+l.size || 0); }, 0);
    var src = sc.length && sc[0].from === 'catalog' ? 'data/h5/catalog.json' : 'the layer list (data/h5/catalog.json was not found)';
    if (!sc.length) return '<p class="small">No NISAR scenes are listed yet.</p>';
    return '<div class="kv"><div><b>' + sc.length + '</b><span>NISAR scenes</span></div><div><b>' + val + ' / ' + (sc.length - val) + '</b><span>validated / provisional</span></div><div><b>' + (Object.keys(tr).join(', ') || 'n/a') + '</b><span>radar tracks</span></div><div><b>' + (tot ? fmtSize(tot) : 'n/a') + '</b><span>H5 files in total</span></div></div>' +
      '<div class="tblwrap tblwrap--tall"><table class="dt dt--scenes"><thead><tr><th scope="col">Acquired</th><th scope="col">Scene</th><th scope="col">Data</th><th scope="col">Status</th><th scope="col">File and checksum</th></tr></thead><tbody>' +
      sc.map(function (l) {
        var when = l.start ? '<b>' + esc(dshort(String(l.start).slice(0, 10))) + '</b><br>' + utcStr(l.start) + '<br>' + istStr(l.start) : '<b>' + esc(dshort(l.date)) + '</b><br><span class="muted">time not listed</span>';
        return '<tr><td class="stack">' + when + '</td>' +
          '<td class="stack"><b>' + esc(l.band) + '-band · ' + esc(l.role ? l.role.charAt(0).toUpperCase() + l.role.slice(1) : '') + '</b><br>T' + esc(l.track) + ' · F' + esc(l.frame) + '<br>' + esc(l.dir || 'direction n/a') + '</td>' +
          '<td class="stack">' + esc(l.pols.length ? l.pols.join(' + ') : 'n/a') + '<br>' + (l.posting ? n0(l.posting) + ' m posting' : 'posting n/a') + '</td>' +
          '<td class="stack">' + statusChip(l.status) + (l.latency ? '<br><span class="small muted">in catalogue after ' + esc(l.latency) + '</span>' : '') + '</td>' +
          '<td class="stack">' + (l.size ? fmtSize(l.size) : 'size n/a') + '<br>' + shaCell(l.sha) + '</td></tr>';
      }).join('') + '</tbody></table></div>' +
      '<p class="small muted">Read from ' + esc(src) + '. New scenes appear here when the catalogue is rebuilt. Times are the start of the radar pass. "In catalogue after" shows only when the catalogue records when a scene was added. PROVISIONAL scenes have not finished NISAR\u2019s own checks and may be replaced.</p>';
  }

  function alertsBlock() { return alertsHtml(); }

  var DL = [
    ['manifest.json', 'Catalogue of layers, sources and events'], ['mandals.geojson', 'Mandal outlines (geoBoundaries, ODbL-1.0 licence)'],
    ['mandal_rank.json', 'Flooded share for each mandal, with uncertainty'], ['profile.json', 'Eye profile: sea brightness by distance'],
    ['alerts.json', 'Alerts snapshot'], ['imd_track_arnab.geojson', 'Cyclone path and position fixes from IMD']
  ];
  var DLI = '<svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path d="M8 2v8m0 0L5 7m3 3l3-3M3 13h10" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  /* ---------- citation ---------- */
  function pageUrl() { return location.href.split('#')[0]; }
  function citeYear() { return '2026'; }
  function siteTitle() { return (X.cfg && X.cfg.site && X.cfg.site.title) || 'Coast radar watch'; }
  function citeText() {
    var sc = sceneList(), ds = sc.map(function (l) { return l.date; }).filter(Boolean).sort();
    var span = ds.length ? ' NISAR L-band scenes from ' + dshort(ds[0]) + ' to ' + dshort(ds[ds.length - 1]) + '.' : '';
    return 'SpaceBros (NASA Space Apps 2026). ' + citeYear() + '. ' + siteTitle() + ': NISAR radar evidence on the coast [dashboard].' + span +
      ' ' + pageUrl() + '. Contains NISAR data, NASA/JPL-Caltech and ISRO, distributed by ASF DAAC. Accessed ' + new Date().toISOString().slice(0, 10) + '.';
  }
  function citeBib() {
    return '@misc{spacebros_nisar_' + citeYear() + ',\n  author       = {{SpaceBros (NASA Space Apps 2026)}},\n  title        = {' + siteTitle() + ': NISAR radar evidence on the coast},\n  year         = {' + citeYear() + '},\n  url          = {' + pageUrl() + '},\n  note         = {Contains NISAR data, NASA/JPL-Caltech and ISRO, distributed by ASF DAAC. Accessed ' + new Date().toISOString().slice(0, 10) + '}\n}';
  }
  function copyText(t, done) {
    function fb() { try { var ta = document.createElement('textarea'); ta.value = t; ta.setAttribute('readonly', ''); ta.style.cssText = 'position:fixed;left:-9999px;top:0'; document.body.appendChild(ta); ta.select(); var ok = document.execCommand('copy'); document.body.removeChild(ta); done(ok); } catch (e) { done(false); } }
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(t).then(function () { done(true); }, fb); else fb();
  }
  function flash(btn, ok) { var o = btn.getAttribute('data-label') || btn.textContent; btn.setAttribute('data-label', o); btn.textContent = ok ? 'Copied' : 'Copy failed'; clearTimeout(btn._t); btn._t = setTimeout(function () { btn.textContent = o; }, 1600); }

  function dlBlock() {
    var sc = sortedScenes(), imgsL = X.manifest.layers.filter(function (l) { return l.type === 'nisar' && l.png; });
    var li = function (main, size) { return '<li><span class="dl__main">' + main + '</span><span class="dl__size"' + (size && size.u ? ' data-size="' + size.u + '"' : '') + '>' + (size && size.t ? size.t : '') + '</span></li>'; };
    var hasCat = !!(X.catalog && X.catalog.scenes && X.catalog.scenes.length);
    return '<h3>Scene files of record (H5)</h3><ul class="dl">' + (sc.filter(function (l) { return l.file; }).map(function (l) {
        var nm = l.file.split('/').pop();
        return li('<b>' + esc(l.band) + '-band ' + esc(l.role) + ', ' + esc(dshort(l.date)) + ' · T' + esc(l.track) + ' ' + statusChip(l.status) + '</b><a class="dl__file" href="../../' + esc(l.file) + '" download>' + DLI + esc(nm) + '</a>' +
          (l.sha ? '<span class="small muted">sha256 <code class="sha">' + esc(l.sha.slice(0, 16)) + '…</code> <button type="button" class="copybtn" data-copy="' + esc(l.sha) + '" aria-label="Copy the full sha256 checksum">Copy</button></span>' : ''),
          l.size ? { t: fmtSize(l.size) } : { u: '../../' + esc(l.file) });
      }).join('') || '<li><span class="dl__main"><span class="small muted">No H5 files are listed yet.</span></span></li>') + '</ul>' +
      '<h3>Cite this</h3><div class="row"><button type="button" class="btn btn--sm" data-cite="text">Copy citation (text)</button><button type="button" class="btn btn--sm" data-cite="bib">Copy BibTeX</button></div>' +
      '<details class="small"><summary>Show the citation</summary><pre class="cite" id="cite-pre"></pre></details>' +
      '<p class="small">Method notes: <span id="methods-link"><span class="muted">checking…</span></span></p>' +
      '<h3>For scripts</h3><ul class="dl">' +
        li('<b>Scene catalogue (all H5 files, sizes, checksums)</b><a class="dl__file" href="../../data/h5/catalog.json" download>' + DLI + 'catalog.json</a>' + (hasCat ? '' : '<span class="small muted">Not found on this server.</span>'), { u: '../../data/h5/catalog.json' }) +
        li('<b>Layer catalogue (what the dashboard shows)</b><a class="dl__file" href="' + D + 'manifest.json" download>' + DLI + 'manifest.json</a>', { u: D + 'manifest.json' }) + '</ul>' +
      '<h3>Dashboard data files</h3><ul class="dl">' + DL.map(function (d) { return '<li><span class="dl__main"><b>' + esc(d[1]) + '</b><a class="dl__file" href="' + D + d[0] + '" download>' + DLI + d[0] + '</a></span><span class="dl__size" data-size="' + D + d[0] + '"></span></li>'; }).join('') +
      '<li><span class="dl__main"><b>Mandal table as a spreadsheet</b><a class="dl__file" href="#" id="csvdl">' + DLI + (rankSample() ? 'mandal_rank_SAMPLE.csv' : 'mandal_rank.csv') + '</a><span class="small muted">Made in your browser from the same table ' + rankTag() + '</span></span><span class="dl__size"></span></li>' +
      imgsL.map(function (l) { var f = l.png.replace('data/processed/', ''); return '<li><span class="dl__main"><b>Radar quick-look, ' + esc(dshort(l.date)) + '</b><a class="dl__file" href="../../' + l.png + '" download>' + DLI + esc(f.split('/').pop()) + '</a>' + (l.h5 && !hasCat ? '<a class="dl__file" href="../../' + esc(l.h5) + '" download>' + DLI + 'H5 of record: ' + esc(l.h5.split('/').pop()) + '</a>' : '') + '<span class="small muted">For display only ' + (layerSample(l) ? tag(l.placeholder.tag || QUICK) : '') + '</span></span><span class="dl__size" data-size="../../' + esc(l.png) + '"></span></li>'; }).join('') + '</ul>';
  }
  function afterDl() {
    var pre = $('#cite-pre'); if (pre) pre.textContent = citeText() + '\n\n' + citeBib();
    var ml = $('#methods-link'); if (!ml) return;
    fetch('../../docs/METHODS.md', { method: 'HEAD' }).then(function (r) {
      ml.innerHTML = r.ok ? '<a class="dl__file" href="../../docs/METHODS.md">docs/METHODS.md</a>' : '<span class="muted">method notes coming</span>';
    }).catch(function () { ml.innerHTML = '<span class="muted">method notes coming</span>'; });
  }

  function sceneOptions() {
    var o = [];
    ROLES.forEach(function (r) { X.scenes[r].slice().reverse().forEach(function (l) { o.push('<option value="' + esc(l.id) + '"' + (l.id === S.histId ? ' selected' : '') + '>' + (r === 'sea' ? 'Sea' : 'Coast') + ', ' + esc(dshort(l.date)) + ' (' + esc(String(l.pol || '').toUpperCase()) + ')</option>'); }); });
    return o.join('');
  }
  function smBlock() {
    var rows = ROLES.filter(function (r) { return X.scenes[r].length; }).map(function (r) {
      return '<div class="sm__row"><h3>' + (r === 'sea' ? 'Sea' : 'Coast') + ' <span class="small muted">' + X.scenes[r].length + ' dates, oldest first</span></h3><div class="sm__g">' + X.scenes[r].map(function (l) {
        var st = String(l.processing_level || '').toUpperCase();
        return '<button type="button" class="sm__i" data-sm="' + esc(l.id) + '" data-role="' + r + '" aria-pressed="false" title="Show this picture on the map"><span class="sm__img"><img src="../../' + esc(l.png) + '" loading="lazy" alt="Radar brightness of the ' + (r === 'sea' ? 'sea' : 'coast') + ' on ' + esc(dshort(l.date)) + '"></span>' +
          '<span class="sm__d"><b>' + esc(dd(l.date)) + '</b><span>' + esc(st ? st.toLowerCase() : '') + (l.group ? ' · ' + esc(l.group) : '') + '</span></span></button>';
      }).join('') + '</div></div>';
    }).join('');
    return rows + '<div class="grayleg"><div class="gray" role="img" aria-label="Greyscale from dark (' + GRAY[0] + ' dB) to bright (' + GRAY[1] + ' dB)"></div><div class="ramp-l"><span>' + GRAY[0] + ' dB, dark</span><span>' + GRAY[1] + ' dB, bright</span></div></div>' +
      '<p class="small muted">All pictures use the same brightness scale, so they can be compared. Dark = smooth surface (calm water, calm sea); bright = rough or built-up. Click one to put it on the map.</p>';
  }
  function histCard() {
    return '<div class="card" id="d-hist"><div><h2>Brightness histogram</h2><p class="small">How many radar pixels fall at each brightness, for the chosen picture. It shows why the water classes can or cannot be separated.</p></div>' +
      '<div class="tools"><label class="small" for="hist-sel"><b>Picture</b></label><select id="hist-sel" class="sel">' + sceneOptions() + '</select></div><div id="hist-body"><p class="small muted">Loading&hellip;</p></div></div>';
  }
  var histCache = {};
  function drawHist() {
    var body = $('#hist-body'); if (!body) return;
    var id = S.histId, l = X.layers[id]; if (!l || !l.png) { body.innerHTML = '<p class="small">No picture chosen.</p>'; return; }
    function paint(d) {
      if (id !== S.histId) return;
      var h = d && d.hist; if (!h || !h.counts) { body.innerHTML = '<p class="small">No histogram is stored for this picture yet.</p>'; return; }
      var thr = d.water_threshold_db, sm = thr && h.counts_smoothed3x3, cnt = sm || h.counts, pols = Object.keys(cnt), co = String(d.pol || pols[0]).toUpperCase(), order = [co].concat(pols.filter(function (p) { return p !== co; }));
      var lo = h.range_db[0], hi = h.range_db[1], bw = h.bin_db, W = 420, H = 210, L = 44, R = 10, T = 12, B = 36;
      var ser = {}, ymax = 0;
      order.forEach(function (p) { var a = cnt[p] || [], t = a.reduce(function (s, v) { return s + v; }, 0) || 1; ser[p] = a.map(function (v) { return v / t * 100; }); ymax = Math.max(ymax, Math.max.apply(null, ser[p])); });
      var ytop = Math.ceil(ymax), ystep = ytop > 6 ? 2 : 1; ytop = Math.ceil(ytop / ystep) * ystep;
      function x(v) { return L + (v - lo) / (hi - lo) * (W - L - R); } function y(v) { return T + (ytop - v) / ytop * (H - T - B); }
      var s = '<svg class="chart" id="hchart" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="Histogram of radar brightness, ' + esc(order.join(' and ')) + ', in dB' + (thr ? ', with the water cut at ' + thr.value + ' dB' : '') + '">';
      if (thr) s += '<rect x="' + x(lo) + '" y="' + T + '" width="' + (x(thr.value) - x(lo)) + '" height="' + (H - T - B) + '" fill="' + css('--water-tint') + '"/>';
      for (var v = 0; v <= ytop; v += ystep) s += '<line x1="' + L + '" x2="' + (W - R) + '" y1="' + y(v) + '" y2="' + y(v) + '" stroke="' + css('--line') + '"/><text x="' + (L - 6) + '" y="' + (y(v) + 3) + '" text-anchor="end">' + v + '</text>';
      for (var t = Math.ceil(lo / 5) * 5; t <= hi; t += 5) s += '<text x="' + x(t) + '" y="' + (H - B + 13) + '" text-anchor="middle">' + t + '</text>';
      s += '<text x="' + (L + (W - L - R) / 2) + '" y="' + (H - 2) + '" text-anchor="middle">radar brightness (dB)</text><text x="10" y="' + (T + 70) + '" transform="rotate(-90 10 ' + (T + 70) + ')" text-anchor="middle">% of pixels per 0.5 dB</text>';
      order.forEach(function (p, i) {
        var pts = ser[p].map(function (v, k) { return x(lo + (k + 0.5) * bw).toFixed(1) + ',' + y(v).toFixed(1); });
        if (i === 0) s += '<polygon points="' + x(lo + bw / 2).toFixed(1) + ',' + y(0) + ' ' + pts.join(' ') + ' ' + x(lo + (ser[p].length - 0.5) * bw).toFixed(1) + ',' + y(0) + '" fill="' + css('--teal-tint') + '" opacity=".8"/>';
        s += '<polyline points="' + pts.join(' ') + '" fill="none" stroke="' + css(i === 0 ? '--teal' : '--ink-2') + '" stroke-width="' + (i === 0 ? 2 : 1.5) + '"' + (i === 0 ? '' : ' stroke-dasharray="4 3"') + '/>';
      });
      if (thr) s += '<line x1="' + x(thr.value) + '" x2="' + x(thr.value) + '" y1="' + T + '" y2="' + (H - B) + '" stroke="' + css('--water-ink') + '" stroke-width="1.8"/><text x="' + (x(thr.value) + 4) + '" y="' + (T + 10) + '" class="plab">water cut ' + thr.value + ' dB (' + thr.pol + ')</text><text x="' + (x(lo) + 4) + '" y="' + (T + 10) + '" class="plab">counted as water</text>';
      s += '</svg>';
      var below = '';
      if (thr && sm && sm[thr.pol]) {
        var a = sm[thr.pol], tt = a.reduce(function (q, w) { return q + w; }, 0) || 1, nb = Math.round((thr.value - lo) / bw), sb = 0; for (var k = 0; k < nb && k < a.length; k++) sb += a[k];
        below = '<p class="small"><b>' + n1(sb / tt * 100) + '%</b> of valid ' + esc(thr.pol) + ' pixels on this date are below the cut. ' + esc(thr.definition ? thr.definition.charAt(0).toUpperCase() + thr.definition.slice(1) + '.' : '') + ' The cut applies to the 3x3-smoothed ' + esc(thr.pol) + '. The share includes permanent water (sea, rivers, ponds); the flood class leaves that out.</p>';
      }
      body.innerHTML = s + '<div class="legendline"><span><i class="sw sw--tl"></i>' + esc(order[0]) + '</span>' + (order[1] ? '<span><i class="sw sw--dash"></i>' + esc(order[1]) + '</span>' : '') + (thr ? '<span><i class="sw sw--w"></i>Below the cut: counted as open water</span>' : '') + '</div>' + below +
        '<p class="small muted">' + (thr ? '' : 'No water cut is used on the sea: brighter simply means a rougher surface. ') + (d.nan_frac != null ? n0(d.nan_frac * 100) + '% of the box has no data (outside the radar swath). ' : '') + 'Source: ' + esc(d.layer_id || id) + '.json, made from ' + esc(d.h5 || 'the H5 file') + '.</p>';
    }
    if (histCache[id]) { paint(histCache[id]); return; }
    body.innerHTML = '<p class="small muted">Loading&hellip;</p>';
    getJSON('../../' + l.png.replace(/\.png$/, '.json')).then(function (d) { histCache[id] = d; paint(d); }).catch(function () { if (id === S.histId) body.innerHTML = '<p class="small">The histogram file could not be loaded.</p>'; });
  }

  function buildData() {
    var rank = X.rank || {};
    if (!S.histId) { var lh = latestScene('coast') || latestScene('sea'); S.histId = lh ? lh.id : null; }
    var tN = rank.normal_period ? 'normal period ' + dshort(rank.normal_period[0]) + ' to ' + dshort(rank.normal_period[1]) : 'a normal fortnight';
    $('#sec-data').innerHTML =
      '<nav class="chips" aria-label="Jump to a part of this section"><a href="#d-layers">Layers</a><a href="#d-mandals">Mandals</a><a href="#d-profile">Eye profile</a><a href="#d-small">Radar by date</a><a href="#d-hist">Histogram</a><a href="#d-scenes">Scenes</a><a href="#d-alerts">Alerts</a><a href="#d-files">Downloads</a><a href="#about-d">About and sources</a>' +
      '<a href="#" data-act="tohappened" class="chips__back">Plain-language view</a></nav>' +
      '<div class="card" id="d-layers"><div class="row row--between"><div><h2>Layers</h2><p class="small">Every map layer with its source, licence and known limits.</p></div><span class="small muted">Tick a box to draw a layer on the map</span></div><div class="tblwrap tblwrap--tall"><table class="dt"><thead><tr><th scope="col">Layer</th><th scope="col">Date</th><th scope="col">Source and credit</th><th scope="col">Licence</th><th scope="col">Status and limits</th><th scope="col">On map</th></tr></thead><tbody>' + layerRows() + '</tbody></table></div></div>' +
      (X.rows.length && rank.period ? '<div class="card" id="d-mandals"><div class="row row--between"><div><h2>Mandal table</h2></div>' + rankTag() + '</div>' +
        '<p class="small">Share of each mandal\'s area (valid land that is not permanent water), in % (± is the uncertainty in percentage points). Radar picture of ' + dshort(rank.latest_date || rank.period[1]) + ' against the pre-storm baseline; ' + esc(tN) + '. Area figures are share × the area the radar saw.</p>' +
        '<p class="small muted">The normal-fortnight comparison is the noise floor: a change smaller than that is not a storm signal. Where ± is as large as the value the row says so. Rank is by open water only; wet crops are a weak signal (radar cannot tell them from normal field change), so the total is optional.</p>' +
        '<div class="tools"><input type="search" id="mtq" placeholder="Filter mandal or district" aria-label="Filter mandals"><span class="small muted" id="mtcount"></span>' +
        '<div class="segl" role="group" aria-label="Rank by"><span class="segl__k">Rank by</span><button type="button" data-rankby="water" aria-pressed="true">Open water</button><button type="button" data-rankby="total" aria-pressed="false">Water + crops</button></div></div>' +
        '<div class="tblwrap"><table class="dt dt--m" id="mtable"><thead id="mthead"></thead><tbody id="mtbody"></tbody></table></div>' + flaggedHtml() + '</div>' : '<div class="card" id="d-mandals"><h2>Mandal table</h2><p class="small">The mandal numbers are not ready yet.</p></div>') +
      (X.hasProf ? '<div class="card" id="d-profile"><div class="row row--between"><h2>Eye profile</h2>' + (profSample() ? tag(X.profile.placeholder.tag || SAMPLE) : '') + '</div>' +
        profileText() + profileChart() + '</div>' : '<div class="card" id="d-profile"><h2>Eye profile</h2><p class="small">The eye profile is not ready yet.</p></div>') +
      '<div class="card" id="d-small"><div><h2>Radar by date</h2><p class="small">The same area on every date we hold, side by side. Coast first, then sea.</p></div>' + smBlock() + '</div>' +
      histCard() +
      '<div class="card" id="d-scenes"><div><h2>Scene catalogue</h2><p class="small">Every NISAR scene we hold as an H5 file, with when it was acquired, how, and how to check the file.</p></div>' + sceneBlock() + '</div>' +
      '<div class="card" id="d-alerts"><div><h2>Alerts</h2>' + (areaName() ? '<p class="small">For ' + esc(areaName()) + '. Each source shows when it was last read.</p>' : '') + '</div>' + alertsBlock() + '</div>' +
      '<div class="card" id="d-files"><div><h2>Downloads</h2><p class="small">Files as stored in the repository. H5 files are the data of record. Credits and licences are in the layer list above. NISAR data credit: NASA/JPL-Caltech and ISRO, via ASF DAAC.</p></div>' + dlBlock() + '</div>' + aboutHtml('about-d');
    mandalTable(); bindProfile(); afterDl(); drawHist(); markThumbs();
    // sizes (best effort)
    $$('[data-size]').forEach(function (e) {
      fetch(e.dataset.size, { method: 'HEAD' }).then(function (r) { var n = +r.headers.get('content-length'); if (n) e.textContent = n > 1e6 ? (n / 1e6).toFixed(1) + ' MB' : Math.round(n / 1e3) + ' KB'; }).catch(function () {});
    });
  }

  /* ---------------- UI wiring ---------------- */
  function setSection(s, o) {
    o = o || {};
    if (s === 'data' && S.mapMode !== 'custom') S.prevMode = S.mapMode;
    S.section = s;
    $('#main').dataset.section = s;
    $('#sec-happened').hidden = s !== 'happened'; $('#sec-data').hidden = s !== 'data';
    $('#tab-happened').setAttribute('aria-selected', String(s === 'happened')); $('#tab-happened').tabIndex = s === 'happened' ? 0 : -1;
    $('#tab-data').setAttribute('aria-selected', String(s === 'data')); $('#tab-data').tabIndex = s === 'data' ? 0 : -1;
    $('#map-modes').hidden = s !== 'happened';
    $('#panel').scrollTop = 0;
    if (s === 'happened') setMapMode(S.mapMode === 'custom' ? (S.prevMode || 'share') : S.mapMode, !o.keepView);
    else {
      var la = latestScene('coast') || latestScene('sea');
      S.mapMode = 'custom'; vis.img = {}; vis.before = null; if (la) vis.img[la.id] = 0.9; vis.outlines = true; vis.track = true;
      applyMap(); if (!o.keepView) fitFor('custom');
    }
    // the panel changes width over 250 ms; fit again once the map has its final size
    setTimeout(function () { map.invalidateSize({ animate: false }); if (!o.keepView) fitFor(S.mapMode); }, 300);
    writeHash();
  }

  function bindCopy() {
    $('#panel').addEventListener('click', function (e) {
      var b = e.target.closest('[data-copy]');
      function sel(el) { try { var r = document.createRange(); r.selectNodeContents(el); var g = window.getSelection(); g.removeAllRanges(); g.addRange(r); } catch (x) { /* ignore */ } }
      if (b) { e.preventDefault(); var full = b.getAttribute('data-copy'); copyText(full, function (ok) {
        flash(b, ok);
        if (!ok) { var code = b.previousElementSibling; if (code && code.classList.contains('sha')) { code.textContent = full; code.style.overflowWrap = 'anywhere'; sel(code); } }
      }); return; }
      var c = e.target.closest('[data-cite]');
      if (c) { e.preventDefault(); copyText(c.dataset.cite === 'bib' ? citeBib() : citeText(), function (ok) {
        flash(c, ok);
        if (!ok) { var d = $('#cite-pre'); if (d) { d.parentNode.open = true; sel(d); d.scrollIntoView({ block: 'nearest' }); } }
      }); }
    });
  }

  var PANEL_KEY = 'spacebros.nisar.panelCollapsed.v1';
  function setPanel(c, remember) {
    $('#main').classList.toggle('collapsed', c);
    ['#panel-toggle', '#panel-close'].forEach(function (id) { $(id).setAttribute('aria-expanded', String(!c)); });
    $('#panel-toggle').classList.toggle('is-collapsed', c); $('#panel-toggle-txt').textContent = c ? 'Show panel' : 'Hide panel';
    $('#panel').setAttribute('aria-hidden', String(c));
    if (c) $('#panel').setAttribute('inert', ''); else $('#panel').removeAttribute('inert');
    if (remember) { try { localStorage.setItem(PANEL_KEY, c ? '1' : '0'); } catch (e) { /* storage blocked */ } }
    setTimeout(function () { map.invalidateSize({ animate: false }); }, 280);
  }
  function bindUI() {
    bindCopy();
    var seg = $('#map-modes');
    seg.innerHTML = MODES.map(function (m) { return '<button type="button" data-m="' + m[0] + '" aria-pressed="false">' + m[1] + '</button>'; }).join('');
    seg.addEventListener('click', function (e) { var b = e.target.closest('button'); if (b) setMapMode(b.dataset.m, true); });

    $('#tab-happened').addEventListener('click', function () { if ($('#main').classList.contains('collapsed')) setPanel(false, true); setSection('happened'); });
    $('#tab-data').addEventListener('click', function () { if ($('#main').classList.contains('collapsed')) setPanel(false, true); setSection('data'); });
    $('.tabs').addEventListener('keydown', function (e) {
      if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') { var s = S.section === 'happened' ? 'data' : 'happened'; setSection(s); $('#tab-' + s).focus(); }
    });

    // side panel: map button and the close button inside the panel do the same thing; the choice is remembered in this browser
    $('#panel-toggle').addEventListener('click', function () { setPanel(!$('#main').classList.contains('collapsed'), true); });
    $('#panel-close').addEventListener('click', function () { setPanel(true, true); $('#panel-toggle').focus(); });
    var pc = null; try { pc = localStorage.getItem(PANEL_KEY); } catch (e) { pc = null; }
    if (pc === '1') setPanel(true, false);

    $('#swipe-range').addEventListener('input', function () { S.swipe = +this.value; updateSwipeLine(); clipBefore(); });

    $('#panel').addEventListener('click', function (e) {
      var t = e.target;
      var rb = t.closest('.rank__item'); if (rb) { selectMandal(rb.dataset.m, { fly: true, user: true }); return; }
      var tr = t.closest('#mtbody tr'); if (tr) { selectMandal(tr.dataset.m, { fly: true, user: true }); return; }
      var fmb = t.closest('[data-fm]'); if (fmb) { S.fm = true; selectMandal(fmb.dataset.fm, { fly: true, user: true }); return; }
      var rbb = t.closest('[data-rankby]'); if (rbb) { S.rankBy = rbb.dataset.rankby; S.sort = { k: 'rank', d: 1 }; mandalTable(); return; }
      var sm = t.closest('.sm__i'); if (sm) { showScene(sm.dataset.sm, sm.dataset.role); return; }
      var evc = t.closest('[data-evchip]'); if (evc) { e.preventDefault(); openEvent(evc.dataset.evchip); return; }
      var as = t.closest('[data-arch-save]'); if (as) { e.preventDefault(); saveArchive(as); return; }
      var so = t.closest('[data-sort]'); if (so) { var k = so.dataset.sort; S.sort = { k: k, d: S.sort.k === k ? -S.sort.d : 1 }; mandalTable(); return; }
      if (t.id === 'rankmore') { S.showAll = !S.showAll; renderRank(); return; }
      if (t.id === 'csvdl') { e.preventDefault(); csv(); return; }
      var a = t.closest('[data-act]'); if (!a) return;
      e.preventDefault();
      var act = a.dataset.act;
      if (act === 'zoom') { setMapMode('share', false); selectMandal(S.sel, { fly: true }); }
      if (act === 'storymap') storyMap();
      if (act === 'tolatest') { S.shareD = null; S.mapMode = 'share'; setMapMode('share', false); }
      if (act === 'evswipe') { if (X.scenes.coast.length) S.role = 'coast'; setMapMode('swipe', true); }
      if (act === 'swipe') { setMapMode('swipe', false); selectMandal(S.sel, { fly: true }); }
      if (act === 'eye') setMapMode('eye', true);
      if (act === 'todata') { setSection('data'); selectMandal(S.sel, {}); }
      if (act === 'tohappened') setSection('happened');
      if (act === 'raw') { setSection('data'); selectMandal(S.sel, {}); var tr2 = $('#mtbody tr[data-m="' + S.sel.replace(/"/g, '\\"') + '"]'); if (tr2) setTimeout(function () { tr2.scrollIntoView({ block: 'center' }); $('#d-mandals').scrollIntoView(); tr2.scrollIntoView({ block: 'nearest' }); }, 50); }
    });
    $('#panel').addEventListener('keydown', function (e) {
      var tr = e.target.closest && e.target.closest('#mtbody tr.clickable');
      if (tr && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); selectMandal(tr.dataset.m, { fly: true, user: true }); }
    });
    $('#panel').addEventListener('change', function (e) {
      if (e.target.id === 'hist-sel') { S.histId = e.target.value; drawHist(); return; }
      var cb = e.target.closest('input[data-lyr]'); if (!cb) return;
      var id = cb.dataset.lyr;
      if (S.mapMode !== 'custom') { S.mapMode = 'custom'; }
      if (id === 'mandal_boundaries') vis.outlines = cb.checked; else if (id === 'imd_track_arnab') vis.track = cb.checked;
      else { if (cb.checked) vis.img[id] = 0.9; else delete vis.img[id]; }
      applyMap(); writeHash();
    });
    $('#panel').addEventListener('input', function (e) { if (e.target.id === 'mtq') { S.q = e.target.value; mandalTable(); } if (e.target.id === 'fm-q') fmList(e.target.value); });
    $('#panel').addEventListener('keydown', function (e) {
      if (e.target.id === 'fm-q' && e.key === 'Enter') { var f = $('#fm-list .fm__b'); if (f) { e.preventDefault(); S.fm = true; selectMandal(f.dataset.fm, { fly: true, user: true }); } }
    });
  }

  /* ---------------- scenes: everything dated comes from the manifest ---------------- */
  function isImg(l) { return !!(l && l.kind === 'image' && l.png && l.bounds && l.status === 'ready'); }
  function buildScenes() {
    X.scenes = { coast: [], sea: [] };
    X.manifest.layers.forEach(function (l) {
      if (l.type !== 'nisar' || !isImg(l) || !l.date) return;
      var mm = /^nisar_l_(sea|coast)_/.exec(l.id), role = mm ? mm[1] : (/sea/.test(l.latest_of || '') ? 'sea' : 'coast');
      X.scenes[role].push(l);
    });
    ROLES.forEach(function (r) { X.scenes[r].sort(function (a, b) { return a.date < b.date ? -1 : a.date > b.date ? 1 : 0; }); });
  }
  function sceneBy(role, date) { var a = X.scenes[role] || []; for (var i = 0; i < a.length; i++) if (a[i].date === date) return a[i]; return null; }
  function latestScene(role) { var a = X.scenes[role]; return a.length ? a[a.length - 1] : null; }
  function defBefore(role, afterDate) {
    var a = X.scenes[role], best = null;
    a.forEach(function (l) { if (l.group === 'before' && l.date < afterDate) best = l; });
    if (!best) a.forEach(function (l) { if (l.date < afterDate) best = l; });
    return best ? best.date : (a.length ? a[0].date : null);
  }
  function setDefaults() {
    X.def = { after: {}, before: {}, eye: null, role: X.scenes.coast.length ? 'coast' : 'sea' };
    ROLES.forEach(function (r) { var la = latestScene(r); X.def.after[r] = la ? la.date : null; X.def.before[r] = la ? defBefore(r, la.date) : null; });
    var e = null; X.scenes.sea.forEach(function (l) { if (l.group === 'during') e = l; });
    if (!e) e = latestScene('sea');
    X.def.eye = e ? e.date : null;
    var yrs = {}; ROLES.forEach(function (r) { X.scenes[r].forEach(function (l) { yrs[l.date.slice(0, 4)] = 1; }); });
    X.multiYear = Object.keys(yrs).length > 1;
    S.role = X.def.role; S.dates = {}; ROLES.forEach(function (r) { S.dates[r] = { after: X.def.after[r], before: X.def.before[r] }; }); S.dEye = X.def.eye;
  }
  function dd(iso) {
    var d = new Date(iso + 'T00:00:00Z'); if (isNaN(d)) return iso;
    return d.toLocaleDateString('en-GB', { timeZone: 'UTC', day: 'numeric', month: 'short' }) + (X.multiYear ? ' ' + d.getUTCFullYear() : '');
  }
  function newestShareDate() {      // the share map is built for the newest derived class period
    var d = null;
    X.manifest.layers.forEach(function (l) { if (l.type === 'derived' && l.classes && l.date && (!d || l.date > d)) d = l.date; });
    return d && sceneBy('coast', d) ? d : X.def.after.coast;
  }
  function shareDate() { return S.shareD && sceneBy('coast', S.shareD) && X.rowsBy[S.shareD] ? S.shareD : newestShareDate(); }
  function classId(date) {
    var base = X.layers[(X.story && X.story.map && X.story.map.layer_id) || 'nisar_class_new_water'];
    if (!base || !base.png) return null;
    var cd = base.class_date || base.date;
    if (date === cd) return base.id;
    var id = base.id + '@' + date;
    if (!X.layers[id]) {
      var png = base.png.replace(/class_\d{8}_/, 'class_' + date.replace(/-/g, '') + '_');
      if (png === base.png) return null;
      var c = {}; Object.keys(base).forEach(function (k) { c[k] = base[k]; }); c.id = id; c.png = png; c.date = date; c.class_date = date; X.layers[id] = c;
    }
    return id;
  }
  function idAt(role, d) { var s = d && sceneBy(role, d); return s ? s.id : null; }
  function viewIds() {
    var m = S.mapMode, r = S.role, o = { after: null, before: null, cls: null };
    if (m === 'share') { o.after = idAt('coast', shareDate()); o.cls = classId(shareDate()); }
    else if (m === 'radar') o.after = idAt(r, S.dates[r].after);
    else if (m === 'swipe') { o.after = idAt(r, S.dates[r].after); o.before = idAt(r, S.dates[r].before); }
    else if (m === 'eye') o.after = idAt('sea', S.dEye);
    return o;
  }
  function primaryDate() {
    var m = S.mapMode;
    if (m === 'radar' || m === 'swipe') return S.dates[S.role].after;
    if (m === 'eye') return S.dEye;
    if (m === 'share') return shareDate();
    var la = latestScene('coast') || latestScene('sea'); return la ? la.date : null;
  }
  function modeName(m) { var f = MODES.filter(function (x) { return x[0] === m; })[0]; return f ? f[1] : 'Layer list'; }

  /* ---------------- timeline (date selector on the map) ---------------- */
  function renderTimeline() {
    var tl = $('#tl'); if (!tl) return;
    var m = S.mapMode, show = ((m === 'radar' || m === 'swipe' || m === 'eye') && (X.scenes.coast.length + X.scenes.sea.length) > 0) || (m === 'share' && X.shareDates.length > 1);
    tl.hidden = !show; if (!show) return;
    var act = document.activeElement, keep = act && tl.contains(act) && act.dataset ? act.dataset.tl + '|' + act.dataset.v : null;
    function row(k, inner) { return '<div class="tl__row"><span class="tl__k">' + k + '</span>' + inner + '</div>'; }
    function dates(kind, role, cur) {
      var arr = X.scenes[role];
      if (!arr.length) return '<span class="tl__none">No scenes yet</span>';
      return '<div class="seg" role="group" aria-label="' + esc(kind === 'before' ? 'Before scene' : 'Scene') + ' dates, ' + role + '">' + arr.map(function (l) {
        var t = dshort(l.date) + (l.processing_level ? ', ' + l.processing_level : '') + (l.name ? ': ' + l.name : '');
        return '<button type="button" data-tl="' + kind + '" data-v="' + l.date + '" aria-pressed="' + (l.date === cur) + '" title="' + esc(t) + '">' + esc(dd(l.date)) + '</button>';
      }).join('') + '</div>';
    }
    var h = '';
    if (m === 'share') h += row('Day', '<div class="seg" role="group" aria-label="Flood share day">' + X.shareDates.map(function (d) { return '<button type="button" data-tl="share" data-v="' + d + '" aria-pressed="' + (d === shareDate()) + '" title="' + esc(dshort(d)) + '">' + esc(dd(d)) + '</button>'; }).join('') + '</div>');
    if (m === 'radar' || m === 'swipe') h += row('Area', '<div class="seg" role="group" aria-label="Coast or sea scenes">' + ROLES.map(function (r) {
      return '<button type="button" data-tl="role" data-v="' + r + '" aria-pressed="' + (r === S.role) + '"' + (X.scenes[r].length ? '' : ' disabled') + '>' + (r === 'sea' ? 'Sea' : 'Coast') + '</button>'; }).join('') + '</div>');
    if (m === 'radar') h += row('Date', dates('after', S.role, S.dates[S.role].after));
    if (m === 'swipe') h += row('Before', dates('before', S.role, S.dates[S.role].before)) + row('After', dates('after', S.role, S.dates[S.role].after));
    if (m === 'eye') h += row('Date', dates('eye', 'sea', S.dEye));
    tl.innerHTML = h;
    if (keep) { var b = $$('button', tl).filter(function (x) { return x.dataset.tl + '|' + x.dataset.v === keep; })[0]; if (b) b.focus(); }
  }

  /* ---------------- view state <-> URL hash ---------------- */
  function curState() {
    var st = { tab: S.section, mode: S.section === 'data' ? 'custom' : S.mapMode, role: S.role, mandal: S.fm ? S.sel : null };
    if (st.mode === 'radar' || st.mode === 'swipe') { st.d = S.dates[S.role].after; if (st.mode === 'swipe') st.b = S.dates[S.role].before; }
    if (st.mode === 'eye') st.d = S.dEye;
    if (st.mode === 'share') st.d = shareDate();
    if (st.mode === 'custom') st.layers = Object.keys(vis.img).filter(function (k) { return vis.img[k]; });
    if (mapReady()) { var c = map.getCenter(); st.c = [+c.lat.toFixed(4), +c.lng.toFixed(4)]; st.z = +map.getZoom().toFixed(2); }
    return st;
  }
  function toHash(st) {
    var p = ['tab=' + st.tab, 'mode=' + st.mode];
    if (st.mode === 'radar' || st.mode === 'swipe') p.push('role=' + st.role);
    if (st.d) p.push('d=' + st.d);
    if (st.b) p.push('b=' + st.b);
    if (st.mandal) p.push('m=' + encodeURIComponent(st.mandal));
    if (st.layers && st.layers.length) p.push('l=' + st.layers.map(encodeURIComponent).join(','));
    if (st.c) p.push('c=' + st.c.join(','));
    if (st.z != null) p.push('z=' + st.z);
    return p.join('&');
  }
  function parseHash(hs) {
    var h = (hs == null ? location.hash : hs).replace(/^#/, ''), st = {};
    if (!h) return st;
    if (h.indexOf('=') < 0) { if (h === 'data' || h === 'happened') st.tab = h; return st; }
    h.split('&').forEach(function (kv) {
      var i = kv.indexOf('='); if (i < 0) return;
      var k = kv.slice(0, i), v = kv.slice(i + 1);
      try { v = decodeURIComponent(v); } catch (e) { return; }
      if (k === 'tab') st.tab = v; else if (k === 'mode') st.mode = v; else if (k === 'role') st.role = v;
      else if (k === 'd') st.d = v; else if (k === 'b') st.b = v; else if (k === 'm') st.mandal = v;
      else if (k === 'l') st.layers = v.split(',').filter(Boolean);
      else if (k === 'c') { var a = v.split(',').map(parseFloat); if (a.length === 2 && isFinite(a[0]) && isFinite(a[1])) st.c = a; }
      else if (k === 'z') { var z = parseFloat(v); if (isFinite(z)) st.z = z; }
    });
    return st;
  }
  function writeHash(now) {
    if (!ready) return;
    clearTimeout(hashTimer);
    function go() { var h = '#' + toHash(curState()); lastHash = h; try { history.replaceState(null, '', h); } catch (e) { /* file:// or sandbox */ } }
    if (now === true) go(); else hashTimer = setTimeout(go, 200);
  }

  /* Restore a view (from the URL or a saved day). Dates are looked up by value, never by position,
     so a scene that has gone from the archive is reported politely and the newest one is used. */
  /* a permalink centre/zoom is only used when it is inside the study area (generous margin) and at a sensible zoom */
  function validView(st) {
    if (!st.c || st.z == null || !isFinite(st.c[0]) || !isFinite(st.c[1]) || !isFinite(st.z)) return false;
    var b = L.latLngBounds(SEA).extend(DELTA[0]).extend(DELTA[1]).pad(1.5);
    return b.contains([st.c[0], st.c[1]]) && st.z >= 5 && st.z <= 18;
  }
  function applyView(st) {
    st = st || {};
    var notes = [];
    var tab = st.tab === 'data' ? 'data' : 'happened';
    var mode = ['share', 'radar', 'swipe', 'eye'].indexOf(st.mode) >= 0 ? st.mode : 'share';
    S.role = (st.role === 'sea' || st.role === 'coast') && X.scenes[st.role].length ? st.role : X.def.role;
    ROLES.forEach(function (r) { S.dates[r] = { after: X.def.after[r], before: X.def.before[r] }; });
    S.dEye = X.def.eye; S.shareD = null;
    function pick(role, d, fb) {
      if (!d) return fb;
      if (sceneBy(role, d)) return d;
      notes.push('The ' + role + ' radar scene of ' + dshort(d) + ' is not in the archive any more, so this view shows ' + (fb ? 'the ' + dshort(fb) + ' scene instead' : 'no scene') + '.');
      return fb;
    }
    if (tab === 'happened') {
      if (mode === 'share' && st.d) { if (X.rowsBy[st.d] && sceneBy('coast', st.d)) S.shareD = st.d; else notes.push('The flood-share day of ' + dshort(st.d) + ' is not in the archive any more, so this view shows the newest day.'); }
      if (mode === 'eye') S.dEye = pick('sea', st.d, X.def.eye);
      if (mode === 'radar' || mode === 'swipe') S.dates[S.role].after = pick(S.role, st.d, X.def.after[S.role]);
      if (mode === 'swipe') S.dates[S.role].before = pick(S.role, st.b, X.def.before[S.role]);
      S.mapMode = mode;
    }
    if (st.mandal && hasM(st.mandal)) { S.sel = st.mandal; S.fm = true; } else if (!S.sel && X.rows.length) S.sel = X.rows[0].mandal;
    var haveView = !!(st.c && st.z != null);
    if (haveView && !validView(st)) { haveView = false; notes.push('The map position in this link is outside the study area, so the map shows the whole area instead.'); }
    setSection(tab, { keepView: haveView });
    if (tab === 'data' && st.layers) {
      vis.img = {};
      st.layers.forEach(function (id) { if (isImg(X.layers[id])) vis.img[id] = 0.9; else notes.push('The layer "' + id + '" is no longer in the list.'); });
      applyMap();
    }
    if (haveView && mapReady()) map.setView([st.c[0], st.c[1]], st.z, { animate: false });
    else if (haveView) S.pendingView = st;
    if (S.sel) selectMandal(S.sel, {});
    S.notice = notes.join(' '); say(S.notice);
    renderTimeline(); updateNow();
  }

  /* ---------------- saved days (localStorage, always in try/catch) ---------------- */
  function loadSaved() {
    var raw = null, a = [];
    try { raw = localStorage.getItem(STORE_KEY); S.storeOK = true; } catch (e) { S.storeOK = false; return []; }
    try { a = JSON.parse(raw || '[]'); } catch (e) { a = []; }
    return Array.isArray(a) ? a.filter(function (r) { return r && typeof r.id === 'string' && typeof r.label === 'string' && typeof r.mode === 'string'; }) : [];
  }
  function persist() {
    try { localStorage.setItem(STORE_KEY, JSON.stringify(S.saved)); S.storeOK = true; return true; } catch (e) { S.storeOK = false; return false; }
  }
  function findSaved(id) { return S.saved.filter(function (r) { return r.id === id; })[0]; }
  function uid() { return Date.now().toString(36) + Math.random().toString(36).slice(2, 6); }
  function say(t, html) { var el = $('#dc-msg'); if (!el) return; if (html) el.innerHTML = t; else el.textContent = t || ''; el.hidden = !t; }

  function buildDayCard() {
    var ls = ROLES.filter(function (r) { return X.scenes[r].length; });
    var all = ROLES.map(function (r) { return latestScene(r); }).filter(Boolean).sort(function (a, b) { return a.date < b.date ? 1 : -1; })[0];
    $('#daycard').innerHTML =
      '<div class="row row--between"><span class="eyebrow">This view</span><span class="small" id="dc-now"></span></div>' +
      '<div class="row"><button type="button" class="btn btn--sm" data-day="save">Save this day</button>' +
      '<button type="button" class="btn btn--sm" data-day="copy">Copy link</button>' +
      '<button type="button" class="btn btn--sm" data-day="files" aria-expanded="false" aria-controls="dc-files">Download this day</button></div>' +
      '<div id="dc-form"></div><p class="small" id="dc-msg" role="status" aria-live="polite" hidden></p><div id="dc-files" hidden></div>' +
      '<div id="dc-saved"></div>' +
      '<p class="small muted" id="dc-latest">' + (all ? 'Latest scene: <b>' + esc(dshort(all.date)) + '</b> (' + ls.map(function (r) { return r + ' ' + esc(dd(latestScene(r).date)); }).join(', ') + '). ' : 'No radar scenes listed yet. ') +
      'Radar layers built: <b>' + esc(ist(X.manifest.generated_utc)) + '</b>.</p>';
    renderSaved(); updateNow();
  }
  function viewSig() { return [S.mapMode, S.role, primaryDate(), S.mapMode === 'swipe' ? S.dates[S.role].before : '', S.mapMode === 'custom' ? Object.keys(vis.img).join(',') : ''].join('|'); }
  function updateNow() {
    var el = $('#dc-now'); if (!el) return;
    var fb = $('#dc-files'); if (fb && !fb.hidden && fb.dataset.sig !== viewSig()) { fb.hidden = true; var fbtn = $('[data-day="files"]'); if (fbtn) fbtn.setAttribute('aria-expanded', 'false'); }
    var m = S.mapMode, d = primaryDate(), t;
    if (m === 'custom') t = 'Layer list';
    else { t = modeName(m); if (m === 'swipe' && S.dates[S.role].before) t += ' (vs ' + dd(S.dates[S.role].before) + ')'; if (d) t = dshort(d) + ' · ' + t; }
    el.textContent = t;
  }
  function savedSub(r) {
    var v = r.view || {}, bits = [r.date ? dshort(r.date) : '', r.mode === 'custom' ? 'Layer list' : modeName(r.mode)];
    if ((r.mode === 'radar' || r.mode === 'swipe') && v.role) bits.push(v.role === 'sea' ? 'sea' : 'coast');
    var gone = [];
    if (r.mode === 'radar' || r.mode === 'swipe') { if (r.date && !sceneBy(v.role === 'sea' ? 'sea' : 'coast', r.date)) gone.push(r.date); if (r.mode === 'swipe' && v.before && !sceneBy(v.role === 'sea' ? 'sea' : 'coast', v.before)) gone.push(v.before); }
    if (r.mode === 'eye' && r.date && !sceneBy('sea', r.date)) gone.push(r.date);
    return bits.filter(Boolean).join(' · ') + (gone.length ? ' · scene not in the archive now' : '');
  }
  function renderSaved() {
    var el = $('#dc-saved'); if (!el) return;
    if (!S.saved.length) {
      el.innerHTML = '<p class="small muted">Saved days will be listed here. They stay in this browser only; use Copy link to share a view.' + (S.storeOK ? '' : ' This browser is blocking storage, so a saved day lasts only until you close the page.') + '</p>';
      return;
    }
    el.innerHTML = '<h3>Saved days</h3><ul class="sd">' + S.saved.map(function (r) {
      return '<li class="sd__i"><button type="button" class="sd__open" data-sd="open" data-id="' + esc(r.id) + '"><b>' + esc(r.label) + '</b><span>' + esc(savedSub(r)) + '</span></button>' +
        '<span class="sd__acts"><button type="button" class="linkbtn small" data-sd="rename" data-id="' + esc(r.id) + '" aria-label="Rename ' + esc(r.label) + '">Rename</button>' +
        '<button type="button" class="linkbtn small" data-sd="remove" data-id="' + esc(r.id) + '" aria-label="Remove ' + esc(r.label) + '">Remove</button></span></li>';
    }).join('') + '</ul><p class="small muted">Saved in this browser only' + (S.storeOK ? '' : ' (storage is blocked here, so these last only until you close the page)') + '. Use Copy link to share a view.</p>';
  }

  var formCb = null;
  function showForm(label, value, cb) {
    formCb = cb;
    $('#dc-form').innerHTML = '<form class="dform" id="dc-formf"><label for="dc-name">' + esc(label) + '</label><div class="row"><input id="dc-name" type="text" maxlength="60" autocomplete="off" value="' + esc(value) + '">' +
      '<button type="submit" class="btn btn--sm">Save</button><button type="button" class="linkbtn small" data-day="cancel">Cancel</button></div></form>';
    var i = $('#dc-name'); i.focus(); i.select();
  }
  function clearForm() { formCb = null; $('#dc-form').innerHTML = ''; }

  function saveCurrent(label) {
    writeHash(true);
    var st = curState(), d = primaryDate();
    var rec = { id: uid(), label: label || (d ? dshort(d) : 'Saved view'), date: d, mode: st.mode,
                view: { tab: st.tab, role: st.role, before: st.b || null, mandal: st.mandal || null, c: st.c, z: st.z, layers: st.layers || null }, saved_at: new Date().toISOString() };
    S.saved.unshift(rec);
    var ok = persist(); renderSaved();
    say(ok ? 'Saved "' + rec.label + '". It is listed below.' : 'Saved "' + rec.label + '" for this visit only: this browser blocks storage. Use Copy link to keep it.');
  }
  function openSaved(id) {
    var r = findSaved(id); if (!r) return;
    var v = r.view || {};
    applyView({ tab: r.mode === 'custom' ? 'data' : v.tab, mode: r.mode, role: v.role, d: r.date, b: v.before, mandal: v.mandal, c: v.c, z: v.z, layers: v.layers });
    writeHash(true);
    if (!S.notice) say('Opened "' + r.label + '".');
    $('#panel').scrollTop = 0;
  }

  function copyLink() {
    writeHash(true);
    var url = location.href;
    function fallback() {
      $('#dc-form').innerHTML = '<div class="dform"><label for="dc-url">Copy this link</label><div class="row"><input id="dc-url" type="text" readonly value="' + esc(url) + '"><button type="button" class="linkbtn small" data-day="cancel">Close</button></div></div>';
      var i = $('#dc-url'); i.focus(); i.select(); say('Press Ctrl+C (Cmd+C on a Mac) to copy the link.');
    }
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(url).then(function () { say('Link copied. It reopens this exact view.'); }, fallback);
      else fallback();
    } catch (e) { fallback(); }
  }

  /* ---------------- "Download this day" ---------------- */
  var dayUrl = null;
  function dayLayers() {
    var o = viewIds(), ids = [];
    if (S.mapMode === 'custom') ids = Object.keys(vis.img).filter(function (k) { return vis.img[k]; });
    else { if (o.before) ids.push(o.before); if (o.after) ids.push(o.after); if (o.cls) ids.push(o.cls); }
    return ids.map(function (id) { return X.layers[id]; }).filter(Boolean);
  }
  function absUrl(p) { return p ? new URL('../../' + p, location.href).href : null; }
  function metaFor(l) {
    if (!/^data\/web\//.test(l.png || '')) return Promise.resolve(null);
    return getJSON('../../' + l.png.replace(/\.png$/, '.json')).catch(function () { return null; });
  }
  function fileOf(p) { return String(p).split('/').pop(); }
  function showFiles() {
    var box = $('#dc-files'), btn = $('[data-day="files"]');
    if (!box.hidden) { box.hidden = true; btn.setAttribute('aria-expanded', 'false'); return; }
    box.hidden = false; btn.setAttribute('aria-expanded', 'true'); box.dataset.sig = viewSig();
    var ls = dayLayers();
    if (!ls.length) { box.innerHTML = '<p class="small">No radar picture is on the map in this view. Choose a date, then try again.</p>'; return; }
    box.innerHTML = '<p class="small">Preparing the files&hellip;</p>';
    writeHash(true);
    Promise.all(ls.map(metaFor)).then(function (metas) {
      var st = curState(), link = location.href, d = primaryDate() || 'view';
      var doc = {
        schema: 'spacebros-day-export-v1', exported_utc: new Date().toISOString(), manifest_generated_utc: X.manifest.generated_utc,
        title: (X.event && X.event.name ? X.event.name + ': ' : '') + (st.mode === 'custom' ? 'layer list' : modeName(st.mode)) + ', ' + d,
        date: d, mode: st.mode, role: st.mode === 'radar' || st.mode === 'swipe' ? st.role : null, link: link, view: st,
        note: 'The PNG files are display images, not data of record. The data of record is the H5 subset named for each layer.',
        layers: ls.map(function (l, i) {
          var mt = metas[i] || {};
          return { id: l.id, name: l.name, type: l.type, date: l.date, time_utc: l.time_utc || null, band: l.band || null, pol: l.pol || null, track: l.track == null ? null : l.track, frame: l.frame == null ? null : l.frame,
                   direction: l.direction || null, processing_level: l.processing_level || null, bounds: l.bounds, bounds_inferred: !!l.bounds_inferred,
                   png: absUrl(l.png), h5: absUrl(l.h5), h5_sources: (l.h5_sources || []).map(absUrl),
                   source_granule: mt.source_granule || null, product_status: mt.product_status || null, build_info: metas[i] || null,
                   source: l.source || null, credit: l.credit || null, limit: l.limit || null, placeholder: l.placeholder || null };
        })
      };
      if (dayUrl) { try { URL.revokeObjectURL(dayUrl); } catch (e) { /* ignore */ } }
      dayUrl = URL.createObjectURL(new Blob([JSON.stringify(doc, null, 2)], { type: 'application/json' }));
      var jname = 'nisar_day_' + d + '_' + st.mode + '.json';
      box.innerHTML = '<ul class="dl">' + ls.map(function (l) {
        var h5s = (l.h5 ? [l.h5] : []).concat(l.h5_sources || []);
        return '<li><span class="dl__main"><b>' + esc(l.name) + ', ' + esc(dshort(l.date)) + '</b>' +
          (missing[l.id] ? '<span class="small muted">Picture not available yet.</span>' : '<a class="dl__file" href="../../' + esc(l.png) + '" download>' + DLI + 'Picture: ' + esc(fileOf(l.png)) + '</a>') +
          h5s.map(function (h) { return '<a class="dl__file" href="../../' + esc(h) + '" download>' + DLI + 'H5 file of record: ' + esc(fileOf(h)) + '</a>'; }).join('') +
          '<span class="small muted">The picture is for display only ' + (layerSample(l) ? tag(l.placeholder.tag) : '') + ' The H5 file is the data of record and can be large.</span></span></li>';
      }).join('') +
        '<li><span class="dl__main"><b>This day as a JSON file</b><a class="dl__file" href="' + dayUrl + '" download="' + esc(jname) + '">' + DLI + esc(jname) + '</a>' +
        '<span class="small muted">Date, layer details, source granule, bounds and the link to this view.</span></span></li></ul>';
    });
  }

  function bindDay() {
    $('#daycard').addEventListener('click', function (e) {
      var b = e.target.closest('[data-day],[data-sd]'); if (!b) return;
      var a = b.dataset.day, sd = b.dataset.sd, id = b.dataset.id;
      if (a === 'save') { var d = primaryDate(); showForm('Name this day', d ? dshort(d) : 'Saved view', saveCurrent); }
      else if (a === 'copy') copyLink();
      else if (a === 'files') showFiles();
      else if (a === 'cancel') { clearForm(); }
      else if (a === 'undo' && S.undo) { S.saved.splice(Math.min(S.undo.i, S.saved.length), 0, S.undo.r); S.undo = null; persist(); renderSaved(); say('Restored.'); }
      else if (sd === 'open') openSaved(id);
      else if (sd === 'rename') { var r = findSaved(id); if (r) showForm('Rename this saved day', r.label, function (v) { if (v) { r.label = v; persist(); renderSaved(); say('Renamed to "' + v + '".'); } }); }
      else if (sd === 'remove') {
        var i = S.saved.map(function (x) { return x.id; }).indexOf(id);
        if (i >= 0) { var rec = S.saved.splice(i, 1)[0]; S.undo = { r: rec, i: i }; persist(); renderSaved(); say('Removed "' + esc(rec.label) + '". <button type="button" class="linkbtn small" data-day="undo">Undo</button>', true); }
      }
    });
    $('#daycard').addEventListener('submit', function (e) {
      e.preventDefault(); var i = $('#dc-name'), cb = formCb, v = i ? i.value.trim() : '';
      clearForm(); if (cb) cb(v);
    });
    $('#daycard').addEventListener('keydown', function (e) { if (e.key === 'Escape' && $('#dc-form').firstChild) { clearForm(); } });
    $('#tl').addEventListener('click', function (e) {
      var b = e.target.closest('button[data-tl]'); if (!b || b.disabled) return;
      var k = b.dataset.tl, v = b.dataset.v;
      if (k === 'role') S.role = v;
      else if (k === 'after') S.dates[S.role].after = v;
      else if (k === 'before') S.dates[S.role].before = v;
      else if (k === 'eye') S.dEye = v;
      else if (k === 'share') S.shareD = v;
      setMapMode(S.mapMode, k === 'role');
    });
  }

  function showScene(id, role) {
    var l = X.layers[id]; if (!l) return;
    S.mapMode = 'custom'; vis.img = {}; vis.img[id] = 0.9; vis.before = null; vis.outlines = true; vis.track = true;
    S.histId = id; var hs = $('#hist-sel'); if (hs) { hs.value = id; drawHist(); }
    applyMap(); map.invalidateSize({ animate: false }); map.fitBounds(role === 'sea' ? SEA : DELTA, { animate: false }); writeHash();
  }
  function saveArchive(btn) {
    var rec = archiveRec(+btn.dataset.archSave); if (!rec) return;
    var dup = S.saved.filter(function (r) { return r.date === rec.date && r.mode === rec.mode && (r.view || {}).role === rec.view.role; })[0];
    var orig = btn.getAttribute('data-label') || btn.textContent; btn.setAttribute('data-label', orig);
    if (dup) { btn.textContent = 'Already saved'; }
    else { S.saved.unshift(rec); var ok = persist(); renderSaved(); btn.textContent = ok ? 'Saved' : 'Saved (this visit only)'; }
    clearTimeout(btn._t); btn._t = setTimeout(function () { btn.textContent = orig; }, 2200);
  }
  function csv() {
    var h = 'rank_water,rank_total,mandal,district,water_pct,water_err,crops_pct,crops_err,total_pct,total_err,normal_water_pct,water_km2,flooded_km2,change_vs_normal_pp_water,change_vs_normal_pp_total,coverage_pct\n';
    var b = X.rows.map(function (r) { return [r.rank, r.rankT, '"' + r.mandal + '"', '"' + r.district + '"', r.water, r.we, r.crops, r.ce, r.tot, r.te, r.normal, r.km, r.kmT, r.chg, r.chgT, r.cover].map(function (v) { return v == null ? '' : v; }).join(','); }).join('\n');
    var a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([h + b], { type: 'text/csv' })); a.download = rankSample() ? 'mandal_rank_SAMPLE.csv' : 'mandal_rank.csv'; a.click();
  }
})();
