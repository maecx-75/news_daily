import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "headlines.json"

# Nur diese Servus-Nachrichten-Unterseite wird als Quelle verwendet.
SERIES_URL = "https://www.servustv.com/de/page/AA-1Y5RJCD1H2111"

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


def urls_from_text(text, base_url):
    if not text:
        return []

    text = (
        text.replace("\\u002F", "/")
        .replace("\\u002f", "/")
        .replace("\\/", "/")
    )

    patterns = [
        r'https?://(?:www\.)?servustv\.com/de/page/[A-Z0-9-]+(?:/[^"\'<>\\\s?#]+)?',
        r'/de/page/[A-Z0-9-]+(?:/[^"\'<>\\\s?#]+)?',
    ]

    out = []
    for pattern in patterns:
        for value in re.findall(pattern, text, flags=re.I):
            url = urljoin(base_url, value).split("?")[0].rstrip("/.,;)")
            if url.rstrip("/") == SERIES_URL.rstrip("/"):
                continue
            if url not in out:
                out.append(url)
    return out


def discover_with_browser():
    print(f"[INFO] Öffne ausschließlich Servus-Nachrichten-Unterseite: {SERIES_URL}")

    candidates = []
    network_candidates = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            locale="de-AT",
            user_agent=HEADERS["User-Agent"],
            viewport={"width": 1440, "height": 1600},
        )
        page = context.new_page()

        def inspect_response(response):
            try:
                ctype = (response.headers.get("content-type") or "").lower()
                if not any(x in ctype for x in ("json", "text", "javascript")):
                    return

                body = response.text()
                for url in urls_from_text(body, response.url):
                    if url not in network_candidates:
                        network_candidates.append(url)
            except Exception:
                pass

        page.on("response", inspect_response)

        page.goto(SERIES_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        # Consent-Dialog schließen, falls vorhanden.
        for label in ("Alle akzeptieren", "Akzeptieren", "Zustimmen"):
            try:
                button = page.get_by_role("button", name=re.compile(label, re.I))
                if button.count() and button.first.is_visible():
                    button.first.click(timeout=1500)
                    page.wait_for_timeout(1200)
                    break
            except Exception:
                pass

        # Einzelbeiträge nachladen. Die Seite ist normalerweise neu -> alt sortiert.
        for _ in range(6):
            page.mouse.wheel(0, 2600)
            page.wait_for_timeout(1200)
            try:
                more = page.get_by_text(
                    re.compile(r"Mehr Einträge anzeigen|Mehr anzeigen", re.I)
                )
                if more.count() and more.first.is_visible():
                    more.first.click(timeout=2000)
                    page.wait_for_timeout(1800)
            except Exception:
                pass

        html = page.content()
        body_text = page.locator("body").inner_text(timeout=5000)
        print(f"[INFO] Gerenderter Seitentext: {len(body_text)} Zeichen")

        # Wichtig: Auf dieser Unterseite sammeln wir ALLE ServusTV-Beitragslinks
        # in DOM-Reihenfolge. Danach wird jeder Link geprüft, ob er wirklich
        # 'Servus Nachrichten in 90 Sekunden' ist.
        links = page.locator("a[href]").evaluate_all(
            "els => els.map(a => ({href:a.href, text:(a.innerText||'').trim()}))"
        )

        for item in links:
            href = (item.get("href") or "").split("?")[0].rstrip("/")
            if "/de/page/" not in href:
                continue
            if href == SERIES_URL.rstrip("/"):
                continue
            if href not in candidates:
                candidates.append(href)

        # Zusätzlich Links aus gerendertem HTML und Netzwerkantworten ergänzen.
        for href in urls_from_text(html, SERIES_URL):
            if href not in candidates:
                candidates.append(href)

        browser.close()

    for href in network_candidates:
        if href not in candidates:
            candidates.append(href)

    print(f"[INFO] {len(candidates)} Beitragskandidaten auf der Unterseite gefunden.")
    for href in candidates[:15]:
        print(f"[KANDIDAT] {href}")

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

    full_title = next((x for x in title_candidates if x), "")

    # Strenger Filter: Nur echte 90-Sekunden-Beiträge dürfen die Kachel ersetzen.
    joined = (page_text + " " + full_title).lower()
    is_news90 = (
        "servus nachrichten in 90 sekunden" in joined
        or "nachrichten in 90 sekunden" in joined
    )

    title = ""
    for candidate in title_candidates:
        cleaned = clean_title(candidate)
        low = cleaned.lower()
        if not cleaned:
            continue
        if low in {
            "servus nachrichten in 90 sekunden",
            "nachrichten in 90 sekunden",
            "servus nachrichten: aktuelle meldungen und videos",
            "servustv on",
        }:
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

    # Fundreihenfolge der Unterseite = neueste Beiträge zuerst.
    for index, href in enumerate(candidates[:80], 1):
        try:
            print(f"[INFO] Prüfe Kandidat {index}: {href}")
            title, image, is_news90 = extract_article_data(href)

            if not is_news90:
                print("[INFO] Übersprungen: kein 'Servus Nachrichten in 90 Sekunden'-Beitrag.")
                continue

            if not title:
                print("[INFO] Übersprungen: keine belastbare Headline gefunden.")
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

    print("[WARNUNG] Auf der Servus-Nachrichten-Unterseite wurde kein bestätigter 90-Sekunden-Beitrag gefunden.")
    print("[WARNUNG] Bestehende news90-Daten bleiben unverändert.")


if __name__ == "__main__":
    get_latest_news90()
