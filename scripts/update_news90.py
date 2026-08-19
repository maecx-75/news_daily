import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "headlines.json"
NEWS_URL = "https://www.servustv.com/de/nachrichten"
SERIES_URL = "https://www.servustv.com/de/page/AAYGF2URW6ALQYE42IJK"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0 Safari/537.36"
    ),
    "Accept-Language": "de-AT,de;q=0.9,en;q=0.7",
}


def clean_title(text: str) -> str:
    text = " ".join((text or "").split())
    text = re.sub(
        r"\s*\|\s*(Servus )?Nachrichten in 90 Sekunden(?:\s*-\s*ServusTV On)?\s*$",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s*-\s*ServusTV On\s*$", "", text, flags=re.IGNORECASE)
    return text.strip()


def normalize_html(raw: str) -> str:
    # Viele SPA-Daten liegen escaped im HTML/JSON der Seite.
    return (
        raw.replace("\\u002F", "/")
           .replace("\\u002f", "/")
           .replace("\\/", "/")
           .replace("&amp;", "&")
    )


def extract_candidate_urls(raw_html: str, base_url: str) -> list[str]:
    html = normalize_html(raw_html)
    found = []

    patterns = [
        r'https?://www\.servustv\.com/de/page/[A-Z0-9-]+/servus-nachrichten-in-90-sekunden-[^"\'<>\\\s]+',
        r'/de/page/[A-Z0-9-]+/servus-nachrichten-in-90-sekunden-[^"\'<>\\\s]+',
    ]

    for pattern in patterns:
        for match in re.findall(pattern, html, flags=re.IGNORECASE):
            url = urljoin(base_url, match)
            url = url.split("?")[0]
            if url not in found:
                found.append(url)

    return found


def extract_article_data(article_url: str):
    response = requests.get(article_url, headers=HEADERS, timeout=25)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    page_text = " ".join(soup.get_text(" ", strip=True).split())
    is_news90 = "servus nachrichten in 90 sekunden" in page_text.lower()

    # Titel: bevorzugt h1/h2, dann OG/Twitter, dann <title>.
    title_candidates = []
    for selector in ("h1", "h2"):
        for node in soup.find_all(selector):
            value = " ".join(node.get_text(" ", strip=True).split())
            if value:
                title_candidates.append(value)

    for attrs in (
        {"property": "og:title"},
        {"name": "twitter:title"},
    ):
        meta = soup.find("meta", attrs=attrs)
        if meta and meta.get("content"):
            title_candidates.append(meta["content"])

    if soup.title and soup.title.string:
        title_candidates.append(soup.title.string)

    title = ""
    for candidate in title_candidates:
        cleaned = clean_title(candidate)
        low = cleaned.lower()
        if not cleaned:
            continue
        if low in {
            "servus nachrichten in 90 sekunden",
            "nachrichten in 90 sekunden",
        }:
            continue
        if "servustv on" == low:
            continue
        title = cleaned
        break

    image = ""
    for attrs in (
        {"property": "og:image"},
        {"name": "twitter:image"},
    ):
        meta = soup.find("meta", attrs=attrs)
        if meta and meta.get("content"):
            image = urljoin(article_url, meta["content"])
            break

    return title, image, is_news90


def discover_candidates() -> list[str]:
    all_candidates = []

    for source_url in (NEWS_URL, SERIES_URL):
        try:
            print(f"[INFO] Lade Quelle: {source_url}")
            response = requests.get(source_url, headers=HEADERS, timeout=25)
            response.raise_for_status()

            candidates = extract_candidate_urls(response.text, source_url)
            print(f"[INFO] {len(candidates)} mögliche 90-Sekunden-Links gefunden.")

            for url in candidates:
                if url not in all_candidates:
                    all_candidates.append(url)
        except Exception as exc:
            print(f"[WARNUNG] Quelle konnte nicht ausgewertet werden: {exc}")

    return all_candidates


def load_existing_data():
    if JSON_PATH.exists():
        try:
            return json.loads(JSON_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {}


def get_latest_news90():
    candidates = discover_candidates()

    if not candidates:
        print("[WARNUNG] Keine Kandidaten im statischen HTML gefunden.")
        print("[WARNUNG] Bestehende news90-Daten bleiben unverändert; Workflow endet ohne Fehler.")
        return

    # Die Quellseiten sind chronologisch sortiert. Daher Kandidaten in Fundreihenfolge testen.
    for index, href in enumerate(candidates[:25], start=1):
        try:
            print(f"[INFO] Prüfe Kandidat {index}: {href}")
            title, image, is_news90 = extract_article_data(href)

            if not is_news90:
                print("[INFO] Übersprungen: kein 90-Sekunden-Beitrag.")
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

            print(f"[ERFOLG] Gefunden: {title}")
            print(f"[ERFOLG] Link: {href}")
            if image:
                print(f"[ERFOLG] Bild: {image}")
            else:
                print("[WARNUNG] Kein Bild gefunden – vorhandenes Bild bleibt erhalten.")
            print("[INFO] headlines.json aktualisiert.")
            return

        except Exception as exc:
            print(f"[WARNUNG] Kandidat konnte nicht verarbeitet werden: {exc}")

    print("[WARNUNG] Kein bestätigter 90-Sekunden-Beitrag gefunden.")
    print("[WARNUNG] Bestehende news90-Daten bleiben unverändert; Workflow endet ohne Fehler.")


if __name__ == "__main__":
    get_latest_news90()
