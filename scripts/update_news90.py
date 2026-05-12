import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "headlines.json"

API_KEY = "AIzaSyCABRNljVUEN_TP7zJrUzzpLGyf9M0H7Pc"
CX = "721b47015e9f54c93"

SEARCH_URL = "https://www.googleapis.com/customsearch/v1"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def clean(text):
    return " ".join((text or "").split()).strip()


def search_latest_news90():
    params = {
        "key": API_KEY,
        "cx": CX,
        "q": "Servus Nachrichten in 90 Sekunden",
        "num": 10,
        "sort": "date"
    }

    r = requests.get(SEARCH_URL, params=params, headers=HEADERS, timeout=30)
    data = r.json()

    items = data.get("items", [])

    if not items:
        raise RuntimeError("Keine Google-Ergebnisse gefunden.")

    for item in items:
        title = clean(item.get("title", ""))
        link = item.get("link", "")
        snippet = clean(item.get("snippet", ""))

        lower = f"{title} {snippet}".lower()

        if (
            "90 sekunden" in lower
            and "servustv.com" in link
        ):
            return {
                "title": title,
                "url": link,
                "snippet": snippet
            }

    raise RuntimeError("Keine passende 90-Sekunden-Folge gefunden.")


def get_meta(url):
    html = requests.get(url, headers=HEADERS, timeout=30).text

    image = ""

    og_image = 'property="og:image" content="'

    if og_image in html:
        image = html.split(og_image)[1].split('"')[0]

    return image


def main():
    old = {}

    if JSON_PATH.exists():
        try:
            old = json.loads(JSON_PATH.read_text(encoding="utf-8"))
        except Exception:
            old = {}

    latest = search_latest_news90()

    image = get_meta(latest["url"])

    title = latest["title"]

    ticker = title.replace(" - Aktuelle Folge", "")

    result = {
        "title": title,
        "short_title": title,
        "full_title": title,

        "url": latest["url"],
        "href": latest["url"],

        "image": image,
        "thumbnail": image,

        "news90_title": title,
        "news90_link": latest["url"],
        "news90_image": image,
        "news90_thumbnail": image,

        "topics": [ticker],

        "ticker": ticker,
        "ticker90": ticker,
        "topmeldung90": ticker,

        "description": latest["snippet"]
    }

    if "google_headlines" in old:
        result["google_headlines"] = old["google_headlines"]

    JSON_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("AKTUELLE 90-SEKUNDEN-FOLGE:")
    print(title)
    print(latest["url"])
    print(image)


if __name__ == "__main__":
    main()
