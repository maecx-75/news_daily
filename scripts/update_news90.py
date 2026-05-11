import json
import requests

API_URL = "https://tv-api.redbull.com/products/dynamic/v5.1/stv/de/us/AA-1Y5RJCD1H2111"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json"
}

def collect_strings(obj, out):
    if isinstance(obj, dict):
        for v in obj.values():
            collect_strings(v, out)
    elif isinstance(obj, list):
        for item in obj:
            collect_strings(item, out)
    elif isinstance(obj, str):
        out.append(obj)

def main():
    res = requests.get(API_URL, headers=HEADERS, timeout=30)

    print("STATUS:", res.status_code)
    print("CONTENT-TYPE:", res.headers.get("content-type"))

    data = res.json()

    strings = []
    collect_strings(data, strings)

    print("ANZAHL STRINGS:", len(strings))

    print("TREFFER MIT 90 / sekunden / Iran / Servus:")
    for s in strings:
        low = s.lower()
        if "90" in low or "sekunden" in low or "iran" in low or "servus" in low:
            print("---")
            print(s[:500])

    print("ERSTE 80 STRINGS:")
    for s in strings[:80]:
        print("---")
        print(s[:300])

if __name__ == "__main__":
    main()
