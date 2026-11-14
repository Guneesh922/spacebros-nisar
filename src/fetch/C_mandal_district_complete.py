"""Worker C job 4: complete mandal -> district mapping for all 146 polygons of data/reference/mandals_delta.geojson.
Inputs: data/reference/mandals_delta_list.csv, data/reference/mandal_district_2022.csv (existing, kept as is),
        Wikipedia wikitext of district pages (data/raw/districts2022/*.wikitext and data/interim/C/wikitext/*.wikitext).
Output: data/interim/C/mandal_district_2022_complete.csv + data/interim/C/mandal_district_unresolved.csv
Matching: exact name match after lower-casing and dropping non-letters, or an explicit BRIDGE entry (each verified by eye).
Never guesses: no match -> district blank.
CAVEAT: the Wikipedia pages are the Nov 2026 text, i.e. after the Dec 2025 creation of Polavaram district. Where that matters
the row is flagged in `note` and the 2022 district is taken from the page statement of what was carved out of what.
"""
import re, csv, os, sys, json, difflib
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
R = os.path.join(ROOT, "data/raw/districts2022"); N = os.path.join(ROOT, "data/interim/C/wikitext")
FILES = {
 "Dr. B.R. Ambedkar Konaseema": R + "/wiki_Konaseema_district.wikitext", "Kakinada": R + "/wiki_Kakinada_district.wikitext",
 "East Godavari": R + "/wiki_East_Godavari_district.wikitext", "West Godavari": R + "/wiki_West_Godavari_district.wikitext",
 "Eluru": R + "/wiki_Eluru_district.wikitext", "Krishna": N + "/wiki_Krishna_district.wikitext", "NTR": N + "/wiki_NTR_district.wikitext",
 "Anakapalli": N + "/wiki_Anakapalli_district.wikitext", "Alluri Sitharama Raju": N + "/wiki_Alluri_Sitharama_Raju_district.wikitext",
 "Visakhapatnam": N + "/wiki_Visakhapatnam_district.wikitext", "Bapatla": N + "/wiki_Bapatla_district.wikitext",
 "Bhadradri Kothagudem (Telangana)": N + "/wiki_Bhadradri_Kothagudem_district.wikitext",
 "Polavaram (created 31 Dec 2025 from Alluri Sitharama Raju)": N + "/wiki_Polavaram_district.wikitext"}
URL = {d: "https://en.wikipedia.org/wiki/" + os.path.basename(f)[5:-9] for d, f in FILES.items()}
def norm(s): return re.sub(r"[^a-z]", "", s.lower())
def parse(fn, district):
    txt = open(fn, encoding="utf-8").read().splitlines(); names = []; on = False
    wg = district == "West Godavari"
    for ln in txt:
        if re.match(r"^=+\s*(Mandals|Administrative divisions)\s*=+", ln): on = True; continue
        if on and re.match(r"^=+[^=]", ln) and not re.match(r"^=+\s*Mandals", ln): on = False
        if not on: continue
        m = re.match(r"^(?:##|\*\*|#|\*)?\s*\d*\.?\s*\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", ln)
        if m and "division" not in m.group(1).lower() and "alt=" not in m.group(1): names.append((m.group(2) or m.group(1)).strip())
        m2 = re.match(r"^\|\s*\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", ln)
        if m2: names.append((m2.group(2) or m2.group(1)).strip())
        m3 = re.match(r"^##\s*([A-Za-z][A-Za-z .]+)\s*$", ln)   # plain-text list items (Polavaram page)
        if m3: names.append(m3.group(1).strip())
    return names
OFF = {}   # norm(name) -> list of (district, official_name)
for d, f in FILES.items():
    for n in parse(f, d): OFF.setdefault(norm(n), []).append((d, n))
# verified spelling bridges geoBoundaries -> wikipedia (norm of wikipedia label)
BRIDGE = {"Mudinepalle": "Mudinepalli", "Kothapalle": "U. Kothapalli", "Palacole": "Palakollu", "Palacoderu": "Palakoderu",
 "Nidadavole": "Nidadavolu", "Rajahmundry (Urban)": "Rajamahendravaram Urban", "Rajahmundry Rural": "Rajamahendravaram Rural",
 "Kakinada (Rural)": "Kakinada Rural", "Kakinada (Urban)": "Kakinada Urban", "Anaparthy": "Anaparthi", "Alamuru": "Alumuru",
 "K Gangavaram": "K. Gangavaram", "P.Gannavaram": "P. Gannavaram", "T.Narasapuram": "T. Narasapuram", "S.Rayavaram": "S. Rayavaram",
 "Y. Ramavaram": "Y. Ramavaram", "Dwarakatirumala": "Dwaraka Tirumala", "Jeelugu Milli": "Jeelugu Milli", "Machilipatnam": "Machilipatnam South", "Jangareddigudem": "Jangareddygudem",
 "Challapalle": "Challapalli", "Kruthivennu": "Kruthivennu", "Vararamachandrapuram": "Vara Ramachandrapuram", "Yelamanchili": "Elamanchili",
 "Nakkapalle": "Nakkapalli", "Kasimkota": "Kasimkota", "Narsipatnam": "Narsipatnam", "Chintalapudi": "Chintalapudi", "Kukunoor": "Kukunuru",
 "Pedapudi": "Pedapudi", "Veeravasaram": "Veeravasaram", "Chagallu": "Chagallu", "Koduru": "Koduru", "Akividu": "Akiveedu",
 "Nidamarru": "Nidamarru", "Aswaraopeta": "Aswaraopeta", "Yeleswaram": "Yeleswaram", "Rampachodavaram": "Rampachodavaram"}
exist = {}
for r in csv.DictReader(open(os.path.join(ROOT, "data/reference/mandal_district_2022.csv"))):
    exist[r["mandal_name_geoboundaries"]] = r
rows = []; unres = []
LIST = list(csv.DictReader(open(os.path.join(ROOT, "data/reference/mandals_delta_list.csv"))))
cnt = {}
for r in LIST: cnt[r["shapeName"]] = cnt.get(r["shapeName"], 0) + 1
ALLOWED = {"East Godavari": ("Kakinada", "Dr. B.R. Ambedkar Konaseema", "East Godavari", "Alluri Sitharama Raju", "Yanam"),
 "West Godavari": ("West Godavari", "Eluru", "East Godavari"), "Krishna": ("Krishna", "NTR", "Eluru", "Bapatla"),
 "Visakhapatnam": ("Anakapalli", "Alluri Sitharama Raju", "Visakhapatnam"), "Bhadradri": ("Eluru", "Alluri Sitharama Raju", "Bhadradri Kothagudem (Telangana)")}
def out(r, dist, off, src, conf, note=""):
    if dist and not any(dist.startswith(a) for a in ALLOWED.get(r["parent_ADM2_name"], (dist,))):
        note = ("2018 parent " + r["parent_ADM2_name"] + " is inconsistent with " + dist + "; name also exists in another district; " + note)
        dist, off, src, conf = "", "", "", "ambiguous"
        unres.append((r, "2018 parent inconsistent with name match"))
    rows.append({"shapeID": r["shapeID"], "mandal_geoboundaries": r["shapeName"], "parent_ADM2_2018": r["parent_ADM2_name"],
                 "frac_inside_delta_box": r["frac_inside_delta_box"], "mandal_official": off, "district_2022": dist, "source": src,
                 "confidence": conf, "note": note})
for r in LIST:
    nm = r["shapeName"]; key = nm
    if cnt[nm] > 1:   # duplicate name: decide by 2018 parent district, never by name alone
        if nm == "Yelamanchili" and r["parent_ADM2_name"] == "Visakhapatnam":
            out(r, "Anakapalli", "Elamanchili", URL["Anakapalli"], "high", "Elamanchili mandal; 2018 parent Visakhapatnam; existing E mapping wrongly gave West Godavari to both polygons")
        elif nm == "Yelamanchili" and r["parent_ADM2_name"] == "West Godavari":
            out(r, "West Godavari", "Yelamanchili", URL["West Godavari"], "medium-high", "Yelamanchili mandal, Narasapuram revenue division, West Godavari list; 2018 parent also West Godavari; the other polygon of this name (parent Visakhapatnam) is Elamanchili in Anakapalli")
        continue
    if nm == "Yanam Taluk":
        out(r, "Yanam (Puducherry UT, not Andhra Pradesh)", "Yanam", "https://en.wikipedia.org/wiki/Yanam_district", "high", "Yanam is a district of the Union Territory of Puducherry"); continue
    if nm in exist and exist[nm]["district_2022"]:
        e = exist[nm]; out(r, e["district_2022"], e["mandal_name_official"], e["source_url"], "medium-high", "existing E mapping kept (wikipedia list match)"); continue
    cand = BRIDGE.get(nm, nm)
    hits = OFF.get(norm(cand), []) if cand else []
    if not hits and cand:
        hits = OFF.get(norm(re.sub(r"\(.*?\)", "", cand)), [])
    if len(hits) == 1:
        d, off = hits[0]
        note = ""; dist = d
        if d.startswith("Polavaram"):
            dist = "Alluri Sitharama Raju"; note = "currently Polavaram district (created 31 Dec 2025 from ASR per Wikipedia Polavaram/ASR pages); 2022 district taken as ASR; medium confidence"
        if norm(off) != norm(nm) and not note: note = "spelling bridge: geoBoundaries '" + nm + "' = Wikipedia '" + off + "'"
        if nm == "Machilipatnam": note = "Machilipatnam mandal was split into Machilipatnam North/South (both in Krishna) per 2026 Wikipedia text; 2022 = Krishna"
        if nm == "Kukunoor": note = "Wikipedia Eluru list spells it 'Kukunuru' (unlinked); same mandal, Jangareddygudem division"
        out(r, dist, off, URL[d], "medium" if note.startswith("currently") else "medium-high", note)
    elif len(hits) > 1:
        out(r, "", "", "", "ambiguous", "name in several lists: " + "; ".join(h[0] for h in hits)); unres.append((r, "name in several district lists"))
    else:
        sugg = difflib.get_close_matches(norm(nm), list(OFF.keys()), 2, 0.8)
        out(r, "", "", "", "unresolved", "no match in saved Wikipedia lists" + (("; near: " + ", ".join(OFF[s][0][1] + " (" + OFF[s][0][0] + ")" for s in sugg)) if sugg else ""))
        unres.append((r, "no match"))
os.makedirs(os.path.join(ROOT, "data/interim/C"), exist_ok=True)
f = os.path.join(ROOT, "data/interim/C/mandal_district_2022_complete.csv")
with open(f, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
uf = os.path.join(ROOT, "data/interim/C/mandal_district_unresolved.csv")
with open(uf, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows([r for r in rows if not r["district_2022"]])
print(len(rows), "rows; with district:", sum(1 for r in rows if r["district_2022"]), "; unresolved:", len(unres))
for r in rows:
    if not r["district_2022"]: print("  UNRES", r["shapeID"][:8], r["mandal_geoboundaries"], r["parent_ADM2_2018"], r["note"])
