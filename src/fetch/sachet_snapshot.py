"""Save the NDMA SACHET all-India CAP RSS feed into the alerts.json shape used by the app.

Usage: python3 src/fetch/sachet_snapshot.py [--out data/interim/C/alerts.json] [--cap] [--keep-all]
  --cap       also fetch each item's CAP XML (link) to fill `area` from cap:areaDesc (one request per kept item)
  --keep-all  keep all items (default keeps all too; use --filter to keep only AP/Arnab-related items)
  --filter    keep only items whose title/area mention Andhra Pradesh, the delta districts, Arnab or cyclone
Feed: https://sachet.ndma.gov.in/cap_public_website/rss/rss_india.xml (RSS 2.0, no key, <copyright>public domain</copyright>).
RSS item fields: title, description (empty), category, link (CAP XML), author ("email (IMD office)"), guid, pubDate (GMT).
Output item: {headline, area, issued (IST ISO), source, link}. `area` = areaDesc if --cap else the issuing office.
Only standard library. Never invents text: headlines are copied from <title>.
"""
import sys, re, json, argparse, urllib.request, datetime as dt
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
FEED = "https://sachet.ndma.gov.in/cap_public_website/rss/rss_india.xml"
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
REL = re.compile(r"andhra|godavari|konaseema|kakinada|yanam|krishna|visakha|bapatla|arnab|cyclon|narsapur|amalapuram|rajamahendravaram|eluru", re.I)

def get(url, t=40):
    req = urllib.request.Request(url, headers={"User-Agent": "spacebros-nisar-snapshot/1.0"})
    return urllib.request.urlopen(req, timeout=t).read()

def cap_area(link):
    try:
        x = ET.fromstring(get(link, 25))
        ns = {"c": "urn:oasis:names:tc:emergency:cap:1.2"}
        a = x.find(".//c:info/c:area/c:areaDesc", ns)
        return (a.text or "").strip() if a is not None else ""
    except Exception:
        return ""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/interim/C/alerts.json")
    ap.add_argument("--cap", action="store_true")
    ap.add_argument("--filter", action="store_true")
    ap.add_argument("--max", type=int, default=200)
    a = ap.parse_args()
    root = ET.fromstring(get(FEED))
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
        items.append({"headline": title, "area": office, "issued": issued, "source": office, "link": link, "category": it.findtext("category") or ""})
    if a.cap:
        for i in items:
            i["area"] = cap_area(i["link"]) or i["area"]
    n_all = len(items)
    oldest = min((i["issued"] for i in items if i["issued"]), default=None)
    newest = max((i["issued"] for i in items if i["issued"]), default=None)
    if a.filter:
        items = [i for i in items if REL.search(i["headline"] + " " + i["area"])]
    items = items[:a.max]
    out = {
        "saved_at_ist": dt.datetime.now(IST).isoformat(timespec="seconds"),
        "feed_url": FEED,
        "feed_pubdate": ch.findtext("pubDate"),
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
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("saved", a.out, "items kept", len(items), "of", n_all)

if __name__ == "__main__":
    main()
