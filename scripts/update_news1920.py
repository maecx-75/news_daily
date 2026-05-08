import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "headlines.json"

PAGE_URL = "https://www.servustv.com/de/page/AA-1Y5RJCD1H2111"
HEADERS = {"User-Agent": "Mozilla/5.0"}


def clean_text(t: str) -> str:
    return re.sub(r"\s+", " ", t or "").strip()


def clean_title(t: str) -> str:
    t = clean_text(t)
    t = re.sub(r"^\s*(NEUE FOLGE\s*)?", "", t, flags=re.I)
    t = re.sub(r"^\s*\d+\s*Min\.\s*", "", t, flags=re.I)
    return clean_text(t)


def pick_latest():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=HEADERS["User-Agent"])
        page.goto(PAGE_URL, wait_until="domcontentloaded", timeout=60000)

        page.wait_for_timeout(3000)

        for _ in range(8):
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

        if not href or "/page/" not in href:
            continue

        if href.split("?")[0] == PAGE_URL.split("?")[0]:
            continue

        lower = txt.lower()

        if "servus nachrichten" not in lower:
            continue

        if "90 sekunden" in lower:
            continue

        if "der wegscheider" in lower:
            continue

        # 19:20 ist meistens länger, z. B. 14 Min.
        if "19:20" in lower or "14 min" in lower or "15 min" in lower or "16 min" in lower:
            title = clean_title(txt)
            candidates.append((title, href))
            print("GEFUNDEN 19:20:", title, href)

    if not candidates:
        raise RuntimeError("Keine aktuelle 19:20-Folge gefunden.")

    return candidates[0]


def find_three_headlines(video_url: str):
    r = requests.get(video_url, headers=HEADERS, timeout=25)
    r.raise_for_status()
    s = BeautifulSoup(r.text, "html.parser")

    meta = s.find("meta", attrs={"name": "description"})
    if meta and meta.get("content") and "|" in meta["content"]:
        parts = [clean_text(p) for p in meta["content"].split("|")]
        parts = [p for p in parts if len(p) > 3]
        return " | ".join(parts[:3])

    text = " ".join(s.get_text(" ", strip=True).split())

    matches = re.findall(
        r"([A-ZÄÖÜa-zäöüß0-9][^|]{3,80}\s\|\s[^|]{3,80}\s\|\s[^|]{3,80})",
        text
    )

    if matches:
        return clean_text(matches[-1])

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

    return ""


def main():
    title, href = pick_latest()
    image_url = find_image(href)
    headlines = find_three_headlines(href)

    data = {}
    if JSON_PATH.exists():
        data = json.loads(JSON_PATH.read_text(encoding="utf-8"))

    data["news1920_title"] = title
    data["news1920_headlines"] = headlines
    data["news1920_link"] = href
    data["news1920_image"] = image_url

    JSON_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("news1920 updated:", title, headlines, href, image_url)


if __name__ == "__main__":
    main()
