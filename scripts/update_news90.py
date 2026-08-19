import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "headlines.json"
NEWS_URL = "https://www.servustv.com/de/nachrichten"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36",
    "Accept-Language": "de-AT,de;q=0.9,en;q=0.7",
}


def clean_title(text):
    text = " ".join((text or "").split())
    text = re.sub(r"\s*\|\s*(Servus )?Nachrichten in 90 Sekunden.*$", "", text, flags=re.I)
    text = re.sub(r"\s*-\s*ServusTV On\s*$", "", text, flags=re.I)
    return text.strip()


def discover_with_browser():
    print("[INFO] Starte Chromium und rendere ServusTV-Nachrichtenseite …")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(locale="de-AT", user_agent=HEADERS["User-Agent"], viewport={"width": 1440, "height": 1200})
        page.goto(NEWS_URL, wait_until="domcontentloaded", timeout=60000)
        try:
            page.wait_for_load_state("networkidle", timeout=30000)
        except Exception:
            pass
        page.wait_for_timeout(5000)
        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "html.parser")
    candidates = []
    for a in soup.find_all("a", href=True):
        href = urljoin(NEWS_URL, a.get("href", ""))
        if "/de/page/" not in href:
            continue
        node = a
        combined = ""
        for _ in range(6):
            if node is None:
                break
            combined = " ".join(node.get_text(" ", strip=True).split())
            if "servus nachrichten in 90 sekunden" in combined.lower():
                break
            node = node.parent
        if "servus nachrichten in 90 sekunden" in combined.lower() and href not in candidates:
            candidates.append(href.split("?")[0])

    print(f"[INFO] {len(candidates)} Kandidaten in der gerenderten Seite gefunden.")
    return candidates


def extract_article_data(article_url):
    r = requests.get(article_url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    page_text = " ".join(soup.get_text(" ", strip=True).split())
    is_news90 = "servus nachrichten in 90 sekunden" in page_text.lower()

    title_candidates = []
    for tag in ("h1", "h2"):
        for node in soup.find_all(tag):
            title_candidates.append(node.get_text(" ", strip=True))
    for attrs in ({"property": "og:title"}, {"name": "twitter:title"}):
        meta = soup.find("meta", attrs=attrs)
        if meta and meta.get("content"):
            title_candidates.append(meta["content"])
    if soup.title:
        title_candidates.append(soup.title.get_text(" ", strip=True))

    title = ""
    for candidate in title_candidates:
        cleaned = clean_title(candidate)
        if cleaned and cleaned.lower() not in {"servus nachrichten in 90 sekunden", "nachrichten in 90 sekunden", "servustv on"}:
            title = cleaned
            break

    image = ""
    for attrs in ({"property": "og:image"}, {"name": "twitter:image"}):
        meta = soup.find("meta", attrs=attrs)
        if meta and meta.get("content"):
            image = urljoin(article_url, meta["content"])
            break
    return title, image, is_news90


def load_existing_data():
    try:
        return json.loads(JSON_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def get_latest_news90():
    try:
        candidates = discover_with_browser()
    except Exception as exc:
        print(f"[WARNUNG] Browser-Suche fehlgeschlagen: {exc}")
        candidates = []

    for index, href in enumerate(candidates[:30], 1):
        try:
            print(f"[INFO] Prüfe Kandidat {index}: {href}")
            title, image, is_news90 = extract_article_data(href)
            if not is_news90 or not title:
                continue

            data = load_existing_data()
            data["news90_title"] = title
            data["news90_link"] = href
            if image:
                data["news90_image"] = image
                data["news90_thumbnail"] = image
            JSON_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            print(f"[ERFOLG] Gefunden: {title}")
            print(f"[ERFOLG] Link: {href}")
            if image:
                print(f"[ERFOLG] Bild: {image}")
            print("[INFO] headlines.json aktualisiert.")
            return
        except Exception as exc:
            print(f"[WARNUNG] Kandidat konnte nicht verarbeitet werden: {exc}")

    print("[WARNUNG] Kein bestätigter 90-Sekunden-Beitrag gefunden.")
    print("[WARNUNG] Bestehende news90-Daten bleiben unverändert.")


if __name__ == "__main__":
    get_latest_news90()
