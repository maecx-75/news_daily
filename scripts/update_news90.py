import json, re
from pathlib import Path
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "headlines.json"
IMG_PATH = ROOT / "news90.png"

PAGE_URL = "https://www.servustv.com/aktuelles/b/servus-nachrichten-in-90-sekunden/aaygf2urw6alqye42ijk/"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def clean_title(t):
    t = re.sub(r"\s*\|\s*Nachrichten in 90 Sekunden\s*$", "", t, flags=re.I)
    return re.sub(r"\s+", " ", t).strip()

def pick_latest():
    r = requests.get(PAGE_URL, headers=HEADERS, timeout=25)
    r.raise_for_status()
    s = BeautifulSoup(r.text, "html.parser")

    for a in s.find_all("a", href=True):
        href = urljoin(PAGE_URL, a["href"])
        txt = " ".join(a.get_text(" ", strip=True).split())

        if "/aktuelles/v/" in href and "Nachrichten in 90 Sekunden" in txt:
            if txt.strip().lower() == "servus nachrichten in 90 sekunden":
                continue
            return txt, href

    raise RuntimeError("Kein Video gefunden")

def extract_topics(video_url):
    r = requests.get(video_url, headers=HEADERS, timeout=25)
    r.raise_for_status()
    s = BeautifulSoup(r.text, "html.parser")

    text = s.get_text("\n", strip=True)

   for line in text.split("\n"):
    if "Die wichtigsten News direkt aus der Redaktion" in line and " | " in line:
        parts = [p.strip() for p in line.split("|")]

        cleaned = []
        for p in parts:
            if not p:
                continue
            if re.match(r"^\d{1,2}\.\d{1,2}\.$", p):
                continue
            if re.match(r"^\d{1,2}:\d{2}\s*Uhr$", p):
                continue
            if p == "Die wichtigsten News direkt aus der Redaktion":
                continue

            p = p.replace("Mehr anzeigen", "").strip()

            if p:
                cleaned.append(p)

        if cleaned:
            return " | ".join(cleaned[:3])

return ""

def find_image(video_url):
    r = requests.get(video_url, headers=HEADERS, timeout=25)
    r.raise_for_status()
    s = BeautifulSoup(r.text, "html.parser")

    og = s.find("meta", attrs={"property": "og:image"})
    if og and og.get("content"):
        return og["content"]

    return None

def main():
    title, href = pick_latest()
    short = clean_title(title)
    topics = extract_topics(href)

    data = {}
    if JSON_PATH.exists():
        data = json.loads(JSON_PATH.read_text(encoding="utf-8"))

    data["topmeldung90"] = short
    data["news90_title"] = title
    data["news90_link"] = href

    if topics:
        data["ticker90"] = topics

    JSON_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    img = find_image(href)
    if img:
        try:
            ir = requests.get(img, headers=HEADERS, timeout=25)
            if ir.status_code == 200:
                IMG_PATH.write_bytes(ir.content)
        except:
            pass

if __name__ == "__main__":
    main()
