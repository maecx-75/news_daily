import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "headlines.json"

API_URL = "https://tv-api.redbull.com/products/dynamic/v5.1/stv/de/us/AA-1Y5RJCD1H2111"
BASE_URL = "https://www.servustv.com"

HEADERS = {"User-Agent": "Mozilla/5.0"}


def clean(text):
    return " ".join(str(text or "").split()).strip()


def all_strings(obj):
    values = []
    if isinstance(obj, dict):
        for v in obj.values():
            values.extend(all_strings(v))
    elif isinstance(obj, list):
        for item in obj:
            values.extend(all_strings(item))
    elif isinstance(obj, str):
        values.append(obj)
    return values


def find_url(obj):
    for text in all_strings(obj):
        if "/de/page/" in text:
            url = text.split("?")[0] if "cid=" not in text else text
            return urljoin(BASE_URL, url)
    return ""


def find_image(obj):
    for text in all_strings(obj):
        if text.startswith("http") and any(x in text.lower() for x in [".jpg", ".jpeg", ".png", "image", "img.liiift"]):
            return text
    return ""


def walk(obj, results):
    if isinstance(obj, dict):
        text_blob = " ".join(all_strings(obj)).lower()

        if "servus nachrichten in 90 sekunden" in text_blob:
            url = find_url(obj)
            if url and "AA-1Y5RJCD1H2111" not in url:
                title = (
                    obj.get("title")
                    or obj.get("headline")
                    or obj.get("name")
                    or "Servus Nachrichten in 90 Sekunden"
                )

                subtitle = (
                    obj.get("subtitle")
                    or obj.get("description")
                    or obj.get("shortDescription")
                    or ""
                )

                image = find_image(obj) or "news90.png"

                results.append({
                    "title": clean(title),
                    "url": url,
                    "subtitle": clean(subtitle),
                    "image": image,
                    "text_blob": clean(" ".join(all_strings(obj)))
                })

        for v in obj.values():
            walk(v, results)

    elif isinstance(obj, list):
        for item in obj:
            walk(item, results)


def extract_ticker(text_blob, title):
    match = re.search(
        r"Servus Nachrichten in 90 Sekunden\s*(.*?)\s*(Jetzt ansehen|Serie anzeigen|2 Min\.|$)",
        text_blob,
        re.I
    )

    if match:
        ticker = clean(match.group(1))
        if "|" in ticker:
            return ticker

    return title


def main():
    old = {}

    if JSON_PATH.exists():
        try:
            old = json.loads(JSON_PATH.read_text(encoding="utf-8"))
        except Exception:
            old = {}

    res = requests.get(API_URL, headers=HEADERS, timeout=30)
    data = res.json()

    results = []
    walk(data, results)

    if not results:
        print("DEBUG: Keine Treffer gefunden.")
        raise RuntimeError("Keine 90-Sekunden-Folge gefunden.")

    first = results[0]

    title = first["title"]
    url = first["url"]
    image = first["image"]

    ticker = extract_ticker(first["text_blob"], title)

    topics = [clean(x) for x in ticker.split("|") if clean(x)]
    topics = topics[:3] if topics else [title]
    ticker = " | ".join(topics)

    result = {
        "title": title,
        "short_title": title,
        "full_title": title,

        "url": url,
        "href": url,

        "image": image,
        "thumbnail": image,

        "news90_title": title,
        "news90_link": url,
        "news90_image": image,
        "news90_thumbnail": image,

        "topics": topics,

        "ticker": ticker,
        "ticker90": ticker,
        "topmeldung90": ticker,

        "description": first["subtitle"]
    }

    if "google_headlines" in old:
        result["google_headlines"] = old["google_headlines"]

    JSON_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("AKTUELLE FOLGE:")
    print(title)
    print(url)
    print(image)
    print(ticker)


if __name__ == "__main__":
    main()
