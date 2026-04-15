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
        return clean_title(text), urljoin(PAGE_URL, a["href"]), text
    raise RuntimeError("Keinen aktuellen 90-Sekunden-Eintrag gefunden.")

def extract_image(video_url: str):
    resp = requests.get(video_url, timeout=20, headers=HEADERS)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for attrs in ({"property": "og:image"}, {"name": "twitter:image"}):
        meta = soup.find("meta", attrs=attrs)
        if meta and meta.get("content"):
            return meta["content"]
    img = soup.find("img")
    if img:
        for attr in ("src","data-src"):
            if img.get(attr):
                return urljoin(video_url, img[attr])
    raise RuntimeError("Kein Bild gefunden.")

title_short, href, title_full = find_latest_video()
image_url = extract_image(href)

data = {}
if JSON_PATH.exists():
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
data["topmeldung90"] = title_short
data["news90_link"] = href
data["news90_title"] = title_full
JSON_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

img = requests.get(image_url, timeout=30, headers=HEADERS)
img.raise_for_status()
IMG_PATH.write_bytes(img.content)
print("Updated news90:", title_short, href, image_url)
