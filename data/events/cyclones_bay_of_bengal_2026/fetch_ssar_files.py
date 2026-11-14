import time
import requests

BASE_URL = "https://bhoonidhi-api.nrsc.gov.in"
USER_ID = "ArkaSPACE"
PASSWORD = "arka@#2359"

# 1. Authenticate and get JWT access token
auth_payload = {
    "userId": USER_ID,
    "password": PASSWORD,
    "grant_type": "password"
}
auth_resp = requests.post(f"{BASE_URL}/auth/token", json=auth_payload)
auth_resp.raise_for_status()
token_data = auth_resp.json()
access_token = token_data["access_token"]
refresh_token = token_data["refresh_token"]

headers = {"Authorization": f"Bearer {access_token}"}

# 2. Search STAC catalog for .h5-producing collections (e.g., NISAR or EOS-06)
# bbox format: [min_lon, min_lat, max_lon, max_lat]
search_payload = {
    "collections": ["NISAR_SSAR_GCOV","NISAR_SSAR_GOFF"],
    "bbox": [76.8, 28.4, 77.4, 28.9],
    "datetime": "2026-10-13T00:00:00Z/2026-11-04T23:59:59Z",
    "filter": {
        "op": "eq",
        "args": [{"property": "Online"}, "Y"]
    },
    "filter-lang": "cql2-json",
    "limit": 50
}

search_resp = requests.post(f"{BASE_URL}/data/search", json=search_payload, headers=headers)
search_resp.raise_for_status()
features = search_resp.json().get("features", [])
print(f"Found {len(features)} online products.")

# 3. Download matching products (respecting the 2 requests/min rate limit)
for item in features:
    item_id = item["id"]
    collection = item["collection"]
    
    # Optional: inspect assets/properties to confirm .h5 file extension
    download_url = f"{BASE_URL}/download?id={item_id}&collection={collection}"
    print(f"Downloading {item_id} from {collection}...")
    
    with requests.get(download_url, headers=headers, stream=True) as dl_resp:
        dl_resp.raise_for_status()
        # Extract filename from Content-Disposition header or fallback to item_id
        filename = f"{item_id}.zip"
        if "Content-Disposition" in dl_resp.headers:
            filename = dl_resp.headers["Content-Disposition"].split("filename=")[-1].strip('"')
            
        with open(filename, "wb") as f:
            for chunk in dl_resp.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Saved {filename}")
    
    # Sleep 35 seconds to stay under the 2 downloads/minute API limit
    time.sleep(35)

# 4. Logout to free up active session slots
requests.post(f"{BASE_URL}/auth/logout", headers={"Authorization": f"Bearer {refresh_token}"})


