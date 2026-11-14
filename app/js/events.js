/* events.js: the Events tab and the event banner / landfall marker on the map. Classic script.
   Defines window.App.events = { init(rootEl) }.
   Reads state, manifest and lookups only through App. Never hard-codes dates, tracks or event names:
   everything about an event comes from App.manifest.events.
   Listens: event, manifest, lang, view (refresh GDACS when the Events tab opens).
   Uses: App.applyEvent, App.clearEvent, App.setState, App.live.getGdacsEvents, App.map.getMap(). */
(function () {
  'use strict';
  var App = window.App;
  if (!App) { console.error('[events] App missing (load core.js first)'); return; }

  App.addStrings('en', {
    'events.live_near': 'Near {region}, last {days} days',
    'events.live_all': 'Nothing near this region in the last {days} days. Showing all current GDACS events.',
    'events.live_loading': 'Loading live alerts',
    'events.live_checked': 'Checked {time}',
    'events.never_loaded': 'never loaded',
    'events.alert_green': 'Green',
    'events.alert_orange': 'Orange',
    'events.alert_red': 'Red',
    'events.hazard_cyclone_flood': 'Cyclone and flood',
    'events.dates_flow': '{before} → {during} → {after}',
    'events.back_now': 'Back to workspace now',
    'events.link_gdacs': 'Open at GDACS',
    'events.new_tab': '(opens in a new tab)',
    'events.banner_loaded': 'Event loaded: {name}',
    'events.landfall_title': 'Landfall position',
    'events.landfall_time': 'Time: {time}',
    'events.sub_saved': 'Saved events open the workspace with their layers, dates and track.'
  });

  var T = function (k, v) { return App.t(k, v); };
  var GDACS_REGION = 'ap_coast';
  var GDACS_PAD_DEG = 5;
  var GDACS_DAYS = 30;
  var LF_RETRY_MS = 250;
  var LF_MAX_TRIES = 20;

  var rootEl = null, gdacsSub = null, gdacsList = null, savedList = null;
  var inited = false;
  var gdacsState = { token: 0, status: 'idle', res: null, fallbackAll: false };
  var banner = null, bannerText = null, bannerDates = null, bannerBtn = null;
  var landfall = null, lfTries = 0, lfTimer = null;

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
  function manifestEvents() { return (App.manifest && App.manifest.events) || []; }
  function isLoaded(id) { return App.state.eventId === id; }
  function dateOnly(s) {
    if (!s) return '';
    var m = /^(\d{4}-\d{2}-\d{2})/.exec(String(s));
    return m ? App.fmt.date(m[1]) : '';
  }
  function hazardWord(h) {
    if (!h) return '';
    var key = 'events.hazard_' + h;
    if (App.hasString(key)) return T(key);
    var plain = String(h).replace(/_/g, ' ');
    return plain.charAt(0).toUpperCase() + plain.slice(1);
  }
  function regionName(id) {
    var r = id ? App.regionById(id) : null;
    return r ? r.name : (id || '');
  }
  function gdacsTypeWord(t) {
    if (!t) return '';
    var key = 'panels.gdacs_type_' + t;
    return App.hasString(key) ? T(key) : String(t);
  }
  function alertWord(a) {
    if (!a) return '';
    var key = 'events.alert_' + String(a).toLowerCase();
    return App.hasString(key) ? T(key) : String(a);
  }
  function safeUrl(u) {
    return (typeof u === 'string' && /^https?:\/\//i.test(u)) ? u : null;
  }
  function paddedBounds(regionId, pad) {
    var r = App.regionById(regionId);
    var b = r && r.bounds;
    if (!b || b.length !== 2 || !b[0] || !b[1]) return null;
    /* manifest order is [[S,W],[N,E]]; live.getGdacsEvents wants [S,W,N,E] */
    return [
      Math.max(-90, b[0][0] - pad), Math.max(-180, b[0][1] - pad),
      Math.min(90, b[1][0] + pad), Math.min(180, b[1][1] + pad)
    ];
  }
  function timeText(iso) { return iso ? App.fmt.dateTime(iso, 'IST') : T('events.never_loaded'); }

  /* ---------------- page skeleton ---------------- */
  function buildPage() {
    rootEl.textContent = '';
    var page = el('div', 'events-page');

    var head = el('header', 'events-head');
    var h2 = el('h2', 'events-title', T('events.title'));
    head.appendChild(h2);
    page.appendChild(head);

    /* live alerts */
    var liveSec = el('section', 'events-section');
    liveSec.setAttribute('aria-labelledby', 'events-live-title');
    var liveTitle = el('h3', 'events-section__title', T('events.live_alerts'));
    liveTitle.id = 'events-live-title';
    gdacsSub = el('p', 'events-section__sub');
    gdacsList = el('div', 'events-list');
    liveSec.appendChild(liveTitle);
    liveSec.appendChild(gdacsSub);
    liveSec.appendChild(gdacsList);
    page.appendChild(liveSec);

    /* saved events */
    var savedSec = el('section', 'events-section');
    savedSec.setAttribute('aria-labelledby', 'events-saved-title');
    var savedTitle = el('h3', 'events-section__title', T('events.saved'));
    savedTitle.id = 'events-saved-title';
    var savedSub = el('p', 'events-section__sub', T('events.sub_saved'));
    savedList = el('div', 'events-list events-list--saved');
    savedSec.appendChild(savedTitle);
    savedSec.appendChild(savedSub);
    savedSec.appendChild(savedList);
    page.appendChild(savedSec);

    rootEl.appendChild(page);
  }

  /* ---------------- GDACS section ---------------- */
  function loadGdacs() {
    var token = (gdacsState.token = gdacsState.token + 1);
    gdacsState.status = 'loading';
    renderGdacs();
    var live = App.live && App.live.getGdacsEvents;
    if (typeof live !== 'function') {
      gdacsState.status = 'fail';
      gdacsState.res = { ok: false, events: [], fetchedAt: null, lastKnown: null };
      renderGdacs();
      return;
    }
    var bounds = paddedBounds(GDACS_REGION, GDACS_PAD_DEG);
    live({ bounds: bounds, days: GDACS_DAYS }).then(function (res) {
      if (token !== gdacsState.token) return null;
      if (!res || !res.ok) return { res: res || { ok: false }, fallbackAll: false };
      if (res.events && res.events.length) return { res: res, fallbackAll: false };
      /* nothing near the region: show everything GDACS has */
      return live({ days: GDACS_DAYS }).then(function (all) {
        if (token !== gdacsState.token) return null;
        return { res: all || res, fallbackAll: true };
      });
    }).then(function (out) {
      if (!out || token !== gdacsState.token) return;
      gdacsState.res = out.res;
      gdacsState.fallbackAll = out.fallbackAll;
      gdacsState.status = out.res.ok ? 'ok' : 'fail';
      renderGdacs();
    }).catch(function (e) {
      if (token !== gdacsState.token) return;
      console.warn('[events] GDACS load failed', e);
      gdacsState.status = 'fail';
      gdacsState.res = { ok: false, events: [], fetchedAt: null, lastKnown: null };
      renderGdacs();
    });
  }

  function gdacsCard(ev) {
    var card = el('article', 'card event-card');
    var typeWord = gdacsTypeWord(ev.type);
    card.appendChild(el('h4', 'event-card__title', ev.title || typeWord || ev.id || ''));
    var meta = [typeWord, alertWord(ev.alert), ev.country].filter(Boolean).join(' · ');
    if (meta) card.appendChild(el('p', 'event-card__meta', meta));
    var from = dateOnly(ev.from), to = dateOnly(ev.to);
    if (from && to) card.appendChild(el('p', 'event-card__meta', T('events.dates', { from: from, to: to })));
    else if (from || to) card.appendChild(el('p', 'event-card__meta', from || to));
    var url = safeUrl(ev.url);
    if (url) {
      var a = el('a', 'btn event-card__link', T('events.link_gdacs'));
      a.href = url;
      a.target = '_blank';
      a.rel = 'noopener noreferrer';
      a.appendChild(el('span', 'visually-hidden', ' ' + T('events.new_tab')));
      card.appendChild(a);
    }
    return card;
  }

  function renderGdacs() {
    if (!gdacsList) return;
    gdacsList.textContent = '';
    var res = gdacsState.res;
    var status = gdacsState.status;
    gdacsSub.textContent = '';

    if (status === 'idle' || status === 'loading') {
      gdacsSub.textContent = T('events.live_loading');
      var wait = el('p', 'events-note', T('state.loading') + '…');
      wait.setAttribute('role', 'status');
      gdacsList.appendChild(wait);
      return;
    }

    var region = regionName(GDACS_REGION) || regionName(App.state.region);
    if (status === 'fail') {
      gdacsSub.textContent = T('events.gdacs_unavailable');
      var lk = res && res.lastKnown;
      var msg = el('p', 'events-note is-fail');
      msg.setAttribute('role', 'status');
      msg.textContent = T('events.gdacs_unavailable') + ' · ' +
        (lk ? T('state.last_known', { time: timeText(lk) }) : T('events.never_loaded'));
      gdacsList.appendChild(msg);
      return;
    }

    var events = (res && res.events) || [];
    gdacsSub.textContent = gdacsState.fallbackAll
      ? T('events.live_all', { days: GDACS_DAYS })
      : T('events.live_near', { region: region, days: GDACS_DAYS });
    if (res && res.fetchedAt) {
      gdacsSub.textContent += ' · ' + T('events.live_checked', { time: timeText(res.fetchedAt) });
    }
    if (!events.length) {
      gdacsList.appendChild(el('p', 'events-note', T('events.none_live')));
      return;
    }
    events.forEach(function (ev) { gdacsList.appendChild(gdacsCard(ev)); });
  }

  /* ---------------- saved events section ---------------- */
  function savedCard(ev) {
    var loaded = isLoaded(ev.id);
    var card = el('article', 'card event-card' + (loaded ? ' is-loaded' : ''));
    card.appendChild(el('h3', 'event-card__title', ev.name || ev.id));

    card.appendChild(el('p', 'event-card__meta', [hazardWord(ev.hazard), regionName(ev.region)].filter(Boolean).join(' · ')));

    var d = ev.dates || {};
    if (d.before || d.during || d.after) {
      card.appendChild(el('p', 'event-card__dates',
        T('events.dates_flow', { before: App.fmt.date(d.before) || '–', during: App.fmt.date(d.during) || '–', after: App.fmt.date(d.after) || '–' })));
    }

    var actions = el('div', 'event-card__actions');
    if (loaded) {
      actions.appendChild(el('span', 'event-card__badge', T('events.loaded')));
      var back = el('button', 'btn event-card__btn', T('events.back_now'));
      back.type = 'button';
      back.addEventListener('click', function () {
        App.clearEvent();
        App.setState({ view: 'workspace' });
      });
      actions.appendChild(back);
    } else {
      var load = el('button', 'btn btn--primary event-card__btn', T('events.load'));
      load.type = 'button';
      load.addEventListener('click', function () {
        if (App.applyEvent(ev.id)) App.setState({ view: 'workspace' });
      });
      actions.appendChild(load);
    }
    card.appendChild(actions);
    return card;
  }

  function renderSaved() {
    if (!savedList) return;
    savedList.textContent = '';
    var list = manifestEvents();
    if (!list.length) {
      savedList.appendChild(el('p', 'events-note', T('events.none_saved')));
      return;
    }
    list.forEach(function (ev) { savedList.appendChild(savedCard(ev)); });
  }

  /* ---------------- banner (#map-wrap, shown only when an event is loaded) ---------------- */
  function ensureBanner() {
    if (banner) return banner;
    banner = el('div', 'event-banner');
    banner.id = 'event-banner';
    banner.setAttribute('role', 'status');
    bannerText = el('span', 'event-banner__text');
    bannerDates = el('span', 'event-banner__dates');
    bannerBtn = el('button', 'event-banner__btn');
    bannerBtn.type = 'button';
    bannerBtn.addEventListener('click', function () { App.clearEvent(); });
    banner.appendChild(bannerText);
    banner.appendChild(bannerDates);
    banner.appendChild(bannerBtn);
    return banner;
  }
  function renderBanner() {
    var id = App.state.eventId;
    var ev = id ? App.eventById(id) : null;
    var wrap = document.getElementById('map-wrap');
    if (!ev || !wrap) {
      if (banner && banner.parentNode) banner.parentNode.removeChild(banner);
      return;
    }
    ensureBanner();
    var d = ev.dates || {};
    bannerText.textContent = T('events.banner_loaded', { name: ev.name || ev.id });
    bannerDates.textContent = T('events.dates_flow', {
      before: App.fmt.date(d.before) || '–', during: App.fmt.date(d.during) || '–', after: App.fmt.date(d.after) || '–'
    });
    bannerBtn.textContent = T('events.back_now');
    if (banner.parentNode !== wrap) wrap.appendChild(banner);
  }

  /* ---------------- landfall marker ---------------- */
  function removeLandfall() {
    if (lfTimer) { clearTimeout(lfTimer); lfTimer = null; }
    lfTries = 0;
    if (landfall) {
      try { if (landfall.map) landfall.map.removeLayer(landfall.marker); } catch (e) { /* ignore */ }
      landfall = null;
    }
  }
  function landfallTooltip(lf) {
    var box = el('div', 'event-landfall-tip');
    box.appendChild(el('div', 'event-landfall-tip__title', T('events.landfall_title')));
    var when = lf.time_utc ? App.fmt.dateTime(lf.time_utc, 'IST') : T('state.landfall_pending');
    box.appendChild(el('div', 'event-landfall-tip__time', T('events.landfall_time', { time: when })));
    return box;
  }
  function syncLandfall() {
    var id = App.state.eventId;
    var ev = id ? App.eventById(id) : null;
    var lf = ev && ev.landfall;
    var valid = lf && typeof lf.lat === 'number' && typeof lf.lon === 'number' && isFinite(lf.lat) && isFinite(lf.lon);
    if (!valid) { removeLandfall(); return; }

    var map = App.map && App.map.getMap && App.map.getMap();
    if (!map || typeof L === 'undefined') {
      if (lfTries < LF_MAX_TRIES) {
        lfTries++;
        if (lfTimer) clearTimeout(lfTimer);
        lfTimer = setTimeout(function () { lfTimer = null; syncLandfall(); }, LF_RETRY_MS);
      }
      return;
    }
    lfTries = 0;

    if (landfall && landfall.eventId === id && landfall.map === map) {
      landfall.marker.setTooltipContent(landfallTooltip(lf));
      return;
    }
    removeLandfall();
    try {
      var marker = L.circleMarker([lf.lat, lf.lon], {
        radius: 7,
        weight: 2,
        color: css('--ink', 'CanvasText'),
        fillColor: css('--white', 'Canvas'),
        fillOpacity: 1,
        interactive: true
      }).bindTooltip(landfallTooltip(lf), {
        permanent: true, direction: 'right', offset: [12, 0], className: 'map-tip'
      }).addTo(map);
      landfall = { marker: marker, map: map, eventId: id };
    } catch (e) {
      console.warn('[events] landfall marker failed', e);
    }
  }

  /* ---------------- wiring ---------------- */
  function renderAll() {
    renderGdacs();
    renderSaved();
    renderBanner();
    syncLandfall();
  }

  function init(root) {
    if (inited) return;
    if (!root) { console.error('[events] init needs a container element'); return; }
    inited = true;
    rootEl = root;
    buildPage();
    renderGdacs();
    renderSaved();

    App.on('event', function () { renderSaved(); renderBanner(); syncLandfall(); });
    App.on('manifest', function () { renderSaved(); renderBanner(); syncLandfall(); });
    App.on('lang', function () { renderAll(); });
    App.on('view', function (v) { if (v === 'events') loadGdacs(); });

    loadGdacs();
    renderBanner();
    syncLandfall();
  }

  App.events = { init: init };
})();
