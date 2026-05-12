import json
import re
from pathlib import Path
from datetime import datetime

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tv_program.json"

URL = "https://tvheute.at/servustv-programm/heute-im-tv"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()

def main():
    html = requests.get(URL, headers=HEADERS, timeout=20).text
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n")

    pattern = re.compile(
        r"ServusTV\s+([A-Za-zÄÖÜäöüß]+)?\s*(\d{2}:\d{2})\s+(\d{2}:\d{2})\s+.*?\n\s*(.+?)\n",
        re.MULTILINE
    )

    items = []

    lines = [clean(x) for x in text.splitlines() if clean(x)]

    for i, line in enumerate(lines):
        if line == "ServusTV" and i + 5 < len(lines):
            genre = lines[i + 1] if not re.match(r"\d{2}:\d{2}", lines[i + 1]) else ""
            times = [x for x in lines[i:i+8] if re.match(r"\d{2}:\d{2}", x)]

            if len(times) >= 2:
                title_index = i + 5
                title = lines[title_index] if title_index < len(lines) else ""

                if title and title not in ["Jetzt LIVE streamen", "Mehr zur Sendung"]:
                    items.append({
                        "start": times[0],
                        "end": times[1],
                        "genre": genre,
                        "title": title,
                        "description": ""
                    })

    # Duplikate entfernen
    unique = []
    seen = set()

    for item in items:
        key = item["start"] + item["end"] + item["title"]
        if key not in seen:
            seen.add(key)
            unique.append(item)

    data = {
        "source": URL,
        "updated": datetime.now().isoformat(timespec="seconds"),
        "program": unique[:40]
    }

    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"TV Programm gespeichert: {len(unique)} Sendungen")

if __name__ == "__main__":
    main()
