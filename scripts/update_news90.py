import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "headlines.json"
IMG_PATH = ROOT / "news90.png"

PAGE_URL = "https://www.servustv.com/de/page/AAYGF2URW6ALQYE42IJK"
HEADERS = {"User-Agent": "Mozilla/5.0"}


def clean_title(t):
    t = re.sub(r"\s*\|\s*Nachrichten in 90 Sekunden\s*$", "", t, flags=re.I)
    return re.sub(r"\s+", " ", t).strip()


def pick_latest():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=HEADERS["User-Agent"])
        page.goto(PAGE_URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(3000)

        html = page.content()
        browser.close()

    s = BeautifulSoup(html, "html.parser")
    candidates = []

    for a in s.find_all("a", href=True):
        href = urljoin(PAGE_URL, a["href"])
        txt = " ".join(a.get_text(" ", strip=True).split())

        if "/de/page/" not in href and "/aktuelles/v/" not in href:
            continue
        if not txt:
            continue

        lower = txt.lower()

        if "90" in lower or "sekunden" in lower or "nachrichten" in lower:
            candidates.append((txt, href))

    if not candidates:
        raise RuntimeError("Kein 90-Sekunden-Video gefunden.")

    return candidates[0]


def extract_topics(video_url):
    r = requests.get(video_url, headers=HEADERS, timeout=25)
    r.raise_for_status()
    s = BeautifulSoup(r.text, "html.parser")

    meta = s.find("meta", attrs={"name": "description"})
    if meta and meta.get("content") and "|" in meta["content"]:
        parts = [p.strip() for p in meta["content"].split("|")]
        return " | ".join(parts[:3])

    text = s.get_text("\n", strip=True)
    best_line = ""

    for line in text.split("\n"):
        if "|" not in line:
            continue
        if "ServusTV" in line or "Mehr anzeigen" in line:
            continue
        if len(line) < 30:
            continue
        if line.count("|") >= 2 and len(line) > len(best_line):
            best_line = line

    if best_line:
        parts = [p.strip() for p in best_line.split("|") if len(p.strip()) > 10]
        return " | ".join(parts[:3])

    return ""


def find_image(video_url):
    r = requests.get(video_url, headers=HEADERS, timeout=25)
    r.raise_for_status()
    s = BeautifulSoup(r.text, "html.parser")

    og = s.find("meta", attrs={"property": "og:image"})
    if og and og.get("content"):
        return og["content"]

    tw = s.find("meta", attrs={"name": "twitter:image"})
    if tw and tw.get("content"):
        return tw["content"]

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

    img = find_image(href)
    if img:
        try:
            ir = requests.get(img, headers=HEADERS, timeout=25)
            if ir.status_code == 200:
                IMG_PATH.write_bytes(ir.content)
        except Exception as e:
            print("Bild konnte nicht geladen werden:", e)

    JSON_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("news90 updated:", title, href, topics)


if __name__ == "__main__":
    main()
