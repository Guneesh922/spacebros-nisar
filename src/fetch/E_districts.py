"""Package E step 4: map geoBoundaries ADM3 mandal names (delta box) to 2022 AP districts using the saved Wikipedia wikitext lists."""
import re, os, csv, json, subprocess
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
D = os.path.join(ROOT, "data/raw/districts2022")
PAGES = {  # district_2022 -> (file, url)
 "Dr. B.R. Ambedkar Konaseema": ("wiki_Konaseema_district.wikitext", "https://en.wikipedia.org/wiki/Konaseema_district"),
 "Kakinada": ("wiki_Kakinada_district.wikitext", "https://en.wikipedia.org/wiki/Kakinada_district"),
 "East Godavari": ("wiki_East_Godavari_district.wikitext", "https://en.wikipedia.org/wiki/East_Godavari_district"),
 "West Godavari": ("wiki_West_Godavari_district.wikitext", "https://en.wikipedia.org/wiki/West_Godavari_district"),
 "Eluru": ("wiki_Eluru_district.wikitext", "https://en.wikipedia.org/wiki/Eluru_district"),
}
official = {}  # official name -> (district, url)
for dist,(fn,url) in PAGES.items():
    txt = open(os.path.join(D,fn)).read().splitlines()
    in_list = False
    for ln in txt:
        if re.match(r"^=+\s*Mandals\s*=+", ln) or re.match(r"^#\s*\[\[[^\]]*revenue division", ln): in_list = True; continue
        if in_list and re.match(r"^=+[^=]", ln) : in_list = False
        m = re.match(r"^##\s*\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", ln)
        if in_list and m:
            official[(m.group(2) or m.group(1)).strip()] = (dist, url)
# manual spelling bridge geoBoundaries -> Wikipedia label (only where the two differ in spelling; verified by eye against both lists)
bridge = {"Anaparthy":"Anaparthi","Kakinada (Rural)":"Kakinada Rural","Kakinada (Urban)":"Kakinada Urban","P.Gannavaram":"P. Gannavaram",
 "Palacole":"Palakollu","Palacoderu":"Palakoderu","Nidadavole":"Nidadavolu","Rajahmundry (Urban)":"Rajamahendravaram Urban",
 "Rajahmundry Rural":"Rajamahendravaram Rural","K Gangavaram":"K. Gangavaram","Alamuru":"Alumuru","Kothapalle":"U. Kothapalli"}
names = [l.strip() for l in open("/tmp/E_names.txt") if l.strip()]
rows=[]; miss=[]
for n in names:
    o = bridge.get(n, n)
    if o in official:
        rows.append([n,o,official[o][0],official[o][1]])
    else:
        rows.append([n,"","",""]); miss.append(n)
with open(os.path.join(ROOT,"data/reference/mandal_district_2022.csv"),"w",newline="") as f:
    w=csv.writer(f); w.writerow(["mandal_name_geoboundaries","mandal_name_official","district_2022","source_url"]); w.writerows(rows)
print(len(rows),"unmatched:",miss, "official parsed:",len(official))
