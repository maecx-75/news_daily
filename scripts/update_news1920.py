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


def pick_latest():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=HEADERS["User-Agent"])

        page.goto(PAGE_URL, wait_until="domcontentloaded", timeout=60000)

        page.wait_for_timeout(3000)

        for _ in range(10):
            page.mouse.wheel(0, 1500)
            page.wait_for_timeout(1000)

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
        href = item["href"]
        txt = " ".join(item["text"].split())

        if not href or "/page/" not in href:
            continue

        lower = txt.lower()

        # Müll raus
        if "wegscheider" in lower:
            continue

        if "blickwechsel" in lower:
            continue

        if "15 sek." in lower:
            continue

        # echte Nachrichten 19:20
        if (
            "servus nachrichten" in lower
            and (
                "19:20" in lower
                or "20 min" in lower
                or "21 min" in lower
                or "22 min" in lower
                or "23 min" in lower
                or "24 min" in lower
            )
        ):
            candidates.append((txt, href))
            print("GEFUNDEN 19:20:", txt, href)

    if not candidates:
        raise RuntimeError("Keine aktuelle 19:20-Folge gefunden.")

    return candidates[0]


def find_three_headlines(video_url):
    r = requests.get(video_url, headers=HEADERS, timeout=25)
    r.raise_for_status()

    s = BeautifulSoup(r.text, "html.parser")

    meta = s.find("meta", attrs={"name": "description"})

    if meta and meta.get("content"):
        text = meta["content"]

        if "|" in text:
            parts = [p.strip() for p in text.split("|")]
            return " | ".join(parts[:3])

    return ""


def find_image(video_url):
    r = requests.get(video_url, headers=HEADERS, timeout=25)
    r.raise_for_status()

    s = BeautifulSoup(r.text, "html.parser")

    og = s.find("meta", attrs={"property": "og:image"})

    if og and og.get("content"):
        return og["content"]

    return ""


def main():
    title, href = pick_latest()

    headlines = find_three_headlines(href)
    image_url = find_image(href)

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

    print("news1920 updated:", title, href)


if __name__ == "__main__":
    main()
