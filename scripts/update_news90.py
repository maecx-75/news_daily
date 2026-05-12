import json
import re
from pathlib import Path
from urllib.parse import urljoin, unquote

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "headlines.json"

SEARCH_URL = "https://www.servustv.com/de/search?q=Servus%20Nachrichten%20in%2090%20Sekunden"
BASE_URL = "https://www.servustv.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def clean(text):
    return " ".join(str(text or "").split()).strip()


def get_meta(soup, key):
    tag = soup.find("meta", attrs={"property": key}) or soup.find("meta", attrs={"name": key})
    return clean(tag.get("content", "")) if tag else ""


def get_episode_meta(url):
    html = requests.get(url, headers=HEADERS, timeout=30).text
    soup = BeautifulSoup(html, "html.parser")

    title = get_meta(soup, "og:title")
    desc = get_meta(soup, "og:description")
    image = get_meta(soup, "og:image")
    text = soup.get_text(" ", strip=True)

    return title, desc, image, text


def get_ticker(text):
    match = re.search(
        r"Servus Nachrichten in 90 Sekunden\s*(.*?)\s*Jetzt ansehen",
        text,
        re.I
    )

    if match:
        return clean(match.group(1))

    return ""


def collect_episode_links():
    html = requests.get(SEARCH_URL, headers=HEADERS, timeout=30).text
    soup = BeautifulSoup(html, "html.parser")

    links = []

    # normale Links
    for a in soup.find_all("a", href=True):
        href = urljoin(BASE_URL, a["href"])
        href = unquote(href)

        if "/de/page/" in href and href not in links:
            links.append(href)

    # Links im HTML/JSON
    for match in re.findall(r"https://www\.servustv\.com/de/page/[A-Z0-9]+[^\"'<>\s]*", html):
        href = unquote(match)
        if href not in links:
            links.append(href)

    return links


def main():
    old = {}

    if JSON_PATH.exists():
        try:
            old = json.loads(JSON_PATH.read_text(encoding="utf-8"))
        except Exception:
            old = {}

    links = collect_episode_links()

    if not links:
        raise RuntimeError("Keine Links in der ServusTV-Suche gefunden.")

    latest = None

    for link in links[:30]:
        try:
            title, desc, image, text = get_episode_meta(link)
        except Exception:
            continue

        check = f"{title} {desc} {text}".lower()

        if "servus nachrichten in 90 sekunden" in check:
            latest = {
                "url": link,
                "title": title or "Servus Nachrichten in 90 Sekunden",
                "description": desc,
                "image": image or "news90.png",
                "text": text
            }
            break

    if not latest:
        raise RuntimeError("Keine echte Servus-Nachrichten-90-Sekunden-Folge gefunden.")

    ticker = get_ticker(latest["text"])

    if not ticker:
        ticker = latest["title"]

    topics = [clean(x) for x in ticker.split("|") if clean(x)]
    topics = topics[:3] if topics else [latest["title"]]
    ticker = " | ".join(topics)

    result = {
        "title": latest["title"],
        "short_title": latest["title"],
        "full_title": latest["title"],

        "url": latest["url"],
        "href": latest["url"],

        "image": latest["image"],
        "thumbnail": latest["image"],

        "news90_title": latest["title"],
        "news90_link": latest["url"],
        "news90_image": latest["image"],
        "news90_thumbnail": latest["image"],

        "topics": topics,

        "ticker": ticker,
        "ticker90": ticker,
        "topmeldung90": ticker,

        "description": latest["description"]
    }

    if "google_headlines" in old:
        result["google_headlines"] = old["google_headlines"]

    JSON_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("AKTUELLE 90-SEKUNDEN-FOLGE:")
    print(result["news90_title"])
    print(result["news90_link"])
    print(result["news90_image"])
    print(result["ticker"])


if __name__ == "__main__":
    main()
