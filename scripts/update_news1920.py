import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "headlines.json"

PAGE_URL = "https://www.servustv.com/aktuelles/b/servus-nachrichten/aa-1y5rjcd1h2111/"
HEADERS = {"User-Agent": "Mozilla/5.0"}


def pick_latest():
    r = requests.get(PAGE_URL, headers=HEADERS, timeout=25)
    r.raise_for_status()
    s = BeautifulSoup(r.text, "html.parser")

    for a in s.find_all("a", href=True):
        href = urljoin(PAGE_URL, a["href"])
        txt = " ".join(a.get_text(" ", strip=True).split())

        if "/aktuelles/v/" not in href:
            continue
        if not txt:
            continue
        if "Nachrichten 19:20" not in txt:
            continue

        return txt, href

    raise RuntimeError("Keine aktuelle 19:20-Folge gefunden.")


def find_three_headlines(video_url: str):
    r = requests.get(video_url, headers=HEADERS, timeout=25)
    r.raise_for_status()
    s = BeautifulSoup(r.text, "html.parser")

    text = " ".join(s.get_text(" ", strip=True).split())

    matches = re.findall(
        r"([A-ZÄÖÜa-zäöüß0-9][^|]{5,80}\s\|\s[^|]{5,80}\s\|\s[^|]{5,80})",
        text
    )

    if matches:
        return matches[-1].strip()

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
