import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "headlines.json"

SEARCH_URL = "https://www.servustv.com/de/search?q=Servus%20Nachrichten%20in%2090%20Sekunden"
BASE_URL = "https://www.servustv.com"
HEADERS = {"User-Agent": "Mozilla/5.0"}


def clean(text):
    return " ".join(str(text or "").split()).strip()


def get_meta(soup, key):
    tag = soup.find("meta", attrs={"property": key}) or soup.find("meta", attrs={"name": key})
    return clean(tag.get("content", "")) if tag else ""


def normalize_page_url(raw):
    raw = raw.replace("page:", "")
    if raw.startswith("http"):
        return raw.split("?")[0]
    return urljoin(BASE_URL, raw).split("?")[0]


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
    return clean(match.group(1)) if match else ""


def collect_candidates():
    candidates = []
    response_bodies = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            user_agent=HEADERS["User-Agent"],
            viewport={"width": 1600, "height": 1000}
        )

        def handle_response(response):
            try:
                body = response.text()
            except Exception:
                return

            if "Servus Nachrichten in 90 Sekunden" in body:
                response_bodies.append(body)

        page.on("response", handle_response)

        page.goto(SEARCH_URL, wait_until="networkidle", timeout=60000)

        for _ in range(8):
            page.mouse.wheel(0, 1000)
            page.wait_for_timeout(800)

        html = page.content()

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

    # 1. Links aus sichtbaren Suchergebnissen
    for item in links:
        href = normalize_page_url(item.get("href", ""))
        text = item.get("text", "")

        if "/de/page/" in href:
            candidates.append({
                "url": href,
                "hint": text
            })

    # 2. IDs/Links aus HTML und Response-Bodies
    blob = html + "\n".join(response_bodies)

    for m in re.findall(r'https://www\.servustv\.com/de/page/(?:page:)?([A-Z0-9]+)', blob):
        candidates.append({
            "url": f"{BASE_URL}/de/page/{m}",
            "hint": ""
        })

    for m in re.findall(r'"detail_page_id"\s*:\s*"page:([A-Z0-9]+)"', blob):
        candidates.append({
            "url": f"{BASE_URL}/de/page/{m}",
            "hint": ""
        })

    for m in re.findall(r'"id"\s*:\s*"([A-Z0-9]{15,25})"', blob):
        candidates.append({
            "url": f"{BASE_URL}/de/page/{m}",
            "hint": ""
        })

    # Duplikate entfernen
    unique = []
    seen = set()

    for item in candidates:
        url = item["url"]

        if url in seen:
            continue

        if "AA-1Y5RJCD1H2111" in url:
            continue

        seen.add(url)
        unique.append(item)

    return unique


def main():
    old = {}

    if JSON_PATH.exists():
        try:
            old = json.loads(JSON_PATH.read_text(encoding="utf-8"))
        except Exception:
            old = {}

    candidates = collect_candidates()

    print("GEFUNDENE KANDIDATEN:", len(candidates))

    latest = None

    for item in candidates[:80]:
        url = item["url"]

        try:
            title, desc, image, text = get_episode_meta(url)
        except Exception:
            continue

        check = f"{title} {desc} {text}".lower()

        print("PRÜFE:", url)
        print("TITLE:", title)
        print("DESC:", desc)
        print("---")

        if "servus nachrichten in 90 sekunden" in check:
            latest = {
                "url": url,
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
