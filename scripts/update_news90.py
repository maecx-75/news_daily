import json
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "headlines.json"

LATEST_URL = "https://www.servustv.com/de/page/AA-1Y5RJCD1H2111"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def clean(text):
    return " ".join((text or "").split()).strip()


def meta(soup, prop):
    tag = soup.find("meta", attrs={"property": prop}) or soup.find("meta", attrs={"name": prop})
    return clean(tag.get("content", "")) if tag else ""


def main():
    html = requests.get(LATEST_URL, headers=HEADERS, timeout=20).text
    soup = BeautifulSoup(html, "html.parser")

    title = meta(soup, "og:title") or "Servus Nachrichten in 90 Sekunden"
    description = meta(soup, "og:description")
    image = meta(soup, "og:image")

    # Laufband: wenn Beschreibung Themen mit | enthält, nimm max. 3 Teile
    source = description or title
    topics = [clean(x) for x in source.split("|") if clean(x)]
    if len(topics) < 2:
        topics = [title]

    topics = topics[:3]

    data = {
        "title": title,
        "short_title": title,
        "full_title": title,
        "url": LATEST_URL,
        "href": LATEST_URL,
        "image": image,
        "thumbnail": image,
        "topics": topics,
        "ticker": " | ".join(topics),
        "description": description
    }

    JSON_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("headlines.json aktualisiert")
    print(title)
    print(LATEST_URL)
    print(image)
    print("Ticker:", data["ticker"])


if __name__ == "__main__":
    main()
