import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

PAGE_URL = "https://www.servustv.com/aktuelles/b/servus-nachrichten-in-90-sekunden/aaygf2urw6alqye42ijk/"
ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "headlines.json"

def clean_title(title: str) -> str:
    title = re.sub(r"\s*\|\s*Nachrichten in 90 Sekunden\s*$", "", title, flags=re.IGNORECASE).strip()
    return title

def find_latest_news90():
    resp = requests.get(PAGE_URL, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    for a in soup.find_all("a", href=True):
        text = " ".join(a.get_text(" ", strip=True).split())
        if not text:
            continue
        if "Nachrichten in 90 Sekunden" not in text:
            continue
        if text.strip() == "Servus Nachrichten in 90 Sekunden":
            continue

        href = urljoin(PAGE_URL, a["href"])
        return clean_title(text), href, text

    raise RuntimeError("Keinen 90-Sekunden-Eintrag gefunden.")

def main():
    title_short, href, title_full = find_latest_news90()

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
    print(f"Updated: {changed} | {title_short} | {href}")
    return changed

if __name__ == "__main__":
    main()
