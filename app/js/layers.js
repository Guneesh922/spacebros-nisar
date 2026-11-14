/* layers.js: layer drawer (desktop panel) and bottom sheet (phone). Defines window.App.layers.
   Public API:
     App.layers.init(el)    build into the <aside id="drawer"> (called by the shell after load)
     App.layers.open() / close() / toggle() / isOpen()
   Reads App.layersFor({region, eventId}), App.manifest.coming_next, App.state.layersOn / opacity / eventId.
   Writes App.setState({layersOn}) and App.setState({opacity}). Persists nothing. */
(function () {
  'use strict';
  var App = window.App;
  if (!App) { return; }

  App.addStrings('en', {
    'layers.chip.nisar': 'NISAR L-band',
    'layers.chip.context': 'Context',
    'layers.chip.model': 'Model',
    'layers.chip.reference': 'Reference',
    'layers.close': 'Close layers',
    'layers.subtitle': 'Read from the data manifest',
    'layers.legend_label': 'Chip legend',
    'layers.unavailable': 'Not available yet · sample pending',
    'layers.open_source': 'Open at source',
    'layers.link_only': 'link only, data not re-hosted',
    'layers.in_alerts': 'Shown in the alerts strip',
    'layers.shows': 'Shows:',
    'layers.source': 'Source:',
    'layers.credit': 'Credit:',
    'layers.live': 'live',
    'layers.other': 'Other layers',
    'layers.handle': 'Drag down to close',
    'layers.limit_icon': 'Limit of this layer',
    'layers.none_stated': 'not stated'
  });

  var T = function (k, v) { return App.t(k, v); };
  var TYPE_ORDER = ['nisar', 'derived', 'optical', 'weather', 'reference', 'alerts'];
  var EVENT_GROUPS = ['before', 'during', 'after'];
  var mqPhone = window.matchMedia ? window.matchMedia('(max-width: 767px)') : { matches: false };

  var root = null, scrim = null, btn = null;
  var body = null;
  var opened = false;
  var expanded = new Set();
  var lastSig = null;
  var lastFocusBeforeOpen = null;

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }
  function svg(path, size, extra) {
    var s = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    s.setAttribute('width', size || 20); s.setAttribute('height', size || 20);
    s.setAttribute('viewBox', '0 0 24 24'); s.setAttribute('fill', 'none');
    s.setAttribute('stroke', 'currentColor'); s.setAttribute('stroke-width', '2');
    s.setAttribute('aria-hidden', 'true'); s.setAttribute('focusable', 'false');
    if (extra) s.setAttribute('class', extra);
    var p = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    p.setAttribute('d', path); s.appendChild(p);
    return s;
  }
  function sid(id) { return String(id).replace(/[^\w-]/g, '_'); }
  function sortedIds(set) { return Array.from(set).sort().join('|'); }

  /* ---------- data helpers ---------- */
  function currentLayers() {
    return App.layersFor({ region: App.state.region, eventId: App.state.eventId });
  }
  function chipKey(l) { return l.chip === 'nisar' ? 'nisar' : (l.chip || 'context'); }
  function chipLabel(l) {
    var k = 'layers.chip.' + chipKey(l);
    return App.hasString(k) ? T(k) : T('layers.chip.context');
  }
  function dateText(l) {
    if (!l.date) return '';
    if (l.date === 'live') return T('layers.live');
    if (/^\d{4}-\d{2}-\d{2}/.test(l.date)) return App.fmt.date(l.date);
    return String(l.date);
  }
  function isAlerts(l) { return l.type === 'alerts'; }
  function isLink(l) { return l.kind === 'link' || l.status === 'link_only'; }
  function isComing(l) { return l.status === 'coming_next'; }
  function isUnavailable(l) { return l.status === 'unavailable'; }
  function isToggle(l) { return !isAlerts(l) && !isLink(l) && !isComing(l); }
  function hasOpacity(l) { return l.kind === 'image' || l.kind === 'wmts'; }
  function opacityOf(l) {
    var o = App.state.opacity && App.state.opacity[l.id];
    if (o == null) o = l.opacity;
    return o == null ? 0.85 : o;
  }
  function sourceText(l) {
    if (l.source) return typeof l.source === 'string' ? l.source : (l.source.provider || l.source.id || '');
    var s = (App.manifest.sources || []).filter(function (x) { return x.id === l.source_id; })[0];
    return s ? (s.provider || s.id) : '';
  }
  function rank(l) { var i = TYPE_ORDER.indexOf(l.type); return i < 0 ? TYPE_ORDER.length : i; }
  function byTypeThenKeep(list) {
    return list.map(function (l, i) { return { l: l, i: i }; }).sort(function (a, b) {
      return (rank(a.l) - rank(b.l)) || (a.i - b.i);
    }).map(function (x) { return x.l; });
  }
  function rangeText(items) {
    var ds = items.map(function (l) { return l.date; })
      .filter(function (d) { return d && /^\d{4}-\d{2}-\d{2}/.test(d); }).sort();
    if (!ds.length) return '';
    var a = ds[0], b = ds[ds.length - 1];
    return a === b ? App.fmt.date(a) : T('events.dates', { from: App.fmt.date(a, { year: false }), to: App.fmt.date(b) });
  }

  /* ---------- toggling ---------- */
  function setOn(id, on) {
    var next = new Set(App.state.layersOn);
    if (on) next.add(id); else next.delete(id);
    App.setState({ layersOn: next });
  }

  /* ---------- row builders ---------- */
  function chipEl(l) { return el('span', 'chip chip--' + (l.chip === 'nisar' ? 'nisar' : 'context'), chipLabel(l)); }

  function sampleTag(l) {
    if (l.placeholder && l.placeholder.is) {
      return el('span', 'tag-sample', l.placeholder.tag || T('state.placeholder'));
    }
    return null;
  }

  function limitLine(l) {
    var p = el('p', 'lrow__limit');
    var ic = svg('M12 3a9 9 0 100 18 9 9 0 000-18zM12 11v6M12 7.5v.5', 14, 'lrow__icon');
    ic.setAttribute('role', 'img'); ic.removeAttribute('aria-hidden');
    ic.setAttribute('aria-label', T('layers.limit_icon'));
    p.appendChild(ic);
    var t = el('span');
    t.appendChild(el('strong', null, T('layers.cant_show') + ' '));
    t.appendChild(document.createTextNode(l.limit || T('layers.none_stated')));
    p.appendChild(t);
    return p;
  }

  function checkbox(l, disabled) {
    var cb = el('input', 'lrow__cb');
    cb.type = 'checkbox';
    cb.checked = App.state.layersOn.has(l.id);
    cb.disabled = !!disabled;
    cb.setAttribute('data-lid', l.id);
    cb.setAttribute('aria-label', T('layers.toggle_aria', { name: l.name || l.id }));
    cb.addEventListener('change', function () { setOn(l.id, cb.checked); });
    return cb;
  }

  function opacityControl(l) {
    var wrap = el('div', 'lrow__opacity');
    var id = 'lop-' + sid(l.id);
    var lab = el('label', 'lrow__oplabel', T('layers.opacity_for', { name: l.name || l.id }));
    lab.setAttribute('for', id);
    var inp = el('input', 'lrow__range');
    inp.type = 'range'; inp.min = '0'; inp.max = '100'; inp.step = '5'; inp.id = id;
    inp.setAttribute('data-oplid', l.id);
    inp.value = String(Math.round(opacityOf(l) * 100));
    var out = el('span', 'mono lrow__opval', inp.value + '%');
    inp.addEventListener('input', function () {
      out.textContent = inp.value + '%';
      var patch = {}; patch[l.id] = Number(inp.value) / 100;
      selfOpacity = true;
      try { App.setState({ opacity: patch }); } finally { selfOpacity = false; }
    });
    wrap.appendChild(lab); wrap.appendChild(inp); wrap.appendChild(out);
    return wrap;
  }
  var selfOpacity = false;

  /* full detail row for ON NOW */
  function onNowRow(l) {
    var row = el('div', 'lrow lrow--now');
    var top = el('div', 'lrow__top');
    top.appendChild(checkbox(l, false));
    var main = el('div', 'lrow__main');
    var head = el('div', 'lrow__head');
    head.appendChild(el('span', 'lrow__name', l.name || l.id));
    head.appendChild(chipEl(l));
    var tag = sampleTag(l); if (tag) head.appendChild(tag);
    main.appendChild(head);
    var meta = el('p', 'lrow__meta');
    var d = dateText(l);
    if (d) meta.appendChild(el('span', 'mono', d));
    var s = sourceText(l);
    if (d && s) meta.appendChild(document.createTextNode(' · '));
    if (s) meta.appendChild(document.createTextNode(s));
    main.appendChild(meta);
    main.appendChild(limitLine(l));
    if (l.credit) main.appendChild(el('p', 'lrow__credit', T('layers.credit') + ' ' + l.credit));
    if (hasOpacity(l)) main.appendChild(opacityControl(l));
    top.appendChild(main);
    row.appendChild(top);
    return row;
  }

  function detailsBlock(l, id) {
    var d = el('div', 'lrow__details'); d.id = id;
    var s = sourceText(l);
    if (l.shows) d.appendChild(el('p', null, l.shows));
    if (s) d.appendChild(el('p', null, T('layers.source') + ' ' + s));
    d.appendChild(limitLine(l));
    if (l.credit) d.appendChild(el('p', 'lrow__credit', T('layers.credit') + ' ' + l.credit));
    var tag = sampleTag(l); if (tag) { var w = el('p'); w.appendChild(tag); d.appendChild(w); }
    return d;
  }

  function expandButton(l, detId) {
    var b = el('button', 'lrow__chev');
    b.type = 'button';
    var open = expanded.has(l.id);
    b.setAttribute('aria-expanded', open ? 'true' : 'false');
    b.setAttribute('aria-controls', detId);
    b.setAttribute('aria-label', T(open ? 'layers.collapse' : 'layers.expand') + ': ' + (l.name || l.id));
    b.setAttribute('data-chev', l.id);
    b.appendChild(svg('M6 9l6 6 6-6', 20, 'lrow__chevsvg'));
    b.addEventListener('click', function () {
      if (expanded.has(l.id)) expanded.delete(l.id); else expanded.add(l.id);
      var now = expanded.has(l.id);
      b.setAttribute('aria-expanded', now ? 'true' : 'false');
      b.setAttribute('aria-label', T(now ? 'layers.collapse' : 'layers.expand') + ': ' + (l.name || l.id));
      var det = document.getElementById(detId);
      if (det) det.hidden = !now;
      b.closest('.lrow').classList.toggle('is-open', now);
    });
    return b;
  }

  /* one-line row (toggle layers), also unavailable rows */
  function lineRow(l) {
    var unavailable = isUnavailable(l);
    var row = el('div', 'lrow lrow--line' + (unavailable ? ' is-off' : '') + (expanded.has(l.id) ? ' is-open' : ''));
    var detId = 'ldet-' + sid(l.id);
    var top = el('div', 'lrow__top lrow__top--line');
    top.appendChild(checkbox(l, unavailable));
    var main = el('div', 'lrow__main');
    var head = el('div', 'lrow__head');
    head.appendChild(el('span', 'lrow__name', l.name || l.id));
    head.appendChild(chipEl(l));
    main.appendChild(head);
    if (unavailable) main.appendChild(el('p', 'lrow__reason', T('layers.unavailable')));
    top.appendChild(main);
    var d = dateText(l);
    top.appendChild(el('span', 'mono lrow__date', d));
    top.appendChild(expandButton(l, detId));
    row.appendChild(top);
    var det = detailsBlock(l, detId);
    det.hidden = !expanded.has(l.id);
    row.appendChild(det);
    return row;
  }

  function linkRow(l) {
    var row = el('div', 'lrow lrow--link');
    var top = el('div', 'lrow__top lrow__top--line');
    var main = el('div', 'lrow__main');
    var head = el('div', 'lrow__head');
    head.appendChild(el('span', 'lrow__name', l.name || l.id));
    head.appendChild(chipEl(l));
    main.appendChild(head);
    main.appendChild(el('p', 'lrow__reason', T('layers.link_only')));
    top.appendChild(main);
    if (l.link_url) {
      var a = el('a', 'lrow__link', T('layers.open_source'));
      a.href = l.link_url; a.target = '_blank'; a.rel = 'noopener noreferrer';
      a.setAttribute('aria-label', T('layers.open_source') + ': ' + (l.name || l.id));
      top.appendChild(a);
    }
    row.appendChild(top);
    return row;
  }

  function alertsRow(l) {
    var row = el('div', 'lrow lrow--info');
    var main = el('div', 'lrow__main');
    var head = el('div', 'lrow__head');
    head.appendChild(el('span', 'lrow__name', l.name || l.id));
    head.appendChild(chipEl(l));
    main.appendChild(head);
    main.appendChild(el('p', 'lrow__reason', T('layers.in_alerts')));
    row.appendChild(main);
    return row;
  }

  function anyRow(l) {
    if (isAlerts(l)) return alertsRow(l);
    if (isLink(l)) return linkRow(l);
    return lineRow(l);
  }

  /* ---------- sections ---------- */
  function section(title, sub, items, cls) {
    var sec = el('section', 'lsec' + (cls ? ' ' + cls : ''));
    var h = el('div', 'lsec__head');
    var h3 = el('h3', 'lsec__title', title);
    h.appendChild(h3);
    if (sub) h.appendChild(el('span', 'mono lsec__sub', sub));
    sec.appendChild(h);
    items.forEach(function (n) { sec.appendChild(n); });
    return sec;
  }

  function buildGroups(rest) {
    var out = [];
    var ev = App.state.eventId ? App.eventById(App.state.eventId) : null;
    var placed = {};
    if (ev) {
      var evl = ev.layers || {};
      EVENT_GROUPS.forEach(function (g) {
        var ids = Array.isArray(evl[g]) ? evl[g] : [];
        var items = [];
        ids.forEach(function (id) {
          var l = rest.filter(function (x) { return x.id === id; })[0];
          if (l && !placed[id]) { items.push(l); placed[id] = true; }
        });
        items = byTypeThenKeep(items);
        if (items.length) out.push(section(T('layers.group.' + g), rangeText(items), items.map(anyRow)));
      });
    }
    var remaining = rest.filter(function (l) { return !placed[l.id]; });
    TYPE_ORDER.forEach(function (t) {
      var items = remaining.filter(function (l) { return (TYPE_ORDER.indexOf(l.type) < 0 ? 'reference' : l.type) === t; });
      if (!items.length) return;
      out.push(section(T('layers.type.' + t), null, items.map(anyRow)));
    });
    return out;
  }

  function comingNext(list) {
    var items = [];
    (App.manifest.coming_next || []).forEach(function (c) { items.push(c.name || c.id); });
    list.filter(isComing).forEach(function (l) { items.push(l.name || l.id); });
    if (!items.length) return null;
    var sec = el('section', 'lsec lsec--next');
    var h = el('div', 'lsec__head');
    h.appendChild(el('h3', 'lsec__title', T('layers.coming_next')));
    sec.appendChild(h);
    var ul = el('ul', 'lnext');
    items.forEach(function (name) {
      var li = el('li', 'lnext__item');
      li.appendChild(el('span', 'lnext__name', name));
      li.appendChild(el('span', 'chip lnext__chip', T('layers.not_built')));
      ul.appendChild(li);
    });
    sec.appendChild(ul);
    return sec;
  }

  /* ---------- render ---------- */
  function render() {
    if (!root || !App.manifest) return;
    // preserve focus + scroll
    var active = document.activeElement;
    var fk = null;
    if (active && root.contains(active)) {
      if (active.getAttribute('data-lid')) fk = ['data-lid', active.getAttribute('data-lid')];
      else if (active.getAttribute('data-chev')) fk = ['data-chev', active.getAttribute('data-chev')];
      else if (active.getAttribute('data-oplid')) fk = ['data-oplid', active.getAttribute('data-oplid')];
    }
    var scroll = body ? body.scrollTop : 0;

    var list = currentLayers();
    var on = list.filter(function (l) { return isToggle(l) && !isUnavailable(l) && App.state.layersOn.has(l.id); });
    var onIds = {}; on.forEach(function (l) { onIds[l.id] = true; });
    var rest = list.filter(function (l) { return !isComing(l) && !onIds[l.id]; });

    body.textContent = '';
    if (on.length) {
      var s = el('section', 'lsec lsec--now');
      var h = el('div', 'lsec__head');
      h.appendChild(el('h3', 'lsec__title', T('layers.on_now')));
      h.appendChild(el('span', 'mono lsec__sub', T('layers.n_layers', { n: on.length })));
      s.appendChild(h);
      on.forEach(function (l) { s.appendChild(onNowRow(l)); });
      body.appendChild(s);
    }
    var groups = buildGroups(rest);
    groups.forEach(function (g) { body.appendChild(g); });
    if (!on.length && !groups.length) body.appendChild(el('p', 'lempty', T('layers.empty')));
    var nxt = comingNext(list);
    if (nxt) body.appendChild(nxt);

    body.scrollTop = scroll;
    if (fk) {
      var t = body.querySelector('[' + fk[0] + '="' + fk[1].replace(/"/g, '\\"') + '"]');
      if (t) { try { t.focus({ preventScroll: true }); } catch (e) { t.focus(); } }
    }
    lastSig = sortedIds(App.state.layersOn) + '#' + (App.state.eventId || '') + '#' + (App.state.region || '');
  }

  function renderShell() {
    root.textContent = '';
    root.setAttribute('aria-label', T('layers.title'));
    var handle = el('div', 'drawer__handle');
    handle.setAttribute('aria-hidden', 'true');
    handle.appendChild(el('span', 'drawer__grip'));
    root.appendChild(handle);
    wireDrag(handle);

    var head = el('div', 'drawer__head');
    var titles = el('div', 'drawer__titles');
    titles.appendChild(el('h2', 'drawer__title', T('layers.title')));
    titles.appendChild(el('span', 'drawer__sub', T('layers.subtitle')));
    head.appendChild(titles);
    var close = el('button', 'drawer__close');
    close.type = 'button';
    close.setAttribute('aria-label', T('layers.close'));
    close.appendChild(svg('M6 6l12 12M18 6L6 18', 22));
    close.addEventListener('click', function () { api.close(); });
    head.appendChild(close);
    root.appendChild(head);

    var legend = el('div', 'drawer__legend');
    legend.setAttribute('role', 'group');
    legend.setAttribute('aria-label', T('layers.legend_label'));
    legend.appendChild(el('span', 'chip chip--nisar', T('layers.chip.nisar')));
    legend.appendChild(el('span', 'drawer__legtxt', T('layers.type.nisar_sub')));
    legend.appendChild(el('span', 'chip chip--context drawer__ctxchip', T('layers.chip.context')));
    legend.appendChild(el('span', 'drawer__legtxt', T('layers.legend.context').replace(/^=\s*/, '')));
    root.appendChild(legend);

    body = el('div', 'drawer__body');
    root.appendChild(body);
    render();
  }

  /* phone: drag the grip down to close */
  function wireDrag(handle) {
    var y0 = null;
    handle.addEventListener('pointerdown', function (e) {
      if (!mqPhone.matches) return;
      y0 = e.clientY;
      try { handle.setPointerCapture(e.pointerId); } catch (x) { /* ignore */ }
    });
    handle.addEventListener('pointermove', function (e) {
      if (y0 == null) return;
      var dy = Math.max(0, e.clientY - y0);
      root.style.transform = 'translateY(' + dy + 'px)';
    });
    function end(e) {
      if (y0 == null) return;
      var dy = e.clientY - y0;
      y0 = null;
      root.style.transform = '';
      if (dy > 80) api.close();
    }
    handle.addEventListener('pointerup', end);
    handle.addEventListener('pointercancel', function () { y0 = null; root.style.transform = ''; });
  }

  /* ---------- open / close ---------- */
  function focusables() {
    return Array.prototype.slice.call(root.querySelectorAll(
      'button:not([disabled]), a[href], input:not([disabled]), select, [tabindex]:not([tabindex="-1"])'))
      .filter(function (n) { return !n.closest('[hidden]') && n.offsetParent !== null; });
  }
  function onKey(e) {
    if (!opened) return;
    if (e.key === 'Escape') { e.preventDefault(); api.close(true); return; }
    if (e.key === 'Tab' && mqPhone.matches) {
      var f = focusables();
      if (!f.length) return;
      var first = f[0], last = f[f.length - 1];
      if (e.shiftKey && (document.activeElement === first || !root.contains(document.activeElement))) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && (document.activeElement === last || !root.contains(document.activeElement))) { e.preventDefault(); first.focus(); }
    }
  }
  function syncVisible() {
    if (!root) return;
    root.hidden = !opened;
    if (scrim) scrim.hidden = !opened;
    if (btn) btn.setAttribute('aria-expanded', opened ? 'true' : 'false');
    document.documentElement.classList.toggle('drawer-open', opened && mqPhone.matches);
  }

  var api = {
    init: function (el_) {
      root = el_ || document.getElementById('drawer');
      if (!root) return;
      btn = document.getElementById('layers-btn');
      root.classList.add('drawer');
      opened = false;
      scrim = document.createElement('div');
      scrim.className = 'drawer-scrim';
      scrim.hidden = true;
      scrim.addEventListener('click', function () { api.close(true); });
      root.parentNode.insertBefore(scrim, root);
      document.addEventListener('keydown', onKey);
      renderShell();
      syncVisible();

      App.on('manifest', function () { renderShell(); });
      App.on('region', function () { render(); });
      App.on('event', function () { render(); });
      App.on('lang', function () { renderShell(); });
      App.on('layers', function () {
        if (selfOpacity) return;
        var sig = sortedIds(App.state.layersOn) + '#' + (App.state.eventId || '') + '#' + (App.state.region || '');
        if (sig !== lastSig) { render(); return; }
        // same checked set: only sync slider values in place (keeps expanded details and drags intact)
        Array.prototype.forEach.call(root.querySelectorAll('input[data-oplid]'), function (inp) {
          var l = App.layerById(inp.getAttribute('data-oplid'));
          if (!l || document.activeElement === inp) return;
          inp.value = String(Math.round(opacityOf(l) * 100));
          if (inp.nextSibling) inp.nextSibling.textContent = inp.value + '%';
        });
      });
      var onMq = function () { syncVisible(); };
      if (mqPhone.addEventListener) mqPhone.addEventListener('change', onMq);
      else if (mqPhone.addListener) mqPhone.addListener(onMq);
    },
    open: function () {
      if (!root || opened) return;
      render();
      opened = true;
      lastFocusBeforeOpen = document.activeElement;
      syncVisible();
      var c = root.querySelector('.drawer__close');
      if (c) c.focus();
    },
    close: function (restoreFocus) {
      if (!root || !opened) return;
      opened = false;
      syncVisible();
      root.style.transform = '';
      var target = btn || lastFocusBeforeOpen;
      if (target && typeof target.focus === 'function') target.focus();
    },
    toggle: function () { if (opened) api.close(); else api.open(); },
    isOpen: function () { return opened; }
  };

  App.layers = api;
})();
