import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "headlines.json"

URL = "https://www.servustv.com/de/nachrichten"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def clean(text):
    return " ".join((text or "").split()).strip()


def get_meta(soup, key):
    tag = soup.find("meta", attrs={"property": key})
    if not tag:
        tag = soup.find("meta", attrs={"name": key})

    return clean(tag.get("content", "")) if tag else ""


def find_latest_news90():

    html = requests.get(URL, headers=HEADERS, timeout=30).text

    soup = BeautifulSoup(html, "html.parser")

    links = []

    for a in soup.find_all("a", href=True):

        href = a["href"]

        text = clean(a.get_text(" ", strip=True))

        combined = f"{text} {href}".lower()

        if "90-sekunden" in combined or "90 sekunden" in combined:

            if href.startswith("/"):
                href = "https://www.servustv.com" + href

            if href not in links:
                links.append(href)

    print("GEFUNDENE LINKS:", len(links))

    if not links:
        raise RuntimeError("Keine 90-Sekunden-Links gefunden.")

    return links[0]


def get_episode_data(url):

    html = requests.get(url, headers=HEADERS, timeout=30).text

    soup = BeautifulSoup(html, "html.parser")

    title = (
        get_meta(soup, "og:title")
        or clean(soup.title.text)
    )

    desc = get_meta(soup, "og:description")

    image = get_meta(soup, "og:image")

    return {
        "title": title,
        "url": url,
        "image": image,
        "description": desc
    }


def main():

    latest_url = find_latest_news90()

    print("NEUESTE FOLGE:", latest_url)

    data = get_episode_data(latest_url)

    ticker = data["title"]

    result = {
        "title": data["title"],
        "short_title": data["title"],
        "full_title": data["title"],

        "url": data["url"],
        "href": data["url"],

        "image": data["image"],
        "thumbnail": data["image"],

        "news90_title": data["title"],
        "news90_link": data["url"],
        "news90_image": data["image"],
        "news90_thumbnail": data["image"],

        "topics": [ticker],

        "ticker": ticker,
        "ticker90": ticker,
        "topmeldung90": ticker,

        "description": data["description"]
    }

    old = {}

    if JSON_PATH.exists():
        try:
            old = json.loads(JSON_PATH.read_text(encoding="utf-8"))
        except:
            pass

    if "google_headlines" in old:
        result["google_headlines"] = old["google_headlines"]

    JSON_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("AKTUALISIERT:")
    print(data["title"])


if __name__ == "__main__":
    main()
