/* brief.js: one-page A4 mandal brief. Classic script. Defines App.brief = { init(rootEl), open(mandalName|null), close(), print() }.
   Preview: full-screen overlay inside #brief-root (scrim, toolbar, page scaled to the screen width).
   Print: brief.css prints only the .brief-page as one A4 sheet.
   Reads only through App (state, manifest, lookups, fetchJSON, assetUrl, map.exportCurrentView).
   Never invents numbers: when the ranking cannot be loaded the page shows the unavailable text and no figures. */
(function () {
  'use strict';

  var App = window.App;
  if (!App) { console.error('[brief] App missing (load core.js first)'); return; }

  App.addStrings('en', {
    'brief.print_btn': 'Print / Save as PDF',
    'brief.nisar_chip': 'NISAR L-band',
    'brief.lbl_water': 'new open water',
    'brief.lbl_crops': 'wet or flooded crops',
    'brief.lbl_total': 'new water or wet crops',
    'brief.pm': '±{n}',
    'brief.map_caption': 'NISAR L-band · T{track} F{frame} · {pol} · {date}',
    'brief.layer_caption': '{name} · {date}',
    'brief.no_layer': 'no radar layer on',
    'brief.no_outline': 'Mandal outline not available',
    'brief.radar_sample': 'Radar image is a quick-look sample',
    'brief.map_label': 'Map crop around {mandal}',
    'brief.period_line': 'Selected period {from} → {to} vs normal period {a} → {b}',
    'brief.what_is_body_plain': 'A cloud-free radar look at the ground for the selected period. A shortlist of where to look first.',
    'brief.unavailable': 'Ranking unavailable. The numbers are left out of this page.',
    'brief.no_numbers': 'No numbers for this mandal in this analysis',
    'brief.lineage_none': 'No NISAR scenes are listed for this period',
    'brief.lineage_row': '{name} · {date} · {provider} · {credit}',
    'brief.lineage_row_short': '{name} · {date} · {provider}',
    'brief.lineage_item': '{name} · {date}',
    'brief.lineage_source': '{label} · {provider}',
    'brief.lineage_source_credit': '{label} · {provider} · {credit}',
    'brief.lineage.derived': 'Derived from NISAR',
    'brief.table_label': 'Neighbouring mandals in rank order'
  });

  var PAGE_W = 794, GUTTER = 16, WINDOW_AROUND = 3, MAX_PCT = 40;
  var SVGNS = 'http://www.w3.org/2000/svg';
  var T = function (k, v) { return App.t(k, v); };

  var root = null, scrim = null, stage = null, page = null, btnPrint = null, btnClose = null;
  var isOpen = false, token = 0, lastFocus = null, savedOverflow = '', lastName = null, lastCtx = null;
  var rankCache = {}, geoPromise = null;

  /* ---------------- DOM helpers ---------------- */
  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = String(text);
    return n;
  }
  function sv(tag, attrs, cls) {
    var n = document.createElementNS(SVGNS, tag);
    Object.keys(attrs || {}).forEach(function (k) { n.setAttribute(k, String(attrs[k])); });
    if (cls) n.setAttribute('class', cls);
    return n;
  }
  function clear(n) { while (n.firstChild) n.removeChild(n.firstChild); }
  function num(v) { var n = parseFloat(v); return isNaN(n) ? 0 : n; }
  function pct(v) { return Math.round(v) + '%'; }
  function pos(v, max) { return (v / max * 100) + '%'; }

  /* ---------------- data ---------------- */
  function normRows(data) {
    var rows = Array.isArray(data) ? data : (data && Array.isArray(data.rows) ? data.rows : []);
    return rows.map(function (r, i) {
      return {
        mandal: String(r.mandal != null ? r.mandal : (r.name || '')),
        district: r.district == null ? null : String(r.district),
        water: num(r.water_pct), we: num(r.water_err),
        crops: num(r.crops_pct), ce: num(r.crops_err),
        normal: r.normal_pct == null ? null : num(r.normal_pct),
        rank0: r.rank != null ? num(r.rank) : i + 1
      };
    }).filter(function (r) { return r.mandal; });
  }

  /* same rules as the ranking card: rows of the region's districts, ranks renumbered,
     total = water + crops, err = round(sqrt(water_err^2 + crops_err^2)) */
  function regionRows(rows) {
    var reg = App.regionById(App.state.region);
    var ds = reg && reg.districts && reg.districts.length ? reg.districts : null;
    return rows
      .filter(function (r) { return !ds || (r.district && ds.indexOf(r.district) >= 0); })
      .sort(function (x, y) { return x.rank0 - y.rank0; })
      .map(function (r, i) {
        return Object.assign({}, r, {
          rank: i + 1,
          total: r.water + r.crops,
          err: Math.round(Math.sqrt(r.we * r.we + r.ce * r.ce))
        });
      });
  }

  function findRow(rows, name) {
    if (!name) return null;
    var i, l = String(name).toLowerCase();
    for (i = 0; i < rows.length; i++) if (rows[i].mandal === name) return rows[i];
    for (i = 0; i < rows.length; i++) if (rows[i].mandal.toLowerCase() === l) return rows[i];
    return null;
  }

  /* same choice as the ranking card: the event's analysis, else the closest region's analysis */
  function pickAnalysis() {
    var m = App.manifest, s = App.state;
    if (!m || !m.analyses || !m.analyses.length) return null;
    if (s.eventId) {
      var ev = App.eventById(s.eventId);
      if (ev && ev.analysis_id) { var ea = App.analysisById(ev.analysis_id); if (ea) return ea; }
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
      if (sc < bs) { best = a; bs = sc; }
    });
    return bs === Infinity ? null : best;
  }

  function loadRank(url) {
    if (!rankCache[url]) {
      rankCache[url] = App.fetchJSON(url, { fallbackLabel: 'ranking' }).then(function (r) {
        if (!r.ok || !r.data) { delete rankCache[url]; return { ok: false, rows: [], placeholder: false }; }
        var d = r.data;
        return {
          ok: true,
          rows: normRows(d),
          placeholder: !!(d && !Array.isArray(d) && d.placeholder && d.placeholder.is)
        };
      });
    }
    return rankCache[url];
  }

  function loadGeo() {
    var f = App.manifest && App.manifest.files && App.manifest.files.mandals;
    if (!f) return Promise.resolve(null);
    if (!geoPromise) {
      geoPromise = App.fetchJSON(App.assetUrl(f), { fallbackLabel: 'mandals' }).then(function (r) {
        var feats = r.ok && r.data && Array.isArray(r.data.features) ? r.data.features : null;
        if (!feats) geoPromise = null;
        return feats;
      });
    }
    return geoPromise;
  }

  /* the first radar image on screen right now (map.exportCurrentView) */
  function currentImage() {
    var ex = null;
    try { ex = App.map && typeof App.map.exportCurrentView === 'function' ? App.map.exportCurrentView() : null; }
    catch (e) { console.warn('[brief] map view unavailable', e); }
    if (!ex || !ex.imgUrls || !ex.imgUrls.length) return null;
    var it = ex.imgUrls[0];
    return { url: it.url, bounds: it.bounds, opacity: it.opacity, layer: App.layerById(it.id) };
  }

  function loadContext(name) {
    var a = pickAnalysis();
    var rankP = a && a.rank_file ? loadRank(App.assetUrl(a.rank_file)) : Promise.resolve(null);
    return Promise.all([rankP, loadGeo()]).then(function (res) {
      var rank = res[0];
      var rows = rank && rank.ok ? regionRows(rank.rows) : [];
      var mandal = name || App.state.mandal || (rows[0] ? rows[0].mandal : null);
      return {
        analysis: a,
        rank: rank,
        rows: rows,
        mandal: mandal,
        sel: findRow(rows, mandal),
        feats: res[1],
        img: currentImage(),
        sample: !!((a && a.placeholder && a.placeholder.is) || (rank && rank.placeholder))
      };
    });
  }

  /* NISAR layers used: scenes inside the selected period, baseline inside the normal period, class maps */
  function lineage(a) {
    var out = { scenes: [], baseline: [], derived: [] };
    if (!a || !App.manifest) return out;
    var p = a.period || null, n = a.normal_period || null, cls = a.class_layers || [];
    App.manifest.layers.forEach(function (l) {
      if (cls.indexOf(l.id) >= 0) { out.derived.push(l); return; }
      if (l.type !== 'nisar' || !l.date) return;
      if (p && l.date >= p[0] && l.date <= p[1]) out.scenes.push(l);
      else if (n && l.date >= n[0] && l.date <= n[1]) out.baseline.push(l);
    });
    function byDate(x, y) {
      return String(x.date).localeCompare(String(y.date)) || String(x.name || '').localeCompare(String(y.name || ''));
    }
    out.scenes.sort(byDate); out.baseline.sort(byDate); out.derived.sort(byDate);
    return out;
  }

  function sourceOf(l) {
    var src = (App.manifest.sources || []).filter(function (s) { return s.id === l.source_id; })[0] || null;
    var provider = (src && src.provider) || l.source_id || '';
    var credit = l.credit || (src && src.credit_line) || '';
    return { provider: provider, credit: credit && credit !== provider ? credit : '' };
  }

  /* ---------------- geometry (lon/lat, lon scaled by cos(lat)) ---------------- */
  function rings(geom) {
    var out = [];
    if (!geom || !geom.coordinates) return out;
    if (geom.type === 'Polygon') geom.coordinates.forEach(function (r) { out.push(r); });
    else if (geom.type === 'MultiPolygon') geom.coordinates.forEach(function (p) { p.forEach(function (r) { out.push(r); }); });
    return out;
  }

  function bboxOf(rs) {
    var b = null;
    rs.forEach(function (r) {
      r.forEach(function (p) {
        if (!b) b = { minLon: p[0], maxLon: p[0], minLat: p[1], maxLat: p[1] };
        else {
          b.minLon = Math.min(b.minLon, p[0]); b.maxLon = Math.max(b.maxLon, p[0]);
          b.minLat = Math.min(b.minLat, p[1]); b.maxLat = Math.max(b.maxLat, p[1]);
        }
      });
    });
    return b;
  }

  function pathD(rs, c) {
    return rs.map(function (r) {
      return 'M' + r.map(function (p) { return (p[0] * c).toFixed(5) + ' ' + (-p[1]).toFixed(5); }).join(' L') + ' Z';
    }).join(' ');
  }

  function findFeat(feats, name) {
    if (!feats || !name) return null;
    var i, l = String(name).toLowerCase();
    for (i = 0; i < feats.length; i++) if ((feats[i].properties || {}).name === name) return feats[i];
    for (i = 0; i < feats.length; i++) if (String((feats[i].properties || {}).name || '').toLowerCase() === l) return feats[i];
    return null;
  }

  /* SVG crop: viewBox = mandal bbox padded 30%; radar image drawn with its bounds; outlines on top */
  function buildMap(ctx) {
    var feat = findFeat(ctx.feats, ctx.mandal);
    if (!feat) return null;
    var own = rings(feat.geometry), b = bboxOf(own);
    if (!b) return null;
    var c = Math.cos(((b.minLat + b.maxLat) / 2) * Math.PI / 180);
    var w = (b.maxLon - b.minLon) * c, h = b.maxLat - b.minLat;
    var pad = 0.3 * Math.max(w, h);
    var vb = [b.minLon * c - pad, -b.maxLat - pad, w + 2 * pad, h + 2 * pad].map(function (v) { return v.toFixed(5); });
    var svg = sv('svg', {
      viewBox: vb.join(' '),
      preserveAspectRatio: 'xMidYMid meet',
      role: 'img',
      'aria-label': T('brief.map_label', { mandal: ctx.mandal })
    });
    if (ctx.img && ctx.img.bounds) {
      var bd = ctx.img.bounds;                       // [[S, W], [N, E]]
      svg.appendChild(sv('image', {
        href: ctx.img.url,
        x: bd[0][1] * c, y: -bd[1][0],
        width: (bd[1][1] - bd[0][1]) * c, height: bd[1][0] - bd[0][0],
        preserveAspectRatio: 'none',
        opacity: ctx.img.opacity != null ? ctx.img.opacity : 0.85
      }));
    }
    var padLon = pad / c, padLat = pad;
    (ctx.feats || []).forEach(function (f) {
      if (f === feat) return;
      var rs = rings(f.geometry), bb = bboxOf(rs);
      if (!bb) return;
      if (bb.maxLat < b.minLat - padLat || bb.minLat > b.maxLat + padLat ||
          bb.maxLon < b.minLon - padLon || bb.minLon > b.maxLon + padLon) return;
      svg.appendChild(sv('path', { d: pathD(rs, c) }, 'brief-map__nb'));
    });
    svg.appendChild(sv('path', { d: pathD(own, c) }, 'brief-map__halo'));
    svg.appendChild(sv('path', { d: pathD(own, c) }, 'brief-map__mandal'));
    return svg;
  }

  function logo() {
    var s = sv('svg', { width: 24, height: 24, viewBox: '0 0 28 28', 'aria-hidden': 'true' }, 'brief-logo');
    s.appendChild(sv('circle', { cx: 14, cy: 14, r: 12, 'stroke-dasharray': '52 8' }, 'brief-logo__ring'));
    s.appendChild(sv('circle', { cx: 14, cy: 14, r: 6.5, 'stroke-dasharray': '26 6' }, 'brief-logo__ring'));
    s.appendChild(sv('circle', { cx: 14, cy: 14, r: 2 }, 'brief-logo__eye'));
    return s;
  }

  /* ---------------- page pieces ---------------- */
  function stat(kind, num, pm, label) {
    var d = el('div', 'brief-stat brief-stat--' + kind);
    var n = el('div', 'brief-stat__num', num);
    if (pm) { n.appendChild(document.createTextNode(' ')); n.appendChild(el('span', 'brief-stat__pm', pm)); }
    d.appendChild(n);
    d.appendChild(el('div', 'brief-stat__label', label));
    return d;
  }

  function unavailableText(ctx) {
    if (!ctx.analysis) return T('state.no_analysis');
    if (ctx.rank && !ctx.rank.ok) return T('brief.unavailable');
    if (!ctx.mandal) return T('brief.pick_mandal');
    return T('brief.no_numbers');
  }

  function legend() {
    var l = el('div', 'brief-legend');
    function item(node, text) {
      var s = el('span', 'brief-legend__item');
      s.appendChild(node);
      s.appendChild(document.createTextNode(text));
      return s;
    }
    l.appendChild(item(el('span', 'brief-sq brief-sq--water'), T('brief.legend.water')));
    l.appendChild(item(el('span', 'brief-sq brief-sq--crops'), T('brief.crops')));
    l.appendChild(item(el('span', 'brief-legend__tick'), T('brief.legend.normal')));
    var wh = sv('svg', { width: 20, height: 10, viewBox: '0 0 20 10', 'aria-hidden': 'true' });
    wh.appendChild(sv('path', { d: 'M1.5 1v8M18.5 1v8M1.5 5h17' }, 'brief-legend__whisk'));
    l.appendChild(item(wh, T('brief.legend.err')));
    return l;
  }

  function nbRow(r, isSel, max) {
    var row = el('div', 'brief-nb' + (isSel ? ' brief-nb--sel' : ''));
    row.setAttribute('role', 'listitem');
    row.appendChild(el('span', 'brief-nb__rank', String(r.rank)));
    row.appendChild(el('span', 'brief-nb__name', r.mandal));
    var tr = el('span', 'brief-track');
    function seg(cls, styles) {
      var s = el('span', cls);
      Object.keys(styles).forEach(function (k) { s.style[k] = styles[k]; });
      tr.appendChild(s);
    }
    var lo = Math.max(0, r.total - r.err), hi = Math.min(max, r.total + r.err);
    seg('brief-track__water', { left: '0', width: pos(r.water, max) });
    seg('brief-track__crops', { left: pos(r.water, max), width: pos(r.crops, max) });
    seg('brief-track__whisk', { left: pos(lo, max), width: pos(hi - lo, max) });
    seg('brief-track__cap', { left: pos(lo, max) });
    seg('brief-track__cap brief-track__cap--r', { left: pos(hi, max) });
    if (r.normal != null) seg('brief-track__tick', { left: pos(r.normal, max) });
    row.appendChild(tr);
    var tot = el('span', 'brief-nb__total');
    tot.appendChild(el('span', 'brief-nb__pct', pct(r.total)));
    tot.appendChild(document.createTextNode(' '));
    tot.appendChild(el('span', 'brief-nb__err', T('brief.pm', { n: r.err })));
    row.appendChild(tot);
    return row;
  }

  function neighbourTable(ctx) {
    var rows = ctx.rows, idx = rows.indexOf(ctx.sel);
    var win = rows.slice(Math.max(0, idx - WINDOW_AROUND), Math.min(rows.length, idx + WINDOW_AROUND + 1));
    var max = MAX_PCT;
    win.forEach(function (r) { max = Math.max(max, r.total + r.err); });
    var list = el('div', 'brief-nb-list');
    list.setAttribute('role', 'list');
    list.setAttribute('aria-label', T('brief.table_label'));
    win.forEach(function (r) { list.appendChild(nbRow(r, r === ctx.sel, max)); });
    return list;
  }

  function noteBox(head, body) {
    var d = el('div', 'brief-note');
    d.appendChild(el('h2', 'brief-h2 brief-note__h', head));
    d.appendChild(el('p', 'brief-note__body', body));
    return d;
  }

  /* one group of layers: the shared source is printed once; rows keep name and date.
     Falls back to a full row per layer when the sources differ inside the group. */
  function lineGroup(label, list) {
    var g = el('div', 'brief-foot__group');
    var first = sourceOf(list[0]);
    var same = list.every(function (l) {
      var s = sourceOf(l);
      return s.provider === first.provider && s.credit === first.credit;
    });
    if (same) {
      var vars = { label: label, provider: first.provider, credit: first.credit };
      g.appendChild(el('div', 'brief-foot__row brief-foot__row--head',
        first.credit ? T('brief.lineage_source_credit', vars) : T('brief.lineage_source', vars)));
      list.forEach(function (l) {
        g.appendChild(el('div', 'brief-foot__row', T('brief.lineage_item', { name: l.name || l.id, date: App.fmt.date(l.date) })));
      });
    } else {
      g.appendChild(el('span', 'brief-foot__label', label));
      list.forEach(function (l) {
        var s = sourceOf(l);
        var vars = { name: l.name || l.id, date: App.fmt.date(l.date), provider: s.provider };
        g.appendChild(el('div', 'brief-foot__row', s.credit
          ? T('brief.lineage_row', Object.assign({ credit: s.credit }, vars))
          : T('brief.lineage_row_short', vars)));
      });
    }
    return g;
  }

  /* ---------------- render ---------------- */
  function renderPage(ctx) {
    clear(page);
    var a = ctx.analysis, p = a && a.period && a.period.length === 2 ? a.period : null;
    var n = a && a.normal_period && a.normal_period.length === 2 ? a.normal_period : null;
    var sel = ctx.sel;

    /* header: app name and generation stamp */
    var head = el('header', 'brief-head');
    var brand = el('span', 'brief-brand');
    brand.appendChild(logo());
    brand.appendChild(el('span', 'brief-brand__name', App.t('app.name')));
    head.appendChild(brand);
    head.appendChild(el('span', 'brief-gen', T('brief.generated', {
      date: App.fmt.dateTime(new Date().toISOString(), 'IST'),
      url: location.host || 'SpaceBros'
    })));
    page.appendChild(head);

    /* title block */
    var tb = el('div', 'brief-title');
    tb.appendChild(el('h1', 'brief-title__name', ctx.mandal || T('brief.pick_mandal')));
    if (p && n) {
      tb.appendChild(el('p', 'brief-title__period', T('brief.period_line', {
        from: App.fmt.date(p[0], { year: false }), to: App.fmt.date(p[1]),
        a: App.fmt.date(n[0], { year: false }), b: App.fmt.date(n[1])
      })));
    }
    var chips = el('div', 'brief-chips');
    chips.appendChild(el('span', 'chip chip--nisar', T('brief.nisar_chip')));
    if (ctx.sample) chips.appendChild(el('span', 'tag-sample', T('brief.sample')));
    if (sel && sel.district) chips.appendChild(el('span', 'brief-title__sub', sel.district));
    tb.appendChild(chips);
    page.appendChild(tb);

    /* map column and numbers column */
    var grid = el('div', 'brief-grid');
    var col1 = el('div', 'brief-mapcol');
    var mapBox = el('div', 'brief-map');
    var svg = buildMap(ctx);
    if (svg) mapBox.appendChild(svg);
    else mapBox.appendChild(el('p', 'brief-map__empty', T('brief.no_outline')));
    if (ctx.mandal) mapBox.appendChild(el('span', 'brief-map__label', ctx.mandal));
    col1.appendChild(mapBox);

    var lay = ctx.img && ctx.img.layer;
    var cap = el('p', 'brief-caption');
    if (lay && lay.track != null) {
      cap.textContent = T('brief.map_caption', { track: lay.track, frame: lay.frame, pol: lay.pol || '', date: App.fmt.date(lay.date) });
    } else if (lay) {
      cap.textContent = T('brief.layer_caption', { name: lay.name || lay.id, date: App.fmt.date(lay.date) });
    } else {
      cap.textContent = T('brief.no_layer');
    }
    col1.appendChild(cap);
    if (lay && lay.placeholder && lay.placeholder.is) col1.appendChild(el('p', 'brief-caption', T('brief.radar_sample')));
    grid.appendChild(col1);

    var col2 = el('div', 'brief-stats');
    if (sel) {
      col2.appendChild(stat('water', pct(sel.water), T('brief.pm', { n: Math.round(sel.we) }), App.likely(T('brief.lbl_water'))));
      col2.appendChild(stat('crops', pct(sel.crops), T('brief.pm', { n: Math.round(sel.ce) }), App.likely(T('brief.lbl_crops'))));
      col2.appendChild(stat('total', pct(sel.total), T('brief.pm', { n: sel.err }), App.likely(T('brief.lbl_total'))));
      if (sel.normal != null) col2.appendChild(stat('normal', pct(sel.normal), '', T('brief.normal')));
      col2.appendChild(el('p', 'brief-rankline', T('brief.rank', { rank: sel.rank, n: ctx.rows.length })));
    } else {
      col2.appendChild(el('p', 'brief-unavail', unavailableText(ctx)));
    }
    grid.appendChild(col2);
    page.appendChild(grid);

    /* neighbours */
    var nb = el('section', 'brief-box');
    var hd = el('div', 'brief-box__head');
    hd.appendChild(el('h2', 'brief-h2', T('brief.compared')));
    if (p) hd.appendChild(el('span', 'brief-box__meta', T('brief.share', { date: App.fmt.date(p[1]) })));
    nb.appendChild(hd);
    nb.appendChild(legend());
    if (sel) nb.appendChild(neighbourTable(ctx));
    page.appendChild(nb);

    /* what this is / is not */
    var pair = el('div', 'brief-pair');
    pair.appendChild(noteBox(T('brief.what_is'), T('brief.what_is_body_plain')));
    pair.appendChild(noteBox(T('brief.what_is_not'), T('brief.what_is_not_body')));
    page.appendChild(pair);

    /* data lineage */
    var L = lineage(a);
    var foot = el('footer', 'brief-foot');
    foot.appendChild(el('div', 'brief-foot__title', T('brief.lineage')));
    if (!L.scenes.length && !L.baseline.length && !L.derived.length) {
      foot.appendChild(el('div', 'brief-foot__row', T('brief.lineage_none')));
    }
    var cells = el('div', 'brief-foot__cells');
    if (L.scenes.length) cells.appendChild(lineGroup(T('brief.lineage.scenes'), L.scenes));
    if (L.baseline.length) cells.appendChild(lineGroup(T('brief.lineage.baseline'), L.baseline));
    if (L.derived.length) cells.appendChild(lineGroup(T('brief.lineage.derived'), L.derived));
    var meth = el('div', 'brief-foot__group');
    meth.appendChild(el('span', 'brief-foot__label', T('brief.lineage.method')));
    meth.appendChild(el('div', 'brief-foot__row', T('brief.lineage.method_value')));
    cells.appendChild(meth);
    foot.appendChild(cells);
    foot.appendChild(el('div', 'brief-foot__note', T('brief.footer')));
    page.appendChild(foot);

    if (scrim) scrim.setAttribute('aria-label', T('brief.title', { mandal: ctx.mandal || '' }));
  }

  function setLoading() {
    clear(page);
    page.appendChild(el('p', 'brief-loading', T('common.loading')));
  }

  /* ---------------- overlay ---------------- */
  function fit() {
    if (!root || !stage) return;
    var w = stage.clientWidth - 2 * GUTTER;
    var s = w > 0 ? Math.min(1, w / PAGE_W) : 1;
    root.style.setProperty('--brief-scale', String(s));
  }

  function buildChrome() {
    scrim = el('div', 'brief-scrim');
    scrim.setAttribute('role', 'dialog');
    scrim.setAttribute('aria-modal', 'true');
    var bar = el('div', 'brief-toolbar');
    btnPrint = el('button', 'brief-btn brief-btn--primary', T('brief.print_btn'));
    btnPrint.type = 'button';
    btnPrint.addEventListener('click', print);
    btnClose = el('button', 'brief-btn', T('common.close'));
    btnClose.type = 'button';
    btnClose.addEventListener('click', close);
    bar.appendChild(btnPrint);
    bar.appendChild(btnClose);
    stage = el('div', 'brief-stage');
    page = el('article', 'brief-page');
    stage.appendChild(page);
    scrim.appendChild(bar);
    scrim.appendChild(stage);
    scrim.addEventListener('click', function (e) { if (e.target === scrim || e.target === stage) close(); });
    root.appendChild(scrim);
  }

  function onKey(e) {
    if (!isOpen) return;
    if (e.key === 'Escape') { e.preventDefault(); close(); return; }
    if (e.key === 'Tab') {
      /* the only controls are the two toolbar buttons: keep focus between them */
      var active = document.activeElement;
      if (e.shiftKey && active === btnPrint) { e.preventDefault(); btnClose.focus(); }
      else if (!e.shiftKey && active === btnClose) { e.preventDefault(); btnPrint.focus(); }
    }
  }

  function init(rootEl) {
    if (!rootEl) { console.warn('[brief] no root element'); return; }
    if (root === rootEl) return;
    root = rootEl;
    root.hidden = true;
    buildChrome();
    document.addEventListener('keydown', onKey);
    window.addEventListener('resize', fit);
    App.on('lang', function () {
      if (!root) return;
      btnPrint.textContent = T('brief.print_btn');
      btnClose.textContent = T('common.close');
      if (isOpen && lastCtx) renderPage(lastCtx);
    });
  }

  function open(name) {
    if (!root) { console.warn('[brief] open() before init()'); return; }
    if (!isOpen) {
      lastFocus = document.activeElement;
      savedOverflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
    }
    isOpen = true;
    root.hidden = false;
    fit();
    lastName = name || null;
    var my = ++token;
    setLoading();
    btnPrint.focus();
    loadContext(lastName).then(function (ctx) {
      if (my !== token || !isOpen) return;
      lastCtx = ctx;
      renderPage(ctx);
    });
  }

  function close() {
    if (!isOpen) return;
    isOpen = false;
    token++;
    root.hidden = true;
    document.body.style.overflow = savedOverflow;
    if (lastFocus && typeof lastFocus.focus === 'function') lastFocus.focus();
    lastFocus = null;
  }

  function print() {
    try { window.print(); } catch (e) { console.warn('[brief] print failed', e); }
  }

  App.brief = { init: init, open: open, close: close, print: print };
})();
