import requests, zipfile, io

URL = "https://www.go-metro.com/wp-content/uploads/2024/12/google_transit-1.zip"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"}

r = requests.get(URL, headers=HEADERS, timeout=30)
print("HTTP status:", r.status_code, "| size:", len(r.content), "bytes")
r.raise_for_status()

with zipfile.ZipFile(io.BytesIO(r.content)) as z:
    print("Files inside:", z.namelist())
    z.extractall("gtfs")
print("Unzipped into the 'gtfs' folder")