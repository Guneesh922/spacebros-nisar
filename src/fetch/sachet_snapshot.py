"""Save the NDMA SACHET all-India CAP RSS feed into the alerts.json shape used by the app.

Usage: python3 src/fetch/sachet_snapshot.py [--out data/interim/C/alerts.json] [--cap] [--keep-all]
  --cap       also fetch each item's CAP XML (link) to fill `area` from cap:areaDesc (one request per kept item)
  --keep-all  keep all items (default keeps all too; use --filter to keep only AP/Arnab-related items)
  --filter    keep only items whose title/area mention Andhra Pradesh, the delta districts, Arnab or cyclone
Feed: https://sachet.ndma.gov.in/cap_public_website/rss/rss_india.xml (RSS 2.0, no key, <copyright>public domain</copyright>).
RSS item fields: title, description (empty), category, link (CAP XML), author ("email (IMD office)"), guid, pubDate (GMT).
Output item: {headline, area, issued (IST ISO), source, link}. `area` = areaDesc if --cap else the issuing office.
Only standard library. Never invents text: headlines are copied from the English <info> or <title>; non-English alerts get one line built from CAP fields (apply_cap).
Importable (used by tools/pipeline/alerts.py): fetch_items(cap=False) -> (items, meta); fill_cap_areas(items, only=None).
Each item also carries `id` (the feed <guid>).
"""
import sys, re, json, argparse, urllib.request, datetime as dt
from concurrent.futures import ThreadPoolExecutor
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
FEED = "https://sachet.ndma.gov.in/cap_public_website/rss/rss_india.xml"
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
REL = re.compile(r"andhra|godavari|konaseema|kakinada|yanam|krishna|visakha|bapatla|arnab|cyclon|narsapur|amalapuram|rajamahendravaram|eluru", re.I)

def get(url, t=40):
    req = urllib.request.Request(url, headers={"User-Agent": "spacebros-nisar-snapshot/1.0"})
    return urllib.request.urlopen(req, timeout=t).read()

ORIG_LABEL = "Original alert (not in English)"
LANG_NOTE = "no English text in the source alert"
CAT_NAME = {"met": "Meteorological", "geo": "Geophysical", "safety": "Safety", "security": "Security", "rescue": "Rescue",
            "fire": "Fire", "health": "Health", "env": "Environmental", "transport": "Transport", "infra": "Infrastructure",
            "cbrne": "CBRNE", "other": "General"}

def is_latin_text(s):
    """True when every letter in s is Latin script (accents fine; digits, punctuation, symbols ignored)."""
    import unicodedata
    for ch in s or "":
        if ch.isalpha() and not unicodedata.name(ch, "").startswith("LATIN"):
            return False
    return True

def _local(tag):
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""

def _child_texts(el, name):
    return [(c.text or "").strip() for c in el if _local(c.tag) == name and (c.text or "").strip()]

def parse_cap(xml_bytes):
    """CAP XML bytes -> {sent, sender, category, infos:[{language, event, severity, urgency, headline, areas:[..]}]}.
    Namespace-agnostic (CAP 1.1 / 1.2). Raises ET.ParseError on bad XML."""
    x = ET.fromstring(xml_bytes)
    cap = {"sent": (x.findtext("{*}sent") or "").strip(), "sender": (x.findtext("{*}senderName") or x.findtext("{*}sender") or "").strip(),
           "infos": []}
    cats = []
    for info in x.findall("{*}info"):
        areas = []
        for a in info.findall("{*}area"):
            areas += _child_texts(a, "areaDesc")
        cats += _child_texts(info, "category")
        cap["infos"].append({"language": (info.findtext("{*}language") or "").strip(), "event": (info.findtext("{*}event") or "").strip(),
                             "severity": (info.findtext("{*}severity") or "").strip(), "urgency": (info.findtext("{*}urgency") or "").strip(),
                             "headline": re.sub(r"\s+", " ", info.findtext("{*}headline") or "").strip(),
                             "senderName": (info.findtext("{*}senderName") or "").strip(), "areas": areas})
    cap["category"] = cats[0] if cats else ""
    if not cap["sender"]:
        cap["sender"] = next((i["senderName"] for i in cap["infos"] if i["senderName"]), "")
    return cap

def _ist_text(iso):
    try:
        d = dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=IST)
        return d.astimezone(IST).strftime("%d %b %Y, %H:%M IST")
    except Exception:
        return ""

def english_line(event, severity, area, issued, office):
    """ONE English line from structured fields only (all inputs already Latin-checked by the caller)."""
    parts = [(event or "Alert") + (" alert" if event and "alert" not in event.lower() else "")]
    if severity:
        parts.append("severity " + severity.lower())
    parts.append("area: " + area if area else "area not given in English" + (", issued by " + office if office else ""))
    if issued:
        parts.append("issued " + issued)
    return ", ".join(parts)

def apply_cap(item, xml_bytes):
    """Fill item from CAP bytes. Prefers an <info> block with language en*. Otherwise builds one English line from
    structured fields and sets link_label + lang_note. Keeps the ORIGINAL text in item['_match_text'] (never output).
    item must hold headline (RSS title), area (office), source, issued, link."""
    cap = parse_cap(xml_bytes)
    infos = cap["infos"]
    orig = [item.get("headline", ""), cap["sender"]] + [s for i in infos for s in (i["headline"], i["event"]) + tuple(i["areas"])]
    item["_match_text"] = " ".join(o for o in orig if o)
    en = next((i for i in infos if i["language"].lower().replace("_", "-").split("-")[0] == "en"), None)
    office = item.get("source") or ""
    office_en = office if is_latin_text(office) else (cap["sender"] if is_latin_text(cap["sender"]) else "")
    if en:
        area = "; ".join(a for a in en["areas"] if is_latin_text(a))
        head = en["headline"] if is_latin_text(en["headline"]) and en["headline"] else ""
        if not head:
            head = english_line(en["event"] if is_latin_text(en["event"]) else "", en["severity"], area, _ist_text(cap["sent"] or item.get("issued", "")), office_en)
        item["headline"] = head
        item["area"] = area or office_en or ""
        if en["severity"]:
            item["severity"] = en["severity"]
        if en["event"] and is_latin_text(en["event"]):
            item["event"] = en["event"]
        item["area_from_cap"] = True
        return item
    # no English info block: structured fallback
    first = infos[0] if infos else {"event": "", "severity": "", "areas": []}
    event = first["event"] if is_latin_text(first["event"]) else ""
    event = event or CAT_NAME.get((cap["category"] or "").lower(), "")
    latin_areas = [a for a in first["areas"] if is_latin_text(a)]
    area = "; ".join(latin_areas) if latin_areas and len(latin_areas) == len(first["areas"]) else ""
    area = area or office_en
    item["headline"] = english_line(event, first["severity"], area, _ist_text(cap["sent"] or item.get("issued", "")),
                                    office_en if not area else "")
    item["area"] = area
    item["link_label"] = ORIG_LABEL
    item["lang_note"] = LANG_NOTE
    item["area_from_cap"] = bool(area)
    return item

def english_fallback_rss(item):
    """RSS-only item (no CAP read) whose title/area/source has non-Latin letters -> English line from what is left."""
    if all(is_latin_text(item.get(k)) for k in ("headline", "area", "source")):
        return item
    item["_match_text"] = " ".join(x for x in (item.get("_match_text"), item.get("headline"), item.get("area"), item.get("source")) if x)
    office = item.get("source") if is_latin_text(item.get("source")) else ""
    item["headline"] = english_line(CAT_NAME.get((item.get("category") or "").lower(), ""), "", "", _ist_text(item.get("issued", "")), office)
    item["area"] = office
    item["source"] = office
    item["link_label"] = ORIG_LABEL
    item["lang_note"] = LANG_NOTE
    return item

def cap_area(link):
    """Back-compat: English-safe area string for a CAP link ('' on failure)."""
    try:
        it = apply_cap({"headline": "", "area": "", "source": "", "issued": "", "link": link}, get(link, 25))
        return it["area"]
    except Exception:
        return ""

def fetch_items(feed=FEED, cap=False, timeout=40):
    """Fetch the SACHET RSS feed. Returns (items, meta). items = [{id, headline, area, issued (IST ISO), source, link,
    category}]; `area` = issuing office, or CAP areaDesc when cap=True. meta = feed_pubdate, counts, oldest/newest item."""
    root = ET.fromstring(get(feed, timeout))
    ch = root.find("channel")
    items = []
    for it in ch.findall("item"):
        title = re.sub(r"\s+", " ", (it.findtext("title") or "")).strip()
        author = it.findtext("author") or ""
        m = re.search(r"\((.*?)\)", author)
        office = m.group(1) if m else author
        link = it.findtext("link") or ""
        try:
            issued = parsedate_to_datetime(it.findtext("pubDate")).astimezone(IST).isoformat(timespec="seconds")
        except Exception:
            issued = ""
        items.append({"id": (it.findtext("guid") or link).strip(), "headline": title, "area": office, "issued": issued,
                      "source": office, "link": link, "category": it.findtext("category") or ""})
    if cap:
        fill_cap_areas(items)
    else:
        for i in items:
            english_fallback_rss(i)
    meta = {"feed_url": feed, "feed_pubdate": ch.findtext("pubDate"), "feed_item_count": len(items),
            "feed_oldest_item_ist": min((i["issued"] for i in items if i["issued"]), default=None),
            "feed_newest_item_ist": max((i["issued"] for i in items if i["issued"]), default=None)}
    return items, meta

def fill_cap_areas(items, only=None, workers=8):
    """Read each item's CAP XML (one request per item, `workers` in parallel) and apply it (see apply_cap): English info
    block if present, else an English line built from structured fields. Items whose CAP cannot be read keep the issuing
    office as area (and get the RSS-only English fallback if their title is not Latin script)."""
    todo = [i for i in items if i.get("link") and (only is None or only(i))]
    def fetch(i):
        try:
            return get(i["link"], 25)
        except Exception:
            return None
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for i, b in zip(todo, ex.map(fetch, todo)):
            try:
                if b is not None:
                    apply_cap(i, b)
            except Exception:
                pass
    for i in items:
        english_fallback_rss(i)
    return len(todo)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/interim/C/alerts.json")
    ap.add_argument("--cap", action="store_true")
    ap.add_argument("--filter", action="store_true")
    ap.add_argument("--max", type=int, default=200)
    a = ap.parse_args()
    items, meta = fetch_items(cap=a.cap)
    n_all = len(items)
    oldest, newest = meta["feed_oldest_item_ist"], meta["feed_newest_item_ist"]
    if a.filter:
        items = [i for i in items if REL.search(i["headline"] + " " + i["area"])]
    items = items[:a.max]
    out = {
        "saved_at_ist": dt.datetime.now(IST).isoformat(timespec="seconds"),
        "feed_url": FEED,
        "feed_pubdate": meta["feed_pubdate"],
        "feed_item_count": n_all,
        "feed_oldest_item_ist": oldest,
        "feed_newest_item_ist": newest,
        "filter": "andhra/godavari/arnab/cyclone keywords" if a.filter else None,
        "credit": "NDMA SACHET (CAP Integrated Alert System); feed states copyright 'public domain'",
        "placeholder": {"is": False},
        "sachet": items,
        "gdacs": [],
    }
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump({**out, "sachet": [{k: v for k, v in i.items() if k != "_match_text"} for i in items]}, f, ensure_ascii=False, indent=2)
    print("saved", a.out, "items kept", len(items), "of", n_all)

if __name__ == "__main__":
    main()
