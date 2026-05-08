import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "headlines.json"

SEARCH_URL = "https://www.servustv.com/de/suche/?q=Servus%20Nachrichten%20in%2090%20Sekunden"
BASE_URL = "https://www.servustv.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def clean(text):
    return " ".join((text or "").split()).strip()


def get_meta(soup, key):
    tag = soup.find("meta", attrs={"property": key}) or soup.find("meta", attrs={"name": key})
    return clean(tag.get("content", "")) if tag else ""


def main():
    old = {}
    if JSON_PATH.exists():
        try:
            old = json.loads(JSON_PATH.read_text(encoding="utf-8"))
        except Exception:
            old = {}

    html = requests.get(SEARCH_URL, headers=HEADERS, timeout=20).text
    soup = BeautifulSoup(html, "html.parser")

    links = []

    for a in soup.find_all("a", href=True):
        href = urljoin(BASE_URL, a["href"]).split("?")[0].rstrip("/")
        text = clean(a.get_text(" ", strip=True))
        combo = f"{href} {text}".lower()

        if "/de/page/" in href and "servus-nachrichten-in-90-sekunden" in combo:
            if href not in links:
                links.append(href)

    if not links:
        # Notfall: alte Daten behalten, statt Action rot zu machen
        if old:
            print("Keine neue Folge gefunden, behalte alte headlines.json")
            return
        raise RuntimeError("Keine 90-Sekunden-Folgen gefunden.")

    latest_url = links[0]

    episode_html = requests.get(latest_url, headers=HEADERS, timeout=20).text
    episode_soup = BeautifulSoup(episode_html, "html.parser")

    title = get_meta(episode_soup, "og:title")
    description = get_meta(episode_soup, "og:description")
    image = get_meta(episode_soup, "og:image")

    if not title:
        h1 = episode_soup.find("h1")
        title = clean(h1.get_text(" ", strip=True)) if h1 else "Servus Nachrichten in 90 Sekunden"

    ticker_source = description or title
    topics = [clean(x) for x in re.split(r"\s*\|\s*", ticker_source) if clean(x)]
    topics = topics[:3] if topics else [title]
    ticker = " | ".join(topics)

    data = {
        "title": title,
        "short_title": title,
        "full_title": title,
        "url": latest_url,
        "href": latest_url,
        "image": image,
        "thumbnail": image,

        "news90_title": title,
        "news90_link": latest_url,
        "news90_image": image,
        "news90_thumbnail": image,

        "topics": topics,
        "ticker": ticker,
        "ticker90": ticker,
        "topmeldung90": ticker,
        "description": description
    }

    if "google_headlines" in old:
        data["google_headlines"] = old["google_headlines"]

    JSON_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("headlines.json aktualisiert:")
    print(data["news90_title"])
    print(data["news90_link"])
    print(data["ticker"])


if __name__ == "__main__":
    main()
