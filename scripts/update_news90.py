import re
import requests

URL = "https://www.servustv.com/de/page/AA-1Y5RJCD1H2111"

html = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30).text

keywords = [
    "Iran-Krieg",
    "Arda Saatci",
    "Iran droht Europa",
    "Geld-Transporte",
    "Virus-Schiff",
    "Servus Nachrichten in 90 Sekunden"
]

for kw in keywords:
    idx = html.find(kw)
    print("KEYWORD:", kw, "INDEX:", idx)

    if idx != -1:
        start = max(0, idx - 1500)
        end = min(len(html), idx + 2500)
        snippet = html[start:end]

        print("===== SNIPPET START =====")
        print(snippet)
        print("===== SNIPPET END =====")
