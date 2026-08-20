import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "headlines.json"

# Nur diese Servus-Nachrichten-Unterseite wird als Quelle verwendet.
SERIES_URL = "https://www.servustv.com/de/page/AA-1Y5RJCD1H2111"
SERIES_ID = "AA-1Y5RJCD1H2111"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36",
    "Accept-Language": "de-AT,de;q=0.9,en;q=0.7",
}


def clean_title(text):
    text = " ".join((text or "").split())
    text = re.sub(
        r"\s*\|\s*(Servus )?Nachrichten in 90 Sekunden.*$",
        "",
        text,
        flags=re.I,
    )
    text = re.sub(r"\s*-\s*ServusTV On\s*$", "", text, flags=re.I)
    return text.strip()


def normalize_candidate(url):
    if not url:
        return ""
    parsed = urlparse(urljoin(SERIES_URL, url))
    if parsed.netloc not in {"www.servustv.com", "servustv.com"}:
        return ""
    path = parsed.path.rstrip("/")
    if not re.fullmatch(r"/de/page/[A-Z0-9-]+", path, flags=re.I):
        return ""
    if SERIES_ID.lower() in path.lower():
        return ""
    return f"https://www.servustv.com{path}"


def discover_with_browser():
    print(f"[INFO] Öffne ausschließlich Servus-Nachrichten-Unterseite: {SERIES_URL}")
    candidates = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            locale="de-AT",
            user_agent=HEADERS["User-Agent"],
            viewport={"width": 1440, "height": 1800},
        )
        page = context.new_page()

        page.goto(SERIES_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        for label in ("Alle akzeptieren", "Akzeptieren", "Zustimmen"):
            try:
                button = page.get_by_role("button", name=re.compile(label, re.I))
                if button.count() and button.first.is_visible():
                    button.first.click(timeout=1500)
                    page.wait_for_timeout(1200)
                    break
            except Exception:
                pass

        # Seite etwas nachladen, aber nur den Bereich Einzelbeiträge auswerten.
        for _ in range(5):
            page.mouse.wheel(0, 2200)
            page.wait_for_timeout(1000)
            try:
                more = page.get_by_text(re.compile(r"Mehr Einträge anzeigen|Mehr anzeigen", re.I))
                if more.count() and more.first.is_visible():
                    more.first.click(timeout=2000)
                    page.wait_for_timeout(1600)
            except Exception:
                pass

        print(f"[INFO] Gerenderter Seitentext: {len(page.locator('body').inner_text(timeout=5000))} Zeichen")

        # Sichtbaren Bereich zwischen 'Einzelbeiträge' und dem nächsten großen Abschnitt bestimmen.
        start_y = None
        end_y = None
        try:
            heading = page.get_by_text(re.compile(r"Servus Nachrichten:\s*Einzelbeiträge", re.I)).first
            box = heading.bounding_box()
            if box:
                start_y = box["y"]
                print(f"[INFO] Einzelbeiträge-Bereich beginnt bei y={start_y:.0f}")
        except Exception:
            pass

        for pattern in (r"Das könnte Ihnen auch gefallen", r"Mehr zu:\s*Servus Nachrichten"):
            try:
                h = page.get_by_text(re.compile(pattern, re.I)).first
                box = h.bounding_box()
                if box:
                    if end_y is None or box["y"] < end_y:
                        end_y = box["y"]
            except Exception:
                pass

        if end_y is not None:
            print(f"[INFO] Einzelbeiträge-Bereich endet bei y={end_y:.0f}")

        links = page.locator("a[href]").evaluate_all(
            """els => els.map(a => {
                const r = a.getBoundingClientRect();
                return {
                    href: a.href,
                    text: (a.innerText || '').trim(),
                    y: r.top + window.scrollY,
                    visible: !!(r.width && r.height)
                };
            })"""
        )

        # Zuerst nur echte Links innerhalb des Einzelbeiträge-Bereichs.
        scoped = []
        for item in links:
            href = normalize_candidate(item.get("href"))
            if not href or not item.get("visible"):
                continue
            y = item.get("y")
            if start_y is not None and y is not None and y < start_y:
                continue
            if end_y is not None and y is not None and y >= end_y:
                continue
            scoped.append((y if y is not None else 10**9, href, item.get("text") or ""))

        scoped.sort(key=lambda x: x[0])
        for _, href, txt in scoped:
            if href not in candidates:
                candidates.append(href)
                print(f"[KANDIDAT] {href} | {txt[:120]}")

        # Fallback: falls die Layout-Grenzen nicht greifen, nur Links mit 90-Sekunden-Text nehmen.
        if not candidates:
            print("[WARNUNG] Keine Bereichs-Kandidaten gefunden; verwende 90-Sekunden-Text-Fallback.")
            for item in links:
                txt = (item.get("text") or "").lower()
                if "90 sekunden" not in txt:
                    continue
                href = normalize_candidate(item.get("href"))
                if href and href not in candidates:
                    candidates.append(href)
                    print(f"[KANDIDAT] {href} | {item.get('text','')[:120]}")

        browser.close()

    print(f"[INFO] {len(candidates)} echte Beitragskandidaten im Einzelbeiträge-Bereich gefunden.")
    return candidates


def extract_article_data(article_url):
    r = requests.get(article_url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    page_text = " ".join(soup.get_text(" ", strip=True).split())

    title_candidates = []
    for tag in ("h1", "h2"):
        for node in soup.find_all(tag):
            value = " ".join(node.get_text(" ", strip=True).split())
            if value:
                title_candidates.append(value)

    for attrs in ({"property": "og:title"}, {"name": "twitter:title"}):
        meta = soup.find("meta", attrs=attrs)
        if meta and meta.get("content"):
            title_candidates.append(meta["content"])

    if soup.title:
        title_candidates.append(soup.title.get_text(" ", strip=True))

    full_title = " ".join(x for x in title_candidates if x)
    joined = (page_text + " " + full_title).lower()
    is_news90 = "servus nachrichten in 90 sekunden" in joined or "nachrichten in 90 sekunden" in joined

    generic_titles = {
        "servus nachrichten in 90 sekunden",
        "nachrichten in 90 sekunden",
        "servus nachrichten: einzelbeiträge",
        "servus nachrichten: aktuelle meldungen und videos",
        "servus nachrichten: aktuelle meldungen und videos - servustv on",
        "servustv on",
    }

    title = ""
    for candidate in title_candidates:
        cleaned = clean_title(candidate)
        low = cleaned.lower()
        if not cleaned or low in generic_titles:
            continue
        # Keine Seiten-/Rubriküberschrift als Headline akzeptieren.
        if low.startswith("servus nachrichten:"):
            continue
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

    for index, href in enumerate(candidates[:40], 1):
        try:
            print(f"[INFO] Prüfe Kandidat {index}: {href}")
            title, image, is_news90 = extract_article_data(href)

            if not is_news90:
                print("[INFO] Übersprungen: kein bestätigter 90-Sekunden-Beitrag.")
                continue
            if not title:
                print("[INFO] Übersprungen: nur generische Rubrik-/Seitentitel gefunden.")
                continue

            data = load_existing_data()
            data["news90_title"] = title
            data["news90_link"] = href
            if image:
                data["news90_image"] = image
                data["news90_thumbnail"] = image

            JSON_PATH.write_text(
                json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            print(f"[ERFOLG] Neuester 90-Sekunden-Beitrag: {title}")
            print(f"[ERFOLG] Link: {href}")
            if image:
                print(f"[ERFOLG] Bild: {image}")
            print("[INFO] headlines.json aktualisiert.")
            return

        except Exception as exc:
            print(f"[WARNUNG] Kandidat konnte nicht verarbeitet werden: {exc}")

    print("[WARNUNG] Kein bestätigter 90-Sekunden-Beitrag im Einzelbeiträge-Bereich gefunden.")
    print("[WARNUNG] Bestehende news90-Daten bleiben unverändert.")


if __name__ == "__main__":
    get_latest_news90()
