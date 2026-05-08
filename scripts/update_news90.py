import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "headlines.json"

SERIES_URL = "https://www.servustv.com/de/page/AAYGF2URW6ALQYE42IJK"
BASE_URL = "https://www.servustv.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def clean(text):
    return " ".join((text or "").split()).strip()


def get_meta(soup, name):
    tag = soup.find("meta", attrs={"property": name}) or soup.find("meta", attrs={"name": name})
    return tag.get("content", "").strip() if tag else ""


def pick_latest():
    html = requests.get(SERIES_URL, headers=HEADERS, timeout=20).text
    soup = BeautifulSoup(html, "html.parser")

    candidates = []

    for a in soup.find_all("a", href=True):
        href = urljoin(BASE_URL, a["href"])
        text = clean(a.get_text(" ", strip=True))
        combo = f"{text} {href}".lower()

        if "servus-nachrichten-in-90-sekunden" not in combo:
            continue

        if href.rstrip("/") == SERIES_URL.rstrip("/"):
            continue

        if "/de/page/" not in href:
            continue

        candidates.append(href)

    # Fallback: falls ServusTV die Links nicht sichtbar rendert
    if not candidates:
        search_html = requests.get(
            "https://www.servustv.com/de/suche/?q=Servus%20Nachrichten%20in%2090%20Sekunden",
            headers=HEADERS,
            timeout=20
        ).text
        search_soup = BeautifulSoup(search_html, "html.parser")

        for a in search_soup.find_all("a", href=True):
            href = urljoin(BASE_URL, a["href"])
            combo = f"{a.get_text(' ', strip=True)} {href}".lower()

            if "servus-nachrichten-in-90-sekunden" in combo and "/de/page/" in href:
                candidates.append(href)

    if not candidates:
        raise RuntimeError("Keine aktuelle 90-Sekunden-Folge gefunden.")

    latest_url = candidates[0]

    episode_html = requests.get(latest_url, headers=HEADERS, timeout=20).text
    episode_soup = BeautifulSoup(episode_html, "html.parser")

    page_title = clean(get_meta(episode_soup, "og:title"))
    page_desc = clean(get_meta(episode_soup, "og:description"))
    image = get_meta(episode_soup, "og:image")

    if not page_title:
        h1 = episode_soup.find(["h1", "h2", "h3"])
        page_title = clean(h1.get_text(" ", strip=True)) if h1 else "Servus Nachrichten in 90 Sekunden"

    ticker_source = page_desc or page_title
    topics = [clean(x) for x in re.split(r"\s*\|\s*", ticker_source) if clean(x)]
    topics = topics[:3] if topics else [page_title]

    return {
        "title": page_title,
        "short_title": page_title,
        "full_title": page_title,
        "url": latest_url,
        "href": latest_url,
        "image": image,
        "thumbnail": image,
        "topics": topics,
        "ticker": " | ".join(topics),
        "series_url": SERIES_URL
    }


def main():
    data = pick_latest()

    JSON_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("headlines.json aktualisiert:")
    print(data["title"])
    print(data["url"])
    print(data.get("image", "kein Bild gefunden"))
    print(data.get("ticker", ""))


if __name__ == "__main__":
    main()
