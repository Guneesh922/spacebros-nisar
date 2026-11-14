/* Dashboard mockup logic. Plain JS, no build. Words live in js/findings.js (FINDINGS). */
(function () {
  'use strict';
  var D = '../../data/processed/';
  var F = window.FINDINGS;
  var SAMPLE = 'Sample values', QUICK = 'Quick-look sample';
  var AFTER = 'nisar_l_coast_20261109_t55_hh', BEFORE = 'nisar_l_coast_20261016_t55_hh', EYE = 'nisar_l_sea_20261027_t48_vv';
  var DELTA = [[16.2, 81.5], [17.25, 82.7]], SEA = [[15.3, 81.5], [17.7, 84.0]];
  var MODES = [['share', 'Flood share'], ['radar', 'Radar, after'], ['swipe', 'Before and after'], ['eye', 'Cyclone eye']];

  var S = { section: 'happened', mapMode: 'share', sel: null, swipe: 50, showAll: false, sort: { k: 'rank', d: 1 }, q: '' };
  var X = {};                                  // loaded data
  var vis = { img: {}, outlines: true, track: true };
  var missing = {}, map, imgs = {}, mandLayer, featByName = {}, trackGrp, eyeGrp, hoverRing, built = {};

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
  function getJSON(u) { return fetch(u).then(function (r) { if (!r.ok) throw new Error(u + ' ' + r.status); return r.json(); }); }

  /* ---------------- load ---------------- */
  Promise.all([getJSON(D + 'manifest.json'), getJSON(D + 'mandals.geojson'), getJSON(D + 'mandal_rank.json'),
               getJSON(D + 'profile.json'), getJSON(D + 'alerts.json'), getJSON(D + 'imd_track_arnab.geojson')])
    .then(function (a) { X.manifest = a[0]; X.mandals = a[1]; X.rank = a[2]; X.profile = a[3]; X.alerts = a[4]; X.track = a[5]; init(); })
    .catch(function (e) {
      var b = $('#banner'); b.hidden = false;
      b.setAttribute('role', 'alert'); b.textContent = 'The data files could not be loaded (' + e.message + '). Serve the repo root with "python3 -m http.server 8000" and open http://localhost:8000/app/dashboard-mockup/ .';
      console.error(e);
    });

  function init() {
    var m = X.manifest;
    $('#hdr-meta').textContent = 'Data updated ' + ist(m.generated_utc);
    $('#hdr-meta').classList.remove('is-loading');
    X.rows = X.rank.rows.map(function (r) {
      var lik = r.water_pct + r.crops_pct;
      return { mandal: r.mandal, district: r.district, water: r.water_pct, crops: r.crops_pct, we: r.water_err, ce: r.crops_err,
               lik: lik, err: Math.hypot(r.water_err, r.crops_err), normal: r.normal_pct, ratio: lik / r.normal_pct, rank: r.rank };
    }).sort(function (a, b) { return a.rank - b.rank; });
    X.byName = {}; X.rows.forEach(function (r) { X.byName[r.mandal] = r; });
    var pts = X.profile.points, pk = pts[0]; pts.forEach(function (p) { if (p.db > pk.db) pk = p; });
    X.peak = pk;
    X.layers = {}; m.layers.forEach(function (l) { X.layers[l.id] = l; });
    X.event = m.events[0];
    S.sel = X.rows[0].mandal;

    initMap();
    buildHappened();
    buildData();
    bindUI();
    setMapMode('share', true);
    selectMandal(S.sel, { fly: false });
    var h = location.hash.replace('#', ''); if (h === 'data') setSection('data');
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

    Object.keys(X.layers).forEach(function (id) {
      var l = X.layers[id];
      if (l.kind === 'image' && l.png && l.bounds && l.status === 'ready') {
        imgs[id] = L.imageOverlay('../../' + l.png, l.bounds, { pane: id === BEFORE ? 'radar2' : 'radar', opacity: 0.9, alt: l.name });
        imgs[id].on('add', clipBefore);
        (function (id) { imgs[id].on('error', function () { missing[id] = true; if (map.hasLayer(imgs[id])) map.removeLayer(imgs[id]); applyMap(); }); })(id);
      }
    });

    // mandal polygons (name match; for duplicates prefer the one in the ranked district)
    mandLayer = L.geoJSON(X.mandals, {
      style: mStyle,
      onEachFeature: function (f, lyr) {
        var nm = f.properties.name;
        var r = X.byName[nm];
        if (r && (!featByName[nm] || (f.properties.district && f.properties.district === r.district))) featByName[nm] = lyr;
        lyr.on('click', function () { if (X.byName[nm]) selectMandal(nm, { fly: false }); });
        lyr.bindTooltip(function () {
          var rr = X.byName[nm];
          return '<span>' + esc(nm) + (rr ? ': about ' + n0(rr.lik) + '% probably flooded (sample)' : '') + '</span>';
        }, { sticky: true, className: 'map-tip' });
      }
    });

    // track, eye, landfall
    trackGrp = L.layerGroup(); eyeGrp = L.layerGroup();
    var line = X.track.features.filter(function (f) { return f.geometry.type === 'LineString'; })[0];
    if (line) L.polyline(line.geometry.coordinates.map(function (c) { return [c[1], c[0]]; }),
      { color: css('--on-stage-muted'), weight: 2.5, dashArray: '6 6', opacity: 0.95 }).bindTooltip('Cyclone path (IMD fixes joined by straight lines)', { sticky: true, className: 'map-tip' }).addTo(trackGrp);
    var lf = X.event.landfall;
    L.circleMarker([lf.lat, lf.lon], { radius: 7, color: css('--white'), weight: 2, fillColor: css('--stage'), fillOpacity: 1 })
      .bindTooltip('Landfall area. ' + (lf.time_utc ? ist(lf.time_utc) : 'Time being confirmed (IMD)'), { className: 'map-tip' }).addTo(trackGrp);
    var eye = X.profile.eye;
    L.circle(eye, { radius: X.profile.eye_radius_km * 1000, color: css('--teal-onmap'), weight: 2, fill: false })
      .bindTooltip('Calm eye, about ' + X.profile.eye_radius_km + ' km radius (sample)', { sticky: true, className: 'map-tip' }).addTo(eyeGrp);
    L.circle(eye, { radius: X.peak.r_km * 1000, color: css('--teal-onmap'), weight: 1.5, dashArray: '3 5', fill: false })
      .bindTooltip('Roughest sea, about ' + X.peak.r_km + ' km from the centre (sample)', { sticky: true, className: 'map-tip' }).addTo(eyeGrp);
    L.circleMarker(eye, { radius: 3, color: css('--teal-onmap'), fillColor: css('--teal-onmap'), fillOpacity: 1, weight: 1 }).addTo(eyeGrp);

    map.on('move zoomend resize', clipBefore);
  }

  function mStyle(f) {
    var nm = f.properties.name, r = X.byName[nm];
    var sel = r && S.sel === nm && featByName[nm] && featByName[nm].feature === f;
    var share = S.mapMode === 'share' && r;
    var base = { color: css('--on-stage-muted'), weight: r ? 1 : 0.6, opacity: r ? 0.7 : 0.3, fillColor: css('--water'), fillOpacity: share ? 0.12 + 0.6 * Math.min(1, r.lik / 35) : (r ? 0.02 : 0) };
    if (sel) { base.color = css('--white'); base.weight = 3; base.opacity = 1; }
    return base;
  }

  function clipBefore() {
    var o = imgs[BEFORE]; if (!o || !map.hasLayer(o) || !o.getElement()) return;
    var e = o.getElement();
    if (S.mapMode !== 'swipe') { e.style.clip = ''; return; }
    var sz = map.getSize(), x = sz.x * S.swipe / 100;
    var nw = map.containerPointToLayerPoint([0, 0]), p = map.containerPointToLayerPoint([x, 0]), se = map.containerPointToLayerPoint(sz);
    var pos = L.DomUtil.getPosition(e) || L.point(0, 0);
    e.style.clip = 'rect(' + (nw.y - pos.y) + 'px,' + (p.x - pos.x) + 'px,' + (se.y - pos.y) + 'px,' + (nw.x - pos.x) + 'px)';
  }

  function computeVis() {
    var m = S.mapMode; if (m === 'custom') return;
    vis.img = {}; vis.outlines = true; vis.track = true;
    if (m === 'share') vis.img[AFTER] = 0.35;
    if (m === 'radar') vis.img[AFTER] = 0.9;
    if (m === 'swipe') { vis.img[AFTER] = 0.9; vis.img[BEFORE] = 0.9; }
    if (m === 'eye') vis.img[EYE] = 0.9;
  }

  function applyMap() {
    Object.keys(imgs).forEach(function (id) {
      var o = imgs[id], on = vis.img[id];
      if (on) { o.setOpacity(on === true ? 0.9 : on); if (!map.hasLayer(o)) o.addTo(map); } else if (map.hasLayer(o)) map.removeLayer(o);
    });
    toggleLayer(mandLayer, vis.outlines); toggleLayer(trackGrp, vis.track); toggleLayer(eyeGrp, vis.track);
    mandLayer.setStyle(mStyle);
    if (vis.outlines) mandLayer.bringToFront();
    $('#swipe').hidden = $('#swipe-line').hidden = S.mapMode !== 'swipe';
    updateSwipeLine(); clipBefore();
    // legend
    var lg = $('#legend');
    lg.innerHTML = S.mapMode === 'share'
      ? '<b class="legend__t">Probably flooded land</b><div class="ramp"></div><div class="ramp-l"><span>less</span><span>35+ in 100</span></div>' + tag(SAMPLE)
      : '';
    // caption
    var c = F.captions[S.mapMode] || F.captions.custom;
    $('#caption').innerHTML = '<div class="cap__row"><span class="cap__k">Shows</span><span>' + esc(c.shows) + '</span></div><div class="cap__row"><span class="cap__k">Cannot show</span><span>' + esc(c.cant) + '</span></div><div class="cap__row"><span class="cap__k">Source</span><span>' + esc(c.src) + '</span></div>' + (c.sample ? tag(c.sample) : '');
    var gone = Object.keys(vis.img).filter(function (id) { return vis.img[id] && missing[id]; });
    if (gone.length) $('#caption').insertAdjacentHTML('beforeend', '<div class="cap__miss" role="status"><b>Radar layer data not loaded yet.</b> The picture for this view is not available in this copy of the project. Outlines and numbers still work.</div>');
    $$('#map-modes button').forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.m === S.mapMode)); });
    $$('input[data-lyr]').forEach(function (cb) {
      var id = cb.dataset.lyr;
      if (missing[id]) { cb.disabled = true; cb.title = 'Layer data not loaded yet'; if (!cb.nextElementSibling) cb.insertAdjacentHTML('afterend', '<span class="sub">Not loaded yet</span>'); }
      cb.checked = id === 'mandal_boundaries' ? vis.outlines : id === 'imd_track_arnab' ? vis.track : !!vis.img[id];
    });
  }
  function toggleLayer(l, on) { if (on && !map.hasLayer(l)) l.addTo(map); if (!on && map.hasLayer(l)) map.removeLayer(l); }
  function updateSwipeLine() { $('#swipe-line').style.left = S.swipe + '%'; }

  function fitFor(m) {
    if (m === 'eye') map.fitBounds(SEA); else map.fitBounds(DELTA);
  }
  function setMapMode(m, fit) {
    S.mapMode = m; computeVis(); applyMap(); if (fit) fitFor(m);
  }

  /* ---------------- selection ---------------- */
  function selectMandal(name, o) {
    o = o || {};
    if (!X.byName[name]) return;
    S.sel = name;
    if (mandLayer) mandLayer.setStyle(mStyle);
    if (featByName[name]) { featByName[name].bringToFront(); if (o.fly) map.fitBounds(featByName[name].getBounds().pad(0.5), { maxZoom: 11 }); }
    $$('.rank__item').forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.m === name)); });
    $$('#mtbody tr').forEach(function (tr) { tr.setAttribute('aria-selected', String(tr.dataset.m === name)); });
    var c = $('#mcard'); if (c) c.innerHTML = mandalCard(X.byName[name]);
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
    var v = { name: niceName(r.mandal), lik: n0(r.lik), normal: n0(r.normal), err: n0(r.err), water: n0(r.water), crops: n0(r.crops) };
    var tw = timesWords(r.ratio);
    v.times = tw;
    var meaning = o.meaning || (tw === 'less' ? F.mandal.meaning_less : tw == null ? F.mandal.meaning_same : F.mandal.meaning);
    var cf = confOf(r);
    var head = o.headline || fill(F.mandal.headline, v);
    return '<div class="row row--between"><span class="eyebrow">Selected mandal · ' + esc(shortDist(r.district)) + '</span>' + tag(SAMPLE) + '</div>' +
      '<h3>' + esc(head) + '</h3>' +
      '<p class="lead">' + esc(fill(meaning, v)) + '</p>' +
      '<div class="waffles">' +
        waffle(r.water, r.crops, 0, 'after the cyclone', v.lik + ' in 100') +
        waffle(0, 0, r.normal, 'in a normal fortnight', v.normal + ' in 100') +
      '</div>' +
      '<div class="legendline"><span><i class="sw sw--w"></i>Probably open water</span><span><i class="sw sw--c"></i>Probably flooded crops</span><span><i class="sw sw--n"></i>Normal fortnight</span><span>Each square is 1 in 100</span></div>' +
      '<p class="small">' + esc(fill(F.mandal.split, v)) + '</p>' +
      '<p class="small">' + esc(fill(F.mandal.err, v)) + info(F.tips.err) + '</p>' +
      '<div class="note"><b>' + dots(cf.lvl) + esc(F.mandal['conf_' + cf.lvl]) + '.</b> ' + esc(cf.note) + '</div>' +
      '<div class="note"><b>What radar cannot tell you.</b> ' + esc(o.cannot || F.mandal.cannot) + '</div>' +
      '<div class="row"><button class="btn btn--sm" data-act="zoom">Show on the map</button>' +
      '<button class="btn btn--sm" data-act="swipe">Before and after here</button>' +
      '<button class="linkbtn small" data-act="raw">See the raw numbers</button></div>';
  }

  function rankItem(r) {
    var max = 40, w = Math.min(100, r.water / max * 100), c = Math.min(100 - w, r.crops / max * 100);
    var tick = Math.min(100, r.normal / max * 100), e0 = Math.max(0, (r.lik - r.err) / max * 100), e1 = Math.min(100, (r.lik + r.err) / max * 100);
    return '<li><button class="rank__item" data-m="' + esc(r.mandal) + '" aria-pressed="false">' +
      '<span class="rank__n">' + r.rank + '</span>' +
      '<span class="rank__top"><span>' + esc(niceName(r.mandal)) + '</span><span>' + n0(r.lik) + ' in 100 land</span></span>' +
      '<span class="bar" aria-hidden="true"><span class="bar__w" style="width:' + w + '%"></span><span class="bar__c" style="left:' + w + '%;width:' + c + '%"></span>' +
      '<span class="bar__tick" style="left:' + tick + '%"></span><span class="bar__err" style="left:' + e0 + '%;width:' + (e1 - e0) + '%"></span></span></button></li>';
  }
  function renderRank() {
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

  function buildHappened() {
    var top = X.rows[0], v0 = { name: top.mandal }, tw = timesWords(top.ratio);
    var cy = F.cyclone, ev = X.event;
    var big = Math.round(top.ratio);
    var html =
      '<div class="card">' +
        '<div class="row row--between"><span class="eyebrow">What happened</span>' + tag(SAMPLE) + '</div>' +
        '<h2>' + esc(F.intro.title) + '</h2>' +
        '<p class="lead">' + esc(F.intro.lead) + '</p>' +
        (ev.landfall && !ev.landfall.time_utc ? '<p class="small">' + esc(F.intro.landfall_unknown) + '</p>' : '') +
        '<div class="bignums">' +
          '<div class="bn"><span class="bn__v bn__v--water">' + n0(top.lik) + '%</span><span class="bn__l">of ' + esc(niceName(top.mandal)) + ' probably flooded, the most of any mandal</span></div>' +
          '<div class="bn"><span class="bn__v">' + big + '×</span><span class="bn__l">the usual share there in a normal fortnight</span></div>' +
          '<div class="bn"><span class="bn__v">' + X.profile.eye_radius_km + ' km</span><span class="bn__l">from the centre of the storm\'s calm eye to its edge</span></div>' +
        '</div>' +
        '<p class="small">' + esc(F.intro.how_to_read) + '</p>' +
      '</div>' +

      '<div class="card" id="ranking">' +
        '<div class="row row--between"><h2>' + esc(F.ranking.title) + '</h2>' + tag(SAMPLE) + '</div>' +
        '<p class="small">' + esc(F.ranking.sub) + ' ' + esc(F.ranking.reading_help) + '</p>' +
        '<ol class="rank" id="ranklist" style="list-style:none"></ol>' +
        '<div class="legendline"><span><i class="sw sw--w"></i>' + esc(F.ranking.legend_water) + '</span><span><i class="sw sw--c"></i>' + esc(F.ranking.legend_crops) + '</span><span><i class="sw sw--t"></i>' + esc(F.ranking.legend_normal) + '</span><span>Thin line: ' + esc(F.ranking.legend_err.toLowerCase()) + '</span></div>' +
        '<button class="linkbtn small" id="rankmore" style="align-self:flex-start"></button>' +
      '</div>' +

      '<div class="card" id="mcard"></div>' +

      '<div class="card" id="cyclone">' +
        '<div class="row row--between"><h2>' + esc(cy.title) + '</h2>' + tag(SAMPLE) + '</div>' +
        '<p class="lead">' + esc(cy.lead) + '</p>' +
        '<div class="row" style="align-items:flex-start">' + eyeDiagram() +
        '<div style="flex:1;min-width:180px;display:flex;flex-direction:column;gap:8px">' +
          '<p class="small"><b>' + esc(cy.category) + '.</b> ' + esc(cy.wind) + '</p>' +
          '<p class="small">' + esc(fill(cy.eye, { eye: X.profile.eye_radius_km, eye_err: X.profile.eye_radius_err })) + '</p>' +
          '<p class="small">' + esc(fill(cy.rough, { peak: X.peak.r_km })) + info(F.tips.db) + '</p>' +
        '</div></div>' +
        '<p class="small">' + esc(cy.where) + ' ' + esc(cy.track_note) + '</p>' +
        '<div class="note"><b>What radar cannot tell you.</b> ' + esc(cy.cannot) + '</div>' +
        '<div class="row"><button class="btn btn--sm" data-act="eye">Show the eye and path on the map</button></div>' +
      '</div>' +

      '<div class="card">' +
        '<h2>' + esc(F.confidence.title) + '</h2>' +
        '<ul class="small" style="margin:0;padding-left:18px;display:flex;flex-direction:column;gap:6px">' + F.confidence.items.map(function (t) { return '<li>' + esc(t) + '</li>'; }).join('') + '</ul>' +
        '<div class="row row--between" style="margin-top:8px"><h3>' + esc(F.cannot_tell.title) + '</h3>' + tag(F.cannot_tell.draft_tag) + '</div>' +
        F.cannot_tell.items.map(function (i) {
          var lab = { yes: 'Radar can', partly: 'Only partly', no: 'Radar cannot' }[i.verdict];
          return '<div class="verd"><span class="chip chip--' + i.verdict + ' verd__chip">' + lab + '</span><b>' + esc(i.claim) + '</b><span>' + esc(i.why) + '</span></div>';
        }).join('') +
      '</div>' +

      '<div class="linkcard"><h2>' + esc(F.link_to_data.title) + '</h2><p>' + esc(F.link_to_data.text) + '</p><button class="btn" data-act="todata">' + esc(F.link_to_data.button) + ' →</button></div>';
    $('#sec-happened').innerHTML = html; $('#sec-happened').removeAttribute('aria-busy');
    renderRank();
  }

  /* ---------------- "Data" ---------------- */
  function layerRows() {
    var src = {}; X.manifest.sources.forEach(function (s) { src[s.id] = s; });
    return X.manifest.layers.map(function (l) {
      var s = src[l.source_id] || {}, drawable = !!imgs[l.id] || l.id === 'mandal_boundaries' || l.id === 'imd_track_arnab';
      var st = l.status === 'ready' ? 'ready' : l.status === 'unavailable' ? 'not available yet' : 'link only';
      return '<tr title="' + esc(l.id) + '"><td><b>' + esc(l.name) + '</b>' + (l.chip === 'nisar' || l.type === 'nisar' ? ' <span class="chip chip--nisar">NISAR L-band</span>' : '') +
        (l.placeholder && l.placeholder.is ? '<span class="sub">' + tag(l.placeholder.tag) + '</span>' : '') + '</td>' +
        '<td class="num">' + esc(l.date ? dshort(l.date) : (l.access === 'live' ? 'Live' : '—')) + '</td>' +
        '<td>' + esc(l.source || '') + '<span class="sub">' + esc(l.credit || '') + '</span></td>' +
        '<td>' + esc(s.licence || 'not stated') + '</td>' +
        '<td><span class="chip chip--st-' + (l.status === 'ready' ? 'ready' : 'other') + '">' + esc(st.charAt(0).toUpperCase() + st.slice(1)) + '</span>' + (l.limit ? '<span class="sub">' + esc(l.limit) + '</span>' : '') + '</td>' +
        '<td>' + (drawable ? '<input type="checkbox" data-lyr="' + esc(l.id) + '" aria-label="Show ' + esc(l.name) + ' on the map">' : '<span class="sub">Not drawn</span>') + '</td></tr>';
    }).join('');
  }

  function pm(v) { return '<span class="pm">\u00B1' + n1(v) + '</span>'; }
  function mandalTable() {
    var q = S.q.toLowerCase(), k = S.sort.k, d = S.sort.d;
    var rows = X.rows.filter(function (r) { return !q || (r.mandal + ' ' + r.district).toLowerCase().indexOf(q) >= 0; });
    rows.sort(function (a, b) { var x = a[k], y = b[k]; return (typeof x === 'string' ? x.localeCompare(y) : x - y) * d; });
    $('#mtbody').innerHTML = rows.map(function (r) {
      return '<tr class="clickable" tabindex="0" data-m="' + esc(r.mandal) + '" aria-selected="' + (r.mandal === S.sel) + '"><td class="num">' + r.rank + '</td><td>' + esc(r.mandal) + '</td><td title="' + esc(r.district) + '">' + esc(shortDist(r.district)) + '</td>' +
        '<td class="num">' + n1(r.water) + pm(r.we) + '</td><td class="num">' + n1(r.crops) + pm(r.ce) + '</td>' +
        '<td class="num"><b>' + n1(r.lik) + '</b>' + pm(r.err) + '</td><td class="num">' + n1(r.normal) + '</td></tr>';
    }).join('') || '<tr class="empty"><td colspan="7">No mandal matches "' + esc(S.q) + '". Clear the filter to see all ' + X.rows.length + '.</td></tr>';
    $$('#d-mandals th[data-col]').forEach(function (th) { th.setAttribute('aria-sort', th.dataset.col === S.sort.k ? (S.sort.d > 0 ? 'ascending' : 'descending') : 'none'); });
    $('#mtcount').textContent = rows.length + ' of ' + X.rows.length + ' mandals';
  }

  function profileChart() {
    var P = X.profile.points, W = 420, H = 190, L = 44, R = 10, T = 10, B = 30, xm = 150, ymin = -2, ymax = 8;
    function x(r) { return L + r / xm * (W - L - R); } function y(v) { return T + (ymax - v) / (ymax - ymin) * (H - T - B); }
    var up = P.map(function (p) { return x(p.r_km) + ',' + y(p.db + p.err); }), lo = P.slice().reverse().map(function (p) { return x(p.r_km) + ',' + y(p.db - p.err); });
    var line = P.map(function (p) { return x(p.r_km) + ',' + y(p.db); }).join(' ');
    var s = '<svg class="chart" id="pchart" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="Radar brightness of the sea against distance from the eye centre, with a band for the uncertainty">';
    [0, 2, 4, 6, 8].forEach(function (v) { s += '<line x1="' + L + '" x2="' + (W - R) + '" y1="' + y(v) + '" y2="' + y(v) + '" stroke="' + css('--line') + '"/><text x="' + (L - 6) + '" y="' + (y(v) + 3) + '" text-anchor="end">' + v + '</text>'; });
    [0, 25, 50, 75, 100, 125, 150].forEach(function (v) { s += '<text x="' + x(v) + '" y="' + (H - 14) + '" text-anchor="middle">' + v + '</text>'; });
    s += '<text x="' + (L + (W - L - R) / 2) + '" y="' + (H - 2) + '" text-anchor="middle">distance from eye centre (km)</text>';
    s += '<text x="10" y="' + (T + 60) + '" transform="rotate(-90 10 ' + (T + 60) + ')" text-anchor="middle">brightness (dB)</text>';
    s += '<polygon points="' + up.concat(lo).join(' ') + '" fill="' + css('--teal-tint') + '"/>';
    s += '<polyline points="' + line + '" fill="none" stroke="' + css('--teal') + '" stroke-width="2"/>';
    var er = X.profile.eye_radius_km;
    s += '<line x1="' + x(er) + '" x2="' + x(er) + '" y1="' + T + '" y2="' + (H - B) + '" stroke="' + css('--ink-2') + '" stroke-dasharray="3 3"/><text x="' + (x(er) + 3) + '" y="' + (T + 9) + '">eye edge ' + er + ' ±' + X.profile.eye_radius_err + ' km</text>';
    s += '<circle cx="' + x(X.peak.r_km) + '" cy="' + y(X.peak.db) + '" r="4" fill="' + css('--teal') + '"/><text x="' + (x(X.peak.r_km) + 6) + '" y="' + (y(X.peak.db) - 6) + '">peak ' + X.peak.db + ' dB at ' + X.peak.r_km + ' km</text>';
    s += '<line id="pcur" x1="0" x2="0" y1="' + T + '" y2="' + (H - B) + '" stroke="' + css('--ink') + '" visibility="hidden"/><text id="pcurt" x="0" y="' + (H - B - 4) + '" visibility="hidden"></text>';
    s += '<rect id="phit" x="' + L + '" y="' + T + '" width="' + (W - L - R) + '" height="' + (H - T - B) + '" fill="transparent"/></svg>';
    return s;
  }
  function bindProfile() {
    var svg = $('#pchart'), P = X.profile.points, vb = svg.viewBox.baseVal, L = 44, R = 10, xm = 150;
    function r(ev) { var b = svg.getBoundingClientRect(); var px = (ev.clientX - b.left) / b.width * vb.width; return Math.max(0, Math.min(xm, (px - L) / (vb.width - L - R) * xm)); }
    $('#phit').addEventListener('mousemove', function (ev) {
      var rk = r(ev), p = P.reduce(function (a, b) { return Math.abs(b.r_km - rk) < Math.abs(a.r_km - rk) ? b : a; });
      var px = L + p.r_km / xm * (vb.width - L - R), c = $('#pcur'), t = $('#pcurt');
      c.setAttribute('x1', px); c.setAttribute('x2', px); c.setAttribute('visibility', 'visible');
      t.setAttribute('x', px + 4); t.setAttribute('visibility', 'visible'); t.textContent = p.r_km + ' km: ' + p.db + ' ±' + p.err + ' dB';
      if (hoverRing) map.removeLayer(hoverRing);
      hoverRing = L.circle(X.profile.eye, { radius: p.r_km * 1000, color: css('--white'), weight: 1.5, dashArray: '2 4', fill: false, interactive: false }).addTo(map);
    });
    $('#phit').addEventListener('mouseleave', function () { $('#pcur').setAttribute('visibility', 'hidden'); $('#pcurt').setAttribute('visibility', 'hidden'); if (hoverRing) { map.removeLayer(hoverRing); hoverRing = null; } });
  }

  function sceneBlock() {
    var sc = X.manifest.layers.filter(function (l) { return l.type === 'nisar' && l.png; }).sort(function (a, b) { return a.date < b.date ? -1 : 1; });
    var val = sc.filter(function (l) { return l.processing_level === 'validated'; }).length;
    var tr = {}; sc.forEach(function (l) { tr['T' + l.track] = 1; });
    var inf = sc.filter(function (l) { return l.bounds_inferred; }).length;
    return '<div class="kv"><div><b>' + sc.length + '</b><span>NISAR L-band scenes</span></div><div><b>' + val + ' / ' + (sc.length - val) + '</b><span>validated / provisional</span></div><div><b>' + Object.keys(tr).join(', ') + '</b><span>tracks (T48 sea, T55 coast)</span></div><div><b>' + inf + '</b><span>with inferred footprint</span></div></div>' +
      '<div class="tblwrap"><table class="dt"><thead><tr><th scope="col">Date</th><th scope="col">Track and frame</th><th scope="col">Polarisation</th><th scope="col">Processing</th><th scope="col">Footprint</th></tr></thead><tbody>' +
      sc.map(function (l) { return '<tr><td class="num">' + dshort(l.date) + '</td><td class="num">T' + l.track + ' \u00B7 F' + l.frame + ' \u00B7 ' + esc(l.direction) + '</td><td class="num">' + esc(String(l.pol).toUpperCase()) + '</td><td><span class="chip ' + (l.processing_level === 'validated' ? 'chip--yes' : 'chip--partly') + '">' + esc(String(l.processing_level).charAt(0).toUpperCase() + String(l.processing_level).slice(1)) + '</span></td><td>' + (l.bounds_inferred ? 'Inferred' : 'From KML') + ' ' + tag(QUICK) + '</td></tr>'; }).join('') + '</tbody></table></div>';
  }

  function alertsBlock() {
    var a = X.alerts;
    return '<div class="row row--between"><span class="small">Saved <b>' + ist(a.saved_at_ist) + '</b> (a snapshot, not live)</span>' + (a.placeholder && a.placeholder.is ? tag(a.placeholder.tag) : '') + '</div>' +
      a.sachet.map(function (x) { return '<div class="alert"><b>' + esc(x.headline) + '</b><div class="alert__m">' + esc(x.area) + ' · issued ' + ist(x.issued) + '</div></div>'; }).join('') +
      '<p class="small">GDACS entries in the snapshot: ' + (a.gdacs.length || 'none') + '. Source: NDMA SACHET (licence to confirm).</p>';
  }

  var DL = [
    ['manifest.json', 'Catalogue of layers, sources and events'], ['mandals.geojson', 'Mandal outlines (geoBoundaries, ODbL-1.0 licence)'],
    ['mandal_rank.json', 'Flooded share for each mandal, with uncertainty (sample)'], ['profile.json', 'Eye profile: sea brightness by distance (sample)'],
    ['alerts.json', 'Alerts snapshot (sample)'], ['imd_track_arnab.geojson', 'Cyclone path and position fixes from IMD']
  ];
  var DLI = '<svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path d="M8 2v8m0 0L5 7m3 3l3-3M3 13h10" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  function dlBlock() {
    var imgsL = X.manifest.layers.filter(function (l) { return l.type === 'nisar' && l.png; });
    return '<ul class="dl">' + DL.map(function (d) { return '<li><span class="dl__main"><b>' + esc(d[1]) + '</b><a class="dl__file" href="' + D + d[0] + '" download>' + DLI + d[0] + '</a></span><span class="dl__size" data-size="' + d[0] + '"></span></li>'; }).join('') +
      '<li><span class="dl__main"><b>Mandal table as a spreadsheet</b><a class="dl__file" href="#" id="csvdl">' + DLI + 'mandal_rank.csv</a><span class="small muted">Made in your browser from the same table ' + tag(SAMPLE) + '</span></span><span class="dl__size"></span></li>' +
      imgsL.map(function (l) { var f = l.png.replace('data/processed/', ''); return '<li><span class="dl__main"><b>Radar quick-look, ' + esc(dshort(l.date)) + '</b><a class="dl__file" href="../../' + l.png + '" download>' + DLI + esc(f.split('/').pop()) + '</a><span class="small muted">For display only ' + tag(QUICK) + '</span></span><span class="dl__size" data-size="' + esc(f) + '"></span></li>'; }).join('') + '</ul>';
  }

  function buildData() {
    var rank = X.rank;
    $('#sec-data').innerHTML =
      '<nav class="chips" aria-label="Jump to a part of this section"><a href="#d-layers">Layers</a><a href="#d-mandals">Mandals</a><a href="#d-profile">Eye profile</a><a href="#d-scenes">Scenes</a><a href="#d-alerts">Alerts</a><a href="#d-files">Downloads</a>' +
      '<a href="#" data-act="tohappened" class="chips__back">Plain-language view</a></nav>' +
      '<div class="card" id="d-layers"><div class="row row--between"><div><h2>Layers</h2><p class="small">Every map layer with its source, licence and known limits.</p></div><span class="small muted">Tick a box to draw a layer on the map</span></div><div class="tblwrap tblwrap--tall"><table class="dt"><thead><tr><th scope="col">Layer</th><th scope="col">Date</th><th scope="col">Source and credit</th><th scope="col">Licence</th><th scope="col">Status and limits</th><th scope="col">On map</th></tr></thead><tbody>' + layerRows() + '</tbody></table></div></div>' +
      '<div class="card" id="d-mandals"><div class="row row--between"><div><h2>Mandal table</h2></div>' + (rank.placeholder && rank.placeholder.is ? tag(rank.placeholder.tag) : '') + '</div>' +
        '<p class="small">Share of each mandal\'s area, in % (± is the uncertainty in percentage points). Period ' + dshort(rank.period[0]) + ' to ' + dshort(rank.period[1]) + '; normal period ' + dshort(rank.normal_period[0]) + ' to ' + dshort(rank.normal_period[1]) + '. Total = water + crops, ± combined in quadrature (calculated here).</p>' +
        '<div class="tools"><input type="search" id="mtq" placeholder="Filter mandal or district" aria-label="Filter mandals"><span class="small muted" id="mtcount"></span></div>' +
        '<div class="tblwrap"><table class="dt"><thead><tr>' +
          [['rank', 'Rank', '', 1], ['mandal', 'Mandal', ''], ['district', 'District', ''], ['water', 'Likely open water', '% of area \u00B1 pts', 1], ['crops', 'Likely wet crops', '% of area \u00B1 pts', 1], ['lik', 'Total likely flooded', '% of area \u00B1 pts', 1], ['normal', 'Normal fortnight', '% of area', 1]].map(function (c) { return '<th scope="col" data-col="' + c[0] + '" aria-sort="none" class="' + (c[3] ? 'num' : '') + '"><button data-sort="' + c[0] + '" title="Sort by ' + c[1].toLowerCase() + '">' + c[1] + '<span class="th-u">' + c[2] + '</span></button></th>'; }).join('') +
        '</tr></thead><tbody id="mtbody"></tbody></table></div></div>' +
      '<div class="card" id="d-profile"><div class="row row--between"><h2>Eye profile</h2>' + (X.profile.placeholder && X.profile.placeholder.is ? tag(X.profile.placeholder.tag) : '') + '</div>' +
        '<p class="small">Mean radar brightness of the sea (VV, dB) by distance from the eye centre, 27 Oct 2026. Eye centre ' + X.profile.eye[0] + ' N, ' + X.profile.eye[1] + ' E; IMD fix is ' + X.profile.imd_offset_km + ' km away. Hover the chart to draw that distance on the map.</p>' + profileChart() + '</div>' +
      '<div class="card" id="d-scenes"><div><h2>Scene catalogue</h2><p class="small">NISAR radar scenes used for the quick-looks on the map.</p></div>' + sceneBlock() + '</div>' +
      '<div class="card" id="d-alerts"><div><h2>Alerts snapshot</h2></div>' + alertsBlock() + '</div>' +
      '<div class="card" id="d-files"><div><h2>Downloads</h2><p class="small">Files as stored in the repository. Credits and licences are in the layer list above.</p></div>' + dlBlock() + '</div>';
    mandalTable(); bindProfile();
    // sizes (best effort)
    $$('[data-size]').forEach(function (e) {
      fetch(D + e.dataset.size, { method: 'HEAD' }).then(function (r) { var n = +r.headers.get('content-length'); if (n) e.textContent = n > 1e6 ? (n / 1e6).toFixed(1) + ' MB' : Math.round(n / 1e3) + ' KB'; }).catch(function () {});
    });
  }

  /* ---------------- UI wiring ---------------- */
  function setSection(s) {
    S.section = s;
    $('#main').dataset.section = s;
    $('#sec-happened').hidden = s !== 'happened'; $('#sec-data').hidden = s !== 'data';
    $('#tab-happened').setAttribute('aria-selected', String(s === 'happened')); $('#tab-happened').tabIndex = s === 'happened' ? 0 : -1;
    $('#tab-data').setAttribute('aria-selected', String(s === 'data')); $('#tab-data').tabIndex = s === 'data' ? 0 : -1;
    $('#map-modes').hidden = s !== 'happened';
    $('#panel').scrollTop = 0;
    history.replaceState(null, '', '#' + s);
    if (s === 'happened') setMapMode(S.mapMode === 'custom' ? 'share' : S.mapMode, true);
    else { setMapMode('custom'); vis.img = {}; vis.img[AFTER] = 0.9; vis.outlines = true; vis.track = true; applyMap(); map.fitBounds(DELTA); }
    setTimeout(function () { map.invalidateSize(); }, 280);
  }

  function bindUI() {
    var seg = $('#map-modes');
    seg.innerHTML = MODES.map(function (m) { return '<button type="button" data-m="' + m[0] + '" aria-pressed="false">' + m[1] + '</button>'; }).join('');
    seg.addEventListener('click', function (e) { var b = e.target.closest('button'); if (b) setMapMode(b.dataset.m, true); });

    $('#tab-happened').addEventListener('click', function () { setSection('happened'); });
    $('#tab-data').addEventListener('click', function () { setSection('data'); });
    $('.tabs').addEventListener('keydown', function (e) {
      if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') { var s = S.section === 'happened' ? 'data' : 'happened'; setSection(s); $('#tab-' + s).focus(); }
    });

    $('#panel-toggle').addEventListener('click', function () {
      var c = $('#main').classList.toggle('collapsed');
      this.setAttribute('aria-expanded', String(!c));
      this.classList.toggle('is-collapsed', c); $('#panel-toggle-txt').textContent = c ? 'Show panel' : 'Hide panel';
      setTimeout(function () { map.invalidateSize(); }, 280);
    });

    $('#swipe-range').addEventListener('input', function () { S.swipe = +this.value; updateSwipeLine(); clipBefore(); });

    $('#panel').addEventListener('click', function (e) {
      var t = e.target;
      var rb = t.closest('.rank__item'); if (rb) { selectMandal(rb.dataset.m, { fly: true }); return; }
      var tr = t.closest('#mtbody tr'); if (tr) { selectMandal(tr.dataset.m, { fly: true }); return; }
      var so = t.closest('[data-sort]'); if (so) { var k = so.dataset.sort; S.sort = { k: k, d: S.sort.k === k ? -S.sort.d : 1 }; mandalTable(); return; }
      if (t.id === 'rankmore') { S.showAll = !S.showAll; renderRank(); return; }
      if (t.id === 'csvdl') { e.preventDefault(); csv(); return; }
      var a = t.closest('[data-act]'); if (!a) return;
      e.preventDefault();
      var act = a.dataset.act;
      if (act === 'zoom') { setMapMode('share', false); selectMandal(S.sel, { fly: true }); }
      if (act === 'swipe') { setMapMode('swipe', false); selectMandal(S.sel, { fly: true }); }
      if (act === 'eye') setMapMode('eye', true);
      if (act === 'todata') { setSection('data'); selectMandal(S.sel, {}); }
      if (act === 'tohappened') setSection('happened');
      if (act === 'raw') { setSection('data'); selectMandal(S.sel, {}); var tr2 = $('#mtbody tr[data-m="' + S.sel.replace(/"/g, '\\"') + '"]'); if (tr2) setTimeout(function () { tr2.scrollIntoView({ block: 'center' }); $('#d-mandals').scrollIntoView(); tr2.scrollIntoView({ block: 'nearest' }); }, 50); }
    });
    $('#panel').addEventListener('keydown', function (e) {
      var tr = e.target.closest && e.target.closest('#mtbody tr.clickable');
      if (tr && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); selectMandal(tr.dataset.m, { fly: true }); }
    });
    $('#panel').addEventListener('change', function (e) {
      var cb = e.target.closest('input[data-lyr]'); if (!cb) return;
      var id = cb.dataset.lyr;
      if (S.mapMode !== 'custom') { S.mapMode = 'custom'; }
      if (id === 'mandal_boundaries') vis.outlines = cb.checked; else if (id === 'imd_track_arnab') vis.track = cb.checked;
      else { if (cb.checked) vis.img[id] = 0.9; else delete vis.img[id]; }
      applyMap();
    });
    $('#panel').addEventListener('input', function (e) { if (e.target.id === 'mtq') { S.q = e.target.value; mandalTable(); } });
  }

  function csv() {
    var h = 'rank,mandal,district,water_pct,water_err,crops_pct,crops_err,normal_pct\n';
    var b = X.rows.map(function (r) { return [r.rank, '"' + r.mandal + '"', '"' + r.district + '"', r.water, r.we, r.crops, r.ce, r.normal].join(','); }).join('\n');
    var a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([h + b], { type: 'text/csv' })); a.download = 'mandal_rank_SAMPLE.csv'; a.click();
  }
})();
