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
    lines = [clean(x) for x in text.splitlines() if clean(x)]

    items = []

    for i, line in enumerate(lines):
        # Beispiel-Zeile enthält:
        # ServusTV Info 09:23 09:25 09:23 09:25
        if "ServusTV" in line and re.search(r"\d{2}:\d{2}", line):
            times = re.findall(r"\d{2}:\d{2}", line)

            if len(times) < 2:
                continue

            start = times[0]
            end = times[1]

            genre = ""
            genre_match = re.search(r"ServusTV\s+([A-Za-zÄÖÜäöüß]+)", line)
            if genre_match:
                genre = genre_match.group(1)

            title = ""
            description = ""

            # Titel steht meistens in den nächsten Zeilen
            for j in range(i + 1, min(i + 8, len(lines))):
                candidate = lines[j]

                if candidate in ["Jetzt LIVE streamen", "Mehr zur Sendung", "Erinnerung"]:
                    continue

                if candidate.startswith("ServusTV"):
                    continue

                if re.fullmatch(r"\d{2}:\d{2}", candidate):
                    continue

                if candidate.startswith("*"):
                    continue

                title = candidate
                break

            # Beschreibung danach suchen
            if title:
                for j in range(i + 2, min(i + 14, len(lines))):
                    candidate = lines[j]

                    if candidate == title:
                        continue

                    if candidate in ["Jetzt LIVE streamen", "Mehr zur Sendung", "Erinnerung"]:
                        continue

                    if candidate.startswith("ServusTV"):
                        continue

                    if re.fullmatch(r"\d{2}:\d{2}", candidate):
                        continue

                    if len(candidate) > 20:
                        description = candidate
                        break

            if title:
                items.append({
                    "start": start,
                    "end": end,
                    "genre": genre,
                    "title": title,
                    "description": description,
                    "is_now": False
                })

    # Duplikate entfernen
    unique = []
    seen = set()

    for item in items:
        key = item["start"] + item["end"] + item["title"]
        if key not in seen:
            seen.add(key)
            unique.append(item)

    # aktuelle Sendung markieren
    now = datetime.now()
    now_minutes = now.hour * 60 + now.minute

    for item in unique:
        try:
            sh, sm = map(int, item["start"].split(":"))
            eh, em = map(int, item["end"].split(":"))

            start_m = sh * 60 + sm
            end_m = eh * 60 + em

            if start_m <= now_minutes <= end_m:
                item["is_now"] = True
        except:
            pass

    data = {
        "source": URL,
        "updated": datetime.now().isoformat(timespec="seconds"),
        "program": unique[:60]
    }

    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"TV Programm gespeichert: {len(unique)} Sendungen")

if __name__ == "__main__":
    main()
