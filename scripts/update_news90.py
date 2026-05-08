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


def clean_text(t: str) -> str:
    return re.sub(r"\s+", " ", t or "").strip()


def clean_title(t: str) -> str:
    t = clean_text(t)
    t = re.sub(r"\s*\|\s*Nachrichten in 90 Sekunden\s*$", "", t, flags=re.I)
    t = re.sub(r"^\s*(NEUE FOLGE\s*)?", "", t, flags=re.I)
    t = re.sub(r"^\s*\d+\s*(Sek\.|Min\.)\s*", "", t, flags=re.I)
    t = re.sub(r"\s*Servus Nachrichten\s*$", "", t, flags=re.I)
    return clean_text(t)


def pick_latest():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=HEADERS["User-Agent"])
        page.goto(PAGE_URL, wait_until="domcontentloaded", timeout=60000)

        page.wait_for_timeout(3000)

        for _ in range(10):
            page.mouse.wheel(0, 1200)
            page.wait_for_timeout(800)

        links = page.eval_on_selector_all(
            "a",
            """els => els.map(a => ({
                href: a.href,
                text: (a.innerText || a.textContent || "").trim()
            }))"""
        )

        browser.close()

    candidates = []

    for item in links:
        href = item.get("href", "")
        txt = clean_text(item.get("text", ""))

        if not href:
            continue

        if "/page/" not in href:
            continue

        if href.split("?")[0] == PAGE_URL.split("?")[0]:
            continue

        lower = txt.lower()

        # Nur echte Servus-Nachrichten-Kacheln
        if "servus nachrichten" not in lower:
            continue

        # Andere Formate ausschließen
        if "der wegscheider" in lower:
            continue
        if "blickwechsel" in lower:
            continue
        if "servus nachrichten 19:20" in lower:
            continue

        # 90-Sekunden / Kurzvideo-Kacheln: oft "15 Sek.", "1 Min.", "2 Min."
        if not (
            "sek." in lower
            or "1 min" in lower
            or "2 min" in lower
            or "3 min" in lower
        ):
            continue

        title = clean_title(txt)

        if not title:
            title = read_title_from_video(href)

        candidates.append((title, href))
        print("GEFUNDEN:", title, href)

    if not candidates:
        raise RuntimeError("Kein 90-Sekunden-Video gefunden.")

    return candidates[0]


def read_title_from_video(video_url: str) -> str:
    r = requests.get(video_url, headers=HEADERS, timeout=25)
    r.raise_for_status()
    s = BeautifulSoup(r.text, "html.parser")

    og = s.find("meta", attrs={"property": "og:title"})
    if og and og.get("content"):
        return clean_title(og["content"])

    h1 = s.find("h1")
    if h1:
        return clean_title(h1.get_text(" ", strip=True))

    return "Nachrichten in 90 Sekunden"


def extract_topics(video_url: str) -> str:
    r = requests.get(video_url, headers=HEADERS, timeout=25)
    r.raise_for_status()
    s = BeautifulSoup(r.text, "html.parser")

    meta = s.find("meta", attrs={"name": "description"})
    if meta and meta.get("content") and "|" in meta["content"]:
        parts = [clean_text(p) for p in meta["content"].split("|")]
        parts = [p for p in parts if len(p) > 5]
        return " | ".join(parts[:3])

    text = s.get_text("\n", strip=True)
    best_line = ""

    for line in text.split("\n"):
        line = clean_text(line)

        if "|" not in line:
            continue
        if "ServusTV" in line:
            continue
        if "Mehr anzeigen" in line:
            continue
        if len(line) < 20:
            continue

        if line.count("|") >= 2 and len(line) > len(best_line):
            best_line = line

    if best_line:
        parts = [clean_text(p) for p in best_line.split("|")]
        parts = [p for p in parts if len(p) > 5]
        return " | ".join(parts[:3])

    return ""


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

    return None


def main():
    title, href = pick_latest()
    short = clean_title(title)
    topics = extract_topics(href)

    data = {}
    if JSON_PATH.exists():
        data = json.loads(JSON_PATH.read_text(encoding="utf-8"))

    data["topmeldung90"] = short
    data["news90_title"] = short
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

    print("news90 updated:", short, href, topics)


if __name__ == "__main__":
    main()
