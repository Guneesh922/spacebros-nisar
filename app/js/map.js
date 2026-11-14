/* map.js: Leaflet map, overlay manager, opacity, caption card, scale. Defines window.App.map.
   Classic script. Needs core.js (window.App) and Leaflet 1.9.x (global L) loaded first.
   B1's index.html calls App.map.init(document.getElementById('map')) after App.load().

   Public API:
     App.map.init(el)                 build map + controls inside el, start listening to App events
     App.map.invalidate()             invalidateSize (+ pending region fit)
     App.map.flyTo(bounds)            animated fit of [[S,W],[N,E]]
     App.map.getMap()                 the L.Map (or null before init)
     App.map.activeLayerId            layer id (resolved, after date substitution) shown in the caption, or null
     App.map.getActiveLayer()         that layer object or null
     App.map.getDisplayedLayerIds()   ids of the layers currently drawn (resolved ids, failed ones excluded)
     App.map.setOpacity(id, v)        App.setState({opacity:{[id]:v}}); id is the layersOn id
     App.map.exportCurrentView()      {bounds, center, zoom, imgUrls:[{id,url,bounds,opacity}]}
   Emits: App.emit('caption', layer|null) when the active (caption) layer changes. */
(function () {
  'use strict';

  var App = window.App;
  if (!App) { console.error('[map] core.js must load first'); return; }

  App.addStrings('en', {
    'map.tf': 'T{track} · F{frame}',
    'map.inferred': 'Position inferred from a later pass of the same track and frame; it may be offset slightly.',
    'map.credit_tbc': '[credit line to confirm]',
    'map.none_stated': 'Not stated',
    'map.attr_text': 'Tiles © Esri — Esri, HERE, Garmin, © OpenStreetMap contributors',
    'map.caption_label': 'About the layer shown',
    'map.map_label': 'Map. Use the plus and minus buttons to zoom.',
    'map.details': 'Details',
    'map.details_aria': 'Show or hide the full layer description'
  });

  var T = function (k, v) { return App.t(k, v); };
  var DEFAULT_OPACITY = 0.85;
  var BASEMAP = 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}';

  var map = null, root = null;
  var slots = {};              // slotId (id in layersOn) -> {slot, layer, kind, overlay, failed, token}
  var geoCache = {};           // url -> {ok, data}
  var geoPending = {};         // url -> [callbacks]
  var recent = [];             // slot ids, most recently switched on last
  var prevShown = null;        // Set of slot ids displayed on the last sync (null = first sync)
  var activeSlot = null;
  var captionKey = null;
  var capOpen = false;          // compact (compare) caption: details expanded?
  var lastEmittedId;           // undefined = nothing emitted yet
  var pendingFit = false;
  var syncWanted = false;      // sync() ran before the first view; run it once the view exists
  var refs = {};               // DOM refs: zoomIn, zoomOut, caption
  var mq = null;
  var panesMade = false;

  /* ---------------- helpers ---------------- */
  function css(name, fallback) {
    try {
      var v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
      return v || fallback || '';
    } catch (e) { return fallback || ''; }
  }
  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }
  function reduced() {
    try { return window.matchMedia('(prefers-reduced-motion: reduce)').matches; } catch (e) { return false; }
  }
  function isoDay(s) { return String(s || '').slice(0, 10); }
  function isDay(s) { return /^\d{4}-\d{2}-\d{2}/.test(String(s || '')); }

  function regionBounds() {
    var r = App.regionById(App.state.region);
    return (r && r.bounds) || null;
  }
  function regionDistricts() {
    var r = App.regionById(App.state.region);
    return (r && r.districts && r.districts.length) ? r.districts : null;
  }

  /* ---------------- which layers are displayed ---------------- */
  function opacityFor(slotId, layer) {
    var o = App.state.opacity && App.state.opacity[slotId];
    if (o == null) o = layer && layer.opacity;
    if (o == null || isNaN(o)) o = DEFAULT_OPACITY;
    return Math.max(0, Math.min(1, +o));
  }

  function pickFromSeries(cands, date) {
    cands = cands.slice().sort(function (a, b) { return String(a.date || '').localeCompare(String(b.date || '')); });
    if (!cands.length) return null;
    if (!date) return cands[cands.length - 1];
    var d = isoDay(date), before = null, after = null;
    cands.forEach(function (c) {
      var cd = isoDay(c.date);
      if (cd <= d) before = c;
      else if (!after) after = c;
    });
    return before || after;
  }

  /* Returns ordered [{slot, layer}] for layers that should be on the map now. */
  function desired() {
    var offered = App.layersFor({ region: App.state.region, eventId: App.state.eventId });
    var byId = {};
    offered.forEach(function (l) { byId[l.id] = l; });
    var out = [], seen = {};
    // keep manifest (layersFor) order: NISAR first, then derived, reference
    offered.forEach(function (l) {
      if (!App.state.layersOn.has(l.id)) return;
      var layer = l;
      if (l.latest_of) {
        var cands = offered.filter(function (c) { return c.latest_of === l.latest_of && c.status === 'ready'; });
        // only the newest row of a series follows the header date picker; older dated rows draw their own
        // scene (otherwise ticking "28 Oct" in the drawer would show the latest scene instead)
        var newest = pickFromSeries(cands, null);
        layer = (l.status === 'ready' && newest && l.id !== newest.id) ? l : pickFromSeries(cands, App.state.date);
      } else if (l.status !== 'ready') {
        layer = null;
      }
      if (!layer) return;
      // two slots of one series would resolve to the same layer: draw it once
      if (seen[layer.id]) return;
      seen[layer.id] = 1;
      out.push({ slot: l.id, layer: layer });
    });
    return out;
  }

  /* ---------------- panes ---------------- */
  function makePanes() {
    if (panesMade) return;
    [['nisarPane', 410], ['derivedPane', 420], ['refPane', 430]].forEach(function (p) {
      var pane = map.createPane(p[0]);
      pane.style.zIndex = p[1];
    });
    panesMade = true;
  }
  function paneFor(layer) {
    if (layer.kind === 'geojson') return 'refPane';
    if (layer.type === 'derived') return 'derivedPane';
    if (layer.type === 'reference') return 'refPane';
    return 'nisarPane';
  }

  /* ---------------- drawing ---------------- */
  function remember(url) {
    try { window.localStorage.setItem('app.lastok:' + url, new Date().toISOString()); } catch (e) { /* ignore */ }
  }

  function removeSlot(id) {
    var s = slots[id];
    if (!s) return;
    s.token = null;
    if (s.overlay && map) { try { map.removeLayer(s.overlay); } catch (e) { /* ignore */ } }
    delete slots[id];
  }

  function addImage(s) {
    var layer = s.layer;
    var url = App.assetUrl(layer.png);
    if (!url || !layer.bounds) { s.failed = true; return; }
    s.url = url;
    var ov = L.imageOverlay(url, layer.bounds, {
      opacity: opacityFor(s.slot, layer), interactive: false, className: 'radar-img',
      pane: paneFor(layer), alt: ''
    });
    ov.on('load', function () { remember(url); if (s.failed) { s.failed = false; renderCaption(true); } });
    ov.on('error', function () {
      if (slots[s.slot] !== s) return;
      s.failed = true;
      renderCaption(true);
    });
    ov.addTo(map);
    s.overlay = ov;
  }

  function loadGeo(url, cb) {
    if (geoCache[url]) { cb(geoCache[url]); return; }
    if (geoPending[url]) { geoPending[url].push(cb); return; }
    geoPending[url] = [cb];
    App.fetchJSON(url, { fallbackLabel: 'layer' }).then(function (r) {
      geoCache[url] = { ok: r.ok && r.data && r.data.type, data: r.data };
      var list = geoPending[url] || [];
      delete geoPending[url];
      list.forEach(function (fn) { fn(geoCache[url]); });
    });
  }

  function geomKind(f) {
    var t = f && f.geometry && f.geometry.type;
    if (t === 'Polygon' || t === 'MultiPolygon') return 'poly';
    if (t === 'LineString' || t === 'MultiLineString') return 'line';
    return 'point';
  }

  function polyStyle(f) {
    var sel = App.state.mandal && f.properties && f.properties.name === App.state.mandal;
    return sel
      ? { color: css('--teal-onmap'), weight: 3.5, opacity: 1, fill: true, fillColor: css('--teal-onmap'), fillOpacity: 0.08, lineJoin: 'round' }
      : { color: css('--on-stage-muted'), weight: 1, opacity: 0.7, fill: true, fillColor: css('--stage'), fillOpacity: 0, lineJoin: 'round' };
  }

  function buildGeo(s, data) {
    var districts = regionDistricts();
    var haloLayers = [];
    var gj = L.geoJSON(data, {
      pane: 'refPane',
      filter: function (f) {
        if (geomKind(f) !== 'poly') return true;
        if (!districts) return true;
        var d = f.properties && f.properties.district;
        return !!d && districts.indexOf(d) >= 0;
      },
      style: function (f) {
        var k = geomKind(f);
        if (k === 'poly') return polyStyle(f);
        return { color: css('--white'), weight: 3, dashArray: '10 8', opacity: 1, interactive: false };
      },
      pointToLayer: function (f, ll) {
        return L.circleMarker(ll, {
          pane: 'refPane', radius: 6, color: css('--stage'), weight: 3, fillColor: css('--white'),
          fillOpacity: 1, interactive: false
        });
      },
      onEachFeature: function (f, lyr) {
        var k = geomKind(f);
        if (k === 'poly') {
          var name = f.properties && f.properties.name;
          if (name) lyr.bindTooltip(name, { sticky: true, direction: 'top', className: 'map-tip' });
          lyr.on('mouseover', function () {
            if (App.state.mandal === name) return;
            lyr.setStyle({ color: css('--white'), weight: 2, opacity: 1, fillColor: css('--teal-onmap'), fillOpacity: 0.12 });
            lyr.bringToFront();
          });
          lyr.on('mouseout', function () { lyr.setStyle(polyStyle(f)); });
          lyr.on('click', function (e) {
            if (e.originalEvent) L.DomEvent.stopPropagation(e);
            if (name) App.setState({ mandal: name });
          });
        } else if (k === 'line') {
          // dark halo under the dashed white line, as in the mockup
          var halo = L.geoJSON(f, { pane: 'refPane', interactive: false,
            style: function () { return { color: css('--stage'), weight: 6, opacity: 1, interactive: false }; } });
          haloLayers.push(halo);
        }
      }
    });
    var group = L.layerGroup(haloLayers.concat([gj]));
    group._gj = gj;
    group._halos = haloLayers;
    return group;
  }

  function addGeo(s) {
    var layer = s.layer;
    var file = layer.file || layer.geojson || layer.path || layer.url;
    if (!file) { s.failed = true; return; }
    var url = App.assetUrl(file);
    s.url = url;
    var token = {};
    s.token = token;
    loadGeo(url, function (res) {
      if (slots[s.slot] !== s || s.token !== token) return;
      if (!res.ok) { s.failed = true; renderCaption(true); return; }
      s.data = res.data;
      s.overlay = buildGeo(s, res.data);
      s.overlay.addTo(map);
      s.failed = false;
      // halo layers must be under the white line: add them first (layerGroup order), so bring points up
      restyleGeo();
    });
  }

  function restyleGeo() {
    Object.keys(slots).forEach(function (id) {
      var s = slots[id];
      if (s.kind === 'geojson' && s.overlay && s.overlay._gj) {
        s.overlay._gj.eachLayer(function (l) {
          if (l.feature && geomKind(l.feature) === 'poly' && l.setStyle) l.setStyle(polyStyle(l.feature));
        });
      }
    });
  }

  function rebuildGeo() {
    Object.keys(slots).forEach(function (id) {
      var s = slots[id];
      if (s.kind !== 'geojson' || !s.data) return;
      if (s.overlay) map.removeLayer(s.overlay);
      s.overlay = buildGeo(s, s.data);
      s.overlay.addTo(map);
    });
  }

  function addSlot(d) {
    var layer = d.layer;
    var s = { slot: d.slot, layer: layer, kind: layer.kind, overlay: null, failed: false, url: null, token: null };
    slots[d.slot] = s;
    if (layer.kind === 'image') addImage(s);
    else if (layer.kind === 'geojson') addGeo(s);
    else s.ignored = true;   // wmts / live / link / unknown: live.js draws them
  }

  /* ---------------- sync: diff, don't rebuild ---------------- */
  var lastGeoKey = null;

  function sync() {
    if (!map || !App.manifest) return;
    if (!hasView()) { syncWanted = true; ensureView(); return; }   // no overlays before the first view
    var want = desired();
    var wantBySlot = {};
    want.forEach(function (d) { wantBySlot[d.slot] = d; });

    // region/event change affects geojson filtering
    var geoKey = App.state.region + '|' + App.state.eventId;
    var regionChanged = geoKey !== lastGeoKey;
    lastGeoKey = geoKey;

    Object.keys(slots).forEach(function (id) {
      var d = wantBySlot[id];
      if (!d || d.layer.id !== slots[id].layer.id) removeSlot(id);
    });
    want.forEach(function (d) {
      if (!slots[d.slot]) addSlot(d);
    });
    if (regionChanged) rebuildGeo();

    // opacity
    Object.keys(slots).forEach(function (id) {
      var s = slots[id];
      if (s.kind === 'image' && s.overlay) s.overlay.setOpacity(opacityFor(id, s.layer));
    });

    // active layer tracking (order of additions)
    var displayed = want.filter(function (d) { return !d.ignoredNonDrawn; }).map(function (d) { return d.slot; });
    var shownSet = {};
    displayed.forEach(function (id) { shownSet[id] = 1; });
    var added = prevShown ? displayed.filter(function (id) { return !prevShown[id]; }) : displayed.slice();
    if (!prevShown || added.length > 1) {
      recent = displayed.slice().reverse();         // reload: first displayed is active
    } else {
      recent = recent.filter(function (id) { return shownSet[id]; });
      added.forEach(function (id) { recent.push(id); });
    }
    prevShown = shownSet;
    activeSlot = recent.length ? recent[recent.length - 1] : null;

    renderCaption(false);
  }

  /* ---------------- caption card ---------------- */
  function activeLayer() {
    var s = activeSlot && slots[activeSlot];
    return s ? s.layer : null;
  }

  function row(label, cls) {
    var r = el('div', 'mapcap__row' + (cls ? ' ' + cls : ''));
    r.appendChild(el('span', 'mapcap__label', label));
    var body = el('div', 'mapcap__body');
    r.appendChild(body);
    return { row: r, body: body };
  }

  function creditFor(layer) {
    var c = layer.credit;
    if (!c && layer.source_id) {
      var src = (App.manifest.sources || []).filter(function (x) { return x.id === layer.source_id; })[0];
      if (src) c = src.credit_line || null;
    }
    return c || T('map.credit_tbc');
  }

  function monoLine(layer) {
    var bits = [];
    if (layer.track != null && layer.frame != null) bits.push(T('map.tf', { track: layer.track, frame: layer.frame }));
    var when = '';
    if (layer.time_utc) when = App.fmt.dateTime(layer.time_utc, 'UTC');
    else if (isDay(layer.date)) when = App.fmt.date(layer.date);
    if (when) bits.push(when);
    return bits.join(' · ');
  }

  function isNisar(layer) { return layer.chip === 'nisar' || layer.type === 'nisar'; }

  function compact() { return !!(App.state.compare && App.state.compare.on); }

  function renderCaption(force) {
    if (!refs.caption) return;
    var layer = activeLayer();
    var s = activeSlot && slots[activeSlot];
    var key = layer ? [layer.id, s && s.failed ? 1 : 0, App.state.lang, compact() ? 1 : 0, capOpen ? 1 : 0].join('|') : 'none|' + App.state.lang;
    if (force || key !== captionKey) {
      captionKey = key;
      buildCaption(layer, s);
    } else {
      syncSlider();
    }
    var id = layer ? layer.id : null;
    App.map.activeLayerId = id;
    if (id !== lastEmittedId) {
      lastEmittedId = id;
      App.emit('caption', layer);
    }
  }

  function buildCaption(layer, s) {
    var card = refs.caption;
    card.textContent = '';
    card.setAttribute('aria-label', T('map.caption_label'));
    if (!layer) {
      card.classList.add('mapcap--empty');
      card.classList.remove('is-compact', 'is-open');
      card.appendChild(el('p', 'mapcap__none', T('caption.none')));
      return;
    }
    card.classList.remove('mapcap--empty');
    card.classList.toggle('is-compact', compact());
    card.classList.toggle('is-open', compact() && capOpen);

    // compact line (shown only while comparing): Shows chip + date + details toggle
    var line = el('div', 'mapcap__line');
    var lchip = layer.chip === 'nisar' ? 'chip.nisar' : (App.hasString('chip.' + layer.chip) ? 'chip.' + layer.chip : 'chip.context');
    line.appendChild(el('span', 'chip ' + (layer.chip === 'nisar' ? 'chip--nisar' : 'chip--context'), T(lchip)));
    var lwhen = isDay(layer.date) ? App.fmt.date(layer.date) : '';
    if (lwhen) line.appendChild(el('span', 'mono mapcap__mono', lwhen));
    if (layer.placeholder && layer.placeholder.is) line.appendChild(el('span', 'tag-sample', layer.placeholder.tag || T('state.placeholder')));
    var dbtn = el('button', 'mapcap__toggle', T('map.details'));
    dbtn.type = 'button';
    dbtn.setAttribute('aria-expanded', capOpen ? 'true' : 'false');
    dbtn.setAttribute('aria-label', T('map.details_aria'));
    dbtn.addEventListener('click', function () { capOpen = !capOpen; renderCaption(true); });
    line.appendChild(dbtn);
    card.appendChild(line);

    if (s && s.failed) {
      var last = s.url ? App.lastKnown(s.url) : null;
      var msg = last ? T('state.unavailable_with_last', { time: App.fmt.dateTime(last, 'IST') }) : T('state.unavailable');
      var st = el('p', 'mapcap__status', msg);
      st.setAttribute('role', 'status');
      card.appendChild(st);
    }

    // Shows
    var shows = row(T('caption.shows'));
    shows.body.appendChild(el('span', 'mapcap__text', layer.shows || layer.name || ''));
    var meta = el('span', 'mapcap__meta');
    var chipKey = layer.chip === 'nisar' ? 'chip.nisar' : (App.hasString('chip.' + layer.chip) ? 'chip.' + layer.chip : 'chip.context');
    meta.appendChild(el('span', 'chip ' + (layer.chip === 'nisar' ? 'chip--nisar' : 'chip--context'), T(chipKey)));
    var ml = monoLine(layer);
    if (ml) meta.appendChild(el('span', 'mono mapcap__mono', ml));
    if (isNisar(layer) && isDay(layer.date)) {
      var age = App.fmt.age(layer.date);
      if (age) meta.appendChild(el('span', 'mono mapcap__mono mapcap__age', age));
    }
    if (layer.placeholder && layer.placeholder.is) {
      meta.appendChild(el('span', 'tag-sample', layer.placeholder.tag || T('state.placeholder')));
    }
    shows.body.appendChild(meta);
    if (layer.bounds_inferred) shows.body.appendChild(el('span', 'mapcap__note', T('map.inferred')));
    card.appendChild(shows.row);

    // Can't show
    var cant = row(T('caption.cant_show'));
    cant.body.appendChild(el('span', 'mapcap__text', layer.limit || T('map.none_stated')));
    card.appendChild(cant.row);

    // opacity slider (image layers)
    if (layer.kind === 'image') {
      var op = el('div', 'mapcap__opacity');
      var id = 'mapcap-op-' + String(activeSlot).replace(/[^\w-]/g, '_');
      var lab = el('label', 'mapcap__oplabel', T('layers.opacity_for', { name: layer.name || layer.id }));
      lab.setAttribute('for', id);
      var inp = el('input', 'mapcap__range');
      inp.type = 'range'; inp.min = '0'; inp.max = '100'; inp.step = '5'; inp.id = id;
      inp.value = String(Math.round(opacityFor(activeSlot, layer) * 100));
      var out = el('span', 'mono mapcap__opval', inp.value + '%');
      var slot = activeSlot;
      inp.addEventListener('input', function () {
        out.textContent = inp.value + '%';
        inp.setAttribute('aria-valuetext', inp.value + '%');
        App.map.setOpacity(slot, inp.value / 100);
      });
      op.appendChild(lab); op.appendChild(inp); op.appendChild(out);
      card.appendChild(op);
      refs.slider = inp; refs.sliderOut = out;
    } else { refs.slider = null; }

    // Source: desktop row + phone <details>
    var credit = creditFor(layer);
    var src = row(T('caption.source'), 'mapcap__row--source');
    src.body.appendChild(el('span', 'mapcap__text', credit));
    card.appendChild(src.row);
    var det = el('details', 'mapcap__srcm');
    det.appendChild(el('summary', 'mapcap__summary', T('caption.source')));
    det.appendChild(el('p', 'mapcap__text', credit));
    card.appendChild(det);
  }

  function syncSlider() {
    var layer = activeLayer();
    if (!refs.slider || !layer || document.activeElement === refs.slider) return;
    var v = String(Math.round(opacityFor(activeSlot, layer) * 100));
    if (refs.slider.value !== v) { refs.slider.value = v; if (refs.sliderOut) refs.sliderOut.textContent = v + '%'; }
  }

  /* ---------------- controls ---------------- */
  function buildControls() {
    var zoom = el('div', 'mapzoom');
    zoom.setAttribute('role', 'group');
    zoom.setAttribute('aria-label', T('map.label'));
    var zin = el('button', 'mapzoom__btn', '+'); zin.type = 'button';
    zin.setAttribute('aria-label', T('common.zoom_in'));
    var zout = el('button', 'mapzoom__btn', '−'); zout.type = 'button';
    zout.setAttribute('aria-label', T('common.zoom_out'));
    zin.addEventListener('click', function () { map.zoomIn(); });
    zout.addEventListener('click', function () { map.zoomOut(); });
    zoom.appendChild(zin); zoom.appendChild(zout);
    root.appendChild(zoom);
    L.DomEvent.disableClickPropagation(zoom);
    refs.zoomIn = zin; refs.zoomOut = zout;

    var cap = el('section', 'mapcap');
    cap.setAttribute('aria-live', 'polite');
    root.appendChild(cap);
    L.DomEvent.disableClickPropagation(cap);
    L.DomEvent.disableScrollPropagation(cap);
    refs.caption = cap;

    function updZoom() {
      refs.zoomIn.disabled = map.getZoom() >= map.getMaxZoom();
      refs.zoomOut.disabled = map.getZoom() <= map.getMinZoom();
    }
    map.on('zoomend', updZoom);
    updZoom();

    // <details> open state follows breakpoint (open on desktop, collapsed on phones)
    try {
      mq = window.matchMedia('(max-width: 767px)');
      var apply = function () {
        var d = cap.querySelector('.mapcap__srcm');
        if (d) d.open = false;
      };
      if (mq.addEventListener) mq.addEventListener('change', apply);
    } catch (e) { /* ignore */ }
  }

  /* ---------------- first view ----------------
     Leaflet caches the container size the first time it reads it. If the map is created while its
     section is hidden (page opened on #events), that cache is 0x0, and invalidateSize() does nothing
     until the map has a view, so the map would never get one. The first view is therefore created
     here, only once the container has a real size, after refreshing Leaflet's size cache. */
  function hasView() {
    try { return !!(map && map._loaded); } catch (e) { return false; }
  }
  function containerSized() {
    return !!root && root.clientWidth > 0 && root.clientHeight > 0;
  }
  function ensureView() {
    if (!map) return false;
    if (hasView()) return true;
    if (!containerSized()) return false;
    try {
      map.invalidateSize({ animate: false });   // no-op while the map has no view; harmless
      map._sizeChanged = true;                  // Leaflet internal flag: makes getSize() re-read the container
      var b = regionBounds();
      if (b) map.fitBounds(b, { animate: false, padding: [16, 16] });
      else map.setView([20.6, 79.0], 5, { animate: false });
    } catch (e) { console.warn('[map] first view failed', e); return false; }
    if (!hasView()) return false;
    pendingFit = false;
    if (syncWanted) { syncWanted = false; sync(); }
    // modules that drew while there was no view (landfall marker etc.) listen to 'event': run them again
    if (App.state.eventId) App.emit('event', App.state.eventId);
    return true;
  }
  var viewTries = 0;
  function waitForView() {
    viewTries = 0;
    var first = function () { tryView(); };
    if (window.requestAnimationFrame) window.requestAnimationFrame(first); else setTimeout(first, 0);
  }
  function tryView() {
    if (!map) return;
    viewTries++;
    if (hasView()) { try { map.invalidateSize({ animate: false }); } catch (e) { /* ignore */ } return; }
    if (ensureView()) return;
    if (viewTries < 10) setTimeout(tryView, 50);
  }

  /* ---------------- region fit ---------------- */
  function fitRegion(animate) {
    if (!hasView()) { pendingFit = true; ensureView(); return; }
    pendingFit = false;
    var b = regionBounds();
    if (!b) { map.setView([20.6, 79.0], 5, { animate: false }); return; }
    var opts = { padding: [16, 16] };
    if (animate && !reduced()) { opts.duration = 0.9; map.flyToBounds(b, opts); }
    else { opts.animate = false; map.fitBounds(b, opts); }
  }

  /* ---------------- init ---------------- */
  function init(rootEl) {
    if (map) return App.map;
    if (!rootEl) { console.error('[map] init needs a container element'); return null; }
    if (typeof L === 'undefined') { console.error('[map] Leaflet (L) is not loaded'); return null; }
    root = rootEl;
    root.classList.add('map-dark', 'app-map');
    root.setAttribute('role', 'region');
    root.setAttribute('aria-label', T('map.label'));

    map = L.map(root, {
      zoomControl: false, attributionControl: true, zoomSnap: 0.25, zoomDelta: 1,
      preferCanvas: false, worldCopyJump: false
    });
    map.attributionControl.setPrefix(false);
    map.attributionControl.setPosition('bottomright');
    makePanes();

    try {
      L.tileLayer(BASEMAP, {
        maxNativeZoom: 16, maxZoom: 18, opacity: 0.7, className: 'basemap-tiles',
        attribution: T('map.attr_text'), errorTileUrl: ''
      }).addTo(map);
    } catch (e) { console.warn('[map] basemap unavailable', e); }

    L.control.scale({ position: 'bottomright', imperial: false, metric: true, maxWidth: 120 }).addTo(map);

    buildControls();
    fitRegion(false);

    App.on('layers', sync);
    App.on('event', sync);
    App.on('manifest', function () { fitRegion(false); sync(); });
    App.on('lang', function () {
      captionKey = null;
      refs.zoomIn.setAttribute('aria-label', T('common.zoom_in'));
      refs.zoomOut.setAttribute('aria-label', T('common.zoom_out'));
      renderCaption(true);
    });
    App.on('region', function () {
      var b = regionBounds();
      if (b) fitRegion(true); else fitRegion(true);
      sync();
    });
    App.on('mandal', restyleGeo);
    App.on('compare', function () { if (!compact()) capOpen = false; renderCaption(true); });
    App.on('view', function (v) {
      if (v === 'workspace') waitForView();
    });
    window.addEventListener('resize', function () { App.map.invalidate(); });

    sync();
    waitForView();
    return App.map;
  }

  /* ---------------- public API ---------------- */
  App.map = {
    activeLayerId: null,
    init: init,
    invalidate: function () {
      if (!map) return;
      if (hasView()) map.invalidateSize({ animate: false });
      else ensureView();
    },
    flyTo: function (bounds) {
      if (!map || !bounds) return;
      if (!hasView() && !ensureView()) return;
      if (reduced()) map.fitBounds(bounds, { animate: false, padding: [16, 16] });
      else map.flyToBounds(bounds, { duration: 0.9, padding: [16, 16] });
    },
    getMap: function () { return map; },
    getActiveLayer: activeLayer,
    getDisplayedLayerIds: function () {
      return Object.keys(slots).filter(function (id) { return !slots[id].failed && !slots[id].ignored; })
        .map(function (id) { return slots[id].layer.id; });
    },
    setOpacity: function (id, v) {
      var o = {}; o[id] = Math.max(0, Math.min(1, +v));
      App.setState({ opacity: o });
    },
    exportCurrentView: function () {
      if (!map) return null;
      var imgs = [];
      Object.keys(slots).forEach(function (id) {
        var s = slots[id];
        if (s.kind === 'image' && !s.failed && s.url && s.layer.bounds) {
          imgs.push({ id: s.layer.id, url: s.url, bounds: s.layer.bounds, opacity: opacityFor(id, s.layer) });
        }
      });
      var out = { bounds: null, center: null, zoom: null, imgUrls: imgs };
      if (hasView()) {
        try { out.bounds = map.getBounds(); out.center = map.getCenter(); out.zoom = map.getZoom(); }
        catch (e) { /* no view yet */ }
      }
      return out;
    }
  };
})();
