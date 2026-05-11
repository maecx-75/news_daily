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

    if not title:
        h1 = soup.find("h1")
        title = clean(h1.get_text(" ", strip=True)) if h1 else ""

    return title, desc, image


def get_episode_ticker(url):
    try:
        html = requests.get(url, headers=HEADERS, timeout=20).text
        soup = BeautifulSoup(html, "html.parser")
        full_text = soup.get_text(" ", strip=True)

        match = re.search(
            r"Servus Nachrichten in 90 Sekunden\s*(.*?)\s*Jetzt ansehen",
            full_text,
            re.I
        )

        if match:
            return clean(match.group(1))

    except Exception as e:
        print("Ticker konnte nicht gelesen werden:", e)

    return ""


def find_first_news90_card():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=HEADERS["User-Agent"])

        page.goto(PAGE_URL, wait_until="networkidle", timeout=60000)

        # Zur Reihe "Servus Nachrichten in 90 Sekunden" springen
        page.evaluate("""
            () => {
              const target = [...document.querySelectorAll('h1,h2,h3,h4,div,span')]
                .find(el => (el.innerText || '').trim() === 'Servus Nachrichten in 90 Sekunden');
              if (target) target.scrollIntoView({block:'center'});
            }
        """)

        page.wait_for_timeout(2000)

        # Zur Sicherheit noch minimal scrollen, damit Karten wirklich geladen sind
        page.mouse.wheel(0, 300)
        page.wait_for_timeout(1500)

        cards = page.evaluate("""
            () => {
              const heading = [...document.querySelectorAll('h1,h2,h3,h4,div,span')]
                .find(el => (el.innerText || '').trim() === 'Servus Nachrichten in 90 Sekunden');

              if (!heading) return [];

              const headingY = heading.getBoundingClientRect().top + window.scrollY;

              const all = [...document.querySelectorAll('a[href]')]
                .map(a => {
                  const r = a.getBoundingClientRect();
                  const text = (a.innerText || a.textContent || '').trim();
                  const img = a.querySelector('img');
                  const image =
                    img?.currentSrc ||
                    img?.src ||
                    img?.getAttribute('data-src') ||
                    '';

                  return {
                    href: a.href,
                    text,
                    image,
                    x: r.left,
                    y: r.top + window.scrollY,
                    width: r.width,
                    height: r.height
                  };
                })
                .filter(item =>
                  item.href.includes('/de/page/') &&
                  item.y > headingY &&
                  item.width > 120 &&
                  item.height > 80 &&
                  item.text &&
                  item.text.toLowerCase().includes('servus nachrichten in 90 sekunden')
                )
                .sort((a,b) => {
                  if (Math.abs(a.y - b.y) > 80) return a.y - b.y;
                  return a.x - b.x;
                });

              return all;
            }
        """)

        browser.close()

    if not cards:
        raise RuntimeError("Keine sichtbare News-90-Kachel gefunden.")

    first = cards[0]

    return {
        "url": first["href"].split("&")[0],
        "card_text": clean(first["text"]),
        "card_image": first["image"]
    }


def main():
    old = {}
    if JSON_PATH.exists():
        try:
            old = json.loads(JSON_PATH.read_text(encoding="utf-8"))
        except Exception:
            old = {}

    card = find_first_news90_card()

    title, desc, image = get_episode_meta(card["url"])

    if not title:
        # Kartentext bereinigen
        title = card["card_text"]
        title = title.replace("2 Min.", "").replace("Servus Nachrichten in 90 Sekunden", "")
        title = clean(title)

    if not image:
        image = card["card_image"] or "news90.png"

    ticker = get_episode_ticker(card["url"])

    if not ticker:
        ticker = title

    topics = [clean(x) for x in ticker.split("|") if clean(x)]
    topics = topics[:3] if topics else [title]
    ticker = " | ".join(topics)

    data = {
        "title": title,
        "short_title": title,
        "full_title": title,
        "url": card["url"],
        "href": card["url"],
        "image": image,
        "thumbnail": image,

        "news90_title": title,
        "news90_link": card["url"],
        "news90_image": image,
        "news90_thumbnail": image,

        "topics": topics,
        "ticker": ticker,
        "ticker90": ticker,
        "topmeldung90": ticker,
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
