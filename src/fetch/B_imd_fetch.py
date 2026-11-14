"""Package B: download IMD/RSMC New Delhi bulletins for Cyclone Arnab (no login).
Paths come from the listing page https://rsmcnewdelhi.imd.gov.in/system-archive.php?internal_menu=MzQ=&year=MjAyNg==
"""
import hashlib, os, subprocess, sys, urllib.parse
BASE = "https://rsmcnewdelhi.imd.gov.in/download.php?path="
OUT = "docs/imd_bulletins"
# (local name, remote path under uploads/archive/)
ITEMS = [
 ("20261027_1200UTC_national_bulletin_No20.pdf","1/1_59f3a4_20._National_Bulletin_No_20-27Oct2026_1730IST.pdf"),
 ("20261027_1500UTC_national_bulletin_No21.pdf","1/1_96d6b1_21._National_Bulletin_No_21-27Oct2026_2030IST.pdf"),
 ("20261027_1800UTC_national_bulletin_No22.pdf","1/1_003024_22._National_Bulletin_No_22-27Oct2026_2330IST.pdf"),
 ("20261028_0000UTC_national_bulletin_No24.pdf","1/1_6e0436_24._National_Bulletin_No_24-28Oct2026_0530IST.pdf"),
 ("20261027_1200UTC_tc_advisory_No13.pdf","2/2_a31b38_Tropical_cyclone_advisory__No.13_based_on_1200_UTC_of_27.10.2026.pdf"),
 ("20261027_1500UTC_tc_advisory_No14.pdf","2/2_a4ef14_Tropical_cyclone_advisory__No.14_based_on_1500_UTC_of_27.10.2026.pdf"),
 ("20261027_1800UTC_tc_advisory_No15.pdf","2/2_0c4891_Tropical_cyclone_advisory__No.15_based_on_1800_UTC_of_27.10.2026.pdf"),
 ("20261028_0000UTC_tc_advisory_No17.pdf","2/2_900d51_Tropical_cyclone_advisory__No.17_based_on_0000_UTC_of_27.10.2026.pdf"),
 ("20261027_2000UTC_hourly_bulletin_No7.pdf","48/48_fea61a_7.Hourly_Bulletin_271026_2000UTC.pdf"),
 ("20261027_2100UTC_hourly_bulletin_No8.pdf","48/48_55c135_8.Hourly_Bulletin_271026_2100UTC.pdf"),
 ("20261027_2200UTC_hourly_bulletin_No9.pdf","48/48_73d337_9.Hourly_Bulletin_271026_2200UTC.pdf"),
 ("20261027_2300UTC_hourly_bulletin_No10.pdf","48/48_991dc4_10.Hourly_Bulletin_271026_2300UTC.pdf"),
 ("20261028_0000UTC_hourly_bulletin_No11.pdf","48/48_a7edc0_11.Hourly_Bulletin_281026_0000UTC.pdf"),
 ("20261027_0300UTC_press_release_27Oct.pdf","21/21_5ec45d_Press_Release_dated_27th_October.pdf"),
 ("20261028_0300UTC_press_release_28Oct.pdf","21/21_0acd90_Press_Release_dated_28th_October.pdf"),
]
os.makedirs(OUT, exist_ok=True)
for name, rp in ITEMS:
    url = BASE + urllib.parse.quote("uploads/archive/"+rp, safe="")
    dst = os.path.join(OUT, name)
    if os.path.exists(dst): continue
    r = subprocess.run(["curl","-sS","-m","90","-o",dst+".part","-w","%{http_code}",url],capture_output=True,text=True)
    code = r.stdout.strip()
    if code=="200": os.replace(dst+".part",dst); print(name,"OK",os.path.getsize(dst),url)
    else: print(name,"FAIL",code,r.stderr.strip(),url)
