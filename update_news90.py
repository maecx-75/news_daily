import json
import re
from pathlib import Path
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "headlines.json"
IMG_PATH = ROOT / "news90.png"
PAGE_URL = "https://www.servustv.com/aktuelles/b/servus-nachrichten-in-90-sekunden/aaygf2urw6alqye42ijk/"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def clean_title(t: str) -> str:
    t = re.sub(r"\s*\|\s*Nachrichten in 90 Sekunden\s*$", "", t, flags=re.IGNORECASE).strip()
    t = re.sub(r"\s+", " ", t).strip()
    return t

def score_candidate(text: str, href: str) -> int:
    score = 0
    if "/aktuelles/v/" in href:
        score += 10
    if "Nachrichten in 90 Sekunden" in text:
        score += 5
    if len(text) > 25:
        score += 3
    if text.strip() == "Servus Nachrichten in 90 Sekunden":
        score -= 20
    return score

def find_latest_video():
    resp = requests.get(PAGE_URL, timeout=25, headers=HEADERS)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    candidates = []
    for a in soup.find_all("a", href=True):
        href = urljoin(PAGE_URL, a["href"])
        text = " ".join(a.get_text(" ", strip=True).split())
        if "/aktuelles/v/" not in href:
            continue
        if "Nachrichten in 90 Sekunden" not in text:
            continue
        if text.strip() == "Servus Nachrichten in 90 Sekunden":
            continue
        candidates.append((score_candidate(text, href), text, href))

    if not candidates:
        raise RuntimeError("Keinen 90-Sekunden-Eintrag gefunden.")

    candidates.sort(key=lambda x: x[0], reverse=True)
    _, title_full, href = candidates[0]
    title_short = clean_title(title_full)
    return title_short, href, title_full

def extract_image(video_url: str):
    resp = requests.get(video_url, timeout=25, headers=HEADERS)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    for attrs in ({"property": "og:image"}, {"name": "twitter:image"}):
        meta = soup.find("meta", attrs=attrs)
        if meta and meta.get("content"):
            return meta["content"]

    for img in soup.find_all("img"):
        for attr in ("src", "data-src"):
            url = img.get(attr)
            if url:
                url = urljoin(video_url, url)
                if any(part in url.lower() for part in ("jpg", "jpeg", "png", "webp")):
                    return url

    raise RuntimeError("Kein Bild auf der Videoseite gefunden.")

def main():
    title_short, href, title_full = find_latest_video()

    data = {}
    if JSON_PATH.exists():
        data = json.loads(JSON_PATH.read_text(encoding="utf-8"))

    data["topmeldung90"] = title_short
    data["news90_link"] = href
    data["news90_title"] = title_full

    try:
        image_url = extract_image(href)
        img = requests.get(image_url, timeout=30, headers=HEADERS)
        img.raise_for_status()
        IMG_PATH.write_bytes(img.content)
        print("Bild aktualisiert:", image_url)
    except Exception as e:
        print("Bild konnte nicht aktualisiert werden:", e)

    JSON_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
    print("90 Sekunden aktualisiert:", title_short, href)

if __name__ == "__main__":
    main()
