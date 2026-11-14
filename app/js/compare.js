/* compare.js: swipe compare between two image layers, class toggles legend, L/S band toggle.
   Defines window.App.compare. Classic script. Needs core.js (window.App) and Leaflet (L); map.js must be
   initialised first (App.compare.init is called by index.html after load).

   Swipe implementation: OWN divider (not leaflet-side-by-side). That plugin clips with
   layer.getContainer().style.clip, and L.ImageOverlay has no getContainer() (only getElement()), so it
   throws on image overlays. Here two L.imageOverlay layers live in two dedicated panes (above map.js's
   radar pane) and each pane gets a clip-path polygon in layer-pixel coordinates, recomputed on map
   move/zoom/resize and on slider input.

   Public API:
     App.compare.init(mapWrapEl)   build UI inside #map-wrap, listen to App state
     App.compare.open(a, b)        App.setState({compare:{on:true,a,b}}); a/b optional (defaults chosen)
     App.compare.close()           App.setState({compare:{on:false,a:null,b:null}})
     App.compare.isOpen()          boolean
   State used: compare {on,a,b}, classesOn, layersOn, band, opacity, region, eventId. */
(function () {
  'use strict';

  var App = window.App;
  if (!App) { console.error('[compare] core.js must load first'); return; }

  App.addStrings('en', {
    'cmp.left': 'Left',
    'cmp.right': 'Right',
    'cmp.swap': 'Swap left and right',
    'cmp.credit': 'Left: {left} · Right: {right}',
    'cmp.no_layers': 'No image layers to compare for this view',
    'cmp.divider_aria': 'Comparison divider. Use the left and right arrow keys to move it.',
    'cmp.tools_title': 'Classes and radar band',
    'cmp.options': 'Classes and band',
    'cmp.options_short': 'Classes',
    'cmp.credits_title': 'Credits for the two sides',
    'cmp.credit_side': '{side}: {credit}',
    'cmp.sample_pending': 'sample pending',
    'cmp.side_unavailable': '{side} image: unavailable',
    'cmp.classes_aria': 'Show or hide each class on the map',
    'cmp.bar_aria': 'Compare two layers'
  });

  var T = function (k, v) { return App.t(k, v); };
  var SVGNS = 'http://www.w3.org/2000/svg';
  var THUMB = 44;
  var CLASS_TOKEN = { new_water: '--water', wet_crops: '--crops' };

  var wrap = null, map = null;
  var ui = {};                       // DOM refs
  var side = {                       // per side overlay bookkeeping
    a: { layer: null, overlay: null, failed: false, pane: null },
    b: { layer: null, overlay: null, failed: false, pane: null }
  };
  var ratio = 0.5;                   // divider position 0..1
  var optKey = null, toolKey = null;
  var prevBand = null;
  var inited = false;

  /* ---------------- helpers ---------------- */
  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }
  function svgIcon(path, size) {
    var s = document.createElementNS(SVGNS, 'svg');
    s.setAttribute('width', size || 18); s.setAttribute('height', size || 18);
    s.setAttribute('viewBox', '0 0 24 24'); s.setAttribute('fill', 'none');
    s.setAttribute('stroke', 'currentColor'); s.setAttribute('stroke-width', '2');
    s.setAttribute('stroke-linecap', 'round'); s.setAttribute('stroke-linejoin', 'round');
    s.setAttribute('aria-hidden', 'true');
    var p = document.createElementNS(SVGNS, 'path'); p.setAttribute('d', path); s.appendChild(p);
    return s;
  }
  function cssVar(name) {
    try { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); } catch (e) { return ''; }
  }
  function isOpen() { return !!(App.state.compare && App.state.compare.on); }

  /* ---------------- candidates and defaults ---------------- */
  function allReady() {
    return App.layersFor({ region: App.state.region, eventId: App.state.eventId }).filter(function (l) {
      return l.kind === 'image' && l.status === 'ready' && l.png && l.bounds;
    });
  }
  function candidates() {
    var c = allReady();
    var band = App.state.band || 'L';
    var bl = c.filter(function (l) { return (l.band || 'L') === band; });
    return bl.length ? bl : c;
  }
  function seriesKey(l) { return l.latest_of || l.id; }

  function defaults(c) {
    if (!c.length) return { a: null, b: null };
    var right = null;
    for (var i = 0; i < c.length && !right; i++) {
      var key = seriesKey(c[i]), newest = true;
      c.forEach(function (o) {
        if (seriesKey(o) === key && String(o.date || '') > String(c[i].date || '')) newest = false;
      });
      if (newest) right = c[i];
    }
    right = right || c[0];
    // Left: the latest layer of the same series that the manifest files under 'before' (the pre-event
    // scene), else the previous scene of that series, else any other layer.
    var left = null;
    function older(o) {
      return o.id !== right.id && seriesKey(o) === seriesKey(right) && String(o.date || '') < String(right.date || '');
    }
    c.forEach(function (o) {
      if (older(o) && o.group === 'before' && (!left || String(o.date) > String(left.date))) left = o;
    });
    if (!left) c.forEach(function (o) {
      if (older(o) && (!left || String(o.date) > String(left.date))) left = o;
    });
    if (!left) left = c.filter(function (o) { return o.id !== right.id; })[0] || right;
    return { a: left.id, b: right.id };
  }

  function labelFor(l) {
    var d = l.date && /^\d{4}-\d{2}-\d{2}/.test(l.date) ? App.fmt.date(l.date, { year: false }) : '';
    return (d ? d + ' · ' : '') + (l.name || l.id);
  }
  function creditFor(l) { return (l && l.credit) || T('map.credit_tbc'); }

  /* ---------------- build UI ----------------
     Layout (kept small on purpose, see docs): a top-left row with two 44px buttons [Compare] [Classes and band];
     under it a panel holding the compact compare bar (one row: Left select, swap, Right select, close) and
     the options popover (band toggle, class toggles, credits). The popover is closed by default and never
     taller than 40% of the map. Nothing sits in the right-hand column (Layers button, zoom, scale). */
  function buildUI() {
    // compare button
    var btn = el('button', 'map-btn cmp-btn');
    btn.type = 'button';
    btn.setAttribute('aria-pressed', 'false');
    btn.appendChild(svgIcon('M12 3v18M4 6h5v12H4zM15 6h5v12h-5z'));
    btn.appendChild(el('span', null, T('compare.title')));
    btn.addEventListener('click', function () { if (isOpen()) close(); else open(); });
    ui.btn = btn; ui.btnText = btn.lastChild;

    // options button (classes + radar band), collapsed popover
    var opt = el('button', 'map-btn cmp-opt');
    opt.type = 'button';
    opt.id = 'cmp-opt';
    opt.setAttribute('aria-expanded', 'false');
    opt.setAttribute('aria-controls', 'cmp-pop');
    opt.appendChild(svgIcon('M4 6h16M7 12h10M10 18h4'));
    opt.appendChild(el('span', 'cmp-opt__long', T('cmp.options')));
    opt.appendChild(el('span', 'cmp-opt__short', T('cmp.options_short')));
    opt.setAttribute('aria-label', T('cmp.options'));
    opt.addEventListener('click', function () { setPop(!!ui.pop.hidden); });
    ui.opt = opt;

    var top = el('div', 'cmp-top');
    top.appendChild(btn); top.appendChild(opt);
    ui.top = top;

    // panel under the buttons: compact bar + popover
    var panel = el('div', 'cmp-panel');
    ui.panel = panel;

    var bar = el('div', 'cmp-bar');
    bar.setAttribute('role', 'group');
    bar.setAttribute('aria-label', T('cmp.bar_aria'));
    bar.hidden = true;
    bar.addEventListener('keydown', function (e) { if (e.key === 'Escape') { close(); btn.focus(); } });
    var row = el('div', 'cmp-row');

    function field(cls, labelKey) {
      var f = el('div', 'cmp-field ' + cls);
      var lab = el('label', 'cmp-label', T(labelKey));
      var sel = el('select', 'cmp-select');
      var id = 'cmp-sel-' + cls;
      sel.id = id; lab.setAttribute('for', id);
      f.appendChild(lab); f.appendChild(sel);
      sel.addEventListener('change', onSelect);
      return { f: f, lab: lab, sel: sel };
    }
    var fa = field('cmp-field--a', 'cmp.left'), fb = field('cmp-field--b', 'cmp.right');
    ui.selA = fa.sel; ui.selB = fb.sel; ui.labA = fa.lab; ui.labB = fb.lab;

    var swap = el('button', 'cmp-icon cmp-swap');
    swap.type = 'button';
    swap.setAttribute('aria-label', T('cmp.swap')); swap.title = T('cmp.swap');
    swap.appendChild(svgIcon('M7 4L3 8l4 4M3 8h14M17 20l4-4-4-4M21 16H7'));
    swap.addEventListener('click', function () {
      var c = App.state.compare;
      App.setState({ compare: { on: true, a: c.b, b: c.a } });
    });
    var close_ = el('button', 'cmp-icon cmp-close');
    close_.type = 'button';
    close_.setAttribute('aria-label', T('compare.exit')); close_.title = T('compare.exit');
    close_.appendChild(svgIcon('M6 6l12 12M18 6L6 18'));
    close_.addEventListener('click', function () { close(); btn.focus(); });
    ui.swap = swap; ui.closeBtn = close_;

    row.appendChild(fa.f); row.appendChild(swap); row.appendChild(fb.f); row.appendChild(close_);
    bar.appendChild(row);
    var status = el('p', 'cmp-status');
    status.setAttribute('role', 'status');
    status.hidden = true;
    bar.appendChild(status);
    ui.bar = bar; ui.status = status;

    // popover: band + classes + (while comparing) credits and the drag hint
    var pop = el('div', 'cmp-pop');
    pop.id = 'cmp-pop';
    pop.setAttribute('role', 'region');
    pop.setAttribute('aria-label', T('cmp.tools_title'));
    pop.hidden = true;
    pop.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') { e.stopPropagation(); setPop(false); opt.focus(); }
    });
    var body = el('div', 'cmp-tools__body');
    var extra = el('div', 'cmp-sec cmp-extra');
    extra.hidden = true;
    extra.appendChild(el('p', 'cmp-sec__title', T('cmp.credits_title')));
    var credit = el('p', 'cmp-credit');
    var hint = el('p', 'cmp-hint', T('compare.hint'));
    extra.appendChild(credit); extra.appendChild(hint);
    pop.appendChild(body); pop.appendChild(extra);
    ui.pop = pop; ui.toolsBody = body; ui.extra = extra; ui.credit = credit; ui.hint = hint;

    panel.appendChild(bar);
    panel.appendChild(pop);

    // swipe layer
    var range = el('input', 'cmp-range');
    range.type = 'range'; range.min = '0'; range.max = '1000'; range.step = '10'; range.value = '500';
    range.setAttribute('aria-label', T('cmp.divider_aria'));
    range.addEventListener('input', function () {
      ratio = Math.max(0, Math.min(1, range.value / 1000));
      range.setAttribute('aria-valuetext', Math.round(ratio * 100) + '%');
      updateClip();
    });
    var line = el('div', 'cmp-line');
    var knob = el('span', 'cmp-knob');
    knob.appendChild(svgIcon('M9 6l-6 6 6 6M15 6l6 6-6 6', 20));
    line.appendChild(knob);
    var chipA = el('div', 'cmp-chip cmp-chip--a');
    var chipB = el('div', 'cmp-chip cmp-chip--b');
    ui.range = range; ui.line = line; ui.chipA = chipA; ui.chipB = chipB;
    [range, line, chipA, chipB].forEach(function (n) { n.hidden = true; });

    wrap.appendChild(top);
    wrap.appendChild(panel);
    wrap.appendChild(chipA); wrap.appendChild(chipB);
    wrap.appendChild(range); wrap.appendChild(line);
  }

  function setPop(open) {
    ui.pop.hidden = !open;
    ui.opt.setAttribute('aria-expanded', open ? 'true' : 'false');
    ui.opt.classList.toggle('is-open', open);
    sizeVars();
  }

  /* popover never exceeds 40% of the map height */
  function sizeVars() {
    if (!wrap) return;
    wrap.style.setProperty('--cmp-maxh', Math.max(120, Math.floor((wrap.clientHeight || 0) * 0.4)) + 'px');
  }

  /* ---------------- select options ---------------- */
  function fillSelect(sel, c, value) {
    sel.textContent = '';
    var has = false;
    c.forEach(function (l) {
      var o = document.createElement('option');
      o.value = l.id; o.textContent = labelFor(l);
      if (l.id === value) has = true;
      sel.appendChild(o);
    });
    if (value && !has) {            // layer set from elsewhere that is not in the list: keep it selectable
      var l2 = App.layerById(value);
      var o2 = document.createElement('option');
      o2.value = value; o2.textContent = l2 ? labelFor(l2) : value;
      sel.insertBefore(o2, sel.firstChild);
    }
    sel.value = value || '';
  }

  function onSelect() {
    App.setState({ compare: { on: true, a: ui.selA.value, b: ui.selB.value } });
  }

  /* ---------------- panes + overlays ---------------- */
  function ensureMap() {
    if (map) return true;
    map = (App.map && App.map.getMap && App.map.getMap()) || null;
    if (!map || typeof L === 'undefined') return false;
    side.a.pane = map.createPane('cmpPaneLeft'); side.a.pane.style.zIndex = 412;
    side.b.pane = map.createPane('cmpPaneRight'); side.b.pane.style.zIndex = 413;
    map.on('move zoom zoomend moveend viewreset resize', updateClip);
    if (typeof ResizeObserver !== 'undefined') {
      try { new ResizeObserver(function () { sizeVars(); updateClip(); }).observe(wrap); } catch (e) { /* ignore */ }
    }
    return true;
  }

  function opacityOf(l) {
    var o = App.state.opacity && App.state.opacity[l.id];
    if (o == null) o = l.opacity;
    if (o == null || isNaN(o)) o = 0.85;
    return Math.max(0, Math.min(1, +o));
  }

  function setSide(key, layer) {
    var s = side[key];
    if (s.layer && layer && s.layer.id === layer.id && s.overlay) { s.overlay.setOpacity(opacityOf(layer)); return; }
    if (s.overlay) { try { map.removeLayer(s.overlay); } catch (e) { /* ignore */ } }
    s.overlay = null; s.layer = layer || null; s.failed = false;
    if (!layer || !layer.png || !layer.bounds) { s.failed = !!layer; return; }
    var ov = L.imageOverlay(App.assetUrl(layer.png), layer.bounds, {
      pane: key === 'a' ? 'cmpPaneLeft' : 'cmpPaneRight', opacity: opacityOf(layer),
      interactive: false, className: 'cmp-img', alt: ''
    });
    ov.on('error', function () { if (s.overlay === ov) { s.failed = true; renderBar(); } });
    ov.on('load', function () { if (s.overlay === ov && s.failed) { s.failed = false; renderBar(); } });
    ov.addTo(map);
    s.overlay = ov;
  }

  function clearSides() {
    ['a', 'b'].forEach(function (k) {
      var s = side[k];
      if (s.overlay && map) { try { map.removeLayer(s.overlay); } catch (e) { /* ignore */ } }
      s.overlay = null; s.layer = null; s.failed = false;
      if (s.pane) s.pane.style.clipPath = '';
    });
  }

  /* ---------------- divider geometry ---------------- */
  function dividerX() {
    var w = wrap.clientWidth || 0;
    return THUMB / 2 + ratio * Math.max(0, w - THUMB);
  }

  function updateClip() {
    if (!map || !isOpen() || !side.a.pane) return;
    var w = wrap.clientWidth, x = dividerX();
    ui.line.style.left = x + 'px';
    var nw = map.containerPointToLayerPoint([0, 0]);
    var se = map.containerPointToLayerPoint(map.getSize());
    var cx = nw.x + x;
    function px(n) { return (Math.round(n * 10) / 10) + 'px'; }
    side.a.pane.style.clipPath = 'polygon(' + [px(nw.x), px(nw.y), px(cx), px(nw.y), px(cx), px(se.y), px(nw.x), px(se.y)]
      .reduce(function (acc, v, i) { return acc + (i % 2 ? ' ' : (i ? ', ' : '')) + v; }, '') + ')';
    side.b.pane.style.clipPath = 'polygon(' + [px(cx), px(nw.y), px(se.x), px(nw.y), px(se.x), px(se.y), px(cx), px(se.y)]
      .reduce(function (acc, v, i) { return acc + (i % 2 ? ' ' : (i ? ', ' : '')) + v; }, '') + ')';
    // chips beside the divider
    ui.chipA.style.right = (w - x + 10) + 'px';
    ui.chipA.style.maxWidth = Math.max(0, x - 26) + 'px';
    ui.chipB.style.left = (x + 10) + 'px';
    ui.chipB.style.maxWidth = Math.max(0, w - x - 26) + 'px';
  }

  function fillChip(chip, layer) {
    chip.textContent = '';
    if (!layer) return;
    chip.appendChild(el('span', 'cmp-chip__name', layer.name || layer.id));
    if (layer.date && /^\d{4}-\d{2}-\d{2}/.test(layer.date)) chip.appendChild(el('span', 'cmp-chip__date mono', App.fmt.date(layer.date)));
  }

  /* ---------------- render ---------------- */
  function renderBar() {
    var c = App.state.compare || {};
    var la = side.a.layer, lb = side.b.layer;
    fillChip(ui.chipA, la); fillChip(ui.chipB, lb);
    ui.credit.textContent = (la || lb) ? T('cmp.credit', { left: la ? creditFor(la) : '', right: lb ? creditFor(lb) : '' }) : '';
    ui.extra.hidden = !isOpen();
    var msgs = [];
    if (side.a.failed || (c.a && !la)) msgs.push(T('cmp.side_unavailable', { side: T('cmp.left') }));
    if (side.b.failed || (c.b && !lb)) msgs.push(T('cmp.side_unavailable', { side: T('cmp.right') }));
    if (!candidates().length) msgs = [T('cmp.no_layers')];
    ui.status.textContent = msgs.join(' · ');
    ui.status.hidden = !msgs.length;
  }

  function renderCompare() {
    var on = isOpen();
    ui.btn.setAttribute('aria-pressed', on ? 'true' : 'false');
    ui.bar.hidden = !on;
    ui.extra.hidden = !on;
    [ui.range, ui.line, ui.chipA, ui.chipB].forEach(function (n) { n.hidden = !on; });
    wrap.classList.toggle('compare-on', on);
    if (!on) { clearSides(); return; }
    if (!ensureMap()) { renderBar(); return; }

    var c = candidates();
    var st = App.state.compare;
    var a = st.a, b = st.b;
    if (!a || !b) {                         // opened without ids: fill defaults (re-enters through 'compare')
      var d = defaults(c);
      a = a || d.a; b = b || d.b;
      if (a !== st.a || b !== st.b) { App.setState({ compare: { on: true, a: a, b: b } }); return; }
    }
    var key = c.map(function (l) { return l.id; }).join('|') + '#' + App.state.lang + '#' + a + '#' + b;
    if (key !== optKey) {
      optKey = key;
      fillSelect(ui.selA, c, a); fillSelect(ui.selB, c, b);
    } else {
      ui.selA.value = a; ui.selB.value = b;
    }
    var la = App.layerById(a), lb = App.layerById(b);
    if (la && (la.kind !== 'image' || la.status !== 'ready')) la = null;
    if (lb && (lb.kind !== 'image' || lb.status !== 'ready')) lb = null;
    setSide('a', la); setSide('b', lb);
    renderBar();
    updateClip();
  }

  /* ---------------- tools card: band + classes ---------------- */
  function classLayers() {
    return App.layersFor({ region: App.state.region, eventId: App.state.eventId }).filter(function (l) {
      return l.type === 'derived' && l.class_group && l.kind === 'image';
    });
  }
  function hasS() {
    return App.layersFor({ region: App.state.region, eventId: App.state.eventId }).some(function (l) {
      return l.status === 'ready' && l.band === 'S';
    });
  }
  function classOf(l) { return (l.classes && l.classes[0]) || { id: l.id, label: l.name || l.id, style: 'fill' }; }

  function buildTools() {
    var cls = classLayers(), sOk = hasS();
    var key = cls.map(function (l) { return l.id + ':' + l.status; }).join('|') + '#' + sOk + '#' + App.state.lang;
    if (key === toolKey) { syncTools(); return; }
    toolKey = key;
    var activeId = document.activeElement && ui.toolsBody.contains(document.activeElement)
      ? document.activeElement.getAttribute('data-k') : null;
    var body = ui.toolsBody;
    body.textContent = '';

    // band toggle
    var bs = el('div', 'cmp-sec');
    bs.appendChild(el('p', 'cmp-sec__title', T('compare.band_label')));
    var seg = el('div', 'cmp-seg');
    seg.setAttribute('role', 'group'); seg.setAttribute('aria-label', T('compare.band_label'));
    ['L', 'S'].forEach(function (b) {
      var bt = el('button', 'cmp-seg__btn', T(b === 'L' ? 'compare.band_l' : 'compare.band_s'));
      bt.type = 'button'; bt.setAttribute('data-k', 'band-' + b); bt.setAttribute('data-band', b);
      if (b === 'S' && !sOk) {
        bt.setAttribute('aria-disabled', 'true');
        bt.title = T('compare.s_none');
        bt.setAttribute('aria-describedby', 'cmp-s-reason');
      }
      bt.addEventListener('click', function () {
        if (bt.getAttribute('aria-disabled') === 'true') return;
        App.setState({ band: b });
      });
      seg.appendChild(bt);
    });
    bs.appendChild(seg);
    if (!sOk) {
      var why = el('p', 'cmp-reason', T('compare.s_none'));
      why.id = 'cmp-s-reason';
      bs.appendChild(why);
    }
    body.appendChild(bs);

    // class toggles
    if (cls.length) {
      var cs = el('div', 'cmp-sec');
      var head = el('div', 'cmp-sec__head');
      head.appendChild(el('p', 'cmp-sec__title', T('classes.title')));
      var sample = cls.filter(function (l) { return l.placeholder && l.placeholder.is; })[0];
      if (sample) head.appendChild(el('span', 'tag-sample', sample.placeholder.tag || T('state.placeholder')));
      cs.appendChild(head);
      var list = el('div', 'cmp-classes');
      list.setAttribute('role', 'group'); list.setAttribute('aria-label', T('cmp.classes_aria'));
      cls.forEach(function (l) {
        var c = classOf(l);
        var ready = l.status === 'ready';
        var lab = el('label', 'cmp-class' + (ready ? '' : ' is-disabled'));
        var inp = el('input', 'cmp-class__check');
        inp.type = 'checkbox'; inp.setAttribute('data-k', 'class-' + l.id); inp.setAttribute('data-layer', l.id);
        inp.disabled = !ready;
        inp.addEventListener('change', function () { toggleClass(l, c, inp.checked); });
        var sw = el('span', 'cmp-sw');
        if (c.style === 'outline') sw.classList.add('cmp-sw--outline');
        else {
          var tok = CLASS_TOKEN[c.id] || '--teal';
          sw.style.background = cssVar(tok) || ('var(' + tok + ')');
        }
        var txt = el('span', 'cmp-class__txt');
        txt.appendChild(el('span', 'cmp-class__name', App.likely(c.label)));
        if (!ready) txt.appendChild(el('span', 'cmp-class__pending', T('cmp.sample_pending')));
        lab.appendChild(inp); lab.appendChild(sw); lab.appendChild(txt);
        list.appendChild(lab);
      });
      cs.appendChild(list);
      body.appendChild(cs);
    }
    syncTools();
    if (activeId) {
      var again = body.querySelector('[data-k="' + activeId + '"]');
      if (again && !again.disabled) again.focus();
    }
  }

  function syncTools() {
    var band = App.state.band || 'L';
    Array.prototype.forEach.call(ui.toolsBody.querySelectorAll('.cmp-seg__btn'), function (bt) {
      bt.setAttribute('aria-pressed', bt.getAttribute('data-band') === band ? 'true' : 'false');
    });
    Array.prototype.forEach.call(ui.toolsBody.querySelectorAll('.cmp-class__check'), function (inp) {
      inp.checked = App.state.layersOn.has(inp.getAttribute('data-layer'));
    });
  }

  function toggleClass(l, c, on) {
    var layers = new Set(App.state.layersOn), classes = new Set(App.state.classesOn);
    if (on) { layers.add(l.id); classes.add(c.id); } else { layers.delete(l.id); classes.delete(c.id); }
    App.setState({ layersOn: layers, classesOn: classes });
  }

  /* classesOn mirrors which class layers are on in layersOn (also when changed from the drawer) */
  function mirrorClasses() {
    var want = new Set();
    classLayers().forEach(function (l) { if (App.state.layersOn.has(l.id)) want.add(classOf(l).id); });
    var cur = App.state.classesOn, same = cur.size === want.size;
    if (same) want.forEach(function (v) { if (!cur.has(v)) same = false; });
    if (!same) App.setState({ classesOn: want });
  }

  /* ---------------- text refresh (language) ---------------- */
  function relabel() {
    ui.btnText.textContent = T('compare.title');
    ui.labA.textContent = T('cmp.left'); ui.labB.textContent = T('cmp.right');
    ui.swap.setAttribute('aria-label', T('cmp.swap')); ui.swap.title = T('cmp.swap');
    ui.closeBtn.setAttribute('aria-label', T('compare.exit')); ui.closeBtn.title = T('compare.exit');
    ui.hint.textContent = T('compare.hint');
    ui.opt.setAttribute('aria-label', T('cmp.options'));
    ui.opt.querySelector('.cmp-opt__long').textContent = T('cmp.options');
    ui.opt.querySelector('.cmp-opt__short').textContent = T('cmp.options_short');
    ui.pop.setAttribute('aria-label', T('cmp.tools_title'));
    ui.range.setAttribute('aria-label', T('cmp.divider_aria'));
    ui.bar.setAttribute('aria-label', T('cmp.bar_aria'));
  }

  function refresh() {
    if (!inited) return;
    var band = App.state.band || 'L';
    if (prevBand !== null && band !== prevBand && isOpen()) {
      var d = defaults(candidates());
      prevBand = band;
      App.setState({ compare: { on: true, a: d.a, b: d.b } });
    }
    prevBand = band;
    buildTools();
    mirrorClasses();
    renderCompare();
  }

  /* ---------------- public ---------------- */
  function open(a, b) {
    var patch = { on: true, a: a || null, b: b || null };
    if (!patch.a || !patch.b) {
      var cur = App.state.compare || {};
      var d = defaults(candidates());
      patch.a = patch.a || cur.a || d.a; patch.b = patch.b || cur.b || d.b;
    }
    App.setState({ compare: patch });
    if (isOpen()) renderCompare();
  }
  function close() {
    App.setState({ compare: { on: false, a: null, b: null } });
    renderCompare();
  }

  function init(mapWrapEl) {
    if (inited) return App.compare;
    wrap = mapWrapEl || document.getElementById('map-wrap');
    if (!wrap) { console.error('[compare] init needs the map wrapper element'); return null; }
    var link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = 'css/compare.css?v=2';
    var me = document.querySelector('script[src*="compare.js"]');
    if (me && me.src) link.href = me.src.replace(/js\/compare\.js(\?.*)?$/, 'css/compare.css$1');
    document.head.appendChild(link);

    buildUI();
    inited = true;
    prevBand = App.state.band || 'L';
    sizeVars();
    ensureMap();

    ['layers', 'region', 'event', 'manifest', 'compare'].forEach(function (e) { App.on(e, refresh); });
    App.on('lang', function () { optKey = null; toolKey = null; relabel(); refresh(); });
    App.on('view', function () { setTimeout(updateClip, 50); });
    window.addEventListener('resize', function () { sizeVars(); updateClip(); });
    refresh();
    return App.compare;
  }

  App.compare = { init: init, open: open, close: close, isOpen: isOpen };
})();
