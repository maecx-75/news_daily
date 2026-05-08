import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "weather90.json"

SERIES_URL = "https://www.servustv.com/de/page/AA90VBHT0KRB2CMU1AHQ"
BASE_URL = "https://www.servustv.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def pick_latest():
    html = requests.get(SERIES_URL, headers=HEADERS, timeout=20).text
    soup = BeautifulSoup(html, "html.parser")

    candidates = []

    for a in soup.find_all("a", href=True):
        text = " ".join(a.get_text(" ", strip=True).split())
        href = urljoin(BASE_URL, a["href"])

        if "servus-wetter-in-90-sekunden" in href.lower():
            if text:
                candidates.append((text, href))

    if not candidates:
        # Fallback: Google/ServusTV liefert einzelne Folgen oft direkt in der Suche
        search_url = "https://www.servustv.com/de/suche/?q=Servus%20Wetter%20in%2090%20Sekunden"
        html = requests.get(search_url, headers=HEADERS, timeout=20).text
        soup = BeautifulSoup(html, "html.parser")

        for a in soup.find_all("a", href=True):
            text = " ".join(a.get_text(" ", strip=True).split())
            href = urljoin(BASE_URL, a["href"])

            if "servus-wetter-in-90-sekunden" in href.lower():
                if text:
                    candidates.append((text, href))

    if not candidates:
        raise RuntimeError("Keinen Wetter-90-Eintrag gefunden.")

    full_title, href = candidates[0]

    short_title = re.sub(r"\s*·?\s*Servus Wetter in 90 Sekunden.*", "", full_title).strip()
    if not short_title:
        short_title = "Servus Wetter in 90 Sekunden"

    return short_title, full_title, href


def main():
    short_title, full_title, href = pick_latest()

    data = {
        "title": short_title,
        "short_title": short_title,
        "full_title": full_title,
        "url": href,
        "href": href,
        "series_url": SERIES_URL
    }

    JSON_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("weather90.json aktualisiert:")
    print(short_title)
    print(href)


if __name__ == "__main__":
    main()
