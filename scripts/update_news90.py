import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

PAGE_URL = "https://www.servustv.com/aktuelles/b/servus-nachrichten-in-90-sekunden/aaygf2urw6alqye42ijk/"
ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "headlines.json"
IMG_PATH = ROOT / "news90.png"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def clean_title(title: str) -> str:
    return re.sub(r"\s*\|\s*Nachrichten in 90 Sekunden\s*$", "", title, flags=re.IGNORECASE).strip()

def find_latest_video():
    resp = requests.get(PAGE_URL, timeout=20, headers=HEADERS)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    for a in soup.find_all("a", href=True):
        text = " ".join(a.get_text(" ", strip=True).split())
        if "Nachrichten in 90 Sekunden" not in text:
            continue
        if text.strip() == "Servus Nachrichten in 90 Sekunden":
            continue
        href = urljoin(PAGE_URL, a["href"])
        return clean_title(text), href, text

    raise RuntimeError("Keinen aktuellen 90-Sekunden-Eintrag gefunden.")

def extract_image(video_url: str):
    resp = requests.get(video_url, timeout=20, headers=HEADERS)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    og = soup.find("meta", attrs={"property": "og:image"})
    if og and og.get("content"):
        return og["content"]

    tw = soup.find("meta", attrs={"name": "twitter:image"})
    if tw and tw.get("content"):
        return tw["content"]

    img = soup.find("img")
    if img:
        for attr in ("src", "data-src"):
            if img.get(attr):
                return urljoin(video_url, img[attr])

    raise RuntimeError("Kein Bild auf der Videoseite gefunden.")

def download_image(url: str, target: Path):
    resp = requests.get(url, timeout=30, headers=HEADERS)
    resp.raise_for_status()
    target.write_bytes(resp.content)

def main():
    title_short, href, title_full = find_latest_video()
    image_url = extract_image(href)

    data = {}
    if JSON_PATH.exists():
        data = json.loads(JSON_PATH.read_text(encoding="utf-8"))

    changed = (
        data.get("topmeldung90") != title_short or
        data.get("news90_link") != href or
        data.get("news90_title") != title_full
    )

    data["topmeldung90"] = title_short
    data["news90_link"] = href
    data["news90_title"] = title_full

    JSON_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    download_image(image_url, IMG_PATH)

    print(f"Updated title/link/image: {title_short} | {href} | {image_url} | changed={changed}")

if __name__ == "__main__":
    main()
