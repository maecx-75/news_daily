import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "headlines.json"

PAGE_URL = "https://www.servustv.com/aktuelles/b/servus-wetter-in-90-sekunden/aa90vbht0krb2cmu1ahq/"
HEADERS = {"User-Agent": "Mozilla/5.0"}


def clean_title(t: str) -> str:
    t = re.sub(r"\s*\|\s*Wetter in 90 Sekunden\s*$", "", t, flags=re.I)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def pick_latest():
    r = requests.get(PAGE_URL, headers=HEADERS, timeout=25)
    r.raise_for_status()
    s = BeautifulSoup(r.text, "html.parser")

    # Wichtig:
    # Auf der Übersichtsseite heißen die neuesten Folgen oft NICHT
    # "Servus Wetter in 90 Sekunden - xx:xx Uhr".
    # Deshalb nehmen wir den ersten sinnvollen /aktuelles/v/ Link
    # aus dem Archivbereich.
    candidates = []

    for a in s.find_all("a", href=True):
        href = urljoin(PAGE_URL, a["href"])
        txt = " ".join(a.get_text(" ", strip=True).split())

        if "/aktuelles/v/" not in href:
            continue
        if not txt:
            continue

        # Unbrauchbare Treffer rausfiltern
        lower = txt.strip().lower()
        if lower in {
            "servus wetter in 90 sekunden",
            "favoriten",
            "teilen",
        }:
            continue

        # Brauchbare Videotitel sammeln
        candidates.append((txt, href))

    if not candidates:
        raise RuntimeError("Keinen Wetter-90-Eintrag gefunden.")

    # Der erste passende Eintrag auf der Seite ist der aktuellste
    full_title, href = candidates[0]
    short_title = clean_title(full_title)
    return short_title, full_title, href


def find_image(video_url: str):
    r = requests.get(video_url, headers=HEADERS, timeout=25)
    r.raise_for_status()
    s = BeautifulSoup(r.text, "html.parser")

    og = s.find("meta", attrs={"property": "og:image"})
    if og and og.get("content"):
        return og["content"]

    tw = s.find("meta", attrs={"name": "twitter:image"})
    if tw and tw.get("content"):
        return tw["content"]

    for img in s.find_all("img"):
        src = img.get("src") or img.get("data-src")
        if src and any(ext in src.lower() for ext in [".jpg", ".jpeg", ".png", ".webp"]):
            return urljoin(video_url, src)

    return ""


def main():
    short_title, full_title, href = pick_latest()
    image_url = find_image(href)

    data = {}
    if JSON_PATH.exists():
        data = json.loads(JSON_PATH.read_text(encoding="utf-8"))

    data["weather90_title"] = full_title
    data["weather90_short"] = short_title
    data["weather90_link"] = href
    data["weather90_image"] = image_url

    JSON_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("weather90 updated:", full_title, href, image_url)


if __name__ == "__main__":
    main()
