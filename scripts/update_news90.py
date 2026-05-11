import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "headlines.json"

API_URL = "https://tv-api.redbull.com/products/dynamic/v5.1/stv/de/us/AA-1Y5RJCD1H2111"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def clean(text):
    return " ".join((text or "").split()).strip()


def main():
    old = {}

    if JSON_PATH.exists():
        try:
            old = json.loads(JSON_PATH.read_text(encoding="utf-8"))
        except Exception:
            old = {}

    res = requests.get(API_URL, headers=HEADERS, timeout=30)
    data = res.json()

    cards = []

    def walk(obj):
        if isinstance(obj, dict):

            title = str(obj.get("title", ""))
            href = str(obj.get("href", ""))

            if (
                "90 Sekunden" in title
                and "/de/page/" in href
            ):
                cards.append(obj)

            for v in obj.values():
                walk(v)

        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(data)

    if not cards:
        raise RuntimeError("Keine 90-Sekunden-Folge gefunden.")

    first = cards[0]

    title = clean(first.get("title"))

    url = clean(first.get("href"))

    image = (
        first.get("image", {})
        .get("url")
        or "news90.png"
    )

    subtitle = clean(first.get("subtitle", ""))

    ticker = subtitle

    if "|" in ticker:
        parts = [clean(x) for x in ticker.split("|")]
        parts = parts[:3]
        ticker = " | ".join(parts)

    if not ticker:
        ticker = title

    result = {
        "title": title,
        "short_title": title,
        "full_title": title,

        "url": url,
        "href": url,

        "image": image,
        "thumbnail": image,

        "news90_title": title,
        "news90_link": url,
        "news90_image": image,
        "news90_thumbnail": image,

        "topics": ticker.split("|"),

        "ticker": ticker,
        "ticker90": ticker,
        "topmeldung90": ticker,

        "description": subtitle
    }

    if "google_headlines" in old:
        result["google_headlines"] = old["google_headlines"]

    JSON_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("AKTUELLE FOLGE:")
    print(title)
    print(url)
    print(image)
    print(ticker)


if __name__ == "__main__":
    main()
