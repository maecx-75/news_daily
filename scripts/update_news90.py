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
SERIES_URL = "https://www.servustv.com/de/page/AAYGF2URW6ALQYE42IJK"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36",
    "Accept-Language": "de-AT,de;q=0.9,en;q=0.7",
}


def clean_title(text):
    text = " ".join((text or "").split())
    text = re.sub(r"\s*\|\s*(Servus )?Nachrichten in 90 Sekunden.*$", "", text, flags=re.I)
    text = re.sub(r"\s*-\s*ServusTV On\s*$", "", text, flags=re.I)
    return text.strip()


def urls_from_text(text, base_url):
    if not text:
        return []
    text = text.replace("\\u002F", "/").replace("\\u002f", "/").replace("\\/", "/")
    patterns = [
        r'https?://(?:www\.)?servustv\.com/de/page/[A-Z0-9]+(?:/[^"\'<>\\\s?#]+)?',
        r'/de/page/[A-Z0-9]+(?:/[^"\'<>\\\s?#]+)?',
    ]
    out = []
    for pattern in patterns:
        for value in re.findall(pattern, text, flags=re.I):
            url = urljoin(base_url, value).split("?")[0].rstrip("/.,;)")
            if url not in out:
                out.append(url)
    return out


def discover_with_browser():
    print("[INFO] Starte Chromium und rendere ServusTV …")
    candidates = []
    network_candidates = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            locale="de-AT",
            user_agent=HEADERS["User-Agent"],
            viewport={"width": 1440, "height": 1400},
        )
        page = context.new_page()

        def inspect_response(response):
            try:
                ctype = (response.headers.get("content-type") or "").lower()
                if not any(x in ctype for x in ("json", "text", "javascript")):
                    return
                body = response.text()
                low = body.lower()
                if "90 sekunden" not in low and "servus-nachrichten-in-90-sekunden" not in low:
                    return
                for url in urls_from_text(body, response.url):
                    if url not in network_candidates:
                        network_candidates.append(url)
                print(f"[DEBUG] Relevante Netzwerkantwort: {response.url}")
            except Exception:
                pass

        page.on("response", inspect_response)

        for source in (NEWS_URL, SERIES_URL):
            print(f"[INFO] Öffne: {source}")
            try:
                page.goto(source, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(5000)

                # Cookie-/Consent-Dialog, falls vorhanden.
                for label in ("Alle akzeptieren", "Akzeptieren", "Zustimmen"):
                    try:
                        button = page.get_by_role("button", name=re.compile(label, re.I))
                        if button.count():
                            button.first.click(timeout=1500)
                            page.wait_for_timeout(1500)
                            break
                    except Exception:
                        pass

                # Dynamische Listen nachladen.
                for _ in range(4):
                    page.mouse.wheel(0, 2500)
                    page.wait_for_timeout(1200)
                    try:
                        more = page.get_by_text(re.compile(r"Mehr Einträge anzeigen|Mehr anzeigen", re.I))
                        if more.count() and more.first.is_visible():
                            more.first.click(timeout=2000)
                            page.wait_for_timeout(1800)
                    except Exception:
                        pass

                html = page.content()
                body_text = page.locator("body").inner_text(timeout=5000)
                print(f"[INFO] Gerenderter Text: {len(body_text)} Zeichen; enthält '90 Sekunden': {'90 sekunden' in body_text.lower()}")

                # 1) Alle gerenderten Links einsammeln. Nicht auf Anchor-Text verlassen.
                links = page.locator("a[href]").evaluate_all("els => els.map(a => ({href:a.href, text:(a.innerText||'').trim()}))")
                for item in links:
                    href = (item.get("href") or "").split("?")[0]
                    txt = item.get("text") or ""
                    if "/de/page/" not in href:
                        continue
                    if "90 sekunden" in txt.lower() or "servus-nachrichten-in-90-sekunden" in href.lower():
                        if href not in candidates:
                            candidates.append(href)

                # 2) URLs aus komplett gerendertem HTML/JSON extrahieren.
                for href in urls_from_text(html, source):
                    if "servus-nachrichten-in-90-sekunden" in href.lower() and href not in candidates:
                        candidates.append(href)

                # 3) Bei sichtbarem 90-Sekunden-Text nach dem nächsten/vorigen Link suchen.
                soup = BeautifulSoup(html, "html.parser")
                for node in soup.find_all(string=re.compile(r"Servus Nachrichten in 90 Sekunden", re.I)):
                    cur = node.parent
                    for _ in range(10):
                        if cur is None:
                            break
                        anchors = cur.find_all("a", href=True) if hasattr(cur, "find_all") else []
                        for a in anchors:
                            href = urljoin(source, a.get("href", "")).split("?")[0]
                            if "/de/page/" in href and href not in candidates:
                                candidates.append(href)
                        if anchors:
                            break
                        cur = cur.parent
            except Exception as exc:
                print(f"[WARNUNG] Browser-Quelle fehlgeschlagen: {exc}")

        browser.close()

    for href in network_candidates:
        if href not in candidates:
            candidates.append(href)

    print(f"[INFO] Insgesamt {len(candidates)} Kandidaten gefunden.")
    for href in candidates[:10]:
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
            title_candidates.append(node.get_text(" ", strip=True))
    for attrs in ({"property": "og:title"}, {"name": "twitter:title"}):
        meta = soup.find("meta", attrs=attrs)
        if meta and meta.get("content"):
            title_candidates.append(meta["content"])
    if soup.title:
        title_candidates.append(soup.title.get_text(" ", strip=True))

    full_title = next((" ".join(x.split()) for x in title_candidates if x and x.strip()), "")
    is_news90 = (
        "servus nachrichten in 90 sekunden" in page_text.lower()
        or "nachrichten in 90 sekunden" in full_title.lower()
        or "servus-nachrichten-in-90-sekunden" in article_url.lower()
    )

    title = ""
    for candidate in title_candidates:
        cleaned = clean_title(candidate)
        low = cleaned.lower()
        if cleaned and low not in {"servus nachrichten in 90 sekunden", "nachrichten in 90 sekunden", "servustv on"}:
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
            if not is_news90 or not title:
                print("[INFO] Übersprungen: kein bestätigter 90-Sekunden-Beitrag oder kein Titel.")
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
