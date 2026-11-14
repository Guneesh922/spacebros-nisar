"""Package E step 1: ERA5 (via Open-Meteo archive API) 10 m wind over the sea box, 5x5 grid."""
import json, os, time, csv, urllib.request, urllib.error, datetime
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
RAW = os.path.join(ROOT, "data", "raw", "era5")
os.makedirs(RAW, exist_ok=True)
LATS = [15.0, 15.75, 16.5, 17.25, 18.0]
LONS = [81.0, 82.0, 83.0, 84.0, 85.0]
DATES = ["2026-10-15", "2026-10-27"]
URL = ("https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}"
       "&start_date={d}&end_date={d}&hourly=wind_speed_10m,wind_direction_10m&models=era5&wind_speed_unit=ms")
fails = []
rows = []
for d in DATES:
    for lat in LATS:
        for lon in LONS:
            fn = os.path.join(RAW, f"openmeteo_era5_{d}_{lat}_{lon}.json")
            if not os.path.exists(fn):
                url = URL.format(lat=lat, lon=lon, d=d)
                for attempt in range(6):
                    try:
                        with urllib.request.urlopen(url, timeout=60) as r:
                            body = r.read()
                        json.loads(body)
                        with open(fn, "wb") as f: f.write(body)
                        break
                    except urllib.error.HTTPError as e:
                        if e.code == 429:
                            time.sleep(20 * (attempt + 1)); continue
                        fails.append((url, e.code)); break
                    except Exception as e:
                        fails.append((url, repr(e))); break
                time.sleep(1)
            if os.path.exists(fn):
                j = json.load(open(fn))
                h = j["hourly"]
                for t, s, a in zip(h["time"], h["wind_speed_10m"], h["wind_direction_10m"]):
                    hr = int(t[11:13])
                    if 12 <= hr <= 14:
                        rows.append((d, hr, lat, lon, s, a, j.get("latitude"), j.get("longitude"), j.get("elevation")))
with open(os.path.join(ROOT, "data", "reference", "era5_wind_summary.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["date", "hour_utc", "lat", "lon", "wind_ms", "dir_deg"])
    for r in rows: w.writerow(r[:6])
# grid cell centres reported by API (flags land points via elevation)
with open(os.path.join(ROOT, "data", "reference", "era5_grid_points.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["lat_req", "lon_req", "lat_api", "lon_api", "elevation_m"])
    seen = set()
    for r in rows:
        k = (r[2], r[3])
        if k not in seen:
            seen.add(k); w.writerow([r[2], r[3], r[6], r[7], r[8]])
print("rows", len(rows), "fails", fails)
