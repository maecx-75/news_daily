import requests

URL = "https://www.servustv.com/de/page/AA-1Y5RJCD1H2111"
RAIL_ID = "f7c25019-f876-44ee-ab56-02e0d7bd231e"

html = requests.get(
    URL,
    headers={"User-Agent": "Mozilla/5.0"},
    timeout=30
).text

idx = html.find(RAIL_ID)

print("RAIL INDEX:", idx)

if idx != -1:
    snippet = html[idx:idx+20000]
    print(snippet)
else:
    print("RAIL NICHT GEFUNDEN")
