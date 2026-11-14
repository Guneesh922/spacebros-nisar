/* core.js: window.App contract (docs/FRONTEND_BUILD_PLAN.md section 4).
   State, event bus, manifest loader (schema v2, v1 tolerated), strings, fetch with fallback,
   formatters and lookup helpers. No dates, tracks or landfall times are hard-coded here.

   Optional config, set BEFORE this script:
     window.APP_CONFIG = {
       repoBase:     '../',                                   // prefix for repo-root-relative paths in the manifest
       manifestUrl:  '../data/processed/manifest.json',       // default: repoBase + 'data/processed/manifest.json'
       stringsBase:  'strings/',                              // folder of strings.<lang>.json
       extraStrings: ['case'],                                // optional extra files: <name>.<lang>.json (missing = ignored)
       lang:         'en',
       timeoutMs:    8000
     };
*/
(function () {
  'use strict';

  var CFG = Object.assign({
    repoBase: '../',
    manifestUrl: null,
    stringsBase: 'strings/',
    extraStrings: ['case'],
    lang: null,
    timeoutMs: 8000
  }, window.APP_CONFIG || {});
  if (!CFG.manifestUrl) CFG.manifestUrl = CFG.repoBase + 'data/processed/manifest.json';

  var TYPE_ORDER = ['nisar', 'derived', 'optical', 'weather', 'reference', 'alerts'];
  var CHIP_TO_TYPE = { nisar: 'nisar', context: 'optical', model: 'weather', reference: 'reference' };
  var KNOWN_STATUS = { ready: 1, coming_next: 1, link_only: 1, unavailable: 1 };

  var App = {};
  window.App = App;
  App.config = CFG;

  /* ---------------- event bus ---------------- */
  var handlers = {};
  App.on = function (evt, fn) { (handlers[evt] = handlers[evt] || []).push(fn); return App; };
  App.off = function (evt, fn) {
    if (!handlers[evt]) return App;
    handlers[evt] = fn ? handlers[evt].filter(function (h) { return h !== fn; }) : [];
    return App;
  };
  App.emit = function (evt, payload) {
    (handlers[evt] || []).slice().forEach(function (fn) {
      try { fn(payload, evt); } catch (e) { console.error('[App] handler for "' + evt + '" threw', e); }
    });
    return App;
  };

  /* ---------------- state ---------------- */
  App.state = {
    region: null,
    view: 'workspace',          // workspace | events | case
    eventId: null,
    date: null,                 // ISO or null = latest
    range: null,                // [from,to] or null
    layersOn: new Set(),
    opacity: {},
    band: 'L',
    compare: { on: false, a: null, b: null },
    classesOn: new Set(),
    mandal: null,
    lang: 'en'
  };

  function sameSet(a, b) {
    if (a === b) return true;
    if (!(a instanceof Set) || !(b instanceof Set) || a.size !== b.size) return false;
    var ok = true; a.forEach(function (v) { if (!b.has(v)) ok = false; });
    return ok;
  }
  function same(a, b) {
    if (a instanceof Set || b instanceof Set) return sameSet(a, b);
    if (a && b && typeof a === 'object' && typeof b === 'object') {
      try { return JSON.stringify(a) === JSON.stringify(b); } catch (e) { return false; }
    }
    return a === b;
  }

  /* setState(patch): merges, emits 'state' ({patch, changed, state}) and specific events:
     region(id) event(id|null) layers({layersOn,opacity,classesOn,band}) mandal(name|null)
     compare({on,a,b}) view(name). Only fires for keys that actually changed. */
  App.setState = function (patch) {
    var s = App.state, changed = [];
    patch = patch || {};
    Object.keys(patch).forEach(function (k) {
      var v = patch[k];
      if ((k === 'layersOn' || k === 'classesOn') && !(v instanceof Set)) v = new Set(v || []);
      if (k === 'compare') v = Object.assign({}, s.compare, v);
      if (k === 'opacity') v = Object.assign({}, s.opacity, v);
      if (!same(s[k], v)) { s[k] = v; changed.push(k); }
    });
    if (!changed.length) return changed;
    App.emit('state', { patch: patch, changed: changed, state: s });
    var has = function (k) { return changed.indexOf(k) >= 0; };
    if (has('region')) App.emit('region', s.region);
    if (has('eventId')) App.emit('event', s.eventId);
    if (has('layersOn') || has('opacity') || has('classesOn') || has('band') || has('date') || has('range')) {
      App.emit('layers', { layersOn: s.layersOn, opacity: s.opacity, classesOn: s.classesOn, band: s.band });
    }
    if (has('mandal')) App.emit('mandal', s.mandal);
    if (has('compare')) App.emit('compare', s.compare);
    if (has('view')) App.emit('view', s.view);
    return changed;
  };

  /* ---------------- strings ---------------- */
  var STR = {};            // { lang: { key: text } }
  App.t = function (key, vars) {
    var lang = App.state.lang;
    var txt = (STR[lang] && STR[lang][key]);
    if (txt == null && lang !== 'en') txt = STR.en && STR.en[key];
    if (txt == null) {
      console.warn('[App.t] missing string key: ' + key);
      return '⟨' + key + '⟩';
    }
    if (vars) {
      txt = String(txt).replace(/\{(\w+)\}/g, function (m, name) {
        return vars[name] != null ? vars[name] : m;
      });
    }
    return txt;
  };
  App.hasString = function (key) {
    var l = App.state.lang;
    return !!((STR[l] && STR[l][key] != null) || (STR.en && STR.en[key] != null));
  };
  App.addStrings = function (lang, obj) { STR[lang] = Object.assign(STR[lang] || {}, obj || {}); };

  /* Loads strings.<lang>.json plus extraStrings, for lang and (if different) en.
     Missing optional files are ignored. Returns a promise of true. */
  App.loadStrings = function (lang) {
    lang = lang || App.state.lang || 'en';
    var langs = lang === 'en' ? ['en'] : ['en', lang];
    var jobs = [];
    langs.forEach(function (lg) {
      ['strings'].concat(CFG.extraStrings || []).forEach(function (name) {
        var url = CFG.stringsBase + name + '.' + lg + '.json';
        jobs.push(App.fetchJSON(url).then(function (r) {
          if (r.ok && r.data && typeof r.data === 'object') App.addStrings(lg, r.data);
          else if (name === 'strings' && lg === 'en') console.warn('[App] could not load ' + url + ': ' + r.error);
        }));
      });
    });
    return Promise.all(jobs).then(function () { return true; });
  };
  App.setLang = function (lang) {
    return App.loadStrings(lang).then(function () {
      App.setState({ lang: lang });
      try { document.documentElement.lang = lang; } catch (e) { /* ignore */ }
      App.emit('lang', lang);
      return lang;
    });
  };

  /* ---------------- fetch with fallback ---------------- */
  var memLast = {};
  function lsKey(url) { return 'app.lastok:' + url; }
  App.lastKnown = function (url) {
    try {
      var v = window.localStorage.getItem(lsKey(url));
      if (v) return v;
    } catch (e) { /* storage blocked */ }
    return memLast[url] || null;
  };
  function remember(url, iso) {
    memLast[url] = iso;
    try { window.localStorage.setItem(lsKey(url), iso); } catch (e) { /* ignore */ }
  }

  /* Resolves {ok, data, error, fetchedAt, lastKnown, fallbackLabel}; NEVER rejects/throws. */
  App.fetchJSON = function (url, opts) {
    opts = opts || {};
    var timeoutMs = opts.timeoutMs != null ? opts.timeoutMs : CFG.timeoutMs;
    var label = opts.fallbackLabel || null;
    function fail(msg) {
      return { ok: false, data: null, error: String(msg), fetchedAt: null,
               lastKnown: App.lastKnown(url), fallbackLabel: label };
    }
    try {
      var ctl = (typeof AbortController !== 'undefined') ? new AbortController() : null;
      var timer = ctl ? setTimeout(function () { ctl.abort(); }, timeoutMs) : null;
      return fetch(url, ctl ? { signal: ctl.signal } : undefined).then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      }).then(function (data) {
        if (timer) clearTimeout(timer);
        var iso = new Date().toISOString();
        remember(url, iso);
        return { ok: true, data: data, error: null, fetchedAt: iso, lastKnown: iso, fallbackLabel: label };
      }).catch(function (e) {
        if (timer) clearTimeout(timer);
        return fail(e && e.name === 'AbortError' ? 'timeout after ' + timeoutMs + ' ms' : (e && e.message) || e);
      });
    } catch (e) {
      return Promise.resolve(fail(e && e.message || e));
    }
  };

  /* ---------------- formatters ---------------- */
  function toDate(iso) {
    if (iso instanceof Date) return iso;
    if (typeof iso === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(iso)) return new Date(iso + 'T00:00:00Z');
    return new Date(iso);
  }
  function parts(d, tz, withTime) {
    var o = { timeZone: tz, day: 'numeric', month: 'short', year: 'numeric' };
    if (withTime) { o.hour = '2-digit'; o.minute = '2-digit'; o.hour12 = false; }
    var map = {};
    new Intl.DateTimeFormat('en-GB', o).formatToParts(d).forEach(function (p) { map[p.type] = p.value; });
    return map;
  }
  App.fmt = {
    /* date('2026-11-09') -> '9 Nov 2026'; opts {year:false} -> '9 Nov'. Date-only strings are calendar dates (UTC). */
    date: function (iso, opts) {
      if (!iso) return '';
      var d = toDate(iso); if (isNaN(d)) return '';
      var p = parts(d, 'UTC', false);
      return p.day + ' ' + p.month + ((opts && opts.year === false) ? '' : ' ' + p.year);
    },
    /* dateTime(iso, tz): tz 'IST' (default) | 'UTC' | 'both'. -> '27 Oct 2026, 18:31 IST' */
    dateTime: function (iso, tz) {
      if (!iso) return '';
      var d = toDate(iso); if (isNaN(d)) return '';
      function one(zone, label) {
        var p = parts(d, zone, true);
        var hh = p.hour === '24' ? '00' : p.hour;
        return p.day + ' ' + p.month + ' ' + p.year + ', ' + hh + ':' + p.minute + ' ' + label;
      }
      tz = tz || 'IST';
      if (tz === 'UTC') return one('UTC', 'UTC');
      if (tz === 'both') return one('Asia/Kolkata', 'IST') + ' (' + one('UTC', 'UTC').split(', ')[1] + ')';
      return one('Asia/Kolkata', 'IST');
    },
    /* whole days between iso and now (or opts.now); never negative */
    ageDays: function (iso, now) {
      if (!iso) return null;
      var d = toDate(iso); if (isNaN(d)) return null;
      var n = now ? toDate(now) : new Date();
      return Math.max(0, Math.floor((n - d) / 86400000));
    },
    age: function (iso, now) {
      var n = App.fmt.ageDays(iso, now);
      if (n == null) return '';
      if (n === 0) return App.t('common.today');
      if (n === 1) return App.t('common.yesterday');
      return App.t('common.days_ago', { n: n });
    },
    pct: function (n) { return (n == null || isNaN(n)) ? '' : Math.round(n) + '%'; },
    pm: function (n) { return (n == null || isNaN(n)) ? '' : '±' + Math.round(n); }
  };

  /* "likely " prefix unless already present. Keeps acronyms (NISAR) as written. */
  App.likely = function (label) {
    label = String(label == null ? '' : label).trim();
    if (!label) return 'likely';
    if (/^likely\b/i.test(label)) return label.charAt(0).toLowerCase() + label.slice(1);
    var lowered = (label.length > 1 && label.charAt(1) === label.charAt(1).toUpperCase() && /[A-Z]/.test(label.charAt(1)))
      ? label : label.charAt(0).toLowerCase() + label.slice(1);
    return 'likely ' + lowered;
  };

  /* ---------------- manifest normalisation ---------------- */
  function arr(x) { return Array.isArray(x) ? x : []; }

  function normalise(m) {
    m = (m && typeof m === 'object') ? m : {};
    var out = Object.assign({}, m);
    out.schema_version = m.schema_version || 1;
    out.app = Object.assign({ default_region: null, default_lang: 'en', page_budget_mb: 15 }, m.app || {});
    out.regions = arr(m.regions).map(function (r) {
      return Object.assign({ default: false, bounds: null, districts: null, children: [], parent: null }, r);
    });
    out.sources = arr(m.sources);
    out.events = arr(m.events).map(function (e) {
      return Object.assign({ region: null, dates: {}, layers: {}, default_on: null, analysis_id: null,
                             track_geojson: null, landfall: null, case_study: false }, e);
    });
    out.analyses = arr(m.analyses);
    out.coming_next = arr(m.coming_next);
    out.files = Object.assign({}, m.files || {});
    out.generated_utc = m.generated_utc || null;

    if (!out.regions.length) {
      out.regions.push({ id: 'all', name: App.hasString('common.all_regions') ? App.t('common.all_regions') : 'All regions',
                         default: true, bounds: null, districts: null, children: [], parent: null });
    }
    if (!out.app.default_region) {
      var d = out.regions.filter(function (r) { return r.default; })[0] || out.regions[0];
      out.app.default_region = d.id;
    }

    var srcById = {};
    out.sources.forEach(function (s) { srcById[s.id] = s; });
    out.layers = arr(m.layers).map(function (l) {
      var o = Object.assign({
        kind: 'image', chip: 'context', date: null, latest_of: null, regions: null, event_id: null,
        classes: null, default_on: false, opacity: 0.85, bounds: null, png: null, placeholder: null
      }, l);
      if (!o.type) o.type = CHIP_TO_TYPE[o.chip] || 'optical';
      if (!o.status) o.status = (o.group === 'next') ? 'coming_next' : 'ready';
      if (!KNOWN_STATUS[o.status]) o.status = 'unavailable';
      var src = srcById[o.source_id];
      if (!o.credit && src) o.credit = src.credit_line || src.provider || null;
      if (o.placeholder && o.placeholder === true) o.placeholder = { is: true };
      return o;
    });
    return out;
  }

  /* ---------------- lookups ---------------- */
  var M = function () { return App.manifest || { layers: [], regions: [], events: [], analyses: [] }; };
  App.layerById = function (id) { return M().layers.filter(function (l) { return l.id === id; })[0] || null; };
  App.eventById = function (id) { return M().events.filter(function (e) { return e.id === id; })[0] || null; };
  App.regionById = function (id) { return M().regions.filter(function (r) { return r.id === id; })[0] || null; };
  App.analysisById = function (id) { return M().analyses.filter(function (a) { return a.id === id; })[0] || null; };

  /* region id plus all ancestors (child regions inherit layers offered on their parent) */
  App.regionChain = function (id) {
    var chain = [], seen = {}, r = App.regionById(id);
    while (r && !seen[r.id]) { chain.push(r.id); seen[r.id] = 1; r = r.parent ? App.regionById(r.parent) : null; }
    if (!chain.length && id) chain.push(id);
    return chain;
  };

  /* newest ready layer of a time series: layers whose latest_of === key (or id === key when no series) */
  App.latestFor = function (layerKey) {
    var c = M().layers.filter(function (l) {
      return l.status === 'ready' && (l.latest_of === layerKey || (!l.latest_of && l.id === layerKey));
    });
    c.sort(function (a, b) { return String(b.date || '').localeCompare(String(a.date || '')); });
    return c[0] || null;
  };

  /* layers offered for {region, eventId}. event_id layers only when that event is loaded;
     layer.regions honoured (null/empty = everywhere; parents count). NISAR type first. */
  App.layersFor = function (q) {
    q = q || {};
    var chain = q.region ? App.regionChain(q.region) : null;
    var list = M().layers.filter(function (l) {
      if (l.event_id && l.event_id !== q.eventId) return false;
      if (chain && l.regions && l.regions.length) {
        if (!l.regions.some(function (r) { return chain.indexOf(r) >= 0; })) return false;
      }
      return true;
    });
    function rank(l) { var i = TYPE_ORDER.indexOf(l.type); return i < 0 ? TYPE_ORDER.length : i; }
    return list.map(function (l, i) { return { l: l, i: i }; }).sort(function (a, b) {
      return (rank(a.l) - rank(b.l)) ||
             String(b.l.date || '').localeCompare(String(a.l.date || '')) ||
             (a.i - b.i);
    }).map(function (x) { return x.l; });
  };

  App.assetUrl = function (path) {
    if (!path) return null;
    if (/^(https?:)?\/\//.test(path) || path.charAt(0) === '/' || /^data:/.test(path)) return path;
    return CFG.repoBase + path;
  };

  /* ---------------- landing defaults and events ---------------- */
  function landingLayers(region) {
    return App.layersFor({ region: region, eventId: null })
      .filter(function (l) { return l.status === 'ready' && l.default_on; })
      .map(function (l) { return l.id; });
  }
  function opacityFor(ids) {
    var o = {};
    ids.forEach(function (id) { var l = App.layerById(id); if (l && l.opacity != null) o[id] = l.opacity; });
    return o;
  }

  App.applyEvent = function (id) {
    var ev = App.eventById(id);
    if (!ev) { console.warn('[App] unknown event ' + id); return false; }
    var region = ev.region || App.state.region;
    var ids = arr(ev.default_on).length ? ev.default_on.slice() : null;
    if (!ids) {
      ids = App.layersFor({ region: region, eventId: id })
        .filter(function (l) { return l.status === 'ready' && l.default_on; }).map(function (l) { return l.id; });
    }
    ids = ids.filter(function (x) { return !!App.layerById(x); });
    var d = ev.dates || {};
    var range = (d.before && d.after) ? [d.before, d.after] : (d.normal_period || null);
    App.setState({
      eventId: id, region: region, date: d.after || null, range: range,
      layersOn: new Set(ids), opacity: opacityFor(ids), mandal: null,
      compare: { on: false, a: null, b: null }, classesOn: new Set()
    });
    return true;
  };

  App.clearEvent = function () {
    var region = (M().app && M().app.default_region) || App.state.region;
    var ids = landingLayers(region);
    App.setState({
      eventId: null, region: region, date: null, range: null,
      layersOn: new Set(ids), opacity: opacityFor(ids), mandal: null,
      compare: { on: false, a: null, b: null }, classesOn: new Set()
    });
    return true;
  };

  /* Installs a manifest (already parsed), fills state defaults, emits 'manifest'. Used by load() and tests. */
  App.setManifest = function (raw) {
    App.manifest = normalise(raw);
    var region = App.manifest.app.default_region;
    var ids = landingLayers(region);
    var lang = CFG.lang || App.manifest.app.default_lang || 'en';
    App.setState({ region: region, layersOn: new Set(ids), opacity: opacityFor(ids), lang: lang });
    App.emit('manifest', App.manifest);
    return App.manifest;
  };

  /* load(): strings first (so t() works in listeners), then manifest. Never rejects.
     Resolves to {ok, error, manifest}. On failure an empty normalised manifest is installed and
     App.manifestStatus = {ok:false, error, lastKnown} so the shell can show state.manifest_failed. */
  App.load = function () {
    var lang = CFG.lang || 'en';
    return App.loadStrings(lang).then(function () {
      App.state.lang = lang;
      return App.fetchJSON(CFG.manifestUrl, { fallbackLabel: 'manifest' });
    }).then(function (r) {
      App.manifestStatus = { ok: r.ok, error: r.error, lastKnown: r.lastKnown, fetchedAt: r.fetchedAt };
      App.setManifest(r.ok ? r.data : {});
      try { document.documentElement.lang = App.state.lang; } catch (e) { /* ignore */ }
      return { ok: r.ok, error: r.error, manifest: App.manifest };
    });
  };
})();
