import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "headlines.json"

SERIES_URL = "https://www.servustv.com/de/page/AAYGF2URW6ALQYE42IJK"
SEARCH_URL = "https://www.servustv.com/de/suche/?q=Servus%20Nachrichten%20in%2090%20Sekunden"
BASE_URL = "https://www.servustv.com"

HEADERS = {"User-Agent": "Mozilla/5.0"}


def clean(text):
    return " ".join((text or "").split()).strip()


def get_meta(soup, key):
    tag = soup.find("meta", attrs={"property": key}) or soup.find("meta", attrs={"name": key})
    return clean(tag.get("content", "")) if tag else ""


def collect_episode_links(html):
    links = []

    patterns = [
        r'https://www\.servustv\.com/de/page/[A-Z0-9]+/servus-nachrichten-in-90-sekunden[^"\'>\s<]*',
        r'/de/page/[A-Z0-9]+/servus-nachrichten-in-90-sekunden[^"\'>\s<]*'
    ]

    for pattern in patterns:
        for match in re.findall(pattern, html, flags=re.I):
            url = urljoin(BASE_URL, match)
            url = url.split("?")[0].rstrip("/")
            if url not in links:
                links.append(url)

    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        href = urljoin(BASE_URL, a["href"]).split("?")[0].rstrip("/")
        if "servus-nachrichten-in-90-sekunden" in href.lower() and href not in links:
            links.append(href)

    return links


def pick_latest():
    all_links = []

    for url in [SERIES_URL, SEARCH_URL]:
        html = requests.get(url, headers=HEADERS, timeout=20).text
        all_links.extend(collect_episode_links(html))

    links = []
    for link in all_links:
        if link not in links:
            links.append(link)

    for link in links:
        html = requests.get(link, headers=HEADERS, timeout=20).text
        soup = BeautifulSoup(html, "html.parser")

        title = get_meta(soup, "og:title")
        desc = get_meta(soup, "og:description")
        image = get_meta(soup, "og:image")

        if not title:
            h1 = soup.find("h1")
            title = clean(h1.get_text(" ", strip=True)) if h1 else ""

        if "servus nachrichten: aktuelle meldungen" in title.lower():
            continue

        if not image:
            continue

        ticker_source = desc or title
        topics = [clean(x) for x in ticker_source.split("|") if clean(x)]
        if not topics:
            topics = [title]

        topics = topics[:3]
        ticker = " | ".join(topics)

        return {
            "title": title,
            "short_title": title,
            "full_title": title,
            "url": link,
            "href": link,
            "image": image,
            "thumbnail": image,

            "news90_title": title,
            "news90_link": link,
            "news90_image": image,
            "news90_thumbnail": image,
            "ticker90": ticker,
            "topmeldung90": ticker,
            "ticker": ticker,
            "topics": topics,
            "description": desc,
            "series_url": SERIES_URL
        }

    raise RuntimeError("Keine echte aktuelle 90-Sekunden-Folge gefunden.")


def main():
    old = {}
    if JSON_PATH.exists():
        try:
            old = json.loads(JSON_PATH.read_text(encoding="utf-8"))
        except Exception:
            old = {}

    data = pick_latest()

    if "google_headlines" in old:
        data["google_headlines"] = old["google_headlines"]

    JSON_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("headlines.json aktualisiert:")
    print(data["news90_title"])
    print(data["news90_link"])
    print(data["news90_image"])
    print(data["ticker"])


if __name__ == "__main__":
    main()
