import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "headlines.json"
NEWS_URL = "https://www.servustv.com/de/nachrichten"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0 Safari/537.36"
    )
}


def clean_title(text: str) -> str:
    text = " ".join((text or "").split())
    text = re.sub(
        r"\s*\|\s*Servus Nachrichten in 90 Sekunden\s*$",
        "",
        text,
        flags=re.IGNORECASE,
    )
    return text.strip()


def find_image_near_link(link, page_url: str) -> str:
    # Zuerst direkt im Link bzw. in den nächsten Eltern-Containern suchen.
    nodes = [link]
    parent = link.parent
    for _ in range(5):
        if parent is None:
            break
        nodes.append(parent)
        parent = parent.parent

    for node in nodes:
        img = node.find("img") if hasattr(node, "find") else None
        if not img:
            continue
        for attr in ("src", "data-src", "data-lazy-src"):
            value = img.get(attr)
            if value:
                return urljoin(page_url, value)
        srcset = img.get("srcset")
        if srcset:
            first = srcset.split(",")[0].strip().split(" ")[0]
            if first:
                return urljoin(page_url, first)
    return ""


def extract_og_image(article_url: str) -> str:
    response = requests.get(article_url, headers=HEADERS, timeout=25)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    for attrs in ({"property": "og:image"}, {"name": "twitter:image"}):
        meta = soup.find("meta", attrs=attrs)
        if meta and meta.get("content"):
            return urljoin(article_url, meta["content"])
    return ""


def get_latest_news90():
    print("[INFO] Lade ServusTV-Nachrichtenseite …")
    response = requests.get(NEWS_URL, headers=HEADERS, timeout=25)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    # Die Seite ist chronologisch aufgebaut. Wir nehmen den ersten echten
    # Beitrag, dessen sichtbarer Titel 'Servus Nachrichten in 90 Sekunden' enthält.
    candidate = None

    for link in soup.find_all("a", href=True):
        text = " ".join(link.get_text(" ", strip=True).split())
        if "servus nachrichten in 90 sekunden" not in text.lower():
            continue

        href = urljoin(NEWS_URL, link["href"])
        title = clean_title(text)

        # Navigations-/Serienlinks ohne konkrete Headline ausschließen.
        if not title or title.lower() == "servus nachrichten in 90 sekunden":
            continue

        candidate = (title, href, link)
        break

    if candidate is None:
        raise RuntimeError("Keinen aktuellen 'Servus Nachrichten in 90 Sekunden'-Beitrag gefunden.")

    title, href, link = candidate
    image = find_image_near_link(link, NEWS_URL)
    if not image:
        image = extract_og_image(href)

    print(f"[ERFOLG] Gefunden: {title}")
    print(f"[ERFOLG] Link: {href}")
    if image:
        print(f"[ERFOLG] Bild: {image}")
    else:
        print("[WARNUNG] Kein Bild gefunden – vorhandenes Bild bleibt erhalten.")

    if JSON_PATH.exists():
        try:
            data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
    else:
        data = {}

    # Nur die Kachel 'Servus Nachrichten in 90 Sekunden' aktualisieren.
    # Ticker und andere Kacheln bleiben bewusst unangetastet.
    data["news90_title"] = title
    data["news90_link"] = href
    if image:
        data["news90_image"] = image
        data["news90_thumbnail"] = image

    JSON_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("[INFO] headlines.json aktualisiert.")


if __name__ == "__main__":
    get_latest_news90()
