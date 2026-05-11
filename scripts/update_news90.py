import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "headlines.json"

PAGE_URL = "https://www.servustv.com/de/page/AA-1Y5RJCD1H2111"
BASE_URL = "https://www.servustv.com/de/page/"
HEADERS = {"User-Agent": "Mozilla/5.0"}


def clean(text):
    return " ".join((text or "").split()).strip()


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


def find_latest_ids_and_images():
    seen = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            user_agent=HEADERS["User-Agent"],
            viewport={"width": 1600, "height": 1000}
        )

        def log_request(request):
            url = request.url

            m = re.search(
                r"https://resources\.redbull\.tv/([A-Z0-9]+)/rbtv_display_art_landscape/([^?]+)\?namespace=stv",
                url
            )

            if m:
                item_id = m.group(1)
                if item_id.startswith("AA") and item_id not in [x["id"] for x in seen]:
                    seen.append({
                        "id": item_id,
                        "image": url
                    })

        page.on("request", log_request)

        page.goto(PAGE_URL, wait_until="networkidle", timeout=60000)

        for _ in range(20):
            page.mouse.wheel(0, 1000)
            page.wait_for_timeout(800)

        browser.close()

    if not seen:
        raise RuntimeError("Keine Ressourcen-IDs gefunden.")

    # Die erste sichtbare 90-Sekunden-Kachel ist nach deinem Log die erste neue Ressourcen-ID
    return seen


def main():
    old = {}

    if JSON_PATH.exists():
        try:
            old = json.loads(JSON_PATH.read_text(encoding="utf-8"))
        except Exception:
            old = {}

    candidates = find_latest_ids_and_images()

latest = None

for candidate in candidates:
    page_url = BASE_URL + candidate["id"]

    title, desc, meta_image, text = get_episode_meta(page_url)

    check = f"{title} {desc} {text}".lower()

    if "servus nachrichten in 90 sekunden" in check:
        latest = {
            "id": candidate["id"],
            "image": candidate["image"],
            "page_url": page_url,
            "title": title,
            "desc": desc,
            "meta_image": meta_image,
            "text": text
        }
        break

if not latest:
    raise RuntimeError("Keine echte 90-Sekunden-Folge gefunden.")

    title, desc, meta_image, text = get_episode_meta(page_url)

    image = meta_image or latest["image"] or "news90.png"

    ticker = get_ticker(text)

    if not ticker:
        ticker = title or "Servus Nachrichten in 90 Sekunden"

    topics = [clean(x) for x in ticker.split("|") if clean(x)]
    topics = topics[:3] if topics else [title]
    ticker = " | ".join(topics)

    result = {
        "title": title,
        "short_title": title,
        "full_title": title,

        "url": page_url,
        "href": page_url,

        "image": image,
        "thumbnail": image,

        "news90_title": title,
        "news90_link": page_url,
        "news90_image": image,
        "news90_thumbnail": image,

        "topics": topics,

        "ticker": ticker,
        "ticker90": ticker,
        "topmeldung90": ticker,

        "description": desc
    }

    if "google_headlines" in old:
        result["google_headlines"] = old["google_headlines"]

    JSON_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("AKTUELLE 90-SEKUNDEN-FOLGE:")
    print(title)
    print(page_url)
    print(image)
    print(ticker)


if __name__ == "__main__":
    main()
