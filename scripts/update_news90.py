import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "headlines.json"

PAGE_URL = "https://www.servustv.com/de/page/AA-1Y5RJCD1H2111"
BASE_URL = "https://www.servustv.com"

FALLBACK_URL = "https://www.servustv.com/de/page/AASN6K1VFDPTJSY6YQ5D?cid=f7c25019-f876-44ee-ab56-02e0d7bd231e"

HEADERS = {"User-Agent": "Mozilla/5.0"}


def clean(text):
    return " ".join((text or "").split()).strip()


def get_meta(soup, key):
    tag = soup.find("meta", attrs={"property": key}) or soup.find("meta", attrs={"name": key})
    return clean(tag.get("content", "")) if tag else ""


def get_episode_meta(url):
    html = requests.get(url, headers=HEADERS, timeout=20).text
    soup = BeautifulSoup(html, "html.parser")

    title = get_meta(soup, "og:title")
    desc = get_meta(soup, "og:description")
    image = get_meta(soup, "og:image")

    return title, desc, image


def get_episode_ticker(url):
    ticker = ""

    try:
        html = requests.get(url, headers=HEADERS, timeout=20).text
        soup = BeautifulSoup(html, "html.parser")
        full_text = soup.get_text(" ", strip=True)

        match = re.search(
            r"([A-ZÄÖÜ][^|]{5,120}\s*\|\s*[^|]{5,120}\s*\|\s*[^|]{5,120})\s+(Jetzt ansehen|Serie anzeigen)",
            full_text
        )

        if match:
            ticker = clean(match.group(1))

    except Exception as e:
        print("Ticker konnte nicht gelesen werden:", e)

    return ticker


def main():
    old = {}
    if JSON_PATH.exists():
        try:
            old = json.loads(JSON_PATH.read_text(encoding="utf-8"))
        except Exception:
            old = {}

    latest = None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(user_agent=HEADERS["User-Agent"])

            page.goto(PAGE_URL, wait_until="networkidle", timeout=60000)

            for _ in range(10):
                page.mouse.wheel(0, 1800)
                page.wait_for_timeout(800)

            html = page.content()
            browser.close()

        urls = []

        for match in re.findall(
            r"https://www\.servustv\.com/de/page/[A-Z0-9-]+(?:\?cid=[a-z0-9-]+)?",
            html,
            re.I
        ):
            clean_url = match.strip()
            if clean_url not in urls and "AA-1Y5RJCD1H2111" not in clean_url:
                urls.append(clean_url)

        soup = BeautifulSoup(html, "html.parser")

        for a in soup.find_all("a", href=True):
            href = urljoin(BASE_URL, a["href"])
            if "/de/page/" in href and "AA-1Y5RJCD1H2111" not in href:
                if href not in urls:
                    urls.append(href)

        for url in urls[:60]:
            try:
                title, desc, image = get_episode_meta(url)
            except Exception:
                continue

            combo = f"{title} {desc}".lower()

            if "servus nachrichten in 90 sekunden" in combo:
                latest = {
                    "url": url,
                    "title": title or "Servus Nachrichten in 90 Sekunden",
                    "description": desc,
                    "image": image or "news90.png"
                }
                break

    except Exception as e:
        print("Scraper-Fehler:", e)

    if not latest:
        title, desc, image = get_episode_meta(FALLBACK_URL)

        latest = {
            "url": FALLBACK_URL,
            "title": title or "Servus Nachrichten in 90 Sekunden",
            "description": desc or "Aktuelle Folge",
            "image": image or "news90.png"
        }

    ticker = get_episode_ticker(latest["url"])

    if not ticker:
        ticker = latest["title"]

    topics = [clean(x) for x in ticker.split("|") if clean(x)]
    topics = topics[:3] if topics else [latest["title"]]
    ticker = " | ".join(topics)

    data = {
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
