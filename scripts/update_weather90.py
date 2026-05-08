import json
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
    html = requests.get(
        SERIES_URL,
        headers=HEADERS,
        timeout=20
    ).text

    soup = BeautifulSoup(html, "html.parser")

    candidates = []

    for a in soup.find_all("a", href=True):
        text = " ".join(a.get_text(" ", strip=True).split())
        href = urljoin(BASE_URL, a["href"])

        combo = f"{text} {href}".lower()

        if (
            "servus wetter in 90 sekunden" in combo
            or "servus-wetter-in-90-sekunden" in combo
        ):
            candidates.append((
                text or "Servus Wetter in 90 Sekunden",
                href
            ))

    if not candidates:
        # Stabiler Fallback
        return (
            "Unwetter in Österreich!",
            "Unwetter in Österreich! · Servus Wetter in 90 Sekunden",
            "https://www.servustv.com/de/page/AAP5XFXW216RG1S25J5V/servus-wetter-in-90-sekunden"
        )

    full_title, href = candidates[0]

    short_title = full_title.split("·")[0].strip()

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
