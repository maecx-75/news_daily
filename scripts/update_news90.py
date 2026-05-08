import json
import re
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "headlines.json"

PAGE_URL = "https://www.servustv.com/de/page/AA-1Y5RJCD1H2111"
BASE_URL = "https://www.servustv.com"


def clean(text):
    return " ".join((text or "").split()).strip()


def meta(soup, key):
    tag = soup.find("meta", attrs={"property": key}) or soup.find("meta", attrs={"name": key})
    return clean(tag.get("content", "")) if tag else ""


def get_episode_data(url, page):
    page.goto(url, wait_until="networkidle", timeout=60000)
    html = page.content()
    soup = BeautifulSoup(html, "html.parser")

    title = meta(soup, "og:title") or clean(soup.find("h1").get_text(" ", strip=True) if soup.find("h1") else "")
    desc = meta(soup, "og:description")
    image = meta(soup, "og:image")

    return {
        "title": title or "Servus Nachrichten in 90 Sekunden",
        "description": desc,
        "image": image,
        "url": url
    }


def main():
    old = {}
    if JSON_PATH.exists():
        try:
            old = json.loads(JSON_PATH.read_text(encoding="utf-8"))
        except Exception:
            old = {}

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"
        )

        page.goto(PAGE_URL, wait_until="networkidle", timeout=60000)

        for _ in range(8):
            page.mouse.wheel(0, 1600)
            page.wait_for_timeout(1200)

        links = page.eval_on_selector_all(
            "a[href]",
            """
            els => els.map(a => ({
                href: a.href,
                text: (a.innerText || a.textContent || "").trim()
            }))
            """
        )

        browser.close()

    candidates = []

    for item in links:
        href = item.get("href", "")
        text = item.get("text", "")
        combo = (href + " " + text).lower()

        if "/de/page/" not in href:
            continue

        if "aa-1y5rjcd1h2111" in href.lower():
            continue

        if (
            "servus-nachrichten-in-90-sekunden" in combo
            or "nachrichten in 90 sekunden" in combo
            or "90 sekunden" in combo
        ):
            clean_url = href.split("?")[0].rstrip("/")
            if clean_url not in candidates:
                candidates.append(clean_url)

    if not candidates:
        raise RuntimeError("Keine 90-Sekunden-Folgen auf der Seite gefunden.")

    latest_url = candidates[0]

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"
        )
        episode = get_episode_data(latest_url, page)
        browser.close()

    title = episode["title"]
    desc = episode["description"]
    image = episode["image"]

    ticker_source = desc or title
    topics = [clean(x) for x in re.split(r"\s*\|\s*", ticker_source) if clean(x)]
    if not topics:
        topics = [title]
    topics = topics[:3]

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
        "ticker": " | ".join(topics),
        "ticker90": " | ".join(topics),
        "topmeldung90": " | ".join(topics),
        "description": desc
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
