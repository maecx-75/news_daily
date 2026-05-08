import json
import re
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "headlines.json"

SERIES_URL = "https://www.servustv.com/de/page/AA-1Y5RJCD1H2111"
BASE_URL = "https://www.servustv.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def clean(text):
    return " ".join((text or "").split()).strip()


def find_image_near_link(a):
    parent = a
    for _ in range(5):
        if not parent:
            break

        img = parent.find("img")
        if img:
            src = (
                img.get("src")
                or img.get("data-src")
                or img.get("data-lazy-src")
                or img.get("srcset", "").split(" ")[0]
            )
            if src:
                return urljoin(BASE_URL, src)

        style = parent.get("style", "")
        match = re.search(r"url\(['\"]?(.*?)['\"]?\)", style)
        if match:
            return urljoin(BASE_URL, match.group(1))

        parent = parent.parent

    return ""


def pick_latest():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=HEADERS["User-Agent"])
        page.goto(SERIES_URL, wait_until="networkidle", timeout=60000)
        html = page.content()
        browser.close()

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

        image = find_image_near_link(a)

        if text:
            candidates.append({
                "title": text,
                "url": href,
                "href": href,
                "image": image
            })

    if not candidates:
        raise RuntimeError("Keine aktuelle 90-Sekunden-Folge gefunden.")

    latest = candidates[0]

    title = latest["title"]

    parts = [p.strip() for p in title.split("|") if p.strip()]
    topics = parts[:3] if len(parts) >= 2 else [title]

    latest["topics"] = topics
    latest["ticker"] = " | ".join(topics)
    latest["series_url"] = SERIES_URL

    return latest


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
